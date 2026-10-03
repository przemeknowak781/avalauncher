"""Render AvaFrame flow-thickness time steps over the Tatra base map: frames + animated GIF.

Usage: python tools/avaframe/render_anim.py data/avaframe/anim web/media/lawina
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "data"
FONT = ROOT / "web" / "vendor" / "fonts" / "Archivo-var.ttf"
TRAIL = {"red": (214, 40, 40), "blue": (31, 95, 209), "green": (42, 157, 60), "yellow": (242, 194, 0), "black": (34, 32, 28)}
INK, PAPER = (29, 27, 23), (244, 239, 228)
# flow thickness ramp [m] -> colour (paper-friendly, hazard family)
RAMP = [(0.05, (255, 214, 170)), (0.3, (249, 145, 72)), (0.8, (232, 89, 12)), (1.5, (166, 59, 0)), (3.0, (90, 26, 0))]


def read_asc(p: Path) -> np.ndarray:
    lines = p.read_text().splitlines()
    return np.loadtxt(lines[6:], dtype=np.float32)


def colour(ft: np.ndarray) -> np.ndarray:
    rgba = np.zeros(ft.shape + (4,), np.float32)
    v = np.nan_to_num(ft)
    for (a, ca), (b, cb) in zip(RAMP, RAMP[1:]):
        m = (v >= a) & (v < b)
        t = ((v - a) / (b - a))[m][:, None]
        rgba[m, :3] = np.array(ca) * (1 - t) + np.array(cb) * t
        rgba[m, 3] = 215
    rgba[v >= RAMP[-1][0], :3] = RAMP[-1][1]
    rgba[v >= RAMP[-1][0], 3] = 230
    return rgba.astype(np.uint8)


def font(size: int, weight: int = 700) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_axes([100, weight])
    except Exception:
        pass
    return f


def main(src: str, out: str) -> None:
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    steps = sorted(((float(re.search(r"_t([\d.]+)\.asc$", p.name).group(1)), p) for p in src.glob("*_FT_t*.asc")))
    grids = [(t, read_asc(p)) for t, p in steps]
    terrain = json.loads((WEB / "terrain.json").read_text(encoding="utf-8"))
    h = terrain["height"]
    base = Image.open(WEB / "map.png").convert("RGB")
    k = base.width / terrain["width"]  # px per analysis cell

    # crop around the maximum extent (ASCII rows run from north, like our grid)
    reach = np.any([np.nan_to_num(g) > 0.05 for _, g in grids], axis=0)
    rows, cols = np.nonzero(reach)
    pad = 45
    r0, r1 = max(0, rows.min() - pad), min(h, rows.max() + pad)
    c0, c1 = max(0, cols.min() - pad), min(terrain["width"], cols.max() + pad)
    side = max(r1 - r0, c1 - c0)
    r0, c0 = max(0, min(r0, h - side)), max(0, min(c0, terrain["width"] - side))
    box = (int(c0 * k), int(r0 * k), int((c0 + side) * k), int((r0 + side) * k))
    W = 1080
    scale = W / (box[2] - box[0])

    def to_px(c, r):
        return ((c * k - box[0]) * scale, (r * k - box[1]) * scale)

    trails = json.loads((WEB / "trails.json").read_text(encoding="utf-8"))
    canvas0 = base.crop(box).resize((W, W), Image.LANCZOS)
    d0 = ImageDraw.Draw(canvas0)
    for t in trails:
        for part in t["paths"]:
            pts = [to_px(c, r) for c, r in part]
            d0.line(pts, fill=(255, 255, 255), width=9, joint="curve")
            d0.line(pts, fill=TRAIL.get(t["color"], TRAIL["red"]), width=5, joint="curve")

    title, small, big = font(30, 800), font(20, 500), font(44, 800)
    frames = []
    for t, g in grids:
        layer = Image.fromarray(colour(g), "RGBA").resize((terrain["width"] * 4, h * 4), Image.NEAREST)
        layer = layer.filter(ImageFilter.GaussianBlur(2.5))
        layer = layer.crop(box).resize((W, W), Image.BILINEAR)
        frame = canvas0.copy().convert("RGBA")
        frame.alpha_composite(layer)
        d = ImageDraw.Draw(frame)
        d.rectangle((0, 0, W, 112), fill=(*PAPER, 236))
        d.text((32, 22), "Avalauncher · scenariusz lawiny z biblioteki", font=title, fill=INK)
        d.text((32, 66), "AvaFrame com1DFA na terenie GUGiK NMT · Liliowe E i Mały Kościelec NE · płyta 1,5 m",
               font=small, fill=(90, 82, 68))
        d.text((W - 32, 30), f"t = {t:4.0f} s", font=big, fill=(166, 59, 0), anchor="ra")
        # legend
        y = W - 64
        d.rectangle((0, y - 16, W, W), fill=(*PAPER, 236))
        x = 32
        for v, c in RAMP:
            d.rectangle((x, y + 4, x + 46, y + 22), fill=c)
            d.text((x + 23, y + 26), f"{v:g} m", font=font(15, 600), fill=INK, anchor="ma")
            x += 52
        d.text((x + 10, y + 4), "grubość przepływu", font=font(17, 650), fill=INK)
        d.text((W - 32, y + 6), "Śnieg: scenariusz syntetyczny · Teren: GUGiK · Szlaki: OSM",
               font=font(15, 500), fill=(90, 82, 68), anchor="ra")
        frame = frame.convert("RGB")
        frame.save(out / f"frame_{int(t):04d}.png")
        frames.append(frame)
    hold = [frames[-1]] * 6
    seq = frames + hold
    seq[0].save(out.with_suffix(".gif"), save_all=True, append_images=[f.resize((720, 720)) for f in seq[1:]],
                duration=160, loop=0, optimize=True)
    print(f"{len(frames)} frames, t {grids[0][0]:.0f}-{grids[-1][0]:.0f} s -> {out}.gif")


if __name__ == "__main__":
    main(*sys.argv[1:])

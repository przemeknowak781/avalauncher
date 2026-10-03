"""Render the sweep: one MP4 per simulation, a 3x3 parameter matrix per sector and an 8-sector overview.

Runs on the Spark next to the sweep outputs. Needs pillow, numpy and ffmpeg.
Usage: python render_sweep.py <runsDir> <assetsDir> <outDir> [workers]
  runsDir   contains <sector>_<frictModel>/Outputs/com1DFA/...
  assetsDir contains map.png, terrain.json, trails.json, sectors.json, Archivo-var.ttf
"""

import json
import re
import subprocess
import sys
from configparser import ConfigParser
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TRAIL = {"red": (214, 40, 40), "blue": (31, 95, 209), "green": (42, 157, 60), "yellow": (242, 194, 0), "black": (34, 32, 28)}
INK, INK2, PAPER, HAZ = (29, 27, 23), (90, 82, 68), (244, 239, 228), (166, 59, 0)
RAMP = [(0.05, (255, 214, 170)), (0.3, (249, 145, 72)), (0.8, (232, 89, 12)), (1.5, (166, 59, 0)), (3.0, (90, 26, 0))]
FRICT_PL = {"samosATSmall": "tarcie: małe lawiny", "samosATMedium": "tarcie: średnie lawiny", "samosAT": "tarcie: duże lawiny"}
FRICT_ORDER = ["samosATSmall", "samosATMedium", "samosAT"]
FPS_SIM = 1.0  # saved time step [s]

A = {}


def font(size, weight=700, width=100):
    f = ImageFont.truetype(str(A["font"]), size)
    f.set_variation_by_axes([weight, width])  # axes: Weight, Width
    return f


def read_asc(p):
    return np.loadtxt(p.read_text().splitlines()[6:], dtype=np.float32)


def colour(ft):
    v = np.nan_to_num(ft)
    rgba = np.zeros(v.shape + (4,), np.float32)
    for (a, ca), (b, cb) in zip(RAMP, RAMP[1:]):
        m = (v >= a) & (v < b)
        t = ((v - a) / (b - a))[m][:, None]
        rgba[m, :3] = np.array(ca) * (1 - t) + np.array(cb) * t
        rgba[m, 3] = 220
    top = v >= RAMP[-1][0]
    rgba[top, :3], rgba[top, 3] = RAMP[-1][1], 235
    return rgba.astype(np.uint8)


def load_assets(assets):
    assets = Path(assets)
    A["font"] = assets / "Archivo-var.ttf"
    A["terrain"] = json.loads((assets / "terrain.json").read_text(encoding="utf-8"))
    A["trails"] = json.loads((assets / "trails.json").read_text(encoding="utf-8"))
    A["sectors"] = {s["id"]: s for s in json.loads((assets / "sectors.json").read_text(encoding="utf-8"))}
    A["map"] = Image.open(assets / "map.png").convert("RGB")


def sims_in(run_dir):
    """{simName: {"relTh": float, "frict": str, "steps": [(t, path)]}}"""
    out = {}
    cfg_dir = run_dir / "Outputs" / "com1DFA" / "configurationFiles"
    ts_dir = run_dir / "Outputs" / "com1DFA" / "peakFiles" / "timeSteps"
    for p in ts_dir.glob("*_FT_t*.asc"):
        sim, t = re.match(r"(.+)_FT_t([\d.]+)\.asc$", p.name).groups()
        out.setdefault(sim, {"steps": []})["steps"].append((float(t), p))
    for sim, d in out.items():
        cp = ConfigParser()
        cp.read(cfg_dir / f"{sim}.ini")
        d["relTh"] = round(float(cp["GENERAL"]["relTh"]), 2)
        d["frict"] = cp["GENERAL"]["frictModel"]
        d["steps"].sort()
    return out


def crop_box(grids, pad=None, min_side=70):
    """Square crop (in analysis cells) around everything the given grids reached; tight by default."""
    h, w = A["terrain"]["height"], A["terrain"]["width"]
    reach = np.zeros((h, w), bool)
    for g in grids:
        reach |= np.nan_to_num(g) > 0.1
    rows, cols = np.nonzero(reach)
    ext = max(rows.max() - rows.min(), cols.max() - cols.min())
    pad = max(12, int(0.15 * ext)) if pad is None else pad
    side = min(max(ext + 2 * pad, min_side), h)
    cr, cc = (rows.min() + rows.max()) // 2, (cols.min() + cols.max()) // 2
    r0 = int(np.clip(cr - side // 2, 0, h - side))
    c0 = int(np.clip(cc - side // 2, 0, w - side))
    return r0, c0, side


def base_tile(box, size):
    r0, c0, side = box
    k = A["map"].width / A["terrain"]["width"]
    img = A["map"].crop((int(c0 * k), int(r0 * k), int((c0 + side) * k), int((r0 + side) * k))).resize((size, size), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    s = size / side
    lw = max(3, round(size / 180))
    for t in A["trails"]:
        for part in t["paths"]:
            pts = [((c - c0) * s, (r - r0) * s) for c, r in part]
            d.line(pts, fill=(255, 255, 255), width=lw + 3, joint="curve")
            d.line(pts, fill=TRAIL.get(t["color"], TRAIL["red"]), width=lw, joint="curve")
    return img


def flow_layer(grid, box, size):
    r0, c0, side = box
    sub = grid[r0:r0 + side, c0:c0 + side]
    layer = Image.fromarray(colour(sub), "RGBA").resize((size, size), Image.BILINEAR)
    return layer.filter(ImageFilter.GaussianBlur(size / 520))


def label_bar(img, text_l, text_r, size):
    d = ImageDraw.Draw(img, "RGBA")
    hgt = round(size * 0.085)
    d.rectangle((0, 0, size, hgt), fill=(*PAPER, 232))
    d.text((round(size * 0.03), hgt // 2), text_l, font=font(round(hgt * 0.42), 700), fill=INK, anchor="lm")
    d.text((size - round(size * 0.03), hgt // 2), text_r, font=font(round(hgt * 0.5), 800), fill=HAZ, anchor="rm")


def legend_strip(width, height):
    img = Image.new("RGB", (width, height), PAPER)
    d = ImageDraw.Draw(img)
    x, y = 36, height // 2
    d.text((x, y), "Grubość przepływu", font=font(22, 700), fill=INK, anchor="lm")
    x += 230
    for v, c in RAMP:
        d.rectangle((x, y - 11, x + 64, y + 11), fill=c)
        d.text((x + 32, y + 26), f"{v:g} m".replace(".", ","), font=font(16, 600), fill=INK, anchor="mm")
        x += 76
    d.text((width - 36, y), "AvaFrame com1DFA · teren GUGiK NMT · szlaki © OSM · śnieg: scenariusz syntetyczny",
           font=font(17, 500), fill=INK2, anchor="rm")
    return img


def title_strip(width, height, title, sub):
    img = Image.new("RGB", (width, height), PAPER)
    d = ImageDraw.Draw(img)
    d.text((36, height * 0.38), title, font=font(round(height * 0.34), 800, 112), fill=INK, anchor="lm")
    d.text((36, height * 0.76), sub, font=font(round(height * 0.2), 500), fill=INK2, anchor="lm")
    return img


def frames_at(sim, times):
    """Grid per requested time; after the run ends the last state holds."""
    steps = sim["steps"]
    cache = {}
    out = []
    for t in times:
        i = max(0, np.searchsorted([s[0] for s in steps], t, side="right") - 1)
        if i not in cache:
            cache[i] = read_asc(steps[i][1])
        out.append(cache[i])
    return out


def encode(frame_dir, mp4, fps_out=30):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "8", "-i", str(frame_dir / "f_%04d.png"),
                    "-vf", f"framerate=fps={fps_out}:interp_start=0:interp_end=255:scene=100,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-movflags", "+faststart", str(mp4)], check=True)


def render_single(job):
    name, sim, box, out = job
    size = 1080
    fd = out / "frames" / name
    fd.mkdir(parents=True, exist_ok=True)
    base = base_tile(box, size)
    t_end = sim["steps"][-1][0]
    times = list(np.arange(0, t_end + 1, FPS_SIM)) + [t_end] * 10
    sector = A["sectors"][name.split("_")[0]]
    for i, (t, g) in enumerate(zip(times, frames_at(sim, times))):
        f = base.copy().convert("RGBA")
        f.alpha_composite(flow_layer(g, box, size))
        label_bar(f, f"{sector['name']} · płyta {sim['relTh']:.1f} m · {FRICT_PL[sim['frict']]}".replace(".", ","), f"t = {t:.0f} s", size)
        f.convert("RGB").save(fd / f"f_{i:04d}.png")
    encode(fd, out / "sims" / f"{name}.mp4")
    return name


def render_grid(job):
    """job: (name, title, sub, tiles=[(label, sim, box)], cols)"""
    name, title, sub, tiles, cols = job
    tile = 540 if cols >= 3 else 720
    rows = (len(tiles) + cols - 1) // cols
    gap, top, bottom = 10, 120, 70
    W = cols * tile + (cols + 1) * gap
    H = top + rows * tile + (rows + 1) * gap + bottom
    t_end = max(s["steps"][-1][0] for _, s, _ in tiles)
    times = list(np.arange(0, t_end + 1, FPS_SIM)) + [t_end] * 12
    bases = [base_tile(box, tile) for _, _, box in tiles]
    grids = [frames_at(sim, times) for _, sim, _ in tiles]
    head, foot = title_strip(W, top, title, sub), legend_strip(W, bottom)
    fd = Path(job_out) / "frames" / name
    fd.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        canvas = Image.new("RGB", (W, H), (221, 212, 194))
        canvas.paste(head, (0, 0))
        canvas.paste(foot, (0, H - bottom))
        for j, ((label, sim, box), base) in enumerate(zip(tiles, bases)):
            r, c = divmod(j, cols)
            f = base.copy().convert("RGBA")
            f.alpha_composite(flow_layer(grids[j][i], box, tile))
            label_bar(f, label, f"{min(t, sim['steps'][-1][0]):.0f} s", tile)
            canvas.paste(f.convert("RGB"), (gap + c * (tile + gap), top + gap + r * (tile + gap)))
        canvas.save(fd / f"f_{i:04d}.png")
    encode(fd, Path(job_out) / f"{name}.mp4")
    canvas.save(Path(job_out) / f"{name}_last.png")
    return name


job_out = None


def init(assets, out):
    global job_out
    load_assets(assets)
    job_out = out


def main(runs, assets, out, workers=10):
    runs, out = Path(runs), Path(out)
    (out / "sims").mkdir(parents=True, exist_ok=True)
    load_assets(assets)
    by_sector = {}
    for run_dir in sorted(p for p in runs.iterdir() if (p / "Outputs").exists()):
        sector = run_dir.name.split("_")[0]
        for sim in sims_in(run_dir).values():
            by_sector.setdefault(sector, []).append(sim)
    boxes = {}
    for sector, sims in by_sector.items():
        boxes[sector] = crop_box([read_asc(s["steps"][-1][1]) for s in sims] +
                                 [np.nanmax([read_asc(p) for _, p in s["steps"][::4]], axis=0) for s in sims])
    singles, grids = [], []
    for sector, sims in by_sector.items():
        for s in sims:
            own = crop_box([np.nanmax([read_asc(p) for _, p in s["steps"][::3]] + [read_asc(s["steps"][-1][1])], axis=0)])
            singles.append((f"{sector}_{s['frict']}_{s['relTh']:.1f}", s, own, out))
        ordered = sorted(sims, key=lambda s: (FRICT_ORDER.index(s["frict"]), s["relTh"]))
        name = A["sectors"][sector]["name"]
        grids.append((f"macierz_{sector}", f"{name}: jak zmienia się zasięg",
                      "Wiersze: kalibracja tarcia AvaFrame (małe, średnie, duże lawiny). Kolumny: grubość płyty 0,6 / 1,3 / 2,0 m.",
                      [(f"{FRICT_PL[s['frict']].split(': ')[1]} · {s['relTh']:.1f} m".replace(".", ","), s, boxes[sector]) for s in ordered], 3))
    overview = []
    for sector, sims in by_sector.items():
        s = min(sims, key=lambda s: (abs(s["relTh"] - 1.3), FRICT_ORDER.index(s["frict"]) != 1))
        overview.append((A["sectors"][sector]["name"], s, boxes[sector]))
    grids.append(("przeglad", "Biblioteka scenariuszy: 8 stref startowych nad szlakami Hali Gąsienicowej",
                  "Każdy kafel to fizyczna symulacja AvaFrame na terenie GUGiK. Płyta 1,3 m, tarcie dla średnich lawin.",
                  overview, 4))
    with Pool(int(workers), initializer=init, initargs=(assets, out)) as pool:
        for n in pool.imap_unordered(render_grid, grids):
            print("grid", n, flush=True)
        for n in pool.imap_unordered(render_single, singles):
            print("sim", n, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

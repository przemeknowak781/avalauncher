"""Board filmy/satelita/porownanie.png: Sentinel-2 true colour | NDSI | snow mask on our map.

Reads the cache written by fetch_sentinel.py (data/raw/sentinel/<scene>.npz) and web/data/*.
Run: python tools/satellite/board.py
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web" / "data"
CACHE = ROOT / "data" / "raw" / "sentinel"
OUT = ROOT / "filmy" / "satelita" / "porownanie.png"
FONT = ROOT / "web" / "vendor" / "fonts" / "Archivo-var.ttf"
PAPER, PAPER2, INK, INK2 = (244, 239, 228), (235, 228, 212), (29, 27, 23), (90, 82, 68)
HAZ_T = (166, 59, 0)
TRAIL = {"red": (214, 40, 40), "blue": (31, 95, 209), "green": (42, 157, 60), "yellow": (242, 194, 0), "black": (34, 32, 28)}
W, H, P, M = 1920, 1080, 600, 30  # board, panel side, margin
K0_FIX = 0.9993 / 0.9992  # tools/pl1992.py uses k0 = 0.9992; EPSG:2180 has 0.9993


def font(size, weight=700, width=100):
    f = ImageFont.truetype(str(FONT), int(size))
    f.set_variation_by_axes([weight, width])
    return f


def pl_num(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def trails_fixed(trails, z, e0, n0, cell):
    """Trail vertices in (col, row). If trails.json still carries the k0 = 0.9992 shift (~546 m south),
    move them back onto the GUGiK terrain; detected by where the Kasprowy Wierch trail ends."""
    def fix(c, r):
        e = (e0 + c * cell - 500000) * K0_FIX + 500000
        n = (n0 - r * cell + 5300000) * K0_FIX - 5300000
        return (e - e0) / cell, (n0 - n) / cell
    ends = [p[-1] for t in trails if t["name"].endswith("Kasprowy Wierch") for p in t["paths"]]
    shifted = bool(ends) and np.median([z[int(r), int(c)] for c, r in ends]) < 1900
    out = []
    for t in trails:
        paths = [[fix(c, r) if shifted else (c, r) for c, r in p] for p in t["paths"]]
        out.append({"color": t["color"], "paths": paths})
    return out, shifted


def ndsi_rgb(ndsi):
    """Brown below the 0.4 snow threshold, light to deep blue above it."""
    x = np.nan_to_num(ndsi, nan=-0.2)
    lo = np.clip((x + 0.2) / 0.6, 0, 1)[..., None]
    hi = np.clip((x - 0.4) / 0.6, 0, 1)[..., None]
    brown = np.array((112, 88, 58)) * (1 - lo) + np.array((222, 205, 172)) * lo
    blue = np.array((206, 228, 248)) * (1 - hi) + np.array((28, 84, 170)) * hi
    return np.where(x[..., None] > 0.4, blue, brown).astype(np.uint8)


def main():
    meta = json.loads((DATA / "sentinel_snow.json").read_text(encoding="utf-8"))
    t = json.loads((DATA / "terrain.json").read_text(encoding="utf-8"))
    n = t["width"]
    z = np.fromfile(DATA / "terrain_f32.bin", "<f4").reshape(n, n)
    d = np.load(CACHE / f"{meta['scene_id']}.npz")
    b03, b11, scl = d["b03"], d["b11"], d["scl"]
    ndsi = (b03 - b11) / np.maximum(b03 + b11, 1e-4)
    k = P / n

    tc = Image.open(DATA / "sentinel_truecolor.jpg").convert("RGB").resize((P, P), Image.LANCZOS)
    nd = Image.fromarray(ndsi_rgb(ndsi)).resize((P, P), Image.LANCZOS)
    mp = Image.open(DATA / "map.png").convert("RGBA").resize((P, P), Image.LANCZOS)
    ov = Image.open(DATA / "sentinel_snow.png").convert("RGBA").resize((P, P), Image.NEAREST)
    mp.alpha_composite(ov)
    trails, shifted = trails_fixed(json.loads((DATA / "trails.json").read_text(encoding="utf-8")), z, t["e0"], t["n0"], t["cell_m"])
    dm = ImageDraw.Draw(mp)
    for col in (False, True):
        for tr in trails:
            for part in tr["paths"]:
                pts = [(c * k, r * k) for c, r in part]
                if col:
                    dm.line(pts, fill=TRAIL.get(tr["color"], TRAIL["red"]), width=3, joint="curve")
                else:
                    dm.line(pts, fill=(255, 255, 255), width=6, joint="curve")
    mp = mp.convert("RGB")

    img = Image.new("RGB", (W, H), PAPER)
    g = ImageDraw.Draw(img)
    dt = meta["date"].split("-")
    date_pl = f"{int(dt[2])}.{dt[1]}.{dt[0]}"
    ep = meta["episode_cloud_pct_over_area"]
    g.text((M, 26), f"Śnieg z satelity: Sentinel-2, {date_pl}, {meta['acquired_utc'][11:16]} UTC", font=font(46, 760), fill=INK)
    g.text((M, 90), f"Hala Gąsienicowa, siatka 4 × 4 km. Pierwszy bezchmurny przelot {meta['days_after_episode']} dni po epizodzie "
                    f"11–13.01.2025 (+34 cm, zamieć 72 h).", font=font(25, 420), fill=INK2)
    g.text((M, 124), "W dniach epizodu satelita nie widział terenu: chmury nad "
                     + " i ".join(f"{pl_num(v, 0)}% obszaru {int(k_[8:10])}.{k_[5:7]}" for k_, v in sorted(ep.items())) + ".",
           font=font(25, 600), fill=HAZ_T)

    y0 = 176
    xs = [M + i * (P + M) for i in range(3)]
    for x, im in zip(xs, (tc, nd, mp)):
        img.paste(im, (x, y0))
        g.rectangle((x - 1, y0 - 1, x + P, y0 + P), outline=INK2, width=1)

    # Scale bar and north arrow on the map panel.
    bx, by = xs[2] + 18, y0 + P - 24
    g.rectangle((bx - 8, by - 26, bx + 100 * k + 40, by + 12), fill=PAPER)
    g.line((bx, by, bx + 100 * k, by), fill=INK, width=4)
    g.text((bx + 100 * k + 8, by - 11), "1 km", font=font(17, 650), fill=INK)
    ax, ay = xs[2] + P - 30, y0 + 22
    g.polygon([(ax, ay - 14), (ax + 9, ay + 10), (ax, ay + 4), (ax - 9, ay + 10)], fill=INK)
    g.text((ax - 6, ay + 12), "N", font=font(17, 700), fill=INK)

    cy = y0 + P + 16
    g.text((xs[0], cy), "Barwy naturalne", font=font(26, 720), fill=INK)
    g.text((xs[0], cy + 36), "Kanały B04, B03, B02, 10 m. Słońce tylko 19° nad", font=font(18, 420), fill=INK2)
    g.text((xs[0], cy + 60), "horyzontem: stoki północne leżą w cieniu (niebieskie).", font=font(18, 420), fill=INK2)

    g.text((xs[1], cy), "Indeks śniegu NDSI", font=font(26, 720), fill=INK)
    g.text((xs[1], cy + 36), "(B03 − B11) / (B03 + B11). Śnieg odbija zieleń, a pochłania", font=font(18, 420), fill=INK2)
    g.text((xs[1], cy + 60), "podczerwień, więc działa także w cieniu.", font=font(18, 420), fill=INK2)
    # Colour bar -0.2..1.0 with the 0.4 threshold.
    bar = np.linspace(-0.2, 1.0, 480)[None, :].repeat(16, 0)
    img.paste(Image.fromarray(ndsi_rgb(bar)), (xs[1], cy + 94))
    g.rectangle((xs[1], cy + 94, xs[1] + 480, cy + 110), outline=INK2)
    for v in (-0.2, 0.0, 0.4, 1.0):
        px = xs[1] + (v + 0.2) / 1.2 * 480
        g.line((px, cy + 110, px, cy + 116), fill=INK, width=2)
        g.text((px - 12, cy + 118), pl_num(v), font=font(16, 600 if v == 0.4 else 420), fill=INK)
    g.text((xs[1] + (0.6 / 1.2) * 480 + 22, cy + 118), "próg śniegu", font=font(16, 650), fill=INK)

    g.text((xs[2], cy), "Maska śniegu na mapie", font=font(26, 720), fill=INK)
    g.text((xs[2], cy + 36), "Śnieg: NDSI > 0,4 i jasność B03 > 0,1. Chmury z klasyfikacji SCL.", font=font(18, 420), fill=INK2)
    snow_pct, cloud_pct = meta["snow_pct"], meta["cloud_pct_over_area"]
    leg = [((196, 224, 255), f"śnieg: {pl_num(snow_pct)}% obszaru bez chmur"),
           ((205, 216, 184), f"niepotwierdzony: {pl_num(100 - snow_pct)}% (las, głęboki cień)"),
           ((128, 128, 128), f"chmury: {pl_num(cloud_pct)}%")]
    for i, (c, s) in enumerate(leg):
        ly = cy + 66 + i * 26
        g.rectangle((xs[2], ly, xs[2] + 18, ly + 18), fill=c, outline=INK2)
        g.text((xs[2] + 28, ly - 1), s, font=font(18, 520), fill=INK)

    g.text((M, H - 104), "Satelita pokazuje, gdzie leży śnieg, ale nie ile go jest i jak jest ułożony. "
                         "Grubość płyty nad szlakami musi zmierzyć dron.", font=font(27, 720), fill=INK)
    credit = ("Zawiera zmodyfikowane dane Copernicus Sentinel (2025) · Sentinel-2 L2A przez Element84 Earth Search (AWS Open Data) · "
              f"scena {meta['scene_id']} · Teren: GUGiK NMT · Szlaki: © OpenStreetMap")
    g.text((M, H - 46), credit, font=font(16, 420), fill=INK2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(OUT, "trails shifted back onto terrain:" if shifted else "trails used as is", shifted)


if __name__ == "__main__":
    main()

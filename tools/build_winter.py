"""Winter texture for 3D renders: GUGiK summer orthophoto + synthetic snow cover.

Snow: white above ~1400 m, shaded by relief, thinning on steep rock (> ~50 deg, snow does not hold),
light dusting on forest below, frozen lakes snow-covered. Stylised, labelled "śnieg: scenariusz syntetyczny".
Writes data/avaframe/assets/winter.png (2000 px, 5 px per 10 m cell).
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import build_terrain as bt

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
OUT = ROOT / "data" / "avaframe" / "assets" / "winter.png"
SIZE = 2000


def main() -> None:
    t = json.loads((WEB / "terrain.json").read_text(encoding="utf-8"))
    z10 = np.fromfile(WEB / "terrain_f32.bin", dtype="<f4").reshape(t["height"], t["width"])
    f = SIZE / t["width"]
    nod10 = z10 <= z10.min() + 0.01  # no NMT data (Slovak side), filled flat by build_terrain
    z = ndimage.zoom(ndimage.gaussian_filter(z10, 0.6), f, order=1)
    nod = ndimage.zoom(nod10.astype(np.float32), f, order=1) > 0.5
    cell = t["cell_m"] / f
    gy, gx = np.gradient(z, cell)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    shade = sum(w * bt.hillshade(z, cell, az, 38) for az, w in ((315, 0.6), (270, 0.2), (0, 0.2)))

    ortho = np.asarray(Image.open(bt.RAW / "ortho_gasienicowa.jpg").convert("RGB").resize((SIZE, SIZE), Image.LANCZOS), np.float32)
    lum = ortho.mean(axis=2, keepdims=True) / 255

    # snow amount 0..1
    alt = np.clip((z - 1380) / 220, 0, 1)
    hold = np.clip((54 - slope) / 14, 0, 1)
    s = np.maximum(alt * hold, 0.55 * np.clip((z - 1000) / 300, 0, 1) * (0.6 + 0.4 * hold))
    flat = (slope < 1.2) & (z > 1550)
    lab, n = ndimage.label(ndimage.binary_opening(flat, iterations=4))
    sizes = ndimage.sum(np.ones_like(z), lab, range(1, n + 1))
    lakes = np.isin(lab, [i + 1 for i, v in enumerate(sizes) if v > 4000])
    s = np.where(lakes | nod, 1.0, s)
    s = ndimage.gaussian_filter(s, 1.2)[..., None]

    # snow colour: bright where lit, cool blue in shadow, a little texture from the photo
    k = np.clip((shade - 0.35) / 0.55, 0, 1)[..., None] ** 1.3
    lit, shadow = np.array([246, 248, 252], np.float32), np.array([168, 186, 212], np.float32)
    snow = shadow + (lit - shadow) * (0.05 + 0.95 * k)
    snow *= 0.9 + 0.1 * lum
    snow[lakes] = snow[lakes] * 0.96 + np.array([4, 8, 14])

    rgb = ortho * (1 - s) + snow * s
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.UnsharpMask(1.2, 60, 2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print("winter.png", img.size, f"snow {float(s.mean()):.0%}, lakes px {int(lakes.sum())}")


if __name__ == "__main__":
    main()

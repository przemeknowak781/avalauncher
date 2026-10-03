"""Cartographic base map in the style of a Tatra tourist map: hypsometric tint,
soft hillshade, 50 m contours (250 m index), lakes. Writes web/data/map.png (1600 px)."""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import build_terrain as bt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "data"
SIZE = 1600


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def main() -> None:
    z5 = bt.read_tiff_f32(bt.RAW / "nmt_gasienicowa_5m.tif")
    nodata = z5 <= 1.0
    z5 = np.where(nodata, np.nan, z5)
    fill = np.where(nodata, np.nanmean(z5), z5)
    f = SIZE / z5.shape[0]
    z = ndimage.zoom(ndimage.gaussian_filter(fill, 0.8), f, order=1)
    nod = ndimage.zoom(nodata.astype(np.uint8), f, order=0).astype(bool)
    cell = 5.0 / f

    # Soft multidirectional hillshade.
    shade = sum(w * bt.hillshade(z, cell, az, 40) for az, w in ((315, 0.5), (270, 0.25), (360, 0.25)))
    shade = ndimage.gaussian_filter(shade, 0.6)

    # Hypsometric tint: forest, dwarf pine, alpine meadow, rock.
    stops = [(1300, (205, 216, 184)), (1550, (219, 226, 196)), (1800, (236, 232, 210)),
             (2050, (240, 234, 220)), (2300, (233, 229, 224))]
    rgb = np.zeros(z.shape + (3,))
    for (z0, c0), (z1, c1) in zip(stops, stops[1:]):
        t = np.clip((z - z0) / (z1 - z0), 0, 1)
        m = (z >= z0) & (z < z1) if z1 != stops[-1][0] else (z >= z0)
        rgb[m] = lerp(np.array(c0, float), np.array(c1, float), t)[m]
    rgb[z < stops[0][0]] = stops[0][1]

    shadow = np.array((92, 84, 74), float)
    k = np.clip((shade - 0.35) / 0.65, 0, 1)
    rgb = lerp(shadow, np.zeros(3), np.zeros(z.shape)) * 0 + rgb * (0.5 + 0.5 * k[..., None]) + shadow * (0.5 * (1 - k[..., None])) * 0.6

    # Lakes: large, flat, high areas.
    gy, gx = np.gradient(z, cell)
    flat = np.degrees(np.arctan(np.hypot(gx, gy))) < 1.2
    lab, n = ndimage.label(ndimage.binary_opening(flat, iterations=3))
    sizes = ndimage.sum(np.ones_like(z), lab, range(1, n + 1))
    lakes = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 2500]) & (z > 1550)
    rgb[lakes] = (166, 203, 222)

    # Contours.
    for step, alpha, width in ((50, 0.32, 0), (250, 0.62, 1)):
        q = np.floor(z / step)
        line = (q != np.roll(q, 1, 0)) | (q != np.roll(q, 1, 1))
        if width:
            line = ndimage.binary_dilation(line, iterations=1) & ~ndimage.binary_dilation(line, iterations=0)
            line = (q != np.roll(q, 1, 0)) | (q != np.roll(q, 1, 1)) | (q != np.roll(q, -1, 0))
        line &= ~lakes
        rgb[line] = rgb[line] * (1 - alpha) + np.array((150, 108, 66)) * alpha

    paper = np.array((244, 239, 228), float)
    rgb[nod] = paper
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").save(OUT / "map.png", optimize=True)
    print("map.png", rgb.shape, "lakes px", int(lakes.sum()))


if __name__ == "__main__":
    main()

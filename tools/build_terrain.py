"""Build terrain assets for the demo from GUGiK NMT and OSM hiking relations.

Inputs (data/raw/, fetched by tools/fetch_raw.sh):
  nmt_gasienicowa_5m.tif  GUGiK NMT WCS, 800x800 at 5 m, EPSG:2180, float32
  osm_hiking.json         Overpass relations with full member geometry
Outputs (web/data/): terrain.json, terrain_f32.bin, hillshade.png, sectors.json,
  sectors_u8.bin (row-major sector index per 10 m cell), trails.json
"""

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from pl1992 import to_pl1992  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "web" / "data"

# The WCS request box (see docs/09_plan_budowy.md, section 2).
E_MIN, E_MAX, N_MIN, N_MAX = 570500, 574500, 149500, 153500
CELL = 10  # analysis grid, metres

# Approximate positions of named places, used only to name sectors.
PLACES = [
    ("Kasprowy Wierch", 49.2319, 19.9817),
    ("Beskid", 49.2286, 19.9933),
    ("Liliowe", 49.2252, 19.9990),
    ("Świnica", 49.2193, 20.0090),
    ("Zawrat", 49.2195, 20.0164),
    ("Kościelec", 49.2253, 20.0144),
    ("Mały Kościelec", 49.2337, 20.0083),
    ("Czarny Staw Gąsienicowy", 49.2297, 20.0187),
    ("Kopa Magury", 49.2445, 19.9921),
    ("Sucha Dolina", 49.2380, 19.9890),
]
ASPECTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def read_tiff_f32(path: Path) -> np.ndarray:
    b = path.read_bytes()
    assert b[:4] == b"II*\x00", "expected little-endian TIFF"
    off = struct.unpack("<I", b[4:8])[0]
    n = struct.unpack("<H", b[off:off + 2])[0]
    tags = {}
    for i in range(n):
        tag, typ, cnt, val = struct.unpack("<HHII", b[off + 2 + i * 12: off + 14 + i * 12])
        tags[tag] = (typ, cnt, val)
    w, h = tags[256][2] & 0xFFFF, tags[257][2] & 0xFFFF
    assert tags[259][2] & 0xFFFF == 1, "compressed TIFF not supported"
    typ, cnt, val = tags[273]
    offsets = [val] if cnt == 1 else list(struct.unpack(f"<{cnt}I", b[val:val + 4 * cnt]))
    typ, cnt, val = tags[279]
    if cnt == 1:
        counts = [val & 0xFFFF if typ == 3 else val]
    else:
        fmt = "H" if typ == 3 else "I"
        counts = list(struct.unpack(f"<{cnt}{fmt}", b[val:val + (2 if typ == 3 else 4) * cnt]))
    data = b"".join(b[o:o + c] for o, c in zip(offsets, counts))
    return np.frombuffer(data, dtype="<f4", count=w * h).reshape(h, w).copy()


def hillshade(z: np.ndarray, cell: float, az=315.0, alt=45.0) -> np.ndarray:
    gy, gx = np.gradient(z, cell)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, e = math.radians(az), math.radians(alt)
    shade = np.sin(e) * np.cos(slope) + np.cos(e) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(shade, 0, 1)


def to_cell(lat: float, lon: float) -> list[float]:
    e, n = to_pl1992(lat, lon)
    return [round((e - E_MIN) / CELL, 1), round((N_MAX - n) / CELL, 1)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    z5 = read_tiff_f32(RAW / "nmt_gasienicowa_5m.tif")
    nodata5 = z5 <= 1.0  # zeros lie outside Poland (Slovakia)
    z5f = np.where(nodata5, np.nan, z5)

    # Hillshade at full 5 m resolution, nodata shown dark.
    fill = np.where(nodata5, np.nanmean(z5f), z5)
    hs = hillshade(fill, 5.0)
    rgb = (40 + 200 * hs).astype(np.uint8)
    img = np.dstack([rgb, rgb, rgb, np.where(nodata5, 0, 255).astype(np.uint8)])
    Image.fromarray(img, "RGBA").save(OUT / "hillshade.png", optimize=True)

    # Analysis grid at 10 m.
    h5, w5 = z5.shape
    z = np.nanmean(z5f.reshape(h5 // 2, 2, w5 // 2, 2), axis=(1, 3))
    nodata = np.isnan(z)
    zf = np.where(nodata, np.nanmin(z), z).astype(np.float32)
    zf.tofile(OUT / "terrain_f32.bin")
    height, width = zf.shape

    gy, gx = np.gradient(zf, CELL)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    aspect_deg = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360  # 0 = north, clockwise

    # Potential release areas: steep, high, inside Poland.
    pra = (slope >= 28) & (slope <= 55) & (zf >= 1600) & ~nodata
    # Split release areas by aspect class so one ridge does not become one sector.
    aspect_class = (((aspect_deg + 22.5) % 360) // 45).astype(int)
    labels = np.zeros(zf.shape, dtype=np.int32)
    count = 0
    for k in range(8):
        part = ndimage.binary_opening(pra & (aspect_class == k), iterations=1)
        lab_k, n_k = ndimage.label(part)
        labels[lab_k > 0] = lab_k[lab_k > 0] + count
        count += n_k
    places = [(name, to_cell(lat, lon)) for name, lat, lon in PLACES]
    sectors = []
    for lab in range(1, count + 1):
        rows, cols = np.nonzero(labels == lab)
        if len(rows) < 150:  # < 1.5 ha
            continue
        mean_aspect = math.degrees(math.atan2(
            np.sin(np.radians(aspect_deg[rows, cols])).mean(),
            np.cos(np.radians(aspect_deg[rows, cols])).mean())) % 360
        asp = ASPECTS[int(((mean_aspect + 22.5) % 360) // 45)]
        elev = zf[rows, cols]
        lo, hi = int(elev.min() // 50 * 50), int(math.ceil(elev.max() / 50) * 50)
        c, r = float(cols.mean()), float(rows.mean())
        place = min(places, key=lambda p: (p[1][0] - c) ** 2 + (p[1][1] - r) ** 2)[0]
        mask = (labels == lab).astype(np.uint8)
        sectors.append({
            "label": lab,
            "name": f"{place} {asp}",
            "aspect": asp,
            "band": f"{lo}–{hi} m",
            "centroid": [round(c, 1), round(r, 1)],
            "area_ha": round(len(rows) * CELL * CELL / 10000, 1),
            "top_cell": [int(cols[elev.argmax()]), int(rows[elev.argmax()])],
            "cells": len(rows),
            "polygon": outline(mask),
        })
    sectors.sort(key=lambda s: -s["area_ha"])
    index = np.zeros(zf.shape, dtype=np.uint8)
    for i, s in enumerate(sectors, 1):
        s["id"] = f"S{i:02d}"
        s["index"] = i
        index[labels == s.pop("label")] = i
    index.tofile(OUT / "sectors_u8.bin")  # 0 = none, i = sectors[i-1]

    trails = build_trails(width, height)

    (OUT / "terrain.json").write_text(json.dumps({
        "crs": "EPSG:2180", "e0": E_MIN, "n0": N_MAX, "cell_m": CELL,
        "width": width, "height": height,
        "elevation": "terrain_f32.bin", "hillshade": "hillshade.png",
        "hillshade_cell_m": 5, "z_min": float(np.nanmin(z)), "z_max": float(np.nanmax(z)),
        "attribution": "Teren: GUGiK NMT",
        "places": [{"name": n, "cell": c} for n, c in places],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "sectors.json").write_text(json.dumps(sectors, ensure_ascii=False), encoding="utf-8")
    (OUT / "trails.json").write_text(json.dumps(trails, ensure_ascii=False), encoding="utf-8")
    print(f"grid {width}x{height}, z {np.nanmin(z):.0f}-{np.nanmax(z):.0f} m, "
          f"{len(sectors)} sectors, {len(trails)} trails")


def outline(mask: np.ndarray) -> list[list[int]]:
    """Coarse polygon of a blob: convex-ish ring from boundary cells ordered by angle."""
    edge = mask & ~ndimage.binary_erosion(mask)
    rows, cols = np.nonzero(edge)
    cy, cx = rows.mean(), cols.mean()
    order = np.argsort(np.arctan2(rows - cy, cols - cx))
    pts = [[int(cols[i]), int(rows[i])] for i in order]
    step = max(1, len(pts) // 60)
    return pts[::step]


COLOR_PL = {"red": "czerwony", "blue": "niebieski", "green": "zielony", "yellow": "żółty", "black": "czarny"}
COLORS = {"red": "red", "blue": "blue", "green": "green", "yellow": "yellow", "black": "black"}


def build_trails(width: int, height: int) -> list[dict]:
    path = RAW / "osm_hiking.json"
    if not path.exists():
        return []
    elements = json.loads(path.read_text(encoding="utf-8"))["elements"]
    ways = {e["id"]: e for e in elements if e["type"] == "way" and "geometry" in e}
    trails = []
    for rel in (e for e in elements if e["type"] == "relation"):
        tags = rel.get("tags", {})
        color = COLORS.get(tags.get("osmc:symbol", "").split(":")[0], "red")
        tid = f"T{len(trails) + 1:02d}"
        paths, segments = [], []
        for m in rel.get("members", []):
            way = ways.get(m.get("ref")) if m.get("type") == "way" else None
            if not way:
                continue
            pts = [to_cell(g["lat"], g["lon"]) for g in way["geometry"]]
            pts = [p for p in pts if 0 <= p[0] < width and 0 <= p[1] < height]
            if len(pts) < 2:
                continue
            part = len(paths)
            paths.append(pts)
            start, acc = 0, 0.0
            for i in range(1, len(pts)):
                acc += _dist(pts[i - 1], pts[i]) * CELL
                if acc >= 300 or i == len(pts) - 1:
                    segments.append({"id": f"{tid}-{len(segments) + 1}", "part": part,
                                     "from": start, "to": i})
                    start, acc = i, 0.0
        if not paths:
            continue
        name = tags.get("name") or ""
        if not name or name.isdigit():
            name = f"szlak {COLOR_PL[color]}"
        trails.append({"id": tid, "name": name,
                       "color": color, "paths": paths, "segments": segments})
    return trails


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


if __name__ == "__main__":
    main()

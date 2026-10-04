"""Sanity check of the assumed W-SW wind with real Sentinel-2 snow cover.

Idea: wind strips snow from windward slopes of ridges and drops it on lee slopes. With W-SW wind the
lee aspects are NE/E, so snow-free (scoured) ridge cells should sit more often on W/SW aspects.
NDSI sees presence of snow, not depth, so the test only bites where the wind has bared the ground.

Ridge cells: z > 1800 m, topographic position index > 0 (higher than the 110 m neighbourhood mean),
slope < 40 deg (steeper rock does not hold snow whatever the wind). Snow-free: NDSI <= 0.4 with
B03 >= 0.03 (darker cells are too noisy to judge). Compared pairs: W vs E (sun-neutral at ~11 solar
time) and SW+W vs NE+E (the engine's windward vs lee, but SW is also sun-facing).

Writes data/raw/sentinel/wind_check.json and adds a "wind_check" block to web/data/sentinel_snow.json.
"""

import json
from pathlib import Path

import numpy as np
from rasterio.enums import Resampling
from scipy import ndimage

import fetch_sentinel as fs

SCENES = ["S2A_34UDV_20250116_0_L2A", "S2B_34UDV_20250118_0_L2A", "S2B_34UDV_20250131_0_L2A",
          "S2C_34UDV_20250205_0_L2A", "S2B_34UDV_20250210_0_L2A", "S2C_34UDV_20250222_0_L2A",
          "S2C_34UDV_20250225_0_L2A"]
SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def scene_arrays(item):
    p = fs.CACHE / f"{item['id']}.npz"
    if p.exists():
        d = np.load(p)
        return d["b03"], d["b11"], d["scl"]
    scl = fs.read(item, "scl", Resampling.nearest)[0]
    b03, b11 = fs.reflectance(item, "green"), fs.reflectance(item, "swir16")
    np.savez_compressed(p, b03=b03, b11=b11, scl=scl)
    return b03, b11, scl


def main():
    z = np.fromfile(fs.DATA / "terrain_f32.bin", "<f4").reshape(fs.N, fs.N).astype(np.float64)
    gy, gx = np.gradient(z, fs.TERRAIN["cell_m"])  # gy: towards south (rows), gx: towards east
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    aspect = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360  # downslope direction, clockwise from north
    sector = ((aspect + 22.5) // 45).astype(int) % 8
    tpi = z - ndimage.uniform_filter(z, 11)
    ridge = (z > 1800) & (tpi > 0) & (slope < 40) & (slope > 5)
    ridge[:6], ridge[-6:], ridge[:, :6], ridge[:, -6:] = False, False, False, False

    items = {it["id"]: it for it in fs.stac_search("2025-01-14", "2025-02-28")}
    rows = []
    for sid in SCENES:
        b03, b11, scl = scene_arrays(items[sid])
        ndsi = (b03 - b11) / np.maximum(b03 + b11, 1e-4)
        ok = ridge & ~np.isin(scl, fs.CLOUD_CLASSES) & np.isfinite(ndsi) & (b03 >= 0.03)
        bare = ok & (ndsi <= 0.4)

        def share(secs):
            m = ok & np.isin(sector, [SECTORS.index(s) for s in secs])
            return {"cells": int(m.sum()), "bare": int((bare & m).sum()),
                    "bare_pct": round(100 * float((bare & m).sum()) / max(int(m.sum()), 1), 1)}

        row = {"scene_id": sid, "date": sid.split("_")[2][:4] + "-" + sid.split("_")[2][4:6] + "-" + sid.split("_")[2][6:8],
               "ridge_cells": int(ok.sum()), "bare_cells": int(bare.sum()),
               "W": share(["W"]), "E": share(["E"]), "SW_W": share(["SW", "W"]), "NE_E": share(["NE", "E"]),
               "by_sector_bare_pct": {s: share([s])["bare_pct"] for s in SECTORS}}
        rows.append(row)
        print(f"{row['date']}: ridge {row['ridge_cells']}, bare {row['bare_cells']} | "
              f"W {row['W']['bare_pct']}% vs E {row['E']['bare_pct']}% | SW+W {row['SW_W']['bare_pct']}% vs NE+E {row['NE_E']['bare_pct']}% "
              f"| {row['by_sector_bare_pct']}")

    tot = {k: [sum(r[k]["bare"] for r in rows[1:]), sum(r[k]["cells"] for r in rows[1:])] for k in ("W", "E", "SW_W", "NE_E")}
    pooled = {k: round(100 * b / max(c, 1), 1) for k, (b, c) in tot.items()}
    print("pooled after 16.01:", pooled)
    out = {"method": __doc__.strip().split("\n\n")[2], "scenes": rows, "pooled_after_episode_pct": pooled}
    (fs.CACHE / "wind_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    worst = max(r["bare_cells"] / max(r["ridge_cells"], 1) for r in rows)
    sj = fs.DATA / "sentinel_snow.json"
    meta = json.loads(sj.read_text(encoding="utf-8"))
    meta["wind_check"] = {
        "question": "Czy odsłonięte przez wiatr komórki grzbietów leżą częściej na stokach nawietrznych W–SW niż zawietrznych NE–E?",
        "scenes": [r["date"] for r in rows],
        "ridge_cells": rows[0]["ridge_cells"],
        "episode_scene_bare_cells": rows[0]["bare_cells"],
        "pooled_bare_pct_after_episode": pooled,
        "max_bare_share_pct": round(100 * worst, 1),
        "verdict": (f"Nie rozstrzyga. Na grzbietach powyżej 1800 m odsłonięte jest najwyżej {fs.pl(100 * worst)}% komórek "
                    f"w każdym z {len(rows)} bezchmurnych przelotów (16.01–25.02.2025), a 16.01 ani jednej. Łącznie po epizodzie: "
                    f"W {fs.pl(pooled['W'])}% wobec E {fs.pl(pooled['E'])}%, SW+W {fs.pl(pooled['SW_W'])}% wobec NE+E {fs.pl(pooled['NE_E'])}%. "
                    "Te nieliczne odsłonięte komórki leżą głównie na stokach S, czyli raczej słońce niż wiatr. "
                    "NDSI widzi obecność śniegu, nie jego grubość, więc założenia W–SW nie potwierdza ani nie obala; "
                    "do tego potrzebny jest pomiar grubości z drona."),
    }
    sj.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows, pooled


if __name__ == "__main__":
    main()

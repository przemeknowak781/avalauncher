"""Build an AvaFrame avalanche directory from our Tatra terrain and release sectors.

Writes data/avaframe/<name>/Inputs/{DEM.asc, REL/rel.shp} in EPSG:2180.
Usage: python tools/avaframe/prepare.py S31 S60
"""

import json
import sys
from pathlib import Path

import numpy as np
import shapefile
from shapely.geometry import box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "data"
PRJ_2180 = ('PROJCS["ETRF2000-PL / CS92",GEOGCS["ETRF2000-PL",DATUM["ETRF2000_Poland",SPHEROID["GRS 1980",'
            '6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
            'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",19],'
            'PARAMETER["scale_factor",0.9993],PARAMETER["false_easting",500000],PARAMETER["false_northing",-5300000],'
            'UNIT["metre",1]]')


def main(sector_ids: list[str]) -> Path:
    t = json.loads((WEB / "terrain.json").read_text(encoding="utf-8"))
    sectors = {s["id"]: s for s in json.loads((WEB / "sectors.json").read_text(encoding="utf-8"))}
    w, h, cell, e0, n0 = t["width"], t["height"], t["cell_m"], t["e0"], t["n0"]
    z = np.fromfile(WEB / "terrain_f32.bin", dtype="<f4").reshape(h, w)
    idx = np.fromfile(WEB / "sectors_u8.bin", dtype=np.uint8).reshape(h, w)

    ava = ROOT / "data" / "avaframe" / ("gasienicowa_" + "_".join(sector_ids))
    (ava / "Inputs" / "REL").mkdir(parents=True, exist_ok=True)

    header = (f"ncols {w}\nnrows {h}\nxllcorner {e0}\nyllcorner {n0 - h * cell}\n"
              f"cellsize {cell}\nNODATA_value -9999\n")
    with open(ava / "Inputs" / "DEM.asc", "w", encoding="ascii") as f:
        f.write(header)
        np.savetxt(f, z, fmt="%.2f")
    (ava / "Inputs" / "DEM.prj").write_text(PRJ_2180)

    rel = shapefile.Writer(str(ava / "Inputs" / "REL" / "rel"), shapeType=shapefile.POLYGON)
    rel.field("name", "C", size=40)
    rel.field("thickness", "N", decimal=2)
    for sid in sector_ids:
        s = sectors[sid]
        rows, cols = np.nonzero(idx == s["index"])
        poly = unary_union([box(e0 + c * cell, n0 - (r + 1) * cell, e0 + (c + 1) * cell, n0 - r * cell)
                            for r, c in zip(rows, cols)]).buffer(0)
        poly = max(getattr(poly, "geoms", [poly]), key=lambda p: p.area)
        ring = list(poly.exterior.coords)
        if not shapefile.signed_area(ring) < 0:  # pyshp wants clockwise outer rings
            ring.reverse()
        rel.poly([ring])
        rel.record(sid, 1.0)
        print(f"{sid} {s['name']}: {poly.area / 10000:.1f} ha")
    rel.close()
    (ava / "Inputs" / "REL" / "rel.prj").write_text(PRJ_2180)
    print("avalanche dir:", ava)
    return ava


if __name__ == "__main__":
    main(sys.argv[1:] or ["S31", "S60"])

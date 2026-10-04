"""Filisur 2 forest for the "las_porywanie" runs: the dataset forest polygons dissolved into disjoint single parts.

Why: the 11 dataset polygons (avaFiisur2_forest_area.gpkg, dense/open) do not overlap by area but share edges
(dense next to open). AvaFrame 2.1 rasterises every resistance feature on its own and rejects a shapefile whose
features claim the same cell ("Features [...] are overlapping - this is not allowed"). The default resistance model
uses one cResH for every polygon and ignores the density class, so the union is the same forest for com1DFA.
Same total area, no holes (AvaFrame also rejects multi-part features). Geometry only, no new data.

Usage (Spark): python forest_las.py <avaFilisur2 root>   -> <root>/forest_las/forest.{shp,shx,dbf,prj,cpg}
"""

import shutil
import sys
from pathlib import Path

import shapefile
from shapely.geometry import Polygon, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def main(root: str) -> None:
    rp = Path(root).expanduser()
    src = rp / "forest" / "forest.shp"
    geoms = [shape(s.__geo_interface__) for s in shapefile.Reader(str(src)).shapes()]
    u = unary_union(geoms)
    parts = list(u.geoms) if u.geom_type == "MultiPolygon" else [u]
    assert all(len(p.interiors) == 0 for p in parts), "dissolved forest has holes"
    assert abs(u.area - sum(g.area for g in geoms)) < 1.0, "dataset polygons overlap by area"
    out = rp / "forest_las"
    out.mkdir(exist_ok=True)
    w = shapefile.Writer(str(out / "forest"), shapeType=shapefile.POLYGON)
    w.field("Id", "N", 10, 0)
    w.field("name", "C", 80, 0)
    for i, p in enumerate(parts):
        p = orient(Polygon(p.exterior), sign=-1.0)  # pyshp: exterior clockwise
        w.poly([[list(c[:2]) for c in p.exterior.coords]])
        w.record(i + 1, f"forest_union_{i + 1}")
    w.close()
    shutil.copy(rp / "forest" / "forest.prj", out / "forest.prj")
    (out / "forest.cpg").write_text("UTF-8")
    print(f"{len(geoms)} dataset polygons -> {len(parts)} disjoint parts, area {u.area:.1f} m2 "
          f"(dataset {sum(g.area for g in geoms):.1f} m2)")


if __name__ == "__main__":
    main(sys.argv[1])

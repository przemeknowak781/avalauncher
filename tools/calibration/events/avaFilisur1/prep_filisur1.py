"""Build an AvaFrame com1DFA project for the observed Filisur avalanche (23.02.2012, event avaFilisur1).

Inputs:
  - event data: OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552, CC-BY-4.0), folder avaFilisur1
                (release, deposition and forest outlines, EPSG:2056; Feistl et al. 2014, data SLF Davos)
  - terrain:    swisstopo swissALTI3D 2 m tiles (vintage 2019) from the public STAC API
                data.geo.admin.ch, mosaicked and averaged to a 5 m grid snapped to multiples of 5 m.

Usage (laptop): python prep_filisur1.py <avaFramedataDir/avaFilisur1> <outRoot>
Creates, in the same layout as the Popeletzbach project (so tools/run_calib.py works unchanged):
  <outRoot>/base/Inputs/{DEM.asc,DEM.prj,REL/rel.*}   com1DFA avalanche dir
  <outRoot>/src/{release,deposition}.*                 observed outlines (scoring)
  <outRoot>/forest/forest.*                            forest polygons (optional res run)
  <outRoot>/dem.tif, <outRoot>/obs_deposition.tif      5 m DEM and observed deposit mask on the same grid
  <outRoot>/raw/{tiles/*.tif,dem_native.tif,stac_items.json}
"""

import json
import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import shapefile
from pyproj import CRS, Transformer
from pyproj.enums import WktVersion
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import reproject
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

STAC = "https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissalti3d/items"
YEAR = "2019"
CELL = 5.0
# crop in EPSG:2056: event bbox 2773971-2774110 x 1169721-1169971, ~500 m margin, more downslope (S)
X0, X1, Y0, Y1 = 2773450.0, 2774650.0, 1169000.0, 1170450.0


def write_shp(path: Path, geom, name: str, wkt: str, fields=None, records=None) -> None:
    """pyshp polygon writer (exterior rings clockwise, holes counter-clockwise), Popeletzbach schema."""
    geoms = geom if isinstance(geom, list) else [geom]
    w = shapefile.Writer(str(path), shapeType=shapefile.POLYGON)
    fields = fields or [("Id", "N", 10, 0), ("thickness", "N", 11, 3), ("Name", "C", 250, 0)]
    for f in fields:
        w.field(*f)
    for i, g in enumerate(geoms):
        polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
        parts = []
        for p in polys:
            p = orient(Polygon(p), sign=-1.0)
            parts.append([list(c[:2]) for c in p.exterior.coords])
            parts += [[list(c[:2]) for c in r.coords] for r in p.interiors]
        w.poly(parts)
        w.record(*(records[i] if records else [i + 1, None, f"{name}_{i + 1}"]))
    w.close()
    path.with_suffix(".prj").write_text(wkt)
    path.with_suffix(".cpg").write_text("UTF-8")


def stac_tiles() -> list[dict]:
    with urllib.request.urlopen(f"{STAC}?bbox=9.698,46.647,9.728,46.667&limit=100", timeout=60) as r:
        feats = json.load(r)["features"]
    out = []
    for f in feats:
        if f"_{YEAR}_" not in f["id"]:
            continue
        for k, a in f["assets"].items():
            if k.endswith(".tif") and float(a.get("eo:gsd", 0)) == 2.0:
                tx, ty = (int(v) * 1000 for v in f["id"].split("_")[-1].split("-"))
                if tx < X1 and tx + 1000 > X0 and ty < Y1 and ty + 1000 > Y0:
                    out.append({"id": f["id"], "asset": k, "href": a["href"]})
    return out


def main(src: str, out: str) -> None:
    src_p, out_p = Path(src), Path(out)
    inputs = out_p / "base" / "Inputs"
    for d in (inputs / "REL", out_p / "src", out_p / "forest", out_p / "raw" / "tiles"):
        d.mkdir(parents=True, exist_ok=True)
    wkt = CRS.from_epsg(2056).to_wkt(WktVersion.WKT1_ESRI)

    tiles = stac_tiles()
    assert len(tiles) == 4, tiles
    (out_p / "raw" / "stac_items.json").write_text(json.dumps(tiles, indent=1))
    paths = []
    for t in tiles:
        p = out_p / "raw" / "tiles" / t["asset"]
        if not p.exists():
            urllib.request.urlretrieve(t["href"], p)
        paths.append(p)

    srcs = [rasterio.open(p) for p in paths]
    mosaic, mtr = merge(srcs)
    prof = srcs[0].profile | {"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": mtr,
                              "driver": "GTiff", "compress": "deflate"}
    nodata = srcs[0].nodata
    for s in srcs:
        s.close()
    with rasterio.open(out_p / "raw" / "dem_native.tif", "w", **prof) as d:
        d.write(mosaic)

    nx, ny = int((X1 - X0) / CELL), int((Y1 - Y0) / CELL)
    tr = from_origin(X0, Y1, CELL, CELL)
    dem = np.full((ny, nx), -9999.0, dtype="float32")
    reproject(mosaic[0], dem, src_transform=mtr, src_crs="EPSG:2056", src_nodata=nodata,
              dst_transform=tr, dst_crs="EPSG:2056", dst_nodata=-9999.0, resampling=Resampling.average)
    assert np.isfinite(dem).all() and dem.min() > 0, "DEM has holes"
    with rasterio.open(out_p / "dem.tif", "w", driver="GTiff", height=ny, width=nx, count=1,
                       dtype="float32", crs="EPSG:2056", transform=tr, nodata=-9999.0) as d:
        d.write(dem, 1)
    # AAIGrid with corner registration
    with open(inputs / "DEM.asc", "w") as f:
        f.write(f"ncols {nx}\nnrows {ny}\nxllcorner {X0:.3f}\nyllcorner {Y0:.3f}\n")
        f.write(f"cellsize {CELL:.3f}\nNODATA_value -9999\n")
        np.savetxt(f, dem, fmt="%.2f")
    (inputs / "DEM.prj").write_text(wkt)

    rel = gpd.read_file(src_p / "avaFilisur1_release_area.gpkg").to_crs(2056)
    dep = gpd.read_file(src_p / "avaFilisur1_deposition_area.gpkg").to_crs(2056)
    forest = gpd.read_file(src_p / "avaFilisur1_forest_area.gpkg").to_crs(2056)
    # release thickness is not documented (column is NaN) -> thickness left empty, set via relTh
    write_shp(inputs / "REL" / "rel.shp", list(rel.geometry), "avaFilisur1_release", wkt)
    write_shp(out_p / "src" / "release.shp", list(rel.geometry), "avaFilisur1_release", wkt)
    write_shp(out_p / "src" / "deposition.shp", list(dep.geometry), "avaFilisur1_deposition", wkt)
    write_shp(out_p / "forest" / "forest.shp", list(forest.geometry), "forest", wkt,
              fields=[("Id", "N", 10, 0), ("density", "C", 16, 0)],
              records=[[i + 1, d] for i, d in enumerate(forest["density"])])

    obs = rasterize(list(dep.geometry), out_shape=dem.shape, transform=tr).astype("uint8")
    with rasterio.open(out_p / "obs_deposition.tif", "w", driver="GTiff", height=ny, width=nx, count=1,
                       dtype="uint8", crs="EPSG:2056", transform=tr, nodata=0) as d:
        d.write(obs, 1)

    # sanity: elevations at the outlines (README: release ~1320 m, runout ~1080 m)
    relm = rasterize(list(rel.geometry), out_shape=dem.shape, transform=tr).astype(bool)
    print("DEM", dem.shape, float(dem.min()), float(dem.max()))
    print("release cells", int(relm.sum()), "z", float(dem[relm].min()), float(dem[relm].max()))
    print("deposit cells", int(obs.sum()), "z", float(dem[obs > 0].min()), float(dem[obs > 0].max()))
    lonlat = Transformer.from_crs(2056, 4326, always_xy=True)
    print("release centroid lon/lat", lonlat.transform(*rel.geometry.iloc[0].centroid.coords[0]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

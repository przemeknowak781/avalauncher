"""Build an AvaFrame com1DFA avalanche dir for the observed Filisur 2 avalanche (23.02.2012, event 23022012_2).

Inputs:
  - event data: OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552, CC-BY-4.0), folder avaFilisur2
                (release, deposition and forest polygons, EPSG:2056; provided by SLF Davos, Feistl et al. 2014)
  - terrain:    swissALTI3D 2 m tiles (swisstopo, open government data), year 2019, fetched via the
                public STAC API data.geo.admin.ch, mosaicked and averaged to 5 m in EPSG:2056.

Usage (laptop): python prep_filisur2.py <avaFramedataDir/avaFilisur2> <outDir> [tileCacheDir]
Creates <outDir>/{Inputs/DEM.asc,DEM.prj,REL/rel.*}, dem.tif, forest/forest.*, obs/deposition.*,
obs/deposition_mask.tif, obs/release_mask.tif, src/*.gpkg, README.txt.
"""

import json
import shutil
import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject

STAC = "https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissalti3d/items/"
YEAR = 2019
CELL = 5.0
MARGIN = 400.0  # m around release + deposition; runout of a dry-snow friction model must fit
EPSG = 2056


def tile_href(tile_id: str) -> str:
    """2 m GeoTIFF asset href of one STAC item (do not hand-build the file name)."""
    with urllib.request.urlopen(STAC + tile_id, timeout=60) as r:
        assets = json.load(r)["assets"]
    hrefs = [a["href"] for k, a in assets.items() if "_2_2056_" in k and k.endswith(".tif")]
    assert len(hrefs) == 1, (tile_id, list(assets))
    return hrefs[0]


def fetch_tiles(bounds, cache: Path) -> list[Path]:
    cache.mkdir(parents=True, exist_ok=True)
    xs = range(int(bounds[0] // 1000), int(bounds[2] // 1000) + 1)
    ys = range(int(bounds[1] // 1000), int(bounds[3] // 1000) + 1)
    out = []
    for x in xs:
        for y in ys:
            tid = f"swissalti3d_{YEAR}_{x}-{y}"
            hits = list(cache.glob(f"{tid}_2_2056_*.tif"))
            if not hits:
                href = tile_href(tid)
                dst = cache / href.rsplit("/", 1)[1]
                with urllib.request.urlopen(href, timeout=300) as r, open(dst, "wb") as f:
                    shutil.copyfileobj(r, f)
                hits = [dst]
            out.append(hits[0])
    return out


def write_asc(path: Path, dem: np.ndarray, tr) -> None:
    """AAIGrid with corner registration (same writer as prep_popeletzbach.py)."""
    with open(path, "w") as f:
        f.write(f"ncols {dem.shape[1]}\nnrows {dem.shape[0]}\n")
        f.write(f"xllcorner {tr.c:.3f}\nyllcorner {tr.f + tr.e * dem.shape[0]:.3f}\n")
        f.write(f"cellsize {tr.a:.3f}\nNODATA_value -9999\n")
        np.savetxt(f, dem, fmt="%.2f")


def single_parts(gdf: gpd.GeoDataFrame, keep: list[str], prefix: str) -> gpd.GeoDataFrame:
    g = gdf.explode(index_parts=False).reset_index(drop=True)
    g = g[g.area > 1.0].reset_index(drop=True)
    out = gpd.GeoDataFrame({c: g[c].astype(str) for c in keep}, geometry=g.geometry, crs=gdf.crs)
    out.insert(0, "Id", range(1, len(out) + 1))
    out.insert(1, "name", [f"{prefix}_{i + 1}" for i in range(len(out))])
    return out


def main(src: str, out: str, cache: str | None) -> None:
    src_p, out_p = Path(src), Path(out)
    cache_p = Path(cache) if cache else out_p.parent / "swissalti3d"
    rel = gpd.read_file(src_p / "avaFilisur2_release_area.gpkg")
    dep = gpd.read_file(src_p / "avaFilisur2_deposition_area.gpkg")
    forest = gpd.read_file(src_p / "avaFiisur2_forest_area.gpkg")  # sic, file name typo in the dataset
    for g in (rel, dep, forest):
        assert g.crs.to_epsg() == EPSG, g.crs

    # grid: union of release + deposition, buffered, snapped to multiples of CELL
    b = np.vstack([rel.total_bounds, dep.total_bounds])
    x0 = np.floor((b[:, 0].min() - MARGIN) / CELL) * CELL
    y0 = np.floor((b[:, 1].min() - MARGIN) / CELL) * CELL
    x1 = np.ceil((b[:, 2].max() + MARGIN) / CELL) * CELL
    y1 = np.ceil((b[:, 3].max() + MARGIN) / CELL) * CELL
    ncols, nrows = int(round((x1 - x0) / CELL)), int(round((y1 - y0) / CELL))
    tr = from_origin(x0, y1, CELL, CELL)
    crs = CRS.from_epsg(EPSG)

    tiles = fetch_tiles((x0, y0, x1, y1), cache_p)
    dem = np.full((nrows, ncols), np.nan, dtype="float32")
    for t in tiles:
        with rasterio.open(t) as r:
            part = np.full_like(dem, np.nan)
            reproject(rasterio.band(r, 1), part, dst_transform=tr, dst_crs=crs,
                      dst_nodata=np.nan, resampling=Resampling.average)
        dem = np.where(np.isnan(dem), part, dem)
    assert np.isfinite(dem).all() and dem.min() > 0, "DEM has holes"

    inputs = out_p / "Inputs"
    (inputs / "REL").mkdir(parents=True, exist_ok=True)
    for d in ("forest", "obs", "src"):
        (out_p / d).mkdir(exist_ok=True)
    prof = dict(driver="GTiff", height=nrows, width=ncols, count=1, dtype="float32", crs=crs,
                transform=tr, compress="deflate")
    with rasterio.open(out_p / "dem.tif", "w", **prof) as w:
        w.write(dem, 1)
    write_asc(inputs / "DEM.asc", dem, tr)
    prj = crs.to_wkt(version="WKT1_ESRI")
    (inputs / "DEM.prj").write_text(prj)

    # release: thickness field is empty in the source (no documented thickness) -> dropped,
    # com1DFA gets relTh from the config (relThFromFile = False)
    single_parts(rel, [], "rel").to_file(inputs / "REL" / "rel.shp", engine="pyogrio")
    single_parts(forest, ["Density"], "forest").to_file(out_p / "forest" / "forest.shp", engine="pyogrio")
    dep_s = single_parts(dep, [], "dep")
    dep_s.to_file(out_p / "obs" / "deposition.shp", engine="pyogrio")
    mprof = dict(prof, dtype="uint8", nodata=0)
    masks = {}
    for name, g in (("deposition_mask", dep), ("release_mask", rel)):
        m = rasterize([geom.__geo_interface__ for geom in g.geometry], out_shape=dem.shape,
                      transform=tr).astype("uint8")
        with rasterio.open(out_p / "obs" / f"{name}.tif", "w", **mprof) as w:
            w.write(m, 1)
        masks[name] = m.astype(bool)
        print(name, int(m.sum()), "cells", f"{m.sum() * CELL * CELL:.0f} m2", f"(polygon {g.area.sum():.0f} m2)")
    rel_m, dep_m = masks["release_mask"], masks["deposition_mask"]
    for f in src_p.iterdir():
        shutil.copy(f, out_p / "src" / f.name)

    (out_p / "README.txt").write_text(f"""avaFilisur2 - AvaFrame com1DFA avalanche dir (Avalauncher calibration, HackYeah 2026)

Event: Filisur (GR, Switzerland), 23.02.2012, event id 23022012_2, wet-snow avalanche.
  Dataset README: release ~1360 m a.s.l., runout ~1058 m a.s.l.; mapped release area {rel.area.sum():.0f} m2,
  release volume 1390 m3 per the dataset README (mapped area x assumed fracture depth, Feistl et al. 2014).
  Observed: deposition area polygon ({dep.area.sum():.0f} m2), no documented deposition thickness.
  Release thickness: unknown (not documented). Feistl et al. 2014 used a standardized 1 m for modelling.
  Check on this DEM: release polygon spans {float(dem[rel_m].min()):.0f}-{float(dem[rel_m].max()):.0f} m a.s.l.
  (dataset README says ~1360 m), deposition polygon {float(dem[dep_m].min()):.0f}-{float(dem[dep_m].max()):.0f} m
  (README: runout 1058 m).

Layout
  Inputs/DEM.asc, DEM.prj   terrain, {ncols} x {nrows} cells, {CELL:.0f} m, EPSG:2056 (LV95),
                            lower-left corner ({x0:.0f}, {y0:.0f}), corner registration
  Inputs/REL/rel.shp        release area (single part, no thickness attribute)
  dem.tif                   same terrain as GeoTIFF (grid used for scoring)
  forest/forest.shp         forest polygons, attribute Density = dense | open (for simTypeList=res runs)
  obs/deposition.shp        observed deposition outline (scoring only, not an input)
  obs/deposition_mask.tif   observed deposition rasterized on the {CELL:.0f} m grid (1 = observed)
  obs/release_mask.tif      release rasterized on the same grid
  src/                      original gpkg files and README.md from the dataset
  base/Inputs -> ../Inputs  (Spark only) symlink so tools/calibration/run_calib.py runs unchanged
  runs/smoke/               (Spark only) com1DFA smoke run, smoke_filisur2.py

Sources and licences
  Event data: OpenNHM/AvaFrameData 1.0, Zenodo DOI 10.5281/zenodo.20701552, CC-BY-4.0,
    folder avaFilisur2; data provided by SLF Davos. Reference: Feistl, T., Bebi, P., Teich, M.,
    Buehler, Y., Christen, M., Thuro, K., Bartelt, P. (2014). Observations and modeling of the braking
    effect of forests on small and medium avalanches. Journal of Glaciology 60(219), 124-138.
  Terrain: swissALTI3D, (c) swisstopo, open government data (free use, source attribution required),
    release year {YEAR}, 2 m tiles {', '.join(t.name.split('_2_2056')[0].replace('swissalti3d_', '') for t in tiles)},
    downloaded from data.geo.admin.ch (STAC), mosaicked and averaged 2 m -> {CELL:.0f} m.
    The DEM postdates the 2012 event.
Built by tools/calibration/events/avaFilisur2/prep_filisur2.py
""")
    print("DEM", dem.shape, float(dem.min()), float(dem.max()), "tiles", [t.name for t in tiles])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)

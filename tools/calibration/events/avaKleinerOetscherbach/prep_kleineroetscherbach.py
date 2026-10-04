"""Build an AvaFrame com1DFA project for the observed Kleiner Oetscherbach avalanche (25.02.2009, Lower Austria).

Inputs:
  - event data: OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552, CC-BY-4.0), folder avaKleinerOetscherbach
                (releaseArea / eventArea / forest 20090225, CRS MGI Austria Lambert = EPSG:31287)
  - terrain:    BEV ALS DTM Austria 1 m (CC BY 4.0), 50 km tile N2750000E4700000 in EPSG:3035, read as a
                window over HTTP range requests (no 8-12 GB download), then averaged to 5 m on an
                EPSG:31287 grid (Resampling.average from 1 m, so no overview guesswork).

Usage: python prep_kleineroetscherbach.py <avaFramedataDir/avaKleinerOetscherbach> <outRoot>
Creates the same layout as tools/calibration/prep_popeletzbach.py, so run_calib.py works unchanged:
  <outRoot>/base/Inputs/{DEM.asc,DEM.prj,REL/rel.*}   com1DFA avalanche dir
  <outRoot>/dem.tif                                  same 5 m grid, EPSG:31287
  <outRoot>/forest/forest.*                          optional resistance input
  <outRoot>/src/                                     original event shapefiles + README.md (for scoring)
  <outRoot>/src/obs_event.tif, obs_release.tif       observed outlines rasterised on the DEM grid (0/1)
  <outRoot>/README.txt
"""

import os
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio
import shapefile
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds

STICHTAG = "20250915"
TILE = ("https://data.bev.gv.at/download/ALS/DTM/{d}/"
        "ALS_DTM_CRS3035RES50000mN2750000E4700000.tif")
CELL = 5.0
# event bbox (EPSG:31287): x 536577-537301, y 440488-441687; release at the south end (y 440488-440757).
# Margins: 500 m W/E/S, 800 m N (runout direction), forest (to y 442105) included.
BBOX = (536050.0, 439950.0, 537800.0, 442500.0)
TAG = "20090225"


def fetch_dem(dst_crs: CRS) -> tuple[np.ndarray, rasterio.Affine]:
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    x0, y0, x1, y1 = BBOX
    nx, ny = int(round((x1 - x0) / CELL)), int(round((y1 - y0) / CELL))
    dst_tr = from_origin(x0, y1, CELL, CELL)
    dst = np.full((ny, nx), np.nan, dtype="float32")
    with rasterio.open("/vsicurl/" + TILE.format(d=STICHTAG)) as src:
        b = transform_bounds(dst_crs, src.crs, *BBOX, densify_pts=21)
        pad = 60.0
        win = from_bounds(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad, src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win).astype("float32")
        arr[arr == src.nodata] = np.nan
        print("source window", win, arr.shape, "nan", int(np.isnan(arr).sum()))
        reproject(arr, dst, src_transform=src.window_transform(win), src_crs=src.crs,
                  src_nodata=np.nan, dst_transform=dst_tr, dst_crs=dst_crs, dst_nodata=np.nan,
                  resampling=Resampling.average)
    return dst, dst_tr


def mask_of(shp: Path, shape, transform) -> np.ndarray:
    geoms = [s.__geo_interface__ for s in shapefile.Reader(str(shp)).shapes()]
    return rasterize(geoms, out_shape=shape, transform=transform).astype("uint8")


def main(src: str, out: str) -> None:
    src_p, out_p = Path(src), Path(out)
    inputs = out_p / "base" / "Inputs"
    (inputs / "REL").mkdir(parents=True, exist_ok=True)
    crs = CRS.from_epsg(31287)
    tif = out_p / "dem.tif"
    if tif.exists():
        with rasterio.open(tif) as r:
            dem, tr = r.read(1), r.transform
    else:
        dem, tr = fetch_dem(crs)
        assert np.isfinite(dem).all() and dem.min() > 0, "DEM has holes"
        prof = dict(driver="GTiff", height=dem.shape[0], width=dem.shape[1], count=1,
                    dtype="float32", crs=crs, transform=tr, nodata=-9999.0, compress="deflate")
        with rasterio.open(tif, "w", **prof) as w:
            w.write(dem, 1)
    # AAIGrid with corner registration
    with open(inputs / "DEM.asc", "w") as f:
        f.write(f"ncols {dem.shape[1]}\nnrows {dem.shape[0]}\n")
        f.write(f"xllcorner {tr.c:.3f}\nyllcorner {tr.f + tr.e * dem.shape[0]:.3f}\n")
        f.write(f"cellsize {tr.a:.3f}\nNODATA_value -9999\n")
        np.savetxt(f, dem, fmt="%.2f")
    shutil.copy(src_p / f"releaseArea{TAG}.prj", inputs / "DEM.prj")
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        shutil.copy(src_p / f"releaseArea{TAG}.{ext}", inputs / "REL" / f"rel.{ext}")
    res = out_p / "forest"
    res.mkdir(exist_ok=True)
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        shutil.copy(src_p / f"forest{TAG}.{ext}", res / f"forest.{ext}")
    # originals + observed outlines on the DEM grid, for scoring
    keep = out_p / "src"
    keep.mkdir(exist_ok=True)
    for f in src_p.iterdir():
        shutil.copy(f, keep / f.name)
    prof = dict(driver="GTiff", height=dem.shape[0], width=dem.shape[1], count=1, dtype="uint8",
                crs=crs, transform=tr, nodata=None, compress="deflate")
    stats = {}
    for name, shp in (("obs_event", f"eventArea{TAG}.shp"), ("obs_release", f"releaseArea{TAG}.shp")):
        m = mask_of(src_p / shp, dem.shape, tr)
        with rasterio.open(keep / f"{name}.tif", "w", **prof) as w:
            w.write(m, 1)
        stats[name] = m
    rel, ev = stats["obs_release"].astype(bool), stats["obs_event"].astype(bool)
    rec = shapefile.Reader(str(src_p / f"releaseArea{TAG}.shp")).records()
    print("DEM", dem.shape, round(float(dem.min()), 1), round(float(dem.max()), 1), crs.to_string())
    print("release cells", int(rel.sum()), "elev", round(float(dem[rel].min()), 1), "-",
          round(float(dem[rel].max()), 1), "| event cells", int(ev.sum()), "lowest event elev",
          round(float(dem[ev].min()), 1))
    print("release thickness attribute:", [r.as_dict().get("thickness") for r in rec])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

"""Build an AvaFrame com1DFA avalanche dir for the observed Eiskar avalanche (Ramsau am Dachstein, Styria, 15.01.2019).

Inputs:
  - event data: OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552, CC-BY-4.0), folder avaEiskar (GeoPackages, EPSG:31287)
  - terrain:    BEV ALS DTM Hoehenraster 1 m (Stichtag 15.09.2024, CC BY 4.0), 50 km COG tiles in EPSG:3035,
                read by window over HTTP (no full-tile download) and resampled (average) to 5 m in EPSG:31287.
                The Land Tirol WCS used for Popeletzbach does not cover Styria; BEV is the national ALS product.

Usage (laptop): python prep_eiskar.py <avaFramedataDir/avaEiskar> <outDir>
Creates <outDir>/{Inputs/DEM.asc, Inputs/DEM.prj, Inputs/REL/relESK1.*, dem.tif, observed/*, extras/*, README.txt}.
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import shapefile
from pyproj import CRS
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds
from shapely.geometry import mapping
from shapely.ops import transform as shp_transform

BEV = "https://data.bev.gv.at/download/ALS/DTM/20240915/ALS_DTM_CRS3035RES50000mN{n}E{e}.tif"
CELL = 5.0
# margin around release + all mapped outlines (m): generous downslope (south), runout must fit
M_W, M_E, M_N, M_S = 800.0, 800.0, 500.0, 1200.0
ESRI_WKT = CRS.from_epsg(31287).to_wkt(version="WKT1_ESRI")


def drop_z(g):
    return shp_transform(lambda x, y, z=None: (x, y), g)


def write_shp(path: Path, geoms, records, fields, kind):
    path.parent.mkdir(parents=True, exist_ok=True)
    w = shapefile.Writer(str(path), shapeType=kind)
    for name, typ, size, dec in fields:
        w.field(name, typ, size=size, decimal=dec)
    for g, rec in zip(geoms, records):
        w.shape(mapping(drop_z(g)))
        w.record(*rec)
    w.close()
    path.with_suffix(".prj").write_text(ESRI_WKT)
    path.with_suffix(".cpg").write_text("UTF-8")


def fetch_dem(bounds31287):
    """Mosaic the BEV 1 m COG windows covering bounds (EPSG:3035) and resample (average) to the 5 m EPSG:31287 grid."""
    xmin, ymin, xmax, ymax = bounds31287
    nx, ny = int(round((xmax - xmin) / CELL)), int(round((ymax - ymin) / CELL))
    dst_tr = from_origin(xmin, ymax, CELL, CELL)
    e0, n0, e1, n1 = transform_bounds("EPSG:31287", "EPSG:3035", xmin, ymin, xmax, ymax, densify_pts=41)
    e0, n0, e1, n1 = np.floor(e0) - 30, np.floor(n0) - 30, np.ceil(e1) + 30, np.ceil(n1) + 30
    # 1 m source mosaic in EPSG:3035 (pixel edges on x.5 as in the BEV tiles)
    src_tr = from_origin(e0 - 0.5, n1 + 0.5, 1.0, 1.0)
    w, h = int(e1 - e0) + 1, int(n1 - n0) + 1
    src = np.full((h, w), np.nan, dtype="float32")
    tiles = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                      GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
        for te in range(int(e0 // 50000) * 50000, int(e1 // 50000) * 50000 + 1, 50000):
            for tn in range(int(n0 // 50000) * 50000, int(n1 // 50000) * 50000 + 1, 50000):
                url = BEV.format(n=tn, e=te)
                tiles.append(url)
                with rasterio.open("/vsicurl/" + url) as r:
                    win = from_bounds(*src_tr * (0, h), *src_tr * (w, 0), transform=r.transform)
                    win = win.round_offsets().round_lengths()
                    a = r.read(1, window=win, boundless=True, fill_value=r.nodata).astype("float32")
                    a[a == r.nodata] = np.nan
                    # same 1 m lattice as the mosaic (BEV edges on x.5), so the boundless window is the mosaic grid
                    assert a.shape == src.shape, (a.shape, src.shape)
                    np.copyto(src, a, where=np.isfinite(a))
                print("read", url, a.shape, flush=True)
    assert np.isfinite(src).all(), "1 m mosaic has holes"
    dem = np.full((ny, nx), np.nan, dtype="float32")
    reproject(src, dem, src_transform=src_tr, src_crs="EPSG:3035", dst_transform=dst_tr, dst_crs="EPSG:31287",
              resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
    assert np.isfinite(dem).all() and dem.min() > 0, "DEM has holes"
    return dem, dst_tr, tiles


def main(src: str, out: str) -> None:
    sp, op = Path(src), Path(out)
    rd = lambda n: gpd.read_file(sp / f"{n}Event20190115.gpkg")  # noqa: E731
    rel, dep_line = rd("release"), rd("deposition")
    dfa, mx, psa = rd("depositionDFAOutline"), rd("depositionMaxOutline"), rd("depositionPSAOutline")
    ent, res = rd("entrainment"), rd("resistance")
    for g in (rel, dep_line, dfa, mx, psa, ent, res):
        assert g.crs.to_epsg() == 31287, g.crs

    # release: ESK_1 is the one relevant for the runout (README + report ch. 6); ESK_2 released ~half a day later
    rf = [("name", "C", 80, 0), ("thickness", "N", 11, 3), ("ci95", "N", 11, 3)]
    recs = {r["name"]: (r["name"].replace("_", ""), float(r["thickness"]), None) for _, r in rel.iterrows()}
    geo = {r["name"]: r.geometry for _, r in rel.iterrows()}
    write_shp(op / "Inputs" / "REL" / "relESK1.shp", [geo["ESK_1"]], [recs["ESK_1"]], rf, shapefile.POLYGON)
    write_shp(op / "extras" / "REL_ESK2" / "relESK2.shp", [geo["ESK_2"]], [recs["ESK_2"]], rf, shapefile.POLYGON)
    write_shp(op / "extras" / "REL_ESK1_ESK2" / "relESK1ESK2.shp", [geo["ESK_1"], geo["ESK_2"]],
              [recs["ESK_1"], recs["ESK_2"]], rf, shapefile.POLYGON)
    write_shp(op / "extras" / "ENT" / "entrainment.shp", list(ent.geometry),
              [(f"ent{i}", None, None) for i in range(len(ent))], rf, shapefile.POLYGON)
    write_shp(op / "extras" / "RES" / "resistance.shp", list(res.geometry),
              [(f"res{i}",) for i in range(len(res))], [("name", "C", 80, 0)], shapefile.POLYGON)

    # observed footprints (deposition outlines, not the full affected area)
    obs = op / "observed"
    nf = [("name", "C", 80, 0)]
    write_shp(obs / "depositionDFAOutline.shp", list(dfa.geometry), [("DFA",)] * len(dfa), nf, shapefile.POLYGON)
    write_shp(obs / "depositionMaxOutline.shp", list(mx.geometry), [("MAX",)] * len(mx), nf, shapefile.POLYGON)
    write_shp(obs / "depositionPSAOutline.shp", list(psa.geometry), [("PSA",)] * len(psa), nf, shapefile.POLYGON)
    write_shp(obs / "depositionEventLine.shp", list(dep_line.geometry), [("visual",)] * len(dep_line), nf,
              shapefile.POLYLINE)

    # domain = release + every mapped outline (+ entrainment/resistance) + margin, snapped to the 5 m grid
    allb = np.array([g.total_bounds for g in (rel, dep_line, dfa, mx, psa, ent, res)])
    xmin, ymin = allb[:, 0].min() - M_W, allb[:, 1].min() - M_S
    xmax, ymax = allb[:, 2].max() + M_E, allb[:, 3].max() + M_N
    xmin, ymin = np.floor(xmin / CELL) * CELL, np.floor(ymin / CELL) * CELL
    xmax, ymax = np.ceil(xmax / CELL) * CELL, np.ceil(ymax / CELL) * CELL
    dem, tr, tiles = fetch_dem((xmin, ymin, xmax, ymax))

    inp = op / "Inputs"
    with open(inp / "DEM.asc", "w") as f:
        f.write(f"ncols {dem.shape[1]}\nnrows {dem.shape[0]}\n")
        f.write(f"xllcorner {tr.c:.3f}\nyllcorner {tr.f + tr.e * dem.shape[0]:.3f}\n")
        f.write(f"cellsize {tr.a:.3f}\nNODATA_value -9999\n")
        np.savetxt(f, dem, fmt="%.2f")
    (inp / "DEM.prj").write_text(ESRI_WKT)
    prof = dict(driver="GTiff", dtype="float32", width=dem.shape[1], height=dem.shape[0], count=1,
                crs="EPSG:31287", transform=tr, nodata=-9999.0, compress="deflate")
    with rasterio.open(op / "dem.tif", "w", **prof) as d:
        d.write(dem, 1)
    mprof = dict(prof, dtype="uint8", nodata=None)
    for name, g in (("obs_dfa", dfa), ("obs_max", mx), ("obs_psa", psa), ("rel_esk1", rel[rel["name"] == "ESK_1"])):
        m = rasterize([mapping(drop_z(x)) for x in g.geometry], out_shape=dem.shape, transform=tr).astype("uint8")
        with rasterio.open(obs / f"{name}.tif", "w", **mprof) as d:
            d.write(m, 1)
        print(name, "cells", int(m.sum()), "area_ha", round(m.sum() * CELL * CELL / 1e4, 2))
    print("DEM", dem.shape, float(dem.min()), float(dem.max()), "bounds", (xmin, ymin, xmax, ymax))
    print("tiles", tiles)
    (op / "domain.txt").write_text(
        f"EPSG:31287 bounds {xmin} {ymin} {xmax} {ymax}\ncell {CELL}\nshape {dem.shape}\n"
        f"elev {dem.min():.1f}..{dem.max():.1f}\ntiles {' '.join(tiles)}\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

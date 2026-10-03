"""Build an AvaFrame com1DFA project for the observed Popeletzbach avalanche (7.04.2009).

Inputs:
  - event data: OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552, CC-BY-4.0), folder avaPopeletzbach
  - terrain:    Land Tirol "Gelaendemodell_5m_M28" (CC BY 4.0 AT), fetched from the public WCS
                gis.tirol.gv.at, reprojected server-side (bilinear) to EPSG:31287 (the shapefile CRS), 5 m.

Usage (on Spark): python prep_popeletzbach.py <avaFramedataDir/avaPopeletzbach> <outRoot>
Creates <outRoot>/base/Inputs/{DEM.asc,DEM.prj,REL/rel.*} and <outRoot>/dem.tif.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

WCS = ("https://gis.tirol.gv.at/arcgis/services/Service_Public/terrain/MapServer/WCSServer"
       "?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&COVERAGE=Gelaendemodell_5m_M28"
       "&CRS=EPSG:31287&RESPONSE_CRS=EPSG:31287&BBOX=318800,335300,320100,337800"
       "&RESX=5&RESY=5&FORMAT=GeoTIFF&INTERPOLATION=bilinear")


def main(src: str, out: str) -> None:
    src_p, out_p = Path(src), Path(out)
    inputs = out_p / "base" / "Inputs"
    (inputs / "REL").mkdir(parents=True, exist_ok=True)
    tif = out_p / "dem.tif"
    if not tif.exists():
        subprocess.run(["curl", "-s", "-m", "120", "-o", str(tif), WCS], check=True)
    with rasterio.open(tif) as r:
        dem = r.read(1).astype("float32")
        prof = r.profile
        crs_wkt = r.crs.to_wkt("WKT1_ESRI") if hasattr(r.crs, "to_wkt") else r.crs.wkt
        tr = r.transform
    assert np.isfinite(dem).all() and dem.min() > 0, "DEM has holes"
    # AAIGrid with corner registration
    with open(inputs / "DEM.asc", "w") as f:
        f.write(f"ncols {dem.shape[1]}\nnrows {dem.shape[0]}\n")
        f.write(f"xllcorner {tr.c:.3f}\nyllcorner {tr.f + tr.e * dem.shape[0]:.3f}\n")
        f.write(f"cellsize {tr.a:.3f}\nNODATA_value -9999\n")
        np.savetxt(f, dem, fmt="%.2f")
    shutil.copy(src_p / "releaseArea20090407.prj", inputs / "DEM.prj")
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        shutil.copy(src_p / f"releaseArea20090407.{ext}", inputs / "REL" / f"rel.{ext}")
    # forest as resistance input, kept aside (used only by the optional forest run)
    res = out_p / "forest"
    res.mkdir(exist_ok=True)
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        shutil.copy(src_p / f"forest20090407.{ext}", res / f"forest.{ext}")
    print("DEM", dem.shape, float(dem.min()), float(dem.max()), prof["crs"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

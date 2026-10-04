"""Real snow cover from Sentinel-2 L2A for the demo episode (11-13.01.2025), on our 400x400 grid.

Search: Element84 Earth Search STAC (public, no account). Per scene we read only the SCL window over
our area (HTTP range reads of the public COGs) to measure cloud cover over the area itself, not the
tile. Then we pick the clearest acquisition closest to the demo mornings 12-13.01.2025 and read
B02/B03/B04 (10 m), B11 (20 m) and SCL (20 m), reprojected to EPSG:2180, 10 m cells, rows from north.

Writes web/data/sentinel_snow.json, sentinel_snow.png (RGBA overlay), sentinel_truecolor.jpg and
a cache of the arrays in data/raw/sentinel/ for the board and the wind check.

Run: python tools/satellite/fetch_sentinel.py
"""

import json
import os
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

os.environ.update(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                  AWS_NO_SIGN_REQUEST="YES", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="1")

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from rasterio.vrt import WarpedVRT  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web" / "data"
CACHE = ROOT / "data" / "raw" / "sentinel"
STAC = "https://earth-search.aws.element84.com/v1/search"
BBOX = [19.955, 49.205, 20.035, 49.262]
EPISODE = (date(2025, 1, 12), date(2025, 1, 13))  # demo mornings
EPISODE_DAYS = ["2025-01-11", "2025-01-12", "2025-01-13"]
CLEAR_MAX = 5.0  # % of the area under cloud for a scene to count as clear

TERRAIN = json.loads((DATA / "terrain.json").read_text(encoding="utf-8"))
N = TERRAIN["width"]
GRID = dict(crs=TERRAIN["crs"], transform=from_origin(TERRAIN["e0"], TERRAIN["n0"], TERRAIN["cell_m"], TERRAIN["cell_m"]),
            width=N, height=TERRAIN["height"])

CLOUD_CLASSES = (8, 9, 10)  # SCL: cloud medium/high probability, thin cirrus
SNOW_CLASS = 11


def stac_search(start, end):
    body = {"collections": ["sentinel-2-l2a"], "bbox": BBOX, "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "limit": 200, "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}]}
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90, context=ssl.create_default_context()) as r:
        return json.loads(r.read())["features"]


def href(item, key):
    return "/vsicurl/" + item["assets"][key]["href"]


def read(item, key, resampling):
    """One asset, warped to our grid. Only the blocks over the area are fetched."""
    with rasterio.open(href(item, key)) as src, WarpedVRT(src, resampling=resampling, **GRID) as v:
        return v.read()


def reflectance(item, key):
    """Surface reflectance from the uint16 COG.

    Earth Search lists raster:bands offset -0.1 (the BOA_ADD_OFFSET of baseline >= 04.00), but its COGs
    with earthsearch:boa_offset_applied = true already have the offset subtracted: B11 over snow reads
    DN 1-200, which would be negative after another -1000. So only the 1e-4 scale applies in that case.
    """
    dn = read(item, key, Resampling.bilinear)[0].astype(np.float32)
    off = 0.0 if item["properties"].get("earthsearch:boa_offset_applied", False) else -0.1
    if float(item["properties"].get("s2:processing_baseline", "0")) < 4.0:
        off = 0.0
    r = dn * 1e-4 + off
    r[dn == 0] = np.nan
    return r


def area_cloud(item):
    scl = read(item, "scl", Resampling.nearest)[0]
    valid = scl > 0
    n = max(int(valid.sum()), 1)
    return {"scene_id": item["id"], "datetime": item["properties"]["datetime"],
            "cloud_pct_over_area": round(100 * float(np.isin(scl, CLOUD_CLASSES).sum()) / n, 1),
            "scl_snow_pct": round(100 * float((scl == SNOW_CLASS).sum()) / n, 1),
            "valid_pct": round(100 * n / scl.size, 1), "tile_cloud_pct": round(item["properties"]["eo:cloud_cover"], 1)}


def pl(x, nd=1):
    """Polish decimal comma."""
    return f"{x:.{nd}f}".replace(".", ",")


def day(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def days_from_episode(d):
    if d < EPISODE[0]:
        return (EPISODE[0] - d).days
    return max((d - EPISODE[1]).days, 0)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    items = stac_search("2024-12-01", "2025-02-28")
    byid = {it["id"]: it for it in items}
    with ThreadPoolExecutor(8) as ex:
        survey = sorted(ex.map(area_cloud, items), key=lambda s: s["datetime"])
    (CACHE / "survey.json").write_text(json.dumps(survey, indent=1), encoding="utf-8")
    for s in survey:
        print(f"{s['scene_id']:28s} {s['datetime'][:16]}  area cloud {s['cloud_pct_over_area']:5.1f}%  tile {s['tile_cloud_pct']:5.1f}%")

    clear = [s for s in survey if s["cloud_pct_over_area"] <= CLEAR_MAX]
    best = min(clear, key=lambda s: (days_from_episode(day(s["datetime"])), s["cloud_pct_over_area"]))
    item = byid[best["scene_id"]]
    d = day(best["datetime"])
    print("chosen:", best)

    scl = read(item, "scl", Resampling.nearest)[0]
    b02, b03, b04, b11 = (reflectance(item, k) for k in ("blue", "green", "red", "swir16"))
    ndsi = (b03 - b11) / np.maximum(b03 + b11, 1e-4)
    cloud = np.isin(scl, CLOUD_CLASSES)
    valid = (scl > 0) & np.isfinite(ndsi)
    snow = (ndsi > 0.4) & (b03 > 0.1) & ~cloud & valid
    clear_px = valid & ~cloud
    np.savez_compressed(CACHE / f"{item['id']}.npz", scl=scl, b02=b02, b03=b03, b04=b04, b11=b11)

    z = np.fromfile(DATA / "terrain_f32.bin", "<f4").reshape(N, N)
    bands = [(1300, 1500), (1500, 1700), (1700, 1900), (1900, 2300)]
    by_elev = {f"{lo}-{hi}": round(100 * float(snow[(z >= lo) & (z < hi) & clear_px].mean()), 1) for lo, hi in bands}
    nosnow = clear_px & ~snow
    nosnow_low = float(((z < 1500) & nosnow).sum()) / max(int(nosnow.sum()), 1)

    # Overlay: snow white-blue, clouds grey hatched, snow-free transparent. Row 0 = north, like the grid.
    rgba = np.zeros((N, N, 4), np.uint8)
    rgba[snow] = (196, 224, 255, 150)
    rr, cc = np.mgrid[0:N, 0:N]
    hatch = ((rr + cc) % 6) < 2
    rgba[cloud] = (128, 128, 128, 110)
    rgba[cloud & hatch] = (90, 90, 90, 220)
    Image.fromarray(rgba, "RGBA").save(DATA / "sentinel_snow.png", optimize=True)

    # True colour from B04/B03/B02. The TCI asset saturates on snow (80-90 % of our cells at 255),
    # so we stretch reflectance 0..1.25 linearly with a mild gamma instead.
    rgb = np.stack([b04, b03, b02], -1)
    rgb = np.clip(np.nan_to_num(rgb) / 1.25, 0, 1) ** (1 / 1.25)
    Image.fromarray((rgb * 255 + 0.5).astype(np.uint8)).save(DATA / "sentinel_truecolor.jpg", quality=90)

    ep = {s["datetime"][:10]: s["cloud_pct_over_area"] for s in survey if s["datetime"][:10] in EPISODE_DAYS}
    near = [s for s in survey if abs((day(s["datetime"]) - EPISODE[1]).days) <= 7]
    out = {
        "date": d.isoformat(),
        "acquired_utc": best["datetime"][:19] + "Z",
        "scene_id": item["id"],
        "cloud_pct_over_area": best["cloud_pct_over_area"],
        "snow_pct": round(100 * float(snow.sum()) / max(int(clear_px.sum()), 1), 1),
        "snow_pct_by_elevation_m": by_elev,
        "scl_snow_class_pct": best["scl_snow_pct"],
        "days_after_episode": days_from_episode(d),
        "episode_cloud_pct_over_area": ep,
        "nearby_acquisitions": [{"date": s["datetime"][:10], "scene_id": s["scene_id"],
                                 "cloud_pct_over_area": s["cloud_pct_over_area"]} for s in near],
        "method": "NDSI = (B03 - B11) / (B03 + B11); śnieg gdy NDSI > 0,4 i B03 > 0,1; chmury z SCL (klasy 8, 9, 10). "
                  "B11 (20 m) i SCL przepróbkowane do siatki 10 m EPSG:2180.",
        "grid": {"crs": TERRAIN["crs"], "e0": TERRAIN["e0"], "n0": TERRAIN["n0"], "cell_m": TERRAIN["cell_m"],
                 "width": N, "height": N, "rows": "od północy"},
        "files": {"overlay": "sentinel_snow.png", "truecolor": "sentinel_truecolor.jpg"},
        "overlay_legend": {"snow": [196, 224, 255, 150], "cloud": [128, 128, 128, 110], "cloud_hatch": [90, 90, 90, 220],
                           "no_snow": "przezroczyste (brak potwierdzenia: las, głęboki cień)"},
        "source": "Copernicus Sentinel-2 L2A via Element84 Earth Search (AWS Open Data)",
        "licence": "Copernicus data free and open",
        "credit": f"Zawiera zmodyfikowane dane Copernicus Sentinel ({d.year})",
        "note": (f"Prawdziwe zdjęcie satelitarne z {d.day}.{d.month:02d}.{d.year}, {days_from_episode(d)} dni po epizodzie "
                 f"11–13.01.2025. W dniach epizodu satelita nie widział terenu: "
                 + ", ".join(f"{int(k[8:10])}.{k[5:7]} " + (f"chmury nad {ep[k]:.0f}% obszaru" if k in ep else "brak przelotu")
                             for k in EPISODE_DAYS)
                 + f". Satelita pokazuje, gdzie leży śnieg, a nie jego grubość ani warstwy; grubość płyty w aplikacji "
                 f"pozostaje syntetyczna. Komórki bez potwierdzonego śniegu ({pl(100 * nosnow.sum() / max(int(clear_px.sum()), 1))}%) "
                 f"to ciemne piksele, w {100 * nosnow_low:.0f}% poniżej 1500 m n.p.m., czyli w lesie: korony drzew zasłaniają śnieg, "
                 f"a jasność jest za niska, by go potwierdzić. Klasa śniegu SCL obejmuje tylko {best['scl_snow_pct']:.0f}% "
                 f"obszaru, bo niskie styczniowe słońce zostawia stoki północne w cieniu (SCL: ciemne piksele); "
                 f"NDSI rozpoznaje śnieg także w cieniu."),
    }
    (DATA / "sentinel_snow.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("date", "scene_id", "cloud_pct_over_area", "snow_pct", "snow_pct_by_elevation_m",
                                          "episode_cloud_pct_over_area")}, ensure_ascii=False))
    print(out["note"])


if __name__ == "__main__":
    main()

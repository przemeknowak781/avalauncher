"""Score every com1DFA run under <calibRoot>/runs/* against the observed Popeletzbach event.

Footprint = peak flow thickness pft > 0.1 m (ppr > 1 kPa reported as a second IoU).
Metrics:
  iou          |sim ∩ event| / |sim ∪ event|           (event = eventArea20090407, observed area covered)
  dep_hit      fraction of observed deposit cells (eventDepositionArea20090407) inside the footprint
  runout_err_m  sim runout - observed runout, both = max horizontal distance from the release top
               (highest DEM cell in the release polygon); > 0 overshoot, < 0 stops short
Usage: python score_calib.py <calibRoot>  -> <calibRoot>/scores.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import shapefile
from rasterio.features import rasterize

FT_MIN, PPR_MIN = 0.1, 1.0


def mask_of(shp: Path, shape, transform) -> np.ndarray:
    geoms = [s.__geo_interface__ for s in shapefile.Reader(str(shp)).shapes()]
    return rasterize(geoms, out_shape=shape, transform=transform).astype(bool)


def main(root: str) -> None:
    rootp = Path(root).expanduser()
    src = rootp / "src"
    rows = []
    ref = None
    for run in sorted((rootp / "runs").iterdir()):
        csv = run / "simDF.csv"
        if not csv.exists():
            continue
        df = pd.read_csv(csv, index_col=0)
        for _, s in df.iterrows():
            pk = run / "Outputs" / "com1DFA" / "peakFiles"
            pft_f = pk / f"{s['simName']}_pft.asc"
            if not pft_f.exists():
                continue
            with rasterio.open(pft_f) as r:
                pft = r.read(1)
                tr = r.transform
            with rasterio.open(pk / f"{s['simName']}_ppr.asc") as r:
                ppr = r.read(1)
            if ref is None or ref["shape"] != pft.shape:
                with rasterio.open(rootp / "dem.tif") as d:
                    assert d.shape == pft.shape and d.transform.almost_equals(tr), "grid mismatch"
                    dem = d.read(1)
                ev = mask_of(src / "eventArea20090407.shp", pft.shape, tr)
                dep = mask_of(src / "eventDepositionArea20090407.shp", pft.shape, tr)
                rel = mask_of(src / "releaseArea20090407.shp", pft.shape, tr)
                rr, cc = np.indices(pft.shape)
                xs, ys = tr * (cc + 0.5, rr + 0.5)
                i0 = np.argmax(np.where(rel, dem, -1e9))
                x0, y0 = xs.flat[i0], ys.flat[i0]
                dist = np.hypot(xs - x0, ys - y0)
                obs_run = float(dist[ev].max())
                ref = dict(shape=pft.shape, ev=ev, dep=dep, dist=dist, obs_run=obs_run, dem=dem)
            fp = pft > FT_MIN
            fpp = ppr > PPR_MIN
            ev, dep = ref["ev"], ref["dep"]
            iou = (fp & ev).sum() / max((fp | ev).sum(), 1)
            iou_ppr = (fpp & ev).sum() / max((fpp | ev).sum(), 1)
            sim_run = float(ref["dist"][fp].max()) if fp.any() else 0.0
            frict = s["frictModel"]
            mu = {"samosATSmall": s.get("musamosatsmall"), "samosATMedium": s.get("musamosatmedium"),
                  "samosAT": s.get("musamosat"), "Voellmy": s.get("muvoellmy")}.get(frict)
            rows.append({
                "group": run.name, "simName": s["simName"], "frictModel": frict,
                "relTh": round(float(s["relTh"]), 3),
                "mu": None if mu is None else float(mu),
                "xsi": float(s["xsivoellmy"]) if frict == "Voellmy" else None,
                "iou": round(float(iou), 3), "iou_ppr1kPa": round(float(iou_ppr), 3),
                "dep_hit": round(float((fp & dep).sum() / dep.sum()), 3),
                "precision": round(float((fp & ev).sum() / max(fp.sum(), 1)), 3),
                "recall": round(float((fp & ev).sum() / ev.sum()), 3),
                "runout_sim_m": round(sim_run, 1), "runout_obs_m": round(ref["obs_run"], 1),
                "runout_error_m": round(sim_run - ref["obs_run"], 1),
                "min_elev_sim_m": round(float(ref["dem"][fp].min()), 1) if fp.any() else None,
                "area_sim_ha": round(float(fp.sum()) * abs(tr.a * tr.e) / 1e4, 2),
            })
    rows.sort(key=lambda r: -r["iou"])
    if len(sys.argv) > 2:  # same grid on another DEM variant (here: nearest-neighbour resampling) -> sensitivity
        other = {(r["frictModel"], r["relTh"], r["mu"], r["xsi"]): r
                 for r in json.loads((Path(sys.argv[2]).expanduser() / "scores.json").read_text())
                 if r["group"] != "smoke"}
        for r in rows:
            o = other.get((r["frictModel"], r["relTh"], r["mu"], r["xsi"]))
            if o:
                r["iou_dem_nearest"] = o["iou"]
                r["runout_error_m_dem_nearest"] = o["runout_error_m"]
    (rootp / "scores.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['group']:14s} {r['frictModel']:13s} relTh={r['relTh']:.2f} mu={r['mu']} xsi={r['xsi']} "
              f"IoU={r['iou']:.3f} dep={r['dep_hit']:.2f} P={r['precision']:.2f} R={r['recall']:.2f} "
              f"runoutErr={r['runout_error_m']:+.0f} m")


if __name__ == "__main__":
    main(sys.argv[1])

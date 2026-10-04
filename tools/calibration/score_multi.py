"""Score the run_multi.py grid against every observed event (same logic as score_calib.py, several events).

Footprint = peak flow thickness pft > 0.1 m (ppr > 1 kPa as a second IoU).
Observed reference per event:
  event_area   (Popeletzbach, KleinerOetscherbach): outline of the whole observed avalanche
  deposit_only (Eiskar, Filisur1, Filisur2): deposition outline only, the track is not mapped
Metrics (vs the reference outline `obs`):
  iou             |sim ∩ obs| / |sim ∪ obs|   (deposit_only: low by construction, the track is not in obs)
  recall          |sim ∩ obs| / |obs|          (deposit_only: = dep_hit, share of observed deposit covered)
  precision       |sim ∩ obs| / |sim|
  dep_hit         share of observed deposit cells inside the footprint (Popeletzbach: its deposit outline)
  precision_below_dep_top  deposit_only: share of footprint cells below the top of the deposit that are in it
  runout_error_m  sim - obs runout; runout = max horizontal distance from the release top (highest DEM cell
                  in the release area) over footprint / over obs; > 0 overshoot, < 0 stops short
  Eiskar also vs depositionMaxOutline (dense flow + powder): dep_hit_max, runout_error_max_m
  stopped_by_tEnd the simulation hit tEnd (400 s) instead of the kinetic-energy stop -> not a finished runout
Best per event (grid rows that stopped on their own and stay inside the domain):
  event_area   max IoU (as score_calib.py)
  deposit_only smallest |runout_error_m| among rows with dep_hit >= 0.5; if none, max dep_hit
Usage (Spark): python score_multi.py [out.csv]  -> ~/avalauncher/calib/results.csv, results_best.json
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import shapefile
from rasterio.features import rasterize

CALIB = Path("~/avalauncher/calib").expanduser()
FT_MIN, PPR_MIN, DEP_FLOOR = 0.1, 1.0, 0.5
EVENTS = {
    "avaPopeletzbach": dict(type="event_area", obs="src/eventArea20090407.shp",
                            dep="src/eventDepositionArea20090407.shp", rel="src/releaseArea20090407.shp"),
    "avaKleinerOetscherbach": dict(type="event_area", obs="src/obs_event.tif", rel="src/obs_release.tif"),
    "avaEiskar": dict(type="deposit_only", obs="observed/obs_dfa.tif", obs2="observed/obs_max.tif",
                      rel="observed/rel_esk1.tif"),
    "avaFilisur1": dict(type="deposit_only", obs="obs_deposition.tif", rel="src/release.shp"),
    "avaFilisur2": dict(type="deposit_only", obs="obs/deposition_mask.tif", rel="obs/release_mask.tif"),
}
GROUP = re.compile(r"^(samosATSmall|samosATMedium|samosAT|voellmy_mu\d+)(_th27)?$|^voellmy_th27_mu\d+$")


def load_mask(path: Path, shape, tr) -> np.ndarray:
    if path.suffix == ".shp":
        geoms = [s.__geo_interface__ for s in shapefile.Reader(str(path)).shapes()]
        return rasterize(geoms, out_shape=shape, transform=tr).astype(bool)
    with rasterio.open(path) as r:
        assert r.shape == shape and r.transform.almost_equals(tr), f"grid mismatch {path}"
        return r.read(1) > 0


def end_times(run: Path) -> dict:
    """simName -> time at which com1DFA ended the computation (parsed from the run's own log)."""
    out, cur = {}, None
    for log in run.glob("*.log"):
        for line in log.read_text(errors="ignore").replace("\r", "\n").splitlines():
            m = re.search(r"Run simulation: (\S+)", line)
            if m:
                cur = m.group(1)
            m = re.search(r"Ending computation at time t = ([\d.]+) s", line)
            if m and cur:
                out[cur] = float(m.group(1))
    return out


def score_event(event: str, cfg: dict) -> list[dict]:
    root = CALIB / event
    with rasterio.open(root / "dem.tif") as d:
        dem, tr = d.read(1), d.transform
    shape = dem.shape
    obs = load_mask(root / cfg["obs"], shape, tr)
    dep = load_mask(root / cfg["dep"], shape, tr) if "dep" in cfg else (obs if cfg["type"] == "deposit_only" else None)
    obs2 = load_mask(root / cfg["obs2"], shape, tr) if "obs2" in cfg else None
    rel = load_mask(root / cfg["rel"], shape, tr)
    rr, cc = np.indices(shape)
    xs, ys = tr * (cc + 0.5, rr + 0.5)
    i0 = np.argmax(np.where(rel, dem, -1e9))
    dist = np.hypot(xs - xs.flat[i0], ys - ys.flat[i0])
    obs_run = float(dist[obs].max())
    obs2_run = float(dist[obs2].max()) if obs2 is not None else None
    cell_ha = abs(tr.a * tr.e) / 1e4
    dep_top = float(dem[dep].max()) if dep is not None else None
    rows = []
    for run in sorted((root / "runs").iterdir()) if (root / "runs").exists() else []:
        if not GROUP.match(run.name) or not (run / "simDF.csv").exists():
            continue
        tend = end_times(run)
        df = pd.read_csv(run / "simDF.csv", index_col=0)
        pk = run / "Outputs" / "com1DFA" / "peakFiles"
        for _, s in df.iterrows():
            with rasterio.open(pk / f"{s['simName']}_pft.asc") as r:
                pft = r.read(1)
                assert pft.shape == shape and r.transform.almost_equals(tr), "grid mismatch"
            with rasterio.open(pk / f"{s['simName']}_ppr.asc") as r:
                ppr = r.read(1)
            fp, fpp = pft > FT_MIN, ppr > PPR_MIN
            inter = (fp & obs).sum()
            sim_run = float(dist[fp].max()) if fp.any() else 0.0
            frict = s["frictModel"]
            mu = {"samosATSmall": s.get("musamosatsmall"), "samosATMedium": s.get("musamosatmedium"),
                  "samosAT": s.get("musamosat"), "Voellmy": s.get("muvoellmy")}.get(frict)
            t_end = tend.get(s["simName"])
            row = {
                "event": event, "obs_type": cfg["type"], "group": run.name, "simName": s["simName"],
                "frictModel": frict, "mu": None if mu is None else float(mu),
                "xsi": float(s["xsivoellmy"]) if frict == "Voellmy" else None,
                "relTh": round(float(s["relTh"]), 3),
                "relTh_source": "measured (ESK_1 laser scan)" if "th27" in run.name else "grid",
                "iou": round(float(inter / max((fp | obs).sum(), 1)), 3),
                "iou_ppr1kPa": round(float((fpp & obs).sum() / max((fpp | obs).sum(), 1)), 3),
                "dep_hit": round(float((fp & dep).sum() / dep.sum()), 3) if dep is not None else None,
                "dep_hit_max": round(float((fp & obs2).sum() / obs2.sum()), 3) if obs2 is not None else None,
                "precision": round(float(inter / max(fp.sum(), 1)), 3),
                "precision_below_dep_top": None,
                "recall": round(float(inter / obs.sum()), 3),
                "runout_sim_m": round(sim_run, 1), "runout_obs_m": round(obs_run, 1),
                "runout_error_m": round(sim_run - obs_run, 1),
                "runout_error_max_m": round(sim_run - obs2_run, 1) if obs2 is not None else None,
                "min_elev_sim_m": round(float(dem[fp].min()), 1) if fp.any() else None,
                "min_elev_obs_m": round(float(dem[obs].min()), 1),
                "area_sim_ha": round(float(fp.sum()) * cell_ha, 2), "area_obs_ha": round(float(obs.sum()) * cell_ha, 2),
                "max_pft_m": round(float(pft.max()), 2),
                "t_end_s": t_end, "stopped_by_tEnd": None if t_end is None else bool(t_end >= float(s["tEnd"]) - 0.05),
                "touches_edge": bool(fp[0].any() or fp[-1].any() or fp[:, 0].any() or fp[:, -1].any()),
            }
            if cfg["type"] == "deposit_only":
                low = fp & (dem <= dep_top)
                row["precision_below_dep_top"] = round(float((low & dep).sum() / max(low.sum(), 1)), 3)
            rows.append(row)
    return rows


def pick_best(rows: list[dict]) -> dict | None:
    ok = [r for r in rows if r["stopped_by_tEnd"] is False and not r["touches_edge"]]
    if not ok:
        return None
    if ok[0]["obs_type"] == "event_area":
        return max(ok, key=lambda r: (r["iou"], -abs(r["runout_error_m"])))
    hit = [r for r in ok if r["dep_hit"] >= DEP_FLOOR]
    if hit:
        return min(hit, key=lambda r: (abs(r["runout_error_m"]), -r["dep_hit"]))
    return max(ok, key=lambda r: (r["dep_hit"], -abs(r["runout_error_m"])))


def main(out_name: str = "results.csv") -> None:
    allrows, best = [], {}
    for event, cfg in EVENTS.items():
        rows = score_event(event, cfg)
        allrows += rows
        b = pick_best(rows)
        best[event] = b
        n_t = sum(bool(r["stopped_by_tEnd"]) for r in rows)
        n_e = sum(r["touches_edge"] for r in rows)
        print(f"{event}: {len(rows)} runs, {n_t} hit tEnd, {n_e} touch the domain edge")
        if b:
            print(f"  best {b['frictModel']} mu={b['mu']} xsi={b['xsi']} relTh={b['relTh']} IoU={b['iou']} "
                  f"dep_hit={b['dep_hit']} P={b['precision']} R={b['recall']} runoutErr={b['runout_error_m']:+.0f} m")
    df = pd.DataFrame(allrows)
    df.to_csv(CALIB / out_name, index=False)
    (CALIB / out_name.replace(".csv", "_best.json")).write_text(json.dumps(
        dict(rule={"event_area": "max IoU", "deposit_only": f"min |runout_error_m| with dep_hit >= {DEP_FLOOR}"},
             best=best), indent=1, default=str))
    print(f"{len(df)} rows -> {CALIB / out_name}")


if __name__ == "__main__":
    main(*sys.argv[1:])

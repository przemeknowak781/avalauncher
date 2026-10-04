"""Score the "las_porywanie" grid (run_multi_las.py) exactly as score_multi.py scores round 1.

Same observed references, footprint (pft > 0.1 m; ppr > 1 kPa as a second IoU), metrics, release-top runout
reference, tEnd / domain-edge flags and per-event best rule: the constants and helpers are imported from
score_multi.py, the per-run metric block below is the same code pointed at <event>/runs_las instead of runs.
Added columns:
  variant            las_porywanie
  simType            res | entres (from simDF.csv; the simName ends _res_dfa / _entres_dfa, not _null_dfa)
  res_input, res_source, res_params   the resistance (forest) layer used and the AvaFrame 2.1 defaults applied
  ent_input, ent_th_m, ent_th_source, ent_params   entrainment layer, thickness and its source ('-' if none)
  particles_removed  com1DFA "particles removed" count (zero-mass particles after detrainment are counted too)
Join with round 1 on (event, frictModel, mu, xsi, relTh), not simName.
Usage (Spark): python score_multi_las.py [results_las.csv] -> ~/avalauncher/calib/results_las.csv, results_las_best.json
"""

import json
import re
import sys

import numpy as np
import pandas as pd
import rasterio

from score_multi import CALIB, DEP_FLOOR, EVENTS, FT_MIN, GROUP, PPR_MIN, end_times, load_mask, pick_best

VARIANT = "las_porywanie"
RES_PARAMS = ("AvaFrame 2.1 defaults: ResistanceModel default, cResH 0.01, detrainment True, detK 5, "
              "forestVMin 6, forestVMax 40, forestThMin 0.6, forestThMax 10")
ENT_PARAMS = "AvaFrame 2.1 defaults: rhoEnt 100, entEroEnergy 5000, entShearResistance 0, entDefResistance 0"
DS = "OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552)"
INPUTS = {
    "avaPopeletzbach": dict(
        res_input="forest/forest.shp", ent_input="-", ent_th_m=None,
        res_source=f"dataset: {DS} avaPopeletzbach/forest20090407.shp, byte-identical copy (height >= 10 m)",
        ent_th_source="no entrainment areas in the dataset; run without entrainment as in round 1"),
    "avaKleinerOetscherbach": dict(
        res_input="forest/forest.shp", ent_input="-", ent_th_m=None,
        res_source=f"dataset: {DS} avaKleinerOetscherbach/forest20090225.shp, byte-identical copy (height >= 10 m)",
        ent_th_source="no entrainment areas in the dataset; run without entrainment as in round 1"),
    "avaEiskar": dict(
        res_input="extras/RES/resistance.shp", ent_input="extras/ENT/entrainment.shp", ent_th_m=0.3,
        res_source=f"dataset: {DS} avaEiskar/resistanceEvent20190115.gpkg -> shp (4 polygons, same geometry)",
        ent_th_source=("AvaFrame 2.1 default entThIfMissingInShp 0.3 m: entrainmentEvent20190115.gpkg has no "
                       "thickness attribute and the WLV report gives none")),
    "avaFilisur1": dict(
        res_input="forest/forest.shp", ent_input="-", ent_th_m=None,
        res_source=f"dataset: {DS} avaFilisur1/avaFilisur1_forest_area.gpkg -> shp (14 polygons, same geometry; "
                   "dense/open class not used by the default model)",
        ent_th_source="no entrainment areas in the dataset; run without entrainment as in round 1"),
    "avaFilisur2": dict(
        res_input="forest_las/forest.shp", ent_input="-", ent_th_m=None,
        res_source=f"dataset: {DS} avaFilisur2/avaFiisur2_forest_area.gpkg -> shp; 11 touching dense/open polygons "
                   "dissolved into 4 disjoint parts, same area (AvaFrame rejects features sharing cells)",
        ent_th_source="no entrainment areas in the dataset; run without entrainment as in round 1"),
}


def removed_counts(run) -> dict:
    """simName -> number of particles com1DFA reports as removed (parsed from the run's own log)."""
    out, cur = {}, None
    for log in run.glob("*.log"):
        for line in log.read_text(errors="ignore").replace("\r", "\n").splitlines():
            m = re.search(r"Run simulation: (\S+)", line)
            if m:
                cur = m.group(1)
            m = re.search(r"(\d+) particles have been removed during simulation", line)
            if m and cur:
                out[cur] = int(m.group(1))
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
    runs = root / "runs_las"
    for run in sorted(runs.iterdir()) if runs.exists() else []:
        if not GROUP.match(run.name) or not (run / "simDF.csv").exists():
            continue
        tend, nrem = end_times(run), removed_counts(run)
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
            inp = INPUTS[event]
            row.update({
                "variant": VARIANT, "simType": s["simTypeActual"] if "simTypeActual" in s else s.get("simType"),
                "res_input": inp["res_input"], "res_source": inp["res_source"], "res_params": RES_PARAMS,
                "ent_input": inp["ent_input"], "ent_th_m": inp["ent_th_m"], "ent_th_source": inp["ent_th_source"],
                "ent_params": ENT_PARAMS if inp["ent_input"] != "-" else "-",
                "particles_removed": nrem.get(s["simName"], 0),
            })
            exp = "entres" if inp["ent_input"] != "-" else "res"
            assert row["simType"] == exp and s["simName"].endswith(f"_{exp}_dfa"), (s["simName"], row["simType"])
            rows.append(row)
    return rows


def main(out_name: str = "results_las.csv") -> None:
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
        dict(variant=VARIANT,
             rule={"event_area": "max IoU", "deposit_only": f"min |runout_error_m| with dep_hit >= {DEP_FLOOR}"},
             best=best), indent=1, default=str))
    print(f"{len(df)} rows -> {CALIB / out_name}")


if __name__ == "__main__":
    main(*sys.argv[1:])

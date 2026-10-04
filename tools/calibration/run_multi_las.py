"""Variant "las_porywanie": the round-1 grid (run_multi.py) again, now with each event's own forest / entrainment data.

Same events, same friction grid, same thickness rule as run_multi.py:
  samosATSmall / samosATMedium / samosAT  x  release thickness 0.4-2.0 m step 0.2
  Voellmy mu in {0.15, 0.25, 0.35, 0.45} x xi in {1000, 2000, 4000, 8000} at 1.2 m
  avaEiskar also: the three samosAT calibrations and the Voellmy block at the measured 2.7 m.
Added (pre-registered, AvaFrame 2.1 defaults for every resistance/entrainment parameter):
  avaPopeletzbach         simType res     RES = forest/ (dataset forest20090407.shp, unchanged copy)
  avaKleinerOetscherbach  simType res     RES = forest/ (dataset forest20090225.shp, unchanged copy)
  avaEiskar               simType entres  RES = extras/RES (dataset resistanceEvent20190115.gpkg -> shp)
                                          ENT = extras/ENT (dataset entrainmentEvent20190115.gpkg -> shp; no
                                          thickness in the data -> AvaFrame default entThIfMissingInShp 0.3 m)
  avaFilisur1             simType res     RES = forest/ (dataset avaFilisur1_forest_area.gpkg -> shp)
  avaFilisur2             simType res     RES = forest_las/ (dataset avaFiisur2_forest_area.gpkg -> shp, touching
                                          dense/open polygons dissolved into 4 disjoint parts, same area; AvaFrame
                                          rejects features sharing cells; events/avaFilisur2/forest_las.py)
No event has a derived (non-dataset) layer. Only Eiskar has entrainment areas in the dataset.

--split cuts the samosAT thickness grids into one process per thickness (job name <group>__th<relTh>), so the long
Eiskar entrainment runs spread over the workers; the simulations are the same (fixed seed), only the wall time differs.
Usage (Spark): python run_multi_las.py [--jobs N] [--only EVENT[,EVENT]] [--split EVENT[,EVENT]|all] [--dry]
Runs go to <eventRoot>/runs_las/<job>, logs to <eventRoot>/logs_las/<job>.log, records to
~/avalauncher/calib/jobs_multi_las.json. Round-1 runs/ and logs/ are not touched.
"""

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CALIB = Path("~/avalauncher/calib").expanduser()
PY = str(Path("~/avalauncher/.venv/bin/python").expanduser())
RUN = str(CALIB / "tools" / "run_calib_las.py")
LOAD_MAX = 18.0
EVENTS = ["avaEiskar", "avaKleinerOetscherbach", "avaPopeletzbach", "avaFilisur1", "avaFilisur2"]  # slowest first
SAMOS = ["samosATSmall", "samosATMedium", "samosAT"]
MUS = ["0.15", "0.25", "0.35", "0.45"]
XIS = "1000|2000|4000|8000"
GRID_TH = [f"{0.4 + 0.2 * i:.1f}" for i in range(9)]  # 0.4 .. 2.0, = relTh 1.2 with relThRangeVariation 0.8$9
INPUTS = {  # simType, RES dir, ENT dir (relative to the event root)
    "avaPopeletzbach": ("res", "forest", "-"),
    "avaKleinerOetscherbach": ("res", "forest", "-"),
    "avaEiskar": ("entres", "extras/RES", "extras/ENT"),
    "avaFilisur1": ("res", "forest", "-"),
    "avaFilisur2": ("res", "forest_las", "-"),
}


def jobs_for(event: str, split: bool) -> list[dict]:
    root = str(CALIB / event)
    st, res, ent = INPUTS[event]
    base = dict(event=event, root=root, simType=st, res=res, ent=ent)
    jobs = []
    if event == "avaEiskar":  # measured thickness first: these are the longest runs
        jobs += [dict(base, name=f"voellmy_th27_mu{m.replace('.', '')}", frict="Voellmy", relTh="2.7", var="",
                      extra=[f"muvoellmy={m}", f"xsivoellmy={XIS}"]) for m in MUS]
        jobs += [dict(base, name=f"{f}_th27", frict=f, relTh="2.7", var="", extra=[]) for f in SAMOS]
    if split:
        jobs += [dict(base, name=f"{f}__th{t.replace('.', '')}", frict=f, relTh=t, var="", extra=[])
                 for f in SAMOS for t in GRID_TH]
    else:
        jobs += [dict(base, name=f, frict=f, relTh="1.2", var="0.8$9", extra=[]) for f in SAMOS]
    jobs += [dict(base, name=f"voellmy_mu{m.replace('.', '')}", frict="Voellmy", relTh="1.2", var="",
                  extra=[f"muvoellmy={m}", f"xsivoellmy={XIS}"]) for m in MUS]
    return jobs


def main() -> None:
    args = sys.argv[1:]
    n = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 10
    assert n <= 12, "at most 12 processes on the shared Spark"
    only = args[args.index("--only") + 1].split(",") if "--only" in args else EVENTS
    split = args[args.index("--split") + 1].split(",") if "--split" in args else []
    jobs = [j for e in EVENTS if e in only for j in jobs_for(e, "all" in split or e in split)]
    if "--dry" in args:
        for j in jobs:
            print(j)
        print(len(jobs), "jobs")
        return
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               NUMBA_NUM_THREADS="1", MPLBACKEND="Agg")
    gate = threading.Lock()
    rec_path = CALIB / ("jobs_multi_las.json" if only == EVENTS else f"jobs_multi_las_{'_'.join(only)}.json")
    t_start = time.time()

    def run(job: dict) -> dict:
        with gate:  # wait for headroom, then space launches so the load average can follow
            while os.getloadavg()[0] > LOAD_MAX:
                time.sleep(5)
            time.sleep(1)
        log = Path(job["root"]) / "logs_las" / f"{job['name']}.log"
        log.parent.mkdir(exist_ok=True)
        t0 = time.time()
        cmd = [PY, RUN, job["root"], job["name"], job["frict"], job["relTh"], job["var"], job["simType"],
               job["res"], job["ent"], *job["extra"]]
        with open(log, "w") as fh:
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env).returncode
        out = dict(job, rc=rc, start=round(t0 - t_start, 1), wall_s=round(time.time() - t0, 1))
        print(f"{job['event']:24s} {job['name']:22s} {job['simType']:6s} rc={rc} {out['wall_s']:7.1f} s  "
              f"load={os.getloadavg()[0]:.1f}", flush=True)
        return out

    with ThreadPoolExecutor(max_workers=n) as ex:
        res = list(ex.map(run, jobs))
    rec = dict(started=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_start)),
               wall_min=round((time.time() - t_start) / 60, 2), workers=n, split=split, jobs=res)
    rec_path.write_text(json.dumps(rec, indent=1))
    bad = [r["name"] for r in res if r["rc"]]
    print(f"done: {len(res)} jobs, {len(bad)} failed {bad}, wall {rec['wall_min']} min", flush=True)


if __name__ == "__main__":
    main()

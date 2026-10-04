"""Calibration grid over several observed events: one run_calib.py process per (event, friction group).

Grid per event (AvaFrame com1DFA 2.1, mesh 5 m, no forest, no entrainment, tEnd 400 s default, peak files only):
  samosATSmall / samosATMedium / samosAT  x  release thickness 0.4-2.0 m step 0.2  (relTh 1.2, relThRangeVariation 0.8$9)
  Voellmy mu in {0.15, 0.25, 0.35, 0.45} x xi in {1000, 2000, 4000, 8000} at the grid mid thickness 1.2 m
  avaEiskar only (the one event with a measured thickness, 2.7 m for ESK_1): the three samosAT calibrations
  and the Voellmy block again at 2.7 m.

Usage (Spark): python run_multi.py [--jobs N] [--only EVENT[,EVENT]] [--dry]
Each job logs to <eventRoot>/logs/<group>.log; job records go to ~/avalauncher/calib/jobs_multi.json.
Jobs start only while the 1-min load average is below LOAD_MAX (other workflows share the machine).
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
RUN_CALIB = str(CALIB / "tools" / "run_calib.py")
LOAD_MAX = 18.0
EVENTS = ["avaEiskar", "avaKleinerOetscherbach", "avaPopeletzbach", "avaFilisur1", "avaFilisur2"]  # slowest first
SAMOS = ["samosATSmall", "samosATMedium", "samosAT"]
MUS = ["0.15", "0.25", "0.35", "0.45"]
XIS = "1000|2000|4000|8000"


def jobs_for(event: str) -> list[dict]:
    root = str(CALIB / event)
    jobs = []
    if event == "avaEiskar":  # measured thickness first: these are the longest runs
        jobs += [dict(event=event, root=root, name=f"voellmy_th27_mu{m.replace('.', '')}", frict="Voellmy",
                      relTh="2.7", var="", extra=[f"muvoellmy={m}", f"xsivoellmy={XIS}"]) for m in MUS]
        jobs += [dict(event=event, root=root, name=f"{f}_th27", frict=f, relTh="2.7", var="", extra=[])
                 for f in SAMOS]
    jobs += [dict(event=event, root=root, name=f, frict=f, relTh="1.2", var="0.8$9", extra=[]) for f in SAMOS]
    jobs += [dict(event=event, root=root, name=f"voellmy_mu{m.replace('.', '')}", frict="Voellmy",
                  relTh="1.2", var="", extra=[f"muvoellmy={m}", f"xsivoellmy={XIS}"]) for m in MUS]
    return jobs


def main() -> None:
    args = sys.argv[1:]
    n = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 10
    only = args[args.index("--only") + 1].split(",") if "--only" in args else EVENTS
    jobs = [j for e in EVENTS if e in only for j in jobs_for(e)]
    if "--dry" in args:
        for j in jobs:
            print(j)
        print(len(jobs), "jobs")
        return
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               NUMBA_NUM_THREADS="1", MPLBACKEND="Agg")
    gate = threading.Lock()
    rec_path = CALIB / ("jobs_multi.json" if only == EVENTS else f"jobs_multi_{'_'.join(only)}.json")
    t_start = time.time()

    def run(job: dict) -> dict:
        with gate:  # wait for headroom, then space launches so the load average can follow
            while os.getloadavg()[0] > LOAD_MAX:
                time.sleep(5)
            time.sleep(1)
        log = Path(job["root"]) / "logs" / f"{job['name']}.log"
        log.parent.mkdir(exist_ok=True)
        t0 = time.time()
        cmd = [PY, RUN_CALIB, job["root"], job["name"], job["frict"], job["relTh"], job["var"], *job["extra"]]
        with open(log, "w") as fh:
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env).returncode
        out = dict(job, rc=rc, start=round(t0 - t_start, 1), wall_s=round(time.time() - t0, 1))
        print(f"{job['event']:24s} {job['name']:22s} rc={rc} {out['wall_s']:7.1f} s  load={os.getloadavg()[0]:.1f}",
              flush=True)
        return out

    with ThreadPoolExecutor(max_workers=n) as ex:
        res = list(ex.map(run, jobs))
    rec = dict(started=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_start)),
               wall_min=round((time.time() - t_start) / 60, 2), workers=n, jobs=res)
    rec_path.write_text(json.dumps(rec, indent=1))
    bad = [r["name"] for r in res if r["rc"]]
    print(f"done: {len(res)} jobs, {len(bad)} failed {bad}, wall {rec['wall_min']} min", flush=True)


if __name__ == "__main__":
    main()

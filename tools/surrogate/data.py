"""Collect AvaFrame com1DFA peak flow thickness maps into one training cache.

Runs on the Spark. Scans run directories for Outputs/com1DFA/peakFiles/*_pft.asc, reads relTh and
frictModel from configurationFiles/<simName>.ini and works out the release sector from the run or
simulation name (S\\d\\d), falling back to the sector mask the footprint covers best.

Usage: python data.py <out.npz> <assetsDir> <sectors_u8.bin> <root> [<root> ...]
"""

import json
import re
import sys
from configparser import ConfigParser
from multiprocessing import Pool
from pathlib import Path

import numpy as np

H = W = 400
FRICT = ["samosATSmall", "samosATMedium", "samosAT"]


def read_asc(p):
    tok = Path(p).read_bytes().split()
    a = np.array(tok[12:], dtype=np.float32).reshape(H, W)  # rows from north, as in terrain_f32.bin
    return np.nan_to_num(a, nan=0.0)


def run_time(run_dir):
    """Wall time per simulation from the AvaFrame log (nCPU = 1, sims run one after another)."""
    out = []
    for log in run_dir.glob("*.log"):
        txt = log.read_text(errors="ignore")
        tot = [float(x) for x in re.findall(r"Overall \(parallel\) com1DFA computation took: ([\d.]+) s", txt)]
        cpu = [float(x) for x in re.findall(r"cpu time DFA = ([\d.]+) s", txt)]
        if tot and cpu:
            out.append(sum(tot) / len(cpu))
    return out


def job(args):
    try:
        return _job(*args)
    except Exception as e:  # run still being written, or broken file
        print("skip", args[0], e, flush=True)
        return None


def _job(p, sector_hint):
    p = Path(p)
    sim = p.name[:-len("_pft.asc")]
    cfg_dir = p.parents[1] / "configurationFiles"
    cp = ConfigParser()
    cp.read(cfg_dir / f"{sim}.ini")
    g = cp["GENERAL"]
    return dict(path=str(p), sim=sim, relTh=round(float(g["relTh"]), 3), frict=g["frictModel"],
                sector=sector_hint, pft=read_asc(p).astype(np.float16))


def main(out, assets, sec_bin, roots):
    sectors = json.loads((Path(assets) / "sectors.json").read_text(encoding="utf-8"))
    by_index = {s["index"]: s["id"] for s in sectors}
    idx = np.fromfile(sec_bin, dtype=np.uint8).reshape(H, W)
    jobs, times = [], []
    seen_runs = set()
    for root in roots:
        for p in sorted(Path(root).rglob("Outputs/com1DFA/peakFiles/*_pft.asc")):
            run_dir = p.parents[3]
            hint = None
            for name in (p.name, run_dir.name, run_dir.parent.name):
                m = re.search(r"(?<![A-Za-z0-9])(S\d\d)(?!\d)", name)
                if m:
                    hint = m.group(1)
                    break
            jobs.append((str(p), hint))
            if run_dir not in seen_runs:
                seen_runs.add(run_dir)
                times += run_time(run_dir)
    print(f"{len(jobs)} pft files in {len(seen_runs)} run dirs", flush=True)
    with Pool(2) as pool:
        recs = pool.map(job, jobs, chunksize=8)
    keep = []
    for r in recs:
        if r is None or r["frict"] not in FRICT:
            continue
        fp = r["pft"] > 0.1
        if r["sector"] is None:  # sector whose release cells the footprint covers best
            cov = {i: (fp & (idx == i)).sum() / max(1, (idx == i).sum()) for i in by_index}
            r["sector"] = by_index[max(cov, key=cov.get)]
        if fp.sum() < 10:
            continue
        keep.append(r)
    print(f"kept {len(keep)} sims, sectors: {sorted(set(r['sector'] for r in keep))}", flush=True)
    np.savez(out,
             pft=np.stack([r["pft"] for r in keep]),
             relTh=np.array([r["relTh"] for r in keep], np.float32),
             frict=np.array([FRICT.index(r["frict"]) for r in keep], np.int64),
             sector=np.array([r["sector"] for r in keep]),
             sim=np.array([r["sim"] for r in keep]),
             path=np.array([r["path"] for r in keep]),
             s_per_run=np.array(times, np.float32))
    if times:
        print(f"AvaFrame wall time per sim: median {np.median(times):.2f} s over {len(times)} logs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])

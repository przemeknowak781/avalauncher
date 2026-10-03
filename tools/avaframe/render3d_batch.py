"""Render 3D MP4s for the sweep: every sector at 1.3 m / medium friction, plus the biggest case per sector.

Usage: python render3d_batch.py <runsDir> <assetsDir> <outDir> [workers]
"""

import json
import sys
from configparser import ConfigParser
from multiprocessing import Pool
from pathlib import Path

import render3d as r3

FRICT_PL = {"samosATSmall": "tarcie dla małych lawin", "samosATMedium": "tarcie dla średnich lawin", "samosAT": "tarcie dla dużych lawin"}


def sims(run_dir):
    out = {}
    ts = run_dir / "Outputs" / "com1DFA" / "peakFiles" / "timeSteps"
    for t, p in r3.steps_from(ts):
        sim = p.name.split("_FT_t")[0]
        out.setdefault(sim, []).append((t, p))
    meta = {}
    for sim in out:
        cp = ConfigParser()
        cp.read(run_dir / "Outputs" / "com1DFA" / "configurationFiles" / f"{sim}.ini")
        meta[sim] = (round(float(cp["GENERAL"]["relTh"]), 1), cp["GENERAL"]["frictModel"])
    return out, meta


def job(args):
    assets, steps, out, title, sub = args
    r3.render(assets, steps, out, title, sub)
    return out


def main(runs, assets, out, workers=8):
    runs, out = Path(runs), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    names = {s["id"]: s["name"] for s in json.loads((Path(assets) / "sectors.json").read_text(encoding="utf-8"))}
    jobs = []
    for sector in sorted({p.name.split("_")[0] for p in runs.iterdir()}):
        for frict, th in (("samosATMedium", 1.3), ("samosAT", 2.0)):
            steps, meta = sims(runs / f"{sector}_{frict}")
            sim = next(s for s, (t, f) in meta.items() if t == th)
            title = f"Lawina: {names[sector]}"
            sub = f"AvaFrame com1DFA na terenie GUGiK NMT · płyta {th:.1f} m · {FRICT_PL[frict]}".replace(".", ",")
            jobs.append((assets, steps[sim], str(out / f"3d_{sector}_{frict}_{th:.1f}.mp4"), title, sub))
    with Pool(int(workers)) as pool:
        for o in pool.imap_unordered(job, jobs):
            print("3d", o, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

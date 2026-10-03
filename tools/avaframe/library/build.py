"""Build and run the scenario library on Spark.

Selects sectors whose release cells are >= 8 cells from the grid edge and lie within 800 m of a trail,
prepares one avalanche dir per (sector, friction) under <lib>/runs/<sector>_<frict>, then runs
run_one.py in a pool of N processes (nice 10). Progress goes to <lib>/progress.log.

Usage: python build.py <lib_dir> <web_data_dir> [nproc=12] [--prepare-only]
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import shapefile
from scipy.ndimage import distance_transform_edt
from shapely.geometry import box
from shapely.ops import unary_union

W = H = 400
FRICTS = ["samosATSmall", "samosATMedium", "samosAT"]
PRJ_2180 = ('PROJCS["ETRF2000-PL / CS92",GEOGCS["ETRF2000-PL",DATUM["ETRF2000_Poland",SPHEROID["GRS 1980",'
            '6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
            'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",19],'
            'PARAMETER["scale_factor",0.9993],PARAMETER["false_easting",500000],PARAMETER["false_northing",-5300000],'
            'UNIT["metre",1]]')


def select(web: Path, idx: np.ndarray, sectors: list) -> list:
    trails = json.loads((web / "trails.json").read_text(encoding="utf-8"))
    m = np.zeros((H, W), bool)
    for t in trails:
        for p in t["paths"]:
            p = np.array(p, float)
            for a, b in zip(p[:-1], p[1:]):
                n = max(1, int(np.ceil(np.hypot(*(b - a)) / 0.25)))
                q = np.floor(a + (b - a) * (np.arange(n + 1)[:, None] / n)).astype(int)
                q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
                m[q[:, 1], q[:, 0]] = True
    d = distance_transform_edt(~m) * 10
    out = []
    for s in sectors:
        r, c = np.nonzero(idx == s["index"])
        if len(r) and min(r.min(), c.min(), H - 1 - r.max(), W - 1 - c.max()) >= 8 and d[r, c].min() <= 800:
            out.append((s, len(r)))
    return out


def prepare(lib: Path, web: Path) -> list:
    t = json.loads((web / "terrain.json").read_text(encoding="utf-8"))
    sectors = json.loads((web / "sectors.json").read_text(encoding="utf-8"))
    cell, e0, n0 = t["cell_m"], t["e0"], t["n0"]
    z = np.fromfile(web / "terrain_f32.bin", dtype="<f4").reshape(H, W)
    idx = np.fromfile(web / "sectors_u8.bin", dtype=np.uint8).reshape(H, W)
    base = lib / "base"
    base.mkdir(parents=True, exist_ok=True)
    dem = base / "DEM.asc"
    with open(dem, "w", encoding="ascii") as f:
        f.write(f"ncols {W}\nnrows {H}\nxllcorner {e0}\nyllcorner {n0 - H * cell}\n"
                f"cellsize {cell}\nNODATA_value -9999\n")
        np.savetxt(f, z, fmt="%.2f")
    (base / "DEM.prj").write_text(PRJ_2180)
    sel = select(web, idx, sectors)
    jobs = []
    for s, ncell in sel:
        rows, cols = np.nonzero(idx == s["index"])
        poly = unary_union([box(e0 + c * cell, n0 - (r + 1) * cell, e0 + (c + 1) * cell, n0 - r * cell)
                            for r, c in zip(rows, cols)]).buffer(0)
        poly = max(getattr(poly, "geoms", [poly]), key=lambda p: p.area)
        ring = list(poly.exterior.coords)
        if not shapefile.signed_area(ring) < 0:
            ring.reverse()
        for fr in FRICTS:
            ava = lib / "runs" / f"{s['id']}_{fr}"
            (ava / "Inputs" / "REL").mkdir(parents=True, exist_ok=True)
            for name in ("DEM.asc", "DEM.prj"):
                tgt = ava / "Inputs" / name
                if not tgt.exists():
                    os.link(base / name, tgt)
            w = shapefile.Writer(str(ava / "Inputs" / "REL" / "rel"), shapeType=shapefile.POLYGON)
            w.field("name", "C", size=40)
            w.field("thickness", "N", decimal=2)
            w.poly([ring])
            w.record(s["id"], 1.0)
            w.close()
            (ava / "Inputs" / "REL" / "rel.prj").write_text(PRJ_2180)
            jobs.append((ncell, str(ava), fr))
    jobs.sort(key=lambda j: -j[0])  # biggest releases first
    print(f"sectors={len(sel)} dirs={len(jobs)}: {' '.join(s['id'] for s, _ in sel)}", flush=True)
    return jobs


def main(lib: str, web: str, nproc: int = 12, prepare_only: bool = False) -> None:
    lib, web = Path(lib).resolve(), Path(web).resolve()
    jobs = prepare(lib, web)
    if prepare_only:
        return
    py, run_one = sys.executable, str(Path(__file__).with_name("run_one.py"))
    prog = open(lib / "progress.log", "a", buffering=1)
    t0 = time.time()
    prog.write(f"START {time.ctime()} dirs={len(jobs)} nproc={nproc}\n")

    def work(job):
        _, ava, fr = job
        t = time.time()
        with open(Path(ava) / "run.log", "w") as log:
            rc = subprocess.run(["nice", "-n", "10", py, run_one, ava, fr], stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL).returncode
        prog.write(f"{'OK' if rc == 0 else 'FAIL'} {Path(ava).name} rc={rc} {time.time() - t:.0f}s "
                   f"elapsed={(time.time() - t0) / 60:.1f}min\n")
        return rc

    with ThreadPoolExecutor(nproc) as ex:
        rcs = list(ex.map(work, jobs))
    prog.write(f"DONE {time.ctime()} wall={(time.time() - t0) / 60:.1f}min ok={rcs.count(0)} "
               f"fail={len(rcs) - rcs.count(0)}\n")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0], a[1], int(a[2]) if len(a) > 2 else 12, "--prepare-only" in sys.argv)

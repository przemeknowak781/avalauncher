"""Export AvaFrame com1DFA peak results into the web scenario-library contract.

Runs on Spark (or anywhere with the run dirs). Each run dir is named <sector>_<frictModel>
and holds Outputs/com1DFA/{peakFiles,configurationFiles}.

Usage: python export.py <runs_root> <web_data_dir> <out_dir> [computed_on] [nproc]
Writes out_dir/{scenarios.json, scenario_cells.bin, library_heat.bin}.
"""

import configparser
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

THR = 0.1
W = H = 400
CELL = 10


def read_asc(p: Path) -> np.ndarray:
    with open(p, "r", encoding="ascii") as f:
        lines = f.read().split("\n", 6)
    a = np.array(lines[6].split(), dtype=np.float32).reshape(H, W)
    return np.nan_to_num(a, nan=0.0)


def find_runs(root: Path):
    out = []
    for d in sorted(root.iterdir()):
        cf = d / "Outputs" / "com1DFA" / "configurationFiles"
        if not cf.is_dir():
            continue
        sector = d.name.split("_")[0]
        for ini in sorted(cf.glob("*.ini")):
            if ini.name.startswith("sourceConfiguration"):
                continue
            pft = d / "Outputs" / "com1DFA" / "peakFiles" / (ini.stem + "_pft.asc")
            if not pft.exists():
                continue
            cp = configparser.ConfigParser()
            cp.read(ini)
            g = cp["GENERAL"]
            out.append((sector, float(g["relTh"]), g["frictModel"], str(pft)))
    return out


_CTX = {}


def _init(ctx):
    _CTX.update(ctx)


def process(job):
    try:
        return _process(job)
    except Exception as e:  # e.g. file still being written
        print("skip", job[3], e, flush=True)
        return None


def _process(job):
    sector, relth, frict, pft_path = job
    pft = read_asc(Path(pft_path))
    ppr_p = Path(pft_path.replace("_pft.asc", "_ppr.asc"))
    pfv_p = Path(pft_path.replace("_pft.asc", "_pfv.asc"))
    fp = pft > THR
    cells = np.flatnonzero(fp).astype("<u4")
    # 1-cell buffer (3x3 max) for trail hits
    m = np.pad(pft, 1)
    mx = np.max(np.stack([m[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]
                          for dr in (-1, 0, 1) for dc in (-1, 0, 1)]), axis=0)
    hits, hits_pft, tmax = [], [], 0.0
    for seg_id, idx in _CTX["segs"]:
        v = float(mx.flat[idx].max())
        tmax = max(tmax, v)
        if v > THR:
            hits.append(seg_id)
            hits_pft.append(round(v, 2))
    top_c, top_r = _CTX["tops"][sector]
    runout = 0.0
    if cells.size:
        r, c = np.divmod(cells.astype(np.int64), W)
        runout = float(np.sqrt(((r + 0.5 - top_r) ** 2 + (c + 0.5 - top_c) ** 2).max()) * CELL)
        own = float(np.mean(fp[_CTX["sec_idx"] == _CTX["sec_index"][sector]]))  # share of release sector covered
    else:
        own = 0.0
    rec = {"id": f"{sector}_{frict}_{relth:.1f}", "sector": sector, "relTh": round(relth, 2), "frict": frict,
           "runout_m": round(runout), "area_ha": round(cells.size * CELL * CELL / 1e4, 2),
           "max_pft_m": round(float(pft.max()), 2), "hits": hits, "hits_pft_m": hits_pft,
           "trail_pft_max_m": round(tmax, 2)}
    if ppr_p.exists():
        rec["max_ppr_kpa"] = round(float(read_asc(ppr_p).max()), 1)
    if pfv_p.exists():
        rec["max_pfv_ms"] = round(float(read_asc(pfv_p).max()), 1)
    return rec, cells, own


def main(runs_root, web, out, computed_on="DGX Spark (GB10)", nproc=12):
    runs_root, web, out = Path(runs_root), Path(web), Path(out)
    sectors = json.loads((web / "sectors.json").read_text(encoding="utf-8"))
    trails = json.loads((web / "trails.json").read_text(encoding="utf-8"))
    sec_idx = np.fromfile(web / "sectors_u8.bin", dtype=np.uint8).reshape(H, W)
    segs = []
    for t in trails:
        for s in t["segments"]:
            pts = np.array(t["paths"][s["part"]][s["from"]:s["to"] + 1], dtype=float)
            dense = [pts[0]]
            for a, b in zip(pts[:-1], pts[1:]):
                n = max(1, int(np.ceil(np.hypot(*(b - a)) / 0.25)))
                dense.extend(a + (b - a) * k / n for k in range(1, n + 1))
            d = np.floor(np.array(dense)).astype(int)
            ok = (d[:, 0] >= 0) & (d[:, 0] < W) & (d[:, 1] >= 0) & (d[:, 1] < H)
            d = d[ok]
            if len(d):
                segs.append((s["id"], np.unique(d[:, 1] * W + d[:, 0])))
    ctx = {"segs": segs, "sec_idx": sec_idx,
           "tops": {s["id"]: (s["top_cell"][0] + 0.5, s["top_cell"][1] + 0.5) for s in sectors},
           "sec_index": {s["id"]: s["index"] for s in sectors}}
    jobs = find_runs(runs_root)
    order = {"samosATSmall": 0, "samosATMedium": 1, "samosAT": 2}
    jobs.sort(key=lambda j: (int(j[0][1:]), order.get(j[2], 9), j[1]))
    with Pool(int(nproc), initializer=_init, initargs=(ctx,)) as pool:
        res = pool.map(process, jobs, chunksize=4)
    jobs = [j for j, r in zip(jobs, res) if r is not None]
    res = [r for r in res if r is not None]
    runs, chunks, heat, off = [], [], np.zeros(H * W, dtype=np.uint32), 0
    owns = []
    for rec, cells, own in res:
        rec["cells_offset"], rec["cells_count"] = off, int(cells.size)
        off += cells.size
        chunks.append(cells)
        heat[cells] += 1
        runs.append(rec)
        owns.append(own)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "index.csv", "w", encoding="utf-8") as f:  # run id -> raw pft path (for SURR / VIS)
        f.write("id,sector,relTh,frict,pft_path\n")
        for rec, job in zip(runs, jobs):
            f.write(f"{rec['id']},{rec['sector']},{rec['relTh']},{rec['frict']},{job[3]}\n")
    (np.concatenate(chunks) if chunks else np.zeros(0, "<u4")).astype("<u4").tofile(out / "scenario_cells.bin")
    np.minimum(heat, 65535).astype("<u2").tofile(out / "library_heat.bin")
    doc = {"count": len(runs), "model": "AvaFrame com1DFA 2.1", "computed_on": computed_on,
           "cell_m": CELL, "width": W, "height": H, "threshold_pft_m": THR,
           "thicknesses": sorted({r["relTh"] for r in runs}),
           "frictions": [f for f in order if any(r["frict"] == f for r in runs)],
           "sectors": sorted({r["sector"] for r in runs}, key=lambda s: int(s[1:])),
           "runs": runs}
    (out / "scenarios.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    nz = [o for o, r in zip(owns, runs) if r["cells_count"]]
    print(f"runs={len(runs)} cells={off} hitting={sum(1 for r in runs if r['hits'])} "
          f"own-sector overlap: min={min(nz):.2f} mean={np.mean(nz):.2f}" if nz else "no footprints")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], *(a[3:5]))

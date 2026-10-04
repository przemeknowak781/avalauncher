"""Smoke check of the avaFilisur2 avalanche dir on the Spark: one com1DFA run, then a plain overlap count.

Usage (on Spark): python smoke_filisur2.py ~/avalauncher/calib/avaFilisur2 [frictModel] [relTh] [tEnd]
Copies <ava>/Inputs to <ava>/runs/smoke/, runs com1DFA (nCPU 1), and prints for the footprint pft > 0.1 m:
cells, fraction of observed deposition cells inside it, and the lowest footprint elevation.
"""

import shutil
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, logUtils


def main(ava_dir: str, frict: str = "samosATMedium", relth: str = "1.0", tend: str = "300") -> None:
    root = Path(ava_dir).expanduser()
    run = root / "runs" / "smoke"
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)
    shutil.copytree(root / "Inputs", run / "Inputs")
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = str(run)
    cfg_main["MAIN"]["nCPU"] = "1"
    logUtils.initiateLogger(str(run), "smoke")
    cfg = cfgUtils.getModuleConfig(com1DFA, str(run), toPrint=False)
    cfg["GENERAL"].update({"relThFromFile": "False", "relTh": relth, "relThRangeVariation": "",
                           "meshCellSize": "5", "simTypeList": "null", "frictModel": frict,
                           "tEnd": tend, "resType": "ppr|pft|pfv|timeInfo"})
    t0 = time.perf_counter()
    com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    dt = time.perf_counter() - t0
    pk = sorted((run / "Outputs" / "com1DFA" / "peakFiles").glob("*_pft.asc"))
    assert pk, "no pft peak file"
    with rasterio.open(pk[0]) as r:
        pft = r.read(1)
    with rasterio.open(root / "obs" / "deposition_mask.tif") as r:
        dep = r.read(1) > 0
    with rasterio.open(root / "dem.tif") as r:
        dem = r.read(1)
    assert pft.shape == dep.shape, (pft.shape, dep.shape)
    fp = pft > 0.1
    print(f"smoke {frict} relTh={relth} tEnd={tend}: {dt:.1f} s, {pk[0].name}")
    print(f"footprint cells {int(fp.sum())}, observed deposition cells {int(dep.sum())}, "
          f"deposition inside footprint {(fp & dep).sum() / dep.sum():.3f}, "
          f"IoU {(fp & dep).sum() / max((fp | dep).sum(), 1):.3f}, "
          f"lowest footprint z {float(dem[fp].min()):.0f} m, observed lowest z {float(dem[dep].min()):.0f} m, "
          f"footprint touches domain edge {bool(fp[0].any() or fp[-1].any() or fp[:, 0].any() or fp[:, -1].any())}")


if __name__ == "__main__":
    main(*sys.argv[1:])

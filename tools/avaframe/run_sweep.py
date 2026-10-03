"""One avalanche dir, one friction calibration, three release thicknesses (0.6 / 1.3 / 2.0 m).
Saves flow thickness every 1 s for animation. Run many of these in parallel (one per process).

Usage: python run_sweep.py <avalancheDir> <frictModel>   (samosATSmall | samosATMedium | samosAT)
"""

import sys
import time

from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, initializeProject, logUtils


def main(ava: str, frict: str) -> None:
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = ava
    cfg_main["MAIN"]["nCPU"] = "1"
    initializeProject.cleanSingleAvaDir(ava, deleteOutput=True)
    logUtils.initiateLogger(ava, "sweep")
    cfg = cfgUtils.getModuleConfig(com1DFA, ava, toPrint=False)
    g = cfg["GENERAL"]
    g.update({"relThFromFile": "False", "relTh": "1.3", "relThRangeVariation": "0.7$3",
              "meshCellSize": "10", "tEnd": "240", "simTypeList": "null", "frictModel": frict,
              "resType": "ppr|pft|FT|timeInfo", "tSteps": "0:1"})
    t0 = time.perf_counter()
    com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    print(f"{ava} {frict} done in {time.perf_counter() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

"""One com1DFA run that saves flow thickness (FT) every 2 s, for the animation.

Usage: python run_anim.py <avalancheDir> [releaseThickness_m]
"""

import sys
import time

from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, initializeProject, logUtils


def main(ava: str, rel_th: str = "1.5") -> None:
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = ava
    cfg_main["MAIN"]["nCPU"] = "1"
    initializeProject.cleanSingleAvaDir(ava, deleteOutput=True)
    logUtils.initiateLogger(ava, "anim")
    cfg = cfgUtils.getModuleConfig(com1DFA, ava, toPrint=False)
    g = cfg["GENERAL"]
    g["relThFromFile"] = "False"
    g["relTh"] = rel_th
    g["meshCellSize"] = "10"
    g["tEnd"] = "200"
    g["simTypeList"] = "null"
    g["resType"] = "ppr|pft|pfv|FT|timeInfo"
    g["tSteps"] = "0:2"
    t0 = time.perf_counter()
    com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    print(f"done in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main(*sys.argv[1:])

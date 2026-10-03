"""Run com1DFA for one avalanche dir and one friction model: 9 release thicknesses 0.4-2.0 m.
Peak files only (ppr|pft|pfv), no plots, no report.

Usage: python run_one.py <avalancheDir> <frictModel>
"""

import sys
import time

from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, initializeProject, logUtils


def main(ava: str, frict: str) -> None:
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = ava
    cfg_main["MAIN"]["nCPU"] = "1"
    cfg_main["FLAGS"].update({"showPlot": "False", "savePlot": "False", "createReport": "False",
                              "ReportDir": "False", "reportOneFile": "False", "debugPlot": "False"})
    initializeProject.cleanSingleAvaDir(ava, deleteOutput=True)
    logUtils.initiateLogger(ava, "lib")
    cfg = cfgUtils.getModuleConfig(com1DFA, ava, toPrint=False)
    cfg["GENERAL"].update({"relThFromFile": "False", "relTh": "1.2", "relThRangeVariation": "0.8$9",
                           "meshCellSize": "10", "tEnd": "300", "simTypeList": "null", "frictModel": frict,
                           "resType": "ppr|pft|pfv", "tSteps": ""})
    t0 = time.perf_counter()
    com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    print(f"{ava} {frict} done in {time.perf_counter() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

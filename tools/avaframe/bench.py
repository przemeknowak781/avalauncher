"""Time AvaFrame com1DFA on an avalanche directory. Runs identically on the laptop and the Spark.

Usage: python bench.py <avalancheDir> <nSims> <nCPU>
nSims > 1 varies the release thickness (0.5-1.5 m) so com1DFA runs nSims simulations in parallel.
"""

import json
import platform
import sys
import time

from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, initializeProject, logUtils


def main(ava: str, n_sims: int, n_cpu: int) -> None:
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = ava
    cfg_main["MAIN"]["nCPU"] = str(n_cpu)
    initializeProject.cleanSingleAvaDir(ava, deleteOutput=True)  # before the logger opens a file (Windows locks it)
    logUtils.initiateLogger(ava, "bench")
    cfg = cfgUtils.getModuleConfig(com1DFA, ava, toPrint=False)
    g = cfg["GENERAL"]
    g["relThFromFile"] = "False"
    g["relTh"] = "1.0"
    g["meshCellSize"] = "10"
    g["tEnd"] = "300"
    g["simTypeList"] = "null"
    if n_sims > 1:
        g["relThRangeVariation"] = f"0.5${n_sims}"
    t0 = time.perf_counter()
    _, _, _, sim_df = com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    dt = time.perf_counter() - t0
    print(json.dumps({"host": platform.node(), "machine": platform.machine(), "sims": len(sim_df),
                      "nCPU": n_cpu, "seconds": round(dt, 1), "per_sim_s": round(dt / max(1, len(sim_df)), 1)}))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))

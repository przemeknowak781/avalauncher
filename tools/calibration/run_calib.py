"""One calibration group: copy the base project, run com1DFA for one friction setting over a release-thickness range.

Usage: python run_calib.py <calibRoot> <name> <frictModel> <relTh> <relThRangeVariation> [key=value ...]
  e.g. python run_calib.py ~/avalauncher/calib samosATSmall samosATSmall 1.1 '0.5$5'
       python run_calib.py ~/avalauncher/calib voellmy Voellmy 1.1 '' 'muvoellmy=0.2|0.3' 'xsivoellmy=1000|2000'
Writes <calibRoot>/runs/<name>/simDF.csv (simHash -> parameters) next to Outputs/com1DFA/peakFiles.
"""

import shutil
import sys
import time
from pathlib import Path

from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, logUtils


def main(root: str, name: str, frict: str, relth: str, var: str, extra: list[str]) -> None:
    rootp = Path(root).expanduser()
    ava = rootp / "runs" / name
    if ava.exists():
        shutil.rmtree(ava)
    shutil.copytree(rootp / "base", ava)
    if any(e.startswith("simTypeList=res") for e in extra):
        (ava / "Inputs" / "RES").mkdir(exist_ok=True)
        for f in (rootp / "forest").iterdir():
            shutil.copy(f, ava / "Inputs" / "RES" / f.name)
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = str(ava)
    cfg_main["MAIN"]["nCPU"] = "1"
    logUtils.initiateLogger(str(ava), "calib")
    cfg = cfgUtils.getModuleConfig(com1DFA, str(ava), toPrint=False)
    g = cfg["GENERAL"]
    g.update({"relThFromFile": "False", "relTh": relth, "relThRangeVariation": var,
              "meshCellSize": "5", "simTypeList": "null", "frictModel": frict,
              "resType": "ppr|pft|pfv|timeInfo"})
    for e in extra:
        k, v = e.split("=", 1)
        if k == "tSteps":
            g["tSteps"] = v
        else:
            g[k] = v
    t0 = time.perf_counter()
    out = com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    sim_df = out[-1] if isinstance(out, tuple) else out
    try:
        sim_df.to_csv(ava / "simDF.csv")
    except Exception as exc:  # noqa: BLE001
        print("could not save simDF:", exc, type(out))
    print(f"{name} {frict} done in {time.perf_counter() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6:])

"""One calibration group of the "las_porywanie" variant: like run_calib.py, plus forest and entrainment inputs.

Copies <calibRoot>/base into <calibRoot>/runs_las/<name>, adds the event's own resistance (forest) polygons as
Inputs/RES and, for simType ent/entres, its entrainment polygons as Inputs/ENT, then runs com1DFA for one
friction setting over a release-thickness range. Resistance and entrainment parameters stay at the AvaFrame 2.1
defaults (ResistanceModel default, cResH 0.01, detrainment True, detK 5, forestVMin/Max 6/40 m/s,
forestThMin/Max 0.6/10 m; rhoEnt 100, entEroEnergy 5000, entThFromFile True -> entThIfMissingInShp 0.3 m when the
shapefile has no thickness value). Nothing here sets any of them.

Usage: python run_calib_las.py <calibRoot> <name> <frictModel> <relTh> <relThRangeVariation> <simType> <resDir> <entDir>
                               [key=value ...]
  simType: res | ent | entres | null;  resDir/entDir: directory relative to calibRoot, or '-' for none
  e.g. python run_calib_las.py ~/avalauncher/calib/avaEiskar samosAT samosAT 2.7 '' entres extras/RES extras/ENT
Writes <calibRoot>/runs_las/<name>/simDF.csv next to Outputs/com1DFA/peakFiles.
"""

import shutil
import sys
import time
from pathlib import Path

from avaframe.com1DFA import com1DFA
from avaframe.in3Utils import cfgUtils, logUtils


def copy_dir(src: Path, dst: Path) -> list[str]:
    files = sorted(f for f in src.iterdir() if f.is_file())
    assert any(f.suffix == ".shp" for f in files), f"no shapefile in {src}"
    dst.mkdir(exist_ok=False)
    for f in files:
        shutil.copy(f, dst / f.name)
    return [f.name for f in files]


def main(root: str, name: str, frict: str, relth: str, var: str, sim_type: str, res_dir: str, ent_dir: str,
         extra: list[str]) -> None:
    rootp = Path(root).expanduser()
    ava = rootp / "runs_las" / name
    if ava.exists():
        shutil.rmtree(ava)
    ava.parent.mkdir(exist_ok=True)
    shutil.copytree(rootp / "base", ava)  # dereferences base/Inputs -> ../Inputs (Eiskar, Filisur2)
    inp = ava / "Inputs"
    assert not inp.is_symlink(), "Inputs must be a real copy, not the shared event Inputs"
    assert not (inp / "RES").exists() and not (inp / "ENT").exists(), "base already has RES/ENT"
    if "res" in sim_type:
        assert res_dir != "-", "simType needs a resistance dir"
        print("RES input:", rootp / res_dir, copy_dir(rootp / res_dir, inp / "RES"), flush=True)
    if "ent" in sim_type:
        assert ent_dir != "-", "simType needs an entrainment dir"
        print("ENT input:", rootp / ent_dir, copy_dir(rootp / ent_dir, inp / "ENT"), flush=True)
    cfg_main = cfgUtils.getGeneralConfig()
    cfg_main["MAIN"]["avalancheDir"] = str(ava)
    cfg_main["MAIN"]["nCPU"] = "1"
    logUtils.initiateLogger(str(ava), "calib")
    cfg = cfgUtils.getModuleConfig(com1DFA, str(ava), toPrint=False)
    g = cfg["GENERAL"]
    g.update({"relThFromFile": "False", "relTh": relth, "relThRangeVariation": var,
              "meshCellSize": "5", "simTypeList": sim_type, "frictModel": frict,
              "resType": "ppr|pft|pfv|timeInfo"})
    for e in extra:
        k, v = e.split("=", 1)
        g[k] = v
    t0 = time.perf_counter()
    out = com1DFA.com1DFAMain(cfg_main, cfgInfo=cfg)
    sim_df = out[-1] if isinstance(out, tuple) else out
    try:
        sim_df.to_csv(ava / "simDF.csv")
    except Exception as exc:  # noqa: BLE001
        print("could not save simDF:", exc, type(out))
    print(f"{name} {frict} {sim_type} done in {time.perf_counter() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9:])

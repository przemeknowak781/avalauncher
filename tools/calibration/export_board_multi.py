"""Export what board_multi.py needs from the Spark calibration runs, one small .npz per event.

Runs on the Spark next to score_multi.py (it reuses its EVENTS table and load_mask):
  python export_board_multi.py calib_loo.json <outDir>
calib_loo.json is written by loo_calib.py (its "plot" block names the best and the leave-one-out run per event).
Each <outDir>/<event>.npz holds dem, transform (a, b, c, d, e, f), obs, rel, optional dep / obs2 masks
and pft_best, pft_loo (peak flow thickness, m) on the same 5 m grid.
"""

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_multi import CALIB, EVENTS, load_mask  # noqa: E402


def main(loo_json: str, out_dir: str) -> None:
    plot = json.loads(Path(loo_json).read_text(encoding="utf-8"))["plot"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for event, p in plot.items():
        cfg, root = EVENTS[event], CALIB / event
        with rasterio.open(root / "dem.tif") as r:
            dem, tr, crs = r.read(1).astype("float32"), r.transform, str(r.crs)
        arrs = {"dem": dem, "transform": np.array(tr[:6], dtype="float64"),
                "obs": load_mask(root / cfg["obs"], dem.shape, tr), "rel": load_mask(root / cfg["rel"], dem.shape, tr)}
        for k in ("dep", "obs2"):
            if k in cfg:
                arrs[k] = load_mask(root / cfg[k], dem.shape, tr)
        for tag in ("best", "loo"):
            pk = root / "runs" / p[f"{tag}_group"] / "Outputs" / "com1DFA" / "peakFiles" / f"{p[tag]}_pft.asc"
            with rasterio.open(pk) as r:
                arrs[f"pft_{tag}"] = r.read(1).astype("float32")
        np.savez_compressed(out / f"{event}.npz", crs=np.array(crs), **arrs)
        print(event, dem.shape, crs, {k: int(v.sum()) for k, v in arrs.items() if v.dtype == bool})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

"""Slide 6: the five calibration panels as separate images, without the best-fit blob
(observed outline + leave-one-out trace only, thick lines for a projector), so the slide can set
event names and results in large HTML type. Reuses tools/calibration/board_multi.panel like popeletzbach.py."""
import inspect
import json
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "calibration"))
import board_multi as bm  # noqa: E402

src = inspect.getsource(bm.panel)
src = src.replace("colors=[LOO_C], linewidths=1.7", "colors=[LOO_C], linewidths=6.0, alpha=0.6")
src = src.replace('color="#1d1b17", lw=2.0, dashes=(4, 2.5)', 'color="#1d1b17", lw=2.8, dashes=(3.2, 2.2)')
src = src.replace('edgecolor="#1d1b17", lw=1.2', 'edgecolor="#1d1b17", lw=1.8')
exec(src, bm.__dict__)

W, H = 400, 560  # rendered at ~1.5x the slide size (266 x 372)
out = ROOT / "deck" / "img"
meta = {}
for k, ev in enumerate(bm.EV, 1):
    z = dict(np.load(bm.NPZ / f"{ev}.npz"))
    z["pft_best"] = np.zeros_like(z["pft_best"])
    im, mpp, _ = bm.panel(ev, z, W, H)
    if ev == "avaPopeletzbach":  # narrow DEM: drop the empty paper columns at the sides
        im = im.crop((43, 0, 373, H))
    im.save(out / f"s6_p{k}.jpg", "JPEG", quality=90, optimize=True)
    meta[ev] = {"file": f"s6_p{k}.jpg", "m_per_px_rendered": round(mpp, 4)}
    print(ev, im.size, "m/px", round(mpp, 3))
(out / "s6_panels.json").write_text(json.dumps(meta, indent=1))

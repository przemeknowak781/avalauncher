"""Slide 1: high-res Popeletzbach panel without the best-fit blob (observed outline + leave-one-out trace only).
Reuses tools/calibration/board_multi.panel with thicker lines for a projector."""
import inspect
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "calibration"))
import board_multi as bm  # noqa: E402

src = inspect.getsource(bm.panel)
src = src.replace("colors=[LOO_C], linewidths=1.7", "colors=[LOO_C], linewidths=7.5, alpha=0.55")
src = src.replace('color="#1d1b17", lw=2.0, dashes=(4, 2.5)', 'color="#1d1b17", lw=3.0, dashes=(3.2, 2.2)')
src = src.replace('edgecolor="#1d1b17", lw=1.2', 'edgecolor="#1d1b17", lw=2.0')
exec(src, bm.__dict__)
z = dict(np.load(bm.NPZ / "avaPopeletzbach.npz"))
z["pft_best"] = np.zeros_like(z["pft_best"])
im, mpp, _ = bm.panel("avaPopeletzbach", z, 700, 1080)
im = im.crop((50, 0, 682, 1080))
out = ROOT / "deck" / "img" / "popeletzbach_hd.png"
im.save(out)
print("saved", out, im.size, "m/px", round(mpp, 3))

"""Sanity check of com1DFA runs for avaKleinerOetscherbach against the observed event area (not a calibration).

Usage: python smoke_check.py <eventRoot> <runName>
  eventRoot = dir made by prep_kleineroetscherbach.py (holds dem.tif, src/obs_*.tif, runs/<runName>)
Footprint = pft > 0.1 m. Prints per simulation: footprint ha, observed ha, IoU, share of observed area hit,
runout difference (max horizontal distance from the highest release cell; > 0 overshoot).
"""

import sys
from pathlib import Path

import numpy as np
import rasterio

FT_MIN = 0.1


def main(root: str, run: str) -> None:
    rootp = Path(root).expanduser()
    with rasterio.open(rootp / "dem.tif") as d:
        dem, tr = d.read(1), d.transform
    ev = rasterio.open(rootp / "src" / "obs_event.tif").read(1).astype(bool)
    rel = rasterio.open(rootp / "src" / "obs_release.tif").read(1).astype(bool)
    rr, cc = np.indices(dem.shape)
    xs, ys = tr * (cc + 0.5, rr + 0.5)
    i0 = np.argmax(np.where(rel, dem, -1e9))
    dist = np.hypot(xs - xs.flat[i0], ys - ys.flat[i0])
    obs_run = dist[ev].max()
    cell_ha = tr.a * tr.a / 1e4
    pk = rootp / "runs" / run / "Outputs" / "com1DFA" / "peakFiles"
    files = sorted(pk.glob("*_pft.asc"))
    assert files, f"no pft files in {pk}"
    for f in files:
        with rasterio.open(f) as r:
            pft = r.read(1)
            assert pft.shape == dem.shape and r.transform.almost_equals(tr), "grid mismatch"
        sim = pft > FT_MIN
        inter, union = (sim & ev).sum(), (sim | ev).sum()
        edge = sim[0].any() or sim[-1].any() or sim[:, 0].any() or sim[:, -1].any()
        print(f"{f.stem}: footprint {sim.sum() * cell_ha:.1f} ha, observed {ev.sum() * cell_ha:.1f} ha, "
              f"IoU {inter / union:.3f}, observed hit {inter / ev.sum():.3f}, "
              f"runout diff {dist[sim].max() - obs_run:+.0f} m (obs {obs_run:.0f} m), "
              f"max pft {pft.max():.2f} m, touches domain edge: {edge}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

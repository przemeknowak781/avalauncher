"""Quick look at a com1DFA run in <avaEiskar>/runs/<name> against the observed Eiskar deposition outlines.

Footprint = pft > 0.1 m. Reports, per peak file:
  dep_hit_dfa / dep_hit_max  fraction of observed deposit cells (DFA / Max outline) inside the footprint
  runout_err_m               sim runout - observed runout; runout = max horizontal distance from the release top
                             (highest DEM cell in ESK_1) over footprint / over the observed outline (DFA and Max)
  min_elev_sim_m             lowest DEM cell reached (observed dense-flow deposit ends ~1150-1190 m)
Usage (Spark): python check_smoke.py ~/avalauncher/calib/avaEiskar [smoke]
"""

import sys
from pathlib import Path

import numpy as np
import rasterio

FT_MIN = 0.1


def main(root: str, name: str = "smoke") -> None:
    rp = Path(root).expanduser()
    with rasterio.open(rp / "dem.tif") as d:
        dem, tr = d.read(1), d.transform
    obs = {k: rasterio.open(rp / "observed" / f"obs_{k}.tif").read(1).astype(bool) for k in ("dfa", "max")}
    rel = rasterio.open(rp / "observed" / "rel_esk1.tif").read(1).astype(bool)
    rr, cc = np.indices(dem.shape)
    xs, ys = tr * (cc + 0.5, rr + 0.5)
    i0 = np.argmax(np.where(rel, dem, -1e9))
    dist = np.hypot(xs - xs.flat[i0], ys - ys.flat[i0])
    obs_run = {k: float(dist[m].max()) for k, m in obs.items()}
    pk = rp / "runs" / name / "Outputs" / "com1DFA" / "peakFiles"
    files = sorted(pk.glob("*_pft.asc"))
    assert files, f"no pft files in {pk}"
    for f in files:
        with rasterio.open(f) as r:
            pft = r.read(1)
            assert pft.shape == dem.shape and r.transform.almost_equals(tr), "grid mismatch"
        fp = pft > FT_MIN
        edge = fp[0].any() or fp[-1].any() or fp[:, 0].any() or fp[:, -1].any()
        sim_run = float(dist[fp].max()) if fp.any() else 0.0
        print(f.name, f"area_ha={fp.sum() * 25 / 1e4:.2f}", f"max_pft={pft.max():.2f}",
              f"min_elev_sim_m={dem[fp].min():.0f}" if fp.any() else "",
              " ".join(f"dep_hit_{k}={(fp & m).sum() / m.sum():.2f}" for k, m in obs.items()),
              " ".join(f"runout_err_{k}_m={sim_run - obs_run[k]:+.0f}" for k in obs),
              f"touches_domain_edge={edge}")
    print("observed runout (m from release top):", {k: round(v) for k, v in obs_run.items()})


if __name__ == "__main__":
    main(*sys.argv[1:])

"""Hero stills (3840x2160) of AvaFrame flows at the moment of largest flow extent, on the winter texture.
The camera sits beyond the runout looking back up the path; 'low' is a near-ground dramatic view.

Usage: python hero_flow.py <assetsDir> <runsDir> <outDir> <job> [<job> ...] [--preview]
  job = SECTOR:FRICT:TH:CAM:AZOFF[:SHIFT]  e.g. S31:samosAT:2.0:low:25 (SHIFT moves the box down the path, fraction of its side)
"""

import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import ImageDraw

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "avaframe")]
import render3d as r3  # noqa: E402
import render3d_batch as rb  # noqa: E402
import vis_common as vc  # noqa: E402

FRICT_PL = {"samosATSmall": "tarcie dla małych lawin", "samosATMedium": "tarcie dla średnich lawin", "samosAT": "tarcie dla dużych lawin"}
CAMS = {"std": dict(elev=32, zoom=1.0), "low": dict(elev=16, zoom=1.12), "mid": dict(elev=24, zoom=1.05)}


def centroid(m):
    r, c = np.nonzero(m)
    return np.array([c.mean(), r.mean()])


def job(args):
    assets, runs, outd, spec, preview = args
    sector, frict, th, cam, azoff, *rest = spec.split(":")
    th, azoff = float(th), float(azoff)
    shift = float(rest[0]) if rest else 0.0
    A = vc.Assets(assets)
    steps, meta = rb.sims(Path(runs) / f"{sector}_{frict}")
    sim = next(s for s, (t, f) in meta.items() if abs(t - th) < 0.05)
    st = sorted(steps[sim])
    grids = [r3.read_asc(p) for _, p in st]
    ext = [int((np.nan_to_num(g) > 0.2).sum()) for g in grids]
    i_pk = int(np.argmax(ext))
    t_pk = st[i_pk][0]
    reach = np.zeros_like(grids[0], bool)
    for g in grids:
        reach |= np.nan_to_num(g) > 0.05
    alive = [i for i, g in enumerate(grids) if (np.nan_to_num(g) > 0.05).sum() > 20]
    start = centroid(np.nan_to_num(grids[0]) > 0.05)
    end = centroid(np.nan_to_num(grids[alive[-1]]) > 0.05)
    dc, dr = end - start
    azim = float(np.degrees(np.arctan2(-dr, dc))) + azoff  # camera beyond the runout, looking back up
    foot = np.zeros_like(reach)
    for g in grids:
        foot |= np.nan_to_num(g) > 0.1
    rows, cols = np.nonzero(foot)  # tight: footprint + max(12 cells, 15 %) pad, min 80 cells
    ext = max(rows.ptp(), cols.ptp())
    side = min(int(max(ext + 2 * max(12, 0.15 * ext), 80)), A.n)
    u = np.array([dc, dr]) / max(1e-6, np.hypot(dc, dr))
    cr = int((rows.min() + rows.max()) / 2 + u[1] * shift * side)
    cc = int((cols.min() + cols.max()) / 2 + u[0] * shift * side)
    box = (int(np.clip(cr - side // 2, 0, A.n - side)), int(np.clip(cc - side // 2, 0, A.n - side)), side)
    W, H = (960, 540) if preview else (3840, 2160)
    up = 2 if preview else int(np.clip(round(1150 / side), 2, int(os.environ.get("UPMAX", 6))))
    S = vc.Surface(A, box, up=up)
    tex = A.draw_trails(A.winter.copy(), w_white=8, w_col=5)
    rgb = S.texture(tex)
    frgb, a = vc.flow_rgba(S.zoom_grid(grids[i_pk]))
    col = rgb * (1 - a[..., None]) + frgb * a[..., None]
    c = CAMS[cam]
    img, _ = S.render(col, W, H, azim, c["elev"], zoom=c["zoom"], axrect=(-0.2, -0.32, 1.4, 1.6))
    name = A.sectors[sector]["name"]
    vc.strips(img, A, f"Lawina: {name}",
              f"AvaFrame com1DFA na terenie GUGiK NMT · płyta {th:.1f} m · {FRICT_PL[frict]} · chwila największej powierzchni przepływu".replace(".", ",", 1),
              right=f"t = {t_pk:.0f} s", legend=vc.flow_legend(A))
    out = Path(outd) / f"{'prev_' if preview else ''}hero_{sector}_{frict}_{th:.1f}_{cam}.png"
    img.save(out)
    return str(out), t_pk, round(azim), box, up


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--preview"]
    preview = "--preview" in sys.argv
    assets, runs, outd, specs = a[0], a[1], a[2], a[3:]
    Path(outd).mkdir(parents=True, exist_ok=True)
    with Pool(int(os.environ.get("WORKERS", min(6, len(specs))))) as p:
        for r in p.imap_unordered(job, [(assets, runs, outd, s, preview) for s in specs]):
            print(*r, flush=True)

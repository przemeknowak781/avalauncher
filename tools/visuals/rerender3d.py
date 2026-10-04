"""Re-render selected 3D AvaFrame videos with render3d's tight framing, frames in parallel.
No-data cells are hidden with transparent faces (NaN heights in plot_surface smear into vertical streaks).

Usage: python rerender3d.py <runsDir> <assetsDir> <outDir> <workers> SECTOR:FRICT:TH [...]
"""

import json
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "avaframe")]
import render3d as r3  # noqa: E402
import render3d_batch as rb  # noqa: E402

G = {}


def fixed_frame(self, ft, azim, elev, t_label, title, sub, zoom=1.5):
    r0, c0, side = self.box
    rgb, a = r3.flow_rgba(self._zoom(ft[r0:r0 + side, c0:c0 + side]))
    col = self.tex * (1 - a[..., None]) + rgb * a[..., None]
    rgba = np.concatenate([col, np.ones(col.shape[:2] + (1,), np.float32)], axis=2)
    rgba[self.hole, 3] = 0.0
    fig = r3.plt.figure(figsize=(r3.W / 100, r3.H / 100), dpi=100, facecolor=np.array(r3.PAPER) / 255)
    ax = fig.add_axes([0, 0.07, 1, 0.82], projection="3d", facecolor=np.array(r3.PAPER) / 255)
    ax.plot_surface(self.X, self.Y, self.zf, facecolors=rgba, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    span = self.X.max()
    zv = self.zf[~self.hole]
    ax.set_box_aspect((1, 1, self.ex * (zv.max() - zv.min()) / span), zoom=zoom)
    ax.set_zlim(zv.min(), zv.max())
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.canvas.draw()
    img = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
    r3.plt.close(fig)
    self.overlay(img, t_label, title, sub)
    return img


def init(assets, steps):
    grids = [r3.read_asc(p) for _, p in steps]
    box = r3.tight_box(grids, grids[0].shape[0])
    sc = r3.Scene(assets, box)
    # scipy zoom with the default mode="constant" can sample just past the last cell and return 0 there,
    # which draws a vertical curtain down to z = 0 along the box edge; mode="nearest" avoids it
    z_all = np.fromfile(Path(assets) / "terrain_f32.bin", dtype="<f4").reshape(grids[0].shape)
    r0, c0, side = box
    sub = z_all[r0:r0 + side, c0:c0 + side]
    zf = ndimage.zoom(sub, sc.up, order=1, mode="nearest")
    hole = np.isnan(sc.z) | (ndimage.zoom((sub <= z_all.min() + 0.01).astype(np.float32), sc.up, order=0, mode="nearest") > 0.5)
    idx = ndimage.distance_transform_edt(hole, return_distances=False, return_indices=True)
    sc.zf = zf[tuple(idx)]
    sc.hole = ndimage.binary_dilation(hole, iterations=1)
    z_full = np.fromfile(Path(assets) / "terrain_f32.bin", dtype="<f4").reshape(grids[0].shape)
    G.update(sc=sc, grids=grids, ts=[s[0] for s in steps], az0=r3.track_azimuth(grids, z_full))


def one(a):
    i, t, u, title, sub, fd = a
    j = max(0, np.searchsorted(G["ts"], t, side="right") - 1)
    t_end = G["ts"][-1]
    img = fixed_frame(G["sc"], G["grids"][j], G["az0"] - 15 + 30 * u, 36 - 6 * u, f"t = {min(t, t_end):.0f} s", title, sub)
    img.save(Path(fd) / f"f_{i:04d}.png")
    return i


def main(runs, assets, outd, workers, *specs):
    runs, outd = Path(runs), Path(outd)
    outd.mkdir(parents=True, exist_ok=True)
    names = {s["id"]: s["name"] for s in json.loads((Path(assets) / "sectors.json").read_text(encoding="utf-8"))}
    for spec in specs:
        sector, frict, th = spec.split(":")
        th = float(th)
        steps, meta = rb.sims(runs / f"{sector}_{frict}")
        sim = next(s for s, (t, f) in meta.items() if abs(t - th) < 0.05)
        st = sorted(steps[sim])
        title = f"Lawina: {names[sector]}"
        sub = f"AvaFrame com1DFA na terenie GUGiK NMT · płyta {th:.1f} m · {rb.FRICT_PL[frict]}".replace(".", ",")
        t_end = st[-1][0]
        times = list(np.arange(0, t_end + 1.0, 1.0)) + [t_end] * 16
        out = outd / f"3d_{sector}_{frict}_{th:.1f}.mp4"
        fd = out.with_suffix("")
        fd.mkdir(exist_ok=True)
        jobs = [(i, t, i / max(1, len(times) - 1), title, sub, str(fd)) for i, t in enumerate(times)]
        with Pool(int(workers), initializer=init, initargs=(assets, st)) as p:
            list(p.imap_unordered(one, jobs, chunksize=2))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", str(fd / "f_%04d.png"),
                        "-vf", "framerate=fps=30:interp_start=0:interp_end=255:scene=100,format=yuv420p",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-movflags", "+faststart", str(out)], check=True)
        print("ok", out, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

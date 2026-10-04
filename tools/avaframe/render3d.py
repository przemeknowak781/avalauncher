"""3D animation of an AvaFrame run: GUGiK terrain as a textured surface, flow thickness draped on it,
slow camera orbit. Offscreen matplotlib, so it runs on the Spark without a display.

Usage (one simulation):
  python render3d.py <assetsDir> <timeStepsDir-or-glob> <out.mp4> "<title>" "<subtitle>"
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

PAPER, INK, INK2, HAZ = (244, 239, 228), (29, 27, 23), (90, 82, 68), (166, 59, 0)
RAMP = [(0.05, (255, 214, 170)), (0.3, (249, 145, 72)), (0.8, (232, 89, 12)), (1.5, (166, 59, 0)), (3.0, (90, 26, 0))]
W, H = 1920, 1080


def read_asc(p):
    return np.loadtxt(Path(p).read_text().splitlines()[6:], dtype=np.float32)


def flow_rgba(ft):
    v = np.nan_to_num(ft)
    rgb = np.zeros(v.shape + (3,), np.float32)
    a = np.zeros(v.shape, np.float32)
    for (lo, cl), (hi, ch) in zip(RAMP, RAMP[1:]):
        m = (v >= lo) & (v < hi)
        t = ((v - lo) / (hi - lo))[m][:, None]
        rgb[m] = np.array(cl) * (1 - t) + np.array(ch) * t
        a[m] = 0.9
    top = v >= RAMP[-1][0]
    rgb[top], a[top] = RAMP[-1][1], 0.95
    return rgb / 255, a


class Scene:
    def __init__(self, assets, box, exaggeration=1.25, up=3):
        from PIL import ImageDraw as _D
        from scipy import ndimage
        assets = Path(assets)
        self.font_path = assets / "Archivo-var.ttf"
        t = json.loads((assets / "terrain.json").read_text(encoding="utf-8"))
        trails = json.loads((assets / "trails.json").read_text(encoding="utf-8"))
        colors = {"red": (214, 40, 40), "blue": (31, 95, 209), "green": (42, 157, 60), "yellow": (242, 194, 0), "black": (34, 32, 28)}
        self.cell = t["cell_m"] / up
        z = np.fromfile(assets / "terrain_f32.bin", dtype="<f4").reshape(t["height"], t["width"])
        r0, c0, side = box
        self.box, self.up = box, up
        sub = z[r0:r0 + side, c0:c0 + side]
        self.z = ndimage.zoom(sub, up, order=1, mode="nearest")
        nodata = ndimage.zoom((sub <= z.min() + 0.01).astype(np.float32), up, order=0) > 0.5
        self.z = np.where(nodata, np.nan, self.z)  # no NMT data (Slovak side): leave a hole, not a flat wall
        tex_file = assets / "winter.png" if (assets / "winter.png").exists() else assets / "map.png"
        base = Image.open(tex_file).convert("RGB")
        k = base.width // t["width"]
        tex = base.crop((c0 * k, r0 * k, (c0 + side) * k, (r0 + side) * k))
        d = _D.Draw(tex)
        for tr in trails:
            for part in tr["paths"]:
                pts = [((c - c0) * k, (r - r0) * k) for c, r in part]
                d.line(pts, fill=(255, 255, 255), width=8, joint="curve")
                d.line(pts, fill=colors.get(tr["color"], colors["red"]), width=5, joint="curve")
        n = side * up
        self.tex = np.asarray(tex.resize((n, n), Image.LANCZOS), np.float32) / 255
        self.X, self.Y = np.meshgrid(np.arange(n) * self.cell, -np.arange(n) * self.cell)  # north is +Y
        self.ex = exaggeration
        self._zoom = lambda a: ndimage.zoom(np.nan_to_num(a), up, order=1)

    def frame(self, ft, azim, elev, t_label, title, sub, zoom=1.5):
        r0, c0, side = self.box
        rgb, a = flow_rgba(self._zoom(ft[r0:r0 + side, c0:c0 + side]))
        col = self.tex * (1 - a[..., None]) + rgb * a[..., None]
        fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=np.array(PAPER) / 255)
        ax = fig.add_axes([0, 0.07, 1, 0.82], projection="3d", facecolor=np.array(PAPER) / 255)
        ax.plot_surface(self.X, self.Y, self.z, facecolors=col, rstride=1, cstride=1,
                        linewidth=0, antialiased=False, shade=False)
        span = self.X.max()
        ax.set_box_aspect((1, 1, self.ex * (np.nanmax(self.z) - np.nanmin(self.z)) / span), zoom=zoom)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        fig.canvas.draw()
        img = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
        plt.close(fig)
        self.overlay(img, t_label, title, sub)
        return img

    def font(self, size, weight=700, width=100):
        f = ImageFont.truetype(str(self.font_path), size)
        f.set_variation_by_axes([weight, width])
        return f

    def overlay(self, img, t_label, title, sub):
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, 0, W, 118), fill=(*PAPER, 236))
        d.text((48, 42), title, font=self.font(40, 800, 112), fill=INK, anchor="lm")
        d.text((48, 88), sub, font=self.font(22, 500), fill=INK2, anchor="lm")
        d.text((W - 48, 60), t_label, font=self.font(52, 800), fill=HAZ, anchor="rm")
        y = H - 52
        d.rectangle((0, y - 26, W, H), fill=(*PAPER, 236))
        x = 48
        d.text((x, y), "Grubość przepływu", font=self.font(22, 700), fill=INK, anchor="lm")
        x += 230
        for v, c in RAMP:
            d.rectangle((x, y - 10, x + 64, y + 10), fill=c)
            d.text((x + 32, y + 22), f"{v:g} m".replace(".", ","), font=self.font(15, 600), fill=INK, anchor="mm")
            x += 76
        d.text((W - 48, y), "AvaFrame com1DFA · teren GUGiK NMT, ortofoto GUGiK (przewyższenie 1,25×) · śnieg: scenariusz syntetyczny",
               font=self.font(18, 500), fill=INK2, anchor="rm")


def box_around(grids, n_total, pad=55, min_side=140):
    """Wide crop (kept for older callers)."""
    reach = np.zeros_like(grids[0], bool)
    for g in grids:
        reach |= np.nan_to_num(g) > 0.05
    rows, cols = np.nonzero(reach)
    side = int(max(rows.max() - rows.min(), cols.max() - cols.min(), min_side) + 2 * pad)
    side = min(side, n_total)
    cr, cc = (rows.min() + rows.max()) // 2, (cols.min() + cols.max()) // 2
    return (int(np.clip(cr - side // 2 + side // 8, 0, n_total - side)),
            int(np.clip(cc - side // 2, 0, n_total - side)), side)


def tight_box(grids, n_total, min_side=80, thr=0.1):
    """Square crop around the run's own peak footprint, pad max(12 cells, 15 % of the extent)."""
    peak = np.nanmax(np.stack([np.nan_to_num(g) for g in grids]), axis=0)
    rows, cols = np.nonzero(peak > thr)
    ext = int(max(rows.max() - rows.min(), cols.max() - cols.min()))
    side = min(n_total, max(min_side, ext + 2 * max(12, int(0.15 * ext))))
    cr, cc = (rows.min() + rows.max()) // 2, (cols.min() + cols.max()) // 2
    return (int(np.clip(cr - side // 2, 0, n_total - side)), int(np.clip(cc - side // 2, 0, n_total - side)), side)


def track_azimuth(grids, z):
    """Camera downslope looking up the track: azimuth along release top -> farthest runout cell."""
    first = next((g for g in grids if np.nan_to_num(g).max() > 0.05), grids[0])
    rel_r, rel_c = np.nonzero(np.nan_to_num(first) > 0.05)
    i = np.argmax(z[rel_r, rel_c])
    tr, tc = rel_r[i], rel_c[i]
    peak = np.nanmax(np.stack([np.nan_to_num(g) for g in grids]), axis=0)
    rr, cc = np.nonzero(peak > 0.1)
    j = np.argmax((rr - tr) ** 2 + (cc - tc) ** 2)
    dx, dy = cc[j] - tc, -(rr[j] - tr)  # plot coords: x = col, y = -row (north up)
    return float(np.degrees(np.arctan2(dy, dx)))


def render(assets, steps, out, title, sub, frames_dir=None, step_s=1.0):
    steps = sorted(steps)
    grids = [read_asc(p) for _, p in steps]
    box = tight_box(grids, grids[0].shape[0])
    sc = Scene(assets, box)
    z_full = np.fromfile(Path(assets) / "terrain_f32.bin", dtype="<f4").reshape(grids[0].shape)
    az0 = track_azimuth(grids, z_full)
    t_end = steps[-1][0]
    times = list(np.arange(0, t_end + step_s, step_s)) + [t_end] * 16
    fd = Path(frames_dir or Path(out).with_suffix(""))
    fd.mkdir(parents=True, exist_ok=True)
    ts = [s[0] for s in steps]
    for i, t in enumerate(times):
        j = max(0, np.searchsorted(ts, t, side="right") - 1)
        u = i / max(1, len(times) - 1)
        azim = az0 - 15 + 30 * u  # slow orbit around the track direction
        elev = 36 - 6 * u
        sc.frame(grids[j], azim, elev, f"t = {min(t, t_end):.0f} s", title, sub).save(fd / f"f_{i:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", str(fd / "f_%04d.png"),
                    "-vf", "framerate=fps=30:interp_start=0:interp_end=255:scene=100,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-movflags", "+faststart", str(out)], check=False)
    return fd


def steps_from(dir_or_glob, sim=None):
    p = Path(dir_or_glob)
    files = p.glob("*_FT_t*.asc") if p.is_dir() else Path(".").glob(str(dir_or_glob))
    out = []
    for f in files:
        m = re.match(r"(.+)_FT_t([\d.]+)\.asc$", f.name)
        if m and (sim is None or m.group(1) == sim):
            out.append((float(m.group(2)), f))
    return out


if __name__ == "__main__":
    assets, src, out, title, sub = sys.argv[1:6]
    render(assets, steps_from(src), out, title, sub)

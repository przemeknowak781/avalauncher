"""Shared bits for pitch visuals: palette, Archivo fonts, GUGiK terrain as a textured matplotlib 3D surface,
3D-to-pixel projection and the paper title/credit strips. Runs offscreen (Spark)."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage  # noqa: E402

PAPER, PAPER2, INK, INK2 = (244, 239, 228), (235, 228, 212), (29, 27, 23), (90, 82, 68)
HAZ, HAZ_T, UNK, ROUTE = (232, 89, 12), (166, 59, 0), (91, 63, 209), (214, 0, 126)
TRAIL = {"red": (214, 40, 40), "blue": (31, 95, 209), "green": (42, 157, 60), "yellow": (242, 194, 0), "black": (34, 32, 28)}
RAMP = [(0.05, (255, 214, 170)), (0.3, (249, 145, 72)), (0.8, (232, 89, 12)), (1.5, (166, 59, 0)), (3.0, (90, 26, 0))]
CREDIT = "Teren i ortofoto: GUGiK · Szlaki: © OSM · Symulacje: AvaFrame com1DFA · Śnieg: scenariusz syntetyczny"


def pl(n, one, few, many):
    """Polish plural: 1 symulacja, 2-4 symulacje (not 12-14), 5+ symulacji."""
    if n == 1:
        return one
    return few if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else many


class Assets:
    def __init__(self, d):
        d = Path(d)
        self.dir = d
        self.t = json.loads((d / "terrain.json").read_text(encoding="utf-8"))
        self.n = self.t["width"]
        self.cell = self.t["cell_m"]
        self.z = np.fromfile(d / "terrain_f32.bin", dtype="<f4").reshape(self.t["height"], self.n)
        self.nodata = self.z <= self.z.min() + 0.01  # no NMT data, filled flat
        self.trails = json.loads((d / "trails.json").read_text(encoding="utf-8"))
        self.sectors = {s["id"]: s for s in json.loads((d / "sectors.json").read_text(encoding="utf-8"))}
        self.font_path = d / "Archivo-var.ttf"
        self.winter = Image.open(d / "winter.png").convert("RGB")
        self.k = self.winter.width // self.n
        sg = d / "sectors_u8.bin"
        self.sid = np.fromfile(sg, np.uint8).reshape(self.z.shape) if sg.exists() else None

    def sector_mask(self, ids, k):
        """Smooth raster mask (PIL L, k px per cell) of the given sectors, from sectors_u8.bin."""
        idx = [self.sectors[s]["index"] for s in ids]
        m = ndimage.gaussian_filter(np.isin(self.sid, idx).astype(np.float32), 0.7)
        m = ndimage.zoom(m, k, order=1) > 0.32
        return Image.fromarray((m * 255).astype(np.uint8))

    def font(self, size, weight=700, width=100):
        f = ImageFont.truetype(str(self.font_path), int(round(size)))
        f.set_variation_by_axes([weight, width])
        return f

    def poly_px(self, sid, k=None):
        k = k or self.k
        return [(c * k, r * k) for c, r in self.sectors[sid]["polygon"]]

    def draw_trails(self, img, k=None, w_white=8, w_col=5):
        k = k or self.k
        d = ImageDraw.Draw(img)
        for tr in self.trails:
            for part in tr["paths"]:
                pts = [(c * k, r * k) for c, r in part]
                d.line(pts, fill=(255, 255, 255), width=w_white, joint="curve")
        for tr in self.trails:
            for part in tr["paths"]:
                pts = [(c * k, r * k) for c, r in part]
                d.line(pts, fill=TRAIL.get(tr["color"], TRAIL["red"]), width=w_col, joint="curve")
        return img

    def z_at(self, c, r):
        return ndimage.map_coordinates(self.z, [np.atleast_1d(r), np.atleast_1d(c)], order=1)


class Surface:
    """Terrain patch (r0, c0, side) in 10 m cells, upsampled `up` times, ready for plot_surface."""

    def __init__(self, A, box=None, up=2, ex=1.25):
        self.A, self.up, self.ex = A, up, ex
        r0, c0, side = box or (0, 0, A.n)
        self.box = (r0, c0, side)
        self.z = ndimage.zoom(A.z[r0:r0 + side, c0:c0 + side], up, order=1, mode="nearest")  # default mode can give 0 at the edge
        nod = ndimage.zoom(A.nodata[r0:r0 + side, c0:c0 + side].astype(np.uint8), up, order=0) > 0
        self.nod = ndimage.binary_dilation(nod, iterations=2)
        self.m = self.z.shape[0]
        self.cell = A.cell / up
        # vertex j sits at cell coordinate c0 + j * (side - 1) / (m - 1) (ndimage.zoom aligns the end points)
        jj = np.linspace(0, side - 1, self.m)
        self.X, self.Y = np.meshgrid((c0 + jj) * A.cell, -(r0 + jj) * A.cell)

    def texture(self, tex_full):
        r0, c0, side = self.box
        k = tex_full.width // self.A.n
        crop = tex_full.crop((c0 * k, r0 * k, (c0 + side) * k, (r0 + side) * k)).resize((self.m, self.m), Image.LANCZOS)
        return np.asarray(crop, np.float32)[..., :3] / 255

    def zoom_grid(self, g, order=1):
        r0, c0, side = self.box
        return ndimage.zoom(np.nan_to_num(g[r0:r0 + side, c0:c0 + side]).astype(np.float32), self.up, order=order, mode="nearest")

    def render(self, rgb, W, H, azim, elev, axrect=(-0.18, -0.25, 1.36, 1.5), zoom=1.0, extra=None, focal=None):
        """rgb: (m, m, 3) float colours. Returns PIL image and project(c, r, z) -> (px, py)."""
        rgba = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,), np.float32)], axis=2)
        rgba[self.nod, 3] = 0.0
        dpi = 100
        fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi, facecolor=np.array(PAPER) / 255)
        ax = fig.add_axes(list(axrect), projection="3d", facecolor=np.array(PAPER) / 255)
        ax.computed_zorder = False
        ax.plot_surface(self.X, self.Y, self.z, facecolors=rgba, rstride=1, cstride=1,
                        linewidth=0, antialiased=False, shade=False, zorder=1)
        zr = float(np.nanmax(self.z) - np.nanmin(self.z[~self.nod] if (~self.nod).any() else self.z))
        span = float(self.X.max() - self.X.min())
        ax.set_xlim(self.X.min(), self.X.max())
        ax.set_ylim(self.Y.min(), self.Y.max())
        ax.set_zlim(float(np.nanmin(self.z[~self.nod])) if (~self.nod).any() else float(self.z.min()), float(self.z.max()))
        ax.set_box_aspect((1, 1, self.ex * zr / span), zoom=zoom)
        if focal:
            ax.set_proj_type("persp", focal_length=focal)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        if extra:
            extra(ax)
        fig.canvas.draw()
        M = ax.M
        tr = ax.transData
        A = self.A

        def project(c, r, z):
            c, r, z = (np.atleast_1d(np.asarray(v, np.float64)) for v in (c, r, z))
            v = M @ np.vstack([c * A.cell, -r * A.cell, z, np.ones_like(c)])
            p = tr.transform(np.c_[v[0] / v[3], v[1] / v[3]])
            return p[:, 0], H - p[:, 1]

        img = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
        plt.close(fig)
        return img, project


def flow_rgba(ft):
    v = np.nan_to_num(ft)
    rgb = np.zeros(v.shape + (3,), np.float32)
    a = np.zeros(v.shape, np.float32)
    for (lo, cl), (hi, ch) in zip(RAMP, RAMP[1:]):
        m = (v >= lo) & (v < hi)
        t = ((v - lo) / (hi - lo))[m][:, None]
        rgb[m] = np.array(cl) * (1 - t) + np.array(ch) * t
        a[m] = 0.92
    top = v >= RAMP[-1][0]
    rgb[top], a[top] = RAMP[-1][1], 0.96
    return rgb / 255, a


def strips(img, A, title, sub, right=None, right_col=HAZ_T, legend=None, credit=CREDIT, top_h=118, bot_h=78):
    """Paper strips at 1920-scale sizes, scaled to the image width. legend(draw, x, y, s) -> draws, returns x end."""
    W, H = img.size
    s = W / 1920
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, W, top_h * s), fill=(*PAPER, 240))
    d.text((48 * s, 44 * s), title, font=A.font(40 * s, 800, 112), fill=INK, anchor="lm")
    d.text((48 * s, 90 * s), sub, font=A.font(22 * s, 500), fill=INK2, anchor="lm")
    if right:
        d.text((W - 48 * s, 60 * s), right, font=A.font(44 * s, 800, 112), fill=right_col, anchor="rm")
    y = H - bot_h * s / 2
    d.rectangle((0, H - bot_h * s, W, H), fill=(*PAPER, 240))
    if legend:
        legend(d, 48 * s, y, s)
    d.text((W - 48 * s, y), credit, font=A.font(18 * s, 500), fill=INK2, anchor="rm")
    return img


def flow_legend(A):
    def leg(d, x, y, s):
        d.text((x, y - 4 * s), "Grubość przepływu", font=A.font(21 * s, 700), fill=INK, anchor="lm")
        x += 220 * s
        for v, c in RAMP:
            d.rectangle((x, y - 18 * s, x + 64 * s, y + 2 * s), fill=c)
            d.text((x + 32 * s, y + 16 * s), f"{v:g} m".replace(".", ","), font=A.font(15 * s, 600), fill=INK, anchor="mm")
            x += 76 * s
        return x
    return leg


def label(d, A, x, y, text, sub=None, color=INK, s=1.0, anchor_pt=None, size=24):
    """Paper label box centred at (x, y); optional leader line to anchor_pt."""
    f1, f2 = A.font(size * s, 800, 100), A.font(size * 0.72 * s, 600, 100)
    w1 = d.textlength(text, font=f1)
    w2 = d.textlength(sub, font=f2) if sub else 0
    w = max(w1, w2) + 28 * s
    h = (size * 1.45 + (size * 0.95 if sub else 0)) * s
    if anchor_pt:
        ey = y + h / 2 if anchor_pt[1] > y else y - h / 2
        d.line([(x, ey), anchor_pt], fill=(*color, 255), width=max(2, int(3 * s)))
        r = 7 * s
        d.ellipse((anchor_pt[0] - r, anchor_pt[1] - r, anchor_pt[0] + r, anchor_pt[1] + r), fill=(255, 255, 255), outline=color, width=max(2, int(3 * s)))
    d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), radius=6 * s, fill=(*PAPER, 245), outline=(*color, 255), width=max(2, int(2.5 * s)))
    if sub:
        d.text((x, y - h / 2 + size * 0.78 * s), text, font=f1, fill=color, anchor="mm")
        d.text((x, y + h / 2 - size * 0.62 * s), sub, font=f2, fill=INK2, anchor="mm")
    else:
        d.text((x, y), text, font=f1, fill=color, anchor="mm")

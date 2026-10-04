"""Concept still (3840x2160) and orbit video (1920x1080, <= 20 s) of the whole massif:
hazard sectors hatched orange, unknown sectors under white fog with a violet edge, trails in their colours,
magenta drone route from the Murowaniec base through the unknown sectors.

Without days.json the flags are an illustration (labelled "ilustracja koncepcji").

Usage: python concept.py <assetsDir> <outDir> still|video|preview [--hazard S31,S10] [--unknown S21,S22,S35] [--base 278,69.2]
       [--flags flags.json]   (flags + route from the demo engine: node tools/visuals/engine_flags.mjs 1 20 > flags.json)
"""

import argparse
import json
import re
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import vis_common as vc

G = {}


def build_texture(A, hazard, unknown, tex_name="map.png"):
    base = Image.open(A.dir / tex_name).convert("RGB")
    up = 4000 // base.width  # draw at 10 px per cell for crisp hatching
    k = base.width * up // A.n
    img = base.resize((A.n * k, A.n * k), Image.LANCZOS)
    n = A.n * k
    um, hm = (np.asarray(A.sector_mask(ids, k)) > 0 for ids in (unknown, hazard))
    dist_u, dist_h = (ndimage.distance_transform_edt(~m) for m in (um, hm))
    # unknown: white fog, soft edge spilling ~3 cells beyond the sector
    fa = (0.9 * np.clip(1 - (dist_u - 1.5 * k) / (2.5 * k), 0, 1) ** 1.5)[..., None]
    arr = np.asarray(img, np.float32)
    arr = arr * (1 - fa) + np.array([252, 252, 255], np.float32) * fa
    # hazard: light orange tint + diagonal hatch, clipped to the sector
    yy, xx = np.mgrid[0:n, 0:n]
    hatch = ((xx + yy) % int(3.2 * k)) < int(1.3 * k)
    haz = np.array(vc.HAZ, np.float32)
    arr[hm] = arr[hm] * 0.7 + haz * 0.3
    arr[hm & hatch] = haz
    img = Image.fromarray(arr.astype(np.uint8))
    A.draw_trails(img, k, w_white=int(1.5 * k), w_col=int(0.9 * k))
    arr = np.asarray(img).copy()
    for m, dist, col in ((hm, dist_h, vc.HAZ), (um, dist_u, vc.UNK)):
        din = ndimage.distance_transform_edt(m)
        ring = ((dist > 0) & (dist <= 0.9 * k)) | (m & (din <= 1.5))
        casing = (dist > 0.9 * k) & (dist <= 1.4 * k)
        arr[casing] = (255, 255, 255)
        arr[ring] = col
    return Image.fromarray(arr)


def route_path(A, base, targets):
    pts, cur, left = [tuple(base)], tuple(base), list(targets)
    while left:  # nearest neighbour, like the planner
        nxt = min(left, key=lambda s: np.hypot(A.sectors[s]["centroid"][0] - cur[0], A.sectors[s]["centroid"][1] - cur[1]))
        cur = tuple(A.sectors[nxt]["centroid"])
        pts.append(cur)
        left.remove(nxt)
    pts.append(tuple(base))
    return pts


def densify(pts, step=1.5):
    out = []
    for (c0, r0), (c1, r1) in zip(pts, pts[1:]):
        m = max(2, int(np.hypot(c1 - c0, r1 - r0) / step))
        t = np.linspace(0, 1, m, endpoint=False)
        out += list(zip(c0 + (c1 - c0) * t, r0 + (r1 - r0) * t))
    out.append(pts[-1])
    return np.array(out)


def init(assets, hazard, unknown, base, route, up, W, H, meta=None):
    A = vc.Assets(assets)
    tex = build_texture(A, hazard, unknown)
    S = vc.Surface(A, None, up=up)
    zmax = ndimage.maximum_filter(ndimage.gaussian_filter(A.z, 2), size=9)
    path = densify(route)
    zr = ndimage.map_coordinates(zmax, [path[:, 1], path[:, 0]], order=1) + 110
    zr = ndimage.gaussian_filter1d(zr, 4)
    G.update(A=A, S=S, rgb=S.texture(tex), hazard=hazard, unknown=unknown, base=base, route=route, path=path, zr=zr, W=W, H=H,
             meta=meta or {})


def frame(azim, elev, zoom, out=None):
    A, S, W, H = G["A"], G["S"], G["W"], G["H"]
    s = W / 1920
    path, zr = G["path"], G["zr"]

    def extra(ax):
        x, y = path[:, 0] * A.cell, -path[:, 1] * A.cell
        ax.plot(x, y, zr, color="white", lw=8 * s, solid_capstyle="round", zorder=5)
        ax.plot(x, y, zr, color=np.array(vc.ROUTE) / 255, lw=4.5 * s, solid_capstyle="round", zorder=6)

    img, project = S.render(G["rgb"], W, H, azim, elev, zoom=zoom, axrect=(-0.12, -0.2, 1.24, 1.4), extra=extra)
    d = ImageDraw.Draw(img, "RGBA")
    # waypoints: drop line from the route to the sector, dot on the ground
    for wi, (c, r) in enumerate(G["route"][1:-1], 1):
        zg = float(A.z_at(c, r)[0])
        i = int(np.argmin(np.hypot(path[:, 0] - c, path[:, 1] - r)))
        zt = float(zr[i])
        (x0,), (y0,) = project(c, r, zg)
        (x1,), (y1,) = project(c, r, zt)
        for k in range(0, 10, 2):
            d.line([(x0 + (x1 - x0) * k / 10, y0 + (y1 - y0) * k / 10), (x0 + (x1 - x0) * (k + 1) / 10, y0 + (y1 - y0) * (k + 1) / 10)],
                   fill=(*vc.ROUTE, 255), width=int(3 * s))
        rr = 13 * s
        d.ellipse((x1 - rr, y1 - rr, x1 + rr, y1 + rr), fill=(*vc.ROUTE, 255), outline=(255, 255, 255), width=int(2.5 * s))
        d.text((x1, y1 + 0.5 * s), str(wi), font=A.font(17 * s, 800), fill=(255, 255, 255), anchor="mm")
    # base
    bc, br = G["base"]
    (bx,), (by,) = project(bc, br, float(A.z_at(bc, br)[0]))
    rr = 13 * s
    d.ellipse((bx - rr, by - rr, bx + rr, by + rr), fill=(*vc.ROUTE, 255), outline=(255, 255, 255), width=int(4 * s))
    vc.label(d, A, bx + 120 * s, by + 6 * s, "Baza drona", "Murowaniec", color=vc.ROUTE, s=s, anchor_pt=None, size=22)
    # sector labels above their sector, pushed apart so they do not overlap
    meta = G["meta"]
    subs = meta.get("subs", {})
    placed, specs = [], []
    groups = [(G["hazard"], vc.HAZ_T, "może zagrozić szlakowi")]
    if len(G["unknown"]) <= 5:  # many unknowns: the fog and the legend speak for themselves
        groups.append((G["unknown"], vc.UNK, "nie wiem: pomiar się zestarzał"))
    for ids, col, sub in groups:
        for sid in ids:
            c, r = A.sectors[sid]["centroid"]
            (px,), (py,) = project(c, r, float(A.z_at(c, r)[0]) + 20)
            specs.append((py, px, A.sectors[sid]["name"], subs.get(sid, sub), col))
    size = 24
    f1, f2 = A.font(size * s, 800, 100), A.font(size * 0.72 * s, 600, 100)
    for py, px, name, sub, col in sorted(specs, reverse=True):
        w = max(d.textlength(name, font=f1), d.textlength(sub, font=f2)) + 28 * s
        h = (size * 1.45 + size * 0.95) * s
        best = None
        for dist in (92, 130, 175, 225):  # candidate spots around the anchor, nearest first
            for dx, dy in ((0, -1), (0, 1), (-0.8, -0.8), (0.8, -0.8), (-0.8, 0.8), (0.8, 0.8), (-1.3, 0), (1.3, 0)):
                x = px + dx * (dist * s + w * 0.35 * abs(dx))
                y = py + dy * dist * s
                if not (w / 2 + 12 * s < x < W - w / 2 - 12 * s and 125 * s + h / 2 < y < H - 80 * s - h / 2):
                    continue
                if any(abs(b[0] - x) < (b[2] + w) / 2 + 8 * s and abs(b[1] - y) < (b[3] + h) / 2 + 6 * s for b in placed):
                    continue
                best = (x, y)
                break
            if best:
                break
        x, y = best or (px, py - 92 * s)
        placed.append((x, y, w, h))
        vc.label(d, A, x, y, name, sub, color=col, s=s, anchor_pt=(px, py), size=size)

    def legend(d, x, y, s):
        f = A.font(20 * s, 650)
        sw, sh = 46 * s, 24 * s
        # hatch swatch
        box = Image.new("RGB", (int(sw), int(sh)), tuple(int(v * 0.78 + h * 0.22) for v, h in zip(vc.PAPER, vc.HAZ)))
        bd = ImageDraw.Draw(box)
        for xx in range(-int(sh), int(sw), int(9 * s)):
            bd.line([(xx, sh), (xx + sh, 0)], fill=vc.HAZ, width=max(2, int(3 * s)))
        img.paste(box, (int(x), int(y - sh / 2)))
        d.rectangle((x, y - sh / 2, x + sw, y + sh / 2), outline=vc.HAZ, width=int(2.5 * s))
        d.text((x + sw + 12 * s, y), "Może zagrozić szlakowi", font=f, fill=vc.HAZ_T, anchor="lm")
        x += sw + 12 * s + d.textlength("Może zagrozić szlakowi", font=f) + 40 * s
        d.rectangle((x, y - sh / 2, x + sw, y + sh / 2), fill=(252, 252, 255), outline=vc.UNK, width=int(2.5 * s))
        nu = len(G["unknown"])
        tu = f"Nie wiem ({nu} {vc.pl(nu, 'stok', 'stoki', 'stoków')})" if nu > 5 else "Nie wiem"
        d.text((x + sw + 12 * s, y), tu, font=f, fill=vc.UNK, anchor="lm")
        x += sw + 12 * s + d.textlength(tu, font=f) + 40 * s
        d.line([(x, y), (x + sw, y)], fill=(255, 255, 255), width=int(9 * s))
        d.line([(x, y), (x + sw, y)], fill=vc.ROUTE, width=int(5 * s))
        nr = len(G["route"]) - 2
        d.text((x + sw + 12 * s, y), f"Plan przelotu ({nr} {vc.pl(nr, 'stok', 'stoki', 'stoków')})", font=f, fill=vc.ROUTE, anchor="lm")
        return x

    vc.strips(img, A, "Co wiemy, czego nie wiemy i dokąd polecieć",
              meta.get("subtitle", "Hala Gąsienicowa, Tatry · teren GUGiK NMT 4 × 4 km · szlaki w kolorach z mapy · stan śniegu syntetyczny"),
              right=meta.get("tag", "ilustracja koncepcji"), right_col=vc.INK2, legend=legend)
    if out:
        img.save(out)
    return img


def vframe(a):
    i, azim, elev, zoom, fd = a
    frame(azim, elev, zoom, Path(fd) / f"f_{i:04d}.png")
    return i


def flags_from_engine(path):
    """JSON from tools/visuals/engine_flags.mjs: the demo engine's flags and flight plan for one morning."""
    e = json.loads(Path(path).read_text(encoding="utf-8"))
    hz = [f["sector"] for f in e["flags"] if f["kind"] == "zagrozenie"]
    uk = [f["sector"] for f in e["flags"] if f["kind"] == "nie_wiem"]
    subs = {}
    for f in e["flags"]:
        m = re.search(r"Pomiar (\d+) h temu, od tego czasu (\d+) cm", f.get("reason", ""))
        if f["kind"] == "nie_wiem" and m:
            subs[f["sector"]] = f"nie wiem: pomiar {m.group(1)} h temu, +{m.group(2)} cm"
    plan = e.get("plan") or {}
    meta = dict(subs=subs, tag=e.get("label", ""),
                subtitle=f"{e.get('status', '')} · wynik silnika demo na {e.get('library_count')} symulacjach AvaFrame"
                         f" · przelot {plan.get('minutes', '?')} min · stan śniegu syntetyczny")
    return hz, uk, plan.get("path"), e.get("base"), meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("assets")
    ap.add_argument("out")
    ap.add_argument("mode", choices=["still", "video", "preview"])
    ap.add_argument("--hazard", default="S31,S10")
    ap.add_argument("--unknown", default="S21,S22,S35")
    ap.add_argument("--base", default="278,69.2")
    ap.add_argument("--flags", help="JSON from engine_flags.mjs")
    ap.add_argument("--azim", type=float, default=72)
    ap.add_argument("--elev", type=float, default=35)
    ap.add_argument("--zoom", type=float, default=1.3)
    ap.add_argument("--seconds", type=float, default=18)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--up", type=float, default=1.5)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sweep", type=float, default=44)
    o = ap.parse_args()
    hazard, unknown = o.hazard.split(","), o.unknown.split(",")
    base = [float(v) for v in o.base.split(",")]
    route_pts, meta = None, {}
    if o.flags:
        hazard, unknown, route_pts, b, meta = flags_from_engine(o.flags)
        base = b or base
    out = Path(o.out)
    out.mkdir(parents=True, exist_ok=True)
    A0 = vc.Assets(o.assets)
    route = [tuple(p) for p in route_pts] if route_pts else route_path(A0, base, unknown)
    if o.mode in ("still", "preview"):
        W, H, up = (3840, 2160, 3) if o.mode == "still" else (960, 540, 1)
        init(o.assets, hazard, unknown, base, route, up, W, H, meta)
        name = "koncepcja_3d.png" if o.mode == "still" else "prev_koncepcja.png"
        frame(o.azim, o.elev, o.zoom, out / name)
        print("ok", out / name)
    else:
        fd = out / "koncepcja_frames"
        fd.mkdir(exist_ok=True)
        n = int(o.seconds * o.fps)
        jobs = []
        for i in range(n):
            u = i / (n - 1)
            e = 0.5 - 0.5 * np.cos(np.pi * u)  # ease in-out
            jobs.append((i, o.azim - o.sweep / 2 + o.sweep * e, o.elev + 3 - 6 * e, o.zoom, str(fd)))
        with Pool(o.workers, initializer=init, initargs=(o.assets, hazard, unknown, base, route, o.up, 1920, 1080, meta)) as p:
            for i in p.imap_unordered(vframe, jobs, chunksize=4):
                if i % 50 == 0:
                    print("frame", i, flush=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(o.fps), "-i", str(fd / "f_%04d.png"),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "6",
                        "-movflags", "+faststart", str(out / "koncepcja_orbit.mp4")], check=True)
        print("ok", out / "koncepcja_orbit.mp4")

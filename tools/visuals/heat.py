"""Library reach map: how many AvaFrame library runs reach each 10 m cell (library_heat.bin, Uint16),
draped on the 3D massif; trail segments hit by at least one run get a dark halo (from scenarios.json hits).

Usage: python heat.py <assetsDir> <heat.bin> <scenarios.json> <outDir> still|video|preview [--seconds 16]
"""

import argparse
import json
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import vis_common as vc

G = {}
HEAT = [(0.0, (255, 226, 160)), (0.35, (249, 160, 63)), (0.65, (214, 82, 10)), (1.0, (96, 30, 4))]


def ramp(u):
    u = np.clip(u, 0, 1)
    out = np.zeros(u.shape + (3,), np.float32)
    for (a, ca), (b, cb) in zip(HEAT, HEAT[1:]):
        m = (u >= a) & (u <= b)
        t = ((u - a) / (b - a))[m][:, None]
        out[m] = np.array(ca) * (1 - t) + np.array(cb) * t
    return out


def build(A, heat, hit_segs):
    base = Image.open(A.dir / "map.png").convert("RGB")
    k = base.width * 2 // A.n
    img = base.resize((A.n * k, A.n * k), Image.LANCZOS)
    hmax = max(1, int(heat.max()))
    h = ndimage.zoom(heat.astype(np.float32), k, order=1)
    u = np.sqrt(np.clip(h, 0, None) / hmax)
    a = np.where(h >= 0.5, 0.5 + 0.4 * u, 0.0)[..., None]
    arr = np.asarray(img, np.float32)
    arr = arr * (1 - a) + ramp(u) * a
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    for tr in A.trails:  # dark halo under segments that at least one run reaches
        for sg in tr.get("segments", []):
            if sg["id"] in hit_segs:
                pts = [(c * k, r * k) for c, r in tr["paths"][sg["part"]][sg["from"]:sg["to"] + 1]]
                d.line(pts, fill=vc.INK, width=int(3.2 * k), joint="curve")
    A.draw_trails(img, k, w_white=int(1.5 * k), w_col=int(0.9 * k))
    return img, hmax


def init(assets, heat_p, scen_p, up, W, H):
    A = vc.Assets(assets)
    heat = np.fromfile(heat_p, dtype="<u2").reshape(A.z.shape)
    sc = json.loads(Path(scen_p).read_text(encoding="utf-8"))
    runs = sc.get("runs") or sc.get("items") or []
    hit_segs = {h for r in runs for h in r.get("hits", [])}
    n_hit = sum(1 for r in runs if r.get("hits"))
    tex, hmax = build(A, heat, hit_segs)
    S = vc.Surface(A, None, up=up)
    n = int(sc.get("count", len(runs)))
    th = sorted(sc.get("thicknesses") or {r["relTh"] for r in runs})
    fr = sc.get("frictions") or sorted({r["frict"] for r in runs})
    pf = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    G.update(A=A, S=S, rgb=S.texture(tex), hmax=hmax, n=n, n_hit=n_hit, n_sect=len({r["sector"] for r in runs}),
             th=f"płyta {pf(th[0])}–{pf(th[-1])} m" if th else "", n_fr=len(fr), thr=pf(sc.get("threshold_pft_m", 0.1)),
             W=W, H=H, partial="partial" in str(sc.get("computed_on", "")))


def frame(azim, elev, zoom, out):
    A, S, W, H = G["A"], G["S"], G["W"], G["H"]
    img, _ = S.render(G["rgb"], W, H, azim, elev, zoom=zoom, axrect=(-0.12, -0.2, 1.24, 1.4))
    hmax = G["hmax"]

    def legend(d, x, y, s):
        f = A.font(19 * s, 650)
        d.text((x, y - 4 * s), "Ile symulacji dociera", font=f, fill=vc.INK, anchor="lm")
        x += d.textlength("Ile symulacji dociera", font=f) + 18 * s
        ticks = sorted({1, 10, 50, hmax} - {t for t in (10, 50) if t >= hmax})
        wbar = 240 * s
        u = np.linspace(0, 1, int(wbar))
        cols = ramp(u)
        for i, c in enumerate(cols):
            d.line([(x + i, y - 18 * s), (x + i, y + 2 * s)], fill=tuple(int(v) for v in c))
        for t in ticks:
            tx = x + wbar * np.sqrt(t / hmax)
            d.line([(tx, y + 2 * s), (tx, y + 7 * s)], fill=vc.INK, width=max(1, int(2 * s)))
            d.text((tx, y + 18 * s), str(t), font=A.font(15 * s, 600), fill=vc.INK, anchor="mm")
        x += wbar + 40 * s
        d.line([(x, y - 8 * s), (x + 46 * s, y - 8 * s)], fill=vc.INK, width=int(13 * s))
        d.line([(x, y - 8 * s), (x + 46 * s, y - 8 * s)], fill=(255, 255, 255), width=int(7 * s))
        d.line([(x, y - 8 * s), (x + 46 * s, y - 8 * s)], fill=vc.TRAIL["blue"], width=int(4 * s))
        d.text((x + 58 * s, y - 8 * s), "szlak w zasięgu lawin", font=f, fill=vc.INK, anchor="lm")
        return x

    n = G["n"]
    kal = {1: "kalibracja", 2: "kalibracje", 3: "kalibracje", 4: "kalibracje"}.get(G["n_fr"], "kalibracji")
    ns = G["n_sect"]
    sub = (f"{ns} {vc.pl(ns, 'strefa startowa', 'strefy startowe', 'stref startowych')} · {G['th']} · {G['n_fr']} {kal} tarcia · {G['n_hit']} z {n} symulacji dochodzi do szlaku"
           f" · zasięg: przepływ ≥ {G['thr']} m")
    if G["partial"]:
        sub += " · biblioteka w trakcie liczenia"
    vc.strips(img, A, f"{n} {vc.pl(n, 'symulacja', 'symulacje', 'symulacji')} AvaFrame: gdzie lawiny dochodzą do szlaków", sub, legend=legend)
    img.save(out)


def vframe(a):
    i, azim, elev, zoom, fd = a
    frame(azim, elev, zoom, Path(fd) / f"f_{i:04d}.png")
    return i


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("assets")
    ap.add_argument("heat")
    ap.add_argument("scenarios")
    ap.add_argument("out")
    ap.add_argument("mode", choices=["still", "video", "preview"])
    ap.add_argument("--azim", type=float, default=72)
    ap.add_argument("--elev", type=float, default=38)
    ap.add_argument("--zoom", type=float, default=1.3)
    ap.add_argument("--seconds", type=float, default=16)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--up", type=float, default=1.5)
    ap.add_argument("--workers", type=int, default=5)
    o = ap.parse_args()
    out = Path(o.out)
    out.mkdir(parents=True, exist_ok=True)
    if o.mode in ("still", "preview"):
        W, H, up = (3840, 2160, 3) if o.mode == "still" else (1920, 1080, 1)
        init(o.assets, o.heat, o.scenarios, up, W, H)
        name = "mapa_zasiegow.png" if o.mode == "still" else "prev_mapa_zasiegow.png"
        frame(o.azim, o.elev, o.zoom, out / name)
        print("ok", out / name)
    else:
        fd = out / "zasiegi_frames"
        fd.mkdir(exist_ok=True)
        nfr = int(o.seconds * o.fps)
        jobs = []
        for i in range(nfr):
            e = 0.5 - 0.5 * np.cos(np.pi * i / (nfr - 1))
            jobs.append((i, o.azim + 30 - 60 * e, o.elev - 4 + 8 * e, o.zoom, str(fd)))
        with Pool(o.workers, initializer=init, initargs=(o.assets, o.heat, o.scenarios, o.up, 1920, 1080)) as p:
            for i in p.imap_unordered(vframe, jobs, chunksize=4):
                if i % 50 == 0:
                    print("frame", i, flush=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(o.fps), "-i", str(fd / "f_%04d.png"),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "6",
                        "-movflags", "+faststart", str(out / "mapa_zasiegow_orbit.mp4")], check=True)
        print("ok", out / "mapa_zasiegow_orbit.mp4")

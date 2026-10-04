"""Collages for the pitch video (ffmpeg xstack), 3840x2160.

  3d_przeglad.mp4: 4x3 grid of 3D AvaFrame videos (6 sectors x 2 variants; S21/S27 left out: their old crop
                   showed the flat no-data wall south of the border). Shorter clips loop.
  2d_mozaika.mp4:  4x2 grid of the 3x3 parameter matrices (8 sectors x 9 runs = 72 simulations).

Usage: python collage.py <assetsDir> <renders3dDir> <renders2dDir> <outDir>
"""

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import vis_common as vc

W, H = 3840, 2160
SECT3D = os.environ.get("SECT3D", "S10,S14,S17,S22,S29,S31").split(",")
VAR3D = [("samosATMedium_1.3", "płyta 1,3 m · tarcie średnich lawin"), ("samosAT_2.0", "płyta 2,0 m · tarcie dużych lawin")]
SECT2D = ["S10", "S14", "S17", "S21", "S22", "S27", "S29", "S31"]


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def header(A, img, title, sub, legend=True):
    s = 2.0
    d = ImageDraw.Draw(img, "RGBA")
    d.text((48 * s, 40 * s), title, font=A.font(40 * s, 800, 112), fill=vc.INK, anchor="lm")
    d.text((48 * s, 74 * s), sub, font=A.font(20 * s, 500), fill=vc.INK2, anchor="lm")
    if legend:
        x = W - 48 * s - 5 * 76 * s
        d.text((x - 16 * s, 34 * s), "Grubość przepływu", font=A.font(20 * s, 700), fill=vc.INK, anchor="rm")
        for v, c in vc.RAMP:
            d.rectangle((x, 24 * s, x + 64 * s, 44 * s), fill=c)
            d.text((x + 32 * s, 54 * s), f"{v:g} m".replace(".", ","), font=A.font(14 * s, 600), fill=vc.INK, anchor="mm")
            x += 76 * s
    d.text((W - 48 * s, 76 * s), vc.CREDIT, font=A.font(16 * s, 500), fill=vc.INK2, anchor="rm")
    return d


def encode(cmd, out):
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-threads", "6",
            "-movflags", "+faststart", str(out)]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_threads", "6"] + cmd, check=True)
    print("ok", out, flush=True)


def collage3d(A, src, out):
    names = {s: A.sectors[s]["name"] for s in SECT3D}
    vids = [(s, v, lab) for s in SECT3D for v, lab in VAR3D]
    files = [src / f"3d_{s}_{v}.mp4" for s, v, _ in vids]
    T = max(dur(f) for f in files)
    rows = -(-len(vids) // 4)
    top, tw = 180, 960
    th = (H - top) // rows // 2 * 2
    cw = int(round(880 * tw / th / 2)) * 2  # crop of the 3D area (y 119..999) with the tile aspect
    cw = min(cw, 1920)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((0, 0, W, top), fill=(*vc.PAPER, 255))
    nv, ns = len(vids), len(SECT3D)
    header(A, ov, f"{nv} {vc.pl(nv, 'lawina', 'lawiny', 'lawin')} AvaFrame w 3D na terenie Hali Gąsienicowej",
           f"{ns} {vc.pl(ns, 'strefa startowa', 'strefy startowe', 'stref startowych')} × 2 warianty płyty i tarcia · przewyższenie 1,25×")
    for i, (s, v, lab) in enumerate(vids):
        x, y = (i % 4) * tw, top + (i // 4) * th
        d.text((x + 24, y + 30), names[s], font=A.font(34, 800, 112), fill=vc.INK, anchor="lm")
        d.text((x + 24, y + 66), lab, font=A.font(22, 600), fill=vc.INK2, anchor="lm")
    for c in range(1, 4):
        d.rectangle((c * tw - 3, top, c * tw + 3, H), fill=(*vc.PAPER2, 255))
    for r in range(1, rows):
        d.rectangle((0, top + r * th - 3, W, top + r * th + 3), fill=(*vc.PAPER2, 255))
    ovp = out.parent / "_ov3d.png"
    ov.save(ovp)
    inputs, chains = [], []
    for i, f in enumerate(files):
        inputs += ["-stream_loop", "-1", "-i", str(f)]
        # drop the per-video strips, keep the centre of the 3D view, shorter clips loop
        chains.append(f"[{i}:v]trim=duration={T:.2f},setpts=PTS-STARTPTS,"
                      f"crop={cw}:880:{(1920 - cw) // 2}:119,scale={tw}:{th},setsar=1[v{i}]")
    layout = "|".join(f"{(i % 4) * tw}_{(i // 4) * th}" for i in range(len(files)))
    fc = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(len(files))) + \
        f"xstack=inputs={len(files)}:layout={layout}[g];[g]pad={W}:{H}:0:{top}:color=0xf4efe4[p];[p][{len(files)}:v]overlay=0:0,fps=30"
    encode(inputs + ["-loop", "1", "-i", str(ovp), "-filter_complex", fc, "-t", f"{T:.2f}"], out)


def mosaic2d(A, src, out):
    files = [src / f"macierz_{s}.mp4" for s in SECT2D]
    T = max(dur(f) for f in files) + 2.0
    top, tw, th = 160, 960, 1000
    ov = Image.new("RGBA", (W, H), (*vc.PAPER, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((0, 0, W, top), fill=(*vc.PAPER, 255))
    header(A, ov, "72 symulacje AvaFrame com1DFA: 8 stref × 3 grubości płyty × 3 kalibracje tarcia",
           "Każdy kafel: jedna strefa startowa. Wiersze: tarcie małych, średnich, dużych lawin. Kolumny: płyta 0,6 / 1,3 / 2,0 m.",
           legend=False)
    ovp = out.parent / "_ov2d.png"
    ov.save(ovp)
    inputs, chains = [], []
    for i, f in enumerate(files):
        inputs += ["-i", str(f)]
        chains.append(f"[{i}:v]tpad=stop_mode=clone:stop_duration={T:.2f},trim=duration={T:.2f},setpts=PTS-STARTPTS,"
                      f"scale=-2:{th - 16},pad={tw}:{th}:(ow-iw)/2:8:color=0xebe4d4,setsar=1[v{i}]")
    layout = "|".join(f"{(i % 4) * tw}_{(i // 4) * th}" for i in range(len(files)))
    fc = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(len(files))) + \
        f"xstack=inputs={len(files)}:layout={layout}[g];[g]pad={W}:{H}:0:{top}:color=0xebe4d4[p];[p][{len(files)}:v]overlay=0:0,fps=30"
    encode(inputs + ["-loop", "1", "-i", str(ovp), "-filter_complex", fc, "-t", f"{T:.2f}"], out)


if __name__ == "__main__":
    assets, r3, r2, outd = (Path(a) for a in sys.argv[1:5])
    outd.mkdir(parents=True, exist_ok=True)
    A = vc.Assets(assets)
    which = sys.argv[5] if len(sys.argv) > 5 else "both"
    if which in ("both", "3d"):
        collage3d(A, r3, outd / "3d_przeglad.mp4")
    if which in ("both", "2d"):
        mosaic2d(A, r2, outd / "2d_mozaika.mp4")

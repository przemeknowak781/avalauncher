"""Short MP4 of the best calibration run: flow thickness over time on the hillshade, observed outline dashed.

Step 1 (Spark): python anim_calib.py pack <runDir> <out.npz>   (FT_t*.asc from peakFiles/timeSteps -> npz)
Step 2 (laptop): python tools/calibration/anim_calib.py render <work>/ft.npz <work>/dem.tif
Output: filmy/kalibracja/najlepszy_przebieg.mp4
"""

import re
import sys
from pathlib import Path

import numpy as np


def pack(run, out):
    import rasterio
    files = sorted(Path(run).glob("Outputs/com1DFA/peakFiles/timeSteps/*_FT_t*.asc"),
                   key=lambda p: float(re.search(r"_t([\d.]+)\.asc$", p.name).group(1)))
    ts = [float(re.search(r"_t([\d.]+)\.asc$", p.name).group(1)) for p in files]
    stack = []
    for p in files:
        with rasterio.open(p) as r:
            stack.append(r.read(1).astype("float16"))
    np.savez_compressed(out, ft=np.stack(stack), t=np.array(ts))
    print(len(files), "frames", ts[:3], ts[-1])


def render(npz, dem_tif):
    import imageio_ffmpeg
    import matplotlib
    matplotlib.use("Agg")
    import rasterio
    from PIL import Image, ImageDraw
    sys.path.insert(0, str(Path(__file__).parent))
    import board_calib as B

    z = np.load(npz)
    ft, ts = z["ft"].astype("float32"), z["t"]
    with rasterio.open(dem_tif) as r:
        dem, tr = r.read(1), r.transform
    W, H = 1080, 1350
    ph = 1180
    pw = int(ph * (B.XMAX - B.XMIN) / (B.YMAX - B.YMIN))
    base_bg = B.panel(dem, tr, None, pw, ph)
    out = B.ROOT / "filmy" / "kalibracja" / "najlepszy_przebieg.mp4"
    w = imageio_ffmpeg.write_frames(str(out), (W, H), fps=12, macro_block_size=8,
                                    output_params=["-crf", "20", "-pix_fmt", "yuv420p"])
    w.send(None)
    peak = np.zeros_like(ft[0])
    for k in range(len(ts)):
        peak = np.maximum(peak, ft[k])
        im = B.panel(dem, tr, ft[k], pw, ph) if ft[k].max() > 0.1 else base_bg
        img = Image.new("RGB", (W, H), B.PAPER)
        img.paste(im, (60, 120))
        d = ImageDraw.Draw(img)
        d.text((60, 36), "Popeletzbach, 7.04.2009: najlepszy przebieg kalibracji", font=B.font(34, 750), fill=B.INK)
        d.text((60, 80), "samosAT, odryw 0,6 m · grubość przepływu w czasie · linia przerywana: obserwowany zasięg",
               font=B.font(18, 450), fill=B.INK2)
        tx = 60 + pw + 40
        d.text((tx, 140), f"t = {ts[k]:.0f} s", font=B.font(44, 750), fill=B.INK)
        d.text((tx, 200), f"maks. grubość teraz: {B.pl(float(ft[k].max()), 1)} m", font=B.font(18, 500), fill=B.INK2)
        d.text((tx, H - 90), "Symulacja AvaFrame com1DFA na terenie\nLand Tirol 5 m (CC BY 4.0 AT).\n"
               "Zdarzenie: OpenNHM/AvaFrameData, CC BY 4.0.", font=B.font(15, 450), fill=B.INK2)
        frame = np.asarray(img)
        for _ in range(2 if k < len(ts) - 1 else 24):
            w.send(frame.tobytes())
    w.close()
    print("saved", out)


if __name__ == "__main__":
    if sys.argv[1] == "pack":
        pack(sys.argv[2], sys.argv[3])
    else:
        render(sys.argv[2], sys.argv[3])

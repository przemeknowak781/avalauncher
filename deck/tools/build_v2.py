"""Deck v2 (deck/storyboard.md): crops of the app screenshots, slide-3 tiles and the five
calibration panels with the leave-one-out run drawn in hazard orange (no in-sample best-fit blob),
so the slide-7 caption "pomarańcz: obliczenie" refers to the run behind the 92 m median."""
import inspect
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deck" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, src, box=None, width=None, q=90):
    im = Image.open(ROOT / src).convert("RGB")
    if box:
        im = im.crop(box)
    if width and width != im.width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(OUT / name, "JPEG", quality=q, optimize=True, progressive=True)
    print(name, im.size, (OUT / name).stat().st_size // 1024, "KB")


# big screenshots (source 1440 x 860), full width, cut vertically
save("v2_s1.jpg", "docs/img/krok1_mapa.png", (0, 76, 1440, 651), q=92)
save("v2_s4.jpg", "docs/img/krok2_stok.png", (0, 0, 1440, 600), q=92)
save("v2_s5.jpg", "docs/img/dzien2_mgla.png", (0, 76, 1440, 676), q=92)
save("v2_s6.jpg", "docs/img/dzien2_mgla.png", (0, 138, 1440, 758), q=92)
# slide 3 tiles, 4:3
save("v2_t2.jpg", "filmy/hero/mapa_zasiegow.png", (620, 300, 2780, 1920), 720, q=86)
save("v2_t3.jpg", "docs/img/krok1_mapa.png", (60, 90, 640, 525), 720, q=90)
# slide 10: start screen, small
save("v2_s10.jpg", "docs/img/logowanie.png", None, 960, q=88)

# slide 7: five panels, observed outline dashed + leave-one-out run in orange
sys.path.insert(0, str(ROOT / "tools" / "calibration"))
import board_multi as bm  # noqa: E402

src = inspect.getsource(bm.panel)
src = src.replace("colors=[LOO_C], linewidths=1.7", "colors=['#e8590c'], linewidths=7.0")
src = src.replace('color="#1d1b17", lw=2.0, dashes=(4, 2.5)', 'color="#1d1b17", lw=3.0, dashes=(3.2, 2.2)')
src = src.replace('edgecolor="#1d1b17", lw=1.2', 'edgecolor="#1d1b17", lw=1.8')
exec(src, bm.__dict__)
W, H = 480, 672
for k, ev in enumerate(bm.EV, 1):
    z = dict(np.load(bm.NPZ / f"{ev}.npz"))
    z["pft_best"] = np.zeros_like(z["pft_best"])
    im, mpp, _ = bm.panel(ev, z, W, H)
    if ev == "avaPopeletzbach":
        im = im.crop((52, 0, 448, H))
    im.convert("RGB").save(OUT / f"v2_p{k}.jpg", "JPEG", quality=90, optimize=True)
    print(ev, im.size)

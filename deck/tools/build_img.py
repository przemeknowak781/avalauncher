"""Crops and compresses every image the deck uses into deck/img/ (JPG, <= 1920 px wide).
Crops follow docs/11_deck.md: numbers that are not in docs/12 are cut out of the frame."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deck" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, src, box=None, width=None, q=85):
    im = Image.open(ROOT / src).convert("RGB")
    if box:
        im = im.crop(box)
    w = min(width or im.width, 1920)
    if w != im.width:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(OUT / name, "JPEG", quality=q, optimize=True, progressive=True)
    print(name, im.size, (OUT / name).stat().st_size // 1024, "KB")


# slide 1: re-rendered panel (deck/tools/popeletzbach.py), no best-fit blob
save("s1_popeletzbach.jpg", "deck/img/popeletzbach_hd.png", q=88)
# slide 2: hero S22 without the title band ("t = 34 s") and the legend strip
save("s2_hero_s22.jpg", "filmy/hero/hero_S22_samosAT_2.0_mid.png", (442, 240, 3514, 2006), 1800)
# slide 3: three steps, cropped to the part of the screen that carries the step
save("s3_krok1.jpg", "docs/img/krok1_mapa.png", (110, 110, 590, 517), 960, q=90)
save("s3_krok2.jpg", "docs/img/krok2_stok.png", (692, 8, 1076, 334), 768, q=90)
save("s3_krok3_mapa.jpg", "docs/img/krok3_trasa.png", (200, 140, 640, 420), 880, q=90)
save("s3_krok3_suwak.jpg", "docs/img/krok3_trasa.png", (676, 628, 1010, 716), 668, q=90)
# slide 4: day 2 before and after the 20 min flight, map window only
save("s4_dzien2.jpg", "docs/img/dzien2_mgla.png", (150, 168, 640, 478), 980, q=90)
save("s4_po_przelocie.jpg", "docs/img/po_przelocie.png", (150, 168, 640, 478), 980, q=90)
# slide 5: natural-colour panel only (the board header with "4 x 4 km" is cut)
save("s5_sentinel.jpg", "filmy/satelita/porownanie.png", (31, 177, 630, 776))
# slide 6: now five separate panels from deck/tools/five_panels.py (names and results set in HTML);
# the old board crop is kept for reference only
# slide 6 (old): panels + leave-one-out rows; "NAJLEPSZY PRZEBIEG" rows and the "94 m" line are cut
save("s6_5_lawin.jpg", "filmy/kalibracja/5_lawin.png", (50, 185, 1900, 866))
# slide 7: Sucha Dolina NE row only (tiles), without the row label that carries IoU 0,70 / 27;
# the small tile chips are cut too, the slide sets the three tile names in large type
save("s7_surogat.jpg", "filmy/surrogate/porownanie.png", (40, 1043, 1873, 1592))
# slide 9: range map without the subtitle ("1291 z 1566") and the legend
save("s9_mapa.jpg", "filmy/hero/mapa_zasiegow.png", (380, 235, 3460, 2000), 1920, q=80)
# slide 10: 3D frame of the same slope, without title and timer
save("s10_3d.jpg", "web/media/3d/S22_samosAT_2.0.jpg", (330, 118, 950, 672), q=85)

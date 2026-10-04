"""Board: leave-one-out runout error per event, variant without forest (round 1) vs with forest + entrainment.

Input:  web/data/calibration.json, key "variants" (loo_calib_las.py): bez_lasu, las_porywanie
Usage:  python tools/calibration/board_variants.py [--out PATH]
Output: filmy/kalibracja/porownanie_wariantow.png (1920x1080), paper #f4efe4, Archivo, same type scale as board_multi.py
Colours: bez lasu #2f6ea5, z lasem #c44808 (dataviz validate_palette.js on #f4efe4: all six checks pass).
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from board_multi import EV, H, INK, INK2, ORANGE_TXT, PAPER, ROOT, W, font, text_block
from loo_calib import fr_pl

OUT = ROOT / "filmy" / "kalibracja" / "porownanie_wariantow.png"
C_R1, C_LAS = (47, 110, 165), (196, 72, 8)
BAND = (231, 224, 210)  # +-100 m band, ink at ~7% on paper
GRID = (214, 206, 190)


def pl(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def signed(v):
    return f"{'+' if v >= 0 else '−'}{pl(abs(v))}"


def setting(fr):
    return fr_pl(fr).replace(" m/s²", "").replace("ξ", "xi").replace(" (μ 0,155)", "")


def bar(d, x0, x1, yz, yv, fill):
    """Bar from the zero line yz to yv, 4 px rounded at the data end only."""
    top, bot = min(yz, yv), max(yz, yv)
    if bot - top < 1:
        return
    d.rounded_rectangle([x0, top, x1, bot], radius=min(4, (bot - top) / 2), fill=fill)
    if yv < yz:  # positive: square the baseline end
        d.rectangle([x0, max(top, bot - 4), x1, bot], fill=fill)
    else:
        d.rectangle([x0, top, x1, min(bot, top + 4)], fill=fill)


def main(out=None):
    cal = json.loads((ROOT / "web" / "data" / "calibration.json").read_text(encoding="utf-8"))
    A, B = cal["variants"]["bez_lasu"], cal["variants"]["las_porywanie"]
    ea, eb = A["runout_error_loo_m"], B["runout_error_loo_m"]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Z lasem i porywaniem śniegu: średni błąd bez zmian, mediana gorsza", font=font(42, 750),
           fill=INK)
    sub = ("Błąd długości zasięgu (m) w teście leave-one-out (ustawienie wybrane bez danego zdarzenia), ta sama reguła i "
           f"siatka {B['n_runs']} symulacji. Plus: za daleko, minus: za krótko.")
    assert d.textlength(sub, font=font(21, 450)) <= W - 120
    d.text((60, 94), sub, font=font(21, 450), fill=INK2)
    # legend
    f = font(17, 500)
    x, y = 60, 140
    for c, lab in ((C_R1, "bez lasu i porywania"), (C_LAS, "z lasem i porywaniem z danych zdarzeń (parametry domyślne, "
                                                           "niestrojone)")):
        d.rounded_rectangle([x, y, x + 22, y + 18], radius=4, fill=c)
        d.text((x + 32, y + 9), lab, font=f, fill=INK, anchor="lm")
        x += 32 + int(d.textlength(lab, font=f)) + 40
    d.rectangle([x, y, x + 22, y + 18], fill=BAND)
    d.text((x + 32, y + 9), "pas ±100 m", font=f, fill=INK, anchor="lm")
    # plot geometry
    px0, px1, py0, py1 = 140, 1340, 210, 820
    vmin, vmax = -260.0, 380.0

    def yv(v):
        return py0 + (vmax - v) / (vmax - vmin) * (py1 - py0)

    d.rectangle([px0, yv(100), px1, yv(-100)], fill=BAND)
    for g in range(-200, 400, 100):
        if g:
            d.line([px0, yv(g), px1, yv(g)], fill=GRID, width=1)
        d.text((px0 - 14, yv(g)), f"{'+' if g > 0 else '−' if g < 0 else ''}{abs(g)} m", font=font(15, 500),
               fill=INK2, anchor="rm")
    d.line([px0, yv(0), px1, yv(0)], fill=INK, width=2)
    gw = (px1 - px0) / len(EV)
    bw, gap = 74, 2
    for k, e in enumerate(EV):
        cx = px0 + gw * (k + 0.5)
        for j, (v, c) in enumerate(((ea[e], C_R1), (eb[e], C_LAS))):
            x0 = cx - bw - gap / 2 if j == 0 else cx + gap / 2
            bar(d, x0, x0 + bw, yv(0), yv(v), c)
            lab = signed(v)
            fy = yv(v) - 8 if v >= 0 else yv(v) + 8
            d.text((x0 + bw / 2, fy), lab, font=font(18, 700), fill=INK, anchor="mb" if v >= 0 else "mt")
        name = B["inputs"][e]["name"]
        ly = py1 + 18
        d.text((cx, ly + 22), name, font=font(22, 750), fill=INK, anchor="ms")
        lo = B["loo"][e]
        inp = f"opór + porywanie ({pl(B['inputs'][e]['ent_th_m'])} m)" if B["inputs"][e]["ent_th_m"] else "las"
        rows = [(f"bez lasu: {setting(lo['round1_setting'])}", INK2),
                (f"z lasem: {setting(lo['setting'])}", INK2),
                (f"z danych: {inp}", INK2)]
        for i, (t, c) in enumerate(rows):
            d.text((cx, ly + 32 + 20 * i), t, font=font(14, 450), fill=c, anchor="mt")
    # stat tiles
    tx, tw = 1420, 440
    tiles = [
        ("ŚREDNI BŁĄD ZASIĘGU", A["mean_abs_runout_error_loo_m"], B["mean_abs_runout_error_loo_m"], 1, " m"),
        ("MEDIANA BŁĘDU", A["median_abs_runout_error_loo_m"], B["median_abs_runout_error_loo_m"], 0, " m"),
        (f"W GRANICACH {B['within_100m']['threshold_m']} M", A["within_100m"]["n"], B["within_100m"]["n"], None,
         f" z {B['within_100m']['of']}"),
    ]
    ty = 210
    for title, a, b, nd, unit in tiles:
        d.rounded_rectangle([tx, ty, tx + tw, ty + 170], radius=6, outline=GRID, width=2)
        d.text((tx + 24, ty + 20), title, font=font(15, 750, 110), fill=ORANGE_TXT)
        for i, (val, c, lab) in enumerate(((a, C_R1, "bez lasu"), (b, C_LAS, "z lasem"))):
            yy = ty + 56 + 54 * i
            d.rounded_rectangle([tx + 24, yy + 10, tx + 40, yy + 26], radius=4, fill=c)
            d.text((tx + 52, yy + 18), lab, font=font(18, 500), fill=INK2, anchor="lm")
            txt = (pl(val, nd) if nd else f"{val:.0f}") + unit if nd is not None else f"{val}{unit}"
            d.text((tx + tw - 24, yy + 18), txt, font=font(36, 780), fill=INK, anchor="rm")
        ty += 190
    # takeaway + caveats
    ys = 960
    d.line([60, ys - 14, W - 60, ys - 14], fill=INK2, width=1)
    gs = setting(B["best_global_setting"]["setting"])
    fil = [eb["avaFilisur1"], eb["avaFilisur2"]]
    pick = sum(1 for h in EV if B["loo"][h]["setting"] == B["best_global_setting"]["setting"])
    head = (f"Las poprawia dopasowanie w próbie, więc trening w {pick} z {len(EV)} "
            f"prób wybiera {gs}, a ono przestrzeliwuje oba Filisur ({signed(fil[0])} i {signed(fil[1])} m).")
    ys = text_block(d, 60, ys, head, font(19, 650), INK, W - 120, 25)
    care = ("Uczciwie: las i porywanie tylko z danych zdarzeń OpenNHM/AvaFrameData 1.0 (DOI 10.5281/zenodo.20701552, "
            "CC BY 4.0), parametry domyślne AvaFrame 2.1, niestrojone; porywanie tylko na Eiskar, grubość 0,3 m "
            "domyślna. Grubość odrywu zmierzona tylko na Eiskar (2,7 m), dla reszty 1,2 m. To przykładowa kalibracja "
            "na zdarzeniach z Austrii i Szwajcarii, nie dla Tatr.")
    text_block(d, 60, ys + 2, care, font(15, 450), INK2, W - 120, 20)
    out = Path(out) if out else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("saved", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[a.index("--out") + 1] if "--out" in a else None)

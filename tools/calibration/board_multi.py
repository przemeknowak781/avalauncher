"""Board: AvaFrame on 5 observed avalanches, best run per event + the leave-one-out result.

Inputs: data/avaframe/calib_loo.json (loo_calib.py), web/data/calibration.json (events block),
        data/avaframe/board_multi/<event>.npz (export_board_multi.py on the Spark),
        observed outlines from data/raw/avaframedata (+ data/raw/calib_events/avaEiskar for ESK_1).
Usage:  python tools/calibration/board_multi.py [--variant las_porywanie] [--out PATH]
Output: filmy/kalibracja/5_lawin.png (1920x1080)
Variant las_porywanie (same layout): data/avaframe/calib_loo_las.json (loo_calib_las.py), best rows from
        calib_results_las_best.json, data/avaframe/board_multi_las/<event>.npz (export_board_multi.py --runs runs_las,
        with the dataset forest/resistance mask and the Eiskar entrainment mask drawn on the panels)
        -> filmy/kalibracja/5_lawin_las.png
"""

import io
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource, LinearSegmentedColormap, Normalize  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "avaframedata" / "OpenNHM-AvaFrameData-fa839ca"
ESK = ROOT / "data" / "raw" / "calib_events" / "avaEiskar"
NPZ = ROOT / "data" / "avaframe" / "board_multi"
FONT = ROOT / "web" / "vendor" / "fonts" / "Archivo-var.ttf"
OUT = ROOT / "filmy" / "kalibracja" / "5_lawin.png"
PAPER, INK, INK2, ORANGE_TXT, LOO_C = (244, 239, 228), (29, 27, 23), (110, 101, 86), (196, 72, 8), "#3b1000"
CMAP = LinearSegmentedColormap.from_list("ava", ["#ffd6aa", "#e8590c", "#5a1a00"])
NORM = Normalize(0.1, 2.5, clip=True)
FOREST_C, ENT_C = "#4d6b3c", "#1f4e79"  # las_porywanie only: dataset forest / resistance fill, entrainment outline
AV = ROOT / "data" / "avaframe"
W, H = 1920, 1080
EV = ["avaPopeletzbach", "avaKleinerOetscherbach", "avaEiskar", "avaFilisur1", "avaFilisur2"]
OUTLINES = {  # observed outline (dashed), release (hatched)
    "avaPopeletzbach": (RAW / "avaPopeletzbach/eventArea20090407.shp", RAW / "avaPopeletzbach/releaseArea20090407.shp"),
    "avaKleinerOetscherbach": (RAW / "avaKleinerOetscherbach/eventArea20090225.shp",
                               RAW / "avaKleinerOetscherbach/releaseArea20090225.shp"),
    "avaEiskar": (ESK / "observed/depositionDFAOutline.shp", ESK / "Inputs/REL/relESK1.shp"),
    "avaFilisur1": (RAW / "avaFilisur1/avaFilisur1_deposition_area.gpkg", RAW / "avaFilisur1/avaFilisur1_release_area.gpkg"),
    "avaFilisur2": (RAW / "avaFilisur2/avaFilisur2_deposition_area.gpkg", RAW / "avaFilisur2/avaFilisur2_release_area.gpkg"),
}
DATE_PL = {"2009-04-07": "7.04.2009", "2009-02-25": "25.02.2009", "2019-01-15": "15.01.2019", "2012-02-23": "23.02.2012"}
SHORT = {"avaPopeletzbach": "mokra lawina", "avaKleinerOetscherbach": "sucha lawina płynąca",
         "avaEiskar": "sucha, z chmurą pyłową", "avaFilisur1": "mokra, zatrzymana przez las",
         "avaFilisur2": "mokra, zatrzymana przez las"}


def font(size, weight=500, width=100):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight, width])
    return f


def pl(x, nd=2):
    return f"{x:.{nd}f}".replace(".", ",")


def signed(v):
    return f"{'+' if v >= 0 else '−'}{abs(v):.0f} m"


def setting_pl(r):
    if r["frictModel"] == "Voellmy":
        return f"Voellmy μ {pl(r['mu'])}, xi {int(r['xsi'])}"
    return f"{r['frictModel']} (μ {pl(r['mu'], 3 if r['frictModel'] == 'samosAT' else 2)})"


def rings(path):
    out = []
    for g in gpd.read_file(path).geometry:
        for p in getattr(g, "geoms", [g]):
            out.append(np.asarray(p.exterior.coords)[:, :2])
    return out


def crop(z, tr, aspect):
    """Bounds around obs, release and both footprints, padded, expanded to the panel aspect (w/h)."""
    m = z["obs"] | z["rel"] | (z["pft_best"] > 0.1) | (z["pft_loo"] > 0.1)
    rr, cc = np.nonzero(m)
    a, c, e, f = tr[0], tr[2], tr[4], tr[5]
    x0, x1 = c + a * cc.min(), c + a * (cc.max() + 1)
    y0, y1 = f + e * (rr.max() + 1), f + e * rr.min()
    w, h = x1 - x0, y1 - y0
    h_content = h
    pad = 0.08 * max(w, h) + 40
    x0, x1, y0, y1 = x0 - pad, x1 + pad, y0 - pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    if w / h < aspect:
        dx = (h * aspect - w) / 2
        x0, x1 = x0 - dx, x1 + dx
    else:
        dy = (w / aspect - h) / 2
        y0, y1 = y0 - dy, y1 + dy
    # slide the window inside the DEM where it fits (no blank strip at the DEM edge)
    ex0, ex1 = c, c + a * z["dem"].shape[1]
    ey0, ey1 = f + e * z["dem"].shape[0], f
    if x1 - x0 > ex1 - ex0 and (ex1 - ex0) / aspect >= h_content + 240:  # too wide for the DEM: trim the padding
        cy, h2 = (y0 + y1) / 2, (ex1 - ex0) / aspect / 2
        x0, x1, y0, y1 = ex0, ex1, cy - h2, cy + h2
    if x1 - x0 <= ex1 - ex0:
        sx = max(0.0, ex0 - x0) - max(0.0, x1 - ex1)
        x0, x1 = x0 + sx, x1 + sx
    if y1 - y0 <= ey1 - ey0:
        sy = max(0.0, ey0 - y0) - max(0.0, y1 - ey1)
        y0, y1 = y0 + sy, y1 + sy
    return x0, x1, y0, y1


def panel(event, z, wpx, hpx):
    tr = z["transform"]
    dem = z["dem"]
    ext = (tr[2], tr[2] + tr[0] * dem.shape[1], tr[5] + tr[4] * dem.shape[0], tr[5])
    x0, x1, y0, y1 = crop(z, tr, wpx / hpx)
    fig = plt.figure(figsize=(wpx / 100, hpx / 100), dpi=100, facecolor=np.array(PAPER) / 255)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(np.array(PAPER) / 255)
    hs = LightSource(azdeg=315, altdeg=40).hillshade(np.nan_to_num(dem, nan=np.nanmean(dem)), vert_exag=1.5,
                                                     dx=abs(tr[0]), dy=abs(tr[4]))
    paper = np.array(PAPER) / 255
    ax.imshow(paper[None, None, :] * (0.50 + 0.50 * hs[..., None]), extent=ext, interpolation="bilinear")
    span = np.nanmax(dem) - np.nanmin(dem)
    step = 50 if (y1 - y0) < 1000 else 100
    lv = np.arange(np.floor(np.nanmin(dem) / step) * step, np.nanmax(dem) + step, step)
    xs = np.linspace(ext[0], ext[1], dem.shape[1])
    ys = np.linspace(ext[3], ext[2], dem.shape[0])
    ax.contour(xs, ys, dem, levels=lv, colors=["#1d1b17"], linewidths=0.4, alpha=0.28)
    if "res" in z:  # las_porywanie: the forest / resistance layer the runs used (from the event data)
        ax.imshow(np.ma.masked_equal(z["res"].astype(float), 0), extent=ext,
                  cmap=LinearSegmentedColormap.from_list("f", [FOREST_C, FOREST_C]), alpha=0.30,
                  interpolation="nearest")
        ax.contour(xs, ys, z["res"].astype(float), levels=[0.5], colors=[FOREST_C], linewidths=0.9)
    ax.imshow(np.ma.masked_less_equal(z["pft_best"], 0.1), extent=ext, cmap=CMAP, norm=NORM, alpha=0.92,
              interpolation="nearest")
    ax.contour(xs, ys, (z["pft_loo"] > 0.1).astype(float), levels=[0.5], colors=[LOO_C], linewidths=1.7)
    if "ent" in z:  # las_porywanie, Eiskar: entrainment areas from the event data
        ax.contour(xs, ys, z["ent"].astype(float), levels=[0.5], colors=[ENT_C], linewidths=1.6,
                   linestyles=[(0, (1, 1.6))])
    obs_p, rel_p = OUTLINES[event]
    for r in rings(rel_p):
        ax.fill(r[:, 0], r[:, 1], facecolor="none", edgecolor="#1d1b17", lw=1.2, hatch="////")
    for r in rings(obs_p):
        ax.plot(r[:, 0], r[:, 1], color="#1d1b17", lw=2.0, dashes=(4, 2.5))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_axis_off()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB"), (x1 - x0) / wpx, span


def nice_bar(mpp, wpx):
    target = 0.35 * wpx * mpp
    for v in (50, 100, 200, 250, 500, 1000):
        if v >= target * 0.6:
            return v
    return 1000


def wrap(txt, f, maxw, d):
    rows, cur = [], ""
    for w in txt.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > maxw and cur:
            rows.append(cur)
            cur = w
        else:
            cur = t
    return rows + [cur]


def text_block(d, x, y, txt, f, fill, maxw, lh):
    for row in wrap(txt, f, maxw, d):
        d.text((x, y), row, font=f, fill=fill)
        y += lh
    return y


def legend(d, img, x, y, las=False):
    f = font(16, 450)
    gap = 26 if las else 34
    # dashed observed outline
    for gx in range(x, x + 44, 10):
        d.line([gx, y + 9, gx + 6, y + 9], fill=INK, width=3)
    d.text((x + 54, y + 9), "obserwowany zasięg lub osad", font=f, fill=INK, anchor="lm")
    x += 54 + int(d.textlength("obserwowany zasięg lub osad", font=f)) + gap
    d.rectangle([x, y, x + 36, y + 18], outline=INK, width=2)
    for gx in range(x - 18, x + 36, 7):
        d.line([max(x, gx), y + 18 - max(0, x - gx), min(x + 36, gx + 18), y + max(0, gx + 18 - x - 36)],
               fill=INK, width=1)
    d.text((x + 46, y + 9), "odryw", font=f, fill=INK, anchor="lm")
    x += 46 + int(d.textlength("odryw", font=f)) + gap
    bar = (CMAP(np.linspace(0, 1, 200))[:, :3] * 255).astype("uint8")
    img.paste(Image.fromarray(np.repeat(bar[None], 14, 0)), (x, y + 2))
    cb = ("najlepszy przebieg: grubość przepływu 0,1 → ≥2,5 m" if las else
          "najlepszy przebieg: maks. grubość przepływu 0,1 → ≥2,5 m")
    d.text((x + 210, y + 9), cb, font=f, fill=INK, anchor="lm")
    x += 210 + int(d.textlength(cb, font=f)) + gap
    d.line([x, y + 9, x + 40, y + 9], fill=LOO_C, width=3)
    lo = "test leave-one-out" if las else "test bez tego zdarzenia (leave-one-out)"
    d.text((x + 50, y + 9), lo, font=f, fill=INK, anchor="lm")
    if not las:
        return
    x += 50 + int(d.textlength(lo, font=f)) + gap
    fc = tuple(int(FOREST_C[i:i + 2], 16) for i in (1, 3, 5))
    d.rectangle([x, y, x + 36, y + 18], fill=tuple(int(0.30 * c + 0.70 * p) for c, p in zip(fc, PAPER)), outline=fc,
                width=1)
    d.text((x + 46, y + 9), "las / opór z danych zdarzenia", font=f, fill=INK, anchor="lm")
    x += 46 + int(d.textlength("las / opór z danych zdarzenia", font=f)) + gap
    ec = tuple(int(ENT_C[i:i + 2], 16) for i in (1, 3, 5))
    for gx in range(x, x + 40, 6):
        d.line([gx, y + 9, gx + 2, y + 9], fill=ec, width=3)
    d.text((x + 50, y + 9), "porywanie (Eiskar)", font=f, fill=INK, anchor="lm")
    end = x + 50 + d.textlength("porywanie (Eiskar)", font=f)
    assert end <= W - 60, f"legend too wide: {end}"


def main(variant="bez_lasu", out=None):
    las = variant == "las_porywanie"
    loo = json.loads((AV / ("calib_loo_las.json" if las else "calib_loo.json")).read_text(encoding="utf-8"))
    cal = json.loads((ROOT / "web" / "data" / "calibration.json").read_text(encoding="utf-8"))
    evs = {e["id"]: e for e in cal["events"]}
    best_las = json.loads((AV / "calib_results_las_best.json").read_text(encoding="utf-8"))["best"] if las else None
    npz = AV / "board_multi_las" if las else NPZ
    S = loo["summary"]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    if las:
        d.text((60, 36), "AvaFrame na prawdziwych lawinach, z lasem i porywaniem śniegu", font=font(42, 750), fill=INK)
        sub = (f"{S['n_runs']} symulacje com1DFA na DGX Spark; las i porywanie z danych zdarzeń, parametry domyślne, "
               "niestrojone. W każdym panelu najlepszy przebieg i test bez tego zdarzenia. Północ u góry.")
        assert d.textlength(sub, font=font(21, 450)) <= W - 120, "subtitle too wide"
        d.text((60, 94), sub, font=font(21, 450), fill=INK2)
    else:
        d.text((60, 36), f"AvaFrame na prawdziwych lawinach: {S['n_events']} zdarzeń z Austrii i Szwajcarii",
               font=font(42, 750), fill=INK)
        d.text((60, 94), f"{S['n_runs']} symulacje com1DFA na DGX Spark. W każdym panelu najlepszy przebieg dla "
                         "zdarzenia i przebieg wybrany bez tego zdarzenia (test leave-one-out). Północ u góry.",
               font=font(21, 450), fill=INK2)
    legend(d, img, 60, 138, las)
    pw, ph, x0, gap, ytop, y0 = 324, 500, 60, 45, 186, 270
    for k, e in enumerate(EV):
        z = dict(np.load(npz / f"{e}.npz"))
        im, mpp, _ = panel(e, z, pw, ph)
        x = x0 + k * (pw + gap)
        ev, lo, b = evs[e], loo["loo"][e], (best_las[e] if las else evs[e]["best"])
        d.text((x, ytop), ev["name"], font=font(25, 750), fill=INK)
        d.text((x, ytop + 33), f"{ev['country']} · {DATE_PL[ev['date']]}", font=font(16, 550), fill=INK)
        obs = "obserwowany zasięg" if ev["obs_type"] == "event_area" else "obserwowany tylko osad"
        d.text((x, ytop + 55), f"{SHORT[e]} · {obs}", font=font(14, 450), fill=INK2)
        img.paste(im, (x, y0))
        d.rectangle([x, y0, x + pw - 1, y0 + ph - 1], outline=INK, width=1)
        sb = nice_bar(mpp, pw)
        spx = int(sb / mpp)
        bx, by = x + 12, y0 + ph - 20
        d.rectangle([bx - 6, by - 10, bx + spx + 58, by + 14], fill=PAPER)
        d.rectangle([bx, by, bx + spx, by + 4], fill=INK)
        d.text((bx + spx + 6, by + 2), f"{sb} m", font=font(13, 600), fill=INK, anchor="lm")
        # labels below the panel
        y = y0 + ph + 12
        d.text((x, y), "TEST BEZ TEGO ZDARZENIA", font=font(13, 750, 110), fill=ORANGE_TXT)
        y += 19
        ov = (f"IoU {pl(lo['iou_or_overlap'])}" if lo["overlap_metric"] == "iou"
              else f"osad {lo['iou_or_overlap'] * 100:.0f}%")
        big = font(32, 780)
        d.text((x, y), signed(lo["runout_error_m"]), font=big, fill=INK)
        wbig = d.textlength(signed(lo["runout_error_m"]), font=big)
        d.text((x + wbig + 10, y + 13), f"zasięgu · {ov}", font=font(16, 550), fill=INK)
        y += 42
        th = "zmierzony" if e == "avaEiskar" else "założony"
        d.text((x, y), f"{setting_pl(lo)}, odryw {pl(lo['relTh'], 1)} m ({th})", font=font(14, 450), fill=INK)
        y += 26
        d.text((x, y), "NAJLEPSZY PRZEBIEG", font=font(13, 750, 110), fill=INK2)
        y += 19
        bov = (f"IoU {pl(b['iou'])}" if ev["obs_type"] == "event_area" else f"osad {b['dep_hit'] * 100:.0f}%")
        d.text((x, y), f"{signed(b['runout_error_m'])} zasięgu · {bov}", font=font(17, 700), fill=INK)
        y += 23
        th = "zmierzony" if str(b["relTh_source"]).startswith("measured") else "z siatki"
        d.text((x, y), f"{setting_pl(b)}, odryw {pl(b['relTh'], 1)} m ({th})", font=font(14, 450), fill=INK2)
    # summary
    g = S["best_global_setting"]
    ys = y0 + ph + 182
    d.line([60, ys - 12, W - 60, ys - 12], fill=INK2, width=1)
    if las:
        r1, nr = S["round1"], S["within_100m"]
        fil = [loo["loo"][h]["runout_error_m"] for h in ("avaFilisur1", "avaFilisur2")]
        gs = g["setting_pl"].replace(" m/s²", "").replace("ξ", "xi")  # Archivo has no ξ glyph
        head = (f"Leave-one-out z lasem: średnio {pl(S['mean_abs_runout_error_loo_m'], 1)} m (bez lasu "
                f"{pl(r1['mean_abs_runout_error_loo_m'], 1)} m), mediana {S['median_abs_runout_error_loo_m']:.0f} m "
                f"(bez lasu {r1['median_abs_runout_error_loo_m']:.0f} m); w granicach {nr['threshold_m']} m {nr['n']} z "
                f"{nr['of']} zdarzeń (bez lasu {r1['within_100m']['n']} z {r1['within_100m']['of']}).")
        care = ("Uczciwie: las i porywanie tylko z danych zdarzeń, parametry domyślne, niestrojone; porywanie tylko na "
                "Eiskar, grubość 0,3 m domyślna. Las poprawia dopasowanie w próbie (jedno "
                f"ustawienie {gs} dobrane na tych 5 myli średnio o {g['mean_abs_runout_error_m']:.0f} m), więc trening w "
                f"{S['loo_same_setting_as_global']} z {len(EV)} prób wybiera je, a ono przestrzeliwuje Filisur o "
                f"{signed(min(fil))} i {signed(max(fil))}. Grubość odrywu zmierzono tylko na Eiskar "
                "(2,7 m). Teren nowszy niż zdarzenia. To przykładowa kalibracja na zdarzeniach z Austrii i "
                "Szwajcarii, nie dla Tatr.")
        ys = text_block(d, 60, ys, head, font(19, 650), INK, W - 120, 25)
        ys = text_block(d, 60, ys + 2, care, font(15, 450), INK2, W - 120, 20)
        src = ("Dane zdarzeń, las i porywanie: OpenNHM/AvaFrameData 1.0, DOI 10.5281/zenodo.20701552, CC BY 4.0 "
               "(F. Perzl, BFW; WLV; SLF Davos, Feistl i in. 2014). Teren: Land Tirol 5 m, CC BY 4.0 AT; BEV ALS DTM "
               "1 m, CC BY 4.0; © swisstopo swissALTI3D. Symulacje: AvaFrame com1DFA 2.1, siatka 5 m.")
        text_block(d, 60, max(ys + 6, H - 46), src, font(13, 450), INK2, W - 120, 17)
        out = Path(out) if out else ROOT / "filmy" / "kalibracja" / "5_lawin_las.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        print("saved", out, "bottom text at", ys)
        return
    head = (f"Jedno ustawienie dla wszystkich (samosAT, odryw 1,2 m, dobrane na tych 5): średni błąd zasięgu "
            f"{g['mean_abs_runout_error_m']:.0f} m. Leave-one-out: średnio {S['mean_abs_runout_error_loo_m']:.0f} m, "
            f"mediana {S['median_abs_runout_error_loo_m']:.0f} m; w {S['loo_same_setting_as_global']} z "
            f"{S['n_events']} prób ta sama kalibracja samosAT.")
    ys = text_block(d, 60, ys, head, font(19, 650), INK, W - 120, 25)
    care = ("Uczciwie: grubość odrywu zmierzono tylko na Eiskar (2,7 m), dla reszty jest nieznana. Model bez lasu i "
            "porywania śniegu: Filisur zatrzymał las, więc każdy przebieg przestrzeliwuje, a Eiskar staje za krótko. "
            "Bez Kleiner Ötscherbach wygrywa małe tarcie dopasowane do Eiskar, stąd +350 m. Teren nowszy niż zdarzenia. "
            "To przykładowa kalibracja na zdarzeniach z Austrii i Szwajcarii, nie dla Tatr.")
    ys = text_block(d, 60, ys + 2, care, font(15, 450), INK2, W - 120, 20)
    src = ("Dane zdarzeń: OpenNHM/AvaFrameData 1.0, DOI 10.5281/zenodo.20701552, CC BY 4.0 (F. Perzl, BFW; WLV; "
           "SLF Davos, Feistl i in. 2014). Teren: Land Tirol 5 m, CC BY 4.0 AT; BEV ALS DTM 1 m, CC BY 4.0; "
           "© swisstopo swissALTI3D. Symulacje: AvaFrame com1DFA 2.1, siatka 5 m.")
    text_block(d, 60, max(ys + 6, H - 46), src, font(13, 450), INK2, W - 120, 17)
    out = Path(out) if out else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("saved", out, "bottom text at", ys)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[a.index("--variant") + 1] if "--variant" in a else "bez_lasu",
         a[a.index("--out") + 1] if "--out" in a else None)

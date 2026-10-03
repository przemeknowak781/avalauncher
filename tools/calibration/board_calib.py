"""Calibration board + web/data/calibration.json from the Spark calibration results.

Expects in <work>: dem.tif, scores.json, pft/<simName>_pft.asc for the plotted runs.
Usage: python tools/calibration/board_calib.py <work>
Outputs: filmy/kalibracja/porownanie.png, web/data/calibration.json
"""

import io
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import shapefile  # noqa: E402
from matplotlib.colors import LightSource, LinearSegmentedColormap, Normalize  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "raw" / "avaframedata" / "OpenNHM-AvaFrameData-fa839ca" / "avaPopeletzbach"
FONT = ROOT / "web" / "vendor" / "fonts" / "Archivo-var.ttf"
PAPER, INK, INK2 = (244, 239, 228), (29, 27, 23), (110, 101, 86)
ORANGE = ["#ffd6aa", "#e8590c", "#5a1a00"]
W, H = 1920, 1080
XMIN, XMAX, YMIN, YMAX = 319070.0, 319770.0, 335600.0, 337600.0  # crop, EPSG:31287
CMAP = LinearSegmentedColormap.from_list("ava", ORANGE)
NORM = Normalize(0.1, 2.5, clip=True)
EVENT, DATE = "Popeletzbach (Tyrol Wschodni, Austria)", "7.04.2009"


def font(size, weight=500, width=100):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight, width])
    return f


def pl(x, nd=2):
    return f"{x:.{nd}f}".replace(".", ",")


def rings(name):
    out = []
    for shp in shapefile.Reader(str(SRC / f"{name}.shp")).shapes():
        pts = np.array(shp.points)
        parts = list(shp.parts) + [len(pts)]
        out += [pts[a:b] for a, b in zip(parts[:-1], parts[1:])]
    return out


def panel(dem, tr, pft, wpx, hpx):
    fig = plt.figure(figsize=(wpx / 100, hpx / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ext = (tr.c, tr.c + tr.a * dem.shape[1], tr.f + tr.e * dem.shape[0], tr.f)
    hs = LightSource(azdeg=315, altdeg=40).hillshade(dem, vert_exag=1.5, dx=5, dy=5)
    paper = np.array(PAPER) / 255
    rgb = paper[None, None, :] * (0.50 + 0.50 * hs[..., None])
    ax.imshow(rgb, extent=ext, interpolation="bilinear")
    ax.contour(np.linspace(ext[0], ext[1], dem.shape[1]), np.linspace(ext[3], ext[2], dem.shape[0]), dem,
               levels=np.arange(1400, 2800, 100), colors=["#1d1b17"], linewidths=0.4, alpha=0.28)
    if pft is not None:
        a = np.ma.masked_less_equal(pft, 0.1)
        ax.imshow(a, extent=ext, cmap=CMAP, norm=NORM, alpha=0.92, interpolation="nearest")
    for r in rings("releaseArea20090407"):
        ax.fill(r[:, 0], r[:, 1], facecolor="none", edgecolor="#1d1b17", lw=1.4, hatch="////")
    for r in rings("eventDepositionArea20090407"):
        ax.fill(r[:, 0], r[:, 1], facecolor="none", edgecolor="#1d1b17", lw=1.6, hatch="....")
    for r in rings("eventArea20090407"):
        ax.plot(r[:, 0], r[:, 1], color="#1d1b17", lw=2.0, dashes=(5, 3))
    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(YMIN, YMAX)
    ax.set_axis_off()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def pick(scores):
    """Best run plus three clearly worse ones: the worst, the shortest and the longest runout."""
    best, rest = scores[0], scores[1:]
    worse = [s for s in rest if s["iou"] < best["iou"] - 0.03] or rest
    picks = [min(worse, key=lambda s: s["iou"])]
    for key in (lambda s: s["runout_error_m"], lambda s: -s["runout_error_m"]):
        cand = [s for s in worse if s not in picks]
        if cand:
            picks.append(min(cand, key=key))
    return [best] + sorted(picks, key=lambda s: -s["iou"])


def label(s):
    if s["frictModel"] == "Voellmy":
        return f"Voellmy μ={pl(s['mu'])}, xi={int(s['xsi'])}", f"odryw {pl(s['relTh'])} m"
    return f"{s['frictModel']} (μ={pl(s['mu'])})", f"odryw {pl(s['relTh'])} m"


def grid_table(d, x, y, scores):
    models = [m for m in ("samosATSmall", "samosATMedium", "samosAT") if any(s["frictModel"] == m for s in scores)]
    ths = sorted({s["relTh"] for s in scores if s["frictModel"] in models})
    cw, ch, lw = 62, 30, 150
    d.text((x, y), "IoU w siatce kalibracji (grubość odrywu, m)", font=font(19, 650), fill=INK)
    y += 34
    for j, t in enumerate(ths):
        d.text((x + lw + j * cw + cw / 2, y + 8), pl(t), font=font(15, 500), fill=INK2, anchor="mm")
    y += 20
    for i, m in enumerate(models):
        d.text((x, y + i * ch + ch / 2), m, font=font(16, 500), fill=INK, anchor="lm")
        for j, t in enumerate(ths):
            hit = [s for s in scores if s["frictModel"] == m and s["relTh"] == t]
            if not hit:
                continue
            v = hit[0]["iou"]
            c = tuple(int(255 * c) for c in CMAP(min(1.0, max(0.0, (v - 0.3) / 0.5)))[:3])
            x0, y0 = x + lw + j * cw, y + i * ch
            d.rectangle([x0 + 2, y0 + 2, x0 + cw - 2, y0 + ch - 2], fill=c)
            d.text((x0 + cw / 2, y0 + ch / 2), pl(v), font=font(15, 600),
                   fill=PAPER if v > 0.62 else INK, anchor="mm")
    y += len(models) * ch
    vo = [s for s in scores if s["frictModel"] == "Voellmy"]
    if vo:
        mus, xis = sorted({s["mu"] for s in vo}), sorted({s["xsi"] for s in vo})
        y += 14
        d.text((x, y), f"Voellmy przy odrywie {pl(vo[0]['relTh'])} m (kolumny: μ)", font=font(16, 600), fill=INK)
        y += 26
        for j, m in enumerate(mus):
            d.text((x + lw + j * cw + cw / 2, y + 8), pl(m), font=font(15, 500), fill=INK2, anchor="mm")
        y += 20
        for i, xi in enumerate(xis):
            d.text((x, y + i * ch + ch / 2), f"xi = {int(xi)} m/s²", font=font(16, 500), fill=INK, anchor="lm")
            for j, m in enumerate(mus):
                hit = [s for s in vo if s["mu"] == m and s["xsi"] == xi]
                if not hit:
                    continue
                v = hit[0]["iou"]
                c = tuple(int(255 * c) for c in CMAP(min(1.0, max(0.0, (v - 0.3) / 0.5)))[:3])
                x0, y0 = x + lw + j * cw, y + i * ch
                d.rectangle([x0 + 2, y0 + 2, x0 + cw - 2, y0 + ch - 2], fill=c)
                d.text((x0 + cw / 2, y0 + ch / 2), pl(v), font=font(15, 600),
                       fill=PAPER if v > 0.62 else INK, anchor="mm")
        y += len(xis) * ch
    return y


def main(work):
    work = Path(work)
    scores = json.loads((work / "scores.json").read_text())
    scores = [s for s in scores if s["group"] != "smoke"]
    with rasterio.open(work / "dem.tif") as r:
        dem, tr = r.read(1), r.transform
    chosen = pick(scores)
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((60, 44), f"Kalibracja AvaFrame na prawdziwej lawinie: Popeletzbach, {DATE}", font=font(42, 750), fill=INK)
    d.text((60, 102), "Mokra lawina, Tyrol Wschodni (Austria). Obserwowany zasięg kontra symulacje com1DFA: "
           f"{len(scores)} {plural(len(scores))}, trzy kalibracje samosAT i model Voellmy.", font=font(21, 450), fill=INK2)
    pw, ph, x0, y0, gap = 300, 720, 60, 210, 46
    pw = int(ph * (XMAX - XMIN) / (YMAX - YMIN))
    for k, s in enumerate(chosen):
        with rasterio.open(work / "pft" / f"{s['simName']}_pft.asc") as r:
            pft = r.read(1)
        im = panel(dem, tr, pft, pw, ph)
        x = x0 + k * (pw + gap)
        img.paste(im, (x, y0))
        d.rectangle([x, y0, x + pw - 1, y0 + ph - 1], outline=INK, width=1)
        tag = "NAJLEPSZE DOPASOWANIE" if k == 0 else "GORZEJ"
        d.text((x, y0 - 70), tag, font=font(15, 700, 110), fill=(232, 89, 12) if k == 0 else INK2)
        l1, l2 = label(s)
        d.text((x, y0 - 49), l1, font=font(17, 650), fill=INK)
        d.text((x, y0 - 26), l2, font=font(17, 450), fill=INK)
        err = s["runout_error_m"]
        d.text((x, y0 + ph + 10), f"IoU {pl(s['iou'])}", font=font(30, 750), fill=INK)
        d.text((x, y0 + ph + 48), f"zasięg {'+' if err >= 0 else '−'}{abs(err):.0f} m · depozyt {s['dep_hit'] * 100:.0f}%",
               font=font(17, 500), fill=INK2)
    # scale bar (first panel)
    mpp = (XMAX - XMIN) / pw
    sb = int(500 / mpp)
    bx, by = x0 + 14, y0 + ph - 22
    d.rectangle([bx, by, bx + sb, by + 5], fill=INK)
    d.text((bx + sb + 6, by + 3), "500 m", font=font(14, 600), fill=INK, anchor="lm")
    # right column
    rx = x0 + 4 * (pw + gap) + 20
    y = 150
    d.text((rx, y), "Legenda", font=font(19, 650), fill=INK)
    y += 34
    d.line([rx, y + 9, rx + 44, y + 9], fill=INK, width=3)
    for gx in range(rx + 9, rx + 44, 14):
        d.line([gx, y + 9, gx + 4, y + 9], fill=PAPER, width=3)
    d.text((rx + 56, y + 9), "obserwowany zasięg lawiny", font=font(17, 450), fill=INK, anchor="lm")
    y += 30
    d.rectangle([rx, y, rx + 44, y + 18], outline=INK, width=2)
    for gx in range(rx + 5, rx + 44, 7):
        for gy in range(y + 5, y + 18, 6):
            d.point((gx, gy), fill=INK)
    d.text((rx + 56, y + 9), "obserwowany depozyt", font=font(17, 450), fill=INK, anchor="lm")
    y += 30
    d.rectangle([rx, y, rx + 44, y + 18], outline=INK, width=2)
    for gx in range(rx - 18, rx + 44, 7):
        d.line([max(rx, gx), y + 18 - max(0, rx - gx), min(rx + 44, gx + 18), y + max(0, gx + 18 - rx - 44)],
               fill=INK, width=1)
    d.text((rx + 56, y + 9), "obszar odrywu", font=font(17, 450), fill=INK, anchor="lm")
    y += 36
    bar = (CMAP(np.linspace(0, 1, 300))[:, :3] * 255).astype("uint8")
    img.paste(Image.fromarray(np.repeat(bar[None], 16, 0)).resize((300, 16)), (rx, y))
    d.text((rx, y + 22), "0,1", font=font(14, 500), fill=INK2)
    d.text((rx + 300, y + 22), "≥2,5 m", font=font(14, 500), fill=INK2, anchor="ra")
    d.text((rx, y + 42), "symulowana maks. grubość przepływu", font=font(16, 450), fill=INK)
    y += 76
    y = grid_table(d, rx, y, scores) + 20
    best = chosen[0]
    near = [s for s in scores if s["iou"] >= best["iou"] - 0.02]
    lines = [
        ("Miara", f"IoU śladu (grubość > 0,1 m) z obserwowanym zasięgiem; zasięg liczony od szczytu odrywu "
                  f"(obserwowany {best['runout_obs_m']:.0f} m)."),
        ("Założenia", "grubość odrywu nieznana, przyjęta siatka 0,6–1,6 m; bez lasu; samosAT to kalibracja "
                      "dla suchego śniegu, tu zastosowana do mokrej lawiny."),
        ("Co wyszło", f"{len(near)} z {len(scores)} przebiegów mieści się w 0,02 IoU od najlepszego: żleb prowadzi "
                      "lawinę, więc jedno zdarzenie słabo rozróżnia parametry. Odrzuca za to wyraźnie zbyt duże "
                      "i zbyt małe tarcie."),
        ("Wniosek", "przykładowa kalibracja na zdarzeniu z Austrii. Dla Tatr potrzebne lokalne obserwacje (TOPR)."),
    ]
    for head, txt in lines:
        d.text((rx, y), head, font=font(16, 700), fill=INK)
        y += 22
        for row in wrap(txt, font(15, 450), 1880 - rx, d):
            d.text((rx, y), row, font=font(15, 450), fill=INK2)
            y += 20
        y += 10
    src = ("Dane zdarzenia: OpenNHM/AvaFrameData 1.0 (F. Perzl, BFW), DOI 10.5281/zenodo.20701552, CC BY 4.0. "
           "Teren: Land Tirol, Geländemodell 5 m (WCS gis.tirol.gv.at), CC BY 4.0 AT; teren współczesny, "
           "zdarzenie z 2009 r. Symulacje: AvaFrame com1DFA 2.1.")
    yy = H - 52
    for row in wrap(src, font(14, 450), W - 120, d):
        d.text((60, yy), row, font=font(14, 450), fill=INK2)
        yy += 19
    out = ROOT / "filmy" / "kalibracja" / "porownanie.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("saved", out, [(s["frictModel"], s["relTh"], s["iou"]) for s in chosen])
    write_json(scores, best, chosen)


def write_json(scores, best, chosen):
    keys = ("frictModel", "mu", "xsi", "relTh", "iou", "iou_ppr1kPa", "dep_hit", "precision", "recall",
            "runout_sim_m", "runout_obs_m", "runout_error_m", "area_sim_ha", "simName")
    doc = {
        "event": "Popeletzbach (Tyrol Wschodni, Austria), mokra lawina",
        "date": "2009-04-07",
        "source": {
            "event_data": "OpenNHM/AvaFrameData 1.0, avaPopeletzbach (release, eventArea, eventDepositionArea); "
                          "dane zebrał Frank Perzl (BFW)",
            "doi": "10.5281/zenodo.20701552",
            "licence": "CC-BY-4.0",
        },
        "dem_used": {
            "name": "Land Tirol, Gelaendemodell_5m_M28 (WCS gis.tirol.gv.at)",
            "resolution_m": 5,
            "crs": "EPSG:31287 (przeprojektowanie po stronie serwera z EPSG:31254)",
            "licence": "CC BY 4.0 AT",
            "caveat": "teren współczesny, zdarzenie z 2009 r.",
        },
        "model": "AvaFrame com1DFA 2.1, meshCellSize 5 m, simTypeList null (bez lasu i porywania)",
        "metrics": {
            "footprint": "peak flow thickness pft > 0.1 m",
            "iou": "|sim ∩ eventArea| / |sim ∪ eventArea|",
            "dep_hit": "udział komórek obserwowanego depozytu objętych śladem",
            "runout_error_m": "zasięg symulowany - obserwowany; zasięg = max odległość pozioma od najwyższego "
                              "punktu odrywu (>0 za daleko, <0 za krótko)",
        },
        "assumptions": "grubość odrywu nieznana w danych (atrybut pusty): siatka 0,6-1,6 m; "
                       "samosAT to kalibracja dla suchego śniegu, tu zastosowana do mokrej lawiny",
        "runs": len(scores),
        "best": {k: best[k] for k in ("frictModel", "relTh", "iou", "runout_error_m", "dep_hit", "mu")},
        "plotted": [s["simName"] for s in chosen],
        "table": [{k: s.get(k) for k in keys} for s in scores],
        "note": "przykładowa kalibracja na zdarzeniu z Austrii; dla Tatr potrzebne lokalne obserwacje (TOPR)",
    }
    p = ROOT / "web" / "data" / "calibration.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", p)


def plural(n):
    if n == 1:
        return "przebieg"
    return "przebiegi" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "przebiegów"


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


if __name__ == "__main__":
    main(sys.argv[1])

"""Board (AvaFrame vs surrogate vs difference), relTh slider film and surrogate.json.

Runs on the Spark next to the trained model.
Usage: python render.py <modelDir> <assetsDir> <sectors_u8.bin> <destDir> <cache.npz> [...]
Writes destDir/porownanie.png, destDir/suwak.mp4, destDir/surrogate.json
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from net import FRICT, S, Surrogate, UNet, load_terrain, release_mask
from train import load_caches

INK, INK2, PAPER, LINE = (29, 27, 23), (90, 82, 68), (244, 239, 228), (221, 212, 194)
HAZ = (166, 59, 0)
RAMP = [(0.05, (255, 214, 170)), (0.3, (249, 145, 72)), (0.8, (232, 89, 12)), (1.5, (166, 59, 0)), (3.0, (90, 26, 0))]
BOTH, MISS, EXTRA = (249, 145, 72), (31, 95, 209), (90, 26, 0)
TRAIL = {"red": (214, 40, 40), "blue": (31, 95, 209), "green": (42, 157, 60), "yellow": (242, 194, 0),
         "black": (34, 32, 28)}
FRICT_PL = {"samosATSmall": "tarcie: małe lawiny", "samosATMedium": "tarcie: średnie lawiny",
            "samosAT": "tarcie: duże lawiny"}
A = {}


def pl(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def font(size, weight=700, width=100):
    f = ImageFont.truetype(str(A["font"]), size)
    f.set_variation_by_axes([weight, width])
    return f


def colour(ft, alpha=225):
    v = np.nan_to_num(ft)
    rgba = np.zeros(v.shape + (4,), np.float32)
    for (a, ca), (b, cb) in zip(RAMP, RAMP[1:]):
        m = (v >= a) & (v < b)
        t = ((v - a) / (b - a))[m][:, None]
        rgba[m, :3] = np.array(ca) * (1 - t) + np.array(cb) * t
        rgba[m, 3] = alpha
    top = v >= RAMP[-1][0]
    rgba[top, :3], rgba[top, 3] = RAMP[-1][1], alpha
    return rgba.astype(np.uint8)


def zoom_box(grids, mask, pad=14, min_side=90):
    reach = mask.copy()
    for g in grids:
        reach |= g > 0.1
    r, c = np.nonzero(reach)
    side = int(max(r.max() - r.min(), c.max() - c.min(), min_side) + 2 * pad)
    side = min(side, 400)
    r0 = int(np.clip((r.min() + r.max()) // 2 - side // 2, 0, 400 - side))
    c0 = int(np.clip((c.min() + c.max()) // 2 - side // 2, 0, 400 - side))
    return r0, c0, side


def base_tile(box, size, fade=0.0):
    r0, c0, side = box
    k = A["map"].width / 400
    img = A["map"].crop((int(c0 * k), int(r0 * k), int((c0 + side) * k), int((r0 + side) * k))).resize(
        (size, size), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    s = size / side
    lw = max(2, round(size / 220))
    for t in A["trails"]:
        for part in t["paths"]:
            pts = [((c - c0) * s, (r - r0) * s) for c, r in part]
            d.line(pts, fill=(255, 255, 255), width=lw + 2, joint="curve")
            d.line(pts, fill=TRAIL.get(t["color"], TRAIL["red"]), width=lw, joint="curve")
    if fade:
        img = Image.blend(img, Image.new("RGB", img.size, PAPER), fade)
    return img.convert("RGBA")


def layer(rgba_cells, box, size, blur=True):
    r0, c0, side = box
    im = Image.fromarray(rgba_cells[r0:r0 + side, c0:c0 + side], "RGBA").resize((size, size), Image.BILINEAR)
    return im.filter(ImageFilter.GaussianBlur(size / 700)) if blur else im


def outline(mask, box, size, col=INK):
    r0, c0, side = box
    m = Image.fromarray((mask[r0:r0 + side, c0:c0 + side] * 255).astype(np.uint8)).resize((size, size), Image.NEAREST)
    w = max(3, round(size / 260)) | 1
    edge = np.array(m.filter(ImageFilter.MaxFilter(w))) ^ np.array(m.filter(ImageFilter.MinFilter(w)))
    rgba = np.zeros((size, size, 4), np.uint8)
    rgba[edge > 0] = (*col, 230)
    return Image.fromarray(rgba, "RGBA")


def tile_flow(pft, mask, box, size):
    img = base_tile(box, size)
    img.alpha_composite(layer(colour(pft), box, size))
    img.alpha_composite(outline(mask, box, size))
    return img


def tile_diff(ref, pred, mask, box, size):
    img = base_tile(box, size, fade=0.45)
    a, b = ref > 0.1, pred > 0.1
    rgba = np.zeros((400, 400, 4), np.uint8)
    rgba[a & b] = (*BOTH, 220)
    rgba[a & ~b] = (*MISS, 230)
    rgba[~a & b] = (*EXTRA, 230)
    img.alpha_composite(layer(rgba, box, size, blur=False))
    img.alpha_composite(outline(mask, box, size))
    return img


def scale_bar(img, box, size):
    d = ImageDraw.Draw(img, "RGBA")
    px = size / box[2] / 10 * 200  # 200 m
    x, y = size - 26 - px, size - 30
    d.rectangle((x - 10, y - 26, x + px + 10, y + 12), fill=(*PAPER, 215))
    d.line((x, y, x + px, y), fill=INK, width=4)
    d.text((x + px / 2, y - 6), "200 m", font=font(17, 700), fill=INK, anchor="mb")


def ramp_legend(d, x, y, sw=58):
    d.text((x, y), "Grubość przepływu (maks.)", font=font(20, 700), fill=INK, anchor="lm")
    x += 270
    for v, c in RAMP:
        d.rectangle((x, y - 10, x + sw, y + 10), fill=c)
        d.text((x + sw / 2, y + 24), f"{pl(v, 2 if v < 0.1 else 1)} m", font=font(15, 600), fill=INK2, anchor="mm")
        x += sw + 8
    return x


def board(D, H, M, dem, idx, sectors, dest):
    held = M["held_out_sectors"]
    tile, gap, mx = 600, 18, 40
    top, row_head, foot = 250, 64, 150
    W = 2 * mx + 3 * tile + 2 * gap
    Hh = top + len(held) * (row_head + tile + gap) + foot
    can = Image.new("RGB", (W, Hh), PAPER)
    d = ImageDraw.Draw(can)
    d.text((mx, 64), "Surogat neuronowy AvaFrame", font=font(58, 800, 112), fill=INK, anchor="lm")
    d.text((mx, 122), f"Dowód koncepcji: U-Net wytrenowany na {M['trained_on_runs']} przebiegach AvaFrame com1DFA "
                      f"({len(M['train_sectors'])} stoków).", font=font(25, 500), fill=INK2, anchor="lm")
    d.text((mx, 156), "Pokazane stoki ani stoki, których lawiny wchodzą na ten sam teren, nie brały udziału w treningu. "
                      "Zasięg = grubość przepływu > 0,1 m.",
           font=font(25, 500), fill=INK2, anchor="lm")
    speed = M["s_per_run_avaframe"] * 1000 / M["ms_per_map_gpu"]
    stats = [("AvaFrame (1 rdzeń CPU)", f"{pl(M['s_per_run_avaframe'])} s"),
             ("Surogat (GPU GB10)", f"{pl(M['ms_per_map_gpu'])} ms"),
             ("IoU zasięgu, stoki testowe", pl(M["iou_mean"], 2))]
    x = mx
    for lab, val in stats:
        d.text((x, 208), val, font=font(40, 800), fill=HAZ if "ms" in val else INK, anchor="ls")
        tw = d.textlength(val, font=font(40, 800))
        d.text((x + tw + 12, 206), lab, font=font(20, 600), fill=INK2, anchor="ls")
        x += tw + 12 + d.textlength(lab, font=font(20, 600)) + 48
    d.text((W - mx, 208), f"≈ {int(round(speed, -2)):,} × szybciej na mapę".replace(",", " "), font=font(30, 800),
           fill=HAZ, anchor="rs")
    d.line((mx, top - 18, W - mx, top - 18), fill=LINE, width=2)

    y = top
    for s in held:
        sel = np.nonzero(H["sector"] == s)[0]
        ious = H["iou"][sel]
        # representative run: IoU closest to the sector median (not the best one)
        k = sel[np.argmin(np.abs(ious - np.median(ious)))]
        ref, pred = H["ref"][k].astype(np.float32), H["pred"][k].astype(np.float32)
        sec = sectors[s]
        mask = release_mask(idx, sec["index"])
        box = zoom_box([ref, pred], mask)
        d.text((mx, y + 30), f"{sec['name']}  ·  płyta {pl(float(H['relTh'][k]))} m  ·  {FRICT_PL[FRICT[H['frict'][k]]]}",
               font=font(28, 750), fill=INK, anchor="lm")
        d.text((W - mx, y + 30), f"IoU {pl(float(H['iou'][k]), 2)}   (średnio na tym stoku {pl(float(ious.mean()), 2)}, "
                                 f"{len(sel)} przebiegów)", font=font(22, 600), fill=INK2, anchor="rm")
        y += row_head
        tiles = [("AvaFrame com1DFA", tile_flow(ref, mask, box, tile)),
                 ("Surogat (U-Net)", tile_flow(pred, mask, box, tile)),
                 ("Różnica zasięgu", tile_diff(ref, pred, mask, box, tile))]
        for j, (lab, im) in enumerate(tiles):
            scale_bar(im, box, tile)
            dd = ImageDraw.Draw(im, "RGBA")
            tw = dd.textlength(lab, font=font(22, 750))
            dd.rectangle((0, 0, tw + 32, 44), fill=(*PAPER, 232))
            dd.text((16, 22), lab, font=font(22, 750), fill=INK, anchor="lm")
            can.paste(im.convert("RGB"), (mx + j * (tile + gap), y))
        y += tile + gap

    y += 30
    x = ramp_legend(d, mx, y)
    x += 50
    d.text((x, y), "Różnica:", font=font(20, 700), fill=INK, anchor="lm")
    x += 100
    for c, lab in [(BOTH, "zasięg w obu"), (MISS, "tylko AvaFrame (surogat nie dosięgnął)"),
                   (EXTRA, "tylko surogat (nadmiar)")]:
        d.rectangle((x, y - 10, x + 34, y + 10), fill=c)
        d.text((x + 44, y), lab, font=font(18, 600), fill=INK, anchor="lm")
        x += 44 + d.textlength(lab, font=font(18, 600)) + 30
    d.rectangle((x, y - 10, x + 34, y + 10), outline=INK, width=3)
    d.text((x + 44, y), "strefa startowa", font=font(18, 600), fill=INK, anchor="lm")
    d.text((mx, y + 62), f"Czas AvaFrame: mediana z {M['avaframe_timing_logs']} katalogów obliczeń na DGX Spark "
                         f"(com1DFA, siatka 10 m, 1 rdzeń na symulację). Czas surogatu: jedna mapa 256×256, "
                         f"partia 1, GPU, mediana ze 100 wywołań.", font=font(17, 500), fill=INK2, anchor="lm")
    d.text((mx, y + 88), "Teren: GUGiK NMT · szlaki © OpenStreetMap · grubość płyty: scenariusze, nie pomiar · "
                         "surogat przybliża AvaFrame, nie zastępuje go", font=font(17, 500), fill=INK2, anchor="lm")
    can.save(dest / "porownanie.png", optimize=True)
    print("board", can.size)


def slider_film(D, M, net, dem, idx, sectors, boxes, dest, work):
    s = M["held_out_sectors"][0]
    fr = FRICT.index("samosATMedium")
    sel = [i for i in range(len(D["sector"])) if D["sector"][i] == s and D["frict"][i] == fr]
    refs = {round(float(D["relTh"][i]), 2): D["pft"][i].astype(np.float32) for i in sel}
    grid = {k: v for k, v in refs.items() if abs(k * 5 - round(k * 5)) < 1e-6}  # library step 0.2 m
    if len(grid) >= 5:
        refs = grid
    lib = sorted(refs)
    sec = sectors[s]
    mask = release_mask(idx, sec["index"])
    r0, c0 = boxes[s]
    dev = "cuda"
    sur = Surrogate(net).eval()
    z = torch.tensor(dem[r0:r0 + S, c0:c0 + S], device=dev)[None, None]
    m = torch.tensor(mask[r0:r0 + S, c0:c0 + S], dtype=torch.float32, device=dev)[None, None]
    vals = np.round(np.arange(0.4, 2.0001, 0.01), 2)
    vals = np.concatenate([vals, [2.0] * 18, vals[::-1], [0.4] * 12])
    preds, ms = [], []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for _ in range(20):
            sur(z, m, torch.tensor([1.2], device=dev), torch.tensor([fr], device=dev))
        torch.cuda.synchronize()
        for v in vals:
            a = time.perf_counter()
            p = sur(z, m, torch.tensor([float(v)], device=dev), torch.tensor([fr], device=dev))[0].float().cpu().numpy()
            ms.append((time.perf_counter() - a) * 1000)
            full = np.zeros((400, 400), np.float32)
            full[r0:r0 + S, c0:c0 + S] = p
            preds.append(full)
    box = zoom_box([refs[lib[-1]], preds[len(vals) // 4]] + [refs[k] for k in lib], mask, pad=12)
    Wd, Hd, tile = 1920, 1080, 820
    gap = 40
    x0 = (Wd - 2 * tile - gap) // 2
    ytile = 150
    base = base_tile(box, tile)
    ol = outline(mask, box, tile)
    fd = work / "frames"
    if fd.exists():
        shutil.rmtree(fd)
    fd.mkdir(parents=True)
    ref_tiles = {}
    for k in lib:
        im = base.copy()
        im.alpha_composite(layer(colour(refs[k]), box, tile))
        im.alpha_composite(ol)
        scale_bar(im, box, tile)
        ref_tiles[k] = im.convert("RGB")
    sx0, sx1, sy = x0 + 120, Wd - x0 - 120, 1030
    for n, (v, p, t) in enumerate(zip(vals, preds, ms)):
        can = Image.new("RGB", (Wd, Hd), PAPER)
        d = ImageDraw.Draw(can)
        d.text((x0, 52), "Interaktywny suwak grubości płyty", font=font(46, 800, 112), fill=INK, anchor="lm")
        d.text((x0, 104), f"{sec['name']} · {FRICT_PL['samosATMedium']} · stok spoza treningu · dowód koncepcji, "
                          f"surogat wytrenowany na {M['trained_on_runs']} przebiegach AvaFrame",
               font=font(22, 500), fill=INK2, anchor="lm")
        im = base.copy()
        im.alpha_composite(layer(colour(p), box, tile))
        im.alpha_composite(ol)
        scale_bar(im, box, tile)
        near = min(lib, key=lambda k: abs(k - v))
        for j, (img, lab, right) in enumerate([
                (im.convert("RGB"), f"Surogat · płyta {pl(v, 2)} m", f"{pl(t, 1)} ms (GPU)"),
                (ref_tiles[near], f"AvaFrame · najbliższy przebieg {pl(near)} m", f"≈ {pl(M['s_per_run_avaframe'], 0)} s (CPU)")]):
            can.paste(img, (x0 + j * (tile + gap), ytile))
            dd = ImageDraw.Draw(can, "RGBA")
            xx = x0 + j * (tile + gap)
            dd.rectangle((xx, ytile, xx + tile, ytile + 50), fill=(*PAPER, 235))
            dd.text((xx + 16, ytile + 25), lab, font=font(24, 750), fill=INK, anchor="lm")
            dd.text((xx + tile - 16, ytile + 25), right, font=font(22, 750), fill=HAZ if j == 0 else INK2, anchor="rm")
        # slider
        d.text((x0, sy), "płyta", font=font(22, 700), fill=INK, anchor="lm")
        d.line((sx0, sy, sx1, sy), fill=LINE, width=10)
        xv = sx0 + (v - 0.4) / 1.6 * (sx1 - sx0)
        d.line((sx0, sy, xv, sy), fill=(232, 89, 12), width=10)
        for k in lib:
            xk = sx0 + (k - 0.4) / 1.6 * (sx1 - sx0)
            d.line((xk, sy - 16, xk, sy - 8), fill=INK2, width=3)
            d.text((xk, sy + 26), pl(k), font=font(15, 600), fill=INK2, anchor="mm")
        d.ellipse((xv - 16, sy - 16, xv + 16, sy + 16), fill=PAPER, outline=INK, width=4)
        d.text((sx1 + 20, sy), f"{pl(v, 2)} m", font=font(30, 800), fill=HAZ, anchor="lm")
        d.text((x0 + 2 * tile + gap, ytile + tile + 26), "kreski na suwaku: grubości policzone w AvaFrame · "
               "teren GUGiK NMT · szlaki © OSM", font=font(16, 500), fill=INK2, anchor="rm")
        can.save(fd / f"f_{n:04d}.png", compress_level=1)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", str(fd / "f_%04d.png"),
                    "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-movflags", "+faststart", str(dest / "suwak.mp4")], check=True)
    print(f"film: {len(vals)} frames, surrogate median {np.median(ms):.2f} ms/frame")
    return float(np.median(ms))


def main(model_dir, assets, sec_bin, dest, caches):
    model_dir, dest = Path(model_dir), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    A["font"] = Path(assets) / "Archivo-var.ttf"
    A["map"] = Image.open(Path(assets) / "map.png").convert("RGB")
    A["trails"] = json.loads((Path(assets) / "trails.json").read_text(encoding="utf-8"))
    dem, idx, sectors = load_terrain(assets, sec_bin)
    M = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    H = np.load(model_dir / "held_pred.npz")
    ck = torch.load(model_dir / "model.pt", map_location="cuda", weights_only=False)
    net = UNet().cuda()
    net.load_state_dict(ck["state"])
    net.eval()
    D, _ = load_caches(caches)
    board(D, H, M, dem, idx, sectors, dest)
    film_ms = slider_film(D, M, net, dem, idx, sectors, ck["boxes"], dest, model_dir)
    j = {"model": M["model"], "trained_on_runs": M["trained_on_runs"], "train_sectors": len(M["train_sectors"]),
         "held_out_sectors": M["held_out_sectors"], "held_out_runs": M["held_out_runs"],
         "excluded_sectors": M.get("excluded_sectors", []),
         "iou_mean": M["iou_mean"], "iou_by_sector": M["iou_by_sector"],
         "iou_definition": "IoU zasięgu pft > 0,1 m na siatce 400x400, stoki wyłączone z treningu",
         "ms_per_map_gpu": M["ms_per_map_gpu"], "ms_per_map_gpu_film": round(film_ms, 2),
         "s_per_run_avaframe": M["s_per_run_avaframe"],
         "note": f"Dowód koncepcji: U-Net wytrenowany na {M['trained_on_runs']} przebiegach AvaFrame com1DFA "
                 f"(DGX Spark, GPU GB10). Stoki testowe i stoki, których lawiny wchodzą na ich teren, wyłączone z treningu. Przybliża mapę maksymalnej grubości przepływu dla zadanej strefy startowej, "
                 f"grubości płyty i wariantu tarcia; nie zastępuje AvaFrame. Czas AvaFrame: mediana na symulację, "
                 f"1 rdzeń CPU; czas surogatu: jedna mapa 256x256 na GPU."}
    (dest / "surrogate.json").write_text(json.dumps(j, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(j, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])

"""Progress board: newest visuals from filmy/ + data status, one 1920x1080 PNG in filmy/plansze/."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FILMY = ROOT / "filmy"
DATA = ROOT / "web" / "data"
FONT = ROOT / "web" / "vendor" / "fonts" / "Archivo-var.ttf"
PAPER, INK, INK2, HAZ = (244, 239, 228), (29, 27, 23), (90, 82, 68), (166, 59, 0)
W, H = 1920, 1080
THUMBS = FILMY / "plansze" / ".thumbs"


def font(size, weight=700, width=100):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight, width])
    return f


def thumb(p: Path) -> Image.Image:
    if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return Image.open(p).convert("RGB")
    THUMBS.mkdir(parents=True, exist_ok=True)
    out = THUMBS / (p.stem + f"_{int(p.stat().st_mtime)}.jpg")
    if not out.exists():
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-sseof", "-3", "-i", str(p),
                        "-frames:v", "1", "-q:v", "3", str(out)], check=False)
    return Image.open(out).convert("RGB") if out.exists() else Image.new("RGB", (16, 9), (200, 200, 200))


def status():
    lines = []
    def j(name):
        try:
            return json.loads((DATA / name).read_text(encoding="utf-8"))
        except Exception:
            return None
    sc, pr, su = j("scenarios.json"), j("proof.json"), j("surrogate.json")
    lines.append(f"Biblioteka AvaFrame: {sc['count']} symulacji" if sc else "Biblioteka AvaFrame: w toku")
    if pr:
        m = pr.get("misses", {})
        lines.append(f"Dowód: przeoczenia Avalauncher {m.get('avalauncher')} vs reguła 3 dni {m.get('baseline_3d')}")
    else:
        lines.append("Dowód: w toku")
    lines.append(f"Sieć zastępcza: IoU {su.get('iou_mean')}, {su.get('ms_per_map_gpu')} ms/mapa" if su else "Sieć zastępcza: w toku")
    vids = list(FILMY.rglob("*.mp4"))
    lines.append(f"Filmy: {len(vids)} · kadry: {len([p for p in FILMY.rglob('*.png') if 'plansze' not in p.parts])}")
    lines.append("Silnik: " + ("prawdziwy (days.json)" if (DATA / "days.json").exists() else "tymczasowy"))
    return lines


def main():
    media = [p for p in FILMY.rglob("*") if p.suffix.lower() in (".mp4", ".png", ".jpg")
             and "plansze" not in p.parts and "pojedyncze_2d" not in p.parts]
    media.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    picks = media[:9]
    board = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(board)
    now = datetime.now().strftime("%H:%M")
    d.text((40, 34), f"Avalauncher · plansza postępu {now}", font=font(40, 800, 112), fill=INK)
    d.text((40, 88), "Najnowsze materiały z filmy/ (Spark: AvaFrame, rendery 2D i 3D, sieć zastępcza)", font=font(20, 500), fill=INK2)
    x0, y0, cw, ch, gap = 40, 140, 440, 280, 16
    for i, p in enumerate(picks):
        r, c = divmod(i, 3)
        im = thumb(p)
        im.thumbnail((cw, ch - 30))
        x, y = x0 + c * (cw + gap), y0 + r * (ch + gap)
        d.rectangle((x - 2, y - 2, x + cw + 2, y + ch + 2), fill=(231, 223, 207))
        board.paste(im, (x + (cw - im.width) // 2, y + (ch - 30 - im.height) // 2))
        age = int((time.time() - p.stat().st_mtime) / 60)
        d.text((x + 6, y + ch - 24), f"{p.parent.name}/{p.name}"[:52], font=font(15, 650), fill=INK)
        d.text((x + cw - 6, y + ch - 24), f"{age} min temu", font=font(14, 500), fill=INK2, anchor="ra")
    sx = x0 + 3 * (cw + gap) + 24
    d.text((sx, y0), "Stan", font=font(28, 800), fill=INK)
    for k, line in enumerate(status()):
        d.text((sx, y0 + 50 + k * 44), line, font=font(19, 600), fill=HAZ if "w toku" in line else INK)
    out = FILMY / "plansze" / f"plansza_{now.replace(':', '')}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out)
    print(out)


if __name__ == "__main__":
    main()

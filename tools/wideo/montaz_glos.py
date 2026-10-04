# -*- coding: utf-8 -*-
"""Montaz filmu z glosem (wersja v2, glos TTS, take 1).

Wynik: filmy/wideo/avalauncher_film_glos_v3.mp4 (1920x1080, 30 kl./s, H.264 crf 23 veryfast, AAC 48 kHz).
Kazda scena jest renderowana osobno (tylko obraz, te same parametry kodeka), potem concat demuxer
z kopiowaniem strumienia. Dzwiek jest skladany jednym przebiegiem na osi calego filmu, wiec nie ma
dryfu na granicach scen.

Uruchomienie: python tools/wideo/montaz_glos.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FF = r"C:/Users/Przemke/AppData/Local/Programs/Python/Python311/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
SUR = ROOT / "filmy/wideo/surowe"
GLOS = ROOT / "filmy/wideo/glos/v2"
AUD = ROOT / "filmy/wideo/audio"
FONT = ROOT / "web/vendor/fonts/Archivo-var.ttf"
SKRYPT = ROOT / "filmy/wideo/glos/skrypt_tts.json"
OUT = ROOT / "filmy/wideo/avalauncher_film_glos_v3.mp4"
SHEET = ROOT / "filmy/wideo/podglad_glos_v3.jpg"
TMP = Path(tempfile.gettempdir()) / "avalauncher_montaz_glos_v3"

FPS = 30
VENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-r", str(FPS), "-video_track_timescale", "15360"]

# v3: ujecia aplikacji z nagrania 08:33 (*_old: plynne, ok. 16 kl./s, czasy pasuja do planu ponizej);
# nagranie z 09:47 (nowa tapeta) jest skokowe (6-7 kl./s) i nierowno wolniejsze, wiec plan by sie rozjechal.
UDOST = SUR / "komunikator_udostepnianie.mp4"
SRC = {
    "dzwoni": SUR / "komunikator_dzwoni.mp4",
    "rozmowa": SUR / "komunikator_rozmowa.mp4",
    "film": SUR / "komunikator_film.mp4",
    "koniec": SUR / "komunikator_koniec.mp4",
    "A1": SUR / "A1_s04_start_old.mp4",
    "A2": SUR / "A2_s05-06_dzien1_old.mp4",
    "A3": SUR / "A3_s07_dzien2_mgla_old.mp4",
    "A4": SUR / "A4_s07_imgw_old.mp4",
    "A5": SUR / "A5_s08_przelot_old.mp4",
    "A6": SUR / "A6_s10_wylacz_old.mp4",
    "B1": SUR / "B1_s09_biblioteka_old.mp4",
}

LOWER = "{\\b1}Avalauncher{\\b0} · mapa stoków, które mogą zrzucić lawinę na szlak"
CAPTIONS = {
    5: "Grubość płyty i przeloty drona: dane syntetyczne",
    7: "IMGW-PIB Kasprowy Wierch, 11–13.01.2025: +34 cm śniegu w 3 dni (dane prawdziwe)",
    8: "Przelot 20 min · symulacja, dane syntetyczne",
    9: "Fizyka AvaFrame sprawdzona na 5 prawdziwych lawinach z Austrii i Szwajcarii: "
       "typowa pomyłka zasięgu 92 m (test bez podglądania)",
}
CARD_EXTRA = "Głos Staszka: syntezator mowy ElevenLabs."
CARD_WALL = "Tapeta: Radek Kucharski, Wikimedia Commons, CC BY 4.0"
LOWER_END_S2 = 16.5  # w rozmowie od 16,6 s jest wlasny podpis kamery "Avalauncher · HackYeah 2026 · Defence"

VOICE_LEAD = 0.05     # glos startuje 50 ms po cieciu
S11_VOICE_AT = 0.9    # po dzwieku rozlaczenia


def run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-4000:])
        raise SystemExit(f"ffmpeg error ({args[1:4]}...)")
    return p


def duration(path):
    p = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def mean_volume(path):
    p = subprocess.run([FF, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", p.stderr).group(1))


def pixel_hex(path, t, x, y):
    p = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(path),
                        "-frames:v", "1", "-vf", f"format=rgb24,crop=1:1:{x}:{y}", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True)
    r, g, b = p.stdout[:3]
    return f"0x{r:02x}{g:02x}{b:02x}"


def ass_time(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Archivo,40,&H00FFFFFF,&H00FFFFFF,&H40000000,&H40000000,0,0,0,0,100,100,0,0,3,10,0,2,80,80,16,1
Style: SubShare,Archivo,40,&H00FFFFFF,&H00FFFFFF,&H40000000,&H40000000,0,0,0,0,100,100,0,0,3,10,0,2,40,360,16,1
Style: Cap,Archivo,20,&H00FFFFFF,&H00FFFFFF,&H38171B1D,&H38171B1D,0,0,0,0,100,100,0,0,3,5,0,7,330,230,46,1
Style: Lower,Archivo,34,&H00E4EFF4,&H00E4EFF4,&H20171B1D,&H20171B1D,0,0,0,0,100,100,0,0,3,12,0,1,40,600,140,1
Style: Card,Archivo,26,&H00171B1D,&H00171B1D,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(path, events):
    lines = [ASS_HEAD]
    for (a, b, style, text) in events:
        lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},{style},,0,0,0,,{text}\n")
    path.write_text("".join(lines), encoding="utf-8")


def subtitle_events(napisy, v0, vd, scene_dur, style):
    """Napisy rozlozone proporcjonalnie do dlugosci tekstu na czas glosu."""
    if not napisy:
        return []
    w = [len(x) + 8 for x in napisy]
    tot = sum(w)
    ev = []
    acc = 0
    starts = []
    for wi in w:
        starts.append(v0 + vd * acc / tot)
        acc += wi
    starts[0] = min(starts[0], 0.0) if v0 < 0.2 else starts[0]
    end_last = min(scene_dur, v0 + vd + 0.35)
    for i, txt in enumerate(napisy):
        a = starts[i]
        b = starts[i + 1] if i + 1 < len(napisy) else end_last
        ev.append((a, b, style, txt))
    return ev


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "fonts").mkdir(exist_ok=True)
    shutil.copy(FONT, TMP / "fonts" / "Archivo-var.ttf")
    (TMP / "clock.txt").write_text("6:01", encoding="utf-8")

    sk = json.loads(SKRYPT.read_text(encoding="utf-8"))
    napisy = {s["scena"]: s["napisy"] for s in sk["sceny"]}
    vfile = {n: GLOS / f"s{n:02d}_t1.mp3" for n in range(2, 12)}
    vd = {n: duration(f) for n, f in vfile.items()}

    # --- dlugosci scen (w klatkach) ---
    dur = {1: 3.7}
    for n in range(2, 11):
        dur[n] = vd[n] + 0.4
    dur[11] = S11_VOICE_AT + vd[11] + 1.2
    frames = {n: round(d * FPS) for n, d in dur.items()}
    dur = {n: f / FPS for n, f in frames.items()}
    start = {}
    t = 0.0
    for n in range(1, 12):
        start[n] = t
        t += dur[n]
    total = t
    print("sceny:", {n: round(d, 2) for n, d in dur.items()}, "razem", round(total, 2))

    # --- podklad AvaKomunikatora (udostepnianie): przedzialy lokalne na scene ---
    # 3-6 liniowo 0..26 s (przed efektem "piksele" 32,6 s), 7: 26..36, 8: 36..60,3,
    # 9 (czesc z biblioteka): 60,5..70 bez rozciagania (czat "a skad ona to wie?" 61 s),
    # 10: 73,4..81,9 (Halny na klawiaturze 74 s).
    span36 = sum(dur[n] for n in (3, 4, 5, 6))
    base = {}
    acc = 0.0
    for n in (3, 4, 5, 6):
        base[n] = (26.0 * acc / span36, 26.0 * (acc + dur[n]) / span36, dur[n])
        acc += dur[n]
    base[7] = (26.0, 36.0, dur[7])
    base[8] = (36.0, 60.3, dur[8])
    base[9] = (60.5, 70.0, 9.5)
    base[10] = (73.4, 81.9, dur[10])

    # --- kolor paska zadan pod zegarem w ujeciach aplikacji ---
    tray = {k: pixel_hex(SRC[k], 1.0, 1596, 884) for k in ("A2", "A3", "A4", "A5", "B1")}

    # --- plan ujec: (zrodlo, od, do, predkosc, uklad, zegar) ; ostatni segment wypelnia scene ---
    a2_3d = 39.6 - 23.0
    plan = {
        1: [("dzwoni", 0.5, 4.2, 1.0, "full", False)],
        2: [("rozmowa", 0.0, 26.0, 1.0, "full", False)],
        3: [("A1", 0.0, 2.25, 1.0, "share", False), ("A2", 0.0, 10.8, 1.0, "share", True)],
        4: [("A3", 3.5, 7.5, 1.0, "share", True), ("A5", 0.0, 30.0, 1.0, "share", True)],
        5: [("A2", 5.5, 39.6, 1.0, "share", True)],
        6: [("A2", 23.0, 39.6, a2_3d / dur[6], "share", True)],
        7: [("A3", 3.5, 8.5, 1.0, "share", True), ("A4", 4.5, 9.5, 1.0, "share", True),
            ("A3", 12.0, 17.6, 1.0, "share", True)],
        8: [("A5", 0.5, 14.3, 1.0, "share", True), ("A5", 14.3, 26.5, 4.0, "share", True),
            ("A5", 26.5, 38.7, 1.0, "share", True)],
        9: [("B1", 1.5, 11.0, 1.0, "share", True), ("film", 1.0, 14.0, 1.0, "full", False)],
        10: [("A6", 3.5, 12.0, 2.0, "share", False), ("A6", 12.0, 24.2, 1.0, "share", False)],
        11: [("koniec", 0.0, 8.0, 1.0, "full", False)],
    }

    concat_lines = []
    for n in range(1, 12):
        D = dur[n]
        segs = plan[n]
        inputs = []
        chains = []
        labels = []
        tloc = 0.0  # czas w scenie
        for k, (src, a, b, sp, lay, clock) in enumerate(segs):
            seg_len = (b - a) / sp
            d = D - tloc if k == len(segs) - 1 else min(seg_len, D - tloc)
            d = max(d, 1.0 / FPS)
            fi = len(inputs) // 2
            inputs += ["-i", str(SRC[src])]
            fg = (f"[{fi}:v]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)/{sp:.5f},fps={FPS},")
            if lay == "share":
                fg += "scale=1600:900:in_range=pc:out_range=tv,format=yuv420p,"
                if clock:
                    col = tray.get(src, "0x3a95e8")
                    fg += (f"drawbox=x=1543:y=873:w=55:h=22:color={col}:t=fill,"
                           f"drawtext=fontfile=fonts/Archivo-var.ttf:textfile=clock.txt:fontsize=14:"
                           f"fontcolor=white:x=1570-tw/2:y=878,")
            else:
                fg += "format=yuv420p,"
            fg += f"tpad=stop_mode=clone:stop_duration=60,trim=duration={d:.4f},setpts=PTS-STARTPTS"
            if lay == "share":
                la, lb, span = base[n]
                ba = la + (lb - la) * tloc / span
                bb = la + (lb - la) * min(tloc + d, span) / span
                k_st = d / max(bb - ba, 0.04)
                bi = len(inputs) // 2
                inputs += ["-i", str(UDOST)]
                chains.append(fg + f"[fg{k}]")
                chains.append(f"[{bi}:v]trim=start={ba:.3f}:end={bb:.3f},setpts=(PTS-STARTPTS)*{k_st:.5f},"
                              f"fps={FPS},format=yuv420p,tpad=stop_mode=clone:stop_duration=60,"
                              f"trim=duration={d:.4f},setpts=PTS-STARTPTS[bg{k}]")
                chains.append(f"[bg{k}][fg{k}]overlay=0:90:shortest=1[v{k}]")
            else:
                chains.append(fg + f"[v{k}]")
            labels.append(f"[v{k}]")
            tloc += d

        # napisy, podpisy, belka
        ev = []
        style = "SubShare" if 3 <= n <= 10 else "Sub"
        if n == 11:
            ev += subtitle_events(napisy[n], S11_VOICE_AT, vd[n], D, style)
            ev.append((0, D, "Card", "{\\an8\\pos(960,758)}" + CARD_EXTRA))
            ev.append((0, D, "Card", "{\\an8\\pos(960,792)\\fs22}" + CARD_WALL))
        elif n >= 2:
            ev += subtitle_events(napisy[n], VOICE_LEAD, vd[n], D, style)
        if n == 1:
            ev.append((0, D, "Lower", LOWER))
        elif n == 2:
            ev.append((0, min(D, LOWER_END_S2), "Lower", LOWER))
        if n in CAPTIONS:
            ev.append((0, D, "Cap", "{\\q2}" + CAPTIONS[n]))
        write_ass(TMP / f"s{n:02d}.ass", ev)

        join = "".join(labels) + f"concat=n={len(labels)}:v=1:a=0[vc]" if len(labels) > 1 else None
        if join:
            chains.append(join)
            last = "[vc]"
        else:
            last = labels[0]
        chains.append(f"{last}tpad=stop_mode=clone:stop_duration=10,trim=end_frame={frames[n]},"
                      f"setpts=PTS-STARTPTS,subtitles=s{n:02d}.ass:fontsdir=fonts,format=yuv420p[vout]")
        (TMP / f"s{n:02d}_filter.txt").write_text(";\n".join(chains), encoding="utf-8")
        out = TMP / f"s{n:02d}.mp4"
        run([FF, "-hide_banner", "-loglevel", "error", "-y", *inputs,
             "-filter_complex_script", f"s{n:02d}_filter.txt", "-map", "[vout]", "-an",
             *VENC, "-frames:v", str(frames[n]), str(out)], cwd=TMP)
        concat_lines.append(f"file '{out.as_posix()}'\n")
        print(f"scena {n}: {D:.2f} s gotowa")

    (TMP / "lista.txt").write_text("".join(concat_lines), encoding="utf-8")

    # --- dzwiek: jeden przebieg na osi calego filmu ---
    ain = []
    af = []
    lab = []

    def add(path, at, chain):
        i = len(ain) // 2
        ain.extend(["-i", str(path)])
        ms = int(round(at * 1000))
        af.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,{chain},"
                  f"aresample=48000,adelay=delays={ms}:all=1[a{i}]")
        lab.append(f"[a{i}]")

    g_ring = -21.0 - mean_volume(AUD / "dzwonek.wav")
    g_klik = -24.0 - mean_volume(AUD / "klik.wav")
    g_roz = -22.0 - mean_volume(AUD / "rozlaczenie.wav")
    add(AUD / "dzwonek.wav", 0.0, f"atrim=0:{dur[1]:.3f},volume={g_ring:.1f}dB,"
                                  f"afade=t=out:st={dur[1] - 0.45:.3f}:d=0.45")
    add(AUD / "klik.wav", 3.4, f"volume={g_klik:.1f}dB")          # klik "Odbierz" (3,9 s w ujeciu)
    add(AUD / "rozlaczenie.wav", start[11] + 0.05, f"volume={g_roz:.1f}dB")
    for n in range(2, 12):
        at = start[n] + (S11_VOICE_AT if n == 11 else VOICE_LEAD)
        add(vfile[n], at, "loudnorm=I=-16:TP=-1.5:LRA=11")
    af.append("".join(lab) + f"amix=inputs={len(lab)}:normalize=0:duration=longest,"
              f"apad,atrim=0:{total:.3f},alimiter=limit=0.95[aout]")
    (TMP / "audio_filter.txt").write_text(";\n".join(af), encoding="utf-8")
    run([FF, "-hide_banner", "-loglevel", "error", "-y", *ain, "-filter_complex_script", "audio_filter.txt",
         "-map", "[aout]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", "audio.wav"], cwd=TMP)

    # --- zlozenie ---
    run([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "lista.txt",
         "-i", "audio.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", str(OUT)], cwd=TMP)

    # --- podglad: 8 klatek ---
    picks = [start[1] + 2, start[2] + 18, start[3] + 8, start[5] + 9, start[7] + 7, start[8] + 15,
             start[9] + 15, start[11] + 3]
    sel = "+".join(f"eq(n\\,{round(p * FPS)})" for p in picks)
    run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(OUT), "-vf",
         f"select={sel},scale=640:360,tile=4x2", "-frames:v", "1", "-fps_mode", "vfr", str(SHEET)])
    print("OK", OUT, round(total, 2), "s", round(OUT.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()

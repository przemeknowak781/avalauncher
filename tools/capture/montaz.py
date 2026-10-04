# Montaż wersji roboczej filmu demo (docs/15_wideo.md, sceny 1-11), bez głosu, z napisami.
# Uruchom z katalogu repo: python tools/capture/montaz.py
# Wejście: filmy/wideo/surowe/*.mp4, filmy/wideo/audio/*.wav. Wyjście: filmy/wideo/avalauncher_film_roboczy.mp4, podglad.jpg.
import os, subprocess, sys

FF = r"C:\Users\Przemke\AppData\Local\Programs\Python\Python311\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)
R = "filmy/wideo/surowe"
OUT = "filmy/wideo"
TMP = os.path.join(OUT, "_montaz")
os.makedirs(TMP, exist_ok=True)
FONT = "web/vendor/fonts/Archivo-var.ttf"
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30", "-an"]


SZYBKO = "--szybko" in sys.argv  # nie przebudowuj istniejących segmentów, tylko napisy, dźwięk i podgląd


def run(args):
    print(" ".join(a if " " not in a else f'"{a}"' for a in args[:12]), "...", flush=True)
    subprocess.run([FF, "-v", "error", "-y"] + args, check=True)


def clock(label, enable="1"):
    # Zegar zasobnika aplikacji (slot 1600x900): przykrywamy godzinę nagrania godziną z filmu.
    return (f"drawbox=x=1543:y=871:w=56:h=27:color=0x0e91eb:t=fill:enable='{enable}',"
            f"drawtext=fontfile={FONT}:text='{label}':fontcolor=white:fontsize=15:x=1571-tw/2:y=884-th/2:enable='{enable}'")


def piece_chain(idx, speed, dur, extra=""):
    sp = f"setpts=(PTS-STARTPTS)/{speed}" if speed != 1 else "setpts=PTS-STARTPTS"
    return (f"[{idx}:v]{sp},fps=30,tpad=stop_mode=clone:stop_duration=2,trim=duration={dur},"
            f"setpts=PTS-STARTPTS{extra}[p{idx}]")


def slot_segment(name, bg, bg_ss, bg_dur, pieces):
    """bg: plik komunikatora (1920x1080), pieces: (plik, od, do, czas_wyjściowy, zegar)."""
    total = round(sum(p[3] for p in pieces), 3)
    assert abs(total - bg_dur) < 1e-6, (name, total, bg_dur)
    args = ["-ss", str(bg_ss), "-t", str(bg_dur + 1), "-i", f"{R}/{bg}"]
    chains, labels = [], []
    for i, (f, a, b, d, clk) in enumerate(pieces, start=1):
        args += ["-ss", str(a), "-t", str(b - a), "-i", f"{R}/{f}"]
        speed = round((b - a) / d, 4)
        chains.append(piece_chain(i, speed, d, "," + clock(clk) if clk else ""))
        labels.append(f"[p{i}]")
    fc = ";".join(chains)
    fc += f";{''.join(labels)}concat=n={len(pieces)}:v=1:a=0[slot]"
    fc += f";[0:v]setpts=PTS-STARTPTS,fps=30,trim=duration={bg_dur},setpts=PTS-STARTPTS[bg]"
    fc += ";[bg][slot]overlay=0:90:eof_action=pass,format=yuv420p[v]"
    out = f"{TMP}/{name}.mp4"
    if SZYBKO and os.path.exists(out):
        return out
    run(args + ["-filter_complex", fc, "-map", "[v]", "-t", str(bg_dur)] + ENC + [out])
    return out


def plain_segment(name, src, ss, dur):
    out = f"{TMP}/{name}.mp4"
    if SZYBKO and os.path.exists(out):
        return out
    run(["-ss", str(ss), "-t", str(dur + 0.5), "-i", f"{R}/{src}", "-vf",
         f"setpts=PTS-STARTPTS,fps=30,tpad=stop_mode=clone:stop_duration=1,trim=duration={dur},setpts=PTS-STARTPTS,format=yuv420p",
         "-t", str(dur)] + ENC + [out])
    return out


# Oś czasu filmu (s). Komunikator: dzwoni 0=0:00, rozmowa 0=0:03, owca 0=0:28,2, udostepnianie 0=0:27, film 0=1:34, koniec 0=1:48.
segs = []
segs.append(plain_segment("s01_dzwoni", "komunikator_dzwoni.mp4", 0.0, 4.1))            # 0:00-0:04,1
segs.append(plain_segment("s02_rozmowa", "komunikator_rozmowa.mp4", 1.1, 24.1))         # 0:04,1-0:28,2
segs.append(plain_segment("s03_owca", "komunikator_owca.mp4", 0.0, 3.8))                # 0:28,2-0:32
segs.append(slot_segment("s04_ekran", "komunikator_udostepnianie.mp4", 5.0, 62.0, [   # 0:32-1:34
    ("A1_s04_start.mp4", 0.0, 2.0, 2.0, "6\\:01"),            # 0:32 ekran powitalny
    ("A2_s05-06_dzien1.mp4", 0.3, 3.8, 3.5, "6\\:01"),        # 0:34 dymek „Przelot wykonany o 6:00”
    ("A2_s05-06_dzien1.mp4", 10.0, 23.5, 6.75, "6\\:01"),     # 0:37,5 klik znaczka 1, okno flagi, klik 3D
    ("A2_s05-06_dzien1.mp4", 23.5, 39.6, 7.75, "6\\:01"),     # 0:44,25 odtwarzacz 3D (przyspieszony)
    ("A3_s07_dzien2_mgla.mp4", 3.5, 7.0, 3.5, "6\\:01"),      # 0:52 dzień 2, mgła, „Przelot odwołany”
    ("A4_s07_imgw.mp4", 8.8, 12.8, 4.0, "6\\:01"),            # 0:55,5 wstawka IMGW, podpowiedź „Epizod … +34 cm”
    ("A3_s07_dzien2_mgla.mp4", 10.8, 14.3, 3.5, "6\\:01"),    # 0:59,5 „Liliowe E · nie wiem”, „4 sektory: Nie wiem”
    ("A5_s08_przelot.mp4", 1.0, 38.7, 25.0, "6\\:01"),        # 1:03 plan i przelot (×1,5)
    ("B1_s09_biblioteka.mp4", 1.0, 12.4, 6.0, "6\\:02"),      # 1:28 biblioteka (×1,9)
]))
segs.append(plain_segment("s05_film", "komunikator_film.mp4", 0.0, 7.0))                # 1:34-1:41
segs.append(slot_segment("s06_wylacz", "komunikator_udostepnianie.mp4", 74.0, 7.0, [  # 1:41-1:48
    ("A6_s10_wylacz.mp4", 3.0, 9.5, 2.0, "6\\:02"),
    ("A6_s10_wylacz.mp4", 9.5, 13.3, 1.52, "6\\:02"),
    ("A6_s10_wylacz.mp4", 13.3, 16.78, 3.48, "6\\:02"),
]))
segs.append(plain_segment("s07_koniec", "komunikator_koniec.mp4", 0.0, 6.0))           # 1:48-1:54

with open(f"{TMP}/lista.txt", "w", encoding="utf-8") as fh:
    for s in segs:
        fh.write(f"file '{os.path.abspath(s).replace(os.sep, '/')}'\n")
base = f"{TMP}/podklad.mp4"
run(["-f", "concat", "-safe", "0", "-i", f"{TMP}/lista.txt", "-c", "copy", base])

# Dźwięki UI (własne, tools/wideo/dzwieki.py): dzwonek do kliknięcia „Odbierz”, kliki, rozłączenie, motyw planszy.
aud = [
    ("dzwonek.wav", 1.0, "atrim=0:2.9,afade=t=out:st=2.4:d=0.5,volume=0.8"),
    ("klik.wav", 3.9, "volume=0.9"),
    ("klik.wav", 31.75, "volume=0.9"),
    ("rozlaczenie.wav", 108.1, "volume=0.8"),
    ("plansza_motyw.wav", 109.6, "volume=0.6"),
]
args = ["-i", base, "-f", "lavfi", "-t", "114", "-i", "anullsrc=r=48000:cl=stereo"]
fc = []
for i, (f, t, flt) in enumerate(aud, start=2):
    args += ["-i", f"{OUT}/audio/{f}"]
    ms = int(t * 1000)
    fc.append(f"[{i}:a]{flt},aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
fc.append("[1:a]" + "".join(f"[a{i}]" for i in range(2, 2 + len(aud))) + f"amix=inputs={1 + len(aud)}:normalize=0:duration=first[a]")
fc.append("[0:v]ass=filmy/wideo/napisy_film.ass:fontsdir=filmy/wideo/_montaz/fonts[v]")
final = f"{OUT}/avalauncher_film_roboczy.mp4"
crf = "21"
run(args + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
            "-crf", crf, "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-t", "114",
            "-movflags", "+faststart", final])

# Arkusz podglądu: 6 klatek (sceny 2, 5, 7, 8, 9, 10).
times = [10, 40, 57, 75, 90, 105]
sel = "+".join(f"eq(n\\,{int(t * 30)})" for t in times)
run(["-i", final, "-vf", f"select='{sel}',scale=960:-1,tile=2x3", "-frames:v", "1", "-q:v", "3", f"{OUT}/podglad.jpg"])
print("OK", final)

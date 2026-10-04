# Napisy (docs/15_wideo.md 2.1) i podpisy z tabeli scen do pliku ASS dla montażu wersji roboczej.
# Uruchom z katalogu repo: python tools/capture/napisy_ass.py
import os
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
srt = open("filmy/wideo/surowe/napisy_robocze.srt", encoding="utf-8").read().strip().split("\n\n")


def conv(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return f"{int(h)}:{m}:{s}.{ms[:2]}"


ev = []
for b in srt:
    lines = b.split("\n")
    a, z = lines[1].split(" --> ")
    ev.append(f"Dialogue: 0,{conv(a)},{conv(z)},Napis,,0,0,0,,{' '.join(lines[2:])}")

P = r"{\an6\pos(1700,60)}"
B = r"{\b1}"
S = r"\N{\b0\fs20}"
cap = [
    ("0:00:32.00", "0:00:45.00", B + "12.01.2025 · dron poleciał" + S + "Grubość płyty i przeloty drona: dane syntetyczne."),
    ("0:00:45.00", "0:00:52.00", B + "12.01.2025 · dron poleciał" + S + "Przebieg AvaFrame z biblioteki · teren i ortofotomapa: GUGiK · śnieg w 3D: syntetyczny"),
    ("0:00:52.00", "0:00:55.50", B + "13.01.2025 · zamieć, przelot odwołany"),
    ("0:00:55.50", "0:00:59.50", B + "13.01.2025 · zamieć, przelot odwołany" + S + "IMGW-PIB Kasprowy Wierch, 11–13.01.2025: +34 cm śniegu w 3 dni, 72 h zamieci, pokrywa 51 → 85 cm (dane prawdziwe)"),
    ("0:00:59.50", "0:01:03.00", B + "13.01.2025 · zamieć, przelot odwołany"),
    ("0:01:03.00", "0:01:28.00", B + "Przelot 20 min · symulacja, dane syntetyczne"),
    ("0:01:28.00", "0:01:34.00", B + "1566 symulacji lawin AvaFrame w 30,4 min" + S + "Fizyka AvaFrame sprawdzona na 5 prawdziwych lawinach z Austrii i Szwajcarii: typowa pomyłka zasięgu 92 m (test bez podglądania)"),
    ("0:01:34.00", "0:01:41.00", B + "Sieć neuronowa: ok. 4500× szybciej, zgodność zasięgu 0,81 na stokach spoza treningu" + S + "Dowód koncepcji, nie zastępuje AvaFrame."),
]
for a, z, t in cap:
    ev.append(f"Dialogue: 1,{a},{z},Podpis,,0,0,0,,{P}{t}")

hdr = """[Script Info]
; Napisy i podpisy wersji roboczej filmu (docs/15_wideo.md). Generowane przez tools/capture/napisy_ass.py.
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Napis,ArchivoFilm,40,&H00FFFFFF,&H00FFFFFF,&H00171B1D,&H00171B1D,0,0,0,0,100,100,0,0,3,10,0,2,60,60,20,1
Style: Podpis,ArchivoFilm,25,&H00171B1D,&H00171B1D,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,6,40,220,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open("filmy/wideo/napisy_film.ass", "w", encoding="utf-8").write(hdr + "\n".join(ev) + "\n")
print(len(ev), "zdarzeń")

# libass nie wybiera instancji z czcionki zmiennej (spada na Arial), więc robimy statyczne Archivo 400 i 700.
os.makedirs("filmy/wideo/_montaz/fonts", exist_ok=True)
for w, style in [(400, "Regular"), (700, "Bold")]:
    inst = instancer.instantiateVariableFont(TTFont("web/vendor/fonts/Archivo-var.ttf"), {"wght": w, "wdth": 100})
    name = inst["name"]
    for nid in (16, 17, 21, 22, 25):
        name.removeNames(nameID=nid)
    name.setName("ArchivoFilm", 1, 3, 1, 0x409)
    name.setName(style, 2, 3, 1, 0x409)
    name.setName(f"ArchivoFilm {style}", 4, 3, 1, 0x409)
    name.setName(f"ArchivoFilm-{style}", 6, 3, 1, 0x409)
    inst["OS/2"].usWeightClass = w
    if w == 700:
        inst["OS/2"].fsSelection = (inst["OS/2"].fsSelection | 0x20) & ~0x40
        inst["head"].macStyle |= 1
    else:
        inst["OS/2"].fsSelection = (inst["OS/2"].fsSelection | 0x40) & ~0x21
        inst["head"].macStyle &= ~1
    inst.save(f"filmy/wideo/_montaz/fonts/ArchivoFilm-{style}.ttf")

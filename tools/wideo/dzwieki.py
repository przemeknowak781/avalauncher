"""Własne dźwięki AvaKomunikatora (docs/15_wideo.md, sekcja 4.3): dzwonek, rozłączenie, klik.

Dzwonek: podhalańska kwarta lidyjska G4 D5 C#5 D5 (pauza) G4 D5 C#5 D5 E5, dwa razy, 132 BPM, ton trójkątny.
Użycie: python tools/wideo/dzwieki.py  ->  filmy/wideo/audio/*.wav
"""
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path("filmy/wideo/audio")
NUTY = {"G4": 392.00, "C#5": 554.37, "D5": 587.33, "E5": 659.25, "A4": 440.00, "D4": 293.66}


def tri(freq, dur, decay=7.0, amp=0.5):
    t = np.arange(int(SR * dur)) / SR
    x = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    env = np.exp(-decay * t) * np.minimum(1, t / 0.004)
    return amp * x * env


def zapisz(name, x):
    OUT.mkdir(parents=True, exist_ok=True)
    x = np.clip(x / max(1e-9, np.abs(x).max()) * 0.8, -1, 1)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print("zapisano", OUT / name)


def melodia(seq, osemka):
    parts = []
    for n in seq:
        parts.append(np.zeros(int(SR * osemka)) if n is None else tri(NUTY[n], osemka, decay=6.0))
    return np.concatenate(parts)


osemka = 60 / 132 / 2
motyw = ["G4", "D5", "C#5", "D5", None, "G4", "D5", "C#5", "D5", "E5", None, None]
dzwonek = np.concatenate([melodia(motyw, osemka), melodia(motyw, osemka), np.zeros(int(SR * 0.6))])
zapisz("dzwonek.wav", dzwonek)
zapisz("rozlaczenie.wav", np.concatenate([tri(NUTY["D5"], 0.22, 5), tri(NUTY["G4"], 0.5, 4)]))
zapisz("klik.wav", tri(1800, 0.03, 120) + 0.3 * np.random.default_rng(1).standard_normal(int(SR * 0.03)) * np.exp(-np.arange(int(SR * 0.03)) / SR * 200))
zapisz("plansza_motyw.wav", melodia(motyw[:10], osemka * 1.6))

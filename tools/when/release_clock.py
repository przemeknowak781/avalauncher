"""Zegar uwolnienia (PoC): KIEDY lawiny są prawdopodobne, na prawdziwej zimie 2024/25.

Heurystyka, nie prognoza; docelowo model pokrywy SNOWPACK. Jedno zdanie na pomysł:
- Doba dla poranka D: przyrost PKSN na ranek D i meteorologia doby D-1 (opad, zamieć, temperatura).
- Świeży śnieg dobowy = większa z dwóch: przyrost PKSN albo opad śnieżny 1 mm -> 1 cm
  (stacja to wywiewana kopuła, sam przyrost PKSN zaniża).
- Płyta h = świeży śnieg z 3 dób (Mayer i in. 2023) z osiadaniem 15 %/dobę, razy nawianie:
  stoki zawietrzne względem założonego wiatru W-SW zyskują do +100 % przy 48 h zamieci w 3 doby,
  nawietrzne tracą do 30 %; kierunku wiatru IMGW nie podaje dla tej zimy, więc W-SW to założenie.
- Uwolnienie suche = logistyka w h, te same progi co silnik: 0,3 m rzadko, 0,5 m zwykle.
- Uwolnienie mokre = deszcz na śnieg albo silne ocieplenie powyżej 0 °C po świeżym śniegu
  (stoki dosłoneczne mocniej); P_uwolnienia = max(suche, mokre).
- Skutek = udział analogów z biblioteki AvaFrame dla danego sektora przy grubości h, które
  kładą na szlaku >= 0,5 m płynącego śniegu (jak w web/engine.js; poniżej 0,4 m proporcjonalnie mniej).
- Ryzyko = P_uwolnienia x skutek; podsumowanie dnia = liczba sektorów z ryzykiem >= 0,5.
"""
import json
import math
import os
from collections import defaultdict
from datetime import date, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WEB = os.path.join(ROOT, "web", "data")

HIT_PFT_M = 0.5        # web/engine.js HIT_PFT_M
RELEASE_MIN_M = 0.3    # web/engine.js RELEASE_MIN_M
RELEASE_FULL_M = 0.5   # web/engine.js RELEASE_FULL_M
RISK_THRESHOLD = 0.5   # web/engine.js HIT_SHARE
SETTLE = 0.15          # osiadanie świeżego śniegu na dobę
WIND_FROM_DEG = 247.5  # założony wiatr W-SW
LEE_GAIN = 1.0         # maks. nawianie na stoku zawietrznym
SCOUR = 0.3            # maks. wywiewanie na stoku nawietrznym
BLOW_FULL_H = 48.0     # godziny zamieci w 3 doby dające pełne nawianie
START, END = date(2024, 11, 1), date(2025, 4, 30)
ASPECT_DEG = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
SUN = {"S": 1.0, "SE": 0.9, "SW": 0.9, "E": 0.6, "W": 0.6, "NE": 0.35, "NW": 0.35, "N": 0.25}


def logistic(x, mid, scale):
    return 1.0 / (1.0 + math.exp(-(x - mid) / scale))


def dry_release(h):
    # mid 0.4 m, scale 0.045 -> ~0.1 at 0.3 m, ~0.9 at 0.5 m
    return logistic(h, (RELEASE_MIN_M + RELEASE_FULL_M) / 2, 0.045)


def load_library():
    sc = json.load(open(os.path.join(WEB, "scenarios.json"), encoding="utf-8"))
    by = defaultdict(lambda: defaultdict(list))
    for r in sc["runs"]:
        hit = any(p >= HIT_PFT_M for p in r.get("hits_pft_m", []))
        by[r["sector"]][round(r["relTh"], 2)].append(hit)
    lib = {}
    for s, lv in by.items():
        levels = sorted((th, sum(v) / len(v)) for th, v in lv.items())
        lib[s] = {"levels": levels, "any_hit": any(x for v in lv.values() for x in v)}
    return lib, sc["count"]


def reach_at(levels, h):
    if h <= 0:
        return 0.0
    th0, r0 = levels[0]
    if h < th0:
        return r0 * h / th0  # cieńsza niż najcieńsza symulacja: proporcjonalnie mniej
    for (ta, ra), (tb, rb) in zip(levels, levels[1:]):
        if h < tb:
            return ra + (h - ta) / (tb - ta) * (rb - ra)
    return levels[-1][1]


def main():
    met = json.load(open(os.path.join(WEB, "kasprowy_2024_25.json"), encoding="utf-8"))
    sectors = json.load(open(os.path.join(WEB, "sectors.json"), encoding="utf-8"))
    lib, n_runs = load_library()
    by_date = {d["date"]: d for d in met["days"]}

    def g(dt, key):
        v = by_date.get(dt.isoformat(), {}).get(key)
        return 0.0 if v is None else float(v)

    def ptype(dt):
        return by_date.get(dt.isoformat(), {}).get("precip_type")

    def hn(dt):  # świeży śnieg na ranek dt [m]
        prev = dt - timedelta(days=1)
        snow_mm = g(prev, "precip_mm") if ptype(prev) == "S" else 0.0
        return max(g(dt, "new_cm"), snow_mm) / 100.0

    days, hs, newsnow, weather = [], [], [], []
    d = START
    while d <= END:
        days.append(d)
        d += timedelta(days=1)

    secs = [s for s in sectors if s["id"] in lib]
    risk = [[0.0] * len(days) for _ in secs]
    prel = [[0.0] * len(days) for _ in secs]
    hmat = [[0.0] * len(days) for _ in secs]
    kind = [[""] * len(days) for _ in secs]

    for j, dt in enumerate(days):
        prev = dt - timedelta(days=1)
        hs_m = g(dt, "hs_cm") / 100.0
        hn3 = sum(hn(dt - timedelta(days=k)) * (1 - SETTLE) ** k for k in range(3))
        blow3 = sum(g(dt - timedelta(days=k + 1), "blowing_h") for k in range(3))
        wind = min(1.0, blow3 / BLOW_FULL_H)
        rain = g(prev, "precip_mm") if ptype(prev) == "W" else 0.0
        tmax = g(prev, "tmax_c")
        hs.append(hs_m)
        newsnow.append(hn(dt))
        weather.append({"hn3_m": round(hn3, 2), "blow3_h": round(blow3, 1), "rain_mm": rain, "tmax_c": tmax})
        # mokre: deszcz na śnieg (>= 5 mm) albo ocieplenie > ~4,5 °C po >= 15 cm świeżego śniegu w 3 doby
        wet_rain = logistic(rain, 6.0, 1.5) if hs_m >= 0.2 else 0.0
        hn5 = sum(hn(dt - timedelta(days=k)) for k in range(5))
        wet_warm = logistic(tmax, 4.5, 1.0) * min(1.0, hn5 / 0.3) if hs_m >= 0.2 else 0.0
        for i, s in enumerate(secs):
            rel = math.radians(ASPECT_DEG[s["aspect"]] - (WIND_FROM_DEG + 180) % 360)
            c = math.cos(rel)
            load = 1 + LEE_GAIN * wind * max(0.0, c) - SCOUR * wind * max(0.0, -c)
            h = min(hn3 * load, hs_m)
            dry = dry_release(h) if h > 0.05 else 0.0
            wet = max(wet_rain, wet_warm * SUN[s["aspect"]])
            p = max(dry, wet)
            # mokra lawina rusza całą świeżą warstwą, co najmniej świeży śnieg z 5 dób
            h_mass = max(h, min(hn5, hs_m)) if wet > dry else h
            cons = reach_at(lib[s["id"]]["levels"], h_mass) if lib[s["id"]]["any_hit"] else 0.0
            risk[i][j] = p * cons
            prel[i][j] = p
            hmat[i][j] = h
            kind[i][j] = "mokra" if wet > dry else "sucha"

    summary = []
    for j, dt in enumerate(days):
        col = [(risk[i][j], secs[i]["id"]) for i in range(len(secs))]
        over = sorted([c for c in col if c[0] >= RISK_THRESHOLD], reverse=True)
        summary.append({
            "date": dt.isoformat(),
            "sectors_over": len(over),
            "max_risk": round(max(c[0] for c in col), 2),
            "top": [sid for _, sid in over[:5]],
            "kind": max(((kind[i][j], risk[i][j]) for i in range(len(secs))), key=lambda x: x[1])[0] if over else None,
            **weather[j],
            "hs_m": round(hs[j], 2),
        })

    out = {
        "source": "Pogoda: IMGW-PIB Kasprowy Wierch, dobowe dane synoptyczne (prawdziwe). "
                  f"Skutek: biblioteka AvaFrame com1DFA ({n_runs} symulacji). Model uwolnienia: heurystyka PoC.",
        "note": "Heurystyka, nie prognoza; docelowo model pokrywy SNOWPACK. Płyta = świeży śnieg z 3 dób "
                "(osiadanie 15 %/dobę) x nawianie na stokach zawietrznych względem ZAŁOŻONEGO wiatru W-SW "
                "(IMGW nie podaje kierunku wiatru dla tej zimy). Suche uwolnienie: logistyka, 0,3 m rzadko, "
                "0,5 m zwykle. Mokre: deszcz na śnieg lub ocieplenie po świeżym śniegu. Skutek: udział analogów "
                "AvaFrame z >= 0,5 m płynącego śniegu na szlaku. Ryzyko = P_uwolnienia x skutek; próg 0,5. Znana luka: masa mokrej lawiny to świeży śnieg z 5 dób, nie cała pokrywa, więc deszcz na starą pokrywę (15 i 24.04.2025) daje tu małe ryzyko; to zadanie dla SNOWPACK.",
        "threshold": RISK_THRESHOLD,
        "days": [d.isoformat() for d in days],
        "sectors": [s["id"] for s in secs],
        "sector_aspect": [s["aspect"] for s in secs],
        "sector_name": [s["name"] for s in secs],
        "risk": [[round(v, 2) for v in row] for row in risk],
        "p_release": [[round(v, 2) for v in row] for row in prel],
        "h_m": [[round(v, 2) for v in row] for row in hmat],
        "hs_m": [round(v, 2) for v in hs],
        "new_m": [round(v, 2) for v in newsnow],
        "summary": summary,
        "episodes": met["episodes"],
        "demo_days": met["demo_days"],
    }
    path = os.path.join(WEB, "release_calendar.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), "B;", len(secs), "sectors x", len(days), "days")
    top = sorted(summary, key=lambda s: -s["sectors_over"])[:12]
    for s in top:
        print(s["date"], s["sectors_over"], s["max_risk"], s["kind"], s["hn3_m"], s["blow3_h"], s["rain_mm"], s["tmax_c"])
    for dd in met["demo_days"]:
        s = summary[[x["date"] for x in summary].index(dd)]
        print("DEMO", dd, s)


if __name__ == "__main__":
    main()

"""Real winter 2024/25 at Kasprowy Wierch from the IMGW-PIB daily synop archive.

Reads data/raw/kasprowy_2024.zip and data/raw/kasprowy_2025.zip (s_d_650_YYYY.csv, cp1250,
no header, column meaning in IMGW s_d_format.txt) and writes web/data/kasprowy_2024_25.json:
a daily series Oct 2024 - May 2025 plus the largest storm episodes (3-day new snow with
blowing snow), the candidates for the demo mornings.

Status flags: "8" = no measurement (null), "9" = phenomenon did not occur (0).
Source: IMGW-PIB, https://danepubliczne.imgw.pl (attribution "Źródło: IMGW-PIB").

    python tools/real/build_kasprowy.py
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "web" / "data" / "kasprowy_2024_25.json"
START, END = date(2024, 10, 1), date(2025, 5, 31)

# s_d columns (0-based) -> (value index, status index), see s_d_format.txt
COLS = {
    "tmax_c": (5, 6), "tmin_c": (7, 8), "tmean_c": (9, 10),
    "precip_mm": (13, 14), "hs_cm": (16, 17), "rwsn_mm_per_cm": (18, 19),
    "snowfall_h": (24, 25), "blowing_low_h": (38, 39), "blowing_high_h": (40, 41),
    "wind10_h": (44, 45), "wind15_h": (46, 47),
}
PRECIP_TYPE = 15  # ROOP: S snow, W rain


def value(row: list[str], vi: int, si: int) -> float | None:
    v, s = row[vi].strip(), row[si].strip()
    if v:
        return float(v)
    if s == "9":
        return 0.0  # phenomenon did not occur
    return None  # "8": no measurement


def read(zip_name: str, member: str) -> list[list[str]]:
    with zipfile.ZipFile(RAW / zip_name) as z:
        return list(csv.reader(io.StringIO(z.read(member).decode("cp1250"))))


def main() -> None:
    rows = read("kasprowy_2024.zip", "s_d_650_2024.csv") + read("kasprowy_2025.zip", "s_d_650_2025.csv")
    by_date = {date(int(r[2]), int(r[3]), int(r[4])): r for r in rows}

    days, gaps, prev_hs = [], [], None
    d = START - timedelta(days=1)
    if d in by_date:
        prev_hs = value(by_date[d], *COLS["hs_cm"])
    d = START
    while d <= END:
        r = by_date.get(d)
        if r is None:
            gaps.append({"date": d.isoformat(), "what": "brak wiersza w archiwum"})
            days.append({"date": d.isoformat()})
            prev_hs = None
            d += timedelta(days=1)
            continue
        rec = {"date": d.isoformat()}
        for k, (vi, si) in COLS.items():
            rec[k] = value(r, vi, si)
            if rec[k] is None and k in ("hs_cm", "snowfall_h", "blowing_high_h", "precip_mm"):
                gaps.append({"date": d.isoformat(), "what": k})
        rec["precip_type"] = r[PRECIP_TYPE].strip() or None
        hs = rec["hs_cm"]
        rec["new_cm"] = max(0.0, hs - prev_hs) if hs is not None and prev_hs is not None else None
        # SWE estimate: RWSN is a per-centimetre water equivalent (mm per cm of snow)
        rec["swe_mm"] = round(hs * rec["rwsn_mm_per_cm"], 1) if hs and rec["rwsn_mm_per_cm"] else (0.0 if hs == 0 else None)
        rec["blowing_h"] = max(rec["blowing_low_h"] or 0, rec["blowing_high_h"] or 0)
        prev_hs = hs
        days.append(rec)
        d += timedelta(days=1)

    # storm episodes: largest 3-day sum of new snow with blowing snow in the window, non-overlapping
    cands = []
    for i in range(2, len(days)):
        w = days[i - 2 : i + 1]
        if any(x.get("new_cm") is None for x in w):
            continue
        new = sum(x["new_cm"] for x in w)
        blow = sum(x["blowing_h"] for x in w)
        # the rise read at the morning of day D is mostly snow of precipitation day D-1
        pre = days[i - 3 : i] if i >= 3 else w
        if blow > 0 and new > 0:
            cands.append((new, blow, i, sum(x.get("precip_mm") or 0 for x in pre)))
    cands.sort(key=lambda c: (-c[0], -c[1]))
    episodes, used = [], set()
    for new, blow, i, precip in cands:
        if any(abs(i - j) <= 3 for j in used):
            continue
        used.add(i)
        w = days[i - 2 : i + 1]
        peak = max(w, key=lambda x: x["new_cm"])
        episodes.append({
            "start": w[0]["date"], "end": w[-1]["date"],
            "new_cm_3d": round(new), "blowing_h_3d": round(blow, 1),
            "precip_mm_3d": round(precip, 1),
            "hs_before_cm": days[i - 3]["hs_cm"] if i >= 3 else None, "hs_after_cm": w[-1]["hs_cm"],
            "peak_day": peak["date"], "peak_new_cm": round(peak["new_cm"]),
            "tmin_c": min(x["tmin_c"] for x in w if x["tmin_c"] is not None),
        })
        if len(episodes) == 3:
            break
    episodes.sort(key=lambda e: e["start"])
    top = max(episodes, key=lambda e: e["new_cm_3d"])
    # demo mornings inside the top episode: day 1 = morning before the peak night, day 2 = peak morning
    peak = date.fromisoformat(top["peak_day"])
    demo = [(peak - timedelta(days=1)).isoformat(), peak.isoformat()]
    for e in episodes:
        e["label"] = f"{fmt(e['start'])}–{fmt(e['end'])}: +{e['new_cm_3d']} cm, zamieć {round(e['blowing_h_3d'])} h"

    hs_vals = [x["hs_cm"] for x in days if x.get("hs_cm") is not None]
    out = {
        "station": {"name": "Kasprowy Wierch", "code": "349190650", "elevation_m": 1987},
        "source": "IMGW-PIB, dane publiczne, dobowe dane synoptyczne (s_d), https://danepubliczne.imgw.pl",
        "attribution": "Źródło: IMGW-PIB",
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "fields": {
            "hs_cm": "PKSN, wysokość pokrywy śnieżnej, pomiar poranny 06 UTC",
            "new_cm": "dodatni przyrost PKSN względem poprzedniego ranka (przybliżenie świeżego śniegu; osiadanie i wywiewanie go zaniżają)",
            "swe_mm": "PKSN × RWSN (RWSN to równoważnik wodny w mm na cm śniegu)",
            "precip_mm": "SMDB, suma dobowa opadu (doba opadowa od 06 UTC dnia D)", "precip_type": "ROOP: S śnieg, W deszcz",
            "snowfall_h": "SNEG, czas trwania opadu śniegu", "blowing_low_h": "ZMNI, zamieć niska", "blowing_high_h": "ZMWS, zamieć wysoka",
            "blowing_h": "max(ZMNI, ZMWS)", "wind10_h": "FF10, godziny z wiatrem ≥10 m/s", "wind15_h": "FF15, godziny z wiatrem >15 m/s",
            "tmax_c": "TMAX", "tmin_c": "TMIN", "tmean_c": "STD",
        },
        "notes": [
            "Status IMGW 9 (brak zjawiska) zapisany jako 0, status 8 (brak pomiaru) jako null.",
            "Średniej prędkości i kierunku wiatru brak dla zimy 2024/25: plik s_d_t w archiwum kończy się 2024-06-30, a archiwum 2025 go nie zawiera. Jako miarę wiatru podajemy godziny z wiatrem ≥10 i >15 m/s (FF10, FF15). Kierunek wiatru jest tylko w odczycie na żywo.",
            "Przyrost PKSN na ranek dnia D to głównie śnieg z doby opadowej D−1 (np. 12.01.2025: 25,1 mm, 13.01.2025: +20 cm).",
            "Kasprowy Wierch to wywiewana kopuła szczytowa: pokrywa na stacji jest niższa niż w żlebach, gdzie wiatr ją nawiewa.",
        ],
        "gaps": gaps,
        "summary": {"hs_max_cm": max(hs_vals), "new_cm_total": round(sum(x.get("new_cm") or 0 for x in days)),
                    "days_with_blowing_snow": sum(1 for x in days if (x.get("blowing_h") or 0) > 0)},
        "episodes": episodes,
        "demo_days": demo,
        "days": days,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({len(days)} days, {len(gaps)} gaps)")
    for e in episodes:
        print(" ", e["label"], "| HS", e["hs_before_cm"], "->", e["hs_after_cm"], "| opad", e["precip_mm_3d"], "mm")
    print("  demo mornings:", demo)


def fmt(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day}.{d.month:02d}.{d.year}"


if __name__ == "__main__":
    main()

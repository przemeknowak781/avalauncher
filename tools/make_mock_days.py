"""Mock days so the screen works before package B. Replace with tools/build_scenarios.py output.

Writes web/data/mock/days.json in the contract shape plus a temporary `exposure` map
(sector -> nearest trail), which package B replaces with scenario-based trail hits.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data"


def main() -> None:
    sectors = json.loads((DATA / "sectors.json").read_text(encoding="utf-8"))
    trails = json.loads((DATA / "trails.json").read_text(encoding="utf-8"))
    pts = [(t, p) for t in trails for part in t["paths"] for p in part]

    exposure = {}
    for s in sectors:
        c, r = s["centroid"]
        t, p = min(pts, key=lambda tp: (tp[1][0] - c) ** 2 + (tp[1][1] - r) ** 2)
        d = math.hypot(p[0] - c, p[1] - r) * 10
        if d < 400:
            exposure[s["id"]] = {"trail": t["id"], "name": t["name"], "distance_m": round(d)}

    exposed = sorted(exposure, key=lambda k: exposure[k]["distance_m"])
    loaded = {k for k in exposed if next(s for s in sectors if s["id"] == k)["aspect"] in ("NE", "E", "N")}
    loaded = sorted(loaded, key=lambda k: exposure[k]["distance_m"])[:2]
    stale = [k for k in exposed if k not in loaded][:3]
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from pl1992 import to_pl1992
    e, n = to_pl1992(49.2433, 20.0072)  # Murowaniec, flight base
    base = (round((e - 570500) / 10, 1), round((153500 - n) / 10, 1))

    def state(sid, day):
        s = next(x for x in sectors if x["id"] == sid)
        lee = s["aspect"] in ("N", "NE", "E")
        if day == 1:
            return {"hs_m": 1.4, "dhs_m": 0.45 if sid in loaded else 0.12, "wind": 0.8 if sid in loaded else 0.3,
                    "sigma_m": 0.08, "hours_since_measured": 1}
        return {"hs_m": 1.8, "dhs_m": 0.55 if sid in loaded else 0.15, "wind": 0.9 if sid in loaded else 0.5,
                "sigma_m": 0.45 if sid in stale else 0.25, "hours_since_measured": 26}

    flight1 = [list(base)] + [next(s for s in sectors if s["id"] == k)["centroid"] for k in exposed[:8]]
    days = [
        {"id": "d1", "label": "Dzień 1, 7:00", "status": "Przelot wykonany",
         "flight": {"flown": True, "path": flight1},
         "weather": {"new_cm": 20, "wind_dir": "SW", "wind_ms": 12, "hours_since_flight": 1},
         "sectors": {sid: state(sid, 1) for sid in exposure}},
        {"id": "d2", "label": "Dzień 2, 7:00", "status": "Śnieżyca, przelot odwołany",
         "flight": {"flown": False, "path": []},
         "weather": {"new_cm": 40, "wind_dir": "W", "wind_ms": 18, "hours_since_flight": 26},
         "sectors": {sid: state(sid, 2) for sid in exposure}},
    ]
    out = DATA / "mock"
    out.mkdir(exist_ok=True)
    (out / "days.json").write_text(json.dumps({"base": list(base), "exposure": exposure, "days": days},
                                              ensure_ascii=False), encoding="utf-8")
    print(f"{len(exposure)} exposed sectors, loaded {loaded}, stale {stale}")


if __name__ == "__main__":
    main()

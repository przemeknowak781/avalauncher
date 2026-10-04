"""SYNTHETIC mornings without a 6:00 flight (numpy only), shape of tools/proof.mjs: k = 1..3 days
since the last pass, snowfall and wind per day, wind loading by aspect, unknown catchment. The
hidden truth is drawn from the belief N(h, sigma) itself, the reading is truth + sensor error.
Usage: python tools/rl/gen.py <meta.json> <out.json> <n> <seed> [days.json -> append demo day 2]"""
import json
import sys

import numpy as np

SENSOR, SPH, SNS, SETTLE = 0.08, 0.003, 0.4, 0.85
DIRS = ["W", "W", "SW", "SW", "NW", "NW", "S", "N", "E", "SE", "NE"]
DEG = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}


def sigma_after(hours, new):
    return np.sqrt(SENSOR**2 + (SPH * hours) ** 2 + (SNS * new) ** 2)


def load_factor(aspect, frm, ms):
    c = np.cos(np.deg2rad(aspect - (frm + 180.0) % 360.0))
    return np.clip(1.0 + 1.1 * np.minimum(ms, 20.0) / 20.0 * c, 0.15, 2.2)


def generate(aspect_deg, n, seed):
    R = np.random.default_rng(seed)
    L = len(aspect_deg)
    k = R.choice([1, 2, 3], size=n, p=[0.6, 0.3, 0.1])
    hours = 24 * k + 1
    F = np.exp(0.45 * R.standard_normal((n, L)))
    old = np.clip(0.08 * np.exp(1.0 * R.standard_normal((n, L))), 0, 1.4) * SETTLE ** k[:, None]
    since, fresh, cum = np.zeros((n, L)), np.zeros((n, L)), np.zeros(n)
    for j in range(3):
        active, last = j < k, j == k - 1
        u = R.random(n)
        hn = np.where(u < 0.6, 0.0, np.where(u < 0.9, 0.01 + 0.05 * R.random(n), 0.06 + 0.1 * R.random(n)))
        hn = np.where(last, 0.03 + 0.3 * R.random(n) ** 1.5, hn)  # the night before the cancelled flight
        frm = np.array([DEG[d] for d in R.choice(DIRS, size=n)], dtype=np.float64)
        ms = np.round(2 + 22 * R.random(n) ** 1.3)
        ms = np.where(last, np.maximum(ms, 8 + 16 * R.random(n)), ms)
        cum = cum + hn * active
        drift = 0.01 * np.maximum(0, ms - 8) * np.minimum(1, cum / 0.2)
        lf = load_factor(aspect_deg[None, :], frm[:, None], ms[:, None])
        fc = (hn[:, None] + 2 * drift[:, None] * np.maximum(0, lf - 1)) * lf * F * active[:, None]
        since += fc
        fresh += fc * np.where(active, SETTLE ** np.maximum(0, k - 1 - j), 0)[:, None]
    h = old + fresh
    s = sigma_after(hours[:, None], since)
    truth = np.maximum(0, h + s * R.standard_normal((n, L)))
    reading = np.maximum(0, truth + SENSOR * R.standard_normal((n, L)))
    return dict(h=h, s=s, truth=truth, reading=reading, hours=hours)


if __name__ == "__main__":
    meta = json.load(open(sys.argv[1], encoding="utf8"))
    n, seed = int(sys.argv[3]), int(sys.argv[4])
    m = generate(np.array([DEG[a] for a in meta["aspect"]], dtype=np.float64), n, seed)
    out = {k: np.round(v, 4).tolist() for k, v in m.items()}
    out["hours"] = m["hours"].tolist()
    if len(sys.argv) > 5:  # demo morning: days.json day 2 (truth = the drone reading)
        d2 = json.load(open(sys.argv[5], encoding="utf8"))["days"][1]["sectors"]
        g = lambda key: [d2[i][key] for i in meta["ids"]]
        out["h"].append(g("slab_m"))
        out["s"].append(g("sigma_m"))
        out["reading"].append(g("drone_reading_m"))
        out["truth"].append(g("drone_reading_m"))
        out["hours"].append(d2[meta["ids"][0]]["hours_since_measured"])
    out.update(ids=meta["ids"], seed=seed)
    json.dump(out, open(sys.argv[2], "w"))

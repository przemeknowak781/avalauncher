"""rl_result.json (train.py) -> web/data/rl.json, filmy/rl/krzywa_uczenia.png, filmy/rl/trasy.png.
Usage: python tools/rl/plots.py <rl_result.json>"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib import patheffects as pe  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA, OUT = ROOT / "web" / "data", ROOT / "filmy" / "rl"
OUT.mkdir(parents=True, exist_ok=True)
PAPER, INK, RL, FIX, VOI = "#f4efe4", "#1d1b17", "#d6007e", "#e8590c", "#5b3fd1"
font_manager.fontManager.addfont(str(ROOT / "web" / "vendor" / "fonts" / "Archivo-var.ttf"))
plt.rcParams.update({"font.family": "Archivo", "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.edgecolor": INK, "figure.facecolor": PAPER, "axes.facecolor": PAPER})

R = json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
proof = json.loads((DATA / "proof.json").read_text(encoding="utf8"))
M = R["metrics"]
rl, voi, fx = M["rl"], M["greedy_voi"], M["fixed_route"]
rel = (rl["uncertainty_drop_pct"] - voi["uncertainty_drop_pct"]) / voi["uncertainty_drop_pct"] * 100
if rel > 2:
    verdict = f"RL wygrywa z planem VOI o {rel:.0f}% spadku niepewności przy tym samym budżecie 20 min."
elif rel >= -2:
    thr = (rl["threats_caught"] - voi["threats_caught"]) / max(1, voi["threats_caught"]) * 100
    verdict = (f"RL dorównuje planowi VOI ({rel:+.1f}% spadku niepewności, {thr:+.0f}% wykrytych zagrożeń); "
               "zgodnie z docs/07 zostajemy przy prostszym planerze.")
else:
    verdict = f"RL zostaje {-rel:.0f}% za planem VOI; zgodnie z docs/07 zostajemy przy prostszym planerze."
pick = lambda m: {k: m[k] for k in ("uncertainty_drop_pct", "unknowns_resolved", "threats_caught", "reward", "sectors_per_flight")}
fixed_ids = proof.get("flight_test", {}).get("fixed_route") or R["day2"]["fixed_route"]
assert sorted(fixed_ids) == sorted(R["day2"]["fixed_route"]), "fixed patrol differs from proof.mjs"
curve = R["curve"]


def fixed_minutes(ids):  # the patrol in proof.mjs order (same set as train.py, so same metrics)
    import math
    sec = {x["id"]: x["centroid"] for x in json.loads((DATA / "sectors.json").read_text(encoding="utf8"))}
    base = json.loads((DATA / "days.json").read_text(encoding="utf8"))["base"]
    pos, m = base, 0.0
    for i in ids:
        m += math.dist(pos, sec[i]) / 60 + 1.5
        pos = sec[i]
    return m + math.dist(pos, base) / 60


step = max(1, len(curve) // 120)
out = dict(
    algo=R["algo"], env_episodes_trained=R["env_episodes_trained"], train_minutes=R["train_minutes"], gpu=R["gpu"],
    eval_mornings=R["eval_mornings"], train_mornings=R["train_mornings"], budget_min=20, sectors=R["sectors"],
    metrics=dict(rl=pick(rl), greedy_voi=pick(voi), fixed_route=pick(fx)),
    unknowns_before=voi["unknowns_before"], threats_catchable=voi["threats_catchable"],
    rl_vs_voi_pct=round(rel, 1), verdict=verdict,
    definitions=dict(
        uncertainty_drop_pct="spadek niepewności decyzji silnika (engine.uncertainty) po locie, % sumy przed lotem",
        unknowns_resolved="stoki „nie wiem” przed lotem, które po pomiarze mają odpowiedź",
        threats_caught="stoki naprawdę groźne (ukryta prawda), które lot zamienił w „zagrożenie”",
        reward="nagroda RL na lot: spadek niepewności × waga szlaku + 0,5 × waga za wykryte zagrożenie",
        greedy_voi="engine.planFlight (wartość informacji, zachłannie), ta sama ocena",
        fixed_route="stały patrol z tools/proof.mjs: korytarz Murowaniec – Czarny Staw – Zawrat, potem najbliższe stoki",
    ),
    day2=dict(rl=R["day2"]["rl"], greedy_voi=R["day2"]["greedy_voi"], fixed_route=fixed_ids,
              minutes=dict(rl=R["day2"]["rl_min"], greedy_voi=R["day2"]["voi_min"], fixed_route=round(fixed_minutes(fixed_ids), 1)),
              metrics={k: pick(v) for k, v in R["day2"]["metrics"].items()}),
    curve=[dict(episodes=c["episodes"], train=c["train_reward"], test=c["eval_reward"]) for c in curve[::step]],
    note="dane syntetyczne, test logiki",
)
(DATA / "rl.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
print(json.dumps({k: out[k] for k in ("metrics", "verdict", "env_episodes_trained", "gpu", "train_minutes")}, ensure_ascii=False, indent=1))

# ---------- learning curve ----------
fig, ax = plt.subplots(figsize=(12, 6.75), dpi=160)
ep = [c["episodes"] / 1e6 for c in curve]
ax.plot(ep, [c["train_reward"] for c in curve], color=RL, alpha=0.25, lw=1.2, label="RL, trening (losowanie trasy)")
ax.plot(ep, [c["eval_reward"] for c in curve], color=RL, lw=2.6, label="RL, poranki testowe (najlepsza trasa)")
ax.axhline(voi["reward"], color=VOI, lw=2.2, ls="--", label=f"Plan VOI silnika: {voi['reward']:.1f}")
ax.axhline(fx["reward"], color=FIX, lw=2.2, ls="--", label=f"Stały patrol: {fx['reward']:.1f}")
ax.set_xlabel("Epizody treningowe (mln porannych lotów)", fontsize=13)
ax.set_ylabel("Nagroda na lot 20 min", fontsize=13)
ax.set_title("Czego uczy się dron: gdzie polecieć, żeby się dowiedzieć", fontsize=18, fontweight="bold", loc="left", pad=28)
ax.text(0, 1.02, f"{R['eval_mornings']} poranków testowych, budżet 20 min z powrotem do bazy · {R['gpu']} · dane syntetyczne, test logiki",
        transform=ax.transAxes, fontsize=10.5, alpha=0.75)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.set_ylim(0, max(voi["reward"], max(c["eval_reward"] for c in curve)) * 1.18)
ax.legend(frameon=False, fontsize=11.5, loc="lower right")
ax.text(0.99, 0.30, verdict.replace("; ", ";\n"), transform=ax.transAxes, ha="right", fontsize=12, fontweight="bold", color=INK, wrap=True)
fig.tight_layout()
fig.savefig(OUT / "krzywa_uczenia.png", facecolor=PAPER)
plt.close(fig)

# ---------- one morning on the map ----------
sectors = {s["id"]: s for s in json.loads((DATA / "sectors.json").read_text(encoding="utf8"))}
trails = json.loads((DATA / "trails.json").read_text(encoding="utf8"))
base = json.loads((DATA / "days.json").read_text(encoding="utf8"))["base"]
img = Image.open(DATA / "map.png").convert("RGB")
S = img.size[0] / 400.0  # px per cell
d2 = out["day2"]
kind0 = R["day2"]["kind0"]
routes = [("fixed_route", FIX, "Stały patrol", 0), ("greedy_voi", VOI, "Plan VOI silnika", 1), ("rl", RL, "Polityka RL", 2)]
pts = [base] + [sectors[i]["centroid"] for k, *_ in routes for i in d2[k]] + [sectors[i]["centroid"] for i, v in kind0.items() if v]
xs, ys = [p[0] for p in pts], [p[1] for p in pts]
pad = 28
x0, x1, y0, y1 = max(0, min(xs) - pad), min(400, max(xs) + pad), max(0, min(ys) - pad), min(400, max(ys) + pad)
w, h = x1 - x0, y1 - y0
H = 11.76 * h / w
FH = H + 1.05
fig = plt.figure(figsize=(12, FH), dpi=160)
ax = fig.add_axes([0.01, 0.12 / FH, 0.98, H / FH])
ax.imshow(img, extent=(0, 400, 400, 0))
for t in trails:
    for path in t["paths"]:
        ax.plot([p[0] for p in path], [p[1] for p in path], color=INK, lw=1.0, alpha=0.45, ls=(0, (3, 2)))
offs = {0: (-1.2, -1.2), 1: (0, 0), 2: (1.2, 1.2)}
for key, col, label, z in routes:
    ids = d2[key]
    pp = [base] + [sectors[i]["centroid"] for i in ids] + [base]
    dx, dy = offs[z]
    m = d2["metrics"][key]
    ax.plot([p[0] + dx for p in pp], [p[1] + dy for p in pp], color=col, lw=3.2, alpha=0.95, zorder=3 + z,
            solid_capstyle="round", path_effects=[pe.Stroke(linewidth=5.2, foreground=PAPER), pe.Normal()],
            label=f"{label}: {len(ids)} stoków, {d2['minutes'][key]:.0f} min, spadek niepewności {m['uncertainty_drop_pct']:.0f}%")
    ax.scatter([sectors[i]["centroid"][0] + dx for i in ids], [sectors[i]["centroid"][1] + dy for i in ids], s=38, color=col,
               edgecolor=PAPER, lw=1.2, zorder=6 + z)
for sid, v in kind0.items():
    if not v:
        continue
    c = sectors[sid]["centroid"]
    ax.scatter([c[0]], [c[1]], s=520, facecolor="none", edgecolor=INK if v == 1 else "#b00020", lw=2.2, zorder=9,
               ls="--" if v == 1 else "-")
    ax.text(c[0] + 5, c[1] - 5, ("? " if v == 1 else "! ") + sectors[sid]["name"], fontsize=9.5, fontweight="bold", zorder=10,
            color=INK if v == 1 else "#b00020", path_effects=[pe.withStroke(linewidth=3, foreground=PAPER)])
ax.scatter([base[0]], [base[1]], s=180, marker="s", color=INK, zorder=11)
ax.text(base[0] + 5, base[1] + 9, "Murowaniec (baza)", fontsize=10.5, fontweight="bold", zorder=11,
        path_effects=[pe.withStroke(linewidth=3, foreground=PAPER)])
ax.set_xlim(x0, x1)
ax.set_ylim(y1, y0)
ax.axis("off")
ax.legend(loc="lower left", fontsize=10.5, frameon=True, facecolor=PAPER, edgecolor=INK, framealpha=0.92)
fig.text(0.02, 1 - 0.18 / FH, "Dzień 2, 7:00: trzy plany lotu, 20 min z powrotem do bazy", fontsize=18, fontweight="bold", va="top")
fig.text(0.02, 1 - 0.58 / FH, "Kółko przerywane: stok „nie wiem” przed lotem · czerwone: „zagrożenie” · dane syntetyczne, test logiki · "
         "mapa: GUGiK NMT, szlaki © OpenStreetMap", fontsize=10.5, va="top", alpha=0.8)
fig.savefig(OUT / "trasy.png", facecolor=PAPER)
plt.close(fig)
print("wrote", DATA / "rl.json", OUT / "krzywa_uczenia.png", OUT / "trasy.png")

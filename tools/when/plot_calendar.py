"""Kalendarz sezonu 2024/25: ryzyko (P_uwolnienia x skutek) per sektor i dzień -> filmy/kiedy/kalendarz.png."""
import json
import os
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONT = os.path.join(ROOT, "web", "vendor", "fonts", "Archivo-var.ttf")
font_manager.fontManager.addfont(FONT)
FAM = font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams.update({"font.family": FAM, "font.size": 10})

PAPER, INK, MUTED = "#f4efe4", "#1d1b17", "#7a7367"
CMAP = LinearSegmentedColormap.from_list("risk", ["#ebe3d2", "#f3c9a0", "#e8590c", "#5a1a00"], N=256)
ORDER = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
MONTHS = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]

c = json.load(open(os.path.join(ROOT, "web", "data", "release_calendar.json"), encoding="utf-8"))
days = [date.fromisoformat(d) for d in c["days"]]
R = np.array(c["risk"])
asp = c["sector_aspect"]
# tylko sektory, których biblioteka w ogóle sięga szlaku
keep = [i for i in range(len(asp)) if R[i].max() > 0]
keep.sort(key=lambda i: (ORDER.index(asp[i]), -R[i].sum()))
M = R[keep]
n, T = M.shape
THR = str(c["threshold"]).replace(".", ",")

fig = plt.figure(figsize=(16, 9), dpi=150, facecolor=PAPER)
gs = fig.add_gridspec(3, 1, height_ratios=[1.25, 5.2, 0.9], hspace=0.08, left=0.075, right=0.975, top=0.86, bottom=0.12)
ax0, ax1, ax2 = (fig.add_subplot(gs[k]) for k in range(3))
for ax in (ax0, ax1, ax2):
    ax.set_facecolor(PAPER)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlim(-0.5, T - 0.5)
    ax.tick_params(colors=INK, length=0)

x = np.arange(T)
idx = {d: k for k, d in enumerate(c["days"])}

# epizody burzowe i dwa poranki demo
for e in c["episodes"]:
    a, b = idx.get(e["start"]), idx.get(e["end"])
    if a is None or b is None:
        continue
    for ax in (ax0, ax1, ax2):
        ax.axvspan(a - 0.5, b + 0.5, color=INK, alpha=0.06, lw=0, zorder=0)
    ax0.text((a + b) / 2, 1.16, f"+{e['new_cm_3d']} cm\nzamieć {e['blowing_h_3d']:.0f} h", ha="center", va="bottom",
             fontsize=8.5, color=INK, linespacing=1.1)

# pas pogody: pokrywa i świeży śnieg (IMGW, prawdziwe)
hs = np.array(c["hs_m"])
ax0.fill_between(x, 0, hs, step="mid", color="#c9c0ae", lw=0, zorder=1)
ax0.plot(x, hs, drawstyle="steps-mid", color=INK, lw=0.9, zorder=2)
ax0.bar(x, np.array(c["new_m"]), width=0.9, color="#2f5d8a", zorder=3)
ax0.set_ylim(0, 1.15)
ax0.set_yticks([0, 0.5, 1.0])
ax0.set_yticklabels(["0", "50", "100 cm"], fontsize=8.5, color=MUTED)
ax0.set_xticks([])
ax0.text(0.0, 0.98, "pokrywa (szare)  ·  świeży śnieg na ranek (niebieskie)", transform=ax0.transAxes,
         fontsize=8.5, color=MUTED, va="top")

# mapa ryzyka
im = ax1.imshow(M, aspect="auto", cmap=CMAP, vmin=0, vmax=1, interpolation="nearest", zorder=1,
                extent=(-0.5, T - 0.5, n - 0.5, -0.5))
prev = None
for r, i in enumerate(keep):
    if asp[i] != prev:
        if prev is not None:
            ax1.axhline(r - 0.5, color=PAPER, lw=2.2, zorder=3)
        grp = [rr for rr, ii in enumerate(keep) if asp[ii] == asp[i]]
        ax1.text(-2.5, (grp[0] + grp[-1]) / 2, asp[i], ha="right", va="center", fontsize=11, color=INK, weight="bold")
        prev = asp[i]
ax1.set_yticks([])
ax1.set_xticks([])
ax1.text(-11, n / 2, "sektory wg wystawy", rotation=90, ha="center", va="center", fontsize=9, color=MUTED)

# podsumowanie masywu
cnt = np.array([s["sectors_over"] for s in c["summary"]])
ax2.bar(x, cnt, width=0.9, color="#e8590c")
ax2.set_ylim(0, max(cnt.max(), 1) * 1.15)
ax2.set_yticks([0, int(cnt.max())])
ax2.tick_params(axis="y", labelsize=8.5, labelcolor=MUTED)
ax2.text(0.0, 0.95, f"sektory z ryzykiem ≥ {THR}", transform=ax2.transAxes, fontsize=8.5, color=MUTED, va="top")
ticks = [k for k, d in enumerate(days) if d.day == 1]
ax2.set_xticks(ticks)
ax2.set_xticklabels([f"{MONTHS[days[k].month - 1]} {days[k].year}" if days[k].month in (1, 11) else MONTHS[days[k].month - 1]
                     for k in ticks], fontsize=10, color=INK)
for ax in (ax0, ax1, ax2):
    for k in ticks:
        ax.axvline(k - 0.5, color=PAPER if ax is ax1 else "#d8cfbd", lw=1.0, zorder=2)

# poranki demo
for j, d in enumerate(c["demo_days"]):
    k = idx[d]
    for ax in (ax0, ax1, ax2):
        ax.axvline(k, color=INK, lw=0.9, ls=(0, (2, 2)), zorder=4)
    s = c["summary"][k]
    ax1.annotate(f"{date.fromisoformat(d).day}.01 rano: {s['sectors_over']} sektorów ≥ {THR}",
                 xy=(k, n * (0.08 + 0.1 * j)), xytext=(k + 9, n * (0.08 + 0.1 * j)), fontsize=9.5, color=INK,
                 va="center", arrowprops=dict(arrowstyle="-", color=INK, lw=0.8),
                 bbox=dict(boxstyle="round,pad=0.25", fc=PAPER, ec="none", alpha=0.92), zorder=6)

# tytuł, legenda, stopka
fig.text(0.075, 0.95, "Kiedy stoki mogą zagrozić szlakom: zima 2024/25 nad Halą Gąsienicową", fontsize=20, color=INK, weight="bold")
fig.text(0.075, 0.915, "Ryzyko = P(uwolnienia płyty, z prawdziwej pogody IMGW) × udział symulacji AvaFrame sięgających szlaku z ≥ 0,5 m śniegu. "
         "Heurystyka, nie prognoza; docelowo SNOWPACK.", fontsize=10.5, color=MUTED)
cax = fig.add_axes([0.80, 0.045, 0.175, 0.014])
cb = fig.colorbar(im, cax=cax, orientation="horizontal")
cb.outline.set_visible(False)
cb.set_ticks([0, 0.5, 1])
cb.set_ticklabels(["0", "0,5", "1"])
cax.tick_params(labelsize=8.5, colors=INK, length=0)
cax.set_title("ryzyko", fontsize=8.5, color=MUTED, loc="left", pad=3)
fig.text(0.075, 0.035, "Pogoda: IMGW-PIB Kasprowy Wierch (prawdziwe dane) · Skutek: biblioteka AvaFrame (1566 symulacji) · "
         "Model uwolnienia: heurystyka PoC", fontsize=9.5, color=INK)
fig.text(0.075, 0.012, "Kierunek wiatru nieznany dla tej zimy: nawianie liczone dla założonego wiatru W–SW. "
         f"Szare pasy: epizody burzowe. Przerywane linie: poranki 12 i 13.01.2025. {n} z {len(asp)} sektorów (bez tych, których żadna symulacja nie sięga szlaku).", fontsize=8, color=MUTED)

out = os.path.join(ROOT, "filmy", "kiedy", "kalendarz.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, facecolor=PAPER)
print("wrote", out, f"{n} sektorów x {T} dni")

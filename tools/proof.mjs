// Proof on 30 SYNTHETIC mornings (test of the logic, not a validation).
// Hidden truth: the true slab thickness per sector, and a "real world" that differs from the
// library the engine reads: each morning the true avalanche behaves like ONE friction calibration
// (unknown to the engine, which pools all three) and the effective slab is off by a systematic
// ±15–25 % plus per-sector noise. The engine keeps its own belief (drone reading or forecast + σ).
//   1. Mornings as they happened (6:00 flight when the weather allowed): Avalauncher (engine.assess)
//      vs baseline "3-day new snow >= 30 cm flags every slope above a trail": misses and false alarms.
//   2. Every morning as if the 6:00 flight was cancelled: a 20-min flight later, the value-of-
//      information plan vs a fixed patrol along the main corridor from Murowaniec (blue trail to
//      Czarny Staw and Zawrat, then the nearest slopes): unknowns resolved, threatening slopes
//      caught as "zagrozenie", decision uncertainty removed.
// Usage: node tools/proof.mjs  -> web/data/proof.json
import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { loadCtx, rng, loadFactor, DATA } from "./synth.mjs";
import {
  assess, planFlight, applyFlight, uncertainty, routeMinutes, sigmaAfter, library, shareAt, hitSegments, releaseAt,
  SENSOR_SIGMA_M, HIT_SHARE,
} from "../web/engine.js";

const MORNINGS = 30, SPIN = 3, BUDGET = 20, HN3_THRESHOLD_M = 0.30, SETTLE = 0.85;
const CORRIDOR = ["T26", "T27", "T28", "T29"]; // Murowaniec – Czarny Staw – Zmarzły Staw – Zawrat
const { sectors, trails, scenarios, cells, base } = loadCtx();
const ctx = { scenarios, cells, trails, base };
const lib = library(ctx);
const rel = sectors.filter((s) => lib.get(s.id)?.anyHit);
const byId = Object.fromEntries(sectors.map((s) => [s.id, s]));
const R = rng(20261004);

// ---- "real world" response: one friction calibration, interpolated over thickness ----
const FRICTIONS = scenarios.frictions ?? [...new Set(scenarios.runs.map((r) => r.frict))];
function trueShare(id, frict, x) {
  const L = lib.get(id).levels.map((l) => {
    const rs = l.runs.filter((r) => r.frict === frict);
    return { th: l.th, reach: rs.length ? rs.filter((r) => hitSegments(r).length).length / rs.length : null };
  }).filter((l) => l.reach != null);
  if (!L.length) return 0;
  let reach = L[L.length - 1].reach;
  if (x <= L[0].th) reach = L[0].reach;
  else for (let i = 1; i < L.length; i++) if (x < L[i].th) {
    const t = (x - L[i - 1].th) / (L[i].th - L[i - 1].th);
    reach = L[i - 1].reach + t * (L[i].reach - L[i - 1].reach);
    break;
  }
  return releaseAt(x) * reach;
}

// ---- winter: real IMGW-PIB Kasprowy Wierch days (new snow, blowing-snow hours) when the file
// exists, else synthetic; wind direction is always assumed (not in the IMGW daily archive) ----
const DIRS = ["W", "W", "SW", "SW", "NW", "NW", "S", "N", "E", "SE", "NE"];
const KFILE = join(DATA, "kasprowy_2024_25.json");
const K = existsSync(KFILE) ? JSON.parse(readFileSync(KFILE, "utf8")) : null;
const START = "2024-12-20"; // 33 real days around the January 2025 storms
const realDays = K ? K.days.slice(Math.max(0, K.days.findIndex((d) => d.date === START))).slice(0, MORNINGS + SPIN) : null;
const days = [];
for (let d = 0; d < MORNINGS + SPIN; d++) {
  const u = R();
  const k = realDays?.[d];
  const hn = k ? (k.new_cm ?? 0) / 100 : u < 0.5 ? 0 : u < 0.75 ? 0.02 + 0.13 * R() : u < 0.93 ? 0.15 + 0.2 * R() : 0.35 + 0.25 * R();
  const from = DIRS[Math.floor(R() * DIRS.length)];
  const ms = k ? Math.min(20, 8 + 0.4 * (k.blowing_h ?? 0)) : Math.round(2 + 22 * R() ** 1.3);
  const bias = (R() < 0.5 ? -1 : 1) * (0.15 + 0.1 * R()); // systematic model error, unknown to the engine
  const frict = FRICTIONS[Math.floor(R() * FRICTIONS.length)];
  days.push({ hn, from, ms, bias, frict, date: k?.date, flown: !(ms > 14 || hn > 0.2) });
}
const F = Object.fromEntries(rel.map((s) => [s.id, Math.exp(0.25 * R.gauss())])); // catchment, known
// Wind also drifts loose snow without snowfall (lee slopes only): the 3-day sum cannot see it.
const drift = days.map((w, d) => 0.01 * Math.max(0, w.ms - 8) * Math.min(1, days.slice(Math.max(0, d - 4), d + 1).reduce((a, x) => a + x.hn, 0) / 0.2));
const fc = {}, tr = {};
for (const s of rel) {
  fc[s.id] = days.map((w, d) => {
    const l = loadFactor(s.aspect, w.from, w.ms);
    return (w.hn + 2 * drift[d] * Math.max(0, l - 1)) * l * F[s.id];
  });
  tr[s.id] = fc[s.id].map((x) => x * Math.exp(0.3 * R.gauss()));
}
const win3 = (arr, d, from = 0) => arr.slice(Math.max(from, d - 2), d + 1).reduce((a, x, k, A) => a + x * SETTLE ** (A.length - 1 - k), 0);
const truthSlab = Object.fromEntries(rel.map((s) => [s.id, days.map((_, d) => win3(tr[s.id], d))]));
const reading = Object.fromEntries(rel.map((s) => [s.id, days.map((_, d) => Math.max(0, truthSlab[s.id][d] + 0.5 * SENSOR_SIGMA_M * R.gauss()))]));
const noise = Object.fromEntries(rel.map((s) => [s.id, days.map(() => Math.exp(0.1 * R.gauss()))]));
const threat = (id, d) => trueShare(id, days[d].frict, truthSlab[id][d] * (1 + days[d].bias) * noise[id][d]) >= HIT_SHARE;
const threatNoError = (id, d) => lib.get(id) && shareAtPooled(id, truthSlab[id][d]) >= HIT_SHARE;
const shareAtPooled = (id, x) => shareAt(lib.get(id), x);

// Engine state on morning d, knowing only the last flight `L` (reading) and the forecast since then.
function stateOn(d, L, flownNow) {
  const hours = flownNow ? 1 : 24 * (d - L) + 1;
  const st = {};
  for (const s of rel) {
    const id = s.id;
    const since = fc[id].slice(L + 1, d + 1).reduce((a, x) => a + x, 0);
    const all = win3(fc[id], L), still = win3(fc[id], L, d - 2); // share of the old reading still inside the 3-day window
    const oldPart = all > 1e-9 ? reading[id][L] * SETTLE ** (d - L) * (still / all) : 0;
    const est = flownNow ? reading[id][d] : oldPart + win3(fc[id], d, L + 1);
    st[id] = {
      slab_m: est, sigma_m: flownNow ? sigmaAfter(1, 0) : sigmaAfter(hours, since),
      hours_since_measured: hours, dhs_m: since, wind: 0, drone_reading_m: reading[id][d],
    };
  }
  const newCm = Math.round(100 * days.slice(L + 1, d + 1).reduce((a, x) => a + x.hn, 0));
  return { weather: { new_cm: newCm }, sectors: st };
}

// ---- fixed patrol: slopes along the main corridor in trail order, then the nearest ones ----
const corridor = CORRIDOR.flatMap((id) => trails.find((t) => t.id === id)?.paths.flat() ?? []);
const along = (c) => {
  let bi = 0, bd = Infinity;
  corridor.forEach((p, i) => { const d = Math.hypot(p[0] - c[0], p[1] - c[1]); if (d < bd) { bd = d; bi = i; } });
  return { i: bi, d: bd * 10 };
};
const onCorridor = rel.map((s) => ({ id: s.id, ...along(s.centroid) })).filter((x) => x.d <= 800).sort((a, b) => a.i - b.i).map((x) => x.id);
const FIXED = [];
for (const id of onCorridor) if (routeMinutes([...FIXED, id], sectors, ctx) <= BUDGET) FIXED.push(id);
for (;;) { // keep patrolling to the nearest slope from the last one while the budget allows
  const last = FIXED.length ? byId[FIXED.at(-1)].centroid : base;
  const next = rel.filter((s) => !FIXED.includes(s.id) && routeMinutes([...FIXED, s.id], sectors, ctx) <= BUDGET)
    .sort((a, b) => Math.hypot(a.centroid[0] - last[0], a.centroid[1] - last[1]) - Math.hypot(b.centroid[0] - last[0], b.centroid[1] - last[1]))[0];
  if (!next) break;
  FIXED.push(next.id);
}

// ---- 1. mornings as they happened ----
const r1 = { misses: { avalauncher: 0, baseline_3d: 0 }, false_alarms: { avalauncher: 0, baseline_3d: 0 }, unknown: 0, threatening: 0, n: 0, cancelled: 0,
  unknownFlown: 0, unknownStale: 0, unknownNotThreat: 0, flipped: 0 };
let last = -1;
for (let d = 0; d < days.length; d++) {
  if (days[d].flown) last = d;
  if (d < SPIN) continue;
  if (!days[d].flown) r1.cancelled++;
  const day = stateOn(d, last, days[d].flown);
  const kind = Object.fromEntries(assess(day, rel, ctx).map((f) => [f.sector, f.kind]));
  const hn3 = days.slice(d - 2, d + 1).reduce((a, x) => a + x.hn, 0);
  for (const s of rel) {
    const t = threat(s.id, d), b = hn3 >= HN3_THRESHOLD_M;
    r1.n++; r1.threatening += t; r1.unknown += kind[s.id] === "nie_wiem";
    if (kind[s.id] === "nie_wiem") {
      if (days[d].flown) r1.unknownFlown++; else r1.unknownStale++;
      if (!t) r1.unknownNotThreat++;
    }
    if (t !== threatNoError(s.id, d)) r1.flipped++;
    if (t && !kind[s.id]) r1.misses.avalauncher++;
    if (!t && kind[s.id] === "zagrozenie") r1.false_alarms.avalauncher++;
    if (t && !b) r1.misses.baseline_3d++;
    if (!t && b) r1.false_alarms.baseline_3d++;
  }
}

// ---- 2. every morning as if the 6:00 flight was cancelled ----
const r2 = { mornings: 0, unknown: 0, threatening: 0, u0: 0,
  plan: { resolved: 0, caught: 0, du: 0, sectors: 0 }, fixed: { resolved: 0, caught: 0, du: 0, sectors: 0 } };
last = -1;
for (let d = 0; d < days.length; d++) {
  if (d >= SPIN && last >= 0) {
    const day = stateOn(d, last, false);
    const flags = assess(day, rel, ctx);
    const unknown = flags.filter((f) => f.kind === "nie_wiem").map((f) => f.sector);
    const threatening = rel.filter((s) => threat(s.id, d)).map((s) => s.id);
    const u0 = uncertainty(day, rel, ctx);
    r2.mornings++; r2.unknown += unknown.length; r2.threatening += threatening.length; r2.u0 += u0;
    const plan = planFlight(day, rel, flags, BUDGET, ctx).route;
    for (const [key, route] of [["plan", plan], ["fixed", FIXED]]) {
      const after = applyFlight(day, route);
      const kind = Object.fromEntries(assess(after, rel, ctx).map((f) => [f.sector, f.kind]));
      r2[key].resolved += unknown.filter((id) => kind[id] !== "nie_wiem").length;
      r2[key].caught += threatening.filter((id) => kind[id] === "zagrozenie").length;
      r2[key].du += u0 - uncertainty(after, rel, ctx);
      r2[key].sectors += route.length;
    }
  }
  if (days[d].flown) last = d;
}

const pct = (x, n) => (n > 0 ? Math.round((100 * x) / n) : 0);
const proof = {
  mornings: MORNINGS,
  weather_source: realDays ? `IMGW-PIB Kasprowy Wierch, ${days[SPIN].date} – ${days.at(-1).date} (kierunek wiatru założony)` : "syntetyczna",
  slopes: rel.length,
  sector_mornings: r1.n,
  threatening: r1.threatening,
  flights_cancelled: r1.cancelled,
  misses: r1.misses,
  false_alarms: r1.false_alarms,
  unknown_flags: r1.unknown,
  unknown_split: { drone_flew: r1.unknownFlown, flight_cancelled: r1.unknownStale, on_not_threatening: r1.unknownNotThreat },
  model_error_flips: r1.flipped,
  model_error_flips_note: "ile razy błąd modelu zmienia prawdę (zagraża / nie zagraża) względem biblioteki",
  flight_test: {
    mornings: r2.mornings, budget_min: BUDGET,
    unknown_before: r2.unknown, threatening: r2.threatening,
    unknowns_resolved: { plan: r2.plan.resolved, fixed_route: r2.fixed.resolved },
    threatening_flagged_after: { plan: r2.plan.caught, fixed_route: r2.fixed.caught },
    slopes_measured: { plan: r2.plan.sectors, fixed_route: r2.fixed.sectors },
    fixed_route: FIXED,
  },
  unknowns_resolved: { plan: r2.plan.resolved, fixed_route: r2.fixed.resolved },
  uncertainty_drop: { plan: pct(r2.plan.du, r2.u0), fixed_route: pct(r2.fixed.du, r2.u0), unit: "% niepewności decyzji po przelocie 20 min" },
  model_error: "prawda: jedna kalibracja tarcia na poranek i błąd grubości ±15–25% plus szum; silnik o nich nie wie",
  baseline: "suma nowego śniegu z 3 dni ≥ 30 cm: flaga na wszystkich stokach nad szlakami",
  fixed_route_rule: "patrol wzdłuż niebieskiego szlaku Murowaniec – Czarny Staw – Zawrat, potem najbliższe stoki",
  library: { runs: scenarios.count, sectors: rel.length },
  note: "dane syntetyczne, test logiki",
};
writeFileSync(join(DATA, "proof.json"), JSON.stringify(proof, null, 1));
console.log(JSON.stringify(proof, null, 1));

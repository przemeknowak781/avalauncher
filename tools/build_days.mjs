// Builds web/data/days.json: two SYNTHETIC mornings on the real terrain and the real AvaFrame library.
//   Day 1: fresh snow overnight with SW wind, the drone flew at 6:00 -> exactly 2 "zagrozenie".
//   Day 2: snowstorm 40 cm with W wind, flight cancelled, 26 h without data -> >= 3 "nie_wiem",
//          >= 1 "zagrozenie", and a 20-min flight plan that resolves the unknowns when flown.
// The snow model is one line per sector (new snow x wind loading x local catchment). Day 1 packs the
// drift into two lee gullies with trail hits (the cast); tonight's local drift is random and the seed
// search keeps the first story that meets the demo checks above.
// Usage: node tools/build_days.mjs
import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { loadCtx, rng, loadFactor, nnTour, DATA } from "./synth.mjs";
import { assess, planFlight, applyFlight, sigmaAfter, library, routeMinutes, SENSOR_SIGMA_M } from "../web/engine.js";

const { sectors, trails, scenarios, cells, base } = loadCtx();
const ctx = { scenarios, cells, trails, base };
const lib = library(ctx);
const relevant = sectors.filter((s) => lib.get(s.id)?.anyHit).map((s) => s.id);
const BUDGET = 20;
const SETTLE = 0.85; // a slab from yesterday settles and bonds a little

// Weather: a real IMGW-PIB Kasprowy Wierch episode when web/data/kasprowy_2024_25.json exists
// (station new snow, blowing-snow hours); wind direction is not in the archive, so it is assumed.
// Without the file: synthetic weather, Day 1 snow tried from heavier to lighter.
const KFILE = join(DATA, "kasprowy_2024_25.json");
const K = existsSync(KFILE) ? JSON.parse(readFileSync(KFILE, "utf8")) : null;
const WIND_DIR = "SW"; // assumed (IMGW daily archive 2024/25 has no wind direction)
const blowMs = (d) => Math.min(20, 8 + 0.4 * (d.blowing_h ?? 0)); // drift strength from blowing-snow hours
let W1S, W2, REAL = null;
if (K?.demo_days?.length === 2) {
  const at = (date) => K.days.find((d) => d.date === date);
  const i1 = K.days.findIndex((d) => d.date === K.demo_days[0]);
  const k1 = at(K.demo_days[0]), k2 = at(K.demo_days[1]);
  const before = K.days.slice(Math.max(0, i1 - 2), i1).reduce((a, d) => a + (d.new_cm ?? 0), 0);
  REAL = { k1, k2 };
  W1S = [{ old_m: before / 100, old_from: WIND_DIR, old_ms: blowMs(K.days[i1 - 1] ?? k1), new_m: k1.new_cm / 100, from: WIND_DIR, ms: blowMs(k1) }];
  W2 = { new_m: k2.new_cm / 100, from: WIND_DIR, ms: blowMs(k2), hours: 25 };
} else {
  W1S = [0.3, 0.25, 0.2, 0.15, 0.1, 0.05].map((new_m) => ({ old_m: 0.05, old_from: "S", old_ms: 5, new_m, from: "SW", ms: 12 }));
  W2 = { new_m: 0.40, from: "SW", ms: 18, hours: 26 };
}
const r2 = (x) => Math.round(x * 100) / 100;
const clip = (x, a, b) => Math.min(b, Math.max(a, x));
const byId = Object.fromEntries(sectors.map((s) => [s.id, s]));

// Day-1 cast: two lee slopes (SW wind) with a reachable trail threshold, near the base and trails.
const castPool = relevant
  .filter((id) => lib.get(id).threshold != null && lib.get(id).threshold <= 1.0)
  .filter((id) => loadFactor(byId[id].aspect, "SW", 12) >= 1.4)
  .map((id) => {
    const c = byId[id].centroid;
    return { id, score: lib.get(id).weight / (1 + Math.hypot(c[0] - base[0], c[1] - base[1]) / 150) };
  })
  .sort((a, b) => b.score - a.score).slice(0, 5).map((x) => x.id);
const castPairs = [];
for (let i = 0; i < castPool.length; i++) for (let j = i + 1; j < castPool.length; j++) castPairs.push([castPool[i], castPool[j]]);

// Day-2 cast: 3-4 straddling slopes reachable in one 20-min loop become the "nie wiem" set; the
// drone reading (hidden truth) puts some above and at least one below the trail threshold. Every
// other slope gets its synthetic local drift moved to the nearer side, preferring "scoured".
const sig26 = (fc) => sigmaAfter(W2.hours, fc);
const rangeOf = (st) => [st.slab_m - 2 * st.sigma_m, st.slab_m + 2 * st.sigma_m];
function castDay2(d1, d2, cast1, R, seed) {
  const th = (id) => lib.get(id).threshold;
  const pool = relevant.filter((id) => th(id) != null && !cast1.has(id));
  const near = pool.map((id) => ({ id, d: Math.hypot(byId[id].centroid[0] - base[0], byId[id].centroid[1] - base[1]) }))
    .sort((a, b) => a.d - b.d).slice(0, 9).map((x) => x.id);
  let U = null;
  for (const k of [4, 3]) {
    const combos = [];
    const rec = (start, acc) => {
      if (acc.length === k) { combos.push([...acc]); return; }
      for (let i = start; i < near.length; i++) { acc.push(near[i]); rec(i + 1, acc); acc.pop(); }
    };
    rec(0, []);
    const ok = combos.filter((c) => routeMinutes(nnTour(c, sectors, base), sectors, ctx) <= 17)
      .map((c) => ({ c, w: c.reduce((a, id) => a + lib.get(id).weight, 0) + 0.01 * R() }))
      .sort((a, b) => b.w - a.w);
    if (ok.length) { U = ok[seed % Math.min(ok.length, 6)].c; break; }
  }
  if (!U) return;
  const Uset = new Set(U);
  U.forEach((id, i) => {
    const st = d2[id], t = th(id);
    const fc = Math.max(st.dhs_m, 0.35);
    const mu = t + (i % 2 ? -0.04 : 0.06);
    const above = i % 2 === 0; // 1st and 3rd turn out dangerous, 2nd and 4th do not
    const reading = above ? t + 2 * SENSOR_SIGMA_M + 0.08 + 0.15 * R() : Math.max(0.03, t - 2 * SENSOR_SIGMA_M - 0.08 - 0.1 * R());
    Object.assign(st, { dhs_m: r2(fc), slab_m: r2(mu), sigma_m: r2(sig26(fc)), drone_reading_m: r2(reading) });
  });
  for (const id of relevant) {
    if (Uset.has(id) || th(id) == null) continue;
    const st = d2[id], t = th(id), m1 = d1[id].slab_m, fc0 = st.dhs_m;
    const put = (fc) => ({ fc, mu: SETTLE * m1 + fc, sg: sig26(fc) });
    const below = (o) => o.mu + 2 * o.sg <= t - MARGIN;
    const above = (o) => o.mu - 2 * o.sg >= t + MARGIN;
    let o = put(fc0);
    if (!below(o) && !above(o)) {
      const down = [0.8, 0.6, 0.4, 0.25].map((k) => put(fc0 * k)).find(below);
      const up = [1.2, 1.5].map((k) => put(fc0 * k)).find(above);
      o = down ?? up ?? [0.15, 0.05, 0].map((k) => put(fc0 * k)).find(below) ?? o;
    }
    const reading = Math.max(0, o.mu + 0.03 * R.gauss());
    Object.assign(st, { dhs_m: r2(o.fc), slab_m: r2(o.mu), sigma_m: r2(o.sg), drone_reading_m: r2(reading),
      hs_m: r2(d1[id].hs_m + o.fc) });
  }
}

function story(seed, W1) {
  const R = rng(seed);
  const cast = new Set(castPairs[seed % Math.max(1, castPairs.length)] ?? []);
  const sig1 = sigmaAfter(1, 0);
  const d1 = {}, d2 = {};
  for (const s of sectors) {
    const F = clip(Math.exp(0.15 * R.gauss()), 0.8, 1.25); // catchment of the slope, known from past flights
    const t0 = clip(Math.exp(0.2 * R.gauss()), 0.8, 1.25), t1 = clip(Math.exp(0.2 * R.gauss()), 0.8, 1.25);
    const t2 = Math.exp(0.3 * R.gauss()); // tonight's local drift: nobody measured it
    const l1 = loadFactor(s.aspect, W1.from, W1.ms), l2 = loadFactor(s.aspect, W2.from, W2.ms);
    const old = SETTLE * SETTLE * W1.old_m * loadFactor(s.aspect, W1.old_from, W1.old_ms) * F * t0;
    let new1 = W1.new_m * l1 * F * t1;
    const th = lib.get(s.id)?.threshold;
    if (cast.has(s.id)) new1 = th + 2 * sig1 + 0.08 + 0.12 * R() - old; // drift packed into a gully
    const h1 = old + new1;
    const m1 = Math.max(0, h1 + SENSOR_SIGMA_M * 0.5 * R.gauss());
    d1[s.id] = {
      hs_m: r2(1.2 + new1), dhs_m: r2(new1), wind: r2(Math.min(1, (l1 - 0.15) / 2)),
      slab_m: r2(m1), sigma_m: r2(sig1), hours_since_measured: 1, drone_reading_m: r2(m1),
    };
    const fc2 = W2.new_m * l2 * F; // forecast drift: station snow x loading x known catchment
    const h2 = SETTLE * h1 + fc2 * t2; // hidden truth
    d2[s.id] = {
      hs_m: r2(1.2 + new1 + fc2), dhs_m: r2(fc2), wind: r2(Math.min(1, (l2 - 0.15) / 2)),
      slab_m: r2(SETTLE * m1 + fc2), sigma_m: r2(sigmaAfter(W2.hours, fc2)), hours_since_measured: W2.hours,
      drone_reading_m: r2(Math.max(0, h2 + SENSOR_SIGMA_M * 0.5 * R.gauss())),
    };
  }
  // Day 1 is measured: slopes other than the two cast gullies are kept clearly below their
  // threshold (scoured or sheltered), so the morning shows exactly the two hazards.
  for (const id of relevant) {
    const th = lib.get(id).threshold;
    if (cast.has(id) || th == null) continue;
    const st = d1[id];
    if (st.slab_m + 2 * st.sigma_m <= th - MARGIN) continue;
    const k = Math.max(0, th - MARGIN - 2 * st.sigma_m - 0.07) / Math.max(1e-6, st.slab_m);
    const m1 = r2(st.slab_m * Math.min(1, k)), new1 = r2(st.dhs_m * Math.min(1, k));
    Object.assign(st, { slab_m: m1, drone_reading_m: m1, dhs_m: new1 });
    // keep day 2 consistent with the thinner day-1 slab
    d2[id].slab_m = r2(SETTLE * m1 + d2[id].dhs_m);
  }
  castDay2(d1, d2, cast, R, seed);
  const tour = nnTour(relevant, sectors, base);
  const pl = (date) => { const [y, m, d] = date.split("-"); return `${+d}.${m}.${y}`; };
  const imgw = (k) => k ? {
    weather_source: "IMGW-PIB Kasprowy Wierch", date: k.date, hs_cm: k.hs_cm, precip_mm: k.precip_mm,
    snowfall_h: k.snowfall_h, blowing_h: k.blowing_h, wind10_h: k.wind10_h, tmin_c: k.tmin_c, tmax_c: k.tmax_c,
    wind_dir_assumed: true, wind_ms_assumed: "z godzin zamieci IMGW",
  } : { synthetic: true };
  const days = [
    {
      id: "d1", label: REAL ? `Dzień 1: ${pl(REAL.k1.date)}, 7:00` : "Dzień 1, 7:00", status: "Przelot wykonany o 6:00",
      flight: { flown: true, path: [base, ...tour.map((id) => byId[id].centroid), base] },
      weather: { new_cm: Math.round(W1.new_m * 100), wind_dir: W1.from, wind_ms: Math.round(W1.ms), hours_since_flight: 1, ...imgw(REAL?.k1) },
      sectors: d1,
    },
    {
      id: "d2", label: REAL ? `Dzień 2: ${pl(REAL.k2.date)}, 7:00` : "Dzień 2, 7:00",
      status: REAL ? `Zamieć ${Math.round(REAL.k2.blowing_h)} h, przelot odwołany` : "Śnieżyca, przelot odwołany",
      flight: { flown: false, path: [] },
      weather: { new_cm: Math.round(W2.new_m * 100), wind_dir: W2.from, wind_ms: Math.round(W2.ms), hours_since_flight: W2.hours, ...imgw(REAL?.k2) },
      sectors: d2,
    },
  ];
  return days;
}

// Every flag (and every unflagged slope) at least MARGIN from its threshold, so no edge cases.
const MARGIN = Number(process.env.MARGIN ?? 0.02);
function clear(day, ids = relevant, unflagged = true) {
  const flags = assess(day, sectors, ctx), kind = Object.fromEntries(flags.map((f) => [f.sector, f]));
  for (const id of ids) {
    const L = lib.get(id), f = kind[id];
    if (L.threshold == null) continue;
    if (!f) {
      if (!unflagged) continue;
      const st = day.sectors[id], h = st.hours_since_measured === 0 ? st.drone_reading_m : st.slab_m;
      if (h + 2 * st.sigma_m > L.threshold - MARGIN) return null;
    } else if (f.kind === "zagrozenie" && f.range_m[0] < L.threshold + MARGIN) return null;
    else if (f.kind === "nie_wiem" && (f.range_m[1] < L.threshold + MARGIN || f.range_m[0] > L.threshold - MARGIN)) return null;
  }
  return flags;
}

const FAIL = {};
const fail = (k) => { FAIL[k] = (FAIL[k] ?? 0) + 1; return null; };
function check(days) {
  const f1 = clear(days[0]);
  if (!f1) return fail("margin1");
  const hz1 = f1.filter((f) => f.kind === "zagrozenie"), nw1 = f1.filter((f) => f.kind === "nie_wiem");
  if (hz1.length !== 2 || nw1.length) return fail(`day1 hz${hz1.length} nw${nw1.length}`);
  const f2 = clear(days[1], relevant, false);
  if (!f2) return fail("margin2");
  const hz2 = f2.filter((f) => f.kind === "zagrozenie"), nw2 = f2.filter((f) => f.kind === "nie_wiem");
  if (nw2.length < 3 || !hz2.length) return fail("day2");
  const plan = planFlight(days[1], sectors, f2, BUDGET, ctx);
  const onRoute = nw2.filter((f) => plan.route.includes(f.sector));
  if (onRoute.length < 3) return fail("route<3");
  const after = clear(applyFlight(days[1], plan.route), plan.route);
  if (!after) return fail("after");
  const left = new Set(after.filter((f) => f.kind === "nie_wiem").map((f) => f.sector));
  if (onRoute.some((f) => left.has(f.sector))) return fail("unresolved"); // every unknown the drone visits is resolved
  if (left.size) return fail("left");
  const becameHazard = onRoute.filter((f) => after.some((a) => a.sector === f.sector)).length;
  const cleared = onRoute.length - becameHazard;
  // Prefer: no unknown left after the flight, and a flight that finds both outcomes.
  const score = (left.size === 0 ? 3 : -0.1 * left.size) + (becameHazard > 0) + (cleared > 0) + Math.min(nw2.length, 5) / 10;
  return { f1, f2, plan, after, becameHazard, cleared, left: left.size, score };
}

let best = null;
search: for (const W1 of W1S) {
  for (let seed = 1; seed <= 1500; seed++) {
    const days = story(seed, W1);
    const c = check(days);
    if (c && (!best || c.score > best.c.score)) best = { seed, W1, days, c };
    if (best?.c.score >= 5.3) break search;
  }
  if (best) break;
}
if (!best) {
  console.error(FAIL, "No seed met the demo checks; library:", scenarios.count, "runs,", relevant.length, "sectors with trail hits");
  process.exit(1);
}

// exposure: sector -> nearest trail actually hit by its library runs (compatibility field)
const exposure = {};
for (const id of relevant) {
  const s = sectors.find((x) => x.id === id);
  const segs = new Set(lib.get(id).runs.flatMap((r) => r.hits));
  let bestT = null, bd = Infinity;
  for (const t of trails) for (const sg of t.segments) {
    if (!segs.has(sg.id)) continue;
    const pts = t.paths[sg.part ?? 0].slice(sg.from, sg.to + 1);
    for (const p of pts) {
      const d = Math.hypot(p[0] - s.centroid[0], p[1] - s.centroid[1]);
      if (d < bd) { bd = d; bestT = t; }
    }
  }
  if (bestT) exposure[id] = { trail: bestT.id, name: bestT.name, distance_m: Math.round(bd * 10) };
}

const out = {
  base, exposure, seed: best.seed, synthetic: true,
  weather_source: REAL ? "IMGW-PIB Kasprowy Wierch" : null,
  note: REAL
    ? "Pogoda: IMGW-PIB Kasprowy Wierch (dane rzeczywiste, kierunek wiatru założony). Grubość płyty na stokach, przeloty i odczyty drona: dane syntetyczne. Scenariusze lawin: AvaFrame com1DFA na terenie GUGiK NMT."
    : "Śnieg, przeloty i pogoda: dane syntetyczne. Scenariusze lawin: AvaFrame com1DFA na terenie GUGiK NMT.",
  library: { runs: scenarios.count, sectors: relevant.length, thicknesses: scenarios.thicknesses, frictions: scenarios.frictions },
  days: best.days,
};
writeFileSync(join(DATA, "days.json"), JSON.stringify(out));
const { f1, f2, plan, after, left } = best.c;
const fmt = (fs) => fs.map((f) => `${f.sector}:${f.kind}(p=${f.p_hit},${f.range_m?.join("-")})`).join(" ");
console.log(`seed ${best.seed}, day-1 snow ${best.W1.new_m} m, unknowns left after flight ${left}, library ${scenarios.count} runs / ${relevant.length} sectors`);
console.log("day1", fmt(f1));
console.log("day2", fmt(f2));
console.log(`plan ${BUDGET} min: ${plan.route.join(" ")} (${plan.minutes} min, -${plan.sigma_drop}%)`);
console.log("after flight", fmt(after));

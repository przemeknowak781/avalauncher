// Avalauncher engine. Pure functions, ES module, runs in the browser and in Node
// (tools/build_days.mjs, tools/proof.mjs). It only escalates: no flag never means "safe".
//
// One sentence per idea:
// - State: per sector the day gives a slab-thickness estimate h (new snow + wind loading) and its
//   uncertainty σ, which grows with hours since the last drone pass and with new snow since then;
//   a pass resets σ to the sensor error (sigmaAfter).
// - Analogs: AvaFrame com1DFA runs of the same sector whose release thickness relTh lies in the
//   plausible range [h − 2σ, h + 2σ] (all frictions); if the range falls between two computed
//   thicknesses, the two nearest ones. Between computed thicknesses the share of runs reaching a
//   trail is interpolated; below the thinnest computed slab there is no analog, so no evidence.
// - Hit: a run puts at least 0.5 m of flowing snow on a trail segment (hits_pft_m), not just a touch.
// - Release: a slab rarely releases below 0.3 m and usually does above 0.5 m (linear between).
// - Chance for a slab x: release(x) × share of analogs with a hit; threshold = thinnest x where ≥ 50 %.
// - "zagrozenie": that chance is ≥ 50 % even at the low end of the plausible range.
// - "nie_wiem": the plausible range straddles the threshold thickness, i.e. the measurement error
//   is larger than the margin to the threshold, so the uncertainty decides the answer.
// - Flight plan: value of information, i.e. the expected drop of decision uncertainty (a "nie wiem"
//   that a reading would turn into an answer, plus the entropy of P(slab above the threshold)) ×
//   trail weight, per extra flight minute from the base, greedy within the budget, back to base.
//
// ctx (all optional except scenarios for real flags):
//   scenarios  web/data/scenarios.json {count, thicknesses, runs:[{sector, relTh, frict, hits,
//              runout_m, cells_offset, cells_count, ...}]}
//   cells      Uint32Array of web/data/scenario_cells.bin (row*width+col, peak flow > 0.1 m);
//              when present, flags get `envelope` (union of footprints of analogs hitting a trail)
//   trails     web/data/trails.json, maps segment ids ("T26-5") to trail names
//   base       [c, r] flight base (Murowaniec), from days.json
//   exposure   {sector: {trail, name, distance_m}} from days.json; fallback trail names
//   speed_cells_per_min, survey_min  optional flight model overrides
//
// day.sectors[id]:
//   slab_m                estimated slab thickness h [m]
//   sigma_m               uncertainty σ [m] (build_days.mjs computes it with sigmaAfter)
//   hours_since_measured  0 = just measured: then drone_reading_m replaces slab_m (the UI resets
//                         sigma_m and hours_since_measured of sectors the drone has flown over)
//   drone_reading_m       synthetic reading the drone returns when it flies now
//                         (hidden truth + sensor error); lets the UI "fly" without the engine
//   dhs_m, wind           new snow since last pass [m], wind loading 0..1 (display, fallback for slab_m)
//
// Flag: {sector, kind, reason, trails:[names], segments:[ids], analogs, analogs_hitting,
//        p_hit 0..1, range_m:[lo, hi], h_m, sigma_m, threshold_m, weight, envelope:[cell idx] | null}
// planFlight → {route:[ids], path:[[c,r]…], minutes, sigma_drop (% of decision uncertainty the
//        route is expected to remove), uncertainty_bits, expected_drop_bits}
// Also exported: applyFlight(day, route) (day after the drone flew), uncertainty, sigmaAfter, library.

export const SENSOR_SIGMA_M = 0.08; // drone radar slab-thickness error (matches the UI reset)
export const SIGMA_PER_HOUR_M = 0.003; // knowledge ages: wind and settling since the pass
export const SIGMA_PER_NEW_SNOW = 0.4; // each metre of new snow on the sector adds 0.4 m of doubt
export const HIT_SHARE = 0.5; // "likely": release × share of analogs reaching the trail ≥ 50 %
export const HIT_PFT_M = 0.5; // flow on the trail that matters for people (hits_pft_m)
export const RELEASE_MIN_M = 0.3; // thinner slabs rarely release
export const RELEASE_FULL_M = 0.5; // thicker slabs usually do
const WIND_LOAD = 1.0; // fallback h = dHS · (1 + wind)
const SPEED_CELLS_PER_MIN = 60; // 600 m/min, a slow survey pass
const SURVEY_MIN = 1.5; // minutes over a sector
const MONITOR = 0.01; // watch value of a slope already flagged as a hazard
const FRESHNESS = 0.002; // tiny value of refreshing σ when no decision is at stake (tie-breaker)

export function sigmaAfter(hours, newSnowM = 0) {
  return Math.hypot(SENSOR_SIGMA_M, SIGMA_PER_HOUR_M * hours, SIGMA_PER_NEW_SNOW * newSnowM);
}

// ---------- library index ----------
const CACHE = new WeakMap();

export function library(ctx) {
  const sc = ctx?.scenarios;
  if (!sc?.runs) return new Map();
  if (CACHE.has(sc)) return CACHE.get(sc);
  const by = new Map();
  for (const r of sc.runs) {
    if (!by.has(r.sector)) by.set(r.sector, []);
    by.get(r.sector).push(r);
  }
  const out = new Map();
  for (const [id, runs] of by) {
    const lv = new Map();
    for (const r of runs) {
      const k = Math.round(r.relTh * 100) / 100;
      if (!lv.has(k)) lv.set(k, []);
      lv.get(k).push(r);
    }
    const levels = [...lv.entries()].sort((a, b) => a[0] - b[0])
      .map(([th, rs]) => ({ th, runs: rs, reach: rs.filter(isHit).length / rs.length }));
    const trails = new Set(runs.flatMap((r) => hitSegments(r).map(trailOf)));
    const entry = { id, runs, levels, weight: Math.max(1, trails.size), anyHit: trails.size > 0 };
    entry.threshold = thresholdOf(entry);
    out.set(id, entry);
  }
  CACHE.set(sc, out);
  return out;
}

// A hit matters for people on the trail: at least HIT_PFT_M of flowing snow on a trail segment.
export const hitSegments = (r) =>
  r.hits_pft_m ? r.hits.filter((_, i) => r.hits_pft_m[i] >= HIT_PFT_M) : r.hits;
const isHit = (r) => hitSegments(r).length > 0;
const trailOf = (seg) => seg.split("-")[0];

// A slab releases rarely below RELEASE_MIN_M and usually above RELEASE_FULL_M (linear between).
export const releaseAt = (x) => Math.min(1, Math.max(0, (x - RELEASE_MIN_M) / (RELEASE_FULL_M - RELEASE_MIN_M)));

// Share of library runs reaching a trail with dangerous flow for a slab x (interpolated between
// computed thicknesses; below the thinnest one, the thinnest one is the nearest analog).
function reachAt(lib, x) {
  const L = lib.levels;
  if (!L.length) return 0;
  if (x <= L[0].th) return L[0].reach;
  if (x >= L[L.length - 1].th) return L[L.length - 1].reach;
  for (let i = 1; i < L.length; i++) {
    if (x < L[i].th) {
      const t = (x - L[i - 1].th) / (L[i].th - L[i - 1].th);
      return L[i - 1].reach + t * (L[i].reach - L[i - 1].reach);
    }
  }
  return L[L.length - 1].reach;
}

// Chance that a slab of thickness x releases AND its avalanche reaches a trail with dangerous flow.
export function shareAt(lib, x) {
  return releaseAt(x) * reachAt(lib, x);
}

// Thinnest slab at which that chance reaches HIT_SHARE (null if never).
function thresholdOf(lib) {
  const top = (lib.levels.at(-1)?.th ?? 0) + 0.5;
  for (let x = 0; x <= top; x += 0.01) if (shareAt(lib, x) >= HIT_SHARE) return Math.round(x * 100) / 100;
  return null;
}

// ---------- belief helpers ----------
function slabOf(st) {
  if (st.hours_since_measured === 0 && st.drone_reading_m != null) return st.drone_reading_m;
  return st.slab_m ?? st.dhs_m * (1 + WIND_LOAD * (st.wind ?? 0));
}
function sigmaOf(st) {
  return st.sigma_m ?? sigmaAfter(st.hours_since_measured ?? 0, st.dhs_m ?? 0);
}

const N_Q = 81;
// E[f(x)] and P(f(x) >= T) for x ~ N(h, s), f = shareAt; mass below 0 m counts as no slab.
function belief(lib, h, s) {
  let w = 0, p = 0, q = 0;
  for (let i = 0; i < N_Q; i++) {
    const z = -4 + (8 * i) / (N_Q - 1);
    const wi = Math.exp(-0.5 * z * z);
    const sh = shareAt(lib, h + z * s);
    w += wi; p += wi * sh; q += sh >= HIT_SHARE ? wi : 0;
  }
  return { p: p / w, q: q / w };
}

function rangeShares(lib, lo, hi) {
  let min = Infinity, max = -Infinity;
  const xs = [lo, hi, ...lib.levels.map((l) => l.th).filter((t) => t > lo && t < hi)];
  for (let i = 1; i < 16; i++) xs.push(lo + ((hi - lo) * i) / 16);
  for (const x of xs) { const v = shareAt(lib, x); min = Math.min(min, v); max = Math.max(max, v); }
  return { min, max };
}

function analogLevels(lib, lo, hi, h) {
  const inside = lib.levels.filter((l) => l.th >= lo && l.th <= hi);
  if (inside.length) return inside;
  const below = lib.levels.filter((l) => l.th < lo).at(-1);
  const above = lib.levels.find((l) => l.th > hi);
  if (!below) return []; // range thinner than any computed slab
  return above && h >= below.th ? [below, above] : [below];
}

const H2 = (q) => (q <= 1e-9 || q >= 1 - 1e-9 ? 0 : -(q * Math.log2(q) + (1 - q) * Math.log2(1 - q)));

// ---------- assess ----------
export function assess(day, sectors, ctx = {}) {
  const lib = library(ctx);
  const names = trailNames(ctx);
  const flags = [];
  for (const s of sectors) {
    const L = lib.get(s.id);
    if (!L?.anyHit) continue; // no computed avalanche from here reaches a trail
    const st = day.sectors?.[s.id];
    if (!st) {
      flags.push({
        sector: s.id, kind: "nie_wiem", reason: "Brak pomiaru tego stoku. Lawiny stąd mogą dojść do szlaku.",
        trails: topTrails(L.runs.filter(isHit), names, ctx, s.id), segments: [], analogs: L.runs.length,
        analogs_hitting: L.runs.filter(isHit).length, p_hit: Math.max(...L.levels.map((l) => l.reach)),
        range_m: null, h_m: null, sigma_m: null, threshold_m: L.threshold, weight: L.weight, envelope: null,
      });
      continue;
    }
    const h = slabOf(st), sg = sigmaOf(st);
    const lo = Math.max(0, h - 2 * sg), hi = h + 2 * sg;
    const kind = kindAt(L, h, sg);
    if (!kind) continue;
    const levels = analogLevels(L, lo, hi, h);
    const analogs = levels.flatMap((l) => l.runs);
    const hitting = analogs.filter(isHit);
    const { p } = belief(L, h, sg);
    flags.push({
      sector: s.id, kind,
      reason: reasonOf(kind, st, day, lo, hi, L),
      trails: topTrails(hitting, names, ctx, s.id),
      segments: [...new Set(hitting.flatMap(hitSegments))],
      analogs: analogs.length, analogs_hitting: hitting.length,
      p_hit: round(p, 2), range_m: [round(lo, 2), round(hi, 2)], h_m: round(h, 2), sigma_m: round(sg, 2),
      threshold_m: L.threshold == null ? null : round(L.threshold, 2), weight: L.weight,
      envelope: envelopeOf(hitting, ctx.cells),
    });
  }
  const rank = (f) => (f.kind === "zagrozenie" ? 0 : 1);
  return flags.sort((a, b) => rank(a) - rank(b) || b.p_hit - a.p_hit);
}

function reasonOf(kind, st, day, lo, hi, L) {
  const cm = (m) => Math.round(m * 100);
  const range = `${cm(lo)}–${cm(hi)} cm`;
  if (kind === "zagrozenie") {
    return `${st.hours_since_measured <= 1 ? "Dron zmierzył płytę" : "Płyta"} ${range}. Już przy ${cm(lo)} cm zwykle rusza i dochodzi do szlaku.`;
  }
  const since = st.hours_since_measured > 1
    ? `Pomiar ${st.hours_since_measured} h temu, od tego czasu ${Math.round(day.weather?.new_cm ?? cm(st.dhs_m ?? 0))} cm śniegu. `
    : "";
  return `${since}Płyta ${range}, a od ${cm(L.threshold)} cm zwykle rusza i dochodzi do szlaku.`;
}

function trailNames(ctx) {
  const m = {};
  for (const t of ctx.trails ?? []) m[t.id] = t.name;
  return m;
}

function topTrails(runs, names, ctx, sid) {
  const n = {};
  for (const r of runs) for (const t of new Set(hitSegments(r).map(trailOf))) n[t] = (n[t] ?? 0) + 1;
  const ids = Object.keys(n).sort((a, b) => n[b] - n[a]).slice(0, 2);
  const out = ids.map((t) => names[t] ?? t);
  if (!out.length && ctx.exposure?.[sid]) out.push(ctx.exposure[sid].name);
  return out;
}

function envelopeOf(runs, cells) {
  if (!cells || !runs.length) return null;
  const set = new Set();
  for (const r of runs) for (let i = r.cells_offset; i < r.cells_offset + r.cells_count; i++) set.add(cells[i]);
  return [...set].sort((a, b) => a - b);
}

// ---------- flight plan ----------
// Expected decision-uncertainty drop (bits × trail weight) if the drone measures this sector now.
export function sectorValue(lib, st) {
  if (!st) return { now: 2 * lib.weight, info: 2 * lib.weight, gain: 2 * lib.weight }; // no data: maximal doubt
  const h = slabOf(st), s = sigmaOf(st);
  // Decision uncertainty = "nie wiem" on screen (0/1) + entropy of P(slab above the trail threshold).
  const now = (kindAt(lib, h, s) === "nie_wiem" ? 1 : 0) + H2(belief(lib, h, s).q);
  // After a pass the belief is N(z, sensor σ), with the reading z ~ N(h, sqrt(σ² + sensor σ²)).
  const sz = Math.hypot(s, SENSOR_SIGMA_M);
  let after = 0, wsum = 0;
  for (let i = 0; i < N_Z; i++) {
    const zz = -3 + (6 * i) / (N_Z - 1), w = Math.exp(-0.5 * zz * zz), z = h + zz * sz;
    after += w * ((kindAt(lib, z, SENSOR_SIGMA_M) === "nie_wiem" ? 1 : 0) + H2(belief(lib, z, SENSOR_SIGMA_M).q));
    wsum += w;
  }
  after /= wsum;
  const info = lib.weight * Math.max(0, now - after);
  const fresh = (lib.weight * FRESHNESS * Math.max(0, s * s - SENSOR_SIGMA_M ** 2)) / 0.01;
  return { now: lib.weight * now, info, gain: info + fresh };
}
const N_Z = 25;

function kindAt(lib, h, s) {
  const { min, max } = rangeShares(lib, Math.max(0, h - 2 * s), h + 2 * s);
  return min >= HIT_SHARE ? "zagrozenie" : max >= HIT_SHARE ? "nie_wiem" : null;
}

export function planFlight(day, sectors, flags, budgetMin, ctx = {}) {
  const lib = library(ctx);
  const speed = ctx.speed_cells_per_min ?? SPEED_CELLS_PER_MIN;
  const survey = ctx.survey_min ?? SURVEY_MIN;
  const base = ctx.base ?? [0, 0];
  const hazard = new Set((flags ?? []).filter((f) => f.kind === "zagrozenie").map((f) => f.sector));
  const cand = [];
  for (const s of sectors) {
    const L = lib.get(s.id);
    if (!L?.anyHit || !s.centroid) continue;
    const v = sectorValue(L, day.sectors?.[s.id]);
    // Slopes flagged as a hazard keep a small watch value, so a fresh morning still has a patrol.
    if (hazard.has(s.id)) v.gain += MONITOR * L.weight;
    cand.push({ id: s.id, c: s.centroid, ...v });
  }
  const total = cand.reduce((a, c) => a + c.now, 0);

  // Greedy insertion: add the sector with the most expected knowledge per extra flight minute,
  // at its cheapest place in the tour, while the round trip from base fits the budget.
  // (Run twice, per minute and per sector, and keep the richer tour: a standard orienteering trick.)
  const legs = (tour) => {
    let pos = base, m = 0;
    for (const c of tour) { m += dist(pos, c.c) / speed + survey; pos = c.c; }
    return m + dist(pos, base) / speed;
  };
  const greedy = (perMinute) => {
    let tour = [], minutes = legs(tour);
    const pool = new Set(cand.filter((c) => c.gain > 1e-9));
    for (;;) {
      let best = null;
      for (const c of pool) {
        for (let i = 0; i <= tour.length; i++) {
          const t = [...tour.slice(0, i), c, ...tour.slice(i)];
          const m = legs(t);
          if (m > budgetMin) continue;
          const score = perMinute ? c.gain / Math.max(1e-6, m - minutes) : c.gain - 1e-6 * m;
          if (!best || score > best.score) best = { c, t, m, score };
        }
      }
      if (!best) {
        const shorter = twoOpt(tour, legs); // untangle the loop; if it saves time, try to add more
        if (legs(shorter) < minutes - 1e-6) { tour = shorter; minutes = legs(tour); continue; }
        break;
      }
      pool.delete(best.c);
      tour = best.t; minutes = best.m;
    }
    return { tour, minutes, value: tour.reduce((a, c) => a + c.gain, 0) };
  };
  const a = greedy(true), b = greedy(false);
  const { tour, minutes } = b.value > a.value + 1e-9 ? b : a;
  const route = tour.map((c) => c.id);
  const path = [base, ...tour.map((c) => c.c), base];
  const drop = tour.reduce((a, c) => a + Math.min(c.now, c.info), 0);
  return {
    route, path, minutes: Math.round(minutes),
    sigma_drop: total > 1e-6 ? Math.round((100 * drop) / total) : 0, // % of decision uncertainty removed
    uncertainty_bits: round(total, 2), expected_drop_bits: round(drop, 2),
  };
}

function twoOpt(tour, legs) {
  let best = tour, bm = legs(tour), improved = true;
  while (improved) {
    improved = false;
    for (let i = 0; i < best.length - 1; i++) for (let j = i + 1; j < best.length; j++) {
      const t = [...best.slice(0, i), ...best.slice(i, j + 1).reverse(), ...best.slice(j + 1)];
      const m = legs(t);
      if (m < bm - 1e-6) { best = t; bm = m; improved = true; }
    }
  }
  return best;
}

// Same flight model for any fixed list of sectors (used by the proof's fixed route).
export function routeMinutes(route, sectors, ctx = {}) {
  const speed = ctx.speed_cells_per_min ?? SPEED_CELLS_PER_MIN;
  const survey = ctx.survey_min ?? SURVEY_MIN;
  const byId = Object.fromEntries(sectors.map((s) => [s.id, s]));
  let pos = ctx.base, m = 0;
  for (const id of route) { m += dist(pos, byId[id].centroid) / speed + survey; pos = byId[id].centroid; }
  return m + dist(pos, ctx.base) / speed;
}

// Decision uncertainty over all trail-relevant sectors (bits × trail weight).
export function uncertainty(day, sectors, ctx = {}) {
  const lib = library(ctx);
  let u = 0;
  for (const s of sectors) {
    const L = lib.get(s.id);
    if (L?.anyHit) u += sectorValue(L, day.sectors?.[s.id]).now;
  }
  return u;
}

// The day after the drone flew over `route`: σ back to the sensor error, h = the drone reading.
export function applyFlight(day, route) {
  const s = { ...day.sectors };
  for (const id of route) {
    const st = s[id];
    if (!st) continue;
    const h = st.drone_reading_m ?? st.slab_m;
    s[id] = { ...st, slab_m: h, sigma_m: SENSOR_SIGMA_M, hours_since_measured: 0 };
  }
  return { ...day, sectors: s };
}

function dist(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}
const round = (x, d) => Math.round(x * 10 ** d) / 10 ** d;

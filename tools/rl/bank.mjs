// The REAL engine (web/engine.js) as a black box for the RL environment. Every quantity is per
// sector and independent of the other sectors, so a morning is a table of per-sector numbers.
//   node tools/rl/bank.mjs meta  <out.json>                       ids, aspects, centroids, weights, base
//   node tools/rl/bank.mjs table <mornings.json> <out.json> [plan] engine tables (+ VOI/fixed routes)
import { readFileSync, writeFileSync } from "node:fs";
import { loadCtx, nnTour } from "../synth.mjs";
import { assess, planFlight, uncertainty, routeMinutes, applyFlight, library, sectorValue, shareAt, HIT_SHARE } from "../../web/engine.js";

const [mode, a, b, plan] = process.argv.slice(2);
const { sectors, trails, scenarios, base } = loadCtx();
const ctx = { scenarios, trails, base };
const lib = library(ctx);
const rel = sectors.filter((s) => lib.get(s.id)?.anyHit);
const ids = rel.map((s) => s.id);
const fixedAll = nnTour(ids, sectors, base);
const FIXED = [];
for (const id of fixedAll) { if (routeMinutes([...FIXED, id], sectors, ctx) <= 20) FIXED.push(id); else break; }

if (mode === "meta") {
  writeFileSync(a, JSON.stringify({
    ids, base, runs: scenarios.count, aspect: rel.map((s) => s.aspect), centroid: rel.map((s) => s.centroid),
    weight: ids.map((id) => lib.get(id).weight), threshold: ids.map((id) => lib.get(id).threshold),
    fixed: FIXED, fixed_min: routeMinutes(FIXED, sectors, ctx),
  }));
  console.log(`meta: ${ids.length} sectors, ${scenarios.count} runs, fixed route ${FIXED.join(" ")}`);
} else {
  const E = JSON.parse(readFileSync(a, "utf8"));
  if (E.ids.join() !== ids.join()) throw new Error("library changed since the mornings were generated");
  const T = { now0: [], now1: [], info: [], gain: [], kind0: [], kind1: [], threat: [], p: [], voi: [], voi_min: [], u0: [], u_voi: [], u_fixed: [] };
  const K = { nie_wiem: 1, zagrozenie: 2 };
  const t0 = Date.now();
  for (let m = 0; m < E.h.length; m++) {
    const day = { weather: { new_cm: 0 }, sectors: Object.fromEntries(ids.map((id, i) => [id, {
      slab_m: E.h[m][i], sigma_m: E.s[m][i], hours_since_measured: E.hours[m], drone_reading_m: E.reading[m][i], dhs_m: 0 }])) };
    const after = applyFlight(day, ids); // as if every sector were surveyed now (per-sector outcome)
    const f0 = Object.fromEntries(assess(day, rel, ctx).map((f) => [f.sector, f]));
    const f1 = Object.fromEntries(assess(after, rel, ctx).map((f) => [f.sector, f]));
    const row = (fn) => ids.map(fn);
    const v0 = row((id) => sectorValue(lib.get(id), day.sectors[id]));
    T.now0.push(v0.map((v) => v.now));
    T.info.push(v0.map((v) => v.info));
    T.gain.push(v0.map((v, i) => v.gain + (f0[ids[i]]?.kind === "zagrozenie" ? 0.01 * lib.get(ids[i]).weight : 0)));
    T.now1.push(row((id) => sectorValue(lib.get(id), after.sectors[id]).now));
    T.kind0.push(row((id) => K[f0[id]?.kind] ?? 0));
    T.kind1.push(row((id) => K[f1[id]?.kind] ?? 0));
    T.p.push(row((id) => f0[id]?.p_hit ?? 0));
    T.threat.push(row((id, i) => (shareAt(lib.get(id), E.truth[m][i]) >= HIT_SHARE ? 1 : 0)));
    if (plan) {
      const p = planFlight(day, rel, assess(day, rel, ctx), 20, ctx);
      T.voi.push(p.route); T.voi_min.push(routeMinutes(p.route, sectors, ctx));
      T.u0.push(uncertainty(day, rel, ctx));
      T.u_voi.push(uncertainty(applyFlight(day, p.route), rel, ctx));
      T.u_fixed.push(uncertainty(applyFlight(day, FIXED), rel, ctx));
    }
  }
  writeFileSync(b, JSON.stringify(T));
  console.log(`table: ${E.h.length} mornings in ${Date.now() - t0} ms`);
}

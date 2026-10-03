// Shared helpers for tools/build_days.mjs and tools/proof.mjs: data loading (Node) and the
// SYNTHETIC snow model. Snow, wind, flights and the hidden truth are synthetic; terrain, sectors,
// trails and the AvaFrame com1DFA scenario library are real files from web/data/.
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
export const DATA = join(ROOT, "web", "data");
const BASE_FALLBACK = [278, 69.2]; // Schronisko Murowaniec (49.2433 N, 20.0072 E) in grid cells

const readJson = (p) => JSON.parse(readFileSync(p, "utf8"));

export function loadCtx() {
  const sectors = readJson(join(DATA, "sectors.json"));
  const trails = readJson(join(DATA, "trails.json"));
  const lib = process.env.AVA_LIBRARY_DIR ?? DATA; // override to test against another library export
  const scenarios = readJson(join(lib, "scenarios.json"));
  const buf = readFileSync(join(lib, "scenario_cells.bin"));
  const cells = new Uint32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const mock = join(DATA, "mock", "days.json");
  const base = existsSync(mock) ? readJson(mock).base : BASE_FALLBACK;
  return { sectors, trails, scenarios, cells, base };
}

// Deterministic RNG (mulberry32) and a standard normal draw.
export function rng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  next.gauss = () => Math.sqrt(-2 * Math.log(1 - next())) * Math.cos(2 * Math.PI * next());
  return next;
}

const DIR = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SW: 225, W: 270, NW: 315 };

// Wind loading factor: lee slopes (facing downwind) collect drift, windward slopes are scoured.
export function loadFactor(aspect, windFrom, windMs) {
  const downwind = (DIR[windFrom] + 180) % 360;
  const c = Math.cos(((DIR[aspect] - downwind) * Math.PI) / 180);
  const k = 1.1 * Math.min(windMs, 20) / 20;
  return Math.min(2.2, Math.max(0.15, 1 + k * c));
}

// Nearest-neighbour tour over sector ids from the base (fixed patrol route, day-1 flight path).
export function nnTour(ids, sectors, base) {
  const byId = Object.fromEntries(sectors.map((s) => [s.id, s]));
  const left = new Set(ids), out = [];
  let pos = base;
  while (left.size) {
    let best = null, bd = Infinity;
    for (const id of left) {
      const c = byId[id].centroid, d = Math.hypot(c[0] - pos[0], c[1] - pos[1]);
      if (d < bd) { bd = d; best = id; }
    }
    left.delete(best); out.push(best); pos = byId[best].centroid;
  }
  return out;
}

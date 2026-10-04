import { assess, planFlight, hitSegments } from "./engine.js";
import * as xp from "./xp/xp.js";

const TRAIL = { red: "#d62828", blue: "#1f5fd1", green: "#2a9d3c", yellow: "#f2c200", black: "#22201c" };
const HAZARD = "#e8590c";
const UNKNOWN = "#5b3fd1";
const ROUTE = "#d6007e";
const INK = "#1d1b17";
const PAPER = "#f4efe4";
const MEASURED_SIGMA = 0.08;

const $ = (id) => document.getElementById(id);
const json = (p) => fetch(p).then((r) => (r.ok ? r.json() : Promise.reject(new Error(p))));
const optional = (p) => json(p).catch(() => null);
const binary = (p, T) => fetch(p).then((r) => (r.ok ? r.arrayBuffer() : null))
  .then((b) => (b && b.byteLength % T.BYTES_PER_ELEMENT === 0 ? new T(b) : null)).catch(() => null);

// ---------- data ----------
const [terrain, sectors, trails, real, mock, scenarios, calibration, proof, kasprowy, media3d, sentinel] = await Promise.all([
  json("data/terrain.json"), json("data/sectors.json"), json("data/trails.json"),
  optional("data/days.json"), optional("data/mock/days.json"),
  optional("data/scenarios.json"), optional("data/calibration.json"), optional("data/proof.json"),
  optional("data/kasprowy_2024_25.json"), // real IMGW-PIB daily synop, tools/real/build_kasprowy.py
  optional("media/3d/index.json"), // 3D AvaFrame animations of the flagged sectors (Odtwarzacz 3D)
  optional("data/sentinel_snow.json"), // real Copernicus Sentinel-2 snow cover, tools/satellite/fetch_sentinel.py
]);
// AvaFrame footprints (5 MB) load after the first frame; see loadLibraryCells()
let cells = null, libHeat = null;
const DAYS = real ?? mock;
const index = new Uint8Array(await (await fetch("data/sectors_u8.bin")).arrayBuffer());
// Image.decode() never settles while the page is hidden (background tab, headless capture), which left
// the app blank; the load event does fire, and drawImage() decodes on first use.
const loaded = (img) => new Promise((resolve, reject) => {
  if (img.complete) { img.naturalWidth ? resolve(img) : reject(new Error(img.src)); return; }
  img.addEventListener("load", () => resolve(img), { once: true });
  img.addEventListener("error", () => reject(new Error(img.src)), { once: true });
});
const base = new Image();
base.src = "data/map.png";
await loaded(base).catch(async () => { base.src = `data/${terrain.hillshade}`; await loaded(base); });
await document.fonts.load('700 16px "Archivo"').catch(() => {});

const W = terrain.width, H = terrain.height;
const byId = Object.fromEntries(sectors.map((s) => [s.id, s]));
const ctx = { exposure: DAYS.exposure, base: DAYS.base, scenarios, trails, cells: null };

// Library runs by sector, friction and slab ("Co jeśli płyta ma X m?"), trail names and segment geometry.
const runKey = (sector, frict, th) => `${sector}|${frict}|${Number(th).toFixed(1)}`;
const RUNS = new Map((scenarios?.runs ?? []).map((r) => [runKey(r.sector, r.frict, r.relTh), r]));
const TRAIL_NAME = Object.fromEntries(trails.map((t) => [t.id, t.name]));
const SEGMENT = new Map();
for (const t of trails) for (const s of t.segments ?? []) SEGMENT.set(s.id, t.paths[s.part]?.slice(s.from, s.to + 1) ?? []);

// ---------- real weather: IMGW-PIB Kasprowy Wierch, winter 2024/25 ----------
const KW = kasprowy?.days?.length ? kasprowy : null;
const MONTHS_GEN = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"];
const pl = (v, d = 0) => Number(v).toLocaleString("pl-PL", { maximumFractionDigits: d, minimumFractionDigits: d });
const dmy = (iso) => { const [y, m, d] = iso.split("-"); return `${+d}.${m}.${y}`; };
const longDate = (iso) => { const [y, m, d] = iso.split("-"); return `${+d} ${MONTHS_GEN[m - 1]} ${y}`; };
/** The real morning behind demo day n: that day's IMGW record plus the 3-day storm totals. */
function realMorning(n = state.day) {
  const date = KW?.demo_days?.[n];
  const i = date ? KW.days.findIndex((d) => d.date === date) : -1;
  if (i < 0) return null;
  const w = KW.days.slice(Math.max(0, i - 2), i + 1);
  return { ...KW.days[i], i, new3: w.reduce((a, d) => a + (d.new_cm ?? 0), 0), blow3: w.reduce((a, d) => a + (d.blowing_h ?? 0), 0) };
}

// ---------- state ----------
const state = {
  day: new URLSearchParams(location.search).get("day") === "2" ? 1 : 0, selected: null, budget: 20,
  visited: new Set(), flight: null, // { path, len, t, done }
  heat: false, // "Widok › Zasięgi z biblioteki AvaFrame"
  sat: false, // "Widok › Pokrywa śnieżna z satelity (Sentinel-2)"
  whatIf: null, // { sector, th, frict }: the run chosen with the flag dialog's slider
  fog: new Float32Array(sectors.length + 1), // animated fog per sector index
  dash: 0,
};
let R = null; // computed result for the current state

function effectiveDay() {
  const d = DAYS.days[state.day];
  if (!state.visited.size) return d;
  const s = { ...d.sectors };
  for (const id of state.visited) if (s[id]) s[id] = { ...s[id], sigma_m: MEASURED_SIGMA, hours_since_measured: 0 };
  return { ...d, sectors: s };
}

function compute() {
  const day = effectiveDay();
  const flags = assess(day, sectors, ctx);
  const plan = state.flight ? R.plan : planFlight(day, sectors, flags, state.budget, ctx);
  flags.forEach((f, i) => (f.n = i + 1));
  R = { day, flags, plan, flagOf: Object.fromEntries(flags.map((f) => [f.sector, f])) };
  buildHazardLayer();
}

const fogTarget = (s) => {
  const st = R.day.sectors[s.id];
  return st ? Math.min(1, Math.max(0, (st.sigma_m - 0.12) / 0.3)) : 0;
};

// ---------- canvas ----------
const canvas = $("map");
const g = canvas.getContext("2d");
const view = { scale: 1, ox: 0, oy: 0, dpr: 1, cw: 0, ch: 0 };
const px = ([c, r]) => [view.ox + c * view.scale, view.oy + r * view.scale];

function resize() {
  const r = canvas.parentElement.getBoundingClientRect();
  if (r.width < 4 || r.height < 4) return; // window minimised or not laid out yet
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
  const scale = Math.min(canvas.width / W, canvas.height / H); // whole massif visible
  Object.assign(view, { scale, dpr, cw: canvas.width, ch: canvas.height,
    ox: (canvas.width - W * scale) / 2, oy: (canvas.height - H * scale) / 2 });
  document.querySelector(".scale").style.setProperty("--bar", `${(500 / terrain.cell_m) * scale / dpr}px`);
  buildHazardLayer();
  buildHeatLayer();
  buildWhatIfLayer();
}

function maskCanvas(test) {
  const img = new ImageData(W, H);
  for (let i = 0; i < index.length; i++) {
    const k = index[i];
    if (k && test(sectors[k - 1])) img.data[i * 4 + 3] = 255;
  }
  const c = new OffscreenCanvas(W, H);
  c.getContext("2d").putImageData(img, 0, 0);
  return c;
}

function cellMask(list) {
  const img = new ImageData(W, H), n = W * H;
  for (const idx of list) if (idx < n) img.data[idx * 4 + 3] = 255;
  const c = new OffscreenCanvas(W, H);
  c.getContext("2d").putImageData(img, 0, 0);
  return c;
}

let hazardLayer = null, idleLayer = null, selectLayer = null, unknownLayer = null, envUnion = null, envSelected = null, heatLayer = null;
function scaledLayer(mask, paint) {
  const c = new OffscreenCanvas(view.cw, view.ch);
  const x = c.getContext("2d");
  x.imageSmoothingEnabled = true;
  x.drawImage(mask, view.ox, view.oy, W * view.scale, H * view.scale);
  x.globalCompositeOperation = "source-in";
  paint(x);
  return c;
}
function outlined(mask, color, width, fill) {
  const c = new OffscreenCanvas(view.cw, view.ch);
  const x = c.getContext("2d");
  const fillLayer = scaledLayer(mask, fill);
  const edge = scaledLayer(mask, (y) => { y.fillStyle = color; y.fillRect(0, 0, view.cw, view.ch); });
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-0.7, -0.7], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7]]) {
    x.drawImage(edge, dx * width, dy * width);
  }
  x.globalCompositeOperation = "destination-out";
  x.drawImage(edge, 0, 0);
  x.globalCompositeOperation = "source-over";
  x.drawImage(fillLayer, 0, 0);
  return c;
}

const hatchPattern = (() => {
  const c = new OffscreenCanvas(12, 12);
  const x = c.getContext("2d");
  x.fillStyle = "rgba(232, 89, 12, 0.22)"; x.fillRect(0, 0, 12, 12);
  x.strokeStyle = HAZARD; x.lineWidth = 3.2;
  x.beginPath(); x.moveTo(-3, 15); x.lineTo(15, -3); x.moveTo(-3, 3); x.lineTo(3, -3); x.moveTo(9, 15); x.lineTo(15, 9); x.stroke();
  return c;
})();

function buildHazardLayer() {
  if (!R || !view.cw) return;
  const dpr = view.dpr;
  hazardLayer = outlined(maskCanvas((s) => R.flagOf[s.id]?.kind === "zagrozenie"), HAZARD, 2.2 * dpr,
    (x) => { x.fillStyle = x.createPattern(hatchPattern, "repeat"); x.fillRect(0, 0, view.cw, view.ch); });
  idleLayer = scaledLayer(maskCanvas((s) => !R.flagOf[s.id]),
    (x) => { x.fillStyle = "rgba(120, 72, 30, 0.13)"; x.fillRect(0, 0, view.cw, view.ch); });
  unknownLayer = outlined(maskCanvas((s) => R.flagOf[s.id]?.kind === "nie_wiem"), UNKNOWN, 2.4 * dpr,
    (x) => { x.fillStyle = "rgba(91, 63, 209, 0.10)"; x.fillRect(0, 0, view.cw, view.ch); });
  selectLayer = state.selected
    ? outlined(maskCanvas((s) => s.id === state.selected), INK, 2.6 * dpr, (x) => { x.fillStyle = "rgba(0,0,0,0)"; x.fillRect(0, 0, 1, 1); })
    : null;
  // AvaFrame run-out envelopes: faint union for every hazard flag, a strong one for the selected flag
  const union = new Set();
  for (const f of R.flags) if (f.kind === "zagrozenie" && f.envelope) for (const c of f.envelope) union.add(c);
  // outlined() needs an opaque edge colour; the union is made faint with globalAlpha in draw()
  envUnion = union.size ? outlined(cellMask(union), "#a63b00", 1 * dpr,
    (x) => { x.fillStyle = "rgba(232, 89, 12, 0.22)"; x.fillRect(0, 0, view.cw, view.ch); }) : null;
  const sel = R.flagOf[state.selected]?.envelope;
  envSelected = sel?.length ? outlined(cellMask(sel), "#a63b00", 1.8 * dpr,
    (x) => { x.fillStyle = "rgba(232, 89, 12, 0.32)"; x.fillRect(0, 0, view.cw, view.ch); }) : null;
}

// Library heat: how many of the AvaFrame runs reach each cell (one hue, light to dark).
let heatMax = 0;
async function loadLibraryCells() {
  const [c, h] = await Promise.all([binary("data/scenario_cells.bin", Uint32Array), binary("data/library_heat.bin", Uint16Array)]);
  // footprints only when they belong to this scenarios.json (the library export may be mid-update)
  const need = scenarios?.runs?.reduce((m, r) => Math.max(m, r.cells_offset + r.cells_count), 0) ?? 0;
  cells = c && need && c.length === need ? c : null;
  if (h?.length === W * H) { libHeat = h; heatMax = 0; for (let i = 0; i < h.length; i++) if (h[i] > heatMax) heatMax = h[i]; }
  ctx.cells = cells;
  if (cells && !(state.flight && !state.flight.done)) recompute();
  buildHeatLayer();
  if (shown) { buildWhatIfLayer(); const el = document.getElementById("wi-result"); if (el) el.innerHTML = whatIfText(); }
}
function buildHeatLayer() {
  if (!state.heat || !heatMax || !view.cw) { heatLayer = null; return; }
  const img = new ImageData(W, H);
  for (let i = 0; i < libHeat.length; i++) {
    const v = libHeat[i];
    if (!v) continue;
    const t = Math.sqrt(v / heatMax), o = i * 4;
    img.data[o] = 250 - 110 * t; img.data[o + 1] = 170 - 140 * t; img.data[o + 2] = 60 - 50 * t; img.data[o + 3] = 255 * (0.22 + 0.58 * t);
  }
  const small = new OffscreenCanvas(W, H);
  small.getContext("2d").putImageData(img, 0, 0);
  const c = new OffscreenCanvas(view.cw, view.ch);
  const x = c.getContext("2d");
  x.imageSmoothingEnabled = true;
  x.drawImage(small, view.ox, view.oy, W * view.scale, H * view.scale);
  heatLayer = c;
}
function toggleHeat() {
  state.heat = !state.heat && !!heatMax;
  buildHeatLayer();
  document.getElementById("m-heat")?.classList.toggle("checked", state.heat);
  $("heat-legend").hidden = !state.heat;
  if (state.heat) $("heat-n").textContent = `Zasięgi biblioteki: 1–${heatMax} z ${scenarios?.count?.toLocaleString("pl-PL") ?? "?"} symulacji`;
  if (!heatMax) dlg({ title: "Zasięgi z biblioteki AvaFrame", icon: "i-library", html: "<p>Biblioteka zasięgów jeszcze się liczy. Spróbuj za chwilę.</p>" });
}

// ---------- Sentinel-2 snow cover (real, Copernicus): "Widok › Pokrywa śnieżna z satelity" ----------
// Same 400×400 EPSG:2180 grid as terrain.json (rows from north), so it is drawn exactly like the base map.
const SAT = sentinel?.files?.overlay && sentinel.grid?.width === W && sentinel.grid?.height === H
  && sentinel.grid?.e0 === terrain.e0 && sentinel.grid?.n0 === terrain.n0 ? sentinel : null;
let satImg = null;
if (SAT) {
  const im = new Image();
  im.src = `data/${SAT.files.overlay}`;
  loaded(im).then(() => {
    satImg = im;
    const m = $("m-sat");
    m.hidden = false;
    m.textContent = `Pokrywa śnieżna z satelity (Sentinel-2, ${dmy(SAT.date)})`;
  }).catch(() => {});
}
/** "11.01 chmury nad 100% obszaru, 12.01 brak przelotu, 13.01 chmury nad 86% obszaru" from the JSON. */
function satStormText() {
  const ep = SAT?.episode_cloud_pct_over_area ?? {};
  const dates = Object.keys(ep).sort();
  if (!dates.length) return "";
  const out = [];
  for (let t = Date.parse(dates[0]); t <= Date.parse(dates.at(-1)); t += 864e5) {
    const iso = new Date(t).toISOString().slice(0, 10), v = ep[iso];
    out.push(`${dmy(iso).slice(0, -5)} ${v == null ? "brak przelotu" : `chmury nad ${pl(v)}% obszaru`}`);
  }
  return out.join(", ");
}
function toggleSat() {
  if (!satImg) return;
  state.sat = !state.sat;
  const n = SAT.days_after_episode;
  $("m-sat").classList.toggle("checked", state.sat);
  $("sat-legend").hidden = !state.sat;
  $("sat-n").textContent = `Śnieg z satelity Sentinel-2, ${dmy(SAT.date)}${n ? ` (${n} ${plural(n, "dzień", "dni", "dni")} po zamieci)` : ""}`;
  $("sat-cloud").hidden = !(SAT.cloud_pct_over_area > 0);
  if (!state.sat) return;
  const storm = satStormText();
  xp.balloon({
    title: `Satelita Sentinel-2, ${dmy(SAT.date)}: prawdziwe zdjęcie`, icon: "i-sat", timeout: 10000,
    text: `Pierwszy czysty obraz po zamieci: śnieg na ${pl(SAT.snow_pct, 1)}% obszaru.${storm ? ` W dniach zamieci satelita nie widział terenu: ${storm}.` : ""} Satelita pokazuje, gdzie leży śnieg, a nie jego grubość; grubość płyty musi zmierzyć dron.`,
  });
}

function fogLayer() {
  const img = new ImageData(W, H);
  for (let i = 0; i < index.length; i++) {
    const a = state.fog[index[i]];
    if (a > 0.01) { const o = i * 4; img.data[o] = 255; img.data[o + 1] = 255; img.data[o + 2] = 255; img.data[o + 3] = 255 * a; }
  }
  const small = new OffscreenCanvas(W, H);
  small.getContext("2d").putImageData(img, 0, 0);
  return small;
}

function draw() {
  const { dpr } = view;
  if (!view.cw || !hazardLayer) return;
  g.fillStyle = PAPER; g.fillRect(0, 0, view.cw, view.ch);
  g.imageSmoothingEnabled = true;
  g.drawImage(base, view.ox, view.oy, W * view.scale, H * view.scale);
  if (state.sat && satImg) { g.globalAlpha = 0.85; g.drawImage(satImg, view.ox, view.oy, W * view.scale, H * view.scale); g.globalAlpha = 1; }
  if (idleLayer) g.drawImage(idleLayer, 0, 0);
  if (heatLayer) g.drawImage(heatLayer, 0, 0);
  if (hazardLayer) g.drawImage(hazardLayer, 0, 0);
  if (envUnion) { g.globalAlpha = 0.5; g.drawImage(envUnion, 0, 0); g.globalAlpha = 1; }

  // fog of not knowing: soft white haze, violet edge
  const fog = fogLayer();
  g.save();
  g.filter = `blur(${10 * dpr}px)`;
  for (let i = 0; i < 3; i++) g.drawImage(fog, view.ox, view.oy, W * view.scale, H * view.scale);
  g.filter = `blur(${3 * dpr}px)`;
  g.drawImage(fog, view.ox, view.oy, W * view.scale, H * view.scale);
  g.filter = "none";
  g.restore();
  if (unknownLayer) g.drawImage(unknownLayer, 0, 0);
  if (whatIfLayer) g.drawImage(whatIfLayer, 0, 0);
  else if (envSelected) g.drawImage(envSelected, 0, 0);

  // trails (segments the what-if run reaches with >= 0.5 m of flow get an orange halo)
  for (const id of whatIfSegments()) { const pts = SEGMENT.get(id); if (pts?.length > 1) stroke(pts, "rgba(232, 89, 12, 0.9)", 14 * dpr); }
  for (const t of trails) for (const part of t.paths) {
    stroke(part, "rgba(255,255,255,0.95)", 6 * dpr);
    stroke(part, TRAIL[t.color] ?? TRAIL.red, 3.2 * dpr);
  }
  if (selectLayer) g.drawImage(selectLayer, 0, 0);

  placed = [];
  drawPlaces();
  drawPlan();
  drawBadges();
}

function stroke(pts, color, w, dash) {
  g.save();
  g.strokeStyle = color; g.lineWidth = w; g.lineJoin = "round"; g.lineCap = "round";
  if (dash) { g.setLineDash(dash); g.lineDashOffset = -state.dash; }
  g.beginPath();
  pts.forEach((p, i) => { const [x, y] = px(p); i ? g.lineTo(x, y) : g.moveTo(x, y); });
  g.stroke();
  g.restore();
}

function label(text, x, y, { size = 14, weight = 650, stretch = "87.5%", color = INK, align = "left" } = {}) {
  const { dpr } = view;
  g.font = `${weight} ${stretch} ${size * dpr}px Archivo`;
  g.textAlign = align; g.textBaseline = "middle";
  g.lineJoin = "round"; g.strokeStyle = "rgba(244,239,228,0.92)"; g.lineWidth = 4 * dpr;
  g.strokeText(text, x, y); g.fillStyle = color; g.fillText(text, x, y);
}

let placed = [];
const inside = (r) => r.x >= 4 && r.y >= 4 && r.x + r.w <= view.cw - 4 && r.y + r.h <= view.ch - 4;
const free = (r) => inside(r) && placed.every((q) => r.x > q.x + q.w || r.x + r.w < q.x || r.y > q.y + q.h || r.y + r.h < q.y);

function drawPlaces() {
  const { dpr } = view;
  const flagged = R.flags.map((f) => px(byId[f.sector].centroid));
  for (const p of terrain.places) {
    const [x, y] = px(p.cell);
    if (x < 0 || y < 0 || x > view.cw || y > view.ch) continue;
    g.font = `700 75% ${14 * dpr}px Archivo`;
    const rect = { x: x - 6 * dpr, y: y - 9 * dpr, w: g.measureText(p.name).width + 16 * dpr, h: 18 * dpr };
    if (flagged.some(([fx, fy]) => Math.hypot(fx - x, fy - y) < 60 * dpr)) continue; // flags own that spot
    placed.push(rect);
    g.fillStyle = INK;
    g.beginPath(); g.moveTo(x, y - 5 * dpr); g.lineTo(x + 4.5 * dpr, y + 3 * dpr); g.lineTo(x - 4.5 * dpr, y + 3 * dpr); g.fill();
    label(p.name, x + 8 * dpr, y, { size: 13, weight: 650, stretch: "75%" });
  }
}

function drawPlan() {
  const { dpr } = view;
  const path = R.plan.path;
  const [bx, by] = px(DAYS.base);
  if (path.length > 1 && !state.flight?.done) stroke(path, ROUTE, 3.2 * dpr, [11 * dpr, 8 * dpr]);
  if (state.flight) {
    const f = state.flight;
    const done = pointsUpTo(f.path, f.t * f.len);
    stroke(done, ROUTE, 4 * dpr);
    if (!f.done) drawDrone(...px(done[done.length - 1]));
  }
  // flight base
  g.fillStyle = ROUTE; g.beginPath(); g.arc(bx, by, 11 * dpr, 0, 7); g.fill();
  g.fillStyle = "#fff"; g.font = `800 ${12 * dpr}px Archivo`; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText("H", bx, by + 0.5 * dpr);
  label("Baza: Murowaniec", bx + 16 * dpr, by, { size: 13, weight: 700, color: ROUTE, stretch: "87.5%" });
}

function drawDrone(x, y) {
  const { dpr } = view;
  g.save(); g.translate(x, y);
  g.fillStyle = "rgba(214,0,126,0.18)"; g.beginPath(); g.arc(0, 0, 22 * dpr, 0, 7); g.fill();
  g.strokeStyle = ROUTE; g.lineWidth = 2.5 * dpr;
  g.beginPath(); g.moveTo(-8 * dpr, -8 * dpr); g.lineTo(8 * dpr, 8 * dpr); g.moveTo(8 * dpr, -8 * dpr); g.lineTo(-8 * dpr, 8 * dpr); g.stroke();
  g.fillStyle = ROUTE;
  for (const [a, b] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { g.beginPath(); g.arc(a * 9 * dpr, b * 9 * dpr, 4.5 * dpr, 0, 7); g.fill(); }
  g.fillStyle = "#fff"; g.beginPath(); g.arc(0, 0, 3.5 * dpr, 0, 7); g.fill();
  g.restore();
}

function drawBadges() {
  const { dpr } = view;
  for (const f of R.flags) {
    const s = byId[f.sector];
    const [x, y] = px(s.centroid);
    const color = f.kind === "nie_wiem" ? UNKNOWN : HAZARD;
    const r = (state.selected === s.id ? 14 : 12) * dpr;
    g.save();
    g.shadowColor = "rgba(40,24,8,0.45)"; g.shadowBlur = 8 * dpr; g.shadowOffsetY = 3 * dpr;
    g.fillStyle = color; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    g.restore();
    g.strokeStyle = "#fff"; g.lineWidth = 2.5 * dpr; g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke();
    g.fillStyle = "#fff"; g.font = `800 ${13 * dpr}px Archivo`; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(String(f.n), x, y + 1 * dpr);
    placed.push({ x: x - r, y: y - r, w: 2 * r, h: 2 * r });
    g.font = `700 87.5% ${13.5 * dpr}px Archivo`;
    const tw = g.measureText(s.name).width, th = 18 * dpr;
    const right = { x: x + r + 6 * dpr, y: y - th / 2, w: tw, h: th };
    const left = { x: x - r - 6 * dpr - tw, y: y - th / 2, w: tw, h: th };
    const spot = state.selected === s.id ? right : free(right) ? right : free(left) ? left : null;
    if (spot) {
      placed.push(spot);
      label(s.name, spot.x, y, { size: 13.5, weight: 700, color: f.kind === "nie_wiem" ? UNKNOWN : "#a63b00", stretch: "87.5%" });
    }
  }
}

function pointsUpTo(path, dist) {
  const out = [path[0]];
  let acc = 0;
  for (let i = 1; i < path.length; i++) {
    const seg = Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]);
    if (acc + seg >= dist) {
      const t = (dist - acc) / seg;
      out.push([path[i - 1][0] + (path[i][0] - path[i - 1][0]) * t, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * t]);
      return out;
    }
    acc += seg; out.push(path[i]);
  }
  return out;
}
const pathLength = (p) => p.slice(1).reduce((a, q, i) => a + Math.hypot(q[0] - p[i][0], q[1] - p[i][1]), 0);

// ---------- panel ----------
const NOM = ["zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć"];
const GEN = ["", "jednego", "dwóch", "trzech", "czterech", "pięciu", "sześciu", "siedmiu", "ośmiu", "dziewięciu"];
const cap = (t) => t[0].toUpperCase() + t.slice(1);
const nom = (n) => NOM[n] ?? String(n);
const gen = (n) => GEN[n] ?? String(n);
const mayThreaten = (n) => (n === 1 ? "sektor może" : n >= 2 && n <= 4 ? "sektory mogą" : "sektorów może");
const plural = (n, one, few, many) => (n === 1 ? one : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? few : many);
const counts = () => {
  const nz = R.flags.filter((f) => f.kind === "zagrozenie").length;
  return { nz, nw: R.flags.length - nz };
};
const hazardSentence = (lead) => {
  const { nz } = counts();
  return nz
    ? `${lead ? cap(nom(nz)) : nom(nz)} ${mayThreaten(nz)} zagrozić szlakom.`
    : `${lead ? "Żaden" : "żaden"} sektor nie dostał flagi zagrożenia.`;
};
const FLIGHT_MS = 6500;

function renderSituation() {
  const d = DAYS.days[state.day];
  const { nz, nw } = counts();
  const hz = (lead) => (nz ? `<em>${lead ? cap(nom(nz)) : nom(nz)} ${mayThreaten(nz)}</em> zagrozić szlakom.` : hazardSentence(lead));
  let text;
  if (state.flight?.done) text = `Po przelocie: ${hz(false)} Niepewność nad szlakami spadła o ${R.plan.sigma_drop}%.`;
  else if (nw) text = `<em class="unknown">${cap(gen(nw))} ${nw === 1 ? "sektora" : "sektorów"} nie znamy</em> od ${d.weather.hours_since_flight} h. ${nz ? hz(true) : ""}`;
  else text = hz(true);
  $("summary").innerHTML = text;
  const [day, hour] = d.label.split(", ");
  const rm = realMorning();
  $("stamp").textContent = rm ? `stan na ${hour} · ${longDate(rm.date)}` : `stan na ${hour} · ${day.toLowerCase()}`;
  $("stamp").title = rm ? "Pogoda: IMGW-PIB Kasprowy Wierch (prawdziwe dane). Grubość płyty i przeloty drona: scenariusz syntetyczny." : "";
  // stoki, z których lawina w bibliotece AvaFrame dochodzi do szlaku (docs/12: 48 z 58), not every terrain zone
  const { reach, simulated } = libraryReach();
  const since = state.flight?.done ? "0 h" : `${d.weather.hours_since_flight} h`;
  $("kpis").innerHTML = [
    reach ? [reach, "stoków może sięgnąć szlaku", "", simulated ? `${reach} z ${simulated} stref startowych w bibliotece AvaFrame dochodzi do szlaku (przepływ > 0,1 m)` : ""]
      : [Object.keys(R.day.sectors).length, "stref startowych", ""],
    [nz, "może zagrozić", "hazard"],
    [nw, "nie wiem", "unknown"],
    [since, rm ? `od przelotu · +${pl(rm.new_cm)} cm śniegu w dobę (IMGW)` : `od przelotu · ${d.weather.new_cm} cm śniegu`, ""],
  ].map(([v, l, c, t]) => `<div class="kpi ${c}"${t ? ` title="${t}"` : ""}><b>${v}</b><span>${l}</span></div>`).join("");
  renderSources();
}

function flightStatus() {
  const d = DAYS.days[state.day];
  return state.flight && !state.flight.done ? ["air", "w powietrzu"]
    : state.flight?.done ? ["ok", "wykonany w oknie pogodowym"]
    : d.flight.flown ? ["ok", "wykonany o 6:00"] : ["off", "odwołany, śnieżyca"];
}

function renderSources() {
  const [st, text] = flightStatus();
  const REAL = `<b class="tag real">prawdziwe</b>`, SYN = `<b class="tag syn">syntetyczne</b>`;
  const lib = scenarios?.count ? `${scenarios.count.toLocaleString("pl-PL")} symulacji com1DFA` : "w budowie";
  const src = (icon, dt, tag, dd) => `<div><svg aria-hidden="true"><use href="#${icon}"/></svg><dl><dt>${dt} ${tag}</dt><dd>${dd}</dd></dl></div>`;
  const terrainSrc = src("i-mountain", "Teren GUGiK NMT", REAL, `siatka ${terrain.cell_m} m, nachylenia i strefy`);
  const trailSrc = src("i-trail", "Szlaki OSM", REAL, "w prawdziwych kolorach szlaków");
  const imgwSrc = src("i-network", "IMGW Kasprowy", KW ? REAL : "",
    `${KW ? `<button class="link" data-open="w-imgw" title="Otwórz wykres zimy 2024/25">archiwum 2024/25</button> · teraz ` : ""}<span id="live">łączę…</span>`);
  const libSrc = src("i-library", "Biblioteka AvaFrame", scenarios?.count ? `<b class="tag real">policzona</b>` : "", `${lib}${scenarios?.count ? " · DGX Spark" : ""}`);
  const synSrc = src("i-drone", "Płyta, przeloty", SYN, `<span class="${st === "ok" ? "" : "warn"}">przelot ${text}</span>`);
  // With the satellite the panel keeps two rows of three (the Sytuacja window has no room for a third):
  // the GUGiK orthophoto joins the terrain cell, and the top row holds only one-line entries.
  $("sources").innerHTML = (SAT ? [
    src("i-mountain", "Teren GUGiK", REAL, `NMT ${terrain.cell_m} m · ortofoto w 3D`), trailSrc,
    src("i-sat", "Satelita Sentinel-2", REAL,
      `<button class="link" data-action="sat-snow" title="Pokaż na mapie. ${SAT.credit}. Satelita pokazuje, gdzie leży śnieg, a nie jego grubość.">śnieg ${dmy(SAT.date)}</button> · <span title="W dniach zamieci satelita nie widział terenu: ${satStormText()}">po zamieci</span>`),
    imgwSrc, libSrc, synSrc,
  ] : [terrainSrc, src("i-desktop", "Ortofoto GUGiK", REAL, "tekstura renderów 3D"), trailSrc, imgwSrc, libSrc, synSrc]).join("");
  xp.setTray("drone", { state: st, title: `Przelot drona: ${text}` });
  paintLive();
}

function renderDays() {
  document.querySelectorAll(".tab.day").forEach((b) => {
    const d = DAYS.days[+b.dataset.day];
    const [day, hour] = d.label.split(", ");
    b.innerHTML = `<b>${day} · ${hour}</b><small>${d.status}</small>`;
    b.setAttribute("aria-selected", String(+b.dataset.day === state.day));
  });
  document.querySelectorAll(".check-day").forEach((b) => b.classList.toggle("checked", +b.dataset.day === state.day));
}

function renderRows() {
  const body = $("rows");
  body.innerHTML = "";
  const n = R.flags.length;
  $("sec-count").textContent = `${n} ${plural(n, "obiekt", "obiekty", "obiektów")}`;
  if (!n) {
    body.innerHTML = `<tr class="empty"><td colspan="7">Brak flag. To nie zielone światło: decyzję podejmuje prognosta.</td></tr>`;
    $("why").textContent = "";
    return;
  }
  R.flags.forEach((f, i) => {
    const s = byId[f.sector], st = R.day.sectors[f.sector];
    const tr = document.createElement("tr");
    tr.className = `${f.kind}${state.selected === f.sector ? " selected" : ""}`;
    tr.style.setProperty("--i", i);
    const age = st.hours_since_measured;
    tr.innerHTML = `<td class="c-n"><svg aria-hidden="true"><use href="#${f.kind === "nie_wiem" ? "i-question" : "i-warn"}"/></svg><span class="n">${f.n}</span></td>
      <td class="name"><b>${s.name}</b></td>
      <td class="kind">${f.kind === "nie_wiem" ? "Nie wiem" : "Może zagrozić szlakowi"}</td>
      <td class="num">${Math.round(st.dhs_m * 100)} cm</td>
      <td class="num">±${Math.round(st.sigma_m * 100)} cm</td>
      <td class="num ${age > 12 ? "stale" : ""}">${age} h</td>
      <td class="trail" title="${f.trails.join(", ")}">${f.trails.join(", ")}</td>`;
    tr.addEventListener("click", () => select(f.sector, { toggle: false }));
    body.appendChild(tr);
  });
  const f = R.flagOf[state.selected] ?? R.flags[0];
  const analogs = f.analogs ? ` ${f.analogs_hitting} z ${f.analogs} podobnych scenariuszy dochodzi do szlaku.` : "";
  const film = hasVideo(f.sector) ? ` <button class="link" data-action="player-sel" title="Animacja 3D przebiegu AvaFrame dla tego sektora">Pokaż lawinę w 3D</button>` : "";
  $("why").innerHTML = `<b>${f.n}. ${byId[f.sector].name}:</b> ${f.reason}${analogs}${film}`;
}

function renderPlan() {
  const p = R.plan;
  $("budget-out").textContent = `${state.budget} min`;
  $("plan-kpis").innerHTML = p.route.length
    ? `<div><b>${p.route.length}</b><span>sektorów do zmierzenia</span></div><div><b>${p.minutes} min</b><span>lotu z powrotem</span></div><div><b class="gain">${p.sigma_drop > 0 ? "−" : ""}${p.sigma_drop}%</b><span>niepewności nad szlakami</span></div>`
    : `<div><b>0</b><span>za mało czasu na dolot i powrót</span></div>`;
  $("route").innerHTML = p.route.map((id) => `<li class="${state.visited.has(id) ? "done" : ""}" title="${byId[id].name}">${byId[id].name}</li>`).join("");
  const fly = $("fly");
  const d = DAYS.days[state.day];
  fly.disabled = !p.route.length || (state.flight && !state.flight.done);
  const label = state.flight?.done ? "Wyczyść i zaplanuj od nowa"
    : state.flight ? "Dron w powietrzu…"
    : d.flight.flown ? "Wykonaj przelot" : "Wykonaj przelot w pierwszym oknie pogodowym";
  fly.innerHTML = `<svg aria-hidden="true"><use href="#i-drone"/></svg><span>${label}</span>`;
}

/** Library coverage: zones with computed AvaFrame runs, and those whose runs reach a trail (days.json exposure). */
function libraryReach() {
  return { reach: Object.keys(DAYS.exposure ?? {}).length, simulated: scenarios?.sectors?.length ?? 0 };
}

function factParts() {
  const { reach, simulated } = libraryReach();
  const zones = "stref startowych wyznaczonych z terenu GUGiK NMT (nachylenie 28–55°, powyżej 1600 m)";
  const parts = [simulated ? `Strefy startowe wyznaczone z terenu GUGiK NMT (nachylenie 28–55°, powyżej 1600 m): <strong>${simulated}</strong> w pobliżu szlaków ma policzone scenariusze lawin.`
    : `<strong>${sectors.length}</strong> ${zones}.`];
  if (scenarios?.count) parts.push(`<strong>${scenarios.count.toLocaleString("pl-PL")}</strong> scenariuszy lawin AvaFrame policzonych z góry${reach && simulated ? `; <strong>${reach}</strong> z ${simulated} stref może zrzucić lawinę na szlak` : ""}.`);
  const cal = calibration?.best;
  if (cal?.iou != null && cal.runout_error_m != null) {
    parts.push(`Przykładowa kalibracja na prawdziwym zdarzeniu z Austrii (Popeletzbach): AvaFrame trafia zasięg obserwowanej lawiny z IoU ${pl(cal.iou, 2)}, błąd długości zasięgu ${cal.runout_error_m > 0 ? "+" : ""}${pl(cal.runout_error_m)} m.`);
  }
  if (cells) parts.push("Na mapie: zasięgi tych symulacji, które z danego sektora dochodzą do szlaku.");
  const rm = realMorning();
  const top = KW?.episodes?.length ? KW.episodes.reduce((a, e) => (e.new_cm_3d > a.new_cm_3d ? e : a)) : null;
  if (rm && top) parts.push(`Pogoda: prawdziwy poranek ${dmy(rm.date)} z IMGW Kasprowy Wierch, w środku śnieżycy ${top.label.split(": ")[0]} (+${top.new_cm_3d} cm w 3 dni, zamieć ${pl(top.blowing_h_3d)} h). Grubość płyty i przeloty drona: scenariusz syntetyczny.`);
  if (!real) parts.push("Silnik tymczasowy, dane udawane.");
  return parts;
}
function renderFacts() { $("library").innerHTML = factParts().join(" "); }

function renderAll() { renderDays(); renderSituation(); renderRows(); renderPlan(); renderFacts(); renderPlayer(); }

function select(id, { toggle = true, explain = true } = {}) {
  state.selected = toggle && state.selected === id ? null : id;
  buildHazardLayer(); renderRows();
  if (explain && state.selected && R.flagOf[state.selected]) explainFlag(R.flagOf[state.selected]);
}

function explainFlag(f) {
  const s = byId[f.sector], st = R.day.sectors[f.sector];
  const unknown = f.kind === "nie_wiem";
  const analogs = f.analogs ? `<p>${f.analogs_hitting} z ${f.analogs} podobnych scenariuszy dochodzi do szlaku.${f.envelope?.length ? " Ich zasięg jest zaznaczony na mapie na pomarańczowo." : ""}</p>` : "";
  const inPlan = R.plan.route.includes(f.sector);
  const withLib = RUNS.size > 0;
  xp.msgbox({
    id: "flag-dialog", title: `${f.n}. ${s.name}`, icon: unknown ? "i-question" : "i-warn", className: withLib ? "flag-detail" : "",
    html: `<div class="fd-text"><h3>${unknown ? "Nie wiem" : "Może zagrozić szlakowi"}</h3>
      <p>${f.reason}</p>${analogs}
      <p>Szlak: <b>${f.trails.join(", ")}</b><br>${s.band} · ΔHS ${Math.round(st.dhs_m * 100)} cm · σ ±${Math.round(st.sigma_m * 100)} cm · pomiar ${st.hours_since_measured} h temu</p>
      <p>${inPlan ? "Sektor jest w planie przelotu." : "Sektora nie ma w obecnym planie przelotu."}${unknown ? " Pomiar z drona zamieni „nie wiem” w liczbę." : ""}</p></div>
      ${withLib ? whatIfForm(f, snapTh(f.h_m ?? 1)) : ""}`,
    buttons: unknown && inPlan && !state.flight
      ? [{ label: "Wykonaj przelot", value: "fly" }, { label: "OK", value: true, default: true }]
      : [{ label: "OK", value: true, default: true }],
    near: xp.windowRect("w-sit"),
  }).then((v) => { if (v === "fly") startFlight(); });
  wireWhatIf(document.getElementById("flag-dialog"), f.sector);
}

// ---------- "Co jeśli płyta ma X m?": one real AvaFrame run from the library, drawn on the map ----------
const THS = [0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0];
const FRICTS = [["samosATSmall", "małe lawiny"], ["samosATMedium", "średnie"], ["samosAT", "duże"]];
const FRICT_PL = { samosATSmall: "tarcie dla małych lawin", samosATMedium: "tarcie dla średnich lawin", samosAT: "tarcie dla dużych lawin" };
const snapTh = (x) => THS.reduce((a, t) => (Math.abs(t - x) < Math.abs(a - x) ? t : a));
const cm = (m) => Math.round(m * 100);
let whatIfLayer = null;

function whatIfForm(f, th0) {
  const frac = (x) => (Math.min(2, Math.max(0.4, x)) - 0.4) / 1.6;
  const band = f.range_m
    ? `<i class="wi-band" style="left: calc(6.5px + ${frac(f.range_m[0]).toFixed(3)} * (100% - 13px)); width: calc(${(frac(f.range_m[1]) - frac(f.range_m[0])).toFixed(3)} * (100% - 13px) + 2px)"></i>`
    : "";
  return `<fieldset class="group whatif">
      <legend>Co jeśli płyta ma <output id="wi-out">${pl(th0, 1)} m</output>?</legend>
      <div class="trackbar">${band}
        <input id="wi-th" type="range" min="2" max="10" step="1" value="${Math.round(th0 / 0.2)}" aria-label="Grubość płyty w metrach">
        <div class="ticks" aria-hidden="true">${THS.map((t) => `<span>${pl(t, 1)}</span>`).join("")}</div>
      </div>
      ${f.range_m ? `<p class="wi-today"><i class="wi-swatch"></i>Szacunek płyty na ten poranek: ${cm(f.range_m[0])}–${cm(f.range_m[1])} cm (syntetyczny)</p>` : ""}
      <div class="wi-frict" role="radiogroup" aria-label="Tarcie w modelu AvaFrame">Tarcie:
        ${FRICTS.map(([k, l]) => `<label class="xp-radio" title="${FRICT_PL[k]} (kalibracja AvaFrame)"><input type="radio" name="wi-fr" value="${k}"${k === "samosATMedium" ? " checked" : ""}>${l}</label>`).join("")}
      </div>
      <div class="wi-result" id="wi-result" aria-live="polite"></div>
      <p class="wi-src">Prawdziwe przebiegi AvaFrame z biblioteki (${(scenarios?.count ?? RUNS.size).toLocaleString("pl-PL")} symulacji)</p>
      <button class="xp-btn wi-3d" id="wi-3d" type="button"><svg aria-hidden="true"><use href="#i-player"/></svg>Pokaż lawinę w 3D</button>
    </fieldset>`;
}

function wireWhatIf(el, sector) {
  const range = el?.querySelector("#wi-th");
  if (!range) return;
  const update = () => {
    const th = Math.round(+range.value * 2) / 10;
    const frict = el.querySelector('input[name="wi-fr"]:checked')?.value ?? "samosATMedium";
    setWhatIf({ sector, th, frict });
    el.querySelector("#wi-out").textContent = `${pl(th, 1)} m`;
    el.querySelector("#wi-result").innerHTML = whatIfText();
    const v = videoFor(sector, th, frict), b = el.querySelector("#wi-3d");
    b.disabled = !v;
    b.title = v ? `Film 3D: płyta ${pl(v.relTh, 1)} m, ${FRICT_PL[v.frict]}` : "Brak filmu 3D dla tego sektora";
  };
  range.addEventListener("input", update);
  el.querySelectorAll('input[name="wi-fr"]').forEach((i) => i.addEventListener("change", update));
  el.querySelector("#wi-3d").addEventListener("click", () => {
    const w = state.whatIf;
    if (!w) return;
    el.querySelector(".buttons .default")?.click(); // close the dialog like OK: it would cover the player
    openPlayer(w.sector, w.th, w.frict); // the map then shows the library run of the film being played
  });
  update();
}

const runOf = (w) => (w ? RUNS.get(runKey(w.sector, w.frict, w.th)) ?? null : null);
const whatIfRun = () => runOf(state.whatIf);
const whatIfSegments = () => { const r = runOf(shown); return r ? hitSegments(r) : []; };

// The run on the map: the dialog's slider while the flag dialog is open, otherwise the film playing in the
// 3D player (its com1DFA run is the library run with the same sector, slab and friction, recomputed with time steps).
let shown = null, shownKey = "";
function activeWhatIf() {
  if (state.whatIf && document.getElementById("flag-dialog")) return { ...state.whatIf, from: "dialog" };
  const v = player.cur;
  if (v && !player.el.classList.contains("is-hidden") && RUNS.has(runKey(v.sector, v.frict, v.relTh))) return { sector: v.sector, th: v.relTh, frict: v.frict, from: "player" };
  return null;
}
function syncWhatIf() {
  const w = activeWhatIf();
  const k = w ? `${runKey(w.sector, w.frict, w.th)}|${w.from}` : "";
  if (k === shownKey) return;
  shown = w; shownKey = k;
  buildWhatIfLayer();
  $("whatif-legend").hidden = !w;
  if (w) $("whatif-n").textContent = `${w.from === "player" ? "Film 3D" : "Co jeśli"}: ${byId[w.sector].name}, płyta ${pl(w.th, 1)} m (przebieg AvaFrame)`;
}
function setWhatIf(w) { state.whatIf = w; syncWhatIf(); }

function buildWhatIfLayer() {
  const r = runOf(shown);
  if (!r || !cells || !view.cw) { whatIfLayer = null; return; }
  whatIfLayer = outlined(cellMask(cells.subarray(r.cells_offset, r.cells_offset + r.cells_count)), "#6b1d00", 2.2 * view.dpr,
    (x) => { x.fillStyle = "rgba(166, 59, 0, 0.46)"; x.fillRect(0, 0, view.cw, view.ch); });
}

function whatIfText() {
  const r = whatIfRun();
  if (!r) return "Tego przebiegu nie ma w bibliotece.";
  const segs = hitSegments(r);
  const byTrail = new Map(); // trail id -> peak flow on its segments
  for (const id of segs) {
    const t = id.split("-")[0], v = r.hits_pft_m?.[r.hits.indexOf(id)] ?? 0;
    byTrail.set(t, Math.max(byTrail.get(t) ?? 0, v));
  }
  const top = [...byTrail].sort((a, b) => b[1] - a[1]);
  const flow = top[0]?.[1] ?? 0;
  const names = top.slice(0, 2).map(([t]) => TRAIL_NAME[t] ?? t).join("; ") + (top.length > 2 ? ` i ${top.length - 2} ${plural(top.length - 2, "inny", "inne", "innych")}` : "");
  const reach = segs.length
    ? `<b class="hit">Dochodzi do szlaku</b> z przepływem do ${pl(flow, 1)} m: <b>${names}</b>`
    : r.hits?.length ? "Dotyka szlaku, ale przepływ na nim nie przekracza 0,5 m."
    : "Nie dochodzi do szlaku z przepływem ≥ 0,5 m.";
  return `Zasięg <b>${pl(r.runout_m)} m</b> · ${pl(r.area_ha, 1)} ha<br>${reach}`
    + (cells ? "" : "<br><i>Obrys na mapie: wczytuję bibliotekę zasięgów…</i>");
}

// ---------- Odtwarzacz 3D: animations of AvaFrame runs for the flagged sectors ----------
const VIDEOS = (media3d?.videos ?? []).filter((v) => byId[v.sector] && v.file);
const FRICT_SHORT = { samosATSmall: "tarcie: małe", samosATMedium: "tarcie: średnie", samosAT: "tarcie: duże" };
const player = { el: $("w-player"), video: $("pl-video"), cur: null, list: [], seeking: false };
const mmss = (t) => { const s = Math.max(0, Math.floor(t || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
const hasVideo = (sector) => VIDEOS.some((v) => v.sector === sector);

/** The video closest to a slab thickness (default: this morning's estimate) and friction (default: medium). */
function videoFor(sector, th = null, frict = null) {
  const list = VIDEOS.filter((v) => v.sector === sector);
  if (!list.length) return null;
  const t = th ?? R.flagOf[sector]?.h_m ?? 1;
  const cost = (v) => Math.abs(v.relTh - t) + (v.frict === (frict ?? "samosATMedium") ? 0 : 0.35);
  return list.reduce((a, v) => (cost(v) < cost(a) ? v : a));
}

function playlist() {
  const order = R.flags.map((f) => f.sector).filter(hasVideo);
  for (const v of VIDEOS) if (!order.includes(v.sector)) order.push(v.sector);
  const rank = (v) => (v.frict === "samosATMedium" ? 0 : 1);
  return order.flatMap((id) => VIDEOS.filter((v) => v.sector === id).sort((a, b) => rank(a) - rank(b) || a.relTh - b.relTh));
}

function openPlayer(sector = null, th = null, frict = null) {
  if (!VIDEOS.length) {
    dlg({ title: "Odtwarzacz 3D — scenariusz AvaFrame", icon: "i-player", html: "<p>W tej kopii demo nie ma filmów 3D (web/media/3d/).</p>" });
    return;
  }
  const id = sector ?? (R.flagOf[state.selected] ? state.selected : null) ?? R.flags.find((f) => hasVideo(f.sector))?.sector ?? VIDEOS[0].sector;
  xp.open("w-player");
  const v = videoFor(id, th, frict);
  if (v) playVideo(v);
  else {
    player.cur = null; player.video.pause(); player.video.removeAttribute("src"); player.video.removeAttribute("poster"); player.video.load();
    $("pl-empty").hidden = false;
    $("pl-empty").textContent = `Dla sektora ${byId[id]?.name ?? id} nie ma jeszcze filmu 3D. Wybierz scenariusz z listy.`;
    renderPlayer();
  }
}

function playVideo(v) {
  const vid = player.video;
  player.cur = v;
  $("pl-empty").hidden = true;
  vid.poster = `media/3d/${v.poster}`;
  vid.src = `media/3d/${v.file}`;
  vid.play().catch(() => {});
  renderPlayer();
  paintSeek();
}

function renderPlayer() {
  if (!player.el) return;
  const v = player.cur;
  player.list = playlist();
  $("pl-list").innerHTML = player.list.map((x, i) => {
    const f = R.flagOf[x.sector];
    const near = f && videoFor(x.sector) === x;
    return `<li><button type="button" data-i="${i}" aria-current="${x === v}">
      <span class="pl-n">${f ? `<i class="n${f.kind === "nie_wiem" ? " unknown" : ""}">${f.n}</i>` : ""}</span><span class="pl-t">${byId[x.sector].name}</span><span class="pl-d">${mmss(x.duration_s)}</span>
      <small>${pl(x.relTh, 1)} m · ${FRICT_SHORT[x.frict] ?? x.frict}${near ? ` <b class="near" title="Najbliżej szacunku płyty na ten poranek">≈ dziś</b>` : ""}</small></button></li>`;
  }).join("");
  if (!v) { $("pl-caption").innerHTML = `<p><b>Odtwarzacz 3D</b></p><p class="sub">AvaFrame com1DFA, teren GUGiK, śnieg: scenariusz syntetyczny</p>`; $("pl-now").textContent = ""; return; }
  const s = byId[v.sector], f = R.flagOf[v.sector];
  const pill = f ? ` <span class="pill ${f.kind}">${f.n}. ${f.kind === "nie_wiem" ? "Nie wiem" : "Może zagrozić szlakowi"}</span>` : "";
  const today = f?.range_m ? ` · płyta na ten poranek ${cm(f.range_m[0])}–${cm(f.range_m[1])} cm` : "";
  $("pl-caption").innerHTML = `<p><b>Lawina: ${s.name}</b> · płyta ${pl(v.relTh, 1)} m · ${FRICT_PL[v.frict] ?? v.frict}${pill}</p>
    <p class="sub">AvaFrame com1DFA, teren GUGiK, śnieg: scenariusz syntetyczny${today}</p>`;
  $("pl-now").textContent = `${s.name} · ${pl(v.relTh, 1)} m`;
}

function paintSeek() {
  const vid = player.video, seek = $("pl-seek");
  const d = Number.isFinite(vid.duration) ? vid.duration : player.cur?.duration_s ?? 0, t = vid.currentTime || 0;
  if (!player.seeking) seek.value = d ? Math.round((t / d) * 1000) : 0;
  seek.style.setProperty("--p", `${seek.value / 10}%`);
  $("pl-time").textContent = `${mmss(t)} / ${mmss(d)}`;
}

if (player.el) {
  const vid = player.video, seek = $("pl-seek");
  const status = (t) => { $("pl-status").textContent = t; };
  $("pl-play").addEventListener("click", () => { if (!player.cur) { openPlayer(); return; } vid.paused ? vid.play().catch(() => {}) : vid.pause(); });
  $("pl-stop").addEventListener("click", () => { vid.pause(); vid.currentTime = 0; paintSeek(); status("Zatrzymano"); });
  const step = (k) => {
    const L = player.list;
    if (!L.length) return;
    const i = L.indexOf(player.cur);
    playVideo(L[(i < 0 ? 0 : i + k + L.length) % L.length]);
  };
  $("pl-prev").addEventListener("click", () => step(-1));
  $("pl-next").addEventListener("click", () => step(1));
  $("pl-list").addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (b) playVideo(player.list[+b.dataset.i]); });
  seek.addEventListener("input", () => {
    player.seeking = true;
    const d = vid.duration;
    if (Number.isFinite(d) && d > 0) vid.currentTime = (seek.value / 1000) * d;
    paintSeek();
  });
  seek.addEventListener("change", () => { player.seeking = false; });
  for (const ev of ["play", "playing", "pause", "ended"]) vid.addEventListener(ev, () => {
    const on = !vid.paused;
    player.el.classList.toggle("playing", on);
    $("pl-play").setAttribute("aria-label", on ? "Wstrzymaj" : "Odtwórz");
    if (player.cur) status(on ? `Odtwarzanie: ${byId[player.cur.sector].name}, płyta ${pl(player.cur.relTh, 1)} m` : "Wstrzymano");
  });
  vid.addEventListener("waiting", () => status("Wczytywanie…"));
  vid.addEventListener("timeupdate", () => {
    paintSeek();
    // a "waiting" stall (loop restart, slow disk) is not always followed by "playing"
    if (!vid.paused && player.cur && $("pl-status").textContent === "Wczytywanie…") status(`Odtwarzanie: ${byId[player.cur.sector].name}, płyta ${pl(player.cur.relTh, 1)} m`);
  });
  vid.addEventListener("loadedmetadata", paintSeek);
  vid.addEventListener("error", () => { if (player.cur) status(`Nie udało się wczytać filmu ${player.cur.file}`); });
  vid.addEventListener("click", () => $("pl-play").click());
  // a hidden player (closed, minimised) never plays on in the background
  new MutationObserver(() => { if (player.el.classList.contains("is-hidden")) vid.pause(); })
    .observe(player.el, { attributes: true, attributeFilter: ["class"] });
}

function recompute() { compute(); renderAll(); }

function setDay(n) {
  copy?.close(); copy = null;
  document.getElementById("flag-dialog")?.remove();
  state.day = n; state.selected = null; state.visited.clear(); state.flight = null;
  recompute();
  drawChart();
  try { history.replaceState(null, "", n === 1 ? "?day=2" : location.pathname); } catch {}
  announceDay();
}

function announceDay() {
  xp.clearBalloons();
  const d = DAYS.days[state.day];
  const { nw } = counts();
  if (d.flight.flown) xp.balloon({ title: "Przelot wykonany o 6:00", text: `${d.label.replace(", ", ", stan na ")}. ${hazardSentence(true)}`, icon: "i-drone" });
  else {
    const rm = realMorning();
    xp.balloon({
      title: "Przelot odwołany: śnieżyca", icon: "i-badge-warn",
      text: rm ? `Ostatni przelot ${d.weather.hours_since_flight} h temu. Kasprowy Wierch (IMGW), ${dmy(rm.date)}: +${pl(rm.new_cm)} cm śniegu w dobę, ${pl(rm.new3)} cm w 3 dni, zamieć ${pl(rm.blowing_h)} h.`
        : `Ostatni przelot ${d.weather.hours_since_flight} h temu, od tego czasu ${d.weather.new_cm} cm śniegu.`,
    });
  }
  if (nw) xp.balloon({ title: `${nw} ${plural(nw, "sektor", "sektory", "sektorów")}: Nie wiem`, text: "Mgła niewiedzy na mapie. Plan przelotu wskazuje, gdzie polecieć, żeby się dowiedzieć.", icon: "i-question" });
}

// ---------- interaction ----------
function canvasPoint(ev) {
  const r = canvas.getBoundingClientRect();
  return [(ev.clientX - r.left) * view.dpr, (ev.clientY - r.top) * view.dpr];
}
function sectorAt(ev) {
  const [x, y] = canvasPoint(ev);
  const c = Math.floor((x - view.ox) / view.scale), row = Math.floor((y - view.oy) / view.scale);
  if (c < 0 || row < 0 || c >= W || row >= H) return null;
  const k = index[row * W + c];
  return k ? sectors[k - 1] : null;
}
function badgeAt(ev) {
  const [x, y] = canvasPoint(ev);
  return R.flags.find((f) => { const [bx, by] = px(byId[f.sector].centroid); return Math.hypot(bx - x, by - y) < 15 * view.dpr; }) ?? null;
}
canvas.addEventListener("mousemove", (ev) => {
  const badge = badgeAt(ev);
  const s = badge ? byId[badge.sector] : sectorAt(ev), tip = $("tooltip");
  canvas.style.cursor = badge ? "pointer" : "crosshair";
  if (!s) { tip.hidden = true; return; }
  const f = R.flagOf[s.id];
  tip.hidden = false;
  tip.textContent = `${s.name} · ${s.band}${f ? (f.kind === "nie_wiem" ? " · nie wiem" : " · może zagrozić szlakowi") : ""}`;
  const r = canvas.parentElement.getBoundingClientRect();
  const x = Math.min(ev.clientX - r.left + 16, r.width - tip.offsetWidth - 4);
  tip.style.left = `${Math.max(4, x)}px`; tip.style.top = `${ev.clientY - r.top + 18}px`;
});
canvas.addEventListener("mouseleave", () => { $("tooltip").hidden = true; });
canvas.addEventListener("click", (ev) => {
  const badge = badgeAt(ev);
  if (badge) { select(badge.sector, { toggle: false }); return; }
  select(sectorAt(ev)?.id ?? null);
});

document.querySelectorAll(".tab.day").forEach((b) => b.addEventListener("click", () => setDay(+b.dataset.day)));
$("budget").addEventListener("input", (e) => {
  state.budget = +e.target.value;
  if (state.flight) { copy?.close(); copy = null; state.flight = null; state.visited.clear(); }
  recompute();
});

let copy = null;
function resetFlight() { copy?.close(); copy = null; state.flight = null; state.visited.clear(); recompute(); }
function startFlight() {
  if (state.flight && !state.flight.done) { xp.open("w-map"); return; }
  if (state.flight?.done) resetFlight();
  if (!R.plan.route.length) return;
  const path = R.plan.path;
  state.flight = { path, len: pathLength(path), t: 0, done: false, route: [...R.plan.route] };
  document.getElementById("flag-dialog")?.remove();
  xp.clearBalloons();
  xp.open("w-map");
  renderPlan(); renderSources();
  const n = state.flight.route.length;
  copy = xp.copyDialog({
    title: "Przesyłanie pomiarów z drona…", from: "i-mountain", to: "i-folder",
    line1: `Przesyłanie pomiarów z drona: ${n} ${plural(n, "sektor", "sektory", "sektorów")}`,
    near: xp.windowRect("w-plan"),
    onCancel: () => { copy = null; resetFlight(); xp.balloon({ title: "Przelot przerwany", text: "Pomiary z tego przelotu nie zostały zapisane.", icon: "i-badge-warn" }); },
  });
  stepCopy();
}
$("fly").addEventListener("click", () => { if (state.flight?.done) resetFlight(); else startFlight(); });

function stepCopy() {
  const f = state.flight;
  if (!copy || !f) return;
  const next = f.route.find((id) => !state.visited.has(id));
  copy.update(f.t, next ? `Z: ${byId[next].name} · do: Baza Murowaniec` : "Powrót do bazy: Murowaniec",
    `Pozostało około ${Math.max(1, Math.ceil(((1 - f.t) * FLIGHT_MS) / 1000))} s`);
}

function stepFlight(dt) {
  const f = state.flight;
  if (!f || f.done) return;
  f.t = Math.min(1, f.t + dt / FLIGHT_MS);
  const here = pointsUpTo(f.path, f.t * f.len).at(-1);
  for (const id of f.route) {
    if (state.visited.has(id)) continue;
    const c = byId[id].centroid;
    if (Math.hypot(c[0] - here[0], c[1] - here[1]) < 6) { state.visited.add(id); compute(); renderSituation(); renderRows(); renderPlan(); }
  }
  stepCopy();
  if (f.t >= 1) {
    f.done = true; recompute();
    copy?.close(); copy = null;
    const n = f.route.length;
    xp.balloon({
      title: `Przelot zakończony: niepewność −${R.plan.sigma_drop}%`,
      text: `Zmierzono ${n} ${plural(n, "sektor", "sektory", "sektorów")}. Po przelocie: ${hazardSentence(false)}`,
      icon: "i-drone",
    });
  }
}

// ---------- live Kasprowy Wierch (IMGW) and offline mode ----------
// sw.js answers the IMGW request from its cache when the network is gone and marks it
// with X-Avalauncher-Cache, so a cached reading is never painted as live.
// "Symuluj awarię łączności" blocks every live request inside the app; the map, the
// library, the flight plan and the 2024/25 archive keep running from the cache.
const LIVE_URL = "https://danepubliczne.imgw.pl/api/data/synop/station/kasprowywierch";
const LIVE_KEY = "avalauncher.kasprowy";
const SIM_KEY = "avalauncher.simOffline";
let liveState = null;
let warnedOffline = false;
let simOffline = false;
try { simOffline = sessionStorage.getItem(SIM_KEY) === "1"; } catch {}
const liveFetch = (url, init) => (simOffline || !navigator.onLine
  ? Promise.reject(new TypeError(simOffline ? "Symulowana awaria łączności" : "Brak sieci"))
  : fetch(url, init));

/** When IMGW measured it: data_pomiaru + godzina_pomiaru are UTC. */
function readingAt(d) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d?.data_pomiaru ?? "");
  const t = m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +d.godzina_pomiaru) : NaN;
  return Number.isFinite(t) ? t : null;
}
function ago(ms) {
  const min = Math.max(0, Math.round(ms / 60000));
  return min < 60 ? `${Math.max(1, min)} min temu` : `${Math.round(min / 60)} h temu`;
}
function cachedReading() {
  try { return JSON.parse(localStorage.getItem(LIVE_KEY)); } catch { return null; }
}
const readingAge = (c) => (c?.d ? ago(Date.now() - (readingAt(c.d) ?? c.at)) : null);
const num = (v, k = 0) => (v == null || v === "" || !Number.isFinite(+v) ? "—" : pl(+v, k));
const fmtReading = (d) => `${num(d.temperatura, 1)} °C · ${num(d.predkosc_wiatru)} m/s`;

async function live() {
  try {
    const r = await liveFetch(LIVE_URL, { cache: "no-store" });
    if (!r.ok) throw new Error(`IMGW ${r.status}`);
    const d = await r.json();
    const cachedAt = r.headers.get("x-avalauncher-cache");
    if (cachedAt) { // the network is down and sw.js answered with the last reading it kept
      const mine = cachedReading();
      const c = (readingAt(mine?.d) ?? 0) >= (readingAt(d) ?? 0) ? mine : { d, at: Number(cachedAt) || Date.now() };
      return goOffline(c);
    }
    try { localStorage.setItem(LIVE_KEY, JSON.stringify({ d, at: Date.now() })); } catch {}
    liveState = { ok: true, d };
    warnedOffline = false;
  } catch {
    return goOffline(cachedReading());
  }
  paintLive();
}
function goOffline(c) {
  liveState = { ok: false, c };
  if (!warnedOffline) { warnedOffline = true; offlineBalloon(); }
  paintLive();
}
function offlineBalloon() {
  const age = readingAge(liveState?.c ?? cachedReading());
  const lib = scenarios?.count ? `biblioteka ${scenarios.count.toLocaleString("pl-PL")} symulacji` : "biblioteka scenariuszy";
  xp.balloon({
    title: "Brak łączności — pracuję na danych z pamięci podręcznej",
    text: `${age ? `Ostatni odczyt IMGW: ${age}.` : "Brak zapisanego odczytu IMGW."} Mapa, ${lib} i plan przelotu działają dalej.${simOffline ? " To symulacja awarii: wyłączysz ją w menu Plik albo w zasobniku." : ""}`,
    icon: "i-network", anchor: "#tray-net", timeout: 9000,
  });
}
/** Live reading as text; short = the compact form for the data-sources panel. */
function liveText(short = false) {
  if (!liveState) return simOffline ? "niedostępne" : "łączę…";
  if (liveState.ok) {
    const d = liveState.d, t = readingAt(d);
    return `${fmtReading(d)} · ${t ? new Date(t).toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" }) : `${d.godzina_pomiaru}:00 UTC`}`;
  }
  const c = liveState.c;
  const why = simOffline ? "niedostępne" : "brak łączności";
  if (!c?.d) return `${why} · brak zapisanego odczytu`;
  return short ? `${why} · ostatni odczyt ${readingAge(c)}` : `${why}, ostatni odczyt ${readingAge(c)}: ${fmtReading(c.d)}`;
}
function paintLive() {
  const text = liveText();
  const ok = liveState?.ok;
  const down = simOffline || !navigator.onLine;
  xp.setTray("net", {
    state: down ? "down" : !liveState ? "none" : ok ? "ok" : "off",
    title: `Stacja IMGW Kasprowy Wierch: ${text}${ok ? " (na żywo, poza scenariuszem demo)" : ""}`,
  });
  document.querySelectorAll(".sim-offline").forEach((b) => {
    b.classList.toggle("checked", simOffline);
    b.setAttribute("aria-checked", String(simOffline));
    if (b.classList.contains("sm-item")) b.lastChild.textContent = simOffline ? "Przywróć łączność" : "Symuluj awarię łączności";
  });
  const flag = document.getElementById("offline-flag");
  if (flag) flag.hidden = !(down || (liveState && !ok));
  const el = document.getElementById("live");
  if (!el) return;
  el.textContent = liveText(true);
  el.className = liveState && !ok || simOffline ? "warn" : "";
  el.title = ok ? "Odczyt na żywo, poza scenariuszem demo" : `${text}. Dane na żywo niedostępne; teren, szlaki, biblioteka i plan przelotu działają z pamięci podręcznej.`;
}
function setSimOffline(on) {
  simOffline = on;
  try { on ? sessionStorage.setItem(SIM_KEY, "1") : sessionStorage.removeItem(SIM_KEY); } catch {}
  warnedOffline = false;
  xp.clearBalloons(); // only on a click: at page load the day announcement must not be wiped
  if (on) live(); // takes the offline path at once: no request leaves the app
  else {
    liveState = null;
    paintLive();
    xp.balloon({ title: "Łączność przywrócona", text: "Pobieram świeży odczyt z Kasprowego Wierchu (IMGW).", icon: "i-network", anchor: "#tray-net" });
    live();
  }
}
addEventListener("online", () => { warnedOffline = false; live(); });
addEventListener("offline", () => live());

// Tray network icon: left or right click opens a small XP menu above it.
const trayMenu = $("tray-net-menu");
let trayMenuWasOpen = false;
$("tray-net").addEventListener("pointerdown", () => { trayMenuWasOpen = trayMenu.classList.contains("open"); });
$("tray-net").addEventListener("contextmenu", (e) => { e.preventDefault(); trayMenu.classList.add("open"); });

// ---------- shell actions ----------
const dlg = (o) => xp.msgbox({ near: xp.windowRect("w-map"), ...o });
const COLOR_PL = { red: "czerwone", blue: "niebieskie", green: "zielone", yellow: "żółte", black: "czarne" };
xp.registerActions({
  day1: () => setDay(0),
  day2: () => setDay(1),
  fly: startFlight,
  layout: () => xp.layout(true),
  "max-map": () => xp.toggleMax("w-map"),
  "lib-heat": toggleHeat,
  player: () => openPlayer(),
  "player-sel": () => openPlayer(R.flagOf[state.selected] ? state.selected : R.flags[0]?.sector ?? null),
  "library-page": () => window.open("biblioteka.html", "_blank", "noopener"),
  "show-desktop": () => xp.showDesktop(),
  logoff: () => xp.logoff(),
  about: () => dlg({
    title: "O projekcie Avalauncher", icon: "i-logo",
    html: `<h3>Avalauncher</h3><p>Cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.</p>
      <p>Drony mierzą śnieg nad szlakami, a każdy pomiar porównujemy z policzonymi z góry scenariuszami lawin. Gdy wiedza się starzeje, bo dron nie mógł polecieć, ekran mówi to wprost i planuje przelot.</p>
      <p><b>Brak flagi to nie zielone światło. Decyzję podejmuje prognosta.</b><br>Pogoda: IMGW-PIB Kasprowy Wierch (prawdziwe dane). Grubość płyty i przeloty drona: scenariusz syntetyczny.<br>Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Źródło: IMGW-PIB${SAT ? `<br>Satelita: ${SAT.credit}` : ""}</p>
      <p class="about-links"><a href="projekt.html" target="_blank" rel="noopener">Strona projektu: jak to działa, wyniki, dane i licencje</a><br>
        <a href="biblioteka.html" target="_blank" rel="noopener">Biblioteka scenariuszy${scenarios?.count ? ` (${scenarios.count.toLocaleString("pl-PL")} symulacji AvaFrame)` : ""}</a></p>
      <p>HackYeah 2026 · Defence</p>`,
  }),
  zones: () => dlg({
    title: "Moje strefy startowe", icon: "i-sectors",
    html: `<p>${factParts()[0]}</p>${libraryReach().reach ? `<p>Z <b>${libraryReach().reach}</b> z nich lawina w symulacjach AvaFrame dochodzi do szlaku.</p>` : ""}<p>Na mapie strefy mają brązowe tło, a te z flagą: kreskowanie lub mgłę niewiedzy.</p>`,
  }),
  trails: () => {
    const colors = [...new Set(trails.map((t) => t.color))];
    const list = colors.map((c) => `<span style="display:inline-block;width:16px;height:6px;margin:0 6px 1px 0;background:${TRAIL[c] ?? TRAIL.red};outline:1px solid #888"></span>${COLOR_PL[c] ?? c}`).join("<br>");
    dlg({ title: "Szlaki", icon: "i-trail", html: `<p>Szlaki na mapie w ich prawdziwych kolorach.</p><p>${list}</p><p>Szlaki: © współtwórcy OpenStreetMap</p>` });
  },
  library: () => dlg({
    title: "Biblioteka scenariuszy", icon: "i-library",
    html: factParts().map((p) => `<p>${p}</p>`).join("") + `<p><a href="biblioteka.html" target="_blank" rel="noopener">Otwórz przeglądarkę biblioteki scenariuszy</a></p>`,
  }),
  "sat-snow": toggleSat,
  "project-page": () => window.open("projekt.html", "_blank", "noopener"),
  shutdown: () => xp.shutdown({
    question: "Czy na pewno chcesz wyłączyć lawiny?",
    onOff: "Lawin nie da się wyłączyć. Da się sprawdzić, gdzie polecieć, żeby się dowiedzieć.",
    onStandby: "Śnieg nie przechodzi w stan wstrzymania. Bez pomiaru mgła niewiedzy gęstnieje.",
  }),
  "tray-drone": () => { const [, t] = flightStatus(); xp.balloon({ title: "Przelot drona", text: `${cap(t)}. ${DAYS.days[state.day].label}.`, icon: "i-drone" }); },
  "tray-net": () => { if (!trayMenuWasOpen) trayMenu.classList.add("open"); trayMenuWasOpen = false; },
  "net-status": () => xp.balloon({ title: "Stacja IMGW Kasprowy Wierch", text: liveText() + (liveState?.ok ? " (na żywo, poza scenariuszem demo)" : ""), icon: "i-network", anchor: "#tray-net" }),
  "sim-offline": () => setSimOffline(!simOffline),
});

// ---------- window "Kasprowy Wierch — zima 2024/25 (IMGW)" ----------
const chartCanvas = $("imgw-chart");
const cg = chartCanvas.getContext("2d");
const CH = { hs: "#1d4fa8", hsFill: "rgba(29, 79, 168, 0.13)", nw: "#3a86dc", storm: "rgba(232, 89, 12, 0.13)", now: ROUTE, grid: "#e4e1d3", axis: "#8a8678", text: "#4a4438" };
const MONTHS_SHORT = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"];
const FONT = "Tahoma, 'Segoe UI', sans-serif";
let chartGeom = null;

function drawChart() {
  renderChartStatus();
  const wrap = chartCanvas.parentElement.getBoundingClientRect();
  if (!KW || wrap.width < 40 || wrap.height < 40) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  chartCanvas.width = Math.round(wrap.width * dpr); chartCanvas.height = Math.round(wrap.height * dpr);
  const days = KW.days, n = days.length;
  const cw = wrap.width, ch = wrap.height;
  const L = 44, Rm = 12, T = 30, B = 22;
  const pw = cw - L - Rm, ph = ch - T - B;
  const hsH = Math.round(ph * 0.58), stripY = T + hsH + 8, stripH = 10, nwY = stripY + stripH + 10, nwH = T + ph - nwY;
  let hsTop = 0, nwTop = 0;
  for (const d of days) { hsTop = Math.max(hsTop, d.hs_cm ?? 0); nwTop = Math.max(nwTop, d.new_cm ?? 0); }
  const hsMax = Math.max(60, Math.ceil(hsTop / 20) * 20 + 10);
  const nwMax = Math.max(10, Math.ceil(nwTop / 10) * 10);
  const xOf = (i) => L + ((i + 0.5) / n) * pw, bw = pw / n;
  const yHs = (v) => T + hsH - (v / hsMax) * hsH;
  const yNw = (v) => nwY + nwH - (v / nwMax) * nwH;
  chartGeom = { L, pw, n, T, ph };

  const c = cg;
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.fillStyle = "#fff"; c.fillRect(0, 0, cw, ch);
  c.font = `11px ${FONT}`; c.textBaseline = "middle";

  // storm episodes: pale bands across all panels, labelled at the top
  const idx = Object.fromEntries(days.map((d, i) => [d.date, i]));
  for (const e of KW.episodes ?? []) {
    const a = idx[e.start], b = idx[e.end];
    if (a == null || b == null) continue;
    const x0 = L + (a / n) * pw, x1 = L + ((b + 1) / n) * pw;
    c.fillStyle = CH.storm; c.fillRect(x0, T - 4, x1 - x0, ph + 4);
    c.fillStyle = "#a63b00"; c.fillRect(x0, T - 4, x1 - x0, 2);
    c.fillStyle = CH.text; c.font = `bold 11px ${FONT}`; c.textAlign = "center";
    c.fillText(`+${e.new_cm_3d} cm / 3 dni`, (x0 + x1) / 2, T - 14);
  }
  c.font = `11px ${FONT}`;

  // recessive grid + y labels
  c.strokeStyle = CH.grid; c.lineWidth = 1; c.textAlign = "right"; c.fillStyle = CH.text;
  for (let v = 0; v <= hsMax; v += hsMax > 100 ? 40 : 20) {
    const y = Math.round(yHs(v)) + 0.5;
    c.beginPath(); c.moveTo(L, y); c.lineTo(L + pw, y); c.stroke();
    c.fillText(`${v}`, L - 6, y);
  }
  for (let v = 0; v <= nwMax; v += 10) {
    const y = Math.round(yNw(v)) + 0.5;
    c.beginPath(); c.moveTo(L, y); c.lineTo(L + pw, y); c.stroke();
    c.fillText(`${v}`, L - 6, y);
  }
  // months
  c.textAlign = "left";
  days.forEach((d, i) => {
    if (!d.date.endsWith("-01")) return;
    const x = Math.round(L + (i / n) * pw) + 0.5;
    c.strokeStyle = CH.grid; c.beginPath(); c.moveTo(x, T); c.lineTo(x, T + ph); c.stroke();
    c.fillStyle = CH.text;
    const m = +d.date.slice(5, 7);
    c.fillText(m === 1 ? "sty 2025" : MONTHS_SHORT[m - 1], x + 4, T + ph + 11);
  });

  // panel titles in text ink; the swatch legend above carries identity
  c.fillStyle = "#1d1b17"; c.font = `bold 11px ${FONT}`; c.textAlign = "left";
  c.fillText("Pokrywa śnieżna [cm]", L + 6, T + 9);
  c.fillText("Przyrost w dobę [cm]", L + 6, nwY + 7);
  c.font = `10px ${FONT}`; c.fillStyle = CH.text; c.textAlign = "right";
  c.fillText("zamieć", L - 6, stripY + stripH / 2);

  // snow depth: area + 2px line, broken on gaps
  const runs = [];
  let cur = [];
  days.forEach((d, i) => { if (d.hs_cm == null) { if (cur.length) runs.push(cur); cur = []; } else cur.push([xOf(i), yHs(d.hs_cm)]); });
  if (cur.length) runs.push(cur);
  for (const r of runs) {
    c.beginPath(); c.moveTo(r[0][0], yHs(0));
    for (const [x, y] of r) c.lineTo(x, y);
    c.lineTo(r.at(-1)[0], yHs(0)); c.closePath();
    c.fillStyle = CH.hsFill; c.fill();
    c.beginPath(); r.forEach(([x, y], k) => (k ? c.lineTo(x, y) : c.moveTo(x, y)));
    c.strokeStyle = CH.hs; c.lineWidth = 2; c.lineJoin = "round"; c.stroke();
  }

  // blowing-snow strip: one cell per day, darker = more hours (24 h max)
  days.forEach((d, i) => {
    const h = d.blowing_h ?? 0;
    if (h <= 0) return;
    c.fillStyle = `rgba(74, 68, 56, ${0.15 + 0.85 * Math.min(1, h / 24)})`;
    c.fillRect(L + (i / n) * pw, stripY, Math.max(1, bw - 0.5), stripH);
  });
  c.strokeStyle = "#d5d2bf"; c.lineWidth = 1; c.strokeRect(L + 0.5, stripY - 0.5, pw - 1, stripH + 1);

  // new-snow bars from the baseline, rounded data end
  c.fillStyle = CH.nw;
  days.forEach((d, i) => {
    const v = d.new_cm ?? 0;
    if (v <= 0) return;
    const x = L + (i / n) * pw + 0.25, w = Math.max(1, bw - 0.5), y = yNw(v), h = yNw(0) - y, rr = Math.min(1.5, w / 2);
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, w, h, [rr, rr, 0, 0]); else c.rect(x, y, w, h);
    c.fill();
  });
  c.strokeStyle = CH.axis; c.lineWidth = 1;
  for (const y0 of [yHs(0), yNw(0)]) { c.beginPath(); c.moveTo(L, Math.round(y0) + 0.5); c.lineTo(L + pw, Math.round(y0) + 0.5); c.stroke(); }

  // demo mornings: the other one faint, the current one strong with a label pill
  (KW.demo_days ?? []).forEach((date, k) => {
    const i = idx[date];
    if (i == null) return;
    const x = Math.round(xOf(i)) + 0.5, on = k === state.day;
    c.save();
    c.strokeStyle = on ? CH.now : "rgba(214, 0, 126, 0.4)"; c.lineWidth = on ? 2 : 1; c.setLineDash(on ? [5, 3] : [2, 3]);
    c.beginPath(); c.moveTo(x, T - 2); c.lineTo(x, T + ph); c.stroke();
    c.restore();
    if (!on) return;
    const d = days[i], y = yHs(d.hs_cm ?? 0);
    c.fillStyle = CH.now; c.beginPath(); c.arc(x, y, 4.5, 0, 7); c.fill();
    c.strokeStyle = "#fff"; c.lineWidth = 2; c.stroke();
    const text = `Dzień ${k + 1} · ${dmy(date)}, 7:00 · ${d.hs_cm} cm`;
    c.font = `bold 11px ${FONT}`;
    const tw = c.measureText(text).width + 12;
    const px0 = Math.max(L + 2, Math.min(L + pw - tw - 2, x + 8)), py = Math.max(T + 18, y - 30);
    c.fillStyle = CH.now; c.beginPath();
    if (c.roundRect) c.roundRect(px0, py, tw, 18, 3); else c.rect(px0, py, tw, 18);
    c.fill();
    c.fillStyle = "#fff"; c.textAlign = "left"; c.fillText(text, px0 + 6, py + 9.5);
  });
}

function renderChartStatus() {
  const rm = realMorning();
  if (!rm) { $("imgw-status").textContent = KW ? "" : "Brak danych archiwalnych IMGW."; return; }
  $("imgw-status").textContent = `Dzień ${state.day + 1} = ${dmy(rm.date)}, 7:00: pokrywa ${rm.hs_cm} cm · +${pl(rm.new_cm)} cm w dobę · +${pl(rm.new3)} cm w 3 dni · zamieć ${pl(rm.blowing_h)} h · Tmin ${pl(rm.tmin_c, 1)} °C`;
}

chartCanvas.addEventListener("mousemove", (ev) => {
  const tip = $("chart-tip");
  if (!chartGeom || !KW) return;
  const r = chartCanvas.getBoundingClientRect();
  const x = ev.clientX - r.left, y = ev.clientY - r.top;
  const i = Math.floor(((x - chartGeom.L) / chartGeom.pw) * chartGeom.n);
  const d = KW.days[i];
  if (!d || y < chartGeom.T - 22 || y > chartGeom.T + chartGeom.ph) { tip.hidden = true; return; }
  const ep = (KW.episodes ?? []).find((e) => d.date >= e.start && d.date <= e.end);
  const type = d.precip_type === "S" ? " (śnieg)" : d.precip_type === "W" ? " (deszcz)" : "";
  tip.hidden = false;
  tip.innerHTML = `<b>${longDate(d.date)}</b><br>pokrywa ${d.hs_cm ?? "brak pomiaru"} cm · przyrost ${d.new_cm == null ? "brak" : `+${pl(d.new_cm)} cm`}<br>`
    + `opad ${pl(d.precip_mm ?? 0, 1)} mm${type} · śnieg pada ${pl(d.snowfall_h ?? 0, 1)} h<br>`
    + `zamieć ${pl(d.blowing_h ?? 0, 1)} h · wiatr ≥10 m/s ${pl(d.wind10_h ?? 0, 1)} h · T ${pl(d.tmin_c, 1)}…${pl(d.tmax_c, 1)} °C`
    + (ep ? `<br><b>Epizod: ${ep.label}</b>` : "");
  const wr = chartCanvas.parentElement.getBoundingClientRect();
  tip.style.left = `${Math.max(4, Math.min(x + 14, wr.width - tip.offsetWidth - 4))}px`;
  tip.style.top = `${Math.max(4, Math.min(y + 16, wr.height - tip.offsetHeight - 4))}px`;
});
chartCanvas.addEventListener("mouseleave", () => { $("chart-tip").hidden = true; });
new ResizeObserver(() => drawChart()).observe(chartCanvas.parentElement);

// ---------- loop ----------
let last = performance.now();
function frame(now) {
  const dt = Math.min(64, now - last); last = now;
  state.dash = (state.dash + dt * 0.03 * view.dpr) % 1000;
  stepFlight(dt);
  if (state.whatIf && !document.getElementById("flag-dialog")) state.whatIf = null; // dialog closed or replaced
  syncWhatIf();
  if (player.cur && !player.video.paused) paintSeek();
  const k = 1 - Math.exp(-dt / 260); // exponential ease toward targets
  for (const s of sectors) state.fog[s.index] += (fogTarget(s) - state.fog[s.index]) * k;
  draw();
  requestAnimationFrame(frame);
}

new ResizeObserver(() => resize()).observe(canvas.parentElement);
compute();
resize();
renderAll();
live();
setInterval(live, 10 * 60 * 1000);
requestAnimationFrame(frame);
announceDay();
xp.ready();
loadLibraryCells();
// Offline mode: once sw.js is active, let it pull the 3D films in, so the player works without a network too.
navigator.serviceWorker?.ready.then((r) => setTimeout(() => r.active?.postMessage({ type: "warm-media" }), 4000)).catch(() => {});

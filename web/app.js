import { assess, planFlight } from "./engine.js";
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

// ---------- data ----------
const [terrain, sectors, trails, real, mock, scenarios, calibration, proof] = await Promise.all([
  json("data/terrain.json"), json("data/sectors.json"), json("data/trails.json"),
  optional("data/days.json"), optional("data/mock/days.json"),
  optional("data/scenarios.json"), optional("data/calibration.json"), optional("data/proof.json"),
]);
const DAYS = real ?? mock;
const index = new Uint8Array(await (await fetch("data/sectors_u8.bin")).arrayBuffer());
const base = new Image();
base.src = "data/map.png";
await base.decode().catch(async () => { base.src = `data/${terrain.hillshade}`; await base.decode(); });
await document.fonts.load('700 16px "Archivo"').catch(() => {});

const W = terrain.width, H = terrain.height;
const byId = Object.fromEntries(sectors.map((s) => [s.id, s]));
const ctx = { exposure: DAYS.exposure, base: DAYS.base, scenarios, trails };

// ---------- state ----------
const state = {
  day: new URLSearchParams(location.search).get("day") === "2" ? 1 : 0, selected: null, budget: 20,
  visited: new Set(), flight: null, // { path, len, t, done }
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

let hazardLayer = null, idleLayer = null, selectLayer = null, unknownLayer = null;
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
  if (idleLayer) g.drawImage(idleLayer, 0, 0);
  if (hazardLayer) g.drawImage(hazardLayer, 0, 0);

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

  // trails
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
  $("stamp").textContent = `stan na ${hour} · ${day.toLowerCase()}`;
  const exposed = Object.keys(R.day.sectors).length;
  const since = state.flight?.done ? "0 h" : `${d.weather.hours_since_flight} h`;
  $("kpis").innerHTML = [
    [exposed, "sektorów nad szlakami", ""],
    [nz, "może zagrozić", "hazard"],
    [nw, "nie wiem", "unknown"],
    [since, `od przelotu · ${d.weather.new_cm} cm śniegu`, ""],
  ].map(([v, l, c]) => `<div class="kpi ${c}"><b>${v}</b><span>${l}</span></div>`).join("");
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
  $("sources").innerHTML = `
    <div><svg aria-hidden="true"><use href="#i-drone"/></svg><dl><dt>Przelot drona</dt><dd class="${st === "ok" ? "" : "warn"}">${text}</dd></dl></div>
    <div><svg aria-hidden="true"><use href="#i-network"/></svg><dl><dt>Stacja IMGW Kasprowy Wierch</dt><dd id="live">łączę…</dd></dl></div>
    <div><svg aria-hidden="true"><use href="#i-library"/></svg><dl><dt>Biblioteka scenariuszy</dt><dd>${scenarios?.count ? scenarios.count.toLocaleString("pl-PL") : "w budowie"}</dd></dl></div>`;
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
    body.innerHTML = `<tr class="empty"><td colspan="7">Brak flag. To nie znaczy, że jest bezpiecznie.</td></tr>`;
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
  $("why").innerHTML = `<b>${f.n}. ${byId[f.sector].name}:</b> ${f.reason}${analogs}`;
}

function renderPlan() {
  const p = R.plan;
  $("budget-out").textContent = `${state.budget} min`;
  $("plan-kpis").innerHTML = p.route.length
    ? `<div><b>${p.route.length}</b><span>sektorów do zmierzenia</span></div><div><b>${p.minutes} min</b><span>lotu z powrotem</span></div><div><b class="gain">−${p.sigma_drop}%</b><span>niepewności nad szlakami</span></div>`
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

function factParts() {
  const parts = [`<strong>${sectors.length}</strong> stref startowych wyznaczonych z terenu GUGiK NMT (nachylenie 28–55°, powyżej 1600 m).`];
  if (scenarios?.count) parts.push(`<strong>${scenarios.count.toLocaleString("pl-PL")}</strong> scenariuszy lawin policzonych z góry.`);
  if (calibration) parts.push(`Prosty model skalibrowany do AvaFrame: błąd zasięgu ±${calibration.runout_error_m} m.`);
  if (!real) parts.push("Silnik tymczasowy, dane udawane.");
  return parts;
}
function renderFacts() { $("library").innerHTML = factParts().join(" "); }

function renderAll() { renderDays(); renderSituation(); renderRows(); renderPlan(); renderFacts(); }

function select(id, { toggle = true, explain = true } = {}) {
  state.selected = toggle && state.selected === id ? null : id;
  buildHazardLayer(); renderRows();
  if (explain && state.selected && R.flagOf[state.selected]) explainFlag(R.flagOf[state.selected]);
}

function explainFlag(f) {
  const s = byId[f.sector], st = R.day.sectors[f.sector];
  const unknown = f.kind === "nie_wiem";
  const analogs = f.analogs ? `<p>${f.analogs_hitting} z ${f.analogs} podobnych scenariuszy dochodzi do szlaku.</p>` : "";
  const inPlan = R.plan.route.includes(f.sector);
  xp.msgbox({
    id: "flag-dialog", title: `${f.n}. ${s.name}`, icon: unknown ? "i-question" : "i-warn",
    html: `<h3>${unknown ? "Nie wiem" : "Może zagrozić szlakowi"}</h3>
      <p>${f.reason}</p>${analogs}
      <p>Szlak: <b>${f.trails.join(", ")}</b><br>${s.band} · ΔHS ${Math.round(st.dhs_m * 100)} cm · σ ±${Math.round(st.sigma_m * 100)} cm · pomiar ${st.hours_since_measured} h temu</p>
      <p>${inPlan ? "Sektor jest w planie przelotu." : "Sektora nie ma w obecnym planie przelotu."}${unknown ? " Pomiar z drona zamieni „nie wiem” w liczbę." : ""}</p>`,
    buttons: unknown && inPlan && !state.flight
      ? [{ label: "Wykonaj przelot", value: "fly" }, { label: "OK", value: true, default: true }]
      : [{ label: "OK", value: true, default: true }],
    near: xp.windowRect("w-sit"),
  }).then((v) => { if (v === "fly") startFlight(); });
}

function recompute() { compute(); renderAll(); }

function setDay(n) {
  copy?.close(); copy = null;
  document.getElementById("flag-dialog")?.remove();
  state.day = n; state.selected = null; state.visited.clear(); state.flight = null;
  recompute();
  try { history.replaceState(null, "", n === 1 ? "?day=2" : location.pathname); } catch {}
  announceDay();
}

function announceDay() {
  xp.clearBalloons();
  const d = DAYS.days[state.day];
  const { nw } = counts();
  if (d.flight.flown) xp.balloon({ title: "Przelot wykonany o 6:00", text: `${d.label.replace(", ", ", stan na ")}. ${hazardSentence(true)}`, icon: "i-drone" });
  else xp.balloon({ title: "Przelot odwołany: śnieżyca", text: `Ostatni przelot ${d.weather.hours_since_flight} h temu, od tego czasu ${d.weather.new_cm} cm śniegu.`, icon: "i-badge-warn" });
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

// ---------- live Kasprowy Wierch (IMGW) ----------
let liveState = null;
let warnedOffline = false;
async function live() {
  const key = "avalauncher.kasprowy";
  try {
    const d = await (await fetch("https://danepubliczne.imgw.pl/api/data/synop/station/kasprowywierch", { cache: "no-store" })).json();
    try { localStorage.setItem(key, JSON.stringify({ d, at: Date.now() })); } catch {}
    liveState = { ok: true, d };
  } catch {
    let c = null;
    try { c = JSON.parse(localStorage.getItem(key)); } catch {}
    liveState = { ok: false, c };
    if (!warnedOffline) {
      warnedOffline = true;
      xp.balloon({ title: "Stacja IMGW: brak łączności", text: c ? "Pokazuję ostatni zapisany odczyt z Kasprowego Wierchu." : "Brak zapisanego odczytu. Scenariusz demo działa dalej offline.", icon: "i-network", anchor: "#tray-net" });
    }
  }
  paintLive();
}
function liveText() {
  if (!liveState) return "łączę…";
  if (liveState.ok) { const d = liveState.d; return `${d.temperatura} °C · ${d.predkosc_wiatru} m/s · ${d.godzina_pomiaru}:00`; }
  const c = liveState.c;
  return c?.d ? `brak łączności, odczyt sprzed ${Math.max(1, Math.round((Date.now() - c.at) / 3600000))} h: ${c.d.temperatura} °C · ${c.d.predkosc_wiatru} m/s` : "brak łączności";
}
function paintLive() {
  const text = liveText();
  const ok = liveState?.ok;
  xp.setTray("net", { state: !liveState ? "none" : ok ? "ok" : "off", title: `Stacja IMGW Kasprowy Wierch: ${text}${ok ? " (na żywo, poza scenariuszem demo)" : ""}` });
  const el = document.getElementById("live");
  if (!el) return;
  el.textContent = text;
  el.className = liveState && !ok ? "warn" : "";
  el.title = ok ? "Odczyt na żywo, poza scenariuszem demo" : "";
}

// ---------- shell actions ----------
const dlg = (o) => xp.msgbox({ near: xp.windowRect("w-map"), ...o });
const COLOR_PL = { red: "czerwone", blue: "niebieskie", green: "zielone", yellow: "żółte", black: "czarne" };
xp.registerActions({
  day1: () => setDay(0),
  day2: () => setDay(1),
  fly: startFlight,
  layout: () => xp.layout(true),
  "max-map": () => xp.toggleMax("w-map"),
  "show-desktop": () => xp.showDesktop(),
  logoff: () => xp.logoff(),
  about: () => dlg({
    title: "O projekcie Avalauncher", icon: "i-logo",
    html: `<h3>Avalauncher</h3><p>Cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.</p>
      <p>Drony mierzą śnieg nad szlakami, a każdy pomiar porównujemy z policzonymi z góry scenariuszami lawin. Gdy wiedza się starzeje, bo dron nie mógł polecieć, ekran mówi to wprost i planuje przelot.</p>
      <p><b>Brak flagi nie oznacza, że jest bezpiecznie. Decyzję podejmuje prognosta.</b><br>Śnieg, przeloty i pogoda w scenariuszu to dane syntetyczne.<br>Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap</p>
      <p>HackYeah 2026 · Defence</p>`,
  }),
  zones: () => dlg({
    title: "Moje strefy startowe", icon: "i-sectors",
    html: `<p>${factParts()[0]}</p><p><b>${Object.keys(R.day.sectors).length}</b> z nich leży nad szlakami. Na mapie mają brązowe tło, a te z flagą: kreskowanie lub mgłę niewiedzy.</p>`,
  }),
  trails: () => {
    const by = {};
    for (const t of trails) by[t.color] = (by[t.color] ?? 0) + 1;
    const list = Object.entries(by).map(([c, n]) => `<span style="display:inline-block;width:16px;height:6px;margin:0 6px 1px 0;background:${TRAIL[c] ?? TRAIL.red};outline:1px solid #888"></span>${COLOR_PL[c] ?? c}: ${n}`).join("<br>");
    dlg({ title: "Szlaki", icon: "i-trail", html: `<p><b>${trails.length}</b> ${plural(trails.length, "odcinek", "odcinki", "odcinków")} szlaków na mapie, w ich prawdziwych kolorach.</p><p>${list}</p><p>Szlaki: © współtwórcy OpenStreetMap</p>` });
  },
  library: () => dlg({ title: "Biblioteka scenariuszy", icon: "i-library", html: factParts().map((p) => `<p>${p}</p>`).join("") }),
  shutdown: () => xp.shutdown({
    question: "Czy na pewno chcesz wyłączyć lawiny?",
    onOff: "Lawin nie da się wyłączyć. Da się sprawdzić, gdzie polecieć, żeby się dowiedzieć.",
    onStandby: "Śnieg nie przechodzi w stan wstrzymania. Bez pomiaru mgła niewiedzy gęstnieje.",
  }),
  "tray-drone": () => { const [, t] = flightStatus(); xp.balloon({ title: "Przelot drona", text: `${cap(t)}. ${DAYS.days[state.day].label}.`, icon: "i-drone" }); },
  "tray-net": () => xp.balloon({ title: "Stacja IMGW Kasprowy Wierch", text: liveText() + (liveState?.ok ? " (na żywo, poza scenariuszem demo)" : ""), icon: "i-network", anchor: "#tray-net" }),
});

// ---------- loop ----------
let last = performance.now();
function frame(now) {
  const dt = Math.min(64, now - last); last = now;
  state.dash = (state.dash + dt * 0.03 * view.dpr) % 1000;
  stepFlight(dt);
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

// Biblioteka scenariuszy: browse the precomputed AvaFrame com1DFA library (web/data) offline.
const $ = (id) => document.getElementById(id);
const W = 400, H = 400, PX = 4; // grid 400x400 cells of 10 m; map.png has 4 px per cell
const dpr = () => window.devicePixelRatio || 1;

const TRAIL = { red: "#d62828", blue: "#1f5fd1", green: "#2a9d3c", yellow: "#f2c200", black: "#22201c" };
const FR = {
  samosATSmall: { pl: "małe lawiny", short: "małe", color: "#3f7fd9", ord: 0 },
  samosATMedium: { pl: "średnie lawiny", short: "średnie", color: "#e08a1e", ord: 1 },
  samosAT: { pl: "duże lawiny", short: "duże", color: "#a63b00", ord: 2 },
};
const FR_KEYS = Object.keys(FR);
const ASPECTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
const ASPECT_PL = { N: "północna", NE: "północno-wschodnia", E: "wschodnia", SE: "południowo-wschodnia", S: "południowa", SW: "południowo-zachodnia", W: "zachodnia", NW: "północno-zachodnia" };
const nf = (v, d = 1) => Number(v).toLocaleString("pl-PL", { minimumFractionDigits: d, maximumFractionDigits: d });
const nInt = (v) => Math.round(v).toLocaleString("pl-PL");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// Errors land in the status bar so a screenshot shows them.
const showErr = (m) => { const el = $("st-sel"); if (el) { el.textContent = "Błąd: " + m; el.classList.add("err"); el.hidden = false; } };
addEventListener("error", (e) => showErr(e.message));
addEventListener("unhandledrejection", (e) => showErr(e.reason?.message ?? String(e.reason)));

// ---------------------------------------------------------------- window chrome
let zTop = 20;
const WINS = [...document.querySelectorAll("#desktop > .window")];
function focusWin(w) {
  for (const x of WINS) x.classList.toggle("active", x === w);
  w.style.zIndex = ++zTop;
  renderTasks();
}
function restoreWin(w) { w.classList.remove("minimized"); focusWin(w); redrawFor(w); }
function renderTasks() {
  $("task-buttons").innerHTML = WINS.map((w) => {
    const act = w.classList.contains("active") && !w.classList.contains("minimized");
    return `<button class="task-btn${act ? " active" : ""}${w.classList.contains("minimized") ? " min" : ""}" data-win="${w.id}"><svg><use href="#${w.dataset.icon}"/></svg><span>${esc(w.dataset.title)}</span></button>`;
  }).join("");
}
$("task-buttons").addEventListener("click", (e) => {
  const b = e.target.closest("[data-win]"); if (!b) return;
  const w = $(b.dataset.win);
  if (w.classList.contains("minimized")) restoreWin(w);
  else if (w.classList.contains("active")) { w.classList.add("minimized"); renderTasks(); }
  else focusWin(w);
});
for (const w of WINS) {
  w.addEventListener("pointerdown", () => { if (!w.classList.contains("active")) focusWin(w); }, true);
  const bar = w.querySelector(".title-bar");
  bar.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button") || w.classList.contains("maximized")) return;
    const sx = e.clientX - w.offsetLeft, sy = e.clientY - w.offsetTop;
    const desk = $("desktop").getBoundingClientRect();
    const move = (ev) => {
      w.style.left = Math.min(desk.width - 80, Math.max(-w.offsetWidth + 80, ev.clientX - sx)) + "px";
      w.style.top = Math.min(desk.height - 30, Math.max(0, ev.clientY - sy)) + "px";
    };
    const up = () => { removeEventListener("pointermove", move); removeEventListener("pointerup", up); };
    addEventListener("pointermove", move); addEventListener("pointerup", up);
  });
  bar.addEventListener("dblclick", (e) => { if (!e.target.closest("button")) { w.classList.toggle("maximized"); redrawFor(w); } });
  w.querySelector(".tb-min")?.addEventListener("click", () => { w.classList.add("minimized"); renderTasks(); });
  w.querySelector(".tb-close")?.addEventListener("click", () => { w.classList.add("minimized"); renderTasks(); });
  w.querySelector(".tb-max")?.addEventListener("click", () => { w.classList.toggle("maximized"); redrawFor(w); });
}
renderTasks();

// menus
document.addEventListener("click", (e) => {
  const head = e.target.closest(".menu-head");
  const open = document.querySelector(".menu.open");
  if (head) { const m = head.parentElement; const was = m.classList.contains("open"); open?.classList.remove("open"); if (!was) m.classList.add("open"); return; }
  open?.classList.remove("open");
  const item = e.target.closest(".menu-pop button");
  if (!item) return;
  if (item.dataset.href) location.href = item.dataset.href;
  if (item.dataset.tab) showTab(item.dataset.tab);
  if (item.dataset.open) restoreWin($(item.dataset.open));
  if (item.dataset.act === "reset") resetFilters();
  if (item.dataset.act === "about") $("about").hidden = false;
});
document.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) $(e.target.closest("[data-close]").dataset.close).hidden = true; });

const tick = () => { const d = new Date(); $("clock").textContent = `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`; };
tick(); setInterval(tick, 20000);

// ---------------------------------------------------------------- data
// Tab clicks during the (slow) data load are remembered and applied once the library is ready.
let READY = false, pendingTab = location.hash.slice(1) || null;
document.querySelectorAll(".tab[data-tab]").forEach((b) => b.addEventListener("click", () => { if (!READY) pendingTab = b.dataset.tab; }));
const loading = document.createElement("div");
loading.className = "loading";
loading.innerHTML = `<div class="box"><span>Wczytywanie biblioteki scenariuszy (10 MB śladów zasięgu)…</span><div class="progress marquee"><i></i></div></div>`;
document.querySelector("#w-lib .lib-body").append(loading);

const getJSON = (u) => fetch(u).then((r) => (r.ok ? r.json() : null)).catch(() => null);
const getBin = (u, T) => fetch(u).then((r) => (r.ok ? r.arrayBuffer() : null)).then((b) => (b ? new T(b) : null)).catch(() => null);
const getImg = (u) => new Promise((res) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = u; });

const [S, SECT, TRAILS, SEC8, HEAT, CELLS, MAP, SUR, CAL, RL, PROOF, MEDIA] = await Promise.all([
  getJSON("data/scenarios.json"), getJSON("data/sectors.json"), getJSON("data/trails.json"),
  getBin("data/sectors_u8.bin", Uint8Array), getBin("data/library_heat.bin", Uint16Array), getBin("data/scenario_cells.bin", Uint32Array),
  getImg("data/map.png"), getJSON("data/surrogate.json"), getJSON("data/calibration.json"), getJSON("data/rl.json"),
  getJSON("data/proof.json"), getJSON("media/media.json"),
]);
loading.remove();
if (!S || !CELLS || !SECT || !TRAILS || !SEC8) throw new Error("brak plików biblioteki w web/data");

const secById = new Map(SECT.map((s) => [s.id, s]));
const runById = new Map(S.runs.map((r) => [r.id, r]));
const runsBySec = new Map();
for (const r of S.runs) { if (!runsBySec.has(r.sector)) runsBySec.set(r.sector, []); runsBySec.get(r.sector).push(r); }
const libSecs = S.sectors.map((id) => secById.get(id)).filter(Boolean);
const runKey = (sec, fr, th) => `${sec}_${fr}_${th.toFixed(1)}`;
const segById = new Map();
for (const t of TRAILS) for (const sg of t.segments ?? []) segById.set(sg.id, { trail: t, seg: sg, pts: (t.paths[sg.part] ?? []).slice(sg.from, sg.to + 1) });
const secCells = new Map();
{
  const lists = new Map();
  for (let i = 0; i < SEC8.length; i++) { const v = SEC8[i]; if (v) { let a = lists.get(v); if (!a) lists.set(v, (a = [])); a.push(i); } }
  for (const [k, a] of lists) secCells.set(k, Int32Array.from(a));
}
const relCells = (sid) => secCells.get(secById.get(sid)?.index) ?? new Int32Array(0);
const cellsOf = (r) => CELLS.subarray(r.cells_offset, r.cells_offset + r.cells_count);
const hitCount = (sid) => (runsBySec.get(sid) ?? []).filter((r) => r.hits.length).length;
const media = MEDIA ?? { surrogate: [], kalibracja: [], rl: [], hero: {} };
const ranOn = (() => {
  const m = /(\d+) runs in ([\d.]+) min on (\d+) cores/.exec(S.computed_on ?? "");
  const host = (S.computed_on ?? "").split(",")[0];
  return m ? `${host}: ${m[1]} przebiegów w ${nf(+m[2])} min na ${m[3]} rdzeniach` : S.computed_on ?? "";
})();

const bboxCache = new Map();
function bboxOf(key, idxs) {
  if (bboxCache.has(key)) return bboxCache.get(key);
  let c0 = W, r0 = H, c1 = -1, r1 = -1;
  for (const i of idxs) { const c = i % W, r = (i / W) | 0; if (c < c0) c0 = c; if (c > c1) c1 = c; if (r < r0) r0 = r; if (r > r1) r1 = r; }
  const b = c1 < 0 ? null : { c0, r0, c1, r1 };
  bboxCache.set(key, b);
  return b;
}
const union = (a, b) => (!a ? b : !b ? a : { c0: Math.min(a.c0, b.c0), r0: Math.min(a.r0, b.r0), c1: Math.max(a.c1, b.c1), r1: Math.max(a.r1, b.r1) });
const runBox = (r) => union(bboxOf(r.id, cellsOf(r)), bboxOf("sec:" + r.sector, relCells(r.sector))) ?? { c0: 0, r0: 0, c1: W - 1, r1: H - 1 };
function fitCrop(b, w, h, m = 12) {
  let bw = b.c1 - b.c0 + 1 + 2 * m, bh = b.r1 - b.r0 + 1 + 2 * m;
  const a = w / h;
  if (bw / bh < a) bw = bh * a; else bh = bw / a;
  if (bw > W) { bw = W; bh = bw / a; }
  if (bh > H) { bh = H; bw = bh * a; }
  const cx = (b.c0 + b.c1 + 1) / 2, cy = (b.r0 + b.r1 + 1) / 2;
  return { x0: Math.max(0, Math.min(cx - bw / 2, W - bw)), y0: Math.max(0, Math.min(cy - bh / 2, H - bh)), cw: bw, ch: bh };
}

// ---------------------------------------------------------------- drawing
const ov = document.createElement("canvas"); ov.width = W; ov.height = H;
const ovx = ov.getContext("2d");
const mask = new Uint8Array(W * H);
const FOOT_FILL = [232, 89, 12, 150], FOOT_EDGE = [150, 48, 0, 255];
const REL_FILL = [107, 42, 6, 215], REL_EDGE = [45, 16, 2, 255];
function paint(data, idxs, fill, edge) {
  for (const i of idxs) mask[i] = 1;
  for (const i of idxs) {
    const c = i % W, r = (i / W) | 0;
    const e = c === 0 || c === W - 1 || r === 0 || r === H - 1 || !mask[i - 1] || !mask[i + 1] || !mask[i - W] || !mask[i + W];
    const col = e ? edge : fill, o = i * 4;
    data[o] = col[0]; data[o + 1] = col[1]; data[o + 2] = col[2]; data[o + 3] = col[3];
  }
  for (const i of idxs) mask[i] = 0;
}
function drawBase(ctx, w, h, crop) {
  ctx.fillStyle = "#f4efe4"; ctx.fillRect(0, 0, w, h);
  if (MAP) { ctx.imageSmoothingEnabled = true; ctx.drawImage(MAP, crop.x0 * PX, crop.y0 * PX, crop.cw * PX, crop.ch * PX, 0, 0, w, h); }
  ctx.fillStyle = "rgba(255,255,255,0.14)"; ctx.fillRect(0, 0, w, h);
}
function drawTrails(ctx, crop, s, lw, hits = []) {
  const line = (pts, color, width) => {
    if (pts.length < 2) return;
    ctx.beginPath();
    pts.forEach(([c, r], i) => { const x = (c - crop.x0) * s, y = (r - crop.y0) * s; if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.stroke();
  };
  ctx.lineJoin = "round"; ctx.lineCap = "round";
  for (const t of TRAILS) for (const p of t.paths) line(p, "rgba(255,255,255,0.85)", lw * 3.2);
  for (const t of TRAILS) for (const p of t.paths) line(p, TRAIL[t.color] ?? TRAIL.red, lw * 1.6);
  for (const id of hits) { const g = segById.get(id); if (g) line(g.pts, "#ffd43b", lw * 6.5); }
  for (const id of hits) { const g = segById.get(id); if (g) { line(g.pts, "#22201c", lw * 3.6); line(g.pts, TRAIL[g.trail.color] ?? TRAIL.red, lw * 1.9); } }
}
function drawScene(ctx, w, h, crop, run, { base = null, lw = 1, sector = null } = {}) {
  const s = w / crop.cw;
  if (base) ctx.drawImage(base, 0, 0, w, h); else drawBase(ctx, w, h, crop);
  const img = new ImageData(W, H);
  if (run) paint(img.data, cellsOf(run), FOOT_FILL, FOOT_EDGE);
  const sid = run?.sector ?? sector;
  if (sid) paint(img.data, relCells(sid), REL_FILL, REL_EDGE);
  ovx.putImageData(img, 0, 0);
  ctx.imageSmoothingEnabled = s < 2;
  ctx.drawImage(ov, crop.x0, crop.y0, crop.cw, crop.ch, 0, 0, w, h);
  ctx.imageSmoothingEnabled = true;
  drawTrails(ctx, crop, s, lw, run?.hits ?? []);
}
function fitCanvas(cv) {
  const r = cv.getBoundingClientRect(), k = dpr();
  const w = Math.max(1, Math.round(r.width * k)), h = Math.max(1, Math.round(r.height * k));
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
  return { w, h, k };
}
function scaleBar(ctx, w, h, crop, k) {
  const mpp = (crop.cw * 10) / w;
  const target = 90 * k * mpp;
  const nice = [50, 100, 200, 250, 500, 1000, 2000].reduce((a, b) => (Math.abs(b - target) < Math.abs(a - target) ? b : a));
  const len = nice / mpp, x = 10 * k, y = h - 10 * k;
  ctx.fillStyle = "rgba(255,255,255,0.86)"; ctx.fillRect(x - 5 * k, y - 18 * k, len + 56 * k, 23 * k);
  ctx.fillStyle = "#1d1b17"; ctx.fillRect(x, y - 6 * k, len, 3 * k); ctx.fillRect(x, y - 10 * k, 1.5 * k, 8 * k); ctx.fillRect(x + len - 1.5 * k, y - 10 * k, 1.5 * k, 8 * k);
  ctx.font = `${12 * k}px Tahoma, sans-serif`; ctx.textBaseline = "alphabetic";
  ctx.fillText(`${nInt(nice)} m`, x + len + 6 * k, y - 2 * k);
}

// ---------------------------------------------------------------- state
const state = { sector: null, run: null, tab: "lista", sort: { k: "frict", desc: false } };

function defaultRun(sid) {
  const runs = runsBySec.get(sid) ?? [];
  const med = runs.filter((r) => r.frict === "samosATMedium");
  return (med.find((r) => r.hits.length) ?? runById.get(runKey(sid, "samosATMedium", 1.2)) ?? runs[0])?.id;
}

// ---------------------------------------------------------------- tree
function buildTree() {
  const tree = $("tree");
  const node = (lvl, icon, label, cnt, attrs, tw = "none", title = "") =>
    `<div class="node lvl${lvl}" ${attrs} title="${esc(title)}"><span class="tw ${tw}">${tw === "none" ? "" : "−"}</span><svg><use href="#${icon}"/></svg><span class="lbl">${esc(label)}</span><span class="cnt">${cnt}</span></div>`;
  let html = node(0, "i-library", "Biblioteka scenariuszy", `${S.count}`, `data-sec=""`, "none", "Wszystkie przebiegi");
  for (const a of ASPECTS) {
    const secs = libSecs.filter((s) => s.aspect === a).sort((x, y) => x.id.localeCompare(y.id));
    if (!secs.length) continue;
    html += node(1, "i-folder", `Wystawa ${a} · ${ASPECT_PL[a]}`, `(${secs.length})`, `data-grp="${a}"`, "open", `${secs.length} stoków o wystawie ${ASPECT_PL[a]}`);
    html += `<div class="kids" data-kids="${a}">` + secs.map((s) => {
      const n = (runsBySec.get(s.id) ?? []).length, h = hitCount(s.id);
      return node(2, "i-sectors", `${s.id} · ${s.name}`, `<b>${h}</b>/${n}`, `data-sec="${s.id}"`, "none", `${s.name}, ${s.band}, ${nf(s.area_ha)} ha strefy startowej\n${h} z ${n} przebiegów dochodzi do szlaku`);
    }).join("") + `</div>`;
  }
  tree.innerHTML = html;
  tree.addEventListener("click", (e) => {
    const n = e.target.closest(".node"); if (!n) return;
    if (n.dataset.grp) {
      const kids = tree.querySelector(`[data-kids="${n.dataset.grp}"]`);
      kids.hidden = !kids.hidden;
      n.querySelector(".tw").textContent = kids.hidden ? "+" : "−";
      return;
    }
    selectSector(n.dataset.sec || null);
  });
}
function markTree() {
  const tree = $("tree");
  tree.querySelectorAll(".node.selected").forEach((n) => n.classList.remove("selected"));
  const n = tree.querySelector(`.node[data-sec="${state.sector ?? ""}"]`);
  if (n) {
    n.classList.add("selected");
    const kids = n.closest(".kids"); if (kids?.hidden) { kids.hidden = false; }
    const tr = tree.getBoundingClientRect(), nr = n.getBoundingClientRect();
    if (nr.top < tr.top || nr.bottom > tr.bottom) tree.scrollTop += nr.top - tr.top - tr.height / 3;
  }
}

// ---------------------------------------------------------------- list
const trailLabel = (t) => (t ? t.name : "szlak");
function hitsGrouped(r) {
  const by = new Map();
  r.hits.forEach((id, i) => {
    const g = segById.get(id), key = g?.trail.id ?? id;
    if (!by.has(key)) by.set(key, { t: g?.trail, n: [], pft: [] });
    by.get(key).n.push(id.split("-")[1] ?? id); by.get(key).pft.push(r.hits_pft_m?.[i]);
  });
  return [...by.values()];
}
const swatch = (t) => `<i class="sw-t" style="background:${TRAIL[t?.color] ?? "#999"}"></i>`;
function hitsHtml(r) {
  if (!r.hits.length) return `<span class="no">nie</span>`;
  return `<span class="yes">tak</span> · ` + hitsGrouped(r).map(({ t, n }) => `${swatch(t)}${esc(trailLabel(t))} ${n.join(", ")}`).join("; ");
}
const hitsTitle = (r) => (r.hits.length ? r.hits.map((id, i) => `${trailLabel(segById.get(id)?.trail)}, odcinek ${id}: ${nf(r.hits_pft_m?.[i] ?? 0, 2)} m`).join("\n") : "Nie dochodzi do żadnego odcinka szlaku");
const COLS = [
  { k: "sector", h: "Stok", get: (r) => r.sector, fmt: (r) => `${r.sector} · ${esc(secById.get(r.sector)?.name)}`, all: true },
  { k: "relTh", h: "Grubość<br>płyty [m]", num: 1, get: (r) => r.relTh, fmt: (r) => nf(r.relTh) },
  { k: "frict", h: "Tarcie<br>(wariant)", get: (r) => FR[r.frict]?.ord ?? 9, fmt: (r) => `<i class="fr-dot" style="background:${FR[r.frict]?.color}"></i>${FR[r.frict]?.pl ?? r.frict}` },
  { k: "runout_m", h: "Zasięg<br>[m]", num: 1, get: (r) => r.runout_m, fmt: (r) => nInt(r.runout_m) },
  { k: "area_ha", h: "Powierzchnia<br>[ha]", num: 1, get: (r) => r.area_ha, fmt: (r) => nf(r.area_ha) },
  { k: "max_pft_m", h: "Maks.<br>przepływ [m]", num: 1, get: (r) => r.max_pft_m, fmt: (r) => nf(r.max_pft_m) },
  { k: "hits", h: "Dochodzi<br>do szlaku", cls: "hits", get: (r) => (r.hits.length ? 1 + r.hits.length / 100 : 0), fmt: hitsHtml, title: hitsTitle },
  { k: "trail_pft_max_m", h: "Przepływ na<br>szlaku [m]", num: 1, get: (r) => r.trail_pft_max_m, fmt: (r) => (r.hits.length ? nf(r.trail_pft_max_m, 2) : "—") },
];
const visibleCols = () => COLS.filter((c) => !c.all || !state.sector);
function filtered() {
  const maxTh = S.thicknesses[+$("f-th").value] ?? 99;
  const frs = new Set([...document.querySelectorAll(".f-fr:checked")].map((i) => i.value));
  const hitOnly = $("f-hit").checked;
  const base = state.sector ? runsBySec.get(state.sector) ?? [] : S.runs;
  return { base, rows: base.filter((r) => r.relTh <= maxTh + 1e-6 && frs.has(r.frict) && (!hitOnly || r.hits.length)) };
}
function renderList() {
  const cols = visibleCols();
  const c = cols.find((x) => x.k === state.sort.k) ?? cols[1];
  $("list-head").innerHTML = "<tr>" + cols.map((x) => `<th data-k="${x.k}" class="${x.num ? "num " : ""}${x.k === c.k ? "sorted" + (state.sort.desc ? " desc" : "") : ""}">${x.h}</th>`).join("") + "</tr>";
  const { base, rows } = filtered();
  rows.sort((a, b) => {
    const va = c.get(a), vb = c.get(b), d = va < vb ? -1 : va > vb ? 1 : 0;
    return (state.sort.desc ? -d : d) || a.sector.localeCompare(b.sector) || (FR[a.frict].ord - FR[b.frict].ord) || a.relTh - b.relTh;
  });
  $("list-body").innerHTML = rows.length
    ? rows.map((r) => `<tr data-id="${r.id}"${r.id === state.run ? ` class="selected"` : ""}>${cols.map((x) => `<td class="${x.cls ?? ""}${x.num ? " num" : ""}"${x.title ? ` title="${esc(x.title(r))}"` : ""}>${x.fmt(r)}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${cols.length}" class="empty">Żaden przebieg nie spełnia filtrów.</td></tr>`;
  const hits = rows.filter((r) => r.hits.length).length;
  $("st-count").textContent = `${rows.length} z ${base.length} przebiegów · ${hits} dochodzi do szlaku`;
}
$("list-head").addEventListener("click", (e) => {
  const th = e.target.closest("th"); if (!th) return;
  const k = th.dataset.k;
  state.sort = { k, desc: state.sort.k === k ? !state.sort.desc : ["runout_m", "area_ha", "max_pft_m", "hits", "trail_pft_max_m"].includes(k) };
  renderList();
});
$("list-body").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-id]"); if (tr) selectRun(tr.dataset.id, { scroll: false }); });
$("list").addEventListener("keydown", (e) => {
  if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
  const rows = [...$("list-body").querySelectorAll("tr[data-id]")];
  const i = rows.findIndex((r) => r.dataset.id === state.run);
  const n = rows[Math.max(0, Math.min(rows.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))];
  if (n) { e.preventDefault(); selectRun(n.dataset.id); }
});
$("list").tabIndex = 0;
const syncTh = () => { $("th-val").textContent = `${nf(S.thicknesses[+$("f-th").value])} m`; };
$("f-th").addEventListener("input", () => { syncTh(); renderList(); });
document.querySelectorAll(".f-fr, #f-hit").forEach((i) => i.addEventListener("change", renderList));
function resetFilters() { $("f-th").value = 8; document.querySelectorAll(".f-fr").forEach((i) => (i.checked = true)); $("f-hit").checked = false; syncTh(); renderList(); }

// ---------------------------------------------------------------- preview
function drawPreview() {
  const cv = $("prev-canvas"), run = runById.get(state.run);
  if (!run || $("w-prev").classList.contains("minimized")) return;
  const { w, h, k } = fitCanvas(cv);
  if (w < 8 || h < 8) return;
  const crop = fitCrop(runBox(run), w, h, 14);
  drawScene(cv.getContext("2d"), w, h, crop, run, { lw: k * Math.max(0.9, Math.min(2, w / crop.cw / 2.4)) });
  scaleBar(cv.getContext("2d"), w, h, crop, k);
}
function renderCard() {
  const r = runById.get(state.run); if (!r) return;
  const s = secById.get(r.sector);
  $("prev-title").textContent = `Podgląd — ${r.id}`;
  const cell = (k, v) => `<div><span>${k}</span><b>${v}</b></div>`;
  const hero = media.hero?.[r.id];
  $("prev-card").innerHTML = `
    <h3>${esc(r.sector)} · ${esc(s?.name)} <small>wystawa ${esc(s?.aspect)} · ${esc(s?.band)}</small></h3>
    <div class="grid">
      ${cell("Grubość płyty", `${nf(r.relTh)} m`)}${cell("Tarcie", FR[r.frict]?.short ?? r.frict)}${cell("Zasięg", `${nInt(r.runout_m)} m`)}
      ${cell("Powierzchnia", `${nf(r.area_ha)} ha`)}${cell("Maks. przepływ", `${nf(r.max_pft_m)} m`)}${cell("Maks. ciśnienie", `${nInt(r.max_ppr_kpa)} kPa`)}
      ${cell("Maks. prędkość", `${nf(r.max_pfv_ms)} m/s`)}${cell("Na szlaku", r.hits.length ? `${nf(r.trail_pft_max_m, 2)} m` : "—")}
    </div>
    <div class="hitline${r.hits.length ? "" : " none"}" title="${esc(hitsTitle(r))}">${r.hits.length
      ? "Szlak w zasięgu: " + hitsGrouped(r).map(({ t, n, pft }) => `${swatch(t)}${esc(trailLabel(t))} (odc. ${n.join(", ")}; do ${nf(Math.max(...pft.map((v) => v ?? 0)), 2)} m)`).join("; ")
      : "Ten przebieg nie dochodzi do żadnego szlaku."}</div>
    ${hero ? `<span class="hero-link" data-img="media/${esc(hero)}">▶ Render 3D tego przebiegu</span>` : ""}`;
  if (!$("st-sel").classList.contains("err")) $("st-sel").hidden = true;
  $("addr").textContent = `Biblioteka scenariuszy › Wystawa ${s?.aspect} › ${r.sector} ${s?.name ?? ""} › ${r.id}`;
}

// ---------------------------------------------------------------- heat map window
let heatMax = 0;
if (HEAT) for (const v of HEAT) if (v > heatMax) heatMax = v;
const RAMP = [[0, [255, 243, 176]], [0.25, [253, 196, 106]], [0.5, [242, 140, 56]], [0.75, [205, 78, 26]], [1, [110, 26, 4]]];
const rampAt = (t) => {
  for (let i = 1; i < RAMP.length; i++) if (t <= RAMP[i][0]) {
    const [t0, a] = RAMP[i - 1], [t1, b] = RAMP[i], f = (t - t0) / (t1 - t0);
    return a.map((v, j) => Math.round(v + (b[j] - v) * f));
  }
  return RAMP[RAMP.length - 1][1];
};
const heatT = (v) => (heatMax ? Math.log1p(v) / Math.log1p(heatMax) : 0);
const heatLayer = document.createElement("canvas"); heatLayer.width = W; heatLayer.height = H;
if (HEAT && heatMax) {
  const img = new ImageData(W, H);
  for (let i = 0; i < HEAT.length; i++) {
    const v = HEAT[i]; if (!v) continue;
    const t = heatT(v), c = rampAt(t), o = i * 4;
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = Math.round(110 + 135 * t);
  }
  heatLayer.getContext("2d").putImageData(img, 0, 0);
}
function heatLegend() {
  $("heat-ramp").style.background = `linear-gradient(to top, ${RAMP.map(([t, c]) => `rgb(${c}) ${t * 100}%`).join(", ")})`;
  const ticks = [1, 3, 10, 30, 100].filter((v) => v < heatMax * 0.8).concat(heatMax);
  $("heat-ticks").style.marginTop = "-152px";
  $("heat-ticks").style.height = "152px";
  $("heat-ticks").innerHTML = ticks.map((v) => `<span style="top:${(1 - heatT(v)) * 150 + 1}px">${v === heatMax ? `${v} (maks.)` : v}</span>`).join("");
  $("heat-status").textContent = heatMax ? `${S.count} symulacji · komórka 10 × 10 m · przepływ > 0,1 m` : "Mapa zasięgów: brak pliku library_heat.bin";
}
function drawHeat() {
  const cv = $("heat-canvas");
  if ($("w-heat").classList.contains("minimized")) return;
  const { w, h, k } = fitCanvas(cv);
  if (w < 8) return;
  const ctx = cv.getContext("2d"), crop = { x0: 0, y0: 0, cw: W, ch: H };
  drawBase(ctx, w, h, crop);
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(heatLayer, 0, 0, w, h);
  drawTrails(ctx, crop, w / W, 0.55 * k);
  const r = runById.get(state.run);
  if (r) {
    const img = new ImageData(W, H);
    paint(img.data, relCells(r.sector), [30, 60, 160, 200], [8, 20, 90, 255]);
    ovx.putImageData(img, 0, 0);
    ctx.drawImage(ov, 0, 0, w, h);
    const b = bboxOf("sec:" + r.sector, relCells(r.sector));
    if (b) {
      const s = w / W;
      ctx.strokeStyle = "#0b2a8f"; ctx.lineWidth = 1.5 * k; ctx.setLineDash([4 * k, 3 * k]);
      ctx.strokeRect((b.c0 - 6) * s, (b.r0 - 6) * s, (b.c1 - b.c0 + 13) * s, (b.r1 - b.r0 + 13) * s);
      ctx.setLineDash([]);
    }
  }
}
function heatCell(e) {
  const r = $("heat-canvas").getBoundingClientRect();
  const c = Math.floor(((e.clientX - r.left) / r.width) * W), row = Math.floor(((e.clientY - r.top) / r.height) * H);
  return c < 0 || c >= W || row < 0 || row >= H ? -1 : row * W + c;
}
const secAt = (i) => { const v = SEC8[i]; return v ? SECT.find((s) => s.index === v) : null; };
$("heat-canvas").addEventListener("pointermove", (e) => {
  const i = heatCell(e), tip = $("heat-tip");
  if (i < 0) { tip.hidden = true; return; }
  const s = secAt(i), v = HEAT?.[i] ?? 0;
  tip.innerHTML = `${v ? `<b>${v}</b> z ${S.count} symulacji` : "żadna symulacja tu nie dochodzi"}${s ? `<br>strefa startowa ${esc(s.id)} · ${esc(s.name)}` : ""}`;
  tip.hidden = false;
  const box = e.currentTarget.parentElement.getBoundingClientRect();
  tip.style.left = Math.min(box.width - 150, e.clientX - box.left + 12) + "px";
  tip.style.top = e.clientY - box.top + 14 + "px";
});
$("heat-canvas").addEventListener("pointerleave", () => ($("heat-tip").hidden = true));
$("heat-canvas").addEventListener("click", (e) => {
  const i = heatCell(e); if (i < 0) return;
  const s = secAt(i);
  if (s && runsBySec.has(s.id)) { selectSector(s.id); return; }
  if (!HEAT?.[i]) return;
  // which slopes reach this cell? pick the one with most runs here, and its thinnest such run
  const by = new Map();
  for (const r of S.runs) if (cellsOf(r).includes(i)) { const a = by.get(r.sector) ?? []; a.push(r); by.set(r.sector, a); }
  const best = [...by.entries()].sort((a, b) => b[1].length - a[1].length)[0];
  if (best) selectSector(best[0], best[1].sort((a, b) => a.relTh - b.relTh || FR[b.frict].ord - FR[a.frict].ord)[0].id);
});

// ---------------------------------------------------------------- matrix
function renderMatrix() {
  const p = $("p-macierz");
  if (p.hidden) return;
  const sid = state.sector ?? runById.get(state.run)?.sector, sec = secById.get(sid);
  const runs = runsBySec.get(sid) ?? [];
  if (!sec || !runs.length) { p.innerHTML = `<p class="empty">Wybierz stok w drzewie po lewej.</p>`; return; }
  let b = bboxOf("sec:" + sid, relCells(sid));
  for (const r of runs) b = union(b, bboxOf(r.id, cellsOf(r)));
  const bw = b.c1 - b.c0 + 1, bh = b.r1 - b.r0 + 1;
  const RH = 104, GAP = 4;
  const cw = Math.max(40, Math.floor((p.clientWidth - 30 - RH - 9 * GAP) / 9));
  const ch = Math.round(Math.min(150, Math.max(54, cw * Math.min(1.7, Math.max(0.62, bh / bw)))));
  const ro = runs.map((r) => r.runout_m), hits = runs.filter((r) => r.hits.length).length;
  const lo = runs.reduce((a, r) => (r.runout_m < a.runout_m ? r : a)), hi = runs.reduce((a, r) => (r.runout_m > a.runout_m ? r : a));
  let html = `<div class="mx-head"><h2>Macierz: ${esc(sid)} · ${esc(sec.name)}</h2><p>wiersze: tarcie, kolumny: grubość płyty, ten sam kadr</p></div>`;
  html += `<div class="mx" style="grid-template-columns:${RH}px repeat(9, ${cw}px)"><div></div>`;
  html += S.thicknesses.map((t) => `<div class="ch">${nf(t)} m</div>`).join("");
  for (const fr of FR_KEYS) {
    html += `<div class="rh"><i class="fr-dot" style="background:${FR[fr].color}"></i>${FR[fr].pl}<small>${fr}</small></div>`;
    for (const t of S.thicknesses) {
      const r = runById.get(runKey(sid, fr, t));
      html += r
        ? `<div class="cell${r.hits.length ? " hit" : ""}${r.id === state.run ? " selected" : ""}" data-id="${r.id}" title="${esc(r.id)}: zasięg ${nInt(r.runout_m)} m, ${r.hits.length ? `dochodzi do szlaku (${r.hits.length} odc.)` : "nie dochodzi do szlaku"}"><canvas style="height:${ch}px"></canvas><span class="ro">${nInt(r.runout_m)} m</span></div>`
        : `<div class="cell" style="height:${ch + 4}px"></div>`;
    }
  }
  html += `</div><div class="mx-legend"><span><i class="sw rel"></i>strefa startowa</span><span><i class="sw foot"></i>zasięg (przepływ &gt; 0,1 m)</span><span><i class="sw hit"></i>odcinek szlaku w zasięgu</span><span><i class="dot"></i>przebieg dochodzi do szlaku</span>
    <span>Zasięg od <b>${nInt(Math.min(...ro))} m</b> (${nf(lo.relTh)} m, ${FR[lo.frict].short}) do <b>${nInt(Math.max(...ro))} m</b> (${nf(hi.relTh)} m, ${FR[hi.frict].short}); do szlaku dochodzi <b>${hits} z ${runs.length}</b>.</span></div>`;
  html += chartSvg(runs, p.clientWidth - 30);
  p.innerHTML = html;
  const k = dpr();
  const base = document.createElement("canvas");
  base.width = cw * k; base.height = ch * k;
  const crop = fitCrop(b, base.width, base.height, 5);
  drawBase(base.getContext("2d"), base.width, base.height, crop);
  for (const cell of p.querySelectorAll(".cell[data-id]")) {
    const cv = cell.querySelector("canvas");
    cv.width = base.width; cv.height = base.height;
    drawScene(cv.getContext("2d"), cv.width, cv.height, crop, runById.get(cell.dataset.id), { base, lw: 0.5 * k });
  }
}
function chartSvg(runs, width) {
  const h = 210, m = { l: 58, r: 150, t: 22, b: 36 }, iw = width - m.l - m.r, ih = h - m.t - m.b;
  const ys = runs.map((r) => r.runout_m);
  let step = [25, 50, 100, 200, 250, 500].find((s) => (Math.max(...ys) - Math.min(...ys)) / s <= 5) ?? 500;
  const y0 = Math.floor(Math.min(...ys) / step) * step, y1 = Math.max(y0 + step, Math.ceil(Math.max(...ys) / step) * step);
  const t0 = S.thicknesses[0], t1 = S.thicknesses[S.thicknesses.length - 1];
  const X = (t) => m.l + ((t - t0) / (t1 - t0)) * iw, Y = (v) => m.t + ih - ((v - y0) / (y1 - y0)) * ih;
  let g = `<svg class="chart" width="${width}" height="${h}" viewBox="0 0 ${width} ${h}" role="img" aria-label="Zasięg a grubość płyty">`;
  g += `<text x="${m.l}" y="14" style="font-weight:700">Zasięg [m] a grubość płyty [m]</text>`;
  for (let v = y0; v <= y1 + 1e-6; v += step) g += `<line x1="${m.l}" x2="${m.l + iw}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e6e3d6"/><text x="${m.l - 6}" y="${Y(v) + 4}" text-anchor="end">${nInt(v)}</text>`;
  for (const t of S.thicknesses) g += `<text x="${X(t)}" y="${m.t + ih + 16}" text-anchor="middle">${nf(t)}</text>`;
  g += `<text x="${m.l + iw / 2}" y="${h - 4}" text-anchor="middle" fill="#555">grubość płyty [m]</text>`;
  FR_KEYS.forEach((fr, j) => {
    const rs = runs.filter((r) => r.frict === fr).sort((a, b) => a.relTh - b.relTh);
    if (!rs.length) return;
    g += `<polyline fill="none" stroke="${FR[fr].color}" stroke-width="2" points="${rs.map((r) => `${X(r.relTh)},${Y(r.runout_m)}`).join(" ")}"/>`;
    g += rs.map((r) => `<circle cx="${X(r.relTh)}" cy="${Y(r.runout_m)}" r="4" fill="${r.hits.length ? FR[fr].color : "#fff"}" stroke="${FR[fr].color}" stroke-width="1.6"><title>${esc(r.id)}: ${nInt(r.runout_m)} m</title></circle>`).join("");
    const ly = m.t + 10 + j * 18;
    g += `<line x1="${m.l + iw + 16}" x2="${m.l + iw + 36}" y1="${ly}" y2="${ly}" stroke="${FR[fr].color}" stroke-width="2"/><text x="${m.l + iw + 42}" y="${ly + 4}">${FR[fr].pl}</text>`;
  });
  const ly = m.t + 74;
  g += `<circle cx="${m.l + iw + 26}" cy="${ly}" r="4" fill="#555"/><text x="${m.l + iw + 42}" y="${ly + 4}">dochodzi do szlaku</text>`;
  g += `<circle cx="${m.l + iw + 26}" cy="${ly + 18}" r="4" fill="#fff" stroke="#555" stroke-width="1.6"/><text x="${m.l + iw + 42}" y="${ly + 22}">nie dochodzi</text>`;
  return g + `</svg>`;
}
$("p-macierz").addEventListener("click", (e) => { const c = e.target.closest(".cell[data-id]"); if (c) selectRun(c.dataset.id); });
function markMatrix() { document.querySelectorAll("#p-macierz .cell[data-id]").forEach((c) => c.classList.toggle("selected", c.dataset.id === state.run)); }

// ---------------------------------------------------------------- representative scenarios
function curate() {
  const all = S.runs, hit = all.filter((r) => r.hits.length), miss = all.filter((r) => !r.hits.length);
  const maxBy = (a, f) => a.reduce((x, y) => (f(y) > f(x) ? y : x), a[0]);
  const out = [];
  const add = (r, kind, desc) => { if (r && !out.some((p) => p.r.id === r.id) && out.length < 12) out.push({ r, kind, desc }); };
  const fr = (r) => FR[r.frict]?.pl ?? r.frict;
  const trailsOf = (r) => { const t = [...new Set(r.hits.map((id) => trailLabel(segById.get(id)?.trail)))]; return t.length > 2 ? `${t.slice(0, 2).join(", ")} i ${t.length - 2} inne` : t.join(", "); };
  // per slope: thinnest slab that reaches a trail
  const thr = libSecs.map((s) => {
    const h = (runsBySec.get(s.id) ?? []).filter((r) => r.hits.length).sort((a, b) => a.relTh - b.relTh || FR[b.frict].ord - FR[a.frict].ord);
    return { s, r: h[0] };
  }).filter((x) => x.r);
  const late = thr.filter((x) => x.r.relTh > S.thicknesses[0] + 1e-6).sort((a, b) => b.r.relTh - a.r.relTh);
  for (const x of late.slice(0, 2)) add(x.r, "Próg płyty", `Ten stok dochodzi do szlaku dopiero od ${nf(x.r.relTh)} m płyty (${fr(x.r)}); cieńsze płyty zatrzymują się wcześniej.`);
  const early = thr.filter((x) => x.r.relTh <= S.thicknesses[0] + 1e-6).sort((a, b) => a.r.area_ha - b.r.area_ha)[0];
  if (early) add(early.r, "Cienka płyta wystarczy", `Już ${nf(early.r.relTh)} m płyty i ${nf(early.r.area_ha)} ha zasięgu wystarcza, by dojść do szlaku (${trailsOf(early.r)}).`);
  // friction decides at the same slab
  let fd = null;
  for (const s of libSecs) for (const t of S.thicknesses) {
    const rs = FR_KEYS.map((f) => runById.get(runKey(s.id, f, t))).filter(Boolean);
    const h = rs.filter((r) => r.hits.length), n = rs.filter((r) => !r.hits.length);
    if (h.length && n.length) { const d = h[0].runout_m - n[0].runout_m; if (!fd || d > fd.d) fd = { d, h: h[0], n: n[0] }; }
  }
  if (fd) add(fd.h, "Tarcie decyduje", `Przy tej samej płycie ${nf(fd.h.relTh)} m wariant „${fr(fd.h)}” dochodzi do szlaku, a „${fr(fd.n)}” zatrzymuje się ${nInt(fd.h.runout_m - fd.n.runout_m)} m wcześniej.`);
  const lr = maxBy(all, (r) => r.runout_m);
  add(lr, "Najdłuższy zasięg", `${nInt(lr.runout_m)} m od strefy startowej przy płycie ${nf(lr.relTh)} m (${fr(lr)}).`);
  const tp = maxBy(hit, (r) => r.trail_pft_max_m);
  if (tp) add(tp, "Najgrubszy przepływ na szlaku", `Do ${nf(tp.trail_pft_max_m, 2)} m śniegu w ruchu na szlaku (${trailsOf(tp)}).`);
  const ms = maxBy(hit, (r) => r.hits.length);
  if (ms) add(ms, "Najwięcej odcinków szlaku", `Zasięg obejmuje naraz ${ms.hits.length} odcinków szlaków: ${trailsOf(ms)}.`);
  const lm = maxBy(miss, (r) => r.runout_m);
  if (lm) add(lm, "Daleko, ale obok szlaku", `${nInt(lm.runout_m)} m zasięgu, a żaden odcinek szlaku nie leży w śladzie. Długość zasięgu to nie to samo co zagrożenie szlaku.`);
  // growth of trail exposure with slab thickness (same friction)
  let gr = null;
  for (const s of libSecs) for (const f of FR_KEYS) {
    const a = runById.get(runKey(s.id, f, S.thicknesses[0])), b = runById.get(runKey(s.id, f, S.thicknesses[S.thicknesses.length - 1]));
    if (a && b) { const d = b.hits.length - a.hits.length; if (!gr || d > gr.d) gr = { d, a, b }; }
  }
  if (gr && gr.d > 0) add(gr.b, "Płyta rośnie, szlak w zasięgu też", `Przy ${nf(gr.a.relTh)} m: ${gr.a.hits.length} odc. szlaku, przy ${nf(gr.b.relTh)} m: ${gr.b.hits.length} odc. (${fr(gr.b)}).`);
  const pp = maxBy(all, (r) => r.max_ppr_kpa);
  add(pp, "Największe ciśnienie", `Maks. ciśnienie ${nInt(pp.max_ppr_kpa)} kPa przy prędkości do ${nf(pp.max_pfv_ms)} m/s.`);
  const held = SUR?.held_out_sectors?.find((s) => runById.has(runKey(s, "samosAT", 2)));
  if (held) add(runById.get(runKey(held, "samosAT", 2)), "Stok testowy surogatu", `Stok wyłączony z treningu sieci U-Net; IoU surogatu na tym stoku: ${nf(SUR.iou_by_sector?.[held] ?? SUR.iou_mean, 3)}.`);
  const sr = all.reduce((x, y) => (y.runout_m < x.runout_m ? y : x));
  add(sr, "Najkrótszy zasięg", `Tylko ${nInt(sr.runout_m)} m i ${nf(sr.area_ha)} ha: ${sr.hits.length ? "mimo to dochodzi do szlaku" : "nie dochodzi do szlaku"}.`);
  const la = maxBy(all, (r) => r.area_ha);
  add(la, "Największa powierzchnia", `${nf(la.area_ha)} ha śladu lawiny, ${nInt(la.runout_m)} m zasięgu.`);
  for (const x of thr) add(x.r, "Najcieńsza płyta, która dochodzi", `Od ${nf(x.r.relTh)} m płyty ten stok dochodzi do szlaku (${trailsOf(x.r)}).`);
  return out;
}
let reps = null;
function renderReps() {
  const p = $("p-reprezentatywne");
  if (p.hidden) return;
  reps ??= curate();
  const heroes = Object.entries(media.hero ?? {});
  p.innerHTML = `<div class="mx-head"><h2>Reprezentatywne scenariusze</h2><p>wybrane automatycznie z ${S.count} przebiegów; kliknij kartę, żeby otworzyć przebieg</p></div>
    <div class="cards">${reps.map(({ r, kind, desc }, i) => `<div class="rcard${r.id === state.run ? " selected" : ""}" data-id="${r.id}" data-i="${i}"><canvas></canvas><div class="rc-b"><div class="rc-k">${esc(kind)}</div><div class="rc-t" title="${esc(r.id)}">${esc(r.sector)} · ${esc(secById.get(r.sector)?.name)} · ${nf(r.relTh)} m · ${FR[r.frict]?.short}</div><div class="rc-d">${esc(desc)}</div></div></div>`).join("")}</div>
    ${heroes.length ? `<h3 class="sec-h">Rendery 3D wybranych przebiegów</h3><p class="sec-p">AvaFrame com1DFA na terenie GUGiK NMT; kliknij, żeby powiększyć.</p>
    <div class="heroes">${heroes.map(([id, f]) => `<figure data-img="media/${esc(f)}" data-id="${esc(id)}"><img src="media/${esc(f)}" alt="Render 3D przebiegu ${esc(id)}" loading="lazy"><figcaption>${esc(id)} · ${esc(secById.get(id.split("_")[0])?.name)}</figcaption></figure>`).join("")}</div>` : ""}`;
  for (const c of p.querySelectorAll(".rcard")) {
    const cv = c.querySelector("canvas"), r = runById.get(c.dataset.id);
    const { w, h, k } = fitCanvas(cv);
    drawScene(cv.getContext("2d"), w, h, fitCrop(runBox(r), w, h, 8), r, { lw: 0.65 * k });
  }
}
$("p-reprezentatywne").addEventListener("click", (e) => {
  const f = e.target.closest("figure[data-img]");
  if (f) { lightbox(f.dataset.img); if (runById.has(f.dataset.id)) selectRun(f.dataset.id); return; }
  const c = e.target.closest(".rcard"); if (c) selectRun(c.dataset.id);
});
function markCards() { document.querySelectorAll("#p-reprezentatywne .rcard").forEach((c) => c.classList.toggle("selected", c.dataset.id === state.run)); }

// ---------------------------------------------------------------- training & calibration
const WIP = `<span class="wip">w toku</span>`;
const kv = (rows) => `<dl class="kv">${rows.filter(Boolean).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;
const imgs = (list, alt) => (list ?? []).map((f) => `<img class="tr-img" src="media/${esc(f)}" alt="${esc(alt)}" data-img="media/${esc(f)}">`).join("");
function rlCurve(curve, width = 330) {
  const KEYS = ["train", "test", "train_reward", "val_reward", "eval_reward"];
  const pts = (curve ?? []).filter((c) => KEYS.some((k) => c[k] != null));
  if (pts.length < 2) return "";
  const h = 150, m = { l: 40, r: 10, t: 12, b: 26 }, iw = width - m.l - m.r, ih = h - m.t - m.b;
  const xs = pts.map((c) => c.episodes ?? c.it), keys = KEYS.filter((k) => pts.some((c) => c[k] != null));
  const vs = pts.flatMap((c) => keys.map((k) => c[k]).filter((v) => v != null));
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...vs), y1 = Math.max(...vs) + 1e-9;
  const X = (v) => m.l + ((v - x0) / (x1 - x0 || 1)) * iw, Y = (v) => m.t + ih - ((v - y0) / (y1 - y0)) * ih;
  const col = { train: "#9aa6bd", test: "#1f5fd1", train_reward: "#9aa6bd", val_reward: "#e08a1e", eval_reward: "#1f5fd1" }, pl = { train: "nagroda: trening", test: "nagroda: test", train_reward: "trening", val_reward: "walidacja", eval_reward: "test" };
  let g = `<svg class="chart" width="${width}" height="${h}" viewBox="0 0 ${width} ${h}">`;
  g += `<text x="${m.l - 4}" y="${m.t + 4}" text-anchor="end">${nf(y1, 2)}</text><text x="${m.l - 4}" y="${m.t + ih}" text-anchor="end">${nf(y0, 2)}</text>`;
  g += `<text x="${m.l}" y="${h - 6}">${nInt(x0)}</text><text x="${m.l + iw}" y="${h - 6}" text-anchor="end">${nInt(x1)} epizodów</text>`;
  keys.forEach((k, j) => {
    g += `<polyline fill="none" stroke="${col[k]}" stroke-width="1.8" points="${pts.filter((c) => c[k] != null).map((c) => `${X(c.episodes ?? c.it)},${Y(c[k])}`).join(" ")}"/>`;
    g += `<text x="${m.l + 8 + j * 110}" y="${m.t + 4}" fill="${col[k]}" style="font-weight:700">${pl[k]}</text>`;
  });
  return g + `</svg>`;
}
const PLANNER_PL = { rl: "polityka RL", greedy_voi: "silnik (zachłanny VOI)", voi: "silnik (zachłanny VOI)", fixed: "stała trasa", fixed_route: "stała trasa", random: "losowo" };
function renderTraining() {
  const p = $("p-trening");
  if (p.hidden) return;
  const sur = SUR
    ? kv([
        ["Model", esc(SUR.model)],
        ["Trening", `${nInt(SUR.trained_on_runs)} przebiegów AvaFrame z ${SUR.train_sectors} stoków`],
        ["Stoki testowe", `${(SUR.held_out_sectors ?? []).join(", ")} (${SUR.held_out_runs} przebiegów, wyłączone z treningu)`],
        ["IoU zasięgu (średnio)", `<b class="big">${nf(SUR.iou_mean, 3)}</b>`],
        SUR.iou_by_sector && ["IoU na stokach", Object.entries(SUR.iou_by_sector).map(([k, v]) => `${k}: ${nf(v, 3)}`).join(" · ")],
        ["Czas jednej mapy", `<b>${nf(SUR.ms_per_map_gpu, 2)} ms</b> (GPU) zamiast <b>${nf(SUR.s_per_run_avaframe, 1)} s</b> (AvaFrame, 1 rdzeń)`],
      ]) + `<p class="note" title="${esc(SUR.note ?? "")}">${esc(SUR.iou_definition ?? "")}. ${esc(SUR.note ?? "")}</p>`
    : WIP;
  const best = CAL?.best, row = CAL?.table?.find((t) => t.frictModel === best?.frictModel && t.relTh === best?.relTh && t.iou === best?.iou);
  const cal = CAL
    ? kv([
        ["Zdarzenie", `${esc(CAL.event)}, ${esc(CAL.date)}`],
        ["Przebiegów", `${CAL.runs} (${esc(CAL.model)})`],
        best && ["Najlepsze dopasowanie", `<b>${FR[best.frictModel]?.pl ?? best.frictModel} (${esc(best.frictModel)}), płyta ${nf(best.relTh)} m</b>`],
        best && ["IoU ze śladem zdarzenia", `<b class="big">${nf(best.iou, 3)}</b>`],
        best && ["Błąd zasięgu", `<b>${best.runout_error_m > 0 ? "+" : ""}${nInt(best.runout_error_m)} m</b>${row ? ` (symulacja ${nInt(row.runout_sim_m)} m, obserwacja ${nInt(row.runout_obs_m)} m)` : ""}`],
        best?.dep_hit != null && ["Pokrycie depozytu", `${nInt(best.dep_hit * 100)}%`],
      ]) + `<p class="note">${esc(CAL.assumptions ?? "")}. ${esc(CAL.note ?? "")}.${CAL.source?.doi ? ` Dane zdarzenia: ${esc(CAL.source.event_data ?? "")}, DOI ${esc(CAL.source.doi)}, ${esc(CAL.source.licence ?? "")}.` : ""}</p>`
    : WIP;
  let rl = WIP;
  if (RL) {
    const mt = RL.metrics ?? {};
    const planners = Object.entries(mt).filter(([, v]) => v && typeof v === "object");
    rl = kv([
      RL.algo && ["Algorytm", esc(RL.algo)],
      RL.env_episodes_trained != null && ["Epizody treningu", nInt(RL.env_episodes_trained)],
      RL.train_minutes != null && ["Czas treningu", `${nf(RL.train_minutes)} min${RL.gpu ? ` (${esc(RL.gpu)})` : ""}`],
      RL.eval_mornings != null && ["Poranki testowe", `${nInt(RL.eval_mornings)}${RL.budget_min ? `, lot do ${RL.budget_min} min` : ""}`],
      RL.verdict && ["Wniosek", `<b>${esc(RL.verdict)}</b>`],
    ]) + (planners.length
      ? `<div class="listview"><table><thead><tr><th>Planista</th><th class="num">Spadek<br>niepewności</th><th class="num">Rozwiązane<br>„nie wiem”</th><th class="num">Wykryte<br>zagrożenia</th></tr></thead><tbody>${planners.map(([k, v]) => `<tr><td>${esc(PLANNER_PL[k] ?? k)}</td><td class="num">${v.uncertainty_drop_pct != null ? nf(v.uncertainty_drop_pct) + "%" : "—"}</td><td class="num">${v.unknowns_resolved ?? "—"}</td><td class="num">${v.threats_caught ?? "—"}</td></tr>`).join("")}</tbody></table></div>`
      : "") + (media.rl?.length ? "" : rlCurve(RL.curve, 400)) + (RL.note ? `<p class="note">${esc(RL.note)}</p>` : "");
  }
  const pr = PROOF;
  const bar = (label, ours, base, oursL, baseL, unit = "") => {
    const mx = Math.max(ours, base, 1);
    return `<span>${label}<br><small>${oursL} / ${baseL}</small></span><div><div class="bar"><i class="ours" style="width:${(ours / mx) * 100}%"></i><b>${nInt(ours)}${unit}</b></div><div class="bar" style="margin-top:2px"><i style="width:${(base / mx) * 100}%"></i><b>${nInt(base)}${unit}</b></div></div>`;
  };
  const proof = pr
    ? kv([
        ["Poranki × stoki", `${pr.mornings} × ${pr.slopes} = ${nInt(pr.sector_mornings)}`],
        ["Stoki-poranki zagrażające", nInt(pr.threatening)],
        pr.weather_source && ["Pogoda", esc(pr.weather_source)],
      ]) + `<div class="bars">
        ${pr.misses ? bar("Pominięte zagrożenia", pr.misses.avalauncher, pr.misses.baseline_3d, "Avalauncher", "próg 3 dni") : ""}
        ${pr.false_alarms ? bar("Fałszywe alarmy", pr.false_alarms.avalauncher, pr.false_alarms.baseline_3d, "Avalauncher", "próg 3 dni") : ""}
        ${pr.uncertainty_drop ? bar("Spadek niepewności po 20 min lotu", pr.uncertainty_drop.plan, pr.uncertainty_drop.fixed_route, "plan", "stała trasa", "%") : ""}
      </div><p class="note">Próg 3 dni: ${esc(pr.baseline ?? "")}. Stała trasa: ${esc(pr.fixed_route_rule ?? "")}. Test logiki: ${esc(pr.note ?? "")}; ${esc(pr.model_error ?? "")}.</p>`
    : WIP;
  p.innerHTML = `<div class="mx-head"><h2>Trening i kalibracja</h2><p>tylko liczby z plików wyników; brak pliku = „w toku”</p></div>
  <div class="tr-grid">
    <fieldset class="group"><legend>Surogat U-Net: szybkie przybliżenie AvaFrame</legend>${imgs(media.surrogate, "Porównanie AvaFrame i surogatu")}${sur}</fieldset>
    <fieldset class="group"><legend>Kalibracja na prawdziwym zdarzeniu</legend>${imgs(media.kalibracja, "Kalibracja: AvaFrame a obserwowany ślad")}${cal}</fieldset>
    <fieldset class="group"><legend>Plan przelotu: uczenie ze wzmocnieniem</legend>${imgs(media.rl, "Uczenie ze wzmocnieniem")}${rl}</fieldset>
    <fieldset class="group"><legend>Dowód: ${pr?.mornings ?? "—"} poranków, scenariusz syntetyczny</legend>${proof}</fieldset>
  </div>`;
}
$("p-trening").addEventListener("click", (e) => { const i = e.target.closest("[data-img]"); if (i) lightbox(i.dataset.img); });
$("prev-card").addEventListener("click", (e) => { const i = e.target.closest("[data-img]"); if (i) lightbox(i.dataset.img); });
function lightbox(src) {
  const d = document.createElement("div");
  d.className = "lightbox";
  d.innerHTML = `<img src="${esc(src)}" alt="">`;
  d.addEventListener("click", () => d.remove());
  document.body.append(d);
}

// ---------------------------------------------------------------- tabs + selection
function showTab(t) {
  state.tab = t;
  document.querySelectorAll(".tab[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === t)));
  for (const id of ["lista", "macierz", "reprezentatywne", "trening"]) $("p-" + id).hidden = id !== t;
  if (t === "macierz") renderMatrix();
  if (t === "reprezentatywne") renderReps();
  if (t === "trening") renderTraining();
}
document.querySelectorAll(".tab[data-tab]").forEach((b) => b.addEventListener("click", () => { if (READY) showTab(b.dataset.tab); }));

function selectSector(sid, runId) {
  state.sector = sid && runsBySec.has(sid) ? sid : null;
  markTree();
  renderList();
  const keep = state.run && (!state.sector || runById.get(state.run)?.sector === state.sector);
  selectRun(runId ?? (keep ? state.run : defaultRun(state.sector)), { matrix: true });
}
function selectRun(id, { scroll = true, matrix = false } = {}) {
  const r = runById.get(id);
  if (!r) return;
  if (state.sector && state.sector !== r.sector) { state.sector = r.sector; markTree(); renderList(); matrix = true; }
  const prevSec = runById.get(state.run)?.sector;
  state.run = id;
  document.querySelectorAll("#list-body tr.selected").forEach((t) => t.classList.remove("selected"));
  const tr = document.querySelector(`#list-body tr[data-id="${id}"]`);
  if (tr) { tr.classList.add("selected"); if (scroll) tr.scrollIntoView({ block: "nearest" }); }
  renderCard();
  drawPreview();
  drawHeat();
  if (matrix || prevSec !== r.sector) renderMatrix(); else markMatrix();
  markCards();
}
function redrawFor(w) {
  renderTasks();
  requestAnimationFrame(() => {
    if (w.id === "w-prev") drawPreview();
    if (w.id === "w-heat") drawHeat();
    if (w.id === "w-lib") { if (state.tab === "macierz") renderMatrix(); if (state.tab === "reprezentatywne") renderReps(); }
  });
}
let rto = 0;
addEventListener("resize", () => { clearTimeout(rto); rto = setTimeout(() => { drawPreview(); drawHeat(); if (state.tab === "macierz") renderMatrix(); }, 120); });

// ---------------------------------------------------------------- start
$("lib-title").textContent = `Biblioteka scenariuszy — ${nInt(S.count)} symulacji`;
$("w-lib").dataset.title = `Biblioteka scenariuszy — ${nInt(S.count)} symulacji`;
$("about-body").innerHTML = `<p><b>${nInt(S.count)} symulacji lawin</b> policzonych z góry modelem ${esc(S.model ?? "AvaFrame com1DFA")} (${esc(ranOn)}).</p>
  <p>${libSecs.length} stref startowych × ${S.thicknesses.length} grubości płyty (${nf(S.thicknesses[0])}–${nf(S.thicknesses[S.thicknesses.length - 1])} m) × ${S.frictions.length} warianty tarcia (małe, średnie, duże lawiny). Zasięg to komórki 10 × 10 m, w których maksymalna grubość przepływu przekracza ${nf(S.threshold_pft_m ?? 0.1)} m.</p>
  <p>Avalauncher porównuje każdy pomiar drona z tą biblioteką i wskazuje stoki, które mogą zagrozić szlakom.</p>
  <p class="note">Symulacje: AvaFrame com1DFA 2.1 na DGX Spark · Teren: GUGiK NMT · Szlaki: © OSM · Grubość płyty i przeloty: scenariusz syntetyczny</p>
  <div style="text-align:right"><button class="xp-btn default" data-close="about">OK</button></div>`;
buildTree();
heatLegend();
syncTh();
renderTasks();
const start = libSecs
  .map((s) => {
    const rs = runsBySec.get(s.id) ?? [], h = rs.filter((r) => r.hits.length);
    const hl = rs.map((r) => r.hits.length), ro = rs.map((r) => r.runout_m);
    // most striking slope: strongest relative runout growth, mixed trail outcome, growing trail exposure
    return { s, score: ((Math.max(...ro) - Math.min(...ro)) / Math.max(1, Math.min(...ro))) * 100 + (h.length && h.length < rs.length ? 60 : 0) + (Math.max(...hl) - Math.min(...hl)) * 10 };
  })
  .sort((a, b) => b.score - a.score)[0]?.s;
selectSector(start?.id ?? null);
READY = true;
if (["lista", "macierz", "reprezentatywne", "trening"].includes(pendingTab)) showTab(pendingTab);
new ResizeObserver(() => drawPreview()).observe(document.querySelector(".prev-map"));
new ResizeObserver(() => drawHeat()).observe(document.querySelector(".heat-map"));

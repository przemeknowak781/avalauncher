// Luna-style desktop shell: windows, taskbar, start menu, tray balloons, dialogs, splash.
// Pure DOM, no dependencies. app.js wires the avalanche logic into it.

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const desktop = document.getElementById("desktop");
const taskButtons = document.getElementById("task-buttons");
const startBtn = document.getElementById("start-btn");
const startMenu = document.getElementById("start-menu");
const svg = (id, cls = "") => `<svg class="${cls}" aria-hidden="true"><use href="#${id}"/></svg>`;
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// ---------- actions ----------
const actions = {};
export function registerActions(map) { Object.assign(actions, map); }
export function run(name, el) { actions[name]?.(el); }

// ---------- windows ----------
const wins = new Map(); // id -> { el, btn, min, closed, max, prev }
let z = 20;
let userMoved = false;

for (const el of desktop.querySelectorAll(".window:not(.dialog)")) {
  const id = el.id;
  const btn = document.createElement("button");
  btn.className = "task-btn";
  btn.innerHTML = `${svg(el.dataset.icon)}<span>${esc(el.dataset.title)}</span>`;
  btn.title = el.dataset.title;
  btn.addEventListener("click", () => {
    const w = wins.get(id);
    if (w.min) restore(id);
    else if (el.classList.contains("active")) minimize(id);
    else focus(id);
  });
  taskButtons.appendChild(btn);
  const startMin = el.dataset.start === "min"; // lives on the taskbar until opened
  if (startMin) { btn.classList.add("min"); el.classList.add("is-hidden"); }
  wins.set(id, { el, btn, min: startMin, closed: false, max: false, prev: null });
  wireWindow(el, id);
}

function wireWindow(el, id) {
  el.addEventListener("pointerdown", () => focus(id), true);
  el.querySelector(".tb-min")?.addEventListener("click", (e) => { e.stopPropagation(); minimize(id); });
  el.querySelector(".tb-max")?.addEventListener("click", (e) => { e.stopPropagation(); toggleMax(id); });
  el.querySelector(".tb-close")?.addEventListener("click", (e) => { e.stopPropagation(); close(id); });
  const bar = el.querySelector(".title-bar");
  bar.addEventListener("dblclick", (e) => { if (!e.target.closest(".title-controls")) toggleMax(id); });
  draggable(el, bar, () => wins.get(id)?.max);
}

function draggable(el, handle, locked = () => false) {
  handle.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || e.target.closest(".title-controls") || locked()) return;
    e.preventDefault();
    const sx = e.clientX, sy = e.clientY, ox = el.offsetLeft, oy = el.offsetTop;
    handle.setPointerCapture(e.pointerId);
    const move = (ev) => {
      const dw = desktop.clientWidth, dh = desktop.clientHeight;
      const x = Math.min(dw - 80, Math.max(80 - el.offsetWidth, ox + ev.clientX - sx));
      const y = Math.min(dh - 30, Math.max(0, oy + ev.clientY - sy));
      el.style.left = `${x}px`; el.style.top = `${y}px`;
      userMoved = true;
    };
    const up = () => { handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", up); };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", up);
  });
}

export function focus(id) {
  const w = wins.get(id);
  if (!w) return;
  for (const [k, o] of wins) {
    o.el.classList.toggle("active", k === id);
    o.btn.classList.toggle("active", k === id && !o.min);
  }
  desktop.querySelectorAll(".window.dialog").forEach((d) => d.classList.remove("active"));
  w.el.style.zIndex = ++z;
}

function focusTopmost() {
  const open = [...wins.entries()].filter(([, o]) => !o.min && !o.closed).sort((a, b) => b[1].el.style.zIndex - a[1].el.style.zIndex);
  if (open.length) focus(open[0][0]);
  else for (const o of wins.values()) { o.el.classList.remove("active"); o.btn.classList.remove("active"); }
}

function zoomTo(el, target, out) {
  if (reduced || !el.animate) return Promise.resolve();
  const a = el.getBoundingClientRect(), b = target.getBoundingClientRect();
  const t = `translate(${b.left - a.left}px, ${b.top - a.top}px) scale(${b.width / a.width}, ${b.height / a.height})`;
  const frames = [{ transform: "none", opacity: 1 }, { transform: t, opacity: 0.2 }];
  el.style.transformOrigin = "0 0";
  return el.animate(out ? frames : frames.reverse(), { duration: 200, easing: "ease-in-out" }).finished.catch(() => {});
}

export async function minimize(id) {
  const w = wins.get(id);
  if (!w || w.min) return;
  w.min = true;
  w.btn.classList.add("min"); w.btn.classList.remove("active");
  await zoomTo(w.el, w.btn, true);
  w.el.classList.add("is-hidden");
  focusTopmost();
}

export async function restore(id) {
  const w = wins.get(id);
  if (!w) return;
  if (w.closed) { w.closed = false; w.btn.hidden = false; }
  const wasMin = w.min;
  w.min = false;
  w.btn.classList.remove("min");
  w.el.classList.remove("is-hidden");
  focus(id);
  if (wasMin) await zoomTo(w.el, w.btn, false);
}
export const open = restore;

export function close(id) {
  const w = wins.get(id);
  if (!w) return;
  w.closed = true; w.min = true;
  w.el.classList.add("is-hidden");
  w.btn.hidden = true;
  focusTopmost();
}

export function toggleMax(id, force) {
  const w = wins.get(id);
  if (!w) return;
  const on = force ?? !w.max;
  if (on === w.max) { restore(id); return; }
  if (on) {
    w.prev = { left: w.el.style.left, top: w.el.style.top, width: w.el.style.width, height: w.el.style.height };
    Object.assign(w.el.style, { left: "0px", top: "0px", width: `${desktop.clientWidth}px`, height: `${desktop.clientHeight}px` });
  } else if (w.prev) Object.assign(w.el.style, w.prev);
  w.max = on;
  w.el.classList.toggle("maximized", on);
  restore(id);
}

export function showDesktop() {
  const anyOpen = [...wins.values()].some((o) => !o.min && !o.closed);
  for (const [id, o] of wins) {
    if (o.closed) continue;
    if (anyOpen) minimize(id); else restore(id);
  }
}

// Default composition: big square-ish map on the left, three stacked panels on the right.
export function layout(force = false) {
  if (userMoved && !force) return;
  const dw = desktop.clientWidth, dh = desktop.clientHeight, m = 10;
  const set = (id, x, y, w, h) => {
    const o = wins.get(id);
    if (!o) return;
    if (o.max) { o.max = false; o.el.classList.remove("maximized"); }
    Object.assign(o.el.style, { left: `${Math.round(x)}px`, top: `${Math.round(y)}px`, width: `${Math.round(w)}px`, height: `${Math.round(h)}px` });
  };
  if (dw < 980) { // narrow screens: cascade
    const w = dw - 2 * m;
    ["w-map", "w-sit", "w-sec", "w-plan", "w-imgw"].forEach((id, i) => set(id, m, m + i * 34, w, Math.min(dh - 2 * m - i * 34, 640)));
  } else {
    const strip = 70; // leaves the desktop note visible under the map
    const mapH = dh - m - strip;
    const side = mapH - 116; // title + menubar + legend + status bar
    const mapW = Math.max(460, Math.min(side + 18, dw * 0.52));
    const rx = m + mapW + m, rw = dw - rx - m;
    const avail = dh - 4 * m;
    const h1 = Math.round(avail * 0.42), h2 = Math.round(avail * 0.3), h3 = avail - h1 - h2;
    set("w-map", m, m, mapW, mapH);
    set("w-sit", rx, m, rw, h1);
    set("w-sec", rx, 2 * m + h1, rw, h2);
    set("w-plan", rx, 3 * m + h1 + h2, rw, h3);
    set("w-imgw", rx, 2 * m + h1, rw, h2 + h3 + m); // opens over the two lower panels, never over the map
  }
  if (force) userMoved = false;
}
export function windowRect(id) { return wins.get(id)?.el.getBoundingClientRect(); }

window.addEventListener("resize", () => {
  layout();
  for (const [id, o] of wins) if (o.max) { o.max = false; toggleMax(id, true); }
});

// ---------- delegated clicks: data-open / data-action, menus ----------
document.addEventListener("click", (e) => {
  const opener = e.target.closest("[data-open]");
  const act = e.target.closest("[data-action]");
  const inStart = e.target.closest("#start-menu");
  if (e.target.closest(".desk-icon")) return; // desktop icons open on double click
  if (opener || act) {
    closeStart(); closeMenus();
    if (opener) restore(opener.dataset.open);
    if (act) run(act.dataset.action, act);
    return;
  }
  if (!inStart && !e.target.closest("#start-btn")) closeStart();
  const head = e.target.closest(".menu-head");
  if (head) {
    const menu = head.parentElement, was = menu.classList.contains("open");
    closeMenus();
    if (!was) menu.classList.add("open");
  } else if (!e.target.closest(".menu-pop")) closeMenus();
});
document.addEventListener("pointerover", (e) => {
  const head = e.target.closest(".menu-head");
  if (!head) return;
  const bar = head.closest(".menubar");
  if (bar.querySelector(".menu.open") && !head.parentElement.classList.contains("open")) {
    closeMenus(); head.parentElement.classList.add("open");
  }
});
function closeMenus() { document.querySelectorAll(".menu.open").forEach((m) => m.classList.remove("open")); }

for (const icon of desktop.querySelectorAll(".desk-icon")) {
  icon.addEventListener("dblclick", () => {
    if (icon.dataset.open) restore(icon.dataset.open);
    if (icon.dataset.action) run(icon.dataset.action, icon);
  });
  icon.addEventListener("keydown", (e) => { if (e.key === "Enter") icon.dispatchEvent(new MouseEvent("dblclick")); });
}

// ---------- start menu ----------
function closeStart() { startMenu.hidden = true; startBtn.setAttribute("aria-expanded", "false"); }
startBtn.addEventListener("click", () => {
  const openNow = startMenu.hidden;
  startMenu.hidden = !openNow;
  startBtn.setAttribute("aria-expanded", String(openNow));
  if (openNow) { startMenu.classList.remove("opening"); void startMenu.offsetWidth; startMenu.classList.add("opening"); }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeStart(); closeMenus(); }
});
export function openStart() { if (startMenu.hidden) startBtn.click(); }

// ---------- tray ----------
const clock = document.getElementById("clock");
function tick() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" });
  clock.title = now.toLocaleDateString("pl-PL", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  clock.dateTime = now.toISOString();
}
tick();
setInterval(tick, 10000);

export function setTray(name, { state, title }) {
  const el = document.getElementById(`tray-${name}`);
  if (!el) return;
  el.dataset.state = state;
  el.title = title;
  el.setAttribute("aria-label", title);
  const badge = el.querySelector(".badge use");
  if (badge) badge.setAttribute("href", state === "ok" ? "#i-badge-ok" : "#i-badge-warn");
}

// ---------- balloons ----------
const queue = [];
let current = null;
let balloonsHeld = true;
export function balloon(opts) {
  queue.push(opts);
  if (!current && !balloonsHeld) nextBalloon();
}
export function clearBalloons() { queue.length = 0; if (current) current.dismiss(true); }
function nextBalloon() {
  const o = queue.shift();
  if (!o) { current = null; return; }
  const el = document.createElement("div");
  el.className = "balloon";
  el.setAttribute("role", "status");
  el.innerHTML = `<div class="b-head">${svg(o.icon ?? "i-info")}<span>${esc(o.title)}</span></div><button class="b-close" aria-label="Zamknij"></button>${o.text ? `<p>${esc(o.text)}</p>` : ""}`;
  document.getElementById("screen").appendChild(el);
  const anchor = document.querySelector(o.anchor ?? "#tray-drone").getBoundingClientRect();
  const right = Math.max(6, innerWidth - (anchor.left + anchor.width / 2) - 24);
  el.style.right = `${right}px`;
  el.style.bottom = `${innerHeight - anchor.top + 14}px`;
  requestAnimationFrame(() => el.classList.add("show"));
  let gone = false;
  const dismiss = (instant) => {
    if (gone) return;
    gone = true; clearTimeout(timer);
    el.classList.remove("show");
    setTimeout(() => { el.remove(); current = null; if (!instant || queue.length) setTimeout(nextBalloon, 150); }, instant ? 0 : 260);
  };
  const timer = setTimeout(dismiss, o.timeout ?? 5500);
  el.addEventListener("click", () => dismiss());
  current = { el, dismiss };
}

// ---------- dialogs ----------
function placeDialog(el, near) {
  const d = desktop.getBoundingClientRect();
  const r = near ?? { left: d.left, top: d.top, width: d.width, height: d.height };
  const w = el.offsetWidth, h = el.offsetHeight;
  const x = Math.max(8, Math.min(d.width - w - 8, r.left - d.left + (r.width - w) / 2));
  const y = Math.max(8, Math.min(d.height - h - 8, r.top - d.top + (r.height - h) / 2));
  el.style.left = `${x}px`; el.style.top = `${y}px`;
}

function makeDialog({ id, title, icon, body, className = "" }) {
  if (id) document.getElementById(id)?.remove();
  const el = document.createElement("section");
  el.className = `window dialog active ${className}`;
  if (id) el.id = id;
  el.setAttribute("role", "dialog");
  el.innerHTML = `<div class="title-bar">${icon ? svg(icon, "title-icon") : ""}<span class="title-text">${esc(title)}</span>
    <div class="title-controls"><button class="tb-close" aria-label="Zamknij"></button></div></div>
    <div class="window-body">${body}</div>`;
  el.style.zIndex = 8000 + ++z;
  desktop.appendChild(el);
  draggable(el, el.querySelector(".title-bar"));
  el.addEventListener("pointerdown", () => {
    for (const o of wins.values()) o.el.classList.remove("active");
    desktop.querySelectorAll(".window.dialog").forEach((d) => d.classList.toggle("active", d === el));
    el.style.zIndex = 8000 + ++z;
  }, true);
  return el;
}

/** XP message box. buttons: [{ label, value, default }]. Resolves with the value (null on close). */
export function msgbox({ id, title, icon = "i-info", html, buttons = [{ label: "OK", value: true, default: true }], near }) {
  return new Promise((resolve) => {
    const el = makeDialog({
      id, title, icon,
      body: `<div class="msg">${svg(icon)}<div class="msg-text">${html}</div></div>
        <div class="buttons">${buttons.map((b, i) => `<button data-i="${i}" class="${b.default ? "default" : ""}">${esc(b.label)}</button>`).join("")}</div>`,
    });
    placeDialog(el, near);
    const done = (v) => { el.remove(); resolve(v); };
    el.querySelector(".tb-close").addEventListener("click", () => done(null));
    el.querySelectorAll(".buttons button").forEach((b) => b.addEventListener("click", () => done(buttons[+b.dataset.i].value)));
    el.querySelector(".buttons .default")?.focus({ preventScroll: true });
    el.addEventListener("keydown", (e) => { if (e.key === "Escape") done(null); });
  });
}

/** "File copy" style progress dialog. */
export function copyDialog({ title, from = "i-mountain", to = "i-folder", line1 = "", near, onCancel }) {
  const sheet = `<span class="sheet"><svg viewBox="0 0 16 18"><path d="M1 .5 h10 l4 4 V17.5 H1 Z" fill="#fff" stroke="#5d6f8f"/><path d="M3.5 7 h8 M3.5 10 h8 M3.5 13 h6" stroke="#d6007e" stroke-width="1.2"/></svg></span>`;
  const el = makeDialog({
    id: "copy-dialog", title, icon: "i-drone", className: "copy",
    body: `<div class="anim">${svg(from, "from")}${sheet}${sheet}${sheet}${svg(to, "to")}</div>
      <p class="line l1">${esc(line1)}</p><p class="line l2">&nbsp;</p>
      <div class="progress"><i></i></div>
      <p class="line left">&nbsp;</p>
      <div class="buttons"><button class="cancel">Anuluj</button></div>`,
  });
  el.style.width = "440px";
  placeDialog(el, near);
  const anim = el.querySelector(".anim");
  anim.style.setProperty("--span", `${anim.clientWidth - 44 - 60}px`);
  const bar = el.querySelector(".progress > i");
  let closed = false;
  const closeIt = () => { if (!closed) { closed = true; el.remove(); } };
  const cancel = () => { closeIt(); onCancel?.(); };
  el.querySelector(".cancel").addEventListener("click", cancel);
  el.querySelector(".tb-close").addEventListener("click", cancel);
  return {
    update(t, l2, left) {
      if (closed) return;
      bar.style.width = `${Math.round(t * 100)}%`;
      if (l2 != null) el.querySelector(".l2").textContent = l2;
      if (left != null) el.querySelector(".left").textContent = left;
    },
    close: closeIt,
    get closed() { return closed; },
  };
}

// ---------- shutdown ----------
export function shutdown({ question, onOff, onStandby }) {
  const screen = document.getElementById("screen");
  screen.classList.add("dimmed");
  const wrap = document.createElement("div");
  wrap.className = "shutdown-wrap";
  wrap.innerHTML = `<div class="shutdown" role="dialog" aria-label="Wyłącz komputer">
    <div class="sd-top"><span>Wyłącz komputer</span>${svg("i-logo")}</div>
    <div class="sd-mid">
      <p class="sd-q">${esc(question)}</p>
      <div class="sd-opts">
        <button class="standby"><i>${svg("i-clock")}</i>Stan wstrzymania</button>
        <button class="off"><i>${svg("i-power")}</i>Wyłącz</button>
        <button class="restart"><i>${svg("i-arrow")}</i>Uruchom ponownie</button>
      </div>
      <p class="sd-note" hidden></p>
    </div>
    <div class="sd-bottom"><button class="cancel">Anuluj</button></div>
  </div>`;
  document.body.appendChild(wrap);
  const done = () => { wrap.remove(); screen.classList.remove("dimmed"); };
  const note = wrap.querySelector(".sd-note");
  const say = (t) => { note.hidden = false; note.textContent = t; wrap.querySelector(".cancel").textContent = "OK"; };
  wrap.querySelector(".cancel").addEventListener("click", done);
  wrap.querySelector(".standby").addEventListener("click", () => say(onStandby));
  wrap.querySelector(".off").addEventListener("click", () => say(onOff));
  wrap.querySelector(".restart").addEventListener("click", () => location.reload());
  wrap.addEventListener("keydown", (e) => { if (e.key === "Escape") done(); });
  wrap.querySelector(".cancel").focus();
}

// ---------- splash ----------
const splashEl = document.getElementById("splash");
const t0 = performance.now();
let splashResolve;
const splashGone = new Promise((r) => (splashResolve = r));
function hideSplash() {
  if (splashEl.classList.contains("gone")) return;
  try { sessionStorage.setItem("xp.splash", "1"); } catch {}
  splashEl.classList.add("fade");
  setTimeout(() => { splashEl.classList.add("gone"); splashEl.classList.remove("fade"); splashResolve(); }, reduced ? 0 : 450);
}
if (document.documentElement.classList.contains("nosplash")) { splashEl.classList.add("gone"); splashResolve(); }
splashEl.addEventListener("click", hideSplash);
setTimeout(hideSplash, reduced ? 0 : 3000); // never hold the demo hostage

/** Called by the app once the first frame is ready. */
export function ready() {
  const wait = Math.max(0, 1500 - (performance.now() - t0));
  if (!splashEl.classList.contains("gone")) setTimeout(hideSplash, wait);
  splashGone.then(() => { balloonsHeld = false; if (!current) setTimeout(nextBalloon, 400); });
}

/** Log off: show the welcome screen again for a moment. */
export function logoff() {
  closeStart();
  document.documentElement.classList.remove("nosplash");
  splashEl.classList.remove("gone", "fade");
  setTimeout(hideSplash, 1500);
}

layout(true);
focus("w-map");

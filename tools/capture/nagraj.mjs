// Raw screen shots for the demo video (docs/15_wideo.md, section 3): headless Edge + CDP screencast.
// Usage: node tools/capture/nagraj.mjs [A|B]   (default: both sessions)
// Session A is one continuous screencast; every shot (A1..A6) is cut from it by time marks, so a balloon
// is never truncated by a stop/start. Frames carry their own timestamps (screencast only sends a frame on
// change); ffmpeg concat with per-frame durations gives a constant 30 fps master, shots are trimmed from it.
// The cursor is a drawn SVG arrow (headless draws none) that follows real Input.dispatchMouseEvent moves.
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "../..");
const OUT = path.join(ROOT, "filmy/wideo/surowe");
const MASTER_DIR = path.join(OUT, "ciagle");
const TMP = process.env.NAGRAJ_TMP || path.join(os.tmpdir(), "avalauncher-nagraj");
const FFMPEG = process.env.FFMPEG || "C:/Users/Przemke/AppData/Local/Programs/Python/Python311/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const BASE = "http://localhost:8777/";
// JPEG q80 + --disable-gpu: measured ~30 fps screencast at 1600×900 (q92 gave ~17 fps; encoding is the bottleneck)
const Q = 80;
const W = 1600, H = 900, REST = [960, 770]; // cursor rest point: empty part of the "Plan przelotu" window
const which = (process.argv[2] || "AB").toUpperCase();
fs.mkdirSync(OUT, { recursive: true }); fs.mkdirSync(MASTER_DIR, { recursive: true }); fs.mkdirSync(TMP, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

// Injected before any page script: drawn cursor + a log of balloons (appear / remove, wall clock).
const INJECT = `
window.__bl = [];
addEventListener("DOMContentLoaded", () => {
  requestAnimationFrame(() => requestAnimationFrame(() => { window.__firstPaint = Date.now() / 1000; }));
  const c = document.createElement("div");
  c.id = "__cursor";
  c.innerHTML = '<svg width="22" height="30" viewBox="0 0 22 30"><path d="M1 1 L1 23 L6.5 18 L10.5 28 L14 26.5 L10 17 L18 17 Z" fill="#fff" stroke="#1d1b17" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, { position: "fixed", left: "-40px", top: "0", zIndex: 2147483647, pointerEvents: "none", filter: "drop-shadow(1px 2px 1px rgba(0,0,0,.35))" });
  document.documentElement.appendChild(c);
  addEventListener("mousemove", (e) => { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; }, true);
  const title = (n) => n.querySelector(".b-head span")?.textContent ?? "";
  new MutationObserver((ms) => {
    for (const m of ms) {
      for (const n of m.addedNodes) if (n.classList?.contains("balloon")) __bl.push({ ev: "add", title: title(n), t: Date.now() / 1000 });
      for (const n of m.removedNodes) if (n.classList?.contains("balloon")) __bl.push({ ev: "rm", title: title(n), t: Date.now() / 1000 });
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
});`;

async function openBrowser(name) {
  const port = 9300 + Math.floor(Math.random() * 500);
  const profile = fs.mkdtempSync(path.join(TMP, `edge-${name}-`));
  const edge = spawn(EDGE, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    "--hide-scrollbars", `--window-size=${W},${H}`, "--disable-gpu", "--mute-audio", "--autoplay-policy=no-user-gesture-required",
    "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows",
    "--no-first-run", "--no-default-browser-check", "about:blank"], { stdio: "ignore" });
  let target;
  for (let i = 0; i < 75 && !target; i++) {
    await sleep(200);
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {}
  }
  if (!target) throw new Error("Edge: no page target");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.addEventListener("open", r); ws.addEventListener("error", j); });
  let id = 0;
  const pending = new Map(), handlers = new Map();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.j(new Error(`${p.method}: ${m.error.message}`)) : p.r(m.result); }
    else if (m.method && handlers.has(m.method)) for (const h of handlers.get(m.method)) h(m.params);
  });
  const send = (method, params = {}) => new Promise((r, j) => { pending.set(++id, { r, j, method }); ws.send(JSON.stringify({ id, method, params })); });
  const on = (method, fn) => { if (!handlers.has(method)) handlers.set(method, []); handlers.get(method).push(fn); };
  const close = async () => {
    try { ws.close(); } catch {}
    spawnSync("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
    await sleep(500);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
  };
  await send("Page.enable"); await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "no-preference" }] });
  await send("Emulation.setFocusEmulationEnabled", { enabled: true }).catch(() => {});
  await send("Page.addScriptToEvaluateOnNewDocument", { source: INJECT });
  return { send, on, close, edge };
}

function page(b) {
  const ev = async (expr) => {
    const r = await b.send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(`eval: ${r.exceptionDetails.exception?.description ?? r.exceptionDetails.text}`);
    return r.result.value;
  };
  const waitFor = async (expr, timeout = 15000, what = expr) => {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) { try { if (await ev(expr)) return true; } catch {} await sleep(100); }
    log("TIMEOUT:", what); return false;
  };
  let mx = REST[0], my = REST[1];
  const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
  const moveTo = async (x, y, ms = 700, steps = 25) => {
    const x0 = mx, y0 = my;
    for (let i = 1; i <= steps; i++) {
      const e = ease(i / steps);
      mx = x0 + (x - x0) * e; my = y0 + (y - y0) * e;
      await b.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: mx, y: my });
      await sleep(ms / steps);
    }
  };
  const jump = async (x, y) => { mx = x; my = y; await b.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y }); };
  const click = async () => {
    await b.send("Input.dispatchMouseEvent", { type: "mousePressed", x: mx, y: my, button: "left", buttons: 1, clickCount: 1 });
    await sleep(70);
    await b.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: mx, y: my, button: "left", buttons: 0, clickCount: 1 });
  };
  const center = (sel) => ev(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return null;
    const b = e.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; })()`);
  const clickSel = async (sel, ms = 700, pause = 250) => {
    const c = await center(sel);
    if (!c) throw new Error(`no element: ${sel}`);
    await moveTo(c[0], c[1], ms); await sleep(pause); await click(); return c;
  };
  // map grid cell -> viewport px (same formula as the app's px(): whole massif fitted, centred)
  const gridXY = (cr) => ev(`(() => { const r = document.getElementById("map").getBoundingClientRect();
    const k = Math.min(r.width / 400, r.height / 400);
    return [r.left + (r.width - 400 * k) / 2 + ${cr[0]} * k, r.top + (r.height - 400 * k) / 2 + ${cr[1]} * k]; })()`);
  const sectorXY = async (id) => {
    const c = await ev(`fetch("data/sectors.json").then((r) => r.json()).then((S) => (Array.isArray(S) ? S : S.sectors).find((x) => x.id === ${JSON.stringify(id)}).centroid)`);
    return gridXY(c);
  };
  const balloons = () => ev("window.__bl ?? []");
  const balloonShown = (title) => ev(`(window.__bl ?? []).some((b) => b.ev === "add" && b.title.startsWith(${JSON.stringify(title)}))`);
  const balloonGone = (title) => ev(`(window.__bl ?? []).some((b) => b.ev === "rm" && b.title.startsWith(${JSON.stringify(title)}))`);
  const waitQuiet = async (timeout = 25000, quiet = 600) => { // no balloon on screen (queue gap is 150 ms)
    const t0 = Date.now(); let since = null;
    while (Date.now() - t0 < timeout) {
      const any = await ev(`!!document.querySelector(".balloon")`);
      if (any) since = null; else { since ??= Date.now(); if (Date.now() - since >= quiet) return true; }
      await sleep(100);
    }
    log("TIMEOUT: balloons still showing"); return false;
  };
  return { ev, waitFor, moveTo, jump, click, center, clickSel, gridXY, sectorXY, balloons, balloonShown, balloonGone, waitQuiet, pos: () => [mx, my] };
}

// ---------- screencast recorder ----------
function recorder(b, name) {
  const dir = fs.mkdtempSync(path.join(TMP, `frames-${name}-`));
  const frames = []; let on = false, endWall = null;
  b.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    b.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
    if (!on) return;
    const file = path.join(dir, `f${String(frames.length).padStart(6, "0")}.jpg`);
    fs.writeFileSync(file, Buffer.from(data, "base64"));
    frames.push({ file, ts: metadata.timestamp, wall: now() });
  });
  const marks = [];
  return {
    frames, marks,
    start: async () => { on = true; await b.send("Page.startScreencast", { format: "jpeg", quality: Q, maxWidth: W, maxHeight: H, everyNthFrame: 1 }); },
    restart: async () => { await b.send("Page.stopScreencast").catch(() => {}); await b.send("Page.startScreencast", { format: "jpeg", quality: Q, maxWidth: W, maxHeight: H, everyNthFrame: 1 }); },
    stop: async () => { endWall = now(); await b.send("Page.stopScreencast").catch(() => {}); await sleep(300); on = false; },
    mark: (label) => { marks.push({ label, wall: now() }); log("mark", label); },
    // wall clock -> seconds from the first frame (ts domain; offset = smallest receive latency)
    encode: (out) => {
      if (frames.length < 2) throw new Error(`${name}: only ${frames.length} frames`);
      const off = Math.min(...frames.map((f) => f.wall - f.ts));
      const t0 = frames[0].ts, endTs = endWall - off;
      const lines = ["ffconcat version 1.0"];
      frames.forEach((f, i) => {
        const d = (i + 1 < frames.length ? frames[i + 1].ts : endTs) - f.ts;
        lines.push(`file '${f.file.replace(/\\/g, "/")}'`, `duration ${Math.max(0.001, d).toFixed(4)}`);
      });
      lines.push(`file '${frames.at(-1).file.replace(/\\/g, "/")}'`);
      const list = path.join(dir, "klatki.txt");
      fs.writeFileSync(list, lines.join("\n"));
      ffmpeg(["-f", "concat", "-safe", "0", "-i", list, "-vf", `fps=30,scale=${W}:${H}:flags=lanczos`, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium", "-movflags", "+faststart", out]);
      const gaps = frames.slice(1).map((f, i) => (f.ts - frames[i].ts) * 1000).sort((x, y) => x - y);
      const gapStats = { p50: +gaps[Math.floor(gaps.length * 0.5)].toFixed(1), p95: +gaps[Math.floor(gaps.length * 0.95)].toFixed(1), max: +gaps.at(-1).toFixed(1), over100: gaps.filter((g) => g > 100).length };
      log(`${name}: frame gaps ms`, JSON.stringify(gapStats));
      return { rel: (wall) => wall - off - t0, total: endTs - t0, off, n: frames.length, gapStats };
    },
    dir,
  };
}

function ffmpeg(args) {
  const r = spawnSync(FFMPEG, ["-y", "-hide_banner", "-loglevel", "error", ...args], { encoding: "utf8" });
  if (r.status !== 0) throw new Error(`ffmpeg failed: ${r.stderr}`);
}
function probe(file) {
  const r = spawnSync(FFMPEG, ["-hide_banner", "-i", file], { encoding: "utf8" });
  const d = /Duration: (\d+):(\d+):([\d.]+)/.exec(r.stderr), s = /, (\d{3,4})x(\d{3,4})/.exec(r.stderr), f = /([\d.]+) fps/.exec(r.stderr);
  return { dur: d ? +d[1] * 3600 + +d[2] * 60 + +d[3] : NaN, size: s ? `${s[1]}×${s[2]}` : "?", fps: f ? +f[1] : NaN };
}
function cut(master, rel, shot, file) {
  const s = Math.max(0, rel(shot.from)), e = rel(shot.to);
  ffmpeg(["-ss", s.toFixed(3), "-to", e.toFixed(3), "-i", master, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium", "-r", "30", "-movflags", "+faststart", file]);
  return { s, e };
}

const notes = [];
const report = { shots: [], notes, masters: [] };

// ---------- session A ----------
async function sessionA() {
  const b = await openBrowser("A");
  const p = page(b), rec = recorder(b, "A");
  const shots = {};
  const T = (k) => (shots[k] ??= {});
  try {
    await rec.start();
    T("A1").from = now();
    await b.send("Page.navigate", { url: BASE + "?nohints" }); // ?nohints: no first-run hint balloons (the voice script has none)
    await p.waitFor(`document.readyState !== "loading" && !!document.getElementById("__cursor")`, 10000, "DOM ready");
    await p.jump(...REST);
    await p.waitFor(`!!window.__firstPaint`, 5000, "first paint");
    T("A1").from = (await p.ev(`window.__firstPaint`)) ?? T("A1").from; // skip the blank frames before the splash
    await sleep(1500);
    if (rec.frames.length < 3) { log("screencast stalled after navigate, restarting"); await rec.restart(); }
    await p.waitFor(`document.getElementById("splash").classList.contains("gone")`, 15000, "splash gone");
    const gone = now();
    T("A1").to = gone + 2.2;
    // A2 starts on the bare desktop, before the day-1 balloon slides out of the tray (~0.4 s after the splash)
    T("A2").from = gone + 0.05;
    const lib = await p.waitFor(`document.getElementById("library").textContent.includes("Na mapie: zasięgi")`, 15000, "library loaded");
    if (!lib) notes.push("A2: biblioteka zasięgów nie wczytała się w 15 s, brak pomarańczowego obrysu.");
    await p.waitFor(`(window.__bl ?? []).some((b) => b.title.startsWith("Przelot wykonany o 6:00"))`, 8000, "day-1 balloon");
    await p.waitQuiet(25000); // the balloon (and anything queued after it) has played out completely
    await sleep(800);
    const s22 = await p.sectorXY("S22");
    await p.moveTo(s22[0], s22[1], 900); await sleep(500); await p.click();
    let ok = await p.waitFor(`document.querySelector("#flag-dialog h3")?.textContent.includes("Może zagrozić szlakowi")`, 4000, "flag dialog S22");
    if (!ok) { // fallback from the doc: first row of "Sektory do uwagi"
      notes.push("A2: klik w znaczek 1 na mapie nie otworzył okna flagi, użyty pierwszy wiersz #rows.");
      await p.clickSel("#rows tr"); await p.waitFor(`!!document.getElementById("flag-dialog")`, 4000);
    }
    await sleep(2000);
    await p.moveTo(s22[0], s22[1] + 120, 1250, 35); await p.moveTo(s22[0], s22[1], 1250, 35);
    await sleep(400);
    await p.clickSel("#wi-3d", 800, 400);
    ok = await p.waitFor(`document.getElementById("pl-status")?.textContent.includes("Odtwarzanie: Sucha Dolina NE, płyta 0,8 m")`, 10000, "player status");
    if (!ok) notes.push(`A2: #pl-status = "${await p.ev(`document.getElementById("pl-status")?.textContent`)}" (oczekiwano „Odtwarzanie: Sucha Dolina NE, płyta 0,8 m”).`);
    await p.moveTo(REST[0] + 380, REST[1] + 60, 900); // cursor out of the player picture
    await sleep(2100);
    const rs = await p.ev(`document.getElementById("pl-video")?.readyState ?? -1`);
    report.plVideoReadyState = rs;
    if (rs < 2) notes.push(`A2: po 3 s #pl-video.readyState = ${rs} (< 2), w montażu idzie zapas web/media/3d/S22_samosATMedium_0.8.mp4.`);
    await sleep(10900);
    T("A2").to = now();

    // ---- A3: day 2, fog, tooltip on Liliowe E ----
    await p.clickSel("#w-player .tb-close", 700, 200);
    await sleep(800);
    await p.waitQuiet(10000);
    T("A3").from = now();
    await sleep(1000);
    await p.clickSel('.tab.day[data-day="1"]', 800, 300);
    await sleep(3000);
    const s31 = await p.sectorXY("S31");
    await p.moveTo(s31[0], s31[1], 1000);
    ok = await p.waitFor(`(() => { const t = document.getElementById("tooltip"); return !t.hidden && t.textContent.includes("Liliowe E") && t.textContent.includes("nie wiem"); })()`, 3000, "tooltip Liliowe E");
    if (!ok) { await p.moveTo(s31[0] + 4, s31[1] + 3, 200, 4); await p.waitFor(`!document.getElementById("tooltip").hidden`, 1500); }
    report.tooltipA3 = await p.ev(`document.getElementById("tooltip").textContent`);
    await sleep(2000);
    await p.waitFor(`(window.__bl ?? []).some((b) => b.ev === "add" && b.title.endsWith(": Nie wiem"))`, 12000, "balloon N sektory: Nie wiem");
    report.nwBalloon = (await p.balloons()).filter((x) => x.ev === "add").map((x) => x.title).at(-1);
    await p.waitQuiet(12000); // hold until the second balloon has fully played out
    await sleep(700);
    T("A3").to = now();

    // ---- A4: IMGW window, hover on the +34 cm / 3 dni episode ----
    T("A4").from = now();
    await sleep(800);
    await p.clickSel('#sources button[data-open="w-imgw"]', 900, 300);
    await p.waitFor(`!document.getElementById("w-imgw").classList.contains("is-hidden")`, 4000, "w-imgw open");
    await sleep(700);
    const ep = await p.ev(`fetch("data/kasprowy_2024_25.json").then((r) => r.json()).then((K) => {
      const n = K.days.length, i = K.days.findIndex((d) => d.date === "2025-01-13");
      const c = document.getElementById("imgw-chart"), r = c.getBoundingClientRect(), wr = c.parentElement.getBoundingClientRect();
      const L = 44, pw = wr.width - 56, T = 30, ph = wr.height - 30 - 22; // the app sizes the chart from its parent
      return [r.left + L + ((i + 0.5) / n) * pw, r.top + T + ph * 0.45, r.left + L + ((i - 2.5) / n) * pw];
    })`);
    await p.moveTo(ep[2], ep[1], 900); await p.moveTo(ep[0], ep[1], 1200, 30);
    await sleep(2400);
    report.chartTip = await p.ev(`document.getElementById("chart-tip")?.innerText ?? ""`);
    await sleep(600);
    T("A4").to = now();
    await p.clickSel("#w-imgw .tb-close", 700, 200);
    await p.moveTo(...REST, 700);
    await sleep(800);

    // ---- A5: flight plan, fly once, fog clears ----
    T("A5").from = now();
    await sleep(2000);
    const base = await p.gridXY([278, 69.2]), s55 = await p.sectorXY("S55");
    await p.moveTo(base[0], base[1], 1000); await p.moveTo(s31[0], s31[1], 1500); await p.moveTo(s55[0], s55[1], 1500);
    await p.clickSel("#fly", 900, 500);
    await p.waitFor(`!!document.getElementById("copy-dialog")`, 3000, "copy dialog");
    await p.moveTo(REST[0] + 380, REST[1] + 60, 900);
    await p.waitFor(`!document.getElementById("copy-dialog") && [...document.querySelectorAll(".balloon .b-head span")].some((s) => s.textContent.startsWith("Przelot zakończony"))`, 20000, "flight done balloon");
    await sleep(800);
    const rowXY = (name) => p.ev(`(() => { const tr = [...document.querySelectorAll("#rows tr")].find((t) => t.querySelector(".name")?.textContent.trim() === ${JSON.stringify(name)});
      if (!tr) return null; const b = tr.querySelector(".name").getBoundingClientRect(); return [b.left + 40, b.top + b.height / 2]; })()`);
    for (const nm of ["Liliowe E", "Mały Kościelec W"]) {
      const c = await rowXY(nm);
      if (c) { await p.moveTo(c[0], c[1], 800); await sleep(1500); } else notes.push(`A5: brak wiersza „${nm}” w #rows po przelocie.`);
    }
    report.countsAfter = await p.ev(`({ zagrozenie: document.querySelectorAll("#rows tr.zagrozenie").length, nie_wiem: document.querySelectorAll("#rows tr.nie_wiem").length,
      rows: [...document.querySelectorAll("#rows tr")].map((t) => t.querySelector(".name")?.textContent.trim() + " · " + t.querySelector(".kind")?.textContent.trim()) })`);
    await sleep(2000);
    await p.waitQuiet(10000);
    await sleep(600);
    T("A5").to = now();

    // ---- A5b (optional): Start menu, hover "Biblioteka scenariuszy" ----
    T("A5b").from = now();
    await sleep(800);
    await p.clickSel("#start-btn", 800, 250);
    await sleep(500);
    const lp = await p.center('.sm-right [data-action="library-page"]');
    await p.moveTo(lp[0], lp[1], 800); await sleep(1500);
    await b.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await b.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await sleep(300);
    if (await p.ev(`!document.querySelector(".start-menu, #start-menu")?.hidden`)) { await p.clickSel("#start-btn", 500, 150); }
    await sleep(700);
    T("A5b").to = now();
    await p.moveTo(...REST, 700);
    await sleep(600);

    // ---- A6: shutdown dialog ----
    T("A6").from = now();
    await sleep(1000);
    await p.clickSel("#start-btn", 900, 300);
    await sleep(1000);
    await p.clickSel('.sm-foot [data-action="shutdown"]', 900, 300);
    await p.waitFor(`!!document.querySelector(".shutdown")`, 3000, "shutdown dialog");
    await sleep(1500);
    await p.clickSel(".shutdown .off", 900, 300);
    await p.waitFor(`!document.querySelector(".shutdown .sd-note")?.hidden`, 3000, "sd-note");
    report.sdNote = await p.ev(`document.querySelector(".shutdown .sd-note")?.textContent`);
    await sleep(3500);
    await p.clickSel(".shutdown .cancel", 900, 300);
    await sleep(400);
    await p.moveTo(...REST, 800);
    await sleep(1000);
    T("A6").to = now();
    report.balloonsA = await p.balloons();
    await rec.stop();
  } finally {
    await b.close();
  }
  const master = path.join(MASTER_DIR, "A_sesja_ciagla.mp4");
  log(`encoding A master (${rec.frames.length} frames)`);
  const { rel, total, gapStats } = rec.encode(master);
  report.masters.push({ file: master, total, frames: rec.frames.length, gapStats });
  report.relA = rel;
  for (const bl of report.balloonsA) if (/brak łączności/i.test(bl.title)) notes.push(`Sesja A: dymek „${bl.title}” (${bl.ev}) w ${rel(bl.t).toFixed(1)} s nagrania ciągłego.`);
  const names = { A1: "A1_s04_start.mp4", A2: "A2_s05-06_dzien1.mp4", A3: "A3_s07_dzien2_mgla.mp4", A4: "A4_s07_imgw.mp4", A5: "A5_s08_przelot.mp4", A5b: "A5b_s09_menu_biblioteka.mp4", A6: "A6_s10_wylacz.mp4" };
  for (const [k, file] of Object.entries(names)) {
    if (!shots[k]?.from || !shots[k]?.to) { notes.push(`${k}: brak znaczników czasu, ujęcie pominięte.`); continue; }
    const out = path.join(OUT, file), { s, e } = cut(master, rel, shots[k], out);
    report.shots.push({ k, file, s, e, ...probe(out) });
    log(k, file, `${s.toFixed(2)}–${e.toFixed(2)} s`);
  }
}

// ---------- session B: scenario library page ----------
async function sessionB() {
  const b = await openBrowser("B");
  const p = page(b), rec = recorder(b, "B");
  const shot = {};
  try {
    await b.send("Page.navigate", { url: BASE + "biblioteka.html" });
    await p.waitFor(`document.readyState !== "loading" && !!document.getElementById("__cursor")`, 10000, "B DOM ready");
    await p.waitFor(`!document.querySelector("#w-lib .loading") && document.getElementById("lib-title").textContent.startsWith("Biblioteka scenariuszy — 1566")`, 30000, "library page loaded");
    // the page opens on its own default sector; bring the S22 node into the visible part of the tree first
    await p.ev(`document.querySelector('.node[data-sec="S22"]')?.scrollIntoView({ block: "center" })`);
    await p.jump(1150, 700);
    await sleep(1200);
    await rec.start();
    await sleep(300);
    await p.moveTo(1152, 702, 200, 4); // make sure the first frame is emitted
    shot.from = now();
    await sleep(1000);
    await p.clickSel('.node[data-sec="S22"]', 900, 300);
    await sleep(1500);
    await p.ev(`document.querySelector('#list-body tr[data-id="S22_samosATMedium_0.8"]')?.scrollIntoView({ block: "center" })`);
    await sleep(500);
    const row = await p.ev(`(() => { const tr = document.querySelector('#list-body tr[data-id="S22_samosATMedium_0.8"]'); if (!tr) return null;
      const b = tr.getBoundingClientRect(); return [b.left + Math.min(120, b.width / 3), b.top + b.height / 2]; })()`);
    if (row) { await p.moveTo(row[0], row[1], 900); await sleep(300); await p.click(); }
    else notes.push("B1: brak wiersza S22_samosATMedium_0.8 na liście po wybraniu S22.");
    await sleep(3000);
    report.addrB = await p.ev(`document.getElementById("addr")?.textContent ?? ""`);
    await sleep(700);
    shot.to = now();
    await rec.stop();
  } finally {
    await b.close();
  }
  const master = path.join(MASTER_DIR, "B_sesja_ciagla.mp4");
  const { rel, total, gapStats } = rec.encode(master);
  report.masters.push({ file: master, total, frames: rec.frames.length, gapStats });
  const file = "B1_s09_biblioteka.mp4", out = path.join(OUT, file), { s, e } = cut(master, rel, shot, out);
  report.shots.push({ k: "B1", file, s, e, ...probe(out) });
}

try {
  if (which.includes("A")) await sessionA();
  if (which.includes("B")) await sessionB();
} catch (e) {
  console.error("FAILED:", e.stack ?? e);
  notes.push(`Błąd nagrania: ${e.message}`);
}
delete report.relA;
fs.writeFileSync(path.join(TMP, `report-${which}.json`), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ shots: report.shots, notes, masters: report.masters, plVideoReadyState: report.plVideoReadyState, tooltipA3: report.tooltipA3, nwBalloon: report.nwBalloon, chartTip: report.chartTip, countsAfter: report.countsAfter, sdNote: report.sdNote, addrB: report.addrB }, null, 2));
process.exit(0);

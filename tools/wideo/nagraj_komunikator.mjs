// Nagrywa stany strony web/wideo/ (AvaKomunikator) do filmy/wideo/surowe/komunikator_<stan>.mp4, 1920x1080, 30 kl./s.
// Klatka po klatce, bez zegara ściennego: strona w trybie &render=1, przed każdą klatką await setTime(n/30)
// (animacje CSS zatrzymane i ustawione na czas, kamerka narysowana, film przewinięty), potem Page.captureScreenshot (PNG)
// do ffmpeg (image2pipe, libx264 crf 18, yuv420p). Dłuższe stany dzielone na kawałki renderowane równolegle
// w osobnych instancjach headless Edge, potem sklejane bez ponownego kodowania.
// Użycie: node tools/wideo/nagraj_komunikator.mjs [stan ...]   (domyślnie wszystkie). Serwer: python -m http.server 8777 -d web
// Zmienne: ROWNOLEGLE (domyślnie 8 instancji Edge), KAWALEK (domyślnie 300 klatek), BASE, FFMPEG.
import { spawn, spawnSync } from "node:child_process";
import { writeFileSync, mkdirSync, mkdtempSync, rmSync, existsSync, copyFileSync } from "node:fs";
import { once } from "node:events";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const FFMPEG = process.env.FFMPEG || "C:/Users/Przemke/AppData/Local/Programs/Python/Python311/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe";
const BASE = process.env.BASE || "http://localhost:8777/wideo/";
const OUT = resolve("filmy/wideo/surowe");
const FPS = 30;
// czas nagrania każdego stanu (s), razem z zapasem 1-1,5 s na początku i końcu
const STANY = { dzwoni: 6.5, rozmowa: 26.5, owca: 5.5, udostepnianie: 82, film: 14, koniec: 8 };
const ROWNOLEGLE = +(process.env.ROWNOLEGLE || 8);
const KAWALEK = +(process.env.KAWALEK || 300);
const lista = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(STANY);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
mkdirSync(OUT, { recursive: true });
const TMP = mkdtempSync(join(tmpdir(), "kom-render-"));

let nrPortu = 0;
async function renderuj({ stan, od, do: doK, plik }) {
  const port = 9411 + 3 * (nrPortu++);
  const profile = mkdtempSync(join(tmpdir(), "edge-kom-"));
  const edge = spawn(EDGE, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--hide-scrollbars",
    "--window-size=1920,1080", "--mute-audio", "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore" });
  const ff = spawn(FFMPEG, ["-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", String(FPS), "-video_track_timescale", "15360", plik],
    { stdio: ["pipe", "inherit", "inherit"] });
  const koniecFF = once(ff, "exit");
  try {
    let target;
    for (let i = 0; i < 300 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {} }
    if (!target) throw new Error(`${stan}: Edge nie wystartował (port ${port})`);
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((r) => ws.addEventListener("open", r));
    let id = 0; const pending = new Map();
    ws.addEventListener("message", (e) => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    });
    const send = (method, params = {}) => new Promise((r) => { pending.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });
    const ev = async (expr) => {
      const m = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
      if (m.result?.exceptionDetails) throw new Error(`${stan}: ${JSON.stringify(m.result.exceptionDetails).slice(0, 400)}`);
      return m.result?.result?.value;
    };
    await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
    await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "no-preference" }] });
    await send("Page.navigate", { url: `${BASE}?stan=${stan}&render=1` });
    let gotowe = false;
    for (let i = 0; i < 1200 && !(gotowe = await ev("window.__gotowe === true").catch(() => false)); i++) await sleep(100);
    if (!gotowe) throw new Error(`${stan}: strona nie wczytała się w 120 s`);
    await ev(`setStan(${JSON.stringify(stan)})`);
    // pierwsza klatka kawałka: wszystko, co zdarzyło się wcześniej, jest już zakończone (animacje od 0 s)
    for (let n = od; n < doK; n++) {
      await ev(`setTime(${n}/${FPS})`);
      const m = await send("Page.captureScreenshot", { format: "png", optimizeForSpeed: true, captureBeyondViewport: false });
      if (!m.result?.data) throw new Error(`${stan}: brak zrzutu klatki ${n}: ${JSON.stringify(m.error || {})}`);
      if (!ff.stdin.write(Buffer.from(m.result.data, "base64"))) await once(ff.stdin, "drain");
    }
    ws.close();
  } finally {
    ff.stdin.end();
    spawnSync("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
    for (let i = 0; i < 4; i++) { await sleep(1000); try { rmSync(profile, { recursive: true, force: true }); break; } catch {} }
  }
  const [kod] = await koniecFF;
  if (kod !== 0) throw new Error(`${stan} ${od}-${doK}: ffmpeg ${kod}`);
  console.log(`${stan}: klatki ${od}-${doK - 1} gotowe`);
}

// kawałki: stany dłuższe niż KAWALEK klatek dzielone na równe części
const zadania = [], stany = [];
for (const s of lista) {
  if (!STANY[s]) { console.error("nieznany stan:", s); continue; }
  const n = Math.round(STANY[s] * FPS), k = Math.ceil(n / KAWALEK), czesci = [];
  for (let i = 0; i < k; i++) {
    const od = Math.round((i * n) / k), doK = Math.round(((i + 1) * n) / k);
    const z = { stan: s, od, do: doK, plik: join(TMP, `${s}_${String(i).padStart(2, "0")}.mp4`).replace(/\\/g, "/") };
    zadania.push(z); czesci.push(z);
  }
  stany.push({ stan: s, n, czesci });
}
// najdłuższe kawałki najpierw
const kolejka = [...zadania].sort((a, b) => (b.do - b.od) - (a.do - a.od));
const t0 = Date.now();
await Promise.all(Array.from({ length: Math.min(ROWNOLEGLE, kolejka.length) }, async (_, w) => {
  await sleep(w * 2500);  // instancje startują po kolei, żeby nie zatkać serwera
  while (kolejka.length) {
    const z = kolejka.shift();
    for (let proba = 1; ; proba++) {
      try { await renderuj(z); break; } catch (e) { console.error(`${z.stan} ${z.od}-${z.do}: próba ${proba} nieudana: ${e.message}`); if (proba >= 3) throw e; }
    }
  }
}));

for (const { stan, n, czesci } of stany) {
  const out = join(OUT, `komunikator_${stan}.mp4`);
  const stary = join(OUT, `komunikator_${stan}_old.mp4`);
  if (existsSync(out) && !existsSync(stary)) copyFileSync(out, stary);
  const listPath = join(TMP, `${stan}.txt`);
  writeFileSync(listPath, czesci.map((z) => `file '${z.plik}'\n`).join(""));
  const r = spawnSync(FFMPEG, ["-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listPath, "-c", "copy", "-movflags", "+faststart", out], { stdio: "inherit" });
  if (r.status !== 0) throw new Error(`${stan}: ffmpeg concat ${r.status}`);
  console.log(`${stan}: ${n} klatek (${(n / FPS).toFixed(2)} s, ${czesci.length} kaw.) -> ${out}`);
}
console.log(`razem ${((Date.now() - t0) / 1000).toFixed(0)} s`);
if (!process.env.ZOSTAW) try { rmSync(TMP, { recursive: true, force: true }); } catch {}
process.exit(0);

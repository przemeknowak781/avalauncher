// Nagrywa stany strony web/wideo/ (AvaKomunikator) do filmy/wideo/surowe/komunikator_<stan>.mp4, 1920x1080, 30 kl./s.
// Headless Edge + DevTools: Page.startScreencast (klatki JPEG), potem ffmpeg concat -> stałe 30 kl./s.
// Czas każdej klatki bierzemy z kodu czasu, który strona (&nagranie=1) rysuje pod kadrem w pasku y 1080-1087
// (okno ma 1920x1088, pasek jest odcinany). Znaczniki czasu screencastu bywają przesunięte o ok. 0,5 s.
// Użycie: node tools/wideo/nagraj_komunikator.mjs [stan ...]   (domyślnie wszystkie). Serwer: python -m http.server 8777 -d web
import { spawn, spawnSync } from "node:child_process";
import { writeFileSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const FFMPEG = process.env.FFMPEG || "C:/Users/Przemke/AppData/Local/Programs/Python/Python311/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe";
const BASE = process.env.BASE || "http://localhost:8777/wideo/";
const OUT = resolve("filmy/wideo/surowe");
// czas nagrania każdego stanu (s), razem z zapasem 1-1,5 s na początku i końcu
const STANY = { dzwoni: 6.5, rozmowa: 26.5, owca: 5.5, udostepnianie: 82, film: 14, koniec: 8 };
const lista = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(STANY);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const clampInt = (x, a, b) => Math.max(a, Math.min(b, x));
mkdirSync(OUT, { recursive: true });

// odczyt kodu czasu ze wszystkich klatek naraz: pasek 24x8 px spod kadru (kanał R w pełnym zakresie)
function kody(dir, n) {
  const r = spawnSync(FFMPEG, ["-v", "error", "-start_number", "0", "-i", join(dir, "f%05d.jpg"), "-vf", "crop=24:8:0:1080", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], { maxBuffer: 1 << 28 });
  const b = r.stdout, out = [];
  for (let i = 0; i < n; i++) {
    const avg = (x0) => { let s = 0; for (let y = 2; y < 6; y++) for (let x = x0 + 2; x < x0 + 6; x++) s += b[i * 576 + y * 72 + x * 3]; return s / 16; };
    out.push({ g0: Math.round(avg(0) / 5), g1: clampInt(Math.round((avg(8) - 12) / 25), 0, 9), start: avg(16) > 128 });
  }
  return out;
}

async function nagraj(stan) {
  const dur = STANY[stan];
  const port = 9400 + Math.floor(Math.random() * 400);
  const profile = mkdtempSync(join(tmpdir(), "edge-kom-"));
  const klatki = mkdtempSync(join(tmpdir(), `kom-${stan}-`));
  const edge = spawn(EDGE, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--hide-scrollbars",
    "--window-size=1920,1088", "--autoplay-policy=no-user-gesture-required", "--mute-audio", "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore" });
  try {
    let target;
    for (let i = 0; i < 60 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {} }
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((r) => ws.addEventListener("open", r));
    let id = 0; const pending = new Map(); const frames = [];
    ws.addEventListener("message", (e) => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); return; }
      if (m.method === "Page.screencastFrame") {
        const { data, metadata, sessionId } = m.params;
        const file = join(klatki, `f${String(frames.length).padStart(5, "0")}.jpg`).replace(/\\/g, "/");
        writeFileSync(file, Buffer.from(data, "base64"));
        frames.push({ file, ts: metadata.timestamp });
        ws.send(JSON.stringify({ id: ++id, method: "Page.screencastFrameAck", params: { sessionId } }));
      }
    });
    const send = (method, params = {}) => new Promise((r) => { pending.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });
    const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }))?.result?.value;

    await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1088, deviceScaleFactor: 1, mobile: false });
    await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "no-preference" }] });
    await send("Page.navigate", { url: `${BASE}?stan=${stan}&nagranie=1` });
    for (let i = 0; i < 200 && !(await ev("window.__gotowe === true")); i++) await sleep(100);
    await sleep(600);
    await send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1088, everyNthFrame: 1 });
    await sleep(400);
    await ev(`setStan(${JSON.stringify(stan)})`);
    await sleep(dur * 1000 + 1500);
    await send("Page.stopScreencast");
    await sleep(200);
    ws.close();

    // czas lokalny każdej klatki z kodu (okres 5 s rozwijany przybliżonym czasem screencastu)
    const k = kody(klatki, frames.length);
    const i0 = k.findIndex((x) => x.start);
    if (i0 < 0) throw new Error(`${stan}: brak klatki po starcie`);
    const uzyte = [];
    let last = -1;
    for (let i = i0; i < frames.length; i++) {
      const v = ((k[i].g0 % 50) * 10 + k[i].g1) / 100;
      const approx = frames[i].ts - frames[i0].ts;
      const t = v + 5 * Math.round((approx - v) / 5);
      if (!Number.isFinite(t) || t <= last || t > dur) continue;
      uzyte.push({ file: frames[i].file, t }); last = t;
    }
    if (!uzyte.length) throw new Error(`${stan}: brak klatek`);
    const pierwszy = uzyte[0].t;
    let txt = "";
    for (let i = 0; i < uzyte.length; i++) {
      const b = i + 1 < uzyte.length ? uzyte[i + 1].t : dur;
      txt += `file '${uzyte[i].file}'\nduration ${Math.max(0.001, b - (i === 0 ? 0 : uzyte[i].t)).toFixed(4)}\n`;
    }
    txt += `file '${uzyte[uzyte.length - 1].file}'\n`;
    const listPath = join(klatki, "klatki.txt");
    writeFileSync(listPath, txt);
    const out = join(OUT, `komunikator_${stan}.mp4`);
    const r = spawnSync(FFMPEG, ["-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listPath,
      "-vf", "crop=1920:1080:0:0,scale=1920:1080:flags=lanczos:in_range=pc:out_range=tv,fps=30,format=yuv420p", "-pix_fmt", "yuv420p", "-color_range", "tv",
      "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-t", String(dur), "-movflags", "+faststart", out], { stdio: "inherit" });
    if (r.status !== 0) throw new Error(`${stan}: ffmpeg ${r.status}`);
    console.log(`${stan}: ${uzyte.length} klatek (${(uzyte.length / dur).toFixed(1)}/s), pierwsza klatka t=${pierwszy.toFixed(2)} s, ostatnia t=${last.toFixed(2)} s -> ${out}`);
  } finally {
    spawnSync("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
    // Edge trzyma blokady profilu jeszcze chwilę po taskkill: kilka prób usunięcia
    for (let i = 0; i < 4; i++) { await sleep(1000); try { rmSync(profile, { recursive: true, force: true }); break; } catch {} }
    if (!process.env.ZOSTAW) try { rmSync(klatki, { recursive: true, force: true }); } catch {}
  }
}

for (const s of lista) {
  if (!STANY[s]) { console.error("nieznany stan:", s); continue; }
  await nagraj(s);
}
process.exit(0);

// deck/index.html -> deck/avalauncher_deck.pdf + deck/png/slajd_NN.png, via headless Edge + DevTools (no dependencies).
// Usage: node deck/tools/export.mjs [--png-only]
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const DECK = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const url = pathToFileURL(join(DECK, "index.html")).href;
const pngOnly = process.argv.includes("--png-only");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "edge-deck-"));
const edge = spawn(EDGE, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  "--hide-scrollbars", "--allow-file-access-from-files", "--window-size=1920,1080", "about:blank"], { stdio: "ignore" });
const kill = () => new Promise((r) => spawn("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" }).on("exit", r));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

try {
  let target;
  for (let i = 0; i < 100 && !target; i++) {
    await sleep(200);
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {}
  }
  if (!target) throw new Error("Edge did not start");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  const send = (method, params = {}) => new Promise((r, j) => {
    pending.set(++id, (m) => (m.error ? j(new Error(`${method}: ${m.error.message}`)) : r(m.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result.value;

  await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
  await send("Page.enable");
  await send("Page.navigate", { url });
  await sleep(1500);
  const ready = await evaluate(`Promise.all([document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => i.src))])
    .then((bad) => ({ fonts: [...document.fonts].map((f) => f.family + ":" + f.status), slides: document.querySelectorAll("section.slide").length,
      broken: [...document.images].filter((i) => !i.naturalWidth).map((i) => i.getAttribute("src")),
      overflow: [...document.querySelectorAll(".c")].map((c, k) => [k + 1, c.scrollHeight - c.clientHeight]).filter((x) => x[1] > 0) }))`);
  console.log(JSON.stringify(ready));

  if (!pngOnly) {
    const pdf = await send("Page.printToPDF", { preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false,
      marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 });
    writeFileSync(join(DECK, "avalauncher_deck.pdf"), Buffer.from(pdf.data, "base64"));
    console.log("saved avalauncher_deck.pdf");
  }
  mkdirSync(join(DECK, "png"), { recursive: true });
  for (let i = 0; i < ready.slides; i++) {
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
      clip: { x: 0, y: i * 1080, width: 1920, height: 1080, scale: 1 } });
    const name = `slajd_${String(i + 1).padStart(2, "0")}.png`;
    writeFileSync(join(DECK, "png", name), Buffer.from(shot.data, "base64"));
  }
  console.log("saved", ready.slides, "previews");
  ws.close();
} finally {
  await kill(); // end the whole Edge process tree we started, nothing else
}
process.exit(0);

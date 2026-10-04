// Roboczy plik SRT z web/wideo/cues.json (przedziały "mowi" + "napis"), na osi czasu filmu 0:00-1:54.
// Użycie: node tools/wideo/napisy_srt.mjs  ->  filmy/wideo/surowe/napisy_robocze.srt
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
const z = JSON.parse(readFileSync("web/wideo/cues.json", "utf8")).zdarzenia.filter((e) => e.mowi && e.napis).sort((a, b) => a.mowi[0] - b.mowi[0]);
const ts = (s) => { const ms = Math.round(s * 1000); const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")},${String(ms % 1000).padStart(3, "0")}`; };
// napis zostaje na ekranie co najmniej 1,4 s, ale nie wchodzi na następny
const out = z.map((e, i) => { const od = e.mowi[0], nast = z[i + 1] ? z[i + 1].mowi[0] - 0.05 : Infinity; const ddo = Math.min(Math.max(e.mowi[1] + 0.3, od + 1.4), nast);
  return `${i + 1}\n${ts(od)} --> ${ts(ddo)}\n${e.napis}\n`; }).join("\n");
mkdirSync("filmy/wideo/surowe", { recursive: true });
writeFileSync("filmy/wideo/surowe/napisy_robocze.srt", out);
console.log(`napisy: ${z.length} -> filmy/wideo/surowe/napisy_robocze.srt`);

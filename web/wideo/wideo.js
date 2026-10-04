// AvaKomunikator: rekwizyt filmu demo (docs/15_wideo.md, sekcje 1, 2 i 4). Postać fikcyjna, komunikator wymyślony.
// Stan: ?stan=dzwoni|rozmowa|owca|udostepnianie (alias: ekran)|film|koniec, albo window.setStan(nazwa) przy nagraniu.
// Opcje: &t=<s> (czas filmu na starcie stanu), &napisy=1 (napisy w pasie), &tts=1 (dopisek o syntezatorze na planszy).
"use strict";
(function () {
  const Q = new URLSearchParams(location.search);
  const ALIAS = { udostepnianie: "ekran", ekran: "ekran", dzwoni: "dzwoni", rozmowa: "rozmowa", owca: "owca", film: "film", koniec: "koniec" };
  // czas filmu (s) w chwili 0 każdego stanu: 1 s zapasu przed sceną na montaż
  const START = { dzwoni: 0, rozmowa: 3.0, owca: 28.2, ekran: 27.0, film: 94.0, koniec: 108.0 };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const ease = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const lerp = (a, b, k) => a + (b - a) * k;
  const napisyWl = Q.get("napisy") === "1";
  if (Q.get("tts") === "1") document.body.classList.add("tts");

  let Z = [];          // zdarzenia z cues.json
  let stan = "dzwoni", t0 = performance.now(), filmStart = 0;
  const lt = () => (performance.now() - t0) / 1000;
  const ft = () => filmStart + lt();

  // ---------- losowość z ziarnem (powtarzalne nagrania) ----------
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  const hash = (i) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

  // ---------- scena kamerki (SVG 320x240) ----------
  const SK = "#e7b08a", SK_D = "#c98f6c";
  function staszekSVG(p) {
    const f = p.f, poza = p.staszek, pt = p.staszekT;
    // pochylenie / odsunięcie całej postaci
    let s = 1, dy = 0;
    if (poza === "przeciera_oczy") s = 1 + 0.07 * ease(pt / 0.5);
    if (poza === "mruzy") s = 1 + 0.045 * ease(pt / 0.6);
    if (poza === "odsuwa_sie") { const k = ease(pt / 0.6); s = 1 - 0.1 * k; dy = -5 * k; }
    // głowa
    let rot = 0, hy = 0;
    if (poza === "kiwa") { rot = 1.5; hy = 3.2 * Math.max(0, Math.sin(f * Math.PI * 2 * 1.05)); }
    else if (poza === "kamienna_twarz") { rot = 2; }
    else if (poza === "mruzy") { rot = -1.5; hy = 2; }
    else { rot = 2.5 + 2 * Math.sin(f * 0.55); hy = 0.8 * Math.sin(f * 0.9); }
    // powieki (0 otwarte, 1 zamknięte) i źrenice
    let L = { zaspany: 0.56, mowi: 0.48, mruzy: 0.74, kamienna_twarz: 0.52, odsuwa_sie: 0.25, przeciera_oczy: 1, lyk: 0.5, kiwa: 0.62, dlonie: 0.45 }[poza] ?? 0.55;
    let px = 0, py = 0.8, brew = 0;
    if (poza === "mruzy") { px = -2.3; py = 1.8; brew = 1.2; }
    if (poza === "odsuwa_sie") brew = -3;
    // szklanka: na stole albo przy ustach
    let gk = 0;
    if (poza === "lyk") { gk = pt < 0.45 ? ease(pt / 0.45) : pt < 1.15 ? 1 : 1 - ease((pt - 1.15) / 0.45); if (gk > 0.6) L = 0.95; }
    if (p.blink) L = 1;
    const mouthH = [0.6, 1.8, 3.0, 4.4][p.mouth] || 0.6;

    const eye = (ex, ey) => {
      const lidY = ey - 5 + 10 * L;
      return `<g><clipPath id="oko${ex}"><ellipse cx="${ex}" cy="${ey}" rx="6.2" ry="4.4"/></clipPath>
        <g clip-path="url(#oko${ex})"><rect x="${ex - 7}" y="${ey - 5}" width="14" height="10" fill="#f3eee4"/>
        <circle cx="${ex + px}" cy="${ey + py}" r="2.7" fill="#3a2a1e"/><circle cx="${ex + px - 0.8}" cy="${ey + py - 0.9}" r="0.7" fill="#fff" opacity=".8"/>
        <rect x="${ex - 7}" y="${ey - 6}" width="14" height="${10 * L + 1}" fill="${SK}"/></g>
        <path d="M${ex - 6.4} ${lidY} Q${ex} ${lidY + 1.2} ${ex + 6.4} ${lidY}" stroke="#6b4632" stroke-width="1.3" fill="none" stroke-linecap="round"/>
        <path d="M${ex - 5} ${ey + 5.6} Q${ex} ${ey + 7.6} ${ex + 5} ${ey + 5.6}" stroke="${SK_D}" stroke-width="1.1" fill="none"/></g>`;
    };

    let head = `<g transform="rotate(${rot} 140 150) translate(0 ${hy})">
      <ellipse cx="103" cy="114" rx="7" ry="10" fill="${SK_D}"/><ellipse cx="177" cy="114" rx="7" ry="10" fill="${SK_D}"/>
      <path d="M100 100 Q98 122 108 130 L104 108 Z M180 100 Q182 122 172 130 L176 108 Z" fill="#8c8174"/>
      <ellipse cx="140" cy="112" rx="36" ry="42" fill="${SK}"/>
      <ellipse cx="117" cy="126" rx="9" ry="6" fill="#d77a62" opacity=".45"/><ellipse cx="163" cy="126" rx="9" ry="6" fill="#d77a62" opacity=".45"/>
      ${eye(124, 103)}${eye(156, 103)}
      <path d="M113 ${93 + brew} Q124 ${86 + brew} 135 ${93 + brew}" stroke="#5b4a3a" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M145 ${93 + brew} Q156 ${86 + brew} 167 ${93 + brew}" stroke="#5b4a3a" stroke-width="5" fill="none" stroke-linecap="round"/>
      <ellipse cx="140" cy="150" rx="22" ry="7" fill="${SK_D}" opacity=".35"/>
      <ellipse cx="140" cy="139" rx="7.5" ry="${mouthH}" fill="#4a1f1a"/>
      <ellipse cx="140" cy="${140 + mouthH}" rx="6" ry="1.4" fill="#c46f5c" opacity=".8"/>
      <ellipse cx="140" cy="117" rx="8.5" ry="9.5" fill="#df967a"/><ellipse cx="137" cy="113" rx="2.6" ry="2.2" fill="#f2c2a8" opacity=".8"/>
      <path d="M140 125 C128 119 112 121 104 133 C100 141 102 151 97 158 C108 154 114 144 122 138 C130 136 136 136 140 133 C144 136 150 136 158 138 C166 144 172 154 183 158 C178 151 180 141 176 133 C168 121 152 119 140 125 Z" fill="#6a5644"/>
      <path d="M116 129 C112 134 108 142 104 150 M124 128 C120 134 116 140 112 146 M156 128 C160 134 164 140 168 146 M164 129 C168 134 172 142 176 150" stroke="#8d7760" stroke-width="1.2" fill="none" stroke-linecap="round"/>
      <g transform="rotate(-11 140 80)">
        <path d="M99 92 C97 50 183 50 181 92 Z" fill="#5d6b3a"/>
        <path d="M110 64 C120 58 160 58 170 64" stroke="#6f7f48" stroke-width="2" fill="none"/>
        <rect x="96" y="84" width="88" height="15" rx="5" fill="#4b5730"/>
        ${Array.from({ length: 11 }, (_, i) => `<path d="M${101 + i * 8} 86 V97" stroke="#3c4626" stroke-width="1.6"/>`).join("")}
        <circle cx="140" cy="52" r="9.5" fill="#e6dcc8"/><circle cx="137" cy="49" r="3.5" fill="#f6f0e2"/>
      </g>
    </g>`;

    // tułów: sweter z surowej wełny z brązowym zygzakiem
    const zig = Array.from({ length: 24 }, (_, i) => `${40 + i * 8.5},${i % 2 ? 190 : 199}`).join(" ");
    const body = `<clipPath id="sweter"><path d="M38 240 C42 192 68 168 104 160 L176 160 C212 168 238 192 242 240 Z"/></clipPath>
      <path d="M38 240 C42 192 68 168 104 160 L176 160 C212 168 238 192 242 240 Z" fill="#e4d9c3"/>
      <g clip-path="url(#sweter)">
        ${Array.from({ length: 22 }, (_, i) => `<path d="M${44 + i * 9} 165 V240" stroke="#d2c6ad" stroke-width="2" stroke-dasharray="2 3"/>`).join("")}
        <path d="M30 183 H250" stroke="#7a4e2a" stroke-width="2.4"/><polyline points="${zig}" fill="none" stroke="#7a4e2a" stroke-width="4.5" stroke-linejoin="miter"/><path d="M30 206 H250" stroke="#7a4e2a" stroke-width="2.4"/>
        <path d="M160 160 C190 168 214 182 226 206" stroke="#c9bca2" stroke-width="6" fill="none" opacity=".5"/>
      </g>
      <ellipse cx="140" cy="161" rx="32" ry="9.5" fill="#d6cab1"/><path d="M110 161 Q140 170 170 161" stroke="#c4b79c" stroke-width="2" fill="none"/>`;

    // ręce
    let hands = "";
    if (poza === "przeciera_oczy") {
      const hx = 123 + 3.2 * Math.sin(f * 15);
      hands = `<path d="M70 240 C80 200 100 150 ${hx - 4} 112" stroke="#e4d9c3" stroke-width="18" fill="none" stroke-linecap="round"/>
        <ellipse cx="${hx}" cy="104" rx="11" ry="9.5" fill="${SK}"/><path d="M${hx - 7} 98 Q${hx} 95 ${hx + 7} 98 M${hx - 8} 103 Q${hx} 100 ${hx + 8} 103" stroke="${SK_D}" stroke-width="1.2" fill="none"/>`;
    }
    if (poza === "dlonie") {
      const g = 2.5 * Math.sin(f * 3);
      hands = `<path d="M78 240 C84 222 96 208 ${106 - g} 196" stroke="#e4d9c3" stroke-width="17" fill="none" stroke-linecap="round"/>
        <path d="M202 240 C196 222 184 208 ${174 + g} 196" stroke="#e4d9c3" stroke-width="17" fill="none" stroke-linecap="round"/>
        <ellipse cx="${108 - g}" cy="184" rx="7.5" ry="14" fill="${SK}" transform="rotate(-8 ${108 - g} 184)"/>
        <ellipse cx="${172 + g}" cy="184" rx="7.5" ry="14" fill="${SK}" transform="rotate(8 ${172 + g} 184)"/>
        <path d="M${112 - g} 176 V194 M${168 + g} 176 V194" stroke="${SK_D}" stroke-width="1.2"/>`;
    }
    return { g: `<g transform="translate(140 240) scale(${s}) translate(-140 -240) translate(0 ${dy})">${body}${head}${hands}</g>`, gk };
  }

  function szklankaSVG(f, gk) {
    const x = lerp(70, 117, gk), y = lerp(196, 120, gk), r = lerp(0, -24, gk);
    let steam = "";
    for (let i = 0; i < 3; i++) {
      const pts = [];
      for (let j = 0; j <= 6; j++) {
        const yy = -4 - j * 6;
        pts.push(`${(i - 1) * 4.5 + 3 * Math.sin(f * 2.1 + i * 2 + j * 0.9) * (j / 6 + 0.3)},${yy}`);
      }
      const op = 0.28 + 0.12 * Math.sin(f * 1.7 + i);
      steam += `<polyline points="${pts.join(" ")}" fill="none" stroke="#fff" stroke-width="${2.6 - i * 0.4}" stroke-linecap="round" opacity="${op.toFixed(2)}"/>`;
    }
    const hand = gk > 0.05 ? `<path d="M40 250 C50 220 ${x - 30} ${y + 40} ${x - 16} ${y + 16}" stroke="#e4d9c3" stroke-width="16" fill="none" stroke-linecap="round"/><ellipse cx="${x - 13}" cy="${y + 14}" rx="7.5" ry="8.5" fill="${SK}"/>` : "";
    return `${hand}<g transform="translate(${x} ${y}) rotate(${r})">
      <g transform="translate(0 -1)">${steam}</g>
      <path d="M-9 0 L-8 25 Q0 28 8 25 L9 0 Z" fill="#a8531c" opacity=".9"/>
      <rect x="-9" y="0" width="18" height="4" fill="#d48a4a" opacity=".55"/>
      <ellipse cx="0" cy="0" rx="9" ry="2" fill="#e8b27a" opacity=".85"/>
      <path d="M-9.6 8 L-8.8 26 Q0 29.5 8.8 26 L9.6 8" fill="none" stroke="#c9ccd2" stroke-width="1.6"/>
      <path d="M-9.4 8 H9.4 M-9 14 H9 M-8.8 20 H8.8 M-5 8 L-4 27 M0 8 V28 M5 8 L4 27" stroke="#b7bbc3" stroke-width="1.1"/>
      <path d="M-9.4 10 C-17 10 -17 22 -8.9 22" fill="none" stroke="#c9ccd2" stroke-width="2.4"/>
      <path d="M-6 2 L-5.4 22" stroke="#fff" stroke-width="1.4" opacity=".35"/>
    </g>`;
  }

  function halnySVG(p) {
    const f = p.f, poza = p.halny, ht = p.halnyT;
    let tr = "", headRot = 0, headY = 0, oczy = "otwarte", paszcza = 0;
    if (poza === "klawiatura") {
      const k = ease(ht / 0.9);
      const s = 1 + 0.75 * k, dx = (180 - 262) * k, dy = (226 - 205) * k + Math.abs(Math.sin(ht * 9)) * 2.5 * (1 - k);
      tr = `translate(${dx} ${dy}) translate(262 205) scale(${s}) translate(-262 -205)`;
    }
    if (poza === "ziewa") {
      const k = ht < 1.5 ? Math.sin(Math.PI * clamp(ht / 1.5, 0, 1)) : 0;
      headRot = -9 * k; headY = -3 * k; paszcza = k; if (k > 0.25) oczy = "zamkniete";
    }
    const gl = p.glance; // 0 kamera, 1 na Staszka
    const ex = -2.8 * gl;
    const head = headRot + gl * -4;
    const eyes = oczy === "zamkniete"
      ? `<path d="M244 163 Q251 166 258 163 M266 163 Q273 166 280 163" stroke="#2c2620" stroke-width="1.6" fill="none"/>`
      : `<path d="M243 165 Q251 157 259 165 Q251 170 243 165 Z" fill="#c9c24a"/><path d="M265 165 Q273 157 281 165 Q273 170 265 165 Z" fill="#c9c24a"/>
         <ellipse cx="${251 + ex}" cy="165" rx="1.3" ry="3.4" fill="#111"/><ellipse cx="${273 + ex}" cy="165" rx="1.3" ry="3.4" fill="#111"/>
         <path d="M242 163.5 L259.5 165.2 L259.5 159 L242 159 Z M265 165.2 L282 163.5 L282 159 L265 159 Z" fill="#85796b"/>
         <path d="M242 163.5 L259.5 165.2 M265 165.2 L282 163.5" stroke="#2c2620" stroke-width="1.3"/>`;
    const mouth = paszcza > 0.05
      ? `<ellipse cx="262" cy="${180 + 4 * paszcza}" rx="${5 + 3 * paszcza}" ry="${2 + 8 * paszcza}" fill="#7a2b2b"/><ellipse cx="262" cy="${183 + 6 * paszcza}" rx="${3 + 2 * paszcza}" ry="${1 + 3 * paszcza}" fill="#d97a86"/>
         <path d="M${257 - 2 * paszcza} ${178} l1.2 3.4 l1.2 -3.4 M${264 + 2 * paszcza} 178 l1.2 3.4 l1.2 -3.4" fill="#fff"/>`
      : `<path d="M262 176 Q258 181 254 179.5 M262 176 Q266 181 270 179.5" stroke="#2c2620" stroke-width="1.2" fill="none"/>`;
    const tail = 2 * Math.sin(f * 1.3);
    return `<g transform="${tr}">
      <path d="M290 230 C${312 + tail} 222 ${314 + tail} 196 300 190" stroke="#6e6559" stroke-width="7" fill="none" stroke-linecap="round"/>
      <ellipse cx="262" cy="211" rx="34" ry="30" fill="#7d7366"/>
      <path d="M236 200 Q244 196 248 204 M232 214 Q242 208 248 216 M276 198 Q282 194 288 202 M278 212 Q286 206 292 214" stroke="#4f483f" stroke-width="3" fill="none" stroke-linecap="round"/>
      <ellipse cx="250" cy="236" rx="8" ry="5" fill="#8a8073"/><ellipse cx="274" cy="236" rx="8" ry="5" fill="#8a8073"/>
      <g transform="translate(0 ${headY}) rotate(${head} 262 168)">
        <path d="M242 156 L240 132 L256 146 Z M282 156 L284 132 L268 146 Z" fill="#7d7366"/>
        <path d="M244 151 L243 137 L252 146 Z M280 151 L281 137 L272 146 Z" fill="#c99a94"/>
        <ellipse cx="262" cy="166" rx="27" ry="22" fill="#85796b"/>
        <path d="M252 148 L255 157 M262 146 V156 M272 148 L269 157" stroke="#4f483f" stroke-width="2.4" stroke-linecap="round"/>
        <path d="M238 170 Q244 168 248 172 M286 170 Q280 168 276 172" stroke="#4f483f" stroke-width="2" fill="none"/>
        ${eyes}
        <path d="M259 172 L265 172 L262 175.5 Z" fill="#c98b86"/>
        ${mouth}
        <path d="M250 176 L228 172 M250 179 L229 181 M274 176 L296 172 M274 179 L295 181" stroke="#e8e2d6" stroke-width=".8" opacity=".8"/>
      </g>
    </g>`;
  }

  function sceneSVG(p, vb = "0 0 320 240", w = 320, h = 240) {
    const f = p.f;
    let snow = "";
    for (let i = 0; i < 46; i++) {
      const sp = 0.6 + hash(i) * 0.9;
      const y = 22 + ((hash(i + 50) * 84 + f * 16 * sp) % 84);
      const x = 206 + ((hash(i + 99) * 92 + f * 9 * sp + 3 * Math.sin(f * 0.8 + i)) % 92);
      snow += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(0.7 + hash(i + 7) * 1.1).toFixed(2)}" fill="#fff" opacity="${(0.6 + hash(i + 3) * 0.4).toFixed(2)}"/>`;
    }
    const planks = Array.from({ length: 10 }, (_, i) =>
      `<rect x="${i * 33}" y="0" width="33" height="240" fill="${i % 2 ? "#5e4029" : "#553823"}"/><path d="M${i * 33} 0 V240" stroke="#3a2616" stroke-width="1.6"/><ellipse cx="${i * 33 + 8 + hash(i) * 16}" cy="${30 + hash(i + 20) * 150}" rx="2.2" ry="3.2" fill="#3f2a19" opacity=".7"/>`).join("");
    const st = staszekSVG(p);
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${vb}">
    <defs>
      <linearGradient id="niebo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5f7fb4"/><stop offset=".7" stop-color="#b6c6dc"/><stop offset="1" stop-color="#dfe6ee"/></linearGradient>
      <radialGradient id="lampa" cx="40" cy="70" r="120" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffc870" stop-opacity=".55"/><stop offset="1" stop-color="#ffc870" stop-opacity="0"/></radialGradient>
      <linearGradient id="zimne" x1="0" y1="0" x2="1" y2="0"><stop offset=".45" stop-color="#9fbcff" stop-opacity="0"/><stop offset="1" stop-color="#9fbcff" stop-opacity=".22"/></linearGradient>
      <radialGradient id="winieta" cx="160" cy="120" r="210" gradientUnits="userSpaceOnUse"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>
      <clipPath id="szyba"><rect x="206" y="22" width="92" height="84"/></clipPath>
    </defs>
    ${planks}
    <rect x="0" y="8" width="320" height="9" fill="#3f2a19"/>
    <rect x="198" y="14" width="108" height="100" fill="#3a2717"/>
    <g clip-path="url(#szyba)">
      <rect x="206" y="22" width="92" height="84" fill="url(#niebo)"/>
      <path d="M206 84 L222 66 L232 74 L246 56 L258 70 L270 60 L286 76 L298 68 V106 H206 Z" fill="#9db0cb"/>
      <path d="M246 56 L252 63 L248 62 L244 66 L241 61 Z M270 60 L276 66 L272 65 L268 68 Z" fill="#f2f5fa"/>
      <path d="M206 106 V92 Q230 86 252 94 T298 90 V106 Z" fill="#eef2f7"/>
      <path d="M214 98 l5 -14 l5 14 Z M282 96 l4 -12 l4 12 Z" fill="#4c6170"/>
      ${snow}
    </g>
    <rect x="250" y="22" width="4" height="84" fill="#3a2717"/><rect x="206" y="62" width="92" height="4" fill="#3a2717"/>
    <path d="M200 112 Q226 104 252 110 T306 108 V116 H200 Z" fill="#f4f6fa"/>
    <rect x="6" y="80" width="70" height="5" fill="#3f2a19"/>
    <ellipse cx="34" cy="78" rx="9" ry="3" fill="#6b5a3a"/><path d="M28 77 Q26 64 30 58 H38 Q42 64 40 77 Z" fill="#e9e2c8" opacity=".55"/>
    <path d="M34 72 Q31 67 34 61 Q37 67 34 72 Z" fill="#ffb347"/><rect x="31" y="54" width="6" height="4" fill="#6b5a3a"/>
    <rect x="52" y="70" width="10" height="10" rx="2" fill="#8c3b22"/><rect x="62" y="72" width="9" height="8" rx="2" fill="#4d6b3a"/>
    <rect x="0" y="0" width="320" height="240" fill="url(#lampa)"/>
    ${st.g}
    <rect x="0" y="222" width="320" height="18" fill="#7a4f2c"/><rect x="0" y="222" width="320" height="2.5" fill="#a5734a"/>
    <path d="M0 231 H320" stroke="#6a4325" stroke-width="1"/>
    ${halnySVG(p)}
    ${szklankaSVG(f, st.gk)}
    <rect x="0" y="0" width="320" height="240" fill="url(#zimne)"/>
    <rect x="0" y="0" width="320" height="240" fill="url(#winieta)"/>
    </svg>`;
  }

  // ---------- owca Siwa (siwa.jpg) ----------
  function owcaSVG() {
    const wool = Array.from({ length: 26 }, (_, i) => {
      const a = (i / 26) * Math.PI * 2, rx = 150 + 18 * hash(i), ry = 92 + 12 * hash(i + 5);
      return `<circle cx="${(640 + Math.cos(a) * rx * 0.86).toFixed(1)}" cy="${(470 + Math.sin(a) * ry * 0.8).toFixed(1)}" r="${(46 + 14 * hash(i + 9)).toFixed(1)}" fill="#bdb8ae"/>`;
    }).join("");
    const curls = Array.from({ length: 34 }, (_, i) => `<path d="M${520 + hash(i) * 250} ${400 + hash(i + 40) * 140} q8 -10 16 0" stroke="#a49f95" stroke-width="5" fill="none" stroke-linecap="round"/>`).join("");
    const fence = Array.from({ length: 13 }, (_, i) => `<rect x="${i * 100 + 10}" y="430" width="22" height="240" rx="5" fill="#8a5e36" stroke="#5d3c1e" stroke-width="3"/><path d="M${i * 100 + 10} 434 l11 -16 l11 16" fill="#8a5e36" stroke="#5d3c1e" stroke-width="3"/>`).join("");
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 800">
      <defs>
        <linearGradient id="o-niebo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fb2ea"/><stop offset="1" stop-color="#e6f0fa"/></linearGradient>
        <linearGradient id="o-laka" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9ccc5a"/><stop offset="1" stop-color="#5b8f2c"/></linearGradient>
        <linearGradient id="o-gora" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#93a7c6"/><stop offset="1" stop-color="#b9c8de"/></linearGradient>
      </defs>
      <rect width="1280" height="800" fill="url(#o-niebo)"/>
      <path d="M0 420 L120 330 L190 360 L320 220 L400 290 L470 250 L560 330 L700 200 L790 280 L860 240 L980 330 L1080 260 L1180 320 L1280 290 V520 H0 Z" fill="url(#o-gora)"/>
      <path d="M320 220 L352 256 L336 252 L322 266 L306 250 L292 254 Z M700 200 L736 240 L718 236 L702 250 L686 236 L672 240 Z M1080 260 L1106 290 L1092 287 L1078 298 L1066 286 Z" fill="#fff"/>
      <path d="M0 470 Q320 420 640 450 T1280 440 V800 H0 Z" fill="url(#o-laka)"/>
      <path d="M60 520 q60 -14 120 0 q-60 10 -120 0 Z M900 560 q80 -18 160 0 q-80 14 -160 0 Z" fill="#eef3f8" opacity=".9"/>
      ${fence}
      <rect x="0" y="470" width="1280" height="20" rx="6" fill="#9b6c40" stroke="#5d3c1e" stroke-width="3"/>
      <rect x="0" y="580" width="1280" height="20" rx="6" fill="#9b6c40" stroke="#5d3c1e" stroke-width="3"/>
      <g transform="translate(1010 470)"><rect x="-80" y="-58" width="160" height="62" rx="6" fill="#c89a62" stroke="#5d3c1e" stroke-width="4"/>
        <text x="0" y="-16" text-anchor="middle" font-family="Archivo, Tahoma, sans-serif" font-weight="800" font-size="36" fill="#3d2814">SIWA</text></g>
      <ellipse cx="640" cy="660" rx="230" ry="26" fill="#3d6a1c" opacity=".45"/>
      <rect x="548" y="540" width="26" height="120" rx="10" fill="#3b3631"/><rect x="608" y="550" width="26" height="114" rx="10" fill="#3b3631"/>
      <rect x="672" y="550" width="26" height="114" rx="10" fill="#3b3631"/><rect x="730" y="540" width="26" height="120" rx="10" fill="#3b3631"/>
      ${wool}
      <ellipse cx="640" cy="470" rx="160" ry="100" fill="#c9c5bc"/>
      ${curls}
      <g transform="translate(470 420)">
        <ellipse cx="-58" cy="-6" rx="36" ry="13" fill="#3b3631" transform="rotate(-18 -58 -6)"/>
        <ellipse cx="58" cy="-6" rx="36" ry="13" fill="#3b3631" transform="rotate(18 58 -6)"/>
        <ellipse cx="-56" cy="-4" rx="22" ry="6" fill="#b88d86" transform="rotate(-18 -56 -4)"/>
        <ellipse cx="0" cy="20" rx="56" ry="74" fill="#4a443e"/>
        <circle cx="-10" cy="-40" r="22" fill="#c9c5bc"/><circle cx="14" cy="-44" r="20" fill="#c9c5bc"/><circle cx="0" cy="-58" r="18" fill="#d3cfc6"/>
        <ellipse cx="-24" cy="6" rx="15" ry="11" fill="#f1ead8"/><ellipse cx="24" cy="6" rx="15" ry="11" fill="#f1ead8"/>
        <rect x="-33" y="3" width="18" height="6" rx="3" fill="#1d1b17"/><rect x="15" y="3" width="18" height="6" rx="3" fill="#1d1b17"/>
        <path d="M-40 -4 Q-24 -10 -8 -4 M8 -4 Q24 -10 40 -4" stroke="#4a443e" stroke-width="6" fill="none"/>
        <ellipse cx="0" cy="62" rx="22" ry="14" fill="#5b544d"/><path d="M-10 58 Q0 66 10 58 M0 62 V72 M-8 78 Q0 84 8 78" stroke="#1d1b17" stroke-width="3" fill="none" stroke-linecap="round"/>
        <path d="M-34 104 Q0 122 34 104" stroke="#b33a2a" stroke-width="8" fill="none"/>
        <path d="M-14 114 H14 L18 146 Q0 154 -18 146 Z" fill="#d9a63a" stroke="#7a5714" stroke-width="3"/><circle cx="0" cy="148" r="5" fill="#7a5714"/>
      </g>
    </svg>`;
  }

  // ---------- obraz kamerki: 320x240, 15 kl./s, szum ----------
  const master = document.createElement("canvas"); master.width = 320; master.height = 240;
  const mctx = master.getContext("2d");
  const male = document.createElement("canvas"); const malectx = male.getContext("2d");
  const szum = Array.from({ length: 6 }, () => {
    const c = document.createElement("canvas"); c.width = 320; c.height = 240;
    const x = c.getContext("2d"), d = x.createImageData(320, 240);
    for (let i = 0; i < d.data.length; i += 4) { const v = 128 + (Math.random() - 0.5) * 210; d.data[i] = v + (Math.random() - 0.5) * 30; d.data[i + 1] = v; d.data[i + 2] = v + (Math.random() - 0.5) * 30; d.data[i + 3] = 255; }
    x.putImageData(d, 0, 0); return c;
  });
  const widoczne = () => [$("#cam-duza"), $("#cam-mala")].filter((c) => c && c.offsetParent !== null);

  let camBusy = false, camLast = -1e9, mouth = 0, mouthNext = 0, blinkNext = 2.5, blinkEnd = 0, glanceNext = 5, glanceUntil = 0;
  let pierwszaKlatka = false;
  function camParams() {
    const f = ft(), c = cueAt(f);
    const now = lt();
    if (c.mowi) { if (now >= mouthNext) { let m; do { m = 1 + Math.floor(rnd() * 3); } while (m === mouth); mouth = m; mouthNext = now + 0.09 + rnd() * 0.05; } }
    else mouth = 0;
    if (now >= blinkNext) { blinkEnd = now + 0.13; blinkNext = now + 3 + rnd() * 2; }
    let glance = 0;
    if (c.halny === "wyrzut") {
      if (now >= glanceNext && now > glanceUntil) { glanceUntil = now + 1.1; glanceNext = now + 6 + rnd() * 3; }
      if (now < glanceUntil) glance = 1;
      if (c.spojrzenie != null && f - c.spojrzenie < 0 && f - c.spojrzenie > -1.6) glance = 1;
    }
    return { f, staszek: c.staszek, staszekT: f - c.staszekOd, halny: c.halny, halnyT: f - c.halnyOd, mouth, blink: now < blinkEnd, glance, piksele: c.piksele };
  }
  function camTick(nowMs) {
    if (camBusy || nowMs - camLast < 66) return;
    const cs = widoczne(); if (!cs.length) return;
    camBusy = true; camLast = nowMs;
    const p = camParams();
    const img = new Image();
    const url = URL.createObjectURL(new Blob([sceneSVG(p)], { type: "image/svg+xml" }));
    img.onload = () => {
      if (p.piksele) {
        const w = p.piksele > 0.5 ? 80 : 160; male.width = w; male.height = w * 0.75;
        malectx.imageSmoothingEnabled = true; malectx.drawImage(img, 0, 0, male.width, male.height);
        mctx.imageSmoothingEnabled = false; mctx.drawImage(male, 0, 0, 320, 240);
      } else { mctx.imageSmoothingEnabled = true; mctx.drawImage(img, 0, 0, 320, 240); }
      mctx.globalCompositeOperation = "overlay"; mctx.globalAlpha = 0.2;
      mctx.drawImage(szum[Math.floor(Math.random() * szum.length)], 0, 0);
      mctx.globalCompositeOperation = "multiply"; mctx.globalAlpha = 1; mctx.fillStyle = "#f3ecdc"; mctx.fillRect(0, 0, 320, 240);
      mctx.globalCompositeOperation = "source-over"; mctx.globalAlpha = 0.03 + Math.random() * 0.03; mctx.fillStyle = "#000"; mctx.fillRect(0, 0, 320, 240);
      mctx.globalAlpha = 1;
      for (const c of cs) c.getContext("2d").drawImage(master, 0, 0);
      URL.revokeObjectURL(url); camBusy = false; pierwszaKlatka = true;
    };
    img.onerror = () => { URL.revokeObjectURL(url); camBusy = false; };
    img.src = url;
  }

  // ---------- zdarzenia z cues.json ----------
  function cueAt(f) {
    const c = { staszek: "zaspany", staszekOd: 0, halny: "wyrzut", halnyOd: 0, podpis: "", etykieta: "", mowi: false, napis: "", piksele: 0, spojrzenie: null };
    for (const z of Z) {
      if (z.efekt === "spojrzenie" && f < z.t && c.spojrzenie == null) c.spojrzenie = z.t;
      if (z.t > f) continue;
      if (z.staszek) { c.staszek = z.staszek; c.staszekOd = z.t; }
      if (z.halny) { if (z.halny !== c.halny || z.efekt !== "spojrzenie") c.halnyOd = z.t; c.halny = z.halny; }
      if ("podpis" in z) c.podpis = z.podpis;
      if (z.etykieta) c.etykieta = z.etykieta;
      if (z.efekt === "piksele" && f < z.t + 1) c.piksele = f - z.t < 0.4 ? 1 : 0.4;
    }
    for (const z of Z) if (z.mowi && f >= z.mowi[0] && f < z.mowi[1]) { c.mowi = true; c.napis = z.napis || ""; }
    return c;
  }

  // ---------- czat ----------
  let czatN = -1;
  const godz = (t) => `6:${String(1 + Math.floor(t / 60)).padStart(2, "0")}`;
  function czat(f) {
    const msgs = Z.filter((z) => z.czat && z.t <= f);
    if (msgs.length !== czatN) {
      czatN = msgs.length;
      const html = msgs.map((z) => {
        const i = z.czat.indexOf(":"), kto = z.czat.slice(0, i), txt = z.czat.slice(i + 1).trim();
        if (kto === "System") return `<div class="msg system"><svg><use href="${txt.includes("ekran") ? "#i-ekran" : "#i-ak"}"/></svg>${txt}</div>`;
        return `<div class="msg ${kto === "Staszek" ? "staszek" : ""}"><span class="kto">${kto}</span><span class="czas">${godz(z.t)}</span><p>${txt}</p></div>`;
      }).join("");
      for (const log of $$(".czat-log")) log.innerHTML = html;
    }
    // pisanie naszej wiadomości w polu tekstowym
    const next = Z.find((z) => z.czat && z.czat.startsWith("Ja:") && f >= z.t - 1.5 && f < z.t);
    for (const pole of $$(".czat-pole")) {
      const t = pole.querySelector(".czat-tekst");
      if (next) { const txt = next.czat.slice(3).trim(); const k = clamp((f - (next.t - 1.5)) / 1.2, 0, 1); t.textContent = txt.slice(0, Math.ceil(k * txt.length)); pole.classList.add("pisze"); }
      else { t.textContent = ""; pole.classList.remove("pisze"); }
    }
  }

  // ---------- kursor ----------
  const kursor = $("#kursor");
  let trasa = [];   // [{t, x, y}]
  function kursorTick(t) {
    if (!trasa.length) return;
    let x = trasa[0].x, y = trasa[0].y;
    for (let i = 0; i < trasa.length - 1; i++) {
      const a = trasa[i], b = trasa[i + 1];
      if (t >= a.t && t <= b.t) { const k = ease((t - a.t) / (b.t - a.t)); x = lerp(a.x, b.x, k); y = lerp(a.y, b.y, k); break; }
      if (t > b.t) { x = b.x; y = b.y; }
    }
    kursor.style.transform = `translate(${x - 1}px, ${y - 1}px)`;
  }
  const srodek = (el) => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };

  // ---------- stany ----------
  let jednorazowe = [];  // [{t, fn, done}]
  const o = (t, fn) => jednorazowe.push({ t, fn, done: false });

  const INIT = {
    dzwoni() {
      const toast = $("#toast"); toast.className = "toast"; $("#odbierz").classList.remove("wcisniety");
      document.body.classList.add("kursor");
      o(1.0, () => toast.classList.add("wjazd"));
      o(1.5, () => toast.classList.add("dzwoni"));
      o(2.6, () => { const [x, y] = srodek($("#odbierz")); trasa = [{ t: 0, x: 1210, y: 640 }, { t: 2.6, x: 1210, y: 640 }, { t: 3.5, x: x - 8, y: y + 2 }]; });
      o(3.9, () => $("#odbierz").classList.add("wcisniety"));
      o(4.05, () => { $("#odbierz").classList.remove("wcisniety"); toast.classList.add("zamkniety"); });
      trasa = [{ t: 0, x: 1210, y: 640 }];
    },
    rozmowa() { $("#podpis").classList.remove("show"); $("#etykieta").classList.remove("show"); },
    owca() {
      const w = $("#okno-owca"); w.className = "window active okno-owca"; $("#owca-x").classList.remove("wcisniety");
      document.body.classList.add("kursor");
      trasa = [{ t: 0, x: 980, y: 760 }];
      o(0.5, () => w.classList.add("otwarte"));
      o(2.5, () => { const [x, y] = srodek($("#owca-x")); trasa = [{ t: 0, x: 980, y: 760 }, { t: 2.5, x: 980, y: 760 }, { t: 3.3, x: x - 2, y: y + 1 }]; });
      o(3.6, () => $("#owca-x").classList.add("wcisniety"));
      o(3.75, () => { w.classList.remove("otwarte"); w.classList.add("zamkniete"); });
    },
    ekran() {},
    film() {
      const v = $("#film"); v.pause(); try { v.currentTime = 0; } catch (e) {}
      o(1.0, () => { v.play().catch(() => {}); });
    },
    koniec() { const r = $("#rozlaczono"); r.classList.remove("znika"); o(2.4, () => r.classList.add("znika")); },
  };

  function setStan(nazwa, opts = {}) {
    if (!opts.wewn) znacznik = false;
    const s = ALIAS[nazwa] || "dzwoni";
    stan = s; document.body.dataset.stan = s;
    document.body.classList.remove("kursor");
    jednorazowe = []; trasa = []; czatN = -1;
    filmStart = opts.t != null ? +opts.t : START[s];
    t0 = performance.now();
    blinkNext = 2.5; glanceNext = 5; glanceUntil = 0; mouthNext = 0; seed = 7;
    INIT[s]();
    camLast = -1e9;
    return Date.now();
  }

  function tick(nowMs) {
    const t = lt(), f = ft();
    for (const j of jednorazowe) if (!j.done && t >= j.t) { j.done = true; j.fn(); }
    kursorTick(t);
    if (stan === "rozmowa" || stan === "ekran" || stan === "film") {
      const c = cueAt(f);
      czat(f);
      if (stan === "rozmowa") {
        const pod = $("#podpis"); if (c.podpis) { pod.textContent = c.podpis; pod.classList.add("show"); } else pod.classList.remove("show");
        const et = $("#etykieta"); if (c.etykieta) { et.querySelector("span").textContent = c.etykieta; et.classList.add("show"); } else et.classList.remove("show");
      }
      camTick(nowMs);
    }
    if (napisyWl && stan !== "dzwoni" && stan !== "koniec") $("#napis").textContent = cueAt(f).napis;
    if (znacznik) puls.style.background = "#ff00ff";
    else puls.style.background = (pulsN = 1 - pulsN) ? "rgba(128,128,128,0.012)" : "rgba(128,128,128,0.02)";
    if (kod) {
      // kod czasu pod kadrem (y 1080-1087, poza kadrem 1920x1080): setne części sekundy czasu lokalnego stanu
      const n = Math.max(0, Math.floor(t * 100));
      const g0 = (Math.floor(n / 10) % 50) * 5, g1 = (n % 10) * 25 + 12, g2 = znacznik ? 0 : 255;
      kod.style.background = `linear-gradient(90deg, rgb(${g0},${g0},${g0}) 0 8px, rgb(${g1},${g1},${g1}) 8px 16px, rgb(${g2},${g2},${g2}) 16px 24px)`;
    }
    requestAnimationFrame(tick);
  }
  const puls = $("#puls"); let pulsN = 0;
  // &nagranie=1: do pierwszego wywołania setStan() z zewnątrz w rogu stoi magentowy znacznik 2x2 px,
  // po którym nagrywarka znajduje pierwszą klatkę po resecie osi czasu (klatki ze znacznikiem odrzuca).
  let znacznik = Q.get("nagranie") === "1";
  let kod = null;
  if (znacznik) { kod = document.createElement("div"); Object.assign(kod.style, { position: "fixed", left: "0", top: "1080px", width: "24px", height: "8px", zIndex: 99999 }); document.body.appendChild(kod); }

  // ---------- start ----------
  async function init() {
    // awatary i obraz owcy
    const av = sceneSVG({ f: 0, staszek: "zaspany", staszekT: 5, halny: "wyrzut", halnyT: 5, mouth: 0, blink: false, glance: 0 }, "94 46 92 92", "100%", "100%");
    for (const el of $$("[data-awatar]")) el.innerHTML = av;
    $("#owca-obraz").innerHTML = owcaSVG();
    try { const r = await fetch("cues.json", { cache: "no-store" }); Z = (await r.json()).zdarzenia.sort((a, b) => a.t - b.t); } catch (e) { Z = []; }
    Z.push({ t: 3.6, czat: "System: Rozmowa wideo ze Staszkiem (bacówka) rozpoczęta." }, { t: 28.0, czat: "System: Staszek udostępnia ekran." });
    Z.sort((a, b) => a.t - b.t);
    window.setStan = setStan;
    setStan(Q.get("stan") || "dzwoni", { t: Q.get("t"), wewn: true });
    requestAnimationFrame(tick);
    const obrazy = $$("img").map((im) => (im.complete ? Promise.resolve() : new Promise((r) => { im.onload = im.onerror = r; })));
    await Promise.all([document.fonts.ready, ...obrazy]);
    if (stan === "film") { const v = $("#film"); if (v.readyState < 2) await new Promise((r) => { v.addEventListener("loadeddata", r, { once: true }); setTimeout(r, 6000); }); }
    const czekaj = Date.now();
    while ((stan === "rozmowa" || stan === "ekran" || stan === "film") && !pierwszaKlatka && Date.now() - czekaj < 4000) await new Promise((r) => setTimeout(r, 50));
    window.__gotowe = true;
  }
  init();
})();

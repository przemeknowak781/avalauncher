// Avalauncher service worker: the demo keeps working when the network does not.
// Every URL is relative to this file, so the same worker runs at http://localhost:8777/
// and under /avalauncher/ on GitHub Pages.
//
// - app shell, xp skin, font, engine and every web/data file: precached on install,
//   then network-first (3 s) with the cache as fallback, so fresh deploys show up at once;
// - media/ (3D films, posters, renders): cached on first use, stale-while-revalidate,
//   with byte ranges served from the cache so <video> plays offline;
// - IMGW live API: network-first, falling back to the last cached reading, marked with
//   the X-Avalauncher-Cache header so the app never shows it as live.
//
// Bump VERSION when the precache list changes.

const VERSION = "2026-10-04d";
const SHELL = `ava-shell-${VERSION}`;
const MEDIA = `ava-media-${VERSION}`;
const LIVE = "ava-live"; // survives version bumps: the last IMGW reading stays useful
const KEEP = new Set([SHELL, MEDIA, LIVE]);

// Atomic part: without these the app cannot start at all.
const CORE = [
  "./", "./index.html", "./app.js", "./engine.js", "./style.css",
  "./xp/xp.css", "./xp/xp.js", "./xp/login.css", "./xp/login.js", "./xp/icon.svg", "./vendor/fonts/Archivo-var.ttf", "./manifest.webmanifest",
];
// Best effort, one by one: a single missing file must not cancel the install.
const DATA = [
  "calibration.json", "days.json", "hillshade.png", "kasprowy_2024_25.json", "library_heat.bin", "map.png",
  "mock/days.json", "proof.json", "release_calendar.json", "rl.json", "scenario_cells.bin", "scenarios.json",
  "sectors.json", "sectors_u8.bin", "sentinel_snow.json", "sentinel_snow.png", "sentinel_truecolor.jpg",
  "surrogate.json", "terrain.json", "terrain_f32.bin", "trails.json",
].map((f) => `./data/${f}`);
const EXTRA = [
  "./media/3d/index.json", "./media/media.json",
  "./biblioteka.html", "./biblioteka.css", "./biblioteka.js",
  "./projekt.html", "./projekt.css", "./projekt.js",
];

// Images of projekt.html go to the media cache (media() reads only that one), so the
// landing page shows its hero, posters and calibration board offline even on a first visit.
const LANDING = [
  "hero_koncepcja_1280.jpg", "koncepcja_orbit.jpg", "mapa_zasiegow_orbit.jpg", "przeglad_3d.jpg", "surogat_suwak.jpg",
  "kalibracja_5_lawin.jpg",
].map((f) => `./media/landing/${f}`)
  .concat(["./media/tapeta/tatry_1920.jpg", "./media/tapeta/tatry_1280.jpg"]);
const LANDING_FILMS = ["koncepcja_orbit.mp4", "mapa_zasiegow_orbit.mp4", "przeglad_3d.mp4", "surogat_suwak.mp4"]
  .map((f) => `./media/landing/${f}`);

const BASE = new URL("./", self.location).pathname;
const IMGW_HOST = "danepubliczne.imgw.pl";

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    await cache.addAll(CORE);
    await Promise.allSettled([...DATA, ...EXTRA].map((u) => cache.add(u)));
    const media = await caches.open(MEDIA);
    await Promise.allSettled(LANDING.map((u) => media.add(u)));
    // light 3D previews and their posters: the "Lawina w 3D — podgląd" window plays them at once, offline too
    try {
      const list = await (await fetch("./media/3d/index.json")).json();
      const quick = (list.videos ?? []).flatMap((v) => [v.preview, v.poster]).filter((f) => typeof f === "string");
      await Promise.allSettled(quick.map((f) => media.add(`./media/3d/${f}`)));
    } catch {}
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith("ava-") && !KEEP.has(k)) await caches.delete(k);
    await self.clients.claim();
  })());
});

// The page asks for this once it is idle: pull the 3D films and posters listed in
// media/3d/index.json into the media cache, so the player works offline too.
self.addEventListener("message", (e) => {
  if (e.data?.type === "warm-media") e.waitUntil(warmMedia());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.hostname === IMGW_HOST) { e.respondWith(live(req)); return; }
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;
  const rel = url.pathname.slice(BASE.length);
  if (rel.startsWith("media/") && !rel.endsWith(".json")) { e.respondWith(media(e)); return; }
  e.respondWith(networkFirst(e));
});

// ---------- strategies ----------
const timeout = (ms) => new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms));
const stamp = (r) => r && (r.headers.get("etag") || r.headers.get("last-modified"));

async function networkFirst(e) {
  const req = e.request;
  const cache = await caches.open(SHELL);
  let saved;
  const net = fetch(req).then((r) => {
    if (r.status === 200 && r.type === "basic") {
      const copy = r.clone();
      saved = (async () => {
        const old = await cache.match(req, { ignoreSearch: true });
        if (!(old && stamp(old) && stamp(old) === stamp(copy))) await cache.put(stripSearch(req), copy);
      })().catch(() => {});
    }
    return r;
  });
  // Extend the event now, while respondWith is still pending: the cache refresh must
  // finish even when the cached copy has already answered after the 3 s timeout.
  e.waitUntil(net.then(() => saved, () => {}));
  try {
    return await Promise.race([net, timeout(3000)]);
  } catch {
    const hit = await cache.match(req, { ignoreSearch: true })
      ?? (req.mode === "navigate" ? await cache.match("./index.html") : undefined);
    if (hit) return hit;
    return net; // nothing cached: keep waiting for the network (or fail like it would)
  }
}

const revalidated = new Set();
async function media(e) {
  const req = e.request;
  const key = stripSearch(req).url;
  const cache = await caches.open(MEDIA);
  const hit = await cache.match(key);
  const refresh = () => fetch(key).then(async (r) => {
    if (r.status === 200 && !(hit && stamp(hit) && stamp(hit) === stamp(r))) await cache.put(key, r.clone());
    return r;
  });
  const range = req.headers.get("range");
  if (range) {
    if (hit) {
      if (!revalidated.has(key)) { revalidated.add(key); e.waitUntil(refresh().catch(() => {})); }
      return slice(hit, range);
    }
    e.waitUntil(cache.add(key).catch(() => {})); // first use: fetch the whole file once, in the background
    return fetch(req);
  }
  if (hit) { e.waitUntil(refresh().catch(() => {})); return hit; }
  try { return await refresh(); } catch { return Response.error(); }
}

/** 206 answer for a Range request from a full cached response (cache.put refuses 206). */
async function slice(res, range) {
  const buf = await res.arrayBuffer();
  const size = buf.byteLength;
  const m = /^bytes=(\d*)-(\d*)$/.exec(range.trim());
  let start = m && m[1] !== "" ? Number(m[1]) : NaN;
  let end = m && m[2] !== "" ? Number(m[2]) : NaN;
  if (Number.isNaN(start)) { start = Number.isNaN(end) ? 0 : Math.max(0, size - end); end = size - 1; }
  else if (Number.isNaN(end) || end >= size) end = size - 1;
  if (!m || start >= size || start > end) {
    return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  }
  return new Response(buf.slice(start, end + 1), {
    status: 206, statusText: "Partial Content",
    headers: {
      "Content-Type": res.headers.get("content-type") || "video/mp4",
      "Content-Range": `bytes ${start}-${end}/${size}`,
      "Content-Length": String(end - start + 1),
      "Accept-Ranges": "bytes",
    },
  });
}

async function live(req) {
  const cache = await caches.open(LIVE);
  const key = stripSearch(req).url;
  try {
    const r = await Promise.race([fetch(req), timeout(8000)]);
    if (r.ok && r.type !== "opaque") {
      const body = await r.clone().blob();
      await cache.put(key, new Response(body, {
        headers: { "Content-Type": r.headers.get("content-type") || "application/json", "X-Avalauncher-Cached-At": String(Date.now()) },
      }));
    }
    return r;
  } catch {
    const hit = await cache.match(key);
    if (!hit) return Response.error();
    return new Response(await hit.blob(), {
      status: 200,
      headers: {
        "Content-Type": hit.headers.get("content-type") || "application/json",
        "X-Avalauncher-Cache": hit.headers.get("x-avalauncher-cached-at") || "1",
      },
    });
  }
}

async function warmMedia() {
  try {
    const list = await (await fetch("./media/3d/index.json")).json();
    const files = new Set();
    const walk = (o) => {
      if (Array.isArray(o)) o.forEach(walk);
      else if (o && typeof o === "object") for (const [k, v] of Object.entries(o)) {
        if ((k === "file" || k === "poster" || k === "preview") && typeof v === "string") files.add(new URL(`./media/3d/${v}`, self.location).href);
        else walk(v);
      }
    };
    walk(list);
    for (const f of LANDING_FILMS) files.add(new URL(f, self.location).href);
    const cache = await caches.open(MEDIA);
    for (const u of files) if (!(await cache.match(u))) await cache.add(u).catch(() => {});
  } catch {}
}

function stripSearch(req) {
  const u = new URL(req.url);
  if (!u.search) return req;
  u.search = "";
  return new Request(u.href);
}

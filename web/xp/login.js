// User selection screen at start: "Dowiedz się o projekcie" or "Uruchom aplikację Avalauncher".
// Classic script placed after #splash and before app.js, so it runs before xp.js evaluates.
// While it is shown the app boots behind it, but the welcome splash and the first tray
// balloons are held (the splash is marked "gone", so xp.js never resolves it); "Uruchom"
// then plays the usual "witaj" through xp.logoff() and the balloons follow as today.
// Skipped for deep links (?day=2, ?stan=…, any query or hash), headless screenshot and
// recording tools (tools/shot.mjs, tools/capture: HeadlessChrome UA or webdriver), arrivals
// from projekt.html / biblioteka.html, and after "Uruchom" in the same tab session.
// "#login" forces it (for screenshots and the video).
(function () {
  "use strict";
  const XP = new URL("xp.js", document.currentScript.src).href;
  const KEY = "xp.login";
  const root = document.documentElement;
  const splash = document.getElementById("splash");
  const screen = document.getElementById("screen");
  let box = null;

  function fromSite() {
    try {
      const r = new URL(document.referrer);
      return r.origin === location.origin && /(projekt|biblioteka)\.html$/.test(r.pathname);
    } catch (e) { return false; }
  }
  function seen() { try { return sessionStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function remember(on) { try { on ? sessionStorage.setItem(KEY, "1") : sessionStorage.removeItem(KEY); } catch (e) {} }

  function build() {
    if (box) return;
    box = document.createElement("div");
    box.id = "login";
    box.hidden = true;
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Wybór użytkownika");
    box.innerHTML = `<div class="lg-top"></div>
  <div class="lg-mid">
    <div class="lg-brand">
      <div class="lg-logo"><img src="xp/icon.svg" alt=""><div><b>Avalauncher</b><span>Cyfrowy bliźniak góry</span></div></div>
      <p class="lg-hint">Aby rozpocząć, kliknij użytkownika</p>
    </div>
    <div class="lg-divider" aria-hidden="true"></div>
    <ul class="lg-users">
      <li><a class="lg-user" href="projekt.html"><span class="lg-ava a1"><svg aria-hidden="true"><use href="#i-info"/></svg></span>
        <span class="lg-name"><b>Dowiedz się o projekcie</b><small>Jak to działa, wyniki, dane i licencje</small></span></a></li>
      <li><button class="lg-user" type="button" data-login="app"><span class="lg-ava a2"><img src="xp/icon.svg" alt=""></span>
        <span class="lg-name"><b>Uruchom aplikację Avalauncher</b><small>Mapa stoków, sektory do uwagi, plan przelotu</small></span></button></li>
    </ul>
  </div>
  <div class="lg-bottom">
    <div class="lg-off">
      <button class="lg-power" type="button"><i><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2.6v7" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/><path d="M6.1 5.3a6.2 6.2 0 1 0 7.8 0" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg></i><span>Wyłącz komputer</span></button>
      <div class="lg-tip" role="status" hidden>Lawin nie da się wyłączyć.</div>
    </div>
    <p class="lg-note">Po zalogowaniu możesz zmienić użytkownika w menu Start</p>
  </div>`;
    document.body.appendChild(box);
    box.querySelector('[data-login="app"]').addEventListener("click", launch);
    const tip = box.querySelector(".lg-tip");
    let tipTimer = 0;
    box.querySelector(".lg-power").addEventListener("click", () => {
      tip.hidden = false;
      clearTimeout(tipTimer);
      tipTimer = setTimeout(() => { tip.hidden = true; }, 3500);
    });
  }

  function show(focusApp) {
    build();
    remember(false);
    const sm = document.getElementById("start-menu");
    if (sm) sm.hidden = true;
    document.getElementById("start-btn")?.setAttribute("aria-expanded", "false");
    box.hidden = false;
    if (screen) screen.inert = true;
    if (focusApp) box.querySelector('[data-login="app"]').focus({ preventScroll: true });
  }

  function launch() {
    remember(true);
    if (location.hash === "#login") { try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {} }
    // Put "witaj" up before the login goes away, so the desktop never flashes in between.
    root.classList.remove("nosplash");
    splash?.classList.remove("gone", "fade");
    box.hidden = true;
    if (screen) screen.inert = false;
    import(XP).then((xp) => xp.logoff()).catch(() => splash?.classList.add("gone"));
  }

  // Start menu "Wyloguj" now returns to this screen (as the XP log-off did).
  const off = document.querySelector('.sm-foot [data-action="logoff"]');
  if (off && off.lastChild && off.lastChild.nodeType === 3) off.lastChild.textContent = "Wyloguj / zmień użytkownika";
  document.addEventListener("click", (e) => {
    if (!e.target.closest || !e.target.closest('[data-action="logoff"]')) return;
    e.preventDefault();
    e.stopPropagation();
    show(true);
  }, true);

  const forced = location.hash === "#login";
  const skip = !forced && (location.search || location.hash || navigator.webdriver || /Headless/.test(navigator.userAgent) || fromSite() || seen());
  if (!skip) {
    // Hold the boot: xp.js sees the splash as already gone and waits for "Uruchom".
    root.classList.remove("nosplash");
    splash?.classList.add("gone");
    show(false);
  }
})();

// Avalauncher: strona projektu. Celowo mało kodu: strona działa w pełni bez JavaScriptu.

// Only one film plays at a time, so the jury is never watching two clips at once.
const videos = [...document.querySelectorAll("video")];
for (const v of videos) {
  v.addEventListener("play", () => {
    for (const other of videos) if (other !== v && !other.paused) other.pause();
  });
}

// Highlight the section currently on screen in the top navigation.
const links = new Map([...document.querySelectorAll(".topnav a")].map((a) => [a.getAttribute("href").slice(1), a]));
if ("IntersectionObserver" in window && links.size) {
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      for (const a of links.values()) a.removeAttribute("aria-current");
      links.get(e.target.id)?.setAttribute("aria-current", "true");
    }
  }, { rootMargin: "-45% 0px -50% 0px" });
  for (const id of links.keys()) {
    const el = document.getElementById(id);
    if (el) io.observe(el);
  }
}

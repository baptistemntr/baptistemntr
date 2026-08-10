// Écran d'accueil « Cortex » : le boîtier s'allume, le scroll zoome dans sa dalle jusqu'à
// ce que le configurateur (#app-root, le vrai — pas une maquette) occupe tout l'écran.
//
// #app-root ne vit jamais à deux endroits : ce même nœud est déplacé dans #app-frame
// pendant le zoom (rétréci par transform), puis rendu à sa place normale dans le document
// (#app-dock) une fois le zoom terminé, où il redevient une page ordinaire, défilable,
// interactive. app.js s'exécute normalement quel que soit l'endroit où réside le nœud à
// un instant donné : il retrouve ses éléments par id, indépendamment de leur parent.
(() => {
  "use strict";

  const intro = document.getElementById("intro");
  if (!intro) return; // page sans écran d'accueil (ex. admin.html)

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return; // #intro est masqué par CSS ; #app-root reste à sa place normale dans le flux
  }

  /* --- Géométrie mesurée sur img/hero-crt.webp (boîtier détouré, 702 × 355) --- */
  const DEV_W = 702, DEV_H = 355;
  const SCR = { x: 84, y: 137, w: 247, h: 174 }; // la dalle, dans ce repère

  const fx = SCR.x / DEV_W, fy = SCR.y / DEV_H;
  const fw = SCR.w / DEV_W, fh = SCR.h / DEV_H;
  const ax = (SCR.x + SCR.w / 2) / DEV_W; // ancre = centre de la dalle
  const ay = (SCR.y + SCR.h / 2) / DEV_H;

  const world = document.getElementById("world");
  const screenE = document.getElementById("screen");
  const frame = document.getElementById("app-frame");
  const fxLayer = document.getElementById("crt-fx");
  const appRoot = document.getElementById("app-root");
  const dock = document.getElementById("app-dock");

  const root = document.documentElement;
  root.style.setProperty("--dev-ratio", DEV_H / DEV_W);
  root.style.setProperty("--anchor-x", (ax * 100) + "%");
  root.style.setProperty("--anchor-y", (ay * 100) + "%");
  root.style.setProperty("--s-x", (fx * 100) + "%");
  root.style.setProperty("--s-y", (fy * 100) + "%");
  root.style.setProperty("--s-w", (fw * 100) + "%");
  root.style.setProperty("--s-h", (fh * 100) + "%");

  // Place #app-root dans le cadre avant le premier scroll : à scrollY=0, #intro couvre le
  // viewport, donc ce déplacement est invisible — pas de flash.
  frame.appendChild(appRoot);
  let docked = false;

  let vw, vh, devW, devH, w0, h0, zMax;

  function measure() {
    vw = document.documentElement.clientWidth;
    vh = window.innerHeight;

    devW = Math.min(vw * 0.58, (vh * 0.52) * (DEV_W / DEV_H));
    devH = devW * (DEV_H / DEV_W);
    root.style.setProperty("--dev-w", devW + "px");

    w0 = devW * fw;
    h0 = devH * fh;
    zMax = vw / w0;

    frame.style.width = vw + "px";
    frame.style.height = vh + "px";
  }

  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const smooth = (t) => t * t * (3 - 2 * t);
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  function render(p) {
    const e = easeInOut(p);
    const z = Math.pow(zMax, e);

    // Recadrage : au repos on cadre le boîtier entier ; en avançant, la caméra glisse vers
    // la dalle (pas au centre du boîtier). `k` termine ce glissement tôt, avant que le
    // zoom ne devienne fort.
    const k = smooth(clamp(p / 0.32, 0, 1));
    const offX = (ax - 0.5) * devW * (1 - k);
    const offY = ((ay - 0.5) * devH + vh * 0.055) * (1 - k);

    world.style.transform =
      `translate(${-ax * devW + offX}px, ${-ay * devH + offY}px) scale(${z})`;

    const fade = smooth(clamp((p - 0.42) / 0.34, 0, 1));
    world.style.opacity = String(1 - fade);
    root.style.setProperty("--glow-fade", String(1 - fade));
    root.style.setProperty("--tagline-fade", String(1 - smooth(clamp(p / 0.1, 0, 1))));

    const cx = vw / 2 + offX;
    const cy = vh / 2 + offY;

    // Sur `p` brut, pas sur `e` : l'ouverture doit se terminer pile à la fin réelle du
    // scroll (p=1), là où #stage (position:sticky) se détache et où le nœud est rendu à
    // sa place normale (docked, plus bas). Si elle suivait `e` (doublement adouci), l'écran
    // semblait déjà plein bien avant la fin — l'utilisateur cliquait dans le vide.
    const open = smooth(clamp((p - 0.75) / 0.25, 0, 1));
    const w = w0 * z * (1 - open) + vw * open;
    const h = h0 * z * (1 - open) + vh * open;

    screenE.style.width = w + "px";
    screenE.style.height = h + "px";
    screenE.style.left = cx - w / 2 + "px";
    screenE.style.top = cy - h / 2 + "px";

    const s = Math.min(w / vw, h / vh);
    frame.style.transform = `translate(${(w - vw * s) / 2}px, ${(h - vh * s) / 2}px) scale(${s})`;

    const fxOut = smooth(clamp((p - 0.3) / 0.4, 0, 1));
    fxLayer.style.opacity = String(1 - fxOut);

    document.body.classList.toggle("hero-scrolled", p > 0.015);

    // Le point d'arrivée (p=1) est le seul endroit où #screen couvre exactement le
    // viewport et où le cadre est identique à l'absence de transform (s=1, translate nul) :
    // le nœud peut y passer sans aucun saut visuel.
    if (p >= 0.999 && !docked) {
      docked = true;
      dock.after(appRoot);
      // #stage reste épinglé (position: sticky) tant que son propre défilement n'est pas
      // épuisé, même une fois vidé de son contenu : sans ce masquage, l'écran continue
      // d'afficher un rectangle noir plein cadre pendant ~1 hauteur d'écran de scroll
      // avant de laisser voir l'interface dockée — perçu comme une interface dupliquée.
      document.body.classList.add("hero-docked");
    } else if (p < 0.999 && docked) {
      docked = false;
      frame.appendChild(appRoot);
      document.body.classList.remove("hero-docked");
    }
  }

  function progress() {
    const travel = intro.offsetHeight - vh;
    return travel > 0 ? clamp(window.scrollY / travel, 0, 1) : 0;
  }

  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      render(progress());
      ticking = false;
    });
  }

  function boot() {
    if (document.body.classList.contains("hero-booted")) return;
    document.body.classList.add("hero-booted");
    setTimeout(() => document.body.classList.add("hero-boot-done"), 2800);
  }

  measure();
  render(progress());

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", () => {
    measure();
    render(progress());
  });

  if (window.scrollY > 4) boot();
  else setTimeout(boot, 420);
  window.addEventListener("scroll", boot, { once: true, passive: true });
})();

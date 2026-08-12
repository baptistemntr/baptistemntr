// Écran d'accueil « Cortex » : le boîtier s'allume (noir vers blanc), puis un scroll ou un clic
// zoome directement dans l'écran pour révéler le configurateur opérationnel tout en haut de la page.
// L'utilisateur peut remonter à la vue Cortex à tout moment (scroll vers le haut au sommet ou bouton Vue Cortex).
(() => {
  "use strict";

  const intro = document.getElementById("intro");
  if (!intro) return;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    intro.style.display = "none";
    return;
  }

  /* --- Géométrie mesurée sur img/hero-crt.webp (boîtier détouré, 702 × 355) --- */
  const DEV_W = 702, DEV_H = 355;
  const SCR = { x: 84, y: 137, w: 247, h: 174 }; // la dalle

  const fx = SCR.x / DEV_W, fy = SCR.y / DEV_H;
  const fw = SCR.w / DEV_W, fh = SCR.h / DEV_H;
  const ax = (SCR.x + SCR.w / 2) / DEV_W;
  const ay = (SCR.y + SCR.h / 2) / DEV_H;

  const world = document.getElementById("world");
  const screenE = document.getElementById("screen");
  const frame = document.getElementById("app-frame");
  const fxLayer = document.getElementById("crt-fx");
  const appRoot = document.getElementById("app-root");
  const hint = document.getElementById("hint");
  const stage = document.getElementById("stage");
  const backBtn = document.getElementById("btn-back-to-crt");

  const root = document.documentElement;
  root.style.setProperty("--dev-ratio", DEV_H / DEV_W);
  root.style.setProperty("--anchor-x", (ax * 100) + "%");
  root.style.setProperty("--anchor-y", (ay * 100) + "%");
  root.style.setProperty("--s-x", (fx * 100) + "%");
  root.style.setProperty("--s-y", (fy * 100) + "%");
  root.style.setProperty("--s-w", (fw * 100) + "%");
  root.style.setProperty("--s-h", (fh * 100) + "%");

  // Place #app-root dans le cadre pendant l'intro
  frame.appendChild(appRoot);

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

    const k = smooth(clamp(p / 0.32, 0, 1));
    const offX = (ax - 0.5) * devW * (1 - k);
    const offY = ((ay - 0.5) * devH + vh * 0.055) * (1 - k);

    world.style.transform =
      `translate(${-ax * devW + offX}px, ${-ay * devH + offY}px) scale(${z})`;

    const fade = smooth(clamp((p - 0.4) / 0.35, 0, 1));
    world.style.opacity = String(1 - fade);
    root.style.setProperty("--glow-fade", String(1 - fade));
    root.style.setProperty("--tagline-fade", String(1 - smooth(clamp(p / 0.1, 0, 1))));

    const cx = vw / 2 + offX;
    const cy = vh / 2 + offY;

    const open = smooth(clamp((p - 0.6) / 0.4, 0, 1));
    const w = w0 * z * (1 - open) + vw * open;
    const h = h0 * z * (1 - open) + vh * open;

    screenE.style.width = w + "px";
    screenE.style.height = h + "px";
    screenE.style.left = cx - w / 2 + "px";
    screenE.style.top = cy - h / 2 + "px";

    const s = Math.min(w / vw, h / vh);
    frame.style.transform = `translate(${(w - vw * s) / 2}px, ${(h - vh * s) / 2}px) scale(${s})`;

    const fxOut = smooth(clamp((p - 0.2) / 0.35, 0, 1));
    fxLayer.style.opacity = String(1 - fxOut);
  }

  let animating = false;
  let entered = false;

  // Zoom avant vers le configurateur (Plein écran)
  function enterConfigurator() {
    if (animating || entered) return;
    animating = true;

    const duration = 600; // ms
    const start = performance.now();

    function step(now) {
      const elapsed = now - start;
      const progress = clamp(elapsed / duration, 0, 1);
      render(progress);

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        entered = true;
        animating = false;
        
        document.body.prepend(appRoot);
        intro.classList.add("hero-dismissed");
        setTimeout(() => {
          intro.style.display = "none";
        }, 400);

        window.scrollTo(0, 0);
      }
    }

    requestAnimationFrame(step);
  }

  // Zoom arrière pour revenir au Cortex
  function exitToCrt() {
    if (animating || !entered) return;
    animating = true;

    // Repositionner la page tout en haut avant de zoomer en arrière
    window.scrollTo({ top: 0, behavior: "instant" });

    frame.appendChild(appRoot);
    intro.style.display = "block";
    intro.classList.remove("hero-dismissed");

    const duration = 600; // ms
    const start = performance.now();

    function step(now) {
      const elapsed = now - start;
      const progress = clamp(1 - (elapsed / duration), 0, 1);
      render(progress);

      if (progress > 0) {
        requestAnimationFrame(step);
      } else {
        entered = false;
        animating = false;
        render(0);
      }
    }

    requestAnimationFrame(step);
  }

  // Déclencher le zoom avant au scroll vers le bas
  // Déclencher le retour Cortex au scroll vers le haut si on est au sommet
  let lastScrollTime = 0;
  function onWheel(e) {
    const now = Date.now();
    if (now - lastScrollTime < 500) return;

    if (!entered && e.deltaY > 0) {
      e.preventDefault();
      lastScrollTime = now;
      enterConfigurator();
    } else if (entered && window.scrollY <= 0 && e.deltaY < -20) {
      e.preventDefault();
      lastScrollTime = now;
      exitToCrt();
    }
  }

  let touchStartY = 0;
  function onTouchStart(e) {
    touchStartY = e.touches[0].clientY;
  }
  function onTouchMove(e) {
    const diff = touchStartY - e.touches[0].clientY;
    if (!entered && diff > 15) {
      enterConfigurator();
    } else if (entered && window.scrollY <= 0 && diff < -30) {
      exitToCrt();
    }
  }

  window.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("touchstart", onTouchStart, { passive: true });
  window.addEventListener("touchmove", onTouchMove, { passive: true });

  hint?.addEventListener("click", (e) => {
    e.stopPropagation();
    enterConfigurator();
  });

  stage?.addEventListener("click", () => {
    enterConfigurator();
  });

  backBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    exitToCrt();
  });

  function boot() {
    if (document.body.classList.contains("hero-booted")) return;
    document.body.classList.add("hero-booted");
    setTimeout(() => document.body.classList.add("hero-boot-done"), 2800);
  }

  measure();
  render(0);

  window.addEventListener("resize", () => {
    measure();
    if (!entered) render(0);
  });

  setTimeout(boot, 300);
})();

/* =====================================================================
   app.js — Slide navigation
   ===================================================================== */

(function () {
  "use strict";

  var TOTAL   = document.querySelectorAll(".slide").length;
  var slides  = Array.from(document.querySelectorAll(".slide"));
  var fill    = document.getElementById("progress-fill");
  var counter = document.getElementById("counter");
  var dotsEl  = document.getElementById("dots");
  var btnPrev = document.getElementById("btn-prev");
  var btnNext = document.getElementById("btn-next");
  var current = 0;

  // ── Build dot indicators ──────────────────────────────────────────
  for (var i = 0; i < TOTAL; i++) {
    var d = document.createElement("div");
    d.className = "dot" + (i === 0 ? " active" : "");
    d.dataset.idx = i;
    d.addEventListener("click", function () { go(parseInt(this.dataset.idx)); });
    dotsEl.appendChild(d);
  }

  // ── Navigation core ───────────────────────────────────────────────
  function go(n) {
    if (n < 0 || n >= TOTAL || n === current) return;

    // Direction determines exit direction
    var direction = n > current ? 1 : -1;

    // Exit current slide
    var old = current;
    slides[old].classList.add("exiting");
    slides[old].classList.remove("active");
    setTimeout(function () {
      slides[old].classList.remove("exiting");
    }, 420);

    // Enter new slide from correct side
    current = n;
    slides[current].style.transform = direction > 0
      ? "translateX(48px)"
      : "translateX(-48px)";
    slides[current].style.opacity = "0";
    slides[current].classList.add("active");

    // Force reflow then animate in
    slides[current].getBoundingClientRect();
    slides[current].style.transform = "";
    slides[current].style.opacity   = "";

    updateUI();
  }

  function updateUI() {
    // Progress bar
    fill.style.width = ((current + 1) / TOTAL * 100) + "%";

    // Counter
    counter.textContent = (current + 1) + " / " + TOTAL;

    // Dots
    var dots = dotsEl.querySelectorAll(".dot");
    dots.forEach(function (d, i) {
      d.classList.toggle("active", i === current);
    });

    // Buttons
    btnPrev.disabled = current === 0;
    btnNext.disabled = current === TOTAL - 1;
  }

  // ── Event listeners ───────────────────────────────────────────────
  btnPrev.addEventListener("click", function () { go(current - 1); });
  btnNext.addEventListener("click", function () { go(current + 1); });

  document.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); go(current + 1); }
    if (e.key === "ArrowLeft")                    { e.preventDefault(); go(current - 1); }
    if (e.key === "Home")                         { e.preventDefault(); go(0); }
    if (e.key === "End")                          { e.preventDefault(); go(TOTAL - 1); }
    if (e.key === "f" || e.key === "F")           { toggleFullscreen(); }
    if (e.key === "Escape" && !document.fullscreenElement) { /* let browser handle */ }
  });

  // ── Touch / swipe support ─────────────────────────────────────────
  var touchStart = null;
  document.addEventListener("touchstart", function (e) {
    touchStart = e.changedTouches[0].clientX;
  }, { passive: true });
  document.addEventListener("touchend", function (e) {
    if (touchStart === null) return;
    var dx = e.changedTouches[0].clientX - touchStart;
    touchStart = null;
    if (Math.abs(dx) < 40) return;
    if (dx < 0) go(current + 1);
    else        go(current - 1);
  }, { passive: true });

  // ── Fullscreen ────────────────────────────────────────────────────
  var btnFS = document.getElementById("btn-fullscreen");
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(function () {});
    } else {
      document.exitFullscreen();
    }
  }
  if (btnFS) btnFS.addEventListener("click", toggleFullscreen);
  document.addEventListener("fullscreenchange", function () {
    if (btnFS) btnFS.textContent = document.fullscreenElement ? "⛶ Exit" : "⛶ Full";
  });

  // ── Init ─────────────────────────────────────────────────────────
  updateUI();

})();

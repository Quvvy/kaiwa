/* Hover/focus tooltips for any element with data-tip="…".
 * One shared node and delegated listeners, so it costs nothing per element and
 * works for markup added later (lesson screens, chat bubbles). */
(() => {
  "use strict";

  const DELAY_MS = 400;
  const tip = document.createElement("div");
  tip.className = "tip-pop";
  tip.setAttribute("role", "tooltip");
  tip.id = "kaiwaTip";
  tip.hidden = true;
  let timer = 0;
  let owner = null;

  function place(target) {
    const r = target.getBoundingClientRect();
    tip.style.left = "0px";
    tip.style.top = "0px";
    tip.hidden = false;
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    const left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8));
    let top = r.bottom + 6;
    if (top + h > window.innerHeight - 8) top = r.top - h - 6;
    tip.style.left = `${left}px`;
    tip.style.top = `${Math.max(8, top)}px`;
  }

  function show(target) {
    const text = target.dataset.tip;
    if (!text) return;
    if (!tip.isConnected) document.body.append(tip);
    owner = target;
    tip.textContent = text;
    target.setAttribute("aria-describedby", tip.id);
    place(target);
  }

  function hide() {
    clearTimeout(timer);
    if (owner) owner.removeAttribute("aria-describedby");
    owner = null;
    tip.hidden = true;
  }

  function schedule(target, delay) {
    clearTimeout(timer);
    timer = setTimeout(() => show(target), delay);
  }

  document.addEventListener("mouseover", (e) => {
    const target = e.target.closest && e.target.closest("[data-tip]");
    if (!target) return;
    if (target === owner) return;
    hide();
    schedule(target, DELAY_MS);
  });
  document.addEventListener("mouseout", (e) => {
    const target = e.target.closest && e.target.closest("[data-tip]");
    if (target && !target.contains(e.relatedTarget)) hide();
  });
  document.addEventListener("focusin", (e) => {
    const target = e.target.closest && e.target.closest("[data-tip]");
    if (target && e.target.matches(":focus-visible")) schedule(target, 0);
  });
  document.addEventListener("focusout", hide);
  document.addEventListener("pointerdown", hide, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
  window.addEventListener("scroll", hide, true);
})();

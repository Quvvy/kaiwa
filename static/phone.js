/* Settings → Phone: walks through setup, moving on by itself as each step finishes. */
(() => {
  "use strict";

  const POLL_MS = 3000;
  const root = document.getElementById("phoneSetup");
  if (!root || document.documentElement.dataset.remote === "1") return;

  let shownKey = "";
  let busy = false;

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (key === "onclick") node.addEventListener("click", value);
      else node.setAttribute(key, value);
    }
    node.append(...kids);
    return node;
  }

  function steps(...items) {
    return el("ol", { class: "phone-steps" }, ...items.map((text) => el("li", {}, text)));
  }

  function qr(path) {
    return el("img", { class: "phone-qr", src: path, width: "220", height: "220", alt: "QR code. Scan it with your iPhone's camera." });
  }

  function commands(list) {
    const text = list.join("\n");
    const note = el("span", { class: "status" });
    return el("div", { class: "stack" },
      el("pre", { class: "phone-commands" }, text),
      el("div", { class: "controls" },
        el("button", { class: "secondary", type: "button", onclick: async () => {
          try {
            await navigator.clipboard.writeText(text);
            note.textContent = "Copied. Paste them into a terminal.";
          } catch (_) {
            note.textContent = "Couldn't copy. Select the text above instead.";
          }
        } }, "Copy"),
        note));
  }

  function action(label, path, secondary) {
    return el("button", { type: "button", class: secondary ? "secondary" : "", onclick: async () => {
      if (busy) return;
      busy = true;
      root.querySelectorAll("button").forEach((b) => { b.disabled = true; });
      try {
        const res = await fetch(path, { method: "POST" });
        const data = await res.json();
        if (res.ok) show(data);
      } catch (_) {
        // The server may have just handed over; the next poll catches up.
      } finally {
        busy = false;
        root.querySelectorAll("button").forEach((b) => { b.disabled = false; });
      }
    } }, label);
  }

  function title(text) {
    return el("h3", { class: "phone-title" }, text);
  }

  function turnOff(s) {
    return s.enabled ? el("div", { class: "controls phone-off" }, action("Turn off phone access", "/api/phone/disable", true)) : "";
  }

  function lastUsed(s) {
    if (!s.phone_last_used) return s.phone_online ? `${s.phone_name || "Your phone"} is connected.` : `${s.phone_name || "Your phone"} is offline right now.`;
    const minutes = Math.round((Date.now() / 1000 - s.phone_last_used) / 60);
    return minutes < 2 ? "Your phone is using Kaiwa now." : `Your phone last used Kaiwa ${minutes} minutes ago.`;
  }

  function page(s) {
    const error = s.error ? el("p", { class: "status phone-error" }, s.error) : "";
    if (s.step === "install" || s.step === "signin") {
      const needed = s.step === "signin" ? s.commands.slice(-1) : s.installed ? s.commands.slice(1) : s.commands;
      return [
        title(s.step === "install" ? "Step 1 of 3: Install Tailscale" : "Step 1 of 3: Sign in to Tailscale"),
        el("p", { class: "value" }, "Tailscale connects your phone to this PC privately, wherever you are. Only your own devices can reach Kaiwa."),
        needed.length ? commands(needed) : el("a", { href: "https://tailscale.com/download", target: "_blank", rel: "noopener noreferrer" }, "Download Tailscale"),
        el("p", { class: "status" }, "Run these in a terminal, and sign in when asked. This page moves on by itself."),
      ];
    }
    if (s.step === "enable") {
      if (s.consent_url) {
        return [
          title("Step 1 of 3: Approve secure connections"),
          el("p", { class: "value" }, "Tailscale needs your OK once, so your phone's microphone is allowed to work. It should have opened in your browser."),
          el("p", {}, el("a", { href: s.consent_url, target: "_blank", rel: "noopener noreferrer" }, "Open the approval page")),
          el("p", { class: "status" }, "This page moves on by itself once it's approved."),
          turnOff(s),
        ];
      }
      return [
        title("Step 1 of 3: Turn on phone access"),
        el("p", { class: "value" }, s.service_supported
          ? "Kaiwa will keep running after you close this window and when the PC restarts, and it'll stop the PC going to sleep by itself."
          : "Your phone will be able to reach Kaiwa while it's open on this PC."),
        error,
        el("div", { class: "controls" }, action(s.enabled ? "Try again" : "Turn on", "/api/phone/enable")),
        turnOff(s),
      ];
    }
    if (s.step === "phone") {
      return [
        title("Step 2 of 3: Put Tailscale on your iPhone"),
        qr("/api/phone/qr/app"),
        steps(
          "Scan this with your iPhone's camera and install Tailscale.",
          "Sign in with the same account as this PC.",
          "Tap Allow when it asks to add a VPN.",
        ),
        el("p", { class: "status" }, "This page moves on by itself once your phone joins."),
        turnOff(s),
      ];
    }
    return [
      title("Step 3 of 3: Open Kaiwa on your iPhone"),
      qr("/api/phone/qr/kaiwa"),
      steps(
        "Scan this with your iPhone's camera. It opens Kaiwa in Safari.",
        "Tap Share, then Add to Home Screen.",
        "Open Kaiwa from your home screen from now on.",
      ),
      el("p", { class: "status" }, lastUsed(s)),
      s.service_supported && !s.starts_before_sign_in
        ? el("p", { class: "status" }, "After a restart, Kaiwa starts once you sign in to this PC. To have it start before then, run: sudo loginctl enable-linger $USER")
        : "",
      turnOff(s),
    ];
  }

  function show(s) {
    // Only rebuild when something visible changed, so the QR and links don't flicker.
    const key = JSON.stringify([s.step, s.enabled, s.error, s.consent_url, s.url, s.phone_name, s.phone_online, s.starts_before_sign_in, Math.round((s.phone_last_used || 0) / 60)]);
    if (key === shownKey) return;
    shownKey = key;
    root.replaceChildren(...page(s).filter(Boolean));
  }

  async function poll() {
    if (!busy && root.offsetParent !== null) {
      try {
        const res = await fetch("/api/phone/status");
        if (res.ok) show(await res.json());
      } catch (_) {}
    }
    setTimeout(poll, POLL_MS);
  }
  poll();
})();

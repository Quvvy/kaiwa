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

  /** The two things that stop a phone reaching Kaiwa, said before they happen. */
  function warnings(s) {
    const notes = [];
    if (s.keeps_running && !s.starts_before_sign_in) {
      notes.push("After the PC restarts, your phone reconnects once you've signed in to the PC.");
    }
    if (s.has_battery) {
      notes.push("On a laptop, closing the lid still puts it to sleep, and your phone can't reach Kaiwa until it's open again.");
    }
    return notes.map((text) => el("p", { class: "status" }, text));
  }

  /** Follow the iPhone part on the iPhone, without going back and forth to this screen. */
  function sendSteps(s) {
    if (!s.phone_steps) return "";
    const note = el("span", { class: "status" });
    return el("div", { class: "stack" },
      el("p", { class: "status" }, "Easier on your phone? Send yourself these steps, with the links."),
      el("div", { class: "controls" },
        action("Email them to myself", "/api/phone/email_steps", true),
        el("button", { class: "secondary", type: "button", onclick: async () => {
          try {
            await navigator.clipboard.writeText(s.phone_steps);
            note.textContent = "Copied.";
          } catch (_) {
            note.textContent = "Couldn't copy.";
          }
        } }, "Copy them"),
        note));
  }

  function installPage(s) {
    if (!s.buttons) {
      const needed = s.installed ? s.commands.slice(1) : s.commands;
      return [
        commands(needed),
        el("p", { class: "status" }, "Run these in a terminal, and sign in when asked. This page moves on by itself."),
      ];
    }
    if (s.installed) return [el("p", { class: "status" }, "Tailscale is starting…")];
    if (s.installing) {
      return [el("p", { class: "status" }, "Installing Tailscale… If Windows asks for permission, click Yes.")];
    }
    return [
      s.install_error ? el("p", { class: "status phone-error" }, s.install_error) : "",
      el("div", { class: "controls" }, action("Install Tailscale", "/api/phone/install")),
      el("p", { class: "status" }, "Windows will ask for permission once. Click Yes. By installing, you accept Tailscale's terms."),
      el("p", { class: "status" }, el("a", { href: s.download_url, target: "_blank", rel: "noopener noreferrer" }, "Or download it yourself")),
    ];
  }

  function signInPage(s) {
    if (!s.buttons) {
      return [
        commands(s.commands.slice(-1)),
        el("p", { class: "status" }, "Run this in a terminal, and sign in when asked. This page moves on by itself."),
      ];
    }
    return [
      el("div", { class: "controls" }, action(s.login_url ? "Open sign-in again" : "Sign in to Tailscale", "/api/phone/signin")),
      el("p", { class: "status" }, "A free account. The quickest way is signing in with Google, Apple or Microsoft. This page moves on by itself."),
      s.login_url ? el("p", {}, el("a", { href: s.login_url, target: "_blank", rel: "noopener noreferrer" }, "Open the sign-in page")) : "",
    ];
  }

  function page(s) {
    const error = s.error ? el("p", { class: "status phone-error" }, s.error) : "";
    if (s.step === "install" || s.step === "signin") {
      return [
        title(s.step === "install" ? "Step 1 of 3: Install Tailscale" : "Step 1 of 3: Sign in to Tailscale"),
        el("p", { class: "value" }, "Tailscale connects your phone to this PC privately, wherever you are. Only your own devices can reach Kaiwa."),
        ...(s.step === "install" ? installPage(s) : signInPage(s)),
      ];
    }
    if (s.step === "enable") {
      if (s.consent_url) {
        return [
          title("Step 1 of 3: Approve on Tailscale's page"),
          el("p", { class: "value" }, "It looks technical, but it's safe and only needed once. Approve it, and this lets your iPhone use its microphone with Kaiwa. It should have opened in your browser."),
          el("p", {}, el("a", { href: s.consent_url, target: "_blank", rel: "noopener noreferrer" }, "Open the approval page")),
          el("p", { class: "status" }, "This page moves on by itself once it's approved."),
          turnOff(s),
        ];
      }
      return [
        title("Step 1 of 3: Turn on phone access"),
        el("p", { class: "value" }, s.keeps_running
          ? "Kaiwa will keep running after you close this window, start by itself with this PC, and stop the PC idling to sleep."
          : "Your phone will be able to reach Kaiwa while it's open on this PC."),
        s.https_ready ? "" : el("p", { class: "status" }, "A Tailscale page will open and ask you to approve secure connections. Approve it once, then come back here."),
        ...warnings(s),
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
          "When your iPhone asks to add a VPN, tap Allow. This is how it reaches your PC privately. It doesn't change your other browsing.",
        ),
        el("p", { class: "status" }, "This page moves on by itself once your phone joins."),
        sendSteps(s),
        turnOff(s),
      ];
    }
    return [
      title("Step 3 of 3: Open Kaiwa on your iPhone"),
      el("p", { class: "value" }, "Your iPhone is connected. This is a new code: it opens Kaiwa."),
      qr("/api/phone/qr/kaiwa"),
      steps(
        "Scan this with your iPhone's camera. It opens Kaiwa in Safari.",
        "Tap Share, then Add to Home Screen.",
        "Open Kaiwa from that icon from now on. That's the whole setup.",
      ),
      el("p", { class: "status" }, lastUsed(s)),
      ...warnings(s),
      s.keeps_running ? el("p", { class: "status" }, s.buttons
        ? "Closing this window leaves Kaiwa running in the tray, by the clock. To stop it fully, right-click the icon and choose Quit."
        : "Closing this window leaves Kaiwa running.") : "",
      sendSteps(s),
      turnOff(s),
    ];
  }

  function show(s) {
    // Only rebuild when something visible changed, so the QR and links don't flicker.
    const key = JSON.stringify([s.step, s.enabled, s.error, s.consent_url, s.login_url, s.installing, s.install_error, s.installed, s.https_ready, s.url, s.phone_name, s.phone_online, s.starts_before_sign_in, Math.round((s.phone_last_used || 0) / 60)]);
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

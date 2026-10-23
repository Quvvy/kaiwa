/* Shared microphone for Chat and Learn.
 *
 * Opening a mic on Windows takes 0.5–1 s, so the old "open on every press"
 * cut off the start of what you said and felt slow. This keeps one stream
 * open (released after a few idle minutes), lets you pick the device, and
 * measures the level so a silent recording is reported instead of sent.
 */
(() => {
  "use strict";

  const PREF_ID = "kaiwa_mic_id";
  const PREF_LABEL = "kaiwa_mic_label";
  const IDLE_RELEASE_MS = 3 * 60 * 1000;
  const SILENCE_PEAK = 0.03;

  let stream = null;
  let opening = null;
  let ctx = null;
  let analyser = null;
  let buf = null;
  let idleTimer = null;
  const listeners = new Set();

  function read(key) {
    try { return localStorage.getItem(key) || ""; } catch (_) { return ""; }
  }
  function write(key, value) {
    try { localStorage.setItem(key, value); } catch (_) {}
  }
  function notify() {
    for (const cb of listeners) {
      try { cb(); } catch (_) {}
    }
  }

  function currentLabel() {
    const track = stream && stream.getAudioTracks()[0];
    return (track && track.label) || read(PREF_LABEL) || "";
  }

  async function pickDeviceId() {
    const wantId = read(PREF_ID);
    const wantLabel = read(PREF_LABEL);
    if (!wantId && !wantLabel) return "";
    try {
      const inputs = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
      const byId = inputs.find((d) => d.deviceId === wantId);
      if (byId) return byId.deviceId;
      const byLabel = inputs.find((d) => d.label && d.label === wantLabel);
      return byLabel ? byLabel.deviceId : "";
    } catch (_) {
      return "";
    }
  }

  function scheduleRelease() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(release, IDLE_RELEASE_MS);
  }

  /** Open (or reuse) the selected microphone. Throws with a readable message. */
  async function open() {
    scheduleRelease();
    if (stream && stream.getAudioTracks().some((t) => t.readyState === "live")) return stream;
    if (opening) return opening;
    opening = (async () => {
      const deviceId = await pickDeviceId();
      const audio = { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 };
      if (deviceId) audio.deviceId = { exact: deviceId };
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio });
      } catch (err) {
        if (deviceId) {
          // The saved mic is gone (unplugged): fall back to the system default.
          delete audio.deviceId;
          stream = await navigator.mediaDevices.getUserMedia({ audio });
        } else if (err && err.name === "NotAllowedError") {
          throw new Error("Kaiwa isn't allowed to use the microphone. Allow it in Windows Settings → Privacy → Microphone.");
        } else if (err && err.name === "NotFoundError") {
          throw new Error("No microphone found. Plug one in, then try again.");
        } else {
          throw new Error("Couldn't open the microphone: " + ((err && err.message) || err));
        }
      }
      try {
        ctx = ctx || new AudioContext();
        analyser = ctx.createAnalyser();
        analyser.fftSize = 1024;
        buf = new Uint8Array(analyser.fftSize);
        ctx.createMediaStreamSource(stream).connect(analyser);
      } catch (_) {
        analyser = null;
      }
      stream.getAudioTracks()[0]?.addEventListener("ended", () => { stream = null; notify(); });
      notify();
      return stream;
    })();
    try {
      return await opening;
    } finally {
      opening = null;
    }
  }

  function release() {
    clearTimeout(idleTimer);
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null;
    analyser = null;
    notify();
  }

  /** Current input level, 0–1. */
  function level() {
    if (!analyser) return 0;
    if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
    analyser.getByteTimeDomainData(buf);
    let peak = 0;
    for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
    return Math.min(1, peak / 100);
  }

  async function devices() {
    const inputs = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
    return inputs.map((d) => ({ id: d.deviceId, label: d.label || "Microphone" }));
  }

  /** Switch microphone; also tells the server so desktop push-to-talk uses it too. */
  async function select(id, label) {
    write(PREF_ID, id || "");
    write(PREF_LABEL, label || "");
    release();
    fetch("/api/prefs/mic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: label || "" }),
    }).catch(() => {});
    await open();
  }

  /**
   * Start recording right away (the stream is usually already open).
   * Returns { stop(): Promise<{blob, ext, ms, peak, silent}> }.
   */
  async function record() {
    const s = await open();
    if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
    const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m)) || "";
    const rec = mime ? new MediaRecorder(s, { mimeType: mime }) : new MediaRecorder(s);
    const chunks = [];
    let peak = 0;
    const started = performance.now();
    const meter = setInterval(() => { peak = Math.max(peak, level()); }, 50);
    rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    rec.start(200);
    return {
      stop() {
        clearInterval(meter);
        scheduleRelease();
        return new Promise((resolve) => {
          rec.onstop = () => {
            const type = rec.mimeType || mime || "audio/webm";
            resolve({
              blob: new Blob(chunks, { type }),
              ext: type.includes("mp4") ? "m4a" : "webm",
              ms: performance.now() - started,
              peak,
              silent: peak < SILENCE_PEAK,
            });
          };
          if (rec.state === "recording") {
            rec.requestData();
            rec.stop();
          } else {
            rec.onstop();
          }
        });
      },
    };
  }

  /** A device dropdown with a live level meter. Talk and watch the bar move. */
  function picker({ compact = false } = {}) {
    const wrap = document.createElement("div");
    wrap.className = "mic-picker" + (compact ? " compact" : "");
    const select = document.createElement("select");
    select.setAttribute("aria-label", "Microphone");
    const meter = document.createElement("span");
    meter.className = "mic-meter";
    meter.setAttribute("aria-hidden", "true");
    const bar = document.createElement("span");
    meter.append(bar);
    const note = document.createElement("span");
    note.className = "mic-note";
    wrap.append(select, meter, note);

    async function fill() {
      try {
        await open();
        note.textContent = "";
      } catch (err) {
        note.textContent = String(err.message || err);
      }
      let list = [];
      try { list = await devices(); } catch (_) {}
      const active = currentLabel();
      select.replaceChildren();
      for (const d of list) {
        const opt = document.createElement("option");
        opt.value = d.id;
        opt.textContent = d.label;
        if (d.label === active) opt.selected = true;
        select.append(opt);
      }
      if (!list.length) {
        const opt = document.createElement("option");
        opt.textContent = "No microphone found";
        select.append(opt);
        select.disabled = true;
      }
    }
    select.addEventListener("change", async () => {
      const opt = select.selectedOptions[0];
      note.textContent = "";
      try {
        await select_(opt.value, opt.textContent);
      } catch (err) {
        note.textContent = String(err.message || err);
      }
    });
    const tick = () => {
      if (!wrap.isConnected) return;
      bar.style.width = Math.round(level() * 100) + "%";
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(() => { fill(); tick(); });
    return wrap;
  }
  const select_ = select;

  navigator.mediaDevices?.addEventListener?.("devicechange", notify);

  window.KaiwaMic = {
    picker,
    open,
    release,
    level,
    devices,
    select,
    record,
    selectedLabel: () => read(PREF_LABEL),
    currentLabel,
    isOpen: () => !!stream,
    onChange: (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
  };
})();

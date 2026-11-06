/* Kaiwa daily lesson (Learn tab): Review → New phrases → Listen → Speak.
 * Self-contained: own audio player, hold-to-speak recorder with a live mic
 * meter, and keyboard shortcuts (Enter = primary, hold Space = speak, R = replay).
 * index.html calls KaiwaCourse.show() when the tab opens. */
(() => {
  "use strict";

  const root = document.getElementById("course");
  if (!root) return;

  let today = null;
  let placementAfterHome = false; // Settings asked to open the placement test
  let showRomaji = readPref("kaiwa_course_romaji", "1") === "1";
  let optionsOpen = false; // keep Options open while limits are edited (the home re-renders on save)
  const keys = { primary: null, hold: null, replay: null, choice: null, meanings: null, text: null, tab: null,
    grade: null, space: null, undo: null, hint: null, back: null };

  // ---------- helpers ----------
  function readPref(key, fallback) {
    try { return localStorage.getItem(key) ?? fallback; } catch (_) { return fallback; }
  }
  function writePref(key, value) {
    try { localStorage.setItem(key, value); } catch (_) {}
  }
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
  }
  function kbd(label) {
    return el("kbd", { text: label });
  }
  async function api(path, opts) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    return data;
  }
  function postJson(path, body) {
    return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  /** A screen that isn't a card: nothing left over from the last lesson may answer a key. */
  function clearKeys() {
    for (const k of Object.keys(keys)) keys[k] = null;
  }
  function learnVisible() {
    return document.body.dataset.mode === "learn";
  }

  // ---------- keyboard ----------
  document.addEventListener("keydown", (e) => {
    if (!learnVisible()) return;
    if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z") && !e.shiftKey) {
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA") return; // let text boxes undo their own typing
      e.preventDefault();
      if (keys.undo) keys.undo();
      else undoFromHome();
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "Escape" && askPanel.isOpen()) {
      e.preventDefault();
      askPanel.close();
      return;
    }
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === "?" && askContext) {
      e.preventDefault();
      askPanel.toggle();
      return;
    }
    if (e.key === " " && keys.hold && !keys.space) {
      e.preventDefault();
      if (!e.repeat) keys.hold.start();
    } else if (e.key === "Enter" && keys.primary && !(tag === "BUTTON" && e.target.matches(":focus-visible"))) {
      e.preventDefault();
      keys.primary();
    } else if ((e.key === "r" || e.key === "R") && keys.replay && !e.repeat) {
      e.preventDefault();
      keys.replay();
    } else if (e.key === "Tab" && keys.tab && !e.shiftKey) {
      e.preventDefault();
      keys.tab();
    } else if (e.key === "Backspace" && keys.back) {
      e.preventDefault();
      keys.back();
    } else if ((e.key === "h" || e.key === "H") && keys.hint && !e.repeat) {
      e.preventDefault();
      keys.hint();
    } else if ((e.key === "t" || e.key === "T") && keys.text && !e.repeat) {
      e.preventDefault();
      keys.text();
    } else if ((e.key === "m" || e.key === "M") && keys.meanings && !e.repeat) {
      e.preventDefault();
      keys.meanings();
    } else if (/^[1-9]$/.test(e.key) && keys.choice && !e.repeat) {
      e.preventDefault();
      keys.choice(Number(e.key) - 1);
    } else if (/^[1-4]$/.test(e.key) && keys.grade && !e.repeat) {
      e.preventDefault();
      keys.grade(Number(e.key));
    } else if (e.key === " " && keys.space && !keys.hold) {
      e.preventDefault();
      if (!e.repeat) keys.space();
    }
  });
  document.addEventListener("keyup", (e) => {
    if (e.key === " " && keys.hold) {
      e.preventDefault();
      keys.hold.stop();
    }
  });

  // ---------- audio ----------
  const audioCache = new Map();
  let currentAudio = null;
  let audioProblem = "";

  // While the desktop app is still starting the voice engine, hold audio requests
  // here (one cheap poll) instead of sending a burst that would wait server-side
  // and use up the browser's six connections.
  let voiceReadyPromise = null;
  function voiceReady() {
    if (!voiceReadyPromise) {
      voiceReadyPromise = (async () => {
        for (;;) {
          let state = "ready";
          try { state = (await api("/api/tts/state")).state; } catch (_) {}
          if (state !== "starting") break;
          setAudioProblem("starting");
          await new Promise((r) => setTimeout(r, 700));
        }
        if (audioProblem === STARTING_NOTE) setAudioProblem(null);
      })();
    }
    return voiceReadyPromise;
  }
  const STARTING_NOTE = "Voice engine starting… audio plays in a few seconds.";

  function audioFor(text, { slow = false, voice = "a" } = {}) {
    const key = `${voice}|${slow ? 1 : 0}|${text}`;
    if (!audioCache.has(key)) {
      const pending = voiceReady().then(() => postJson("/api/course/tts", { text, slow, voice })).then((d) => d.audio_base64);
      pending.catch(() => audioCache.delete(key));
      audioCache.set(key, pending);
    }
    return audioCache.get(key);
  }
  function stopAudio() {
    if (currentAudio) {
      window.KaiwaAudio.stop();
      currentAudio = null;
    }
  }
  async function play(text, opts = {}) {
    stopAudio();
    if (opts && opts.clip) {
      // A mined line: the real speaker. If the clip can't load, the voice reads the line instead.
      currentAudio = window.KaiwaAudio.playUrl(opts.clip, { rate: opts.slow ? 0.75 : 1 });
      if ((await currentAudio) !== false) return;
      opts = { ...opts, clip: null };
    }
    let b64;
    try {
      b64 = await audioFor(text, opts);
    } catch (err) {
      setAudioProblem(err);
      return;
    }
    setAudioProblem(null);
    currentAudio = window.KaiwaAudio.play(b64);
    await currentAudio;
  }
  function prefetch(items) {
    for (const [text, opts] of items) audioFor(text, opts).catch(() => {});
  }
  function setAudioProblem(err) {
    audioProblem = err === "starting" ? STARTING_NOTE
      : err ? "No audio: the voice engine stopped." : "";
    const note = root.querySelector(".lesson-audio-note");
    if (note) fillAudioNote(note);
  }
  /** The no-audio note, with a button that starts the voice engine again. */
  function fillAudioNote(note) {
    note.hidden = !audioProblem;
    if (!audioProblem || audioProblem === STARTING_NOTE) {
      note.textContent = audioProblem;
      return;
    }
    const btn = el("button", { type: "button", class: "secondary", onclick: async () => {
      btn.disabled = true;
      btn.textContent = "Restarting the voice…";
      let s = {};
      try {
        s = await postJson("/api/tts/engine/restart", {});
      } catch (err) {
        s = { error: String(err.message || err) };
      }
      if (s.state === "up") {
        audioCache.clear();
        setAudioProblem(null);
      } else {
        btn.disabled = false;
        btn.textContent = "Restart voice";
        note.firstChild.textContent = s.error || "The voice engine didn't come back. Restart Kaiwa, or switch engines in Settings → Speech.";
      }
    } }, "Restart voice");
    note.replaceChildren(el("span", { text: audioProblem + " " }), btn);
  }
  function playRow(text, opts = {}) {
    return el("div", { class: "lesson-play" },
      el("button", { class: "secondary", type: "button", onclick: () => play(text, opts) }, "Play", kbd("R")),
      el("button", { class: "secondary", type: "button", onclick: () => play(text, { ...opts, slow: true }) }, "Slow"),
    );
  }
  // Hearing a phrase from different speakers makes it easier to catch from anyone
  // (talker variability: Logan et al. 1991, Barcroft & Sommers 2005). A replay
  // brings the next voice; a review card gets one of them.
  const VOICES = ["a", "b", "c"];
  function voiceCycler(text) {
    let turn = 0;
    return () => {
      const voice = VOICES[turn % VOICES.length];
      turn += 1;
      return play(text, { voice });
    };
  }
  function reviewVoice(card) {
    return { voice: VOICES[(card.reps || 0) % VOICES.length] };
  }

  // ---------- hold to speak (shared warm mic, live level) ----------
  /**
   * A wide hold-to-speak bar. `onAudio(blob, ext)` gets real speech;
   * `onProblem(message)` explains anything else (too short, silence, mic errors)
   * so a press never ends with nothing on screen.
   */
  function holdControl(label, onAudio, onProblem) {
    const fill = el("span", { class: "hold-level" });
    const text = el("span", { class: "hold-label" }, label, kbd("Space"));
    const btn = el("button", { class: "hold", type: "button" }, fill, text);
    let pressing = false;
    let rec = null;
    let raf = 0;

    function setLabel(...content) {
      text.replaceChildren(...content);
    }
    function resetLabel() {
      setLabel(label, kbd("Space"));
    }
    function meter() {
      btn.style.setProperty("--level", window.KaiwaMic.level().toFixed(3));
      raf = requestAnimationFrame(meter);
    }
    async function start() {
      if (pressing || btn.disabled) return;
      pressing = true;
      stopAudio();
      setLabel("Opening microphone…");
      let handle;
      try {
        handle = await window.KaiwaMic.record();
      } catch (err) {
        pressing = false;
        resetLabel();
        onProblem(String(err.message || err));
        return;
      }
      if (!pressing) {
        // Let go before the mic was ready: nothing usable was recorded.
        handle.stop();
        resetLabel();
        onProblem(window.KaiwaMic.takeJustGranted()
          ? "Microphone's on. Now hold the button and speak."
          : "Released before the microphone opened. Hold until the bar turns red.");
        return;
      }
      rec = handle;
      btn.classList.add("recording");
      setLabel("Listening… release to check");
      meter();
    }
    async function stop() {
      if (!pressing) return;
      pressing = false;
      if (!rec) return; // start() reports the early release
      const handle = rec;
      rec = null;
      cancelAnimationFrame(raf);
      btn.style.setProperty("--level", "0");
      btn.classList.remove("recording");
      resetLabel();
      const res = await handle.stop();
      if (res.ms < 400) {
        onProblem("Too short. Hold the whole time you speak.");
      } else if (res.silent) {
        onProblem(window.KaiwaMic.noSoundMessage());
      } else {
        onAudio(res.blob, res.ext);
      }
    }
    btn.addEventListener("pointerdown", (e) => { e.preventDefault(); btn.setPointerCapture?.(e.pointerId); start(); });
    btn.addEventListener("pointerup", stop);
    btn.addEventListener("pointercancel", stop);
    btn.addEventListener("contextmenu", (e) => e.preventDefault());
    btn.holdApi = { start, stop };
    return btn;
  }

  function micRow() {
    return window.KaiwaMic.remote ? el("span", {}) : window.KaiwaMic.picker({ compact: true });
  }

  function showProblem(result) {
    return (message) => result.replaceChildren(el("p", { class: "verdict off", text: message }));
  }

  function audioForm(blob, ext, fields) {
    const form = new FormData();
    form.append("audio", blob, "utterance." + ext);
    for (const [k, v] of Object.entries(fields)) form.append(k, String(v));
    return form;
  }

  // ---------- shared pieces ----------
  /** Romaji only while the text still has kana you haven't learned (and the box is ticked). */
  function needsRomaji(jp) {
    if (!showRomaji) return false;
    const known = (today && today.kana_known) || "";
    for (const ch of jp) {
      if (ch >= "\u3041" && ch <= "\u30ff" && ch !== "・" && !known.includes(ch)) return true;
    }
    return false;
  }
  function shuffle(list) {
    const out = [...list];
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }
  /** `answer` plus up to n-1 different values from `pool`, shuffled. */
  function choicesFor(answer, pool, n = 4, near = []) {
    const nearby = shuffle([...new Set(near)].filter((v) => v !== answer));
    const others = shuffle([...new Set(pool)].filter((v) => v !== answer && !nearby.includes(v)));
    return shuffle([answer, ...[...nearby, ...others].slice(0, n - 1)]);
  }
  /** Known kana this one gets mistaken for, so drills offer the look-alikes first. */
  function alikeIn(k, pool) {
    return pool.filter((x) => (k.alike || []).includes(x.char));
  }
  /** After a miss: the picture for this kana, and how to tell it from what it looks like. */
  function kanaHelp(k, pool) {
    const twins = alikeIn(k, pool);
    return el("div", { class: "kana-help" },
      k.hook ? el("p", { class: "kana-hook", text: k.hook }) : null,
      twins.length ? el("p", { class: "kana-twins" }, "Don't mix it up with ",
        twins.map((x, i) => [i ? ", " : "", el("span", { lang: "ja", text: x.char }), ` (${x.ro})`]), ".") : null);
  }
  /**
   * One multiple-choice question. Calls onAnswer(right, picked) after showing the result.
   * Number keys pick an option; a right answer moves on by itself.
   */
  function choiceBlock({ options, answer, onAnswer, jp = false, explain = "" }) {
    const feedback = el("p", { class: "verdict", role: "status" });
    let done = false;
    const buttons = options.map((opt, i) =>
      el("button", { class: "secondary choice", type: "button", lang: jp ? "ja" : null, onclick: () => pick(i) },
        el("span", { class: "choice-key", text: String(i + 1) }), String(opt)));
    function pick(i) {
      if (done || i >= options.length) return;
      done = true;
      keys.choice = null;
      const right = options[i] === answer;
      buttons.forEach((b) => { b.disabled = true; });
      buttons[i].classList.add(right ? "right" : "wrong");
      noteResult({ picked: options[i], correct: answer, right });
      if (!right) buttons[options.indexOf(answer)].classList.add("right");
      feedback.className = "verdict " + (right ? "good" : "off");
      feedback.textContent = (right ? "Right." : "Not quite.") + (explain ? " " + explain : "");
      onAnswer(right, options[i]);
    }
    pendingChoice = pick; // frame() hands it to the number keys once the screen is up
    return el("div", { class: "choice-block" }, el("div", { class: "choices" }, buttons), feedback);
  }
  function meaningChoices(word, pool) {
    return { options: choicesFor(word.en, pool.map((w) => w.en)), answer: word.en };
  }

  // Where you were in a lesson, so leaving and coming back doesn't start it over.
  function spotIn(key) {
    try {
      const d = JSON.parse(readPref("kaiwa_spot", "{}"));
      return d.key === key ? Number(d.at) || 0 : 0;
    } catch (_) { return 0; }
  }
  function keepSpot(key, at) {
    writePref("kaiwa_spot", JSON.stringify({ key, at }));
  }
  function clearSpot() {
    writePref("kaiwa_spot", "{}");
  }
  /**
   * Record a finished lesson step, then go on. A lost connection (a phone between
   * networks, say) must not lose the lesson: it says so and offers to try again.
   */
  async function saveThen(path, body, then) {
    try {
      const out = await postJson(path, body);
      clearSpot();
      return then(out);
    } catch (err) {
      const again = () => saveThen(path, body, then);
      frame({
        title: "Couldn't save that",
        body: el("div", { class: "card-body" },
          el("p", { class: "verdict off", text: "Your lesson is done, but saving it failed. Check that Kaiwa can reach your PC, then try again." }),
          el("p", { class: "status", text: String(err.message || err) })),
        actions: [primaryButton("Try again", again)],
        primary: again,
      });
      return undefined;
    }
  }

  /** Learner log: events only the page sees (the server logs answers itself). */
  function track(kind, data = {}) {
    postJson("/api/course/log", { kind, data }).catch(() => {});
  }

  /** First answers inside lessons count as each new card's first review. */
  function lessonGrade(cardId, outcome) {
    postJson("/api/course/grade", { card_id: cardId, ...outcome, lesson: true }).catch(() => {});
  }

  let pendingChoice = null;
  let pendingText = null;
  function wait(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  /** "Frieren E03 · 12:34" for a mined line's source. */
  function sourceLine(src) {
    if (!src) return "";
    const t = src.start_ms != null ? Math.floor(src.start_ms / 1000) : null;
    const at = t == null ? "" : `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
    return [src.title, at].filter(Boolean).join(" · ");
  }
  /** The line as written, with the mined word marked inside it (never furigana). */
  function minedLine(m) {
    const at = m.word ? m.text.indexOf(m.word) : -1;
    const parts = at < 0 ? [m.text]
      : [m.text.slice(0, at), el("mark", { class: "mined-hl", text: m.word }), m.text.slice(at + m.word.length)];
    return el("p", { class: "mined-line", lang: "ja" }, parts);
  }
  /**
   * The back of a mined card, read top to bottom: the line, its reading right under it,
   * what it means, one note, then where it's from with the scene as a small picture.
   */
  function minedBack(m) {
    const src = sourceLine(m.source);
    const thumb = m.image_url ? el("img", {
      class: "mined-thumb", src: m.image_url, alt: "The scene", loading: "lazy", title: "Click to enlarge",
      onclick: (e) => e.currentTarget.classList.toggle("open"),
    }) : null;
    // Imported decks (Kaishi) teach one word per sentence: its reading, meaning, voice and note.
    const word = m.word && m.word_meaning ? el("div", { class: "mined-word-block" },
      el("p", { class: "mined-word-line" },
        el("strong", { lang: "ja", text: m.word }),
        m.word_reading && m.word_reading !== m.word ? el("span", { class: "mined-word-reading", lang: "ja", text: m.word_reading }) : null,
        el("span", { class: "mined-word-meaning", text: m.word_meaning }),
        m.word_audio_url ? el("button", { type: "button", class: "secondary mined-word-play", "aria-label": `Hear ${m.word}`,
          onclick: () => play(m.word, { clip: m.word_audio_url }) }, "▶") : null),
      m.notes ? el("p", { class: "mined-note", text: m.notes }) : null) : null;
    return el("div", { class: "mined-back" },
      minedLine(m),
      m.kana && m.kana !== m.text ? el("p", { class: "mined-kana", lang: "ja", text: m.kana }) : null,
      el("p", { class: "mined-en", text: m.en }),
      m.note ? el("p", { class: "mined-note", text: m.note }) : null,
      word,
      thumb || src ? el("div", { class: "mined-foot" }, thumb, src ? el("span", { class: "mined-source", text: src }) : null) : null);
  }
  function phraseBlock(p) {
    return el("div", { class: "phrase" },
      el("p", { class: "phrase-jp", lang: "ja", text: p.jp }),
      needsRomaji(p.jp) && p.ro ? el("p", { class: "phrase-ro", text: p.ro }) : null,
      el("p", { class: "phrase-en", text: p.en }),
      p.note ? el("p", { class: "phrase-note", text: p.note }) : null,
    );
  }
  function verdictLine(band) {
    if (band === "good") return el("p", { class: "verdict good", text: "That's it." });
    if (band === "close") return el("p", { class: "verdict close", text: "Close. Listen again and try once more." });
    return el("p", { class: "verdict off", text: "Not quite. Play it slowly, then try again." });
  }
  /** The target's sounds with the ones that didn't come through marked. */
  function diffLine(diff) {
    if (!diff || !diff.length || diff.every((r) => r.ok)) return null;
    return el("p", { class: "diff-line" }, "Listen for ",
      el("span", { lang: "ja", class: "diff-target" }, diff.map((r) => (r.ok ? r.text : el("mark", { text: r.text })))));
  }
  function heardLine(prefix, heard, extra) {
    return el("p", { class: "heard-line" }, prefix, el("span", { lang: "ja", text: heard }), extra || null);
  }

  /** Keep a corrected line or example as one of your own phrases. */
  function keepButton(jp, en) {
    const btn = el("button", { type: "button", class: "secondary", onclick: async () => {
      btn.disabled = true;
      try {
        await postJson("/api/course/mine", { jp, en: en || "" });
        btn.textContent = "Kept";
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "Couldn't keep it";
      }
    } }, "Keep");
    return btn;
  }

  // ---------- ask ----------
  // What the current screen is about; frame() sets it, results add to it.
  let askContext = null;
  function noteResult(result) {
    if (askContext) askContext = { ...askContext, result };
  }

  // A chat box docked in the bottom-right corner, opened from a button that sits
  // there on every lesson screen. It overlays the corner; the lesson doesn't move.
  const askPanel = (() => {
    const log = el("div", { class: "ask-log", "aria-live": "polite" });
    const about = el("span", { class: "ask-about" });
    const input = el("input", { type: "text", maxlength: "500", placeholder: "Ask about this screen…" });
    const quick = (label, key) => el("button", { type: "button", class: "secondary", onclick: () => send("", key) }, label);
    const wrongBtn = quick("What did I get wrong?", "wrong");
    const launcher = el("button", { type: "button", class: "ask-launcher", hidden: true, onclick: () => open() },
      "Ask a question", kbd("?"));
    const panel = el("section", { class: "ask-dock", hidden: true, "aria-label": "Ask a question" },
      el("div", { class: "ask-head" },
        el("span", { class: "ask-title", text: "Ask" }),
        about,
        el("button", { type: "button", class: "ask-close", "aria-label": "Close", onclick: () => close() }, "✕")),
      log,
      el("div", { class: "ask-quick" }, quick("Break this down", "breakdown"), quick("Why?", "why"), wrongBtn),
      el("form", { class: "ask-form", onsubmit: (e) => { e.preventDefault(); send(input.value, ""); } },
        input, el("button", { type: "submit" }, "Send")));
    document.body.append(launcher, panel);

    function refresh() {
      if (!askContext) {
        launcher.hidden = true;
        return close();
      }
      launcher.hidden = !panel.hidden;
      about.textContent = askContext.jp || askContext.title || "";
      about.lang = askContext.jp ? "ja" : "";
      wrongBtn.hidden = !askContext.result;
    }
    function open() {
      if (!askContext) return;
      panel.hidden = false;
      refresh();
      input.focus();
    }
    function close() {
      panel.hidden = true;
      launcher.hidden = !askContext;
      if (document.activeElement && panel.contains(document.activeElement)) document.activeElement.blur();
    }
    async function send(question, key) {
      if (!askContext || (!key && !question.trim())) return;
      const label = key ? { breakdown: "Break this down", why: "Why?", wrong: "What did I get wrong?" }[key] : question;
      const answer = el("div", { class: "ask-msg ask-msg-a" }, el("p", { class: "pending", text: "Thinking…" }));
      log.append(el("div", { class: "ask-msg ask-msg-q", text: label }), answer);
      log.scrollTop = log.scrollHeight;
      input.value = "";
      try {
        const r = await postJson("/api/course/ask", { question, quick: key, context: askContext });
        answer.replaceChildren(...renderAnswer(r));
      } catch (err) {
        answer.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
      }
      log.scrollTop = log.scrollHeight;
    }
    function renderAnswer(r) {
      const parts = [el("p", { class: "ask-a", text: r.answer })];
      if (r.unsure) parts.push(el("p", { class: "ask-unsure", text: "Not certain. Double-check this one." }));
      if (r.breakdown.length) {
        parts.push(el("table", { class: "ask-breakdown" }, el("tbody", {}, r.breakdown.map((b) =>
          el("tr", {}, el("td", { lang: "ja", text: b.jp }), el("td", { text: b.en }))))));
      }
      for (const ex of r.examples) {
        parts.push(el("div", { class: "ask-example" },
          el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(ex.jp) }, "▶"),
          el("span", { lang: "ja", text: ex.jp }),
          el("span", { class: "ask-example-en", text: ex.en }),
          ex.en && ex.jp.length <= 40 && !/[一-鿿]/.test(ex.jp) ? keepButton(ex.jp, ex.en) : null));
      }
      if (r.more) parts.push(el("details", { class: "ask-more" }, el("summary", {}, "More"), el("p", { text: r.more })));
      return parts;
    }
    return { open, close, refresh, toggle: () => (panel.hidden ? open() : close()), isOpen: () => !panel.hidden };
  })();

  // ---------- frame ----------
  /** One screen of a lesson: top bar, optional sequence bar, content, action footer. */
  let screenId = 0;
  /** True while the screen that was showing when this was called is still up. */
  function onThisScreen() {
    const id = screenId;
    return () => id === screenId;
  }
  function frame({ title, index, total, body, actions = [], primary = null, hold = null, ask = null }) {
    stopAudio();
    screenId += 1;
    askContext = { title, ...(ask || {}) };
    keys.primary = primary;
    keys.hold = hold ? hold.holdApi : null;
    keys.replay = null;
    keys.meanings = null;
    keys.text = pendingText;
    pendingText = null;
    keys.tab = null;
    keys.grade = null;
    keys.space = null;
    keys.undo = null;
    keys.hint = null;
    keys.back = null;
    keys.choice = pendingChoice;
    pendingChoice = null;
    const top = el("div", { class: "lesson-top" },
      el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Exit"),
      el("h2", { class: "lesson-title", text: title }),
      total ? el("span", { class: "lesson-count", text: `${index + 1} of ${total}` }) : null,
    );
    const steps = total
      ? el("div", { class: "lesson-steps", "aria-hidden": "true" },
          Array.from({ length: total }, (_, i) => el("span", { class: i < index ? "done" : i === index ? "now" : "" })))
      : null;
    const note = el("p", { class: "lesson-audio-note", hidden: !audioProblem });
    fillAudioNote(note);
    const lessonNode = el("div", { class: "lesson", tabindex: "-1" },
      top,
      steps,
      note,
      el("div", { class: "lesson-body" }, body),
      actions.length ? el("div", { class: "lesson-actions" }, actions) : null,
    );
    root.replaceChildren(lessonNode);
    // A new screen is new content for a screen reader, and keys shouldn't stay on a removed button.
    lessonNode.focus({ preventScroll: true });
    root.scrollTop = 0;
    askPanel.refresh();
  }
  function primaryButton(label, onclick, { disabled = false } = {}) {
    return el("button", { type: "button", class: "lesson-primary", disabled, onclick }, label, kbd("Enter"));
  }

  // ---------- home ----------
  const STEP_NAMES = { learn: "New phrases", words: "Words", grammar: "Grammar", listen: "Listen", speak: "Speak", mined: "New lines", kaishi: "New words" };
  /** Today's steps, decided by the server's pacing (state.plan_today). */
  function planSteps() {
    return [...(today.plan || [])];
  }
  // The first time through each kind of step: what it's for. Effortful practice feels less
  // productive than it is (Bjork), so knowing why it's hard is part of sticking with it.
  const STEP_WHY = {
    review: ["Review", "Getting something out of memory is what strengthens it. If it feels a bit hard, it's working: a miss just brings the card back sooner."],
    learn: ["New phrases", "Hear each one and say it out loud. Saying it matters even when you feel silly: your mouth has to learn it too."],
    words: ["Words", "A few at a time, tested right away. Don't try to memorise before the test. The test is the studying."],
    grammar: ["Grammar", "Just enough to see the pattern, then you use it. You'll put real sentences together yourself, and they come back later."],
    listen: ["Listen", "Listen first, no text. You won't catch everything, and you don't need to. Getting the gist from sound alone is the skill."],
    speak: ["Speak", "Answer in your own words if you can. Getting it out imperfectly teaches more than getting it perfect silently."],
    kaishi: ["New words", "Words from Kaishi, each in a recorded sentence. Hear it and pick what it means; the word, its reading and its own audio are on the back. Each comes back until you catch it by ear."],
    mined: ["New lines", "Lines you mined from what you watch, in the real voice. Pick what it means; missing it the first time is normal, and the text is one click away. Each one comes back until you catch it by ear."],
    kana: ["Kana", "Each one comes with a picture, in case it helps you hold the shape at first. What really makes them stick is the practice that follows. You'll drop the pictures once reading is automatic."],
  };
  function withWhy(step, go) {
    const why = STEP_WHY[step];
    const key = `kaiwa_why_${step}`;
    if (!why || readPref(key, "") === "1") return go();
    writePref(key, "1");
    frame({
      title: why[0],
      body: el("div", { class: "card-body" }, el("p", { class: "lesson-note why-note", text: why[1] })),
      actions: [primaryButton("Got it", go)],
      primary: go,
    });
    return undefined;
  }
  function runStep(step) {
    return withWhy(step, () => startStep(step));
  }
  function startStep(step) {
    track("open", { activity: step, unit: today.unit ? today.unit.id : null });
    if (step === "review") return runReview(today.review);
    if (step === "recap") return runReview(today.recap || [], { title: "Recap", planStep: "recap" });
    if (step === "mined") return runReview(today.mined_new || [], { title: "New lines", planStep: "mined" });
    if (step === "kaishi") return runReview(today.kaishi_new || [], { title: "New words", planStep: "kaishi" });
    if (step === "kana") return runKana(today.kana);
    return runUnitStep(today.unit, step, today.unit_steps || {});
  }
  function runUnitStep(unit, step, row) {
    if (step === "learn") return runLearn(unit);
    if (step === "words") return runWords(unit, row);
    if (step === "grammar") return runGrammar(unit);
    if (step === "listen") return runListen(unit);
    return runSpeak(unit);
  }
  // A lesson opened from the course map goes back there, not on through today's plan.
  let afterLesson = null;
  /** After a step: refresh progress, then go straight to the next planned step. */
  async function continuePlan() {
    if (afterLesson) {
      const back = afterLesson;
      afterLesson = null;
      return back();
    }
    if (!(await refreshOrRetry(continuePlan))) return undefined;
    const next = planSteps()[0];
    return next ? runStep(next) : showDayDone();
  }
  function runNext() {
    const next = planSteps()[0];
    return next ? runStep(next) : showDayDone();
  }
  let UNIT_TITLES = [];
  async function refresh() {
    today = await api("/api/course/today");
    if (today.unit_titles) UNIT_TITLES = today.unit_titles;
    if (recapSettled()) today.plan = (today.plan || []).filter((s) => s !== "recap");
  }
  const dayKey = () => String(((today.stats || {}).week || []).find((w) => w.today)?.d);
  /** A recap is over for the day even if a missed card or two is left. New cards bring it back. */
  function recapSettled() {
    try {
      const d = JSON.parse(readPref("kaiwa_recap_settled", "{}"));
      return d.day === dayKey() && (today.recap || []).length <= d.left;
    } catch (_) { return false; }
  }
  /** Going on to the next step: a lost connection says so and offers to try again, never a dead screen. */
  async function refreshOrRetry(again) {
    try {
      await refresh();
      return true;
    } catch (err) {
      frame({
        title: "Couldn't reach Kaiwa",
        body: el("div", { class: "card-body" },
          el("p", { class: "verdict off", text: "What you just did is saved. Check that Kaiwa can reach your PC, then try again." }),
          el("p", { class: "status", text: String(err.message || err) })),
        actions: [primaryButton("Try again", again)],
        primary: again,
      });
      return false;
    }
  }

  async function showHome() {
    stopAudio();
    afterLesson = null;
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    clearKeys();
    try {
      await refresh();
    } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    const s = today.stats;
    const unit = today.unit;
    if (unit && (today.unit_steps || {}).reopened) {
      const c = (today.placement_checks || []).find((x) => x.id === unit.id);
      unit.reopenedNote = `Second pass: ${c ? `${c.miss} of ${c.ok + c.miss}` : "several"} reviews from this unit were missed after it was marked known, so its grammar and listening are back.`;
    }
    const done = today.unit_steps || {};
    const steps = planSteps();
    const pct = Math.round((100 * s.phrases_learned) / Math.max(1, s.phrases_total));

    // The next step is started by the main button, so its row gets no button of its own.
    const open = (key, fn) => (key === steps[0] ? null : fn);
    const rows = [];
    if (today.review.length) {
      // Only today's share is shown: the rest waits for later days, never piles up here.
      const secs = today.review.reduce((n, c) => n + ({ kana: 4, word: 4, listen: 8, speak: 12, mined: 12, line: 12 }[c.kind === "phrase" ? c.skill : c.kind] || 8), 0);
      const n = today.review.length;
      rows.push(planRow("Review", `${n} card${n === 1 ? "" : "s"}, about ${Math.max(1, Math.round(secs / 60))} min`, false, open("review", () => runReview(today.review))));
    } else if (s.phrases_learned) {
      rows.push(planRow("Review", "Nothing left today", false, null));
    }
    if ((today.mined_new || []).length) {
      const n = today.mined_new.length;
      rows.push(planRow("New lines", `${n} from your shows`, false, open("mined", () => runStep("mined"))));
    } else if (today.mined_paused) {
      rows.push(planRow("New lines", "None today: your mined reviews come first", false, null));
    }
    if ((today.kaishi_new || []).length) {
      const n = today.kaishi_new.length;
      rows.push(planRow("New words", `${n} from Kaishi`, false, open("kaishi", () => runStep("kaishi"))));
    }
    if ((today.recap || []).length) {
      const n = today.recap.length;
      rows.push(planRow("Recap", steps.includes("recap") ? `${n} new card${n === 1 ? "" : "s"}, a second look` : `${n} card${n === 1 ? "" : "s"} still settling, if you want another go`, false,
        steps.includes("recap") ? open("recap", () => runStep("recap")) : () => runStep("recap")));
    }
    const kp = today.kana_progress;
    if (today.kana) {
      const k = today.kana;
      const detail = `${k.title}: ${k.kana.map((x) => x.char).join(" ") || "reading practice"}`;
      const planned = steps.includes("kana");
      // Not planned today (done, or alternating with a unit): still one click away.
      rows.push(planRow("Kana", today.kana_done_today ? "Done for today" : planned ? detail : `${detail} (tomorrow)`,
        today.kana_done_today,
        planned ? open("kana", () => runKana(k)) : () => runKana(k),
        planned ? null : today.kana_done_today ? "Next lesson" : "Open"));
    }
    if (unit) {
      const details = {
        learn: `${unit.phrases.length} phrases to learn`,
        words: done.words || !today.words_today || today.words_today >= unit.words.length - (done.words_seen || 0)
          ? `${done.words || !done.words_seen ? unit.words.length : unit.words.length - done.words_seen} words`
          : `Next ${today.words_today} of ${unit.words.length - (done.words_seen || 0)} words`,
        grammar: `${unit.grammar.length} grammar point${unit.grammar.length === 1 ? "" : "s"}, ${unit.drill.length} questions`,
        listen: "A short conversation",
        speak: `Answer ${unit.speak.length} questions out loud`,
      };
      for (const step of unit.steps) {
        const ready = step === "learn" || done.learn;
        const later = !done[step] && !steps.includes(step);
        rows.push(planRow(STEP_NAMES[step], later ? `${details[step]} (tomorrow)` : details[step], !!done[step],
          ready ? (later ? () => runStep(step) : open(step, () => runStep(step))) : null, later && ready ? "Open" : null));
      }
    }

    if (placementAfterHome) {
      placementAfterHome = false;
      return runPlacement();
    }
    const fresh = !s.phrases_learned && !(kp && kp.lessons_done);
    if (steps.length) keys.primary = runNext;
    root.replaceChildren(
      el("div", { class: "home" },
        today.away >= 3 ? el("p", { class: "home-note home-welcome", text: `Welcome back. It's been ${today.away} days, and that's fine: you keep more than it feels like. Today is a normal-sized day, not a pile.` }) : null,
        newMilestones().map((m) => el("p", { class: "milestone", text: m.text })),
        unit
          ? el("div", { class: "home-unit" },
              el("p", { class: "home-kicker", text: `Unit ${unit.number} of ${s.units_total}` }),
              unit.title_jp ? el("p", { class: "home-title-jp", lang: "ja", text: unit.title_jp }) : null,
              el("h1", { class: "home-title", text: unit.title }),
              el("p", { class: "home-goal", text: unit.goal }))
          : el("div", { class: "home-unit" },
              el("h1", { class: "home-title", text: `You've finished all ${s.units_total} units` }),
              el("p", { class: "home-goal", text: "That's real: you can greet, order, shop, plan a day and hold a short conversation in Japanese. What keeps it now is using it. Reviews continue daily, and Chat, missions and the word packs are all yours." }),
              courseNextSteps()),
        unit && unit.reopenedNote ? el("p", { class: "home-note", text: unit.reopenedNote }) : null,
        unit && ["u8", "u11"].includes(unit.id) && !(today.words_pool || []).some((w) => w.jp === "きゅう")
          ? el("p", { class: "home-note" }, "This unit leans on numbers. If they're shaky, there's a 3-minute Numbers pack in the ",
              el("button", { type: "button", class: "link-button", onclick: runMap }, "course map"), ".")
          : null,
        fresh ? el("p", { class: "home-note", text: "Each day: a little new, a little review, and everything out loud. Mistakes are part of how it works; they're what tells Kaiwa what to bring back." }) : null,
        fresh ? el("div", { class: "home-first" },
          el("p", { class: "can-do-label", text: "How much time do you want to give this? You can change it any time." }),
          paceRow(),
          el("p", { class: "can-do-label", text: "And when? People who pick a time are more likely to keep it up." }),
          reminderRow()) : null,
        weekRow(s),
        pct > 0
          ? el("div", { class: "home-bar", role: "progressbar", "aria-label": "Phrases learned", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
              el("span", { style: `width:${pct}%` }))
          : null,
        steps.length
          ? el("div", { class: "home-actions" },
              el("button", { type: "button", class: "lesson-primary", onclick: runNext },
                `${s.studied_today ? "Continue" : "Start today's lesson"} · about ${today.minutes} min`, kbd("Enter")))
          : el("p", { class: "home-done", text: doneLine() }),
        steps.length && !s.studied_today && today.review.length >= 4
          ? el("button", { type: "button", class: "home-tiny", onclick: () => runReview(today.review.slice(0, TINY_CARDS), { title: "Just two minutes", planStep: "tiny" }),
              "data-tip": "A few reviews. It keeps the habit going and the streak alive on a busy day." }, "Busy day? Just two minutes")
          : null,
        today.catching_up
          ? el("p", { class: "home-note", text: "Reviews only today: there's a backlog to clear first. New lessons are still one click away below." })
          : null,
        today.slipping != null
          ? el("p", { class: "home-note", text: `You've been remembering ${today.slipping}% lately, so new material is slowed down until that recovers. This usually only takes a few days.` })
          : null,
        rows.length ? el("ol", { class: "plan" }, rows) : null,
        fresh
          ? el("div", { class: "home-placement" },
              el("p", { text: "Already know some Japanese? A short test finds where to start." }),
              el("button", { type: "button", class: "secondary", onclick: runPlacement }, "Take the placement test (about 8 min)"))
          : null,
        placementLine(today.placement_checks || []),
        today.retention ? retentionLine(today.retention) : null,
        !fresh
          ? el("div", { class: "home-more" },
              el("h2", { class: "home-more-title", text: "More practice" }),
              practiceRow(
                s.listening && s.listening.today ? `Extra listening (${Math.round(s.listening.today)} min today)` : "Extra listening",
                () => runExtraListening(),
                `Short conversations and stories from what you've learned, to understand by ear.${s.listening && s.listening.total ? ` ${s.listening.total} min so far.` : ""}`),
              practiceRow(
                s.talk_today ? `Talk practice (${s.talk_today} today)` : "Talk practice",
                runTalk,
                "A short scene with a goal and a hint when you're stuck. The best place to start speaking."),
              practiceRow("Chat", goChat,
                "Talk about anything, for as long as you like. Easy keeps it to what you've learned."),
              drillRows())
          : null,
        el("div", { class: "home-links" },
          el("button", { type: "button", class: "secondary", onclick: runMap, "data-tip": "All 20 units, what each lets you do, and how far you are" }, "Course map"),
          !fresh ? el("button", { type: "button", class: "secondary", onclick: runBook, "data-tip": "Everything you've learned, to look up and hear again" }, "Phrasebook") : null,
          el("button", { type: "button", class: "secondary", onclick: runDecks,
            "data-tip": "Lines you mined from shows, and decks you brought in from Anki" }, "Your decks"),
          !fresh ? el("button", { type: "button", class: "secondary", onclick: runStats,
            "data-tip": "Retention, what's coming up, your cards, and how scheduling works" }, "Stats") : null),
        el("details", { class: "home-options", open: optionsOpen, ontoggle: (e) => { optionsOpen = e.target.open; } },
          el("summary", {}, "Options"),
          fresh ? null : paceRow(),
          fresh ? null : limitsPanel(),
          el("label", { class: "home-romaji" },
            el("input", { type: "checkbox", checked: showRomaji, onchange: (e) => { showRomaji = e.target.checked; writePref("kaiwa_course_romaji", showRomaji ? "1" : "0"); } }),
            " Show romaji for kana you haven't learned"),
          fresh ? null : reminderRow(),
          unit && !unit.reopenedNote && !Object.values(today.unit_steps || {}).some((v) => v === true)
            ? skipUnitButton(unit)
            : null),
      ),
    );
    markMilestonesSeen();
  }
  /** Short fluency drills, tucked away so the main choices stay few. */
  function drillRows() {
    const rows = [
      (today.words_pool || []).length + (today.phrases_pool || []).length >= SPEED_MIN
        ? practiceRow(today.bests && today.bests.speed ? `Speed round (best ${today.bests.speed})` : "Speed round", runSpeed,
            "One minute, known words only: hear it, tap the meaning. Builds the speed real conversation needs.") : null,
      today.drills && (today.drills.time || today.drills.price)
        ? practiceRow("Numbers by ear", runNumbers, "Prices and times, at full speed. The thing everyone loses in real life.") : null,
      (today.phrases_pool || []).length >= 6
        ? practiceRow("Hands-free", runHandsFree, "Walking or doing dishes? It says the English, you say the Japanese out loud, it says it back.") : null,
    ].filter(Boolean);
    return rows.length ? el("details", { class: "home-drills" }, el("summary", {}, "Quick drills"), rows) : null;
  }
  const TINY_CARDS = 8;
  function doneLine() {
    const d = today.day || {};
    return d.answers ? `Done for today: ${d.answers} answer${d.answers === 1 ? "" : "s"}${d.new ? `, ${d.new} new` : ""}. More tomorrow.` : "Done for today. More tomorrow.";
  }
  /** This week as dots, and the streak: a week's study earns a day off that doesn't break it. */
  function weekRow(s) {
    if (!s.streak && !(s.week || []).some((d) => d.on)) return null;
    const rest = s.rests ? `, ${s.rests} rest day${s.rests === 1 ? "" : "s"} saved` : "";
    return el("div", { class: "week-row", "data-tip": "Every 7 days in a row earns a rest day: miss one day and the streak holds." },
      el("span", { class: "week-dots", "aria-hidden": "true" }, s.week.map((d) => el("span", {
        class: "week-dot" + (d.on ? " on" : "") + (d.today ? " today" : "") + (d.future ? " future" : ""), text: d.label }))),
      el("span", { class: "week-text", text: s.streak ? `${s.streak} day${s.streak === 1 ? "" : "s"} in a row${rest}` : "Studied this week" }));
  }
  /** Abilities reached since the last look. The first ever look only records what's already there. */
  function newMilestones() {
    const list = today.milestones || [];
    const raw = readPref("kaiwa_seen_milestones", "");
    if (!raw) return [];
    const seen = new Set(raw.split(","));
    return list.filter((m) => !seen.has(m.id));
  }
  function markMilestonesSeen() {
    const list = today.milestones || [];
    // Kept even if one lapses: reaching the same line twice isn't news.
    const seen = readPref("kaiwa_seen_milestones", "").split(",").filter((x) => x && x !== "-");
    writePref("kaiwa_seen_milestones", ["-", ...new Set([...seen, ...list.map((m) => m.id)])].join(","));
  }

  /**
   * Free recall: before leaving, say everything you remember from today's phrases, no
   * prompts. It's about the most effective cheap thing a learner can do (Karpicke &
   * Blunt 2011), and nothing else in the day asks you to pull them out unprompted.
   */
  function recallBox() {
    const list = today.phrases_today || [];
    const dayKey = String((today.stats.week || []).find((w) => w.today)?.d);
    if (list.length < 3 || readPref("kaiwa_recall_day", "") === dayKey) return null;
    const result = el("div", { class: "result", "aria-live": "polite" });
    const show = (r) => {
      writePref("kaiwa_recall_day", dayKey);
      const total = r.recalled.length + r.missed.length;
      result.replaceChildren(
        el("p", { class: "verdict " + (r.recalled.length >= total / 2 ? "good" : "close"), text: `${r.recalled.length} of ${total} from memory.` }),
        r.missed.length ? el("div", { class: "recall-missed" },
          el("p", { class: "status", text: "These got away. They'll be back:" }),
          r.missed.map((p) => el("p", { class: "ask-example" },
            el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(p.jp) }, "▶"),
            el("span", { lang: "ja", text: p.jp }), el("span", { class: "ask-example-en", text: p.en })))) : "");
      box.hidden = true;
      keys.hold = null;
    };
    const send = async (form) => {
      result.replaceChildren(el("p", { class: "pending", text: "Listening back…" }));
      try { show(await api("/api/course/recall", { method: "POST", body: form })); }
      catch (err) { result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) })); }
    };
    const box = produceBox({
      placeholder: "Or type what you remember",
      onTyped: ({ kana }) => { const f = new FormData(); f.append("text", kana); send(f); box.reopen(); },
      onAudio: (blob, ext) => send(audioForm(blob, ext, {})),
      onProblem: showProblem(result),
    });
    return el("div", { class: "recall" },
      el("p", { class: "can-do-label", text: `One last thing: today you met ${list.length} new phrases.` }),
      el("p", { class: "lesson-note", text: "Without looking, say every one you can remember. It's fine if it's only one or two: trying is what does it." }),
      box, result);
  }

  /** The end of the day's plan: what you did, what you can now do, and an easy next thing. */
  async function showDayDone() {
    try { await refresh(); } catch (_) { return showHome(); }
    const d = today.day || {};
    const figures = [
      d.answers ? figure(String(d.answers), "answers") : null,
      d.new ? figure(String(d.new), "new things learned") : null,
      d.minutes >= 1 ? figure(String(Math.round(d.minutes)), "minutes") : null,
      today.stats.streak > 1 ? figure(String(today.stats.streak), "days in a row") : null,
    ].filter(Boolean);
    frame({
      title: "That's today",
      body: el("div", { class: "card-body day-done" },
        newMilestones().map((m) => el("p", { class: "milestone", text: m.text })),
        (d.units_finished || []).map((u) => el("div", { class: "can-do" },
          el("p", { class: "can-do-label", text: `Unit ${u.number} done. You can now:` }), el("p", { class: "can-do-text", text: u.goal }))),
        figures.length ? el("div", { class: "stats-figures" }, figures) : null,
        recallBox(),
        el("p", { class: "prompt", text: d.due_tomorrow
          ? `Tomorrow: ${d.due_tomorrow} review${d.due_tomorrow === 1 ? "" : "s"} waiting, then the next lesson. Sleep is part of this: what you did today sets overnight.`
          : "Sleep is part of this: what you did today sets overnight." }),
        el("p", { class: "lesson-note", text: "Got two more minutes? Using what you just learned in a real exchange is the fastest way to keep it." })),
      actions: [
        el("button", { type: "button", class: "secondary", onclick: goChat }, "Say something in Chat"),
        primaryButton("Done", showHome)],
      primary: showHome,
    });
    const holdBtn = root.querySelector(".recall .hold");
    if (holdBtn) keys.hold = holdBtn.holdApi;
    markMilestonesSeen();
    askContext = null;
    askPanel.refresh();
  }

  /**
   * "When will you do it?": people who name a time and place follow through far more
   * (implementation intentions, Gollwitzer 1999). A calendar file works on every device
   * Kaiwa runs on and needs no notification service.
   */
  function reminderRow() {
    const time = el("input", { type: "time", value: readPref("kaiwa_reminder_time", "19:00"), "aria-label": "Study time" });
    const link = el("a", { class: "secondary reminder-link", role: "button" }, "Add to my calendar");
    const update = () => {
      writePref("kaiwa_reminder_time", time.value);
      link.setAttribute("href", `/api/course/reminder.ics?time=${encodeURIComponent(time.value)}`);
    };
    time.addEventListener("change", update);
    update();
    return el("div", { class: "reminder-row" },
      el("span", { class: "pace-label", text: "Study at" }), time, link);
  }
  /** How much a day holds. Takes effect straight away, on today's plan too. */
  function paceRow() {
    return el("div", { class: "pace-row", role: "group", "aria-label": "Daily pace" },
      el("span", { class: "pace-label", text: "Daily pace" }),
      el("div", { class: "pace-options" },
        Object.entries(today.paces || {}).map(([key, p]) => el("button", {
          type: "button", class: "pace-option" + (key === today.pace ? " on" : ""), "aria-pressed": String(key === today.pace),
          onclick: async () => {
            if (key === today.pace) return;
            await postJson("/api/course/pace", { pace: key }).catch(() => {});
            showHome();
          },
        }, p.label, el("span", { class: "pace-minutes", text: `~${p.minutes} min a day · ~${p.months} months` })))));
  }
  /**
   * Anki-style daily limits, per deck and overall. A blank box follows the pace, so the
   * pace chips stay the easy way in; a number here is the learner's own and wins.
   */
  const LIMIT_LABELS = {
    new_per_day: ["New per day", "New words, phrases and kana a day"],
    max_reviews: ["Max reviews per day", "Cards a day. Blank: the pace decides, by time"],
    lesson_minutes: ["Lesson minutes", "Time for new lessons a day, after reviews"],
    retention: ["Desired retention %", "How much you want to remember. Higher means more reviews"],
  };
  const LIMIT_TIPS = {
    mined: { new_per_day: "New lines from your shows a day", max_reviews: "Mined cards a day, at most. The rest wait, never pile up" },
  };
  function limitsPanel() {
    const lim = today.limits;
    if (!lim) return null;
    const status = el("p", { class: "limits-status", role: "status" });
    const save = async (deck, field, input) => {
      const raw = input.value.trim();
      let value = raw === "" ? null : Number(raw);
      if (value != null && !Number.isFinite(value)) return;
      if (field === "retention" && value != null) value = value / 100;
      try {
        await api("/api/course/limits", { method: "PUT", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ deck, values: { [field]: value } }) });
        showHome();
      } catch (err) {
        status.textContent = err.message;
      }
    };
    const field = (deck, name, f) => {
      const [label, baseTip] = LIMIT_LABELS[name];
      const tip = (LIMIT_TIPS[deck] || {})[name] || baseTip;
      const pct = name === "retention";
      const shown = (v) => (v == null ? "" : pct ? String(Math.round(v * 100)) : String(v));
      const input = el("input", {
        type: "number", inputmode: "numeric", class: "limit-input" + (f.set ? " set" : ""),
        min: pct ? "70" : "0", max: pct ? "97" : "9999", step: "1",
        value: f.set ? shown(f.value) : "",
        placeholder: f.default != null ? shown(f.default) : deck === "all" ? "no limit" : "pace",
        "aria-label": `${label}${deck === "all" ? " (all decks)" : ""}`,
        onchange: (e) => save(deck, name, e.target),
      });
      return el("label", { class: "limit-field", "data-tip": tip }, el("span", { class: "limit-name", text: label }), input);
    };
    const decks = Object.entries(lim.decks).map(([deck, d]) => el("fieldset", { class: "limit-deck" },
      el("legend", { text: d.label }),
      Object.entries(d.fields).map(([name, f]) => field(deck, name, f))));
    const overall = el("fieldset", { class: "limit-deck" },
      el("legend", { text: "All decks" }),
      Object.entries(lim.all).map(([name, f]) => field("all", name, f)));
    const reset = lim.custom
      ? el("button", { type: "button", class: "link-button", onclick: async () => {
          const clear = (fields) => Object.fromEntries(Object.keys(fields).map((k) => [k, null]));
          for (const [deck, d] of Object.entries(lim.decks)) {
            await api("/api/course/limits", { method: "PUT", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ deck, values: clear(d.fields) }) }).catch(() => {});
          }
          await api("/api/course/limits", { method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ deck: "all", values: clear(lim.all) }) }).catch(() => {});
          showHome();
        } }, "Back to the pace's numbers")
      : null;
    return el("div", { class: "limits", role: "group", "aria-label": "Daily limits" },
      el("span", { class: "pace-label", text: "Daily limits" }),
      el("p", { class: "limits-note", text: lim.custom
        ? "Using your own limits. The pace's minutes and months are estimates for its own numbers, so they no longer apply."
        : "Blank boxes follow the pace. Type a number to set your own." }),
      decks, overall, reset, status);
  }
  /** One extra-practice mode on the home screen: its button and what it's for. */
  function practiceRow(label, onclick, what) {
    return el("div", { class: "practice-row" },
      el("button", { type: "button", class: "secondary", onclick }, label),
      el("p", { class: "practice-what", text: what }));
  }
  /** "You remember 88% of reviews" with a per-kind breakdown in the tooltip. */
  /** How the checks on placed (or skipped) units are going, while any are still to come. */
  function placementLine(checks) {
    const pending = checks.reduce((n, c) => n + c.pending, 0);
    if (!pending) return null;
    const done = checks.reduce((n, c) => n + c.ok + c.miss, 0);
    const missed = checks.reduce((n, c) => n + c.miss, 0);
    return el("p", { class: "home-note",
      "data-tip": "Units you skipped or tested out of aren't taken on trust. Their first reviews check them, and a unit with too many misses gets its lessons back." },
      `Checking your placement: ${done} of ${done + pending} reviews done${done ? `, ${missed} missed` : ""}.`);
  }

  /** "I already know this unit": two clicks, and the unit's reviews check the claim. */
  function skipUnitButton(unit) {
    let armed = false;
    const btn = el("button", { type: "button", class: "secondary",
      "data-tip": "Marks it known without the lessons. Its words and phrases come up as reviews; if you miss too many, the lessons come back." },
      "Already know this unit? Skip it");
    btn.onclick = async () => {
      if (!armed) {
        armed = true;
        btn.textContent = `Skip unit ${unit.number}: click again to confirm`;
        return;
      }
      btn.disabled = true;
      try {
        await postJson("/api/course/skip_unit", { unit_id: unit.id });
      } catch (err) {
        btn.disabled = false;
        btn.textContent = String(err.message || err);
        return;
      }
      showHome();
    };
    return el("div", { class: "home-placement" }, btn);
  }

  function retentionLine(r) {
    const parts = Object.entries(r.by_kind).map(([k, v]) => `${k} ${v}%`).join(", ");
    const tip = `Out of ${r.reviews} reviews in the last ${r.days} days. Kaiwa aims for ${r.target}%: `
      + `higher means reviews could be spread further, lower means more help is due.`
      + (parts ? ` By kind: ${parts}.` : "")
      + (r.leeches ? ` ${r.leeches} card${r.leeches === 1 ? " is" : "s are"} getting extra help.` : "");
    return el("p", { class: "home-retention", "data-tip": tip },
      el("strong", { text: `${r.percent}%` }), ` remembered in reviews (last ${r.days} days)`);
  }
  // After the last unit: what this course covered and didn't, and where each gap is filled.
  function courseNextSteps() {
    const steps = [
      ["Kanji",
        "Everything here was in kana; real Japanese is written with kanji. Start with the words you already know (日本, 学校, 先生, 雨) in a kanji flashcard app, a few a day."],
      ["More grammar",
        "You've covered about the first five lessons of a beginner textbook, plus a few later forms. Genki I from lesson 6, or Minna no Nihongo I from lesson 14, picks up where this leaves off with the て-form rules and plain speech."],
      ["Lots of easy listening",
        "Hours of Japanese you mostly understand: beginner \"comprehensible input\" videos and podcasts, a little every day."],
      ["Easy reading",
        "Free graded readers for beginners (search \"Tadoku level 0\") are short stories in kana."],
      ["A native ear",
        "Kaiwa can't hear pitch, so a few sessions with a native speaker or tutor will catch what it misses."],
    ];
    return el("div", { class: "home-next" },
      el("p", { class: "can-do-label", text: "Where to go next" }),
      steps.map(([title, text]) => el("div", { class: "can-do" },
        el("p", { class: "can-do-text", text: title }),
        el("p", { class: "can-do-label", text }))));
  }
  function planRow(name, detail, isDone, onOpen, openLabel) {
    return el("li", { class: "plan-row" + (isDone ? " done" : "") },
      el("span", { class: "plan-name", text: name }),
      el("span", { class: "plan-detail", text: isDone && !openLabel ? "Done" : detail }),
      onOpen
        ? el("button", { class: "secondary", type: "button", onclick: onOpen }, openLabel || (isDone ? "Redo" : "Open"))
        : el("span"),
    );
  }
  async function undoFromHome() {
    try {
      const r = await postJson("/api/course/undo", {});
      await showHome();
      const what = r.card.word ? r.card.word.jp : r.card.phrase ? r.card.phrase.jp : r.card.kana ? r.card.kana.char : r.card.grammar ? r.card.grammar.title : "";
      root.querySelector(".home")?.prepend(el("p", { class: "undo-toast", text: `Undid your last answer${what ? ` (${what})` : ""}. It's due again.` }));
    } catch (err) {
      root.querySelector(".home")?.prepend(el("p", { class: "undo-toast", text: String(err.message || err) }));
    }
  }
  function goChat() {
    const tab = document.querySelector('.tab[data-mode="chat"]');
    if (tab) tab.click();
  }

  // ---------- answering in Japanese ----------
  // Romaji typed in the answer box becomes kana as you type (no Japanese keyboard needed).
  const ROMAJI_KANA = (() => {
    const base = {
      a: "あ", i: "い", u: "う", e: "え", o: "お",
      ka: "か", ki: "き", ku: "く", ke: "け", ko: "こ", ga: "が", gi: "ぎ", gu: "ぐ", ge: "げ", go: "ご",
      sa: "さ", shi: "し", si: "し", su: "す", se: "せ", so: "そ", za: "ざ", ji: "じ", zi: "じ", zu: "ず", ze: "ぜ", zo: "ぞ",
      ta: "た", chi: "ち", ti: "ち", tsu: "つ", tu: "つ", te: "て", to: "と", da: "だ", di: "ぢ", du: "づ", de: "で", do: "ど",
      na: "な", ni: "に", nu: "ぬ", ne: "ね", no: "の",
      ha: "は", hi: "ひ", fu: "ふ", hu: "ふ", he: "へ", ho: "ほ", ba: "ば", bi: "び", bu: "ぶ", be: "べ", bo: "ぼ",
      pa: "ぱ", pi: "ぴ", pu: "ぷ", pe: "ぺ", po: "ぽ",
      ma: "ま", mi: "み", mu: "む", me: "め", mo: "も", ya: "や", yu: "ゆ", yo: "よ",
      ra: "ら", ri: "り", ru: "る", re: "れ", ro: "ろ", wa: "わ", wo: "を", nn: "ん", "n'": "ん",
      sha: "しゃ", shu: "しゅ", sho: "しょ", sya: "しゃ", syu: "しゅ", syo: "しょ",
      cha: "ちゃ", chu: "ちゅ", cho: "ちょ", tya: "ちゃ", tyu: "ちゅ", tyo: "ちょ",
      ja: "じゃ", ju: "じゅ", jo: "じょ", zya: "じゃ", zyu: "じゅ", zyo: "じょ",
      "-": "ー",
    };
    for (const [c, k] of Object.entries({ k: "き", g: "ぎ", n: "に", h: "ひ", b: "び", p: "ぴ", m: "み", r: "り" })) {
      base[c + "ya"] = k + "ゃ";
      base[c + "yu"] = k + "ゅ";
      base[c + "yo"] = k + "ょ";
    }
    return base;
  })();
  function toKana(text, { final = false } = {}) {
    const s = String(text || "").toLowerCase();
    let out = "";
    let i = 0;
    while (i < s.length) {
      const ch = s[i];
      if (!/[a-z'\-]/.test(ch)) { out += ch; i += 1; continue; }
      // nn: ん, and if a vowel follows, the second n starts the next kana (konnichiha → こんにちは).
      if (ch === "n" && s[i + 1] === "n") {
        out += "ん";
        i += /[aiueoy]/.test(s[i + 2] || "") ? 1 : 2;
        continue;
      }
      // Doubled consonant → small っ (kk, tt, ss, pp… not nn).
      if (ch !== "n" && /[bcdfghjklmpqrstvwxyz]/.test(ch) && s[i + 1] === ch) { out += "っ"; i += 1; continue; }
      let hit = "";
      for (const len of [3, 2, 1]) {
        const piece = s.slice(i, i + len);
        if (ROMAJI_KANA[piece]) { hit = piece; break; }
      }
      if (hit === "n" || (!hit && ch === "n")) {
        // A lone n is ん before a consonant or at the end; before a vowel/y it's waiting.
        const after = s[i + 1];
        if (after && !/[aiueoy']/.test(after)) { out += "ん"; i += 1; continue; }
        if (!after && final) { out += "ん"; i += 1; continue; }
      }
      if (hit) { out += ROMAJI_KANA[hit]; i += hit.length; continue; }
      out += ch;
      i += 1;
    }
    return out;
  }
  const VOWEL_OF = {};
  for (const [ro, kana] of Object.entries(ROMAJI_KANA)) {
    const v = ro.slice(-1);
    if ("aiueo".includes(v)) VOWEL_OF[kana.slice(-1)] = { a: "あ", i: "い", u: "う", e: "え", o: "お" }[v];
  }
  /** Compare-form: hiragana, no punctuation, ー spelled as the vowel it lengthens. */
  function kanaKey(text) {
    let s = "";
    for (const ch of String(text || "")) {
      const code = ch.charCodeAt(0);
      s += code >= 0x30a1 && code <= 0x30f6 ? String.fromCharCode(code - 0x60) : ch;
    }
    s = s.replace(/[\s、。！？!?.,・「」]/g, "");
    let out = "";
    for (const ch of s) out += ch === "ー" ? (VOWEL_OF[out.slice(-1)] || "") : ch;
    return out;
  }

  /**
   * Say-or-type answer box. Typing shows kana as you go; Enter submits.
   * `onAnswer({ text, kana })` for typed answers; spoken audio goes to `onAudio`.
   */
  function produceBox({ placeholder, onTyped, onAudio, onProblem, romajiOnly = false, typeFirst = false }) {
    const typing = typeFirst || answerMode() === "type";
    const preview = el("span", { class: "produce-preview", lang: "ja" });
    const input = el("input", { type: "text", class: "produce-input", placeholder, autocomplete: "off", spellcheck: "false",
      oninput: () => { preview.textContent = romajiOnly ? "" : toKana(input.value); } });
    const form = el("form", { class: "produce-form", onsubmit: (e) => {
      e.preventDefault();
      if (!input.value.trim()) return;
      input.disabled = true;
      onTyped({ text: input.value.trim(), kana: toKana(input.value.trim(), { final: true }) });
    } }, input, el("button", { type: "submit", class: "secondary" }, "Check"), preview);
    const hold = holdControl("Hold and say it", onAudio, onProblem);
    const box = el("div", { class: "produce" }, typing ? [form, hold] : [hold, form]);
    box.focusTyping = () => input.focus();
    box.reopen = () => { input.disabled = false; input.value = ""; preview.textContent = ""; };
    box.hold = hold;
    if (typing) setTimeout(() => input.focus(), 0);
    return box;
  }
  /** The first sounds and a blank per sound left: enough to jog the memory, not give it away. */
  function cueFor(jp) {
    const sounds = [...jp.replace(/[、。！？!?\s]/g, "")];
    const show = Math.max(1, Math.min(2, Math.ceil(sounds.length / 4)));
    return sounds.slice(0, show).join("") + "＿".repeat(Math.max(1, sounds.length - show));
  }
  function answerMode() {
    return readPref("kaiwa_answer_mode", "speak") === "type" ? "type" : "speak";
  }

  // ---------- sentence building ----------
  /**
   * English prompt, a pile of tiles, one of them a wrong particle or ending. Number
   * keys or clicks move a tile up, Backspace takes the last one back, Enter checks.
   * `onResult` gets { right, helped, answer } once. `keys()` wires the keyboard, after frame().
   */
  function buildExercise(item, onResult) {
    const pile = shuffle([...item.tiles, ...(item.decoy ? [item.decoy] : [])]).map((text) => ({ text, used: false }));
    const picked = [];
    let finished = false;
    let helped = false;
    const answerLine = el("div", { class: "build-answer", "aria-label": "Your sentence" });
    const bank = el("div", { class: "build-bank" });
    const feedback = el("div", { class: "result", "aria-live": "polite" });
    const checkBtn = el("button", { type: "button", class: "secondary", onclick: check }, "Check", kbd("Enter"));
    const hintBtn = el("button", { type: "button", class: "secondary", onclick: hint }, "Hint", kbd("H"));
    const accepted = [item.jp, ...(item.also || [])];

    function draw() {
      answerLine.replaceChildren(...(picked.length ? picked.map((t) => el("button", { type: "button", class: "tile", lang: "ja",
        disabled: finished, onclick: () => giveBack(t) }, t.text)) : [el("span", { class: "build-empty", text: "Pick the pieces in order" })]));
      bank.replaceChildren(...pile.map((t, i) => el("button", { type: "button", class: "tile", lang: "ja",
        disabled: finished || t.used, onclick: () => take(i) }, el("span", { class: "choice-key", text: String(i + 1) }), t.text)));
      checkBtn.disabled = finished || !picked.length;
    }
    function take(i) {
      const t = pile[i];
      if (finished || !t || t.used) return;
      t.used = true;
      picked.push(t);
      draw();
    }
    function giveBack(t) {
      if (finished) return;
      t.used = false;
      picked.splice(picked.indexOf(t), 1);
      draw();
    }
    function hint() {
      if (finished) return;
      // Lay the first piece that's still wrong: clear what's after it, then place it.
      helped = true;
      let at = 0;
      while (at < picked.length && picked[at].text === item.tiles[at]) at += 1;
      for (const t of picked.splice(at)) t.used = false;
      const wanted = pile.find((t) => !t.used && t.text === item.tiles[at]);
      if (wanted) { wanted.used = true; picked.push(wanted); }
      draw();
    }
    function check() {
      if (finished || !picked.length) return;
      finished = true;
      keys.choice = null;
      keys.back = null;
      const answer = picked.map((t) => t.text).join("");
      const right = accepted.includes(answer);
      draw();
      checkBtn.hidden = hintBtn.hidden = true;
      feedback.replaceChildren(...[
        el("p", { class: "verdict " + (right ? "good" : "off"), text: right ? "Right." : "Not quite." }),
        el("p", { class: "build-model", lang: "ja", text: item.tiles.join(" ") }),
        !right && item.rule ? el("p", { class: "grammar-rule", text: item.rule }) : "",
        el("div", { class: "lesson-play" }, el("button", { class: "secondary", type: "button", onclick: () => play(item.jp) }, "Play", kbd("R"))),
      ]);
      keys.replay = () => play(item.jp);
      noteResult({ picked: answer, correct: item.jp, right });
      play(item.jp);
      onResult({ right, helped, answer });
    }
    draw();
    return {
      node: el("div", { class: "build" },
        el("p", { class: "prompt-en", text: item.en }), answerLine, bank,
        el("div", { class: "lesson-play" }, checkBtn, hintBtn), feedback),
      keys() {
        keys.choice = take;
        keys.primary = check;
        keys.hint = hint;
        keys.back = () => { if (picked.length) giveBack(picked[picked.length - 1]); };
      },
    };
  }

  // ---------- review ----------
  const GRADE_NAMES = { 1: "Again", 2: "Hard", 3: "Good", 4: "Easy" };
  function fmtInterval(seconds) {
    const s = Math.max(0, seconds);
    if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min`;
    if (s < 86400) return `${Math.round(s / 3600)} h`;
    const d = Math.round(s / 86400);
    if (d < 31) return d === 1 ? "1 day" : `${d} days`;
    const m = Math.round(d / 30.4);
    if (m < 12) return m === 1 ? "1 month" : `${m} months`;
    const y = Math.round(d / 365 * 10) / 10;
    return `${y} year${y === 1 ? "" : "s"}`;
  }
  /** "Good · next in 23 days", or for a short learning step "Again · back in 10 min (missed)". */
  function gradeLabel(r) {
    const name = GRADE_NAMES[r.rating];
    if (!r.learning) return `${name} · next in ${fmtInterval(r.seconds)}`;
    const why = r.rating === 1 ? " (missed)" : r.reps <= 2 ? " (new card)" : "";
    return `${name} · back in ${fmtInterval(r.seconds)}${why}`;
  }
  function autoAdvance() {
    return readPref("kaiwa_auto_advance", "0") === "1";
  }

  /**
   * Run a queue of cards. Each answer is graded on the server straight away
   * (the grade comes from what happened; see srs.rating_for) and a bar shows the
   * grade and when the card comes back. 1–4 changes the grade, Enter continues,
   * Ctrl+Z takes back the last answer. Cards due again within minutes come back
   * a few cards later.
   */
  function runReview(cards, { title = "Review", planStep = "review" } = {}) {
    const queue = cards.map((c) => ({ ...c, repeat: 0 }));
    let index = 0;
    const firstTry = new Map(); // queue item → right on first try?
    const history = [];         // answered items, for Ctrl+Z
    const MAX_REPEATS = 2;
    prefetch(queue.filter((c) => !c.grammar && !c.mined && !c.line).map((c) => [c.phrase ? c.phrase.jp : c.word ? c.word.jp : c.kana.char,
      c.skill === "listen" || (c.word && c.format === "choice") ? reviewVoice(c) : {}]));

    // Upcoming recognition word cards get swapped for short listening sentences.
    const wordIds = queue.filter((c) => c.kind === "word" && c.format === "choice").map((c) => c.card_id);
    if (wordIds.length >= 2) {
      postJson("/api/course/sentences", { card_ids: wordIds }).then(({ sentences }) => {
        for (const s of sentences || []) {
          const at = s.card_ids.map((id) => queue.findIndex((c, i) => i > index && c.card_id === id && !c.repeat));
          if (at.some((i) => i < 0)) continue;
          for (const i of [...at].sort((a, b) => b - a)) queue.splice(i, 1);
          queue.splice(Math.min(...at), 0, { kind: "sentence", sentence: s, repeat: 0,
            covers: cards.filter((c) => s.card_ids.includes(c.card_id)) });
          prefetch([[s.jp, {}]]);
        }
      }).catch(() => {});
    }

    let shownAt = 0;
    let current = null; // { item, answered, responses, bar } for the card on screen
    function next() {
      if (index >= queue.length) return finish();
      const card = queue[index];
      current = { item: card, answered: false, responses: [] };
      shownAt = performance.now();
      if (card.kind === "sentence") sentenceCard(card);
      else if (card.kind === "grammar") buildCard(card);
      else if (card.kind === "phrase" && card.skill === "speak") speakCard(card);
      else if (card.kind === "phrase") listenCard(card);
      else if (card.kind === "mined" || card.kind === "line") (card.format === "recall" ? minedRecallCard : minedCard)(card);
      else if (card.format === "produce") produceCard(card);
      else if (card.kind === "kana") kanaChoice(card);
      else wordChoice(card);
      keys.undo = undoLast; // after frame(), which clears per-screen keys
    }
    const elapsed = () => Math.round(performance.now() - shownAt);
    const idsOf = (card) => (card.kind === "sentence" ? card.covers.map((c) => c.card_id) : [card.card_id]);

    /**
     * Record an answer: grade it now, show the result bar in `slot`, and wire
     * 1–4 (change grade), Enter/Space (continue) and the optional auto-advance.
     */
    async function answered(card, outcome, slot, nextBtn) {
      if (current.answered) return;
      current.answered = true;
      if (!card.repeat && !firstTry.has(card)) firstTry.set(card, outcome.correct);
      keys.hold = null; // Space continues from here on
      const bar = el("div", { class: "grade-bar" }, el("span", { class: "grade-label", text: "Saving…" }));
      slot.replaceChildren(bar);
      nextBtn.hidden = false;
      keys.primary = keys.space = advance;
      const here = onThisScreen();
      try {
        current.responses = await Promise.all(idsOf(card).map((id) =>
          postJson("/api/course/grade", { card_id: id, ...outcome }).then((d) => d.card)));
      } catch (err) {
        bar.replaceChildren(el("span", { class: "grade-label off", text: String(err.message || err) }));
        return;
      }
      if (!here()) return;
      drawBar(bar);
      if (autoAdvance() && current.responses[0].rating >= 3) {
        let hovered = false;
        bar.addEventListener("mouseenter", () => { hovered = true; });
        await wait(2500);
        if (here() && !hovered && !current.changed) advance();
      }
    }
    function drawBar(bar) {
      const r = current.responses[0];
      const chips = [1, 2, 3, 4].map((g) => el("button", {
        type: "button", class: "grade-chip" + (g === r.rating ? " on" : ""),
        "data-tip": `${GRADE_NAMES[g]} · ${fmtInterval(r.intervals[g])}`,
        onclick: () => changeGrade(g, bar),
      }, el("span", { class: "choice-key", text: String(g) }), GRADE_NAMES[g]));
      // The chips stay out of the way: the grade is Kaiwa's job. 1-4 still change it.
      const chipRow = el("span", { class: "grade-chips", "aria-label": "Change the grade", hidden: !current.changed }, chips);
      const changeBtn = el("button", { type: "button", class: "grade-change", hidden: !!current.changed,
        onclick: () => { chipRow.hidden = false; changeBtn.hidden = true; } }, "Change");
      bar.replaceChildren(...[
        el("span", { class: "grade-label", text: gradeLabel(r) }),
        changeBtn,
        chipRow,
        r.auto_rating !== r.rating ? el("span", { class: "grade-note", text: `(Kaiwa picked ${GRADE_NAMES[r.auto_rating]})` }) : null,
      ].filter(Boolean));
      keys.grade = (g) => changeGrade(g, bar);
    }
    async function changeGrade(g, bar) {
      if (!current.responses.length || current.responses[0].rating === g) return;
      current.changed = true;
      try {
        current.responses = await Promise.all(idsOf(current.item).map((id) =>
          postJson("/api/course/regrade", { card_id: id, rating: g }).then((d) => d.card)));
        drawBar(bar);
      } catch (err) {
        bar.append(el("span", { class: "grade-note off", text: String(err.message || err) }));
      }
    }
    function advance() {
      if (!current || !current.answered || !current.responses.length) return;
      keys.primary = keys.space = keys.grade = null;
      const card = current.item;
      const responses = current.responses;
      let requeued = null;
      // Due again within minutes: bring it back a few cards later this session.
      const soon = responses.filter((r) => r.again_soon);
      if (soon.length && card.repeat < MAX_REPEATS) {
        const bases = card.kind === "sentence" ? card.covers.filter((c) => soon.some((r) => r.card_id === c.card_id)) : [card];
        requeued = bases.map((b) => ({ ...b, repeat: card.repeat + 1 }));
        queue.splice(Math.min(queue.length, index + 4), 0, ...requeued);
      }
      history.push({ card, at: index, requeued, ids: idsOf(card) });
      index += 1;
      const reopened = responses.map((r) => r.reopened).find(Boolean);
      if (reopened) {
        toast(`Unit ${reopened.number} needs another pass: ${reopened.missed} of its ${reopened.checked} checks were missed. Its grammar and listening are back in your lessons.`);
      }
      if (card.leech && !card.repeat && card.kind !== "sentence") return leechHelp(card);
      next();
    }

    /** Ctrl+Z: take back the answer on screen, or the previous one, and ask it again. */
    async function undoLast() {
      let target;
      if (current && current.answered && current.responses.length) {
        target = { card: current.item, at: index, requeued: null, ids: idsOf(current.item) };
      } else {
        target = history.pop();
      }
      if (!target) return toast("Nothing to undo.");
      try {
        for (const id of [...target.ids].reverse()) await postJson("/api/course/undo", { card_id: id });
      } catch (err) {
        return toast(String(err.message || err));
      }
      if (target.requeued) for (const r of target.requeued) {
        const i = queue.indexOf(r);
        if (i >= 0) queue.splice(i, 1);
      }
      firstTry.delete(target.card);
      index = target.at;
      next();
      toast("Undone.");
    }
    function toast(text) {
      const note = el("p", { class: "undo-toast", text });
      root.querySelector(".lesson")?.prepend(note);
      setTimeout(() => note.remove(), 1800);
    }
    const counter = () => ({ index: Math.min(index, queue.length - 1), total: queue.length });
    const repeatTag = (card) => (card.repeat ? el("span", { class: "repeat-tag", text: card.repeat === 1 ? "2nd look" : "3rd look" }) : null);

    /** Multiple choice: answer, see the grade and when it's back, Enter to go on. */
    function choiceCard(card, { big, bigJp, answer, options, audio, voice = {}, audioLater = false, after, extra = null, fmt, askJp }) {
      const result = el("div", { class: "result", "aria-live": "polite" });
      const slot = el("div", { class: "grade-slot" });
      let helped = false;
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      const body = el("div", { class: "card-body" },
        repeatTag(card),
        big ? el("p", { class: bigJp ? "kana-big" : "prompt-en", lang: bigJp ? "ja" : null, text: big }) : null,
        audio && !audioLater ? playRow(audio, voice) : null,
        typeof extra === "function" ? extra(() => { helped = true; }) : extra,
        choiceBlock({
          options, answer,
          onAnswer: (correct, picked) => {
            if (after) result.replaceChildren(after(correct));
            if (audioLater) {
              result.append(playRow(audio, voice));
              keys.replay = () => play(audio, voice);
            }
            if (audio) play(audio, voice);
            answered(card, { correct, ms: elapsed(), helped, fmt, answer: String(picked) }, slot, nextBtn);
          },
        }),
        result,
        slot,
      );
      frame({ title, ...counter(), body, actions: [nextBtn],
        ask: { screen: `${title.toLowerCase()} ${card.kind}`, jp: askJp || "", answer } });
      if (audio && !audioLater) keys.replay = () => play(audio, voice);
    }
    function kanaChoice(card) {
      const k = card.kana;
      const known = today.kana_pool || [];
      const pool = known.filter((x) => x.ro !== k.ro).map((x) => x.ro);
      // Reading test: hearing it first would give the answer away.
      choiceCard(card, { big: k.char, bigJp: true, answer: k.ro, audio: k.char, audioLater: true, fmt: "kana:choice", askJp: k.char,
        options: choicesFor(k.ro, pool, 4, alikeIn(k, known).map((x) => x.ro)),
        after: (right) => (right ? el("span") : kanaHelp(k, known)) });
    }
    /** A word already seen once is understood by ear: its text is one click away, as help. */
    function wordChoice(card) {
      const w = card.word;
      const m = meaningChoices(w, today.words_pool || []);
      const voice = reviewVoice(card);
      const byEar = (card.reps || 0) >= 1 && !card.leech;
      const text = el("p", { class: "kana-big kana-word", lang: "ja", hidden: byEar, text: w.jp });
      choiceCard(card, { answer: m.answer, options: m.options, audio: w.jp, voice, fmt: byEar ? "word:ear" : "word:choice", askJp: w.jp,
        extra: (markHelped) => {
          if (!byEar) return text;
          const showText = el("button", { class: "secondary", type: "button", onclick: () => {
            markHelped(); text.hidden = false; showText.hidden = true; } }, "Show text", kbd("T"));
          pendingText = () => showText.click();
          return [el("div", { class: "lesson-play" }, showText), text];
        },
        after: () => { text.hidden = false; return needsRomaji(w.jp) ? el("p", { class: "phrase-ro", text: w.ro }) : el("span"); } });
      play(w.jp, voice);
    }
    function listenCard(card) {
      const p = card.phrase;
      const pool = (today.phrases_pool || []).map((x) => x.en);
      const voice = reviewVoice(card);
      choiceCard(card, { answer: p.en, options: choicesFor(p.en, pool), audio: p.jp, voice, fmt: "phrase:listen", askJp: p.jp,
        after: () => phraseBlock(p) });
      play(p.jp, voice);
    }
    function sentenceCard(card) {
      const s = card.sentence;
      const text = el("p", { class: "sentence-jp", lang: "ja", hidden: true, text: s.jp });
      choiceCard(card, {
        answer: s.en, options: s.choices, audio: s.jp, fmt: "sentence", askJp: s.jp,
        extra: (markHelped) => {
          const showText = el("button", { class: "secondary", type: "button", onclick: () => {
            markHelped(); text.hidden = false; showText.hidden = true; } }, "Show text", kbd("T"));
          pendingText = () => showText.click();
          return [el("div", { class: "lesson-play" }, showText), text];
        },
        after: () => {
          text.hidden = false;
          return el("p", { class: "sentence-words" }, s.words.map((w) =>
            el("span", {}, el("span", { lang: "ja", text: w.jp }), ` ${w.en}`)));
        },
      });
      play(s.jp);
    }
    /**
     * A line mined from a show: the real clip, then pick its meaning. The text stays
     * hidden (reading it would turn a listening card into a reading one) unless asked for.
     */
    function minedCard(card) {
      const m = card.mined || card.line;
      const voice = m.audio_url ? { clip: m.audio_url } : {};
      const text = el("p", { class: "sentence-jp mined-jp", lang: "ja", hidden: true, text: m.text });
      choiceCard(card, {
        answer: m.en, options: shuffle([m.en, ...m.wrong]), audio: m.text, voice, fmt: `${card.kind}:listen`, askJp: m.text,
        extra: (markHelped) => {
          const showText = el("button", { class: "secondary", type: "button", onclick: () => {
            markHelped(); text.hidden = false; showText.hidden = true; } }, "Show text", kbd("T"));
          keys.text = () => showText.click();
          return [el("div", { class: "lesson-play" }, showText), text];
        },
        after: () => { text.hidden = true; return minedBack(m); }, // the back shows the line, marked
      });
      play(m.text, voice);
    }
    /**
     * A mined line that holds: hear it and recall what it means on your own, then check.
     * No options to lean on; you say whether you had it, and how fast you revealed it
     * (and whether you needed the text) shades the grade.
     */
    function minedRecallCard(card) {
      const m = card.mined || card.line;
      const voice = m.audio_url ? { clip: m.audio_url } : {};
      const text = el("p", { class: "sentence-jp mined-jp", lang: "ja", hidden: true, text: m.text });
      const result = el("div", { class: "result", "aria-live": "polite" });
      const slot = el("div", { class: "grade-slot" });
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      let helped = false;
      let revealMs = 0;
      const showText = el("button", { class: "secondary", type: "button", onclick: () => {
        helped = true; text.hidden = false; showText.hidden = true; } }, "Show text", kbd("T"));
      const ask = el("p", { class: "prompt mined-ask", text: "What does it mean? Say it to yourself, then check." });
      const judge = (got) => {
        if (current.answered) return;
        keys.choice = null;
        judgeRow.hidden = true;
        answered(card, { correct: got, ms: revealMs, helped, fmt: `${card.kind}:recall`, answer: got ? "got it" : "missed it" }, slot, nextBtn);
      };
      const judgeRow = el("div", { class: "mined-judge", hidden: true },
        el("button", { type: "button", class: "secondary", onclick: () => judge(false) }, el("span", { class: "choice-key", text: "1" }), "Missed it"),
        el("button", { type: "button", class: "secondary mined-got", onclick: () => judge(true) }, el("span", { class: "choice-key", text: "2" }), "Got it"));
      const reveal = () => {
        if (!revealBtn.isConnected || revealBtn.hidden) return;
        revealMs = elapsed();
        revealBtn.hidden = true;
        ask.hidden = true;
        text.hidden = true;
        showText.hidden = true;
        keys.text = null;
        result.replaceChildren(minedBack(m));
        judgeRow.hidden = false;
        keys.primary = keys.space = null;
        keys.choice = (i) => { if (i === 0) judge(false); else if (i === 1) judge(true); };
      };
      const revealBtn = el("button", { type: "button", class: "lesson-primary mined-reveal", onclick: reveal }, "Show meaning", kbd("Space"));
      const body = el("div", { class: "card-body" },
        repeatTag(card),
        playRow(m.text, voice),
        el("div", { class: "lesson-play" }, showText),
        text, ask, revealBtn, result, judgeRow, slot);
      frame({ title, ...counter(), body, actions: [nextBtn], primary: reveal,
        ask: { screen: `${title.toLowerCase()} mined recall`, jp: m.text, answer: m.en } });
      keys.space = reveal;
      keys.text = () => showText.click();
      keys.replay = () => play(m.text, voice);
      play(m.text, voice);
    }

    /** Known kana and words: produce the answer (say it, or type it). */
    function produceCard(card) {
      const isKana = card.kind === "kana";
      const target = isKana ? card.kana.char : card.word.jp;
      const result = el("div", { class: "result", "aria-live": "polite" });
      const slot = el("div", { class: "grade-slot" });
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      let startedAt = 0;
      function settle(o, shown) {
        if (current.answered) return;
        result.replaceChildren(...shown);
        play(target);
        dontKnow.hidden = true;
        keys.replay = () => play(target);
        const outcome = { ...o, fmt: `${card.kind}:produce:${o.spoken ? "say" : "type"}` };
        delete outcome.spoken;
        answered(card, outcome, slot, nextBtn);
      }
      function reveal(correct, band) {
        return [
          el("p", { class: "verdict " + (correct ? (band === "close" ? "close" : "good") : "off"),
            text: correct ? (band === "close" ? "Close." : "Right.") : "Not quite." }),
          el("p", { class: "produce-answer" }, el("span", { lang: "ja", text: target }),
            el("span", { class: "produce-answer-ro", text: isKana ? card.kana.ro : `${card.word.ro} · ${card.word.en}` })),
          isKana && !correct ? kanaHelp(card.kana, today.kana_pool || []) : null,
        ].filter(Boolean);
      }
      let helped = false;
      const cue = el("p", { class: "cue", hidden: true });
      const hintBtn = isKana ? null : el("button", { type: "button", class: "secondary", onclick: () => {
        helped = true;
        cue.hidden = false;
        cue.replaceChildren(el("span", { lang: "ja", text: cueFor(target) }));
        hintBtn.hidden = true;
      } }, "Hint", kbd("H"));
      const box = produceBox({
        placeholder: isKana ? "Type its sound (romaji)" : "Type it (romaji becomes kana)",
        romajiOnly: isKana,
        typeFirst: isKana, // single sounds are judged far more reliably typed than spoken
        onTyped: ({ text, kana }) => {
          const ms = elapsed();
          const correct = isKana
            ? kanaKey(kana) === kanaKey(target) || text.toLowerCase().replace(/[^a-z]/g, "") === card.kana.ro.replace(/ \(.*\)/, "")
              || (target === "を" && text.toLowerCase() === "o")
            : kanaKey(kana) === kanaKey(target);
          settle({ correct, ms, helped, answer: kana || text }, reveal(correct, ""));
        },
        onAudio: async (blob, ext) => {
          const ms = Math.round(startedAt - shownAt);
          result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
          try {
            const r = await api("/api/course/check_text", { method: "POST", body: audioForm(blob, ext, { target }) });
            if (r.band === "unsure") {
              result.replaceChildren(el("p", { class: "verdict close", text: "Hard to judge this sound by ear. Type it instead." }));
              box.focusTyping();
              return;
            }
            const correct = r.band !== "off";
            noteResult({ said: r.heard, band: r.band, tip: r.tip });
            settle({ correct, ms, helped, band: r.band, spoken: true, answer: r.heard },
              [...reveal(correct, r.band), heardLine("Sounded like ", r.heard), diffLine(r.diff), r.tip ? el("p", { class: "tip", text: r.tip }) : null].filter(Boolean));
          } catch (err) {
            result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
          }
        },
        onProblem: showProblem(result),
      });
      const holdStart = box.hold.holdApi.start;
      box.hold.holdApi.start = () => { startedAt = performance.now(); return holdStart(); };
      box.hold.addEventListener("pointerdown", () => { startedAt = performance.now(); }, true);
      const dontKnow = el("button", { type: "button", class: "secondary", onclick: () =>
        settle({ correct: false, ms: elapsed(), gave_up: true }, reveal(false, "")) }, "Show me");
      frame({
        title, ...counter(),
        body: el("div", { class: "card-body" },
          repeatTag(card),
          isKana
            ? el("p", { class: "kana-big", lang: "ja", text: target })
            : el("p", { class: "prompt-en", text: card.word.en }),
          el("p", { class: "prompt", text: isKana ? "Say or type its sound." : "Say it in Japanese, or type it." }),
          cue, box, micRow(), result, slot),
        actions: [hintBtn, dontKnow, nextBtn].filter(Boolean),
        hold: box.hold,
        ask: { screen: `${title.toLowerCase()} produce ${card.kind}`, jp: isKana ? target : "", en: isKana ? "" : card.word.en },
      });
      keys.tab = () => box.focusTyping();
      if (hintBtn) keys.hint = () => hintBtn.click();
    }

    /** A grammar point comes back as a different sentence to put together each time. */
    function buildCard(card) {
      const g = card.grammar;
      const item = { ...g.items[(card.reps || 0) % g.items.length], rule: g.rule };
      const slot = el("div", { class: "grade-slot" });
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      const ex = buildExercise(item, ({ right, helped, answer }) => {
        keys.primary = null;
        answered(card, { correct: right, ms: elapsed(), helped, fmt: "grammar:build", answer }, slot, nextBtn);
      });
      frame({ title, ...counter(),
        body: el("div", { class: "card-body" },
          repeatTag(card),
          el("p", { class: "prompt", text: "Put it together" }),
          ex.node,
          slot),
        actions: [nextBtn],
        ask: { screen: "grammar review", jp: item.jp, en: item.en, rule: g.rule, title: g.title } });
      ex.keys();
    }

    /** Say a phrase from its English: by voice or typed, with a hint before giving up. */
    function speakCard(card) {
      const p = card.phrase;
      const result = el("div", { class: "result", "aria-live": "polite" });
      const slot = el("div", { class: "grade-slot" });
      const answer = el("div", { class: "reveal", hidden: true });
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      let startedAt = 0;
      let helped = false;
      function settle(o) {
        if (current.answered) return;
        answer.hidden = false;
        answer.replaceChildren(phraseBlock(p), playRow(p.jp));
        keys.replay = () => play(p.jp);
        giveUp.hidden = true;
        hintBtn.hidden = true;
        answered(card, { ...o, helped, fmt: "phrase:speak" }, slot, nextBtn);
        if (!o.correct || o.band === "close") {
          // Saying it again right after hearing it is what fixes it. The grade stands.
          again.hidden = false;
          keys.hold = box.hold.holdApi;
          keys.space = null;
        }
      }
      function checked(r, ms) {
        result.replaceChildren(...[verdictLine(r.band), heardLine(r.typed ? "You typed " : "Sounded like ", r.heard), diffLine(r.diff),
          r.tip ? el("p", { class: "tip", text: r.tip }) : null].filter(Boolean));
        noteResult({ said: r.heard, band: r.band, tip: r.tip });
        if (current.answered) return; // a retry after the model: no new grade
        settle({ correct: r.band !== "off", ms, band: r.band, answer: r.heard });
        if (r.band !== "good") play(p.jp);
      }
      const cue = el("p", { class: "cue", hidden: true });
      const again = el("p", { class: "lesson-note", hidden: true, text: "Now say it once more, copying what you heard." });
      const box = produceBox({
        placeholder: "Or type it (romaji becomes kana)",
        onTyped: async ({ kana }) => {
          const ms = elapsed();
          const form = new FormData();
          form.append("phrase_id", p.id);
          form.append("text", kana);
          try {
            const r = await api("/api/course/check_typed", { method: "POST", body: form });
            checked({ ...r, typed: true }, ms);
          } catch (err) {
            result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
          }
          box.reopen();
        },
        onAudio: async (blob, ext) => {
          const ms = Math.round(startedAt - shownAt);
          result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
          try {
            checked(await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) }), ms);
          } catch (err) {
            result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
          }
        },
        onProblem: showProblem(result),
      });
      const hold = box.hold;
      hold.addEventListener("pointerdown", () => { startedAt = performance.now(); }, true);
      const holdStart = hold.holdApi.start;
      hold.holdApi.start = () => { startedAt = performance.now(); return holdStart(); };
      const hintBtn = el("button", { type: "button", class: "secondary", onclick: () => {
        helped = true;
        cue.hidden = false;
        cue.replaceChildren(el("span", { lang: "ja", text: cueFor(p.jp) }));
        hintBtn.hidden = true;
      } }, "Hint", kbd("H"));
      const giveUp = el("button", { type: "button", class: "secondary", onclick: () => {
        settle({ correct: false, ms: elapsed(), gave_up: true }); play(p.jp); } }, "Show me");
      frame({ title, ...counter(),
        body: el("div", { class: "card-body" },
          repeatTag(card),
          el("p", { class: "prompt", text: "Say this in Japanese" }),
          el("p", { class: "prompt-en", text: p.en }),
          cue, box, micRow(), result, again, answer, slot),
        actions: [hintBtn, giveUp, nextBtn], hold,
        ask: { screen: `${title.toLowerCase()} speak`, jp: p.jp, en: p.en, note: p.note } });
      keys.tab = () => box.focusTyping();
      keys.hint = () => hintBtn.click();
    }

    /**
     * After answering a card you keep forgetting: a new way in (its parts and a
     * memory hook, written once by Flash and kept), then on with the review.
     */
    async function leechHelp(card) {
      const item = card.word || card.phrase || (card.grammar && card.grammar.items[0]) || (card.kana && { jp: card.kana.char, en: card.kana.ro })
        || ((card.mined || card.line) && { jp: (card.mined || card.line).text, en: (card.mined || card.line).en });
      const line = card.mined || card.line;
      const voice = line && line.audio_url ? { clip: line.audio_url } : {};
      const hookBox = el("div", { class: "leech-hook" }, el("p", { class: "pending", text: "Writing a memory hook…" }));
      current = null;
      frame({
        title, ...counter(),
        body: el("div", { class: "card-body leech" },
          el("p", { class: "leech-note", text: "This one keeps slipping. Here's another way in." }),
          el("p", { class: "kana-big kana-word", lang: "ja", text: item.jp }),
          el("p", { class: "phrase-en", text: item.en }),
          playRow(item.jp, voice),
          hookBox),
        actions: [primaryButton("Continue", next)],
        primary: next,
        ask: { screen: "leech help", jp: item.jp, en: item.en },
      });
      keys.undo = undoLast;
      keys.replay = () => play(item.jp, voice);
      play(item.jp, voice);
      const here = onThisScreen();
      let hook = card.hook;
      if (!hook) {
        try { hook = (await postJson("/api/course/hook", { card_id: card.card_id })).hook; } catch (_) { hook = null; }
      }
      if (!here()) return;
      hookBox.replaceChildren(...(hook ? [
        el("p", { class: "leech-hook-text", text: hook.hook }),
        hook.parts.length ? el("table", { class: "ask-breakdown" }, el("tbody", {}, hook.parts.map((b) =>
          el("tr", {}, el("td", { lang: "ja", text: b.jp }), el("td", { text: b.en }))))) : null,
      ].filter(Boolean) : [el("p", { class: "status", text: "No hook this time; the Ask box can explain it." })]));
    }

    function finish() {
      current = null;
      const onPlan = planStep === "review" || planStep === "recap" || planStep === "mined" || planStep === "kaishi";
      const go = async () => {
        if (!onPlan) return showHome();
        if (!(await refreshOrRetry(go))) return undefined;
        if (planStep === "recap") writePref("kaiwa_recap_settled", JSON.stringify({ day: dayKey(), left: (today.recap || []).length }));
        today.plan = (today.plan || []).filter((s) => s !== planStep);
        return runNext();
      };
      const firsts = firstTry.size;
      const right = [...firstTry.values()].filter(Boolean).length;
      frame({
        title,
        body: el("div", { class: "card-body" },
          el("h3", { class: "end-title", text: `${right} of ${firsts} right` }),
          el("p", { class: "prompt", text: planStep === "recap"
            ? "These come back over the next days, further apart each time you get them right."
            : "Each card comes back when you're about to forget it." })),
        actions: [primaryButton("Continue", go)],
        primary: go,
      });
      keys.undo = undoLast;
    }

    if (!queue.length) return showHome();
    next();
  }

  // ---------- stats ----------
  const SVG_NS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs, ...children) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v != null) node.setAttribute(k, v);
    for (const c of children.flat()) if (c) node.append(c);
    return node;
  }
  /** Vertical bars with a value on hover; `labels` maps index → axis text. */
  function barChart(values, { height = 110, labels = {}, title = (i, v) => String(v), line = null, max = null, min = 0 } = {}) {
    const w = 640;
    const top = Math.max(max ?? 0, ...values.map((v) => v ?? 0), line ?? 0, 1);
    const gap = 3;
    const bw = (w - gap * (values.length - 1)) / values.length;
    const plotH = height - 18;
    const scale = (v) => (Math.max(0, v - min) / Math.max(1, top - min)) * plotH;
    const bars = values.map((v, i) => {
      const h = v == null ? 0 : Math.max(v ? 2 : 0, scale(v));
      return svg("rect", { x: (i * (bw + gap)).toFixed(1), y: (plotH - h).toFixed(1), width: bw.toFixed(1), height: h.toFixed(1),
        rx: 2, class: v == null ? "bar empty" : "bar" }, svg("title", {}, document.createTextNode(title(i, v))));
    });
    const ticks = Object.entries(labels).map(([i, text]) => {
      const n = Number(i);
      // Keep the end labels inside the chart.
      const anchor = n === 0 ? "start" : n === values.length - 1 ? "end" : "middle";
      const x = anchor === "start" ? n * (bw + gap) : anchor === "end" ? n * (bw + gap) + bw : n * (bw + gap) + bw / 2;
      return svg("text", { x: x.toFixed(1), y: height - 4, "text-anchor": anchor, class: "axis" }, document.createTextNode(text));
    });
    const target = line == null ? null : svg("line", { x1: 0, x2: w, y1: (plotH - scale(line)).toFixed(1),
      y2: (plotH - scale(line)).toFixed(1), class: "target-line" });
    return svg("svg", { viewBox: `0 0 ${w} ${height}`, class: "chart", role: "img" }, bars, target, ticks);
  }

  /**
   * Your decks: lines you mined, and decks brought in from Anki (Kaishi). Importing reads a copy
   * of Anki's collection, so Anki itself is never changed. No due counts anywhere here.
   */
  async function runDecks() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    clearKeys();
    const here = screenId;
    root.replaceChildren(el("div", { class: "home" }, el("p", { class: "pending", text: "Loading…" })));
    const [mined, kaishi, job] = await Promise.all([
      api("/api/course/mined").catch(() => null),
      api("/api/course/imported/kaishi").catch(() => null),
      api("/api/course/anki/import/status").catch(() => null),
    ]);
    if (screenId !== here) return;
    const card = (title, ...body) => el("section", { class: "deck-card" }, el("h3", { class: "deck-title", text: title }), ...body);

    const minedCard = card("Mined lines",
      el("p", { class: "stats-text", text: mined ? `${mined.total} line${mined.total === 1 ? "" : "s"} from your shows.` : "Lines you mine from shows." }),
      el("button", { type: "button", class: "secondary", onclick: runMining }, "Open mined lines"));

    let kaishiCard;
    if (kaishi) {
      const c = kaishi.counts;
      kaishiCard = card(kaishi.label,
        el("p", { class: "stats-text", text: `${c.studied} studied, ${c.new} new words waiting${c.paused ? `, ${c.paused} paused` : ""}. Brought in from Anki ${kaishi.imported_at ? new Date(kaishi.imported_at).toLocaleDateString() : ""}.` }),
        el("p", { class: "stats-caption", text: "Studied cards come back a few a day, easiest first. New words start once you've finished the course." }),
        el("div", { class: "deck-actions" },
          el("button", { type: "button", class: "secondary", onclick: () => runImported("kaishi") }, "Browse"),
          el("button", { type: "button", class: "secondary", onclick: () => runAnkiImport() }, "Update from Anki")));
    } else {
      kaishiCard = card("Bring in your Anki deck",
        el("p", { class: "stats-text", text: "Kaishi 1.5k (or another sentence deck) comes in with its audio, pictures and your progress, so what you remember carries over. Anki itself isn't changed." }),
        el("button", { type: "button", class: "lesson-primary", onclick: () => runAnkiImport() }, "Import from Anki"));
    }
    const running = job && job.running ? el("p", { class: "home-note", text: `Importing: ${job.stage} ${job.total ? `${job.done} of ${job.total}` : ""}` }) : null;
    root.replaceChildren(el("div", { class: "home decks" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Back"),
        el("h2", { class: "lesson-title", text: "Your decks" })),
      running, kaishiCard, minedCard));
    keys.primary = showHome;
    if (running) setTimeout(() => { if (screenId === here + 0 && learnVisible()) runDecks(); }, 1500);
  }

  /** Pick an Anki profile and deck, see what comes in, then import with progress. */
  async function runAnkiImport() {
    stopAudio();
    screenId += 1;
    clearKeys();
    const here = screenId;
    const page = (...body) => root.replaceChildren(el("div", { class: "home decks" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => runDecks() }, "Back"),
        el("h2", { class: "lesson-title", text: "Import from Anki" })), ...body));
    page(el("p", { class: "pending", text: "Looking for Anki on this computer…" }));
    let cols;
    try {
      cols = (await api("/api/course/anki/collections")).collections;
    } catch (err) {
      return page(el("p", { class: "verdict off", text: String(err.message || err) }));
    }
    if (screenId !== here) return;
    if (!cols.length) {
      return page(el("p", { class: "stats-text", text: "Kaiwa couldn't find Anki's data on this computer. Open Anki once (and let it finish syncing), then try again." }));
    }
    const status = el("div", { class: "anki-decks", "aria-live": "polite" });
    const pickProfile = async (col) => {
      status.replaceChildren(el("p", { class: "pending", text: "Reading your decks (Anki can stay open)…" }));
      let decks;
      try {
        decks = (await api(`/api/course/anki/decks?path=${encodeURIComponent(col.path)}`)).decks;
      } catch (err) {
        status.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        return;
      }
      if (!decks.length) {
        status.replaceChildren(el("p", { class: "stats-text", text: "No sentence decks here (Kaiwa needs a sentence and its meaning on each card)." }));
        return;
      }
      status.replaceChildren(...decks.map((d) => el("div", { class: "deck-card" },
        el("h3", { class: "deck-title", text: d.name.split("::").pop() }),
        el("p", { class: "stats-text", text: `${d.total} cards: ${d.studied} studied (your progress comes with them), ${d.new} new${d.suspended ? `, ${d.suspended} suspended (they come in paused)` : ""}.` }),
        el("p", { class: "stats-caption", text: `Note type ${d.note_type}. Kaiwa found: ${d.roles.join(", ")}.` }),
        el("button", { type: "button", class: "lesson-primary", onclick: (e) => startImport(col, d, e.currentTarget) }, "Import as Kaishi"))));
    };
    const startImport = async (col, d, btn) => {
      btn.disabled = true;
      try {
        await postJson("/api/course/anki/import", { path: col.path, deck_id: d.id, deck: "kaishi" });
      } catch (err) {
        btn.disabled = false;
        status.append(el("p", { class: "verdict off", text: String(err.message || err) }));
        return;
      }
      const bar = el("div", { class: "home-bar" }, el("span", { style: "width:0%" }));
      const line = el("p", { class: "stats-text", "aria-live": "polite", text: "Starting…" });
      status.replaceChildren(line, bar);
      const poll = async () => {
        if (screenId !== here) return;
        const j = await api("/api/course/anki/import/status").catch(() => null);
        if (!j) return setTimeout(poll, 1000);
        line.textContent = `${j.stage}${j.total ? ` ${j.done} of ${j.total}` : ""}`;
        bar.firstChild.style.width = `${j.total ? Math.round((100 * j.done) / j.total) : 5}%`;
        if (j.running) return setTimeout(poll, 600);
        if (j.error) {
          line.textContent = `Import failed: ${j.error}`;
          return;
        }
        const r = j.result || {};
        status.replaceChildren(
          el("p", { class: "home-done", text: "Done." }),
          el("p", { class: "stats-text", text: r.kept
            ? `Updated ${r.rows} sentences. Your Kaiwa progress was kept for ${r.kept} cards${r.added ? `, and ${r.added} more came in` : ""}.`
            : `${r.rows} sentences came in: ${r.added} with your Anki progress${r.paused ? ` (${r.paused} paused)` : ""}, ${r.new} new words for after the course.` }),
          el("button", { type: "button", class: "lesson-primary", onclick: showHome }, "Back to today"));
      };
      poll();
    };
    const profiles = el("div", { class: "deck-actions" }, cols.map((c) =>
      el("button", { type: "button", class: "secondary", onclick: () => pickProfile(c) }, `Anki profile: ${c.profile}`)));
    page(el("p", { class: "stats-text", text: "Kaiwa reads a copy of your Anki collection, so Anki is never changed and can stay open. Reviews you do in Kaiwa stay in Kaiwa for now." }),
      profiles, status);
    if (cols.length === 1) pickProfile(cols[0]);
  }

  /** An imported deck's cards: search, see what's paused, and bring paused ones back. */
  async function runImported(deck, { q = "", paused = false } = {}) {
    stopAudio();
    screenId += 1;
    clearKeys();
    const here = screenId;
    let d;
    try {
      d = await api(`/api/course/imported/${deck}?q=${encodeURIComponent(q)}&paused=${paused ? 1 : 0}`);
    } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    if (screenId !== here) return;
    const search = el("input", { type: "search", class: "imported-search", value: q, placeholder: "Search words, sentences or meanings", "aria-label": "Search" });
    let timer = 0;
    search.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => runImported(deck, { q: search.value, paused }).then(() => {
        const s = root.querySelector(".imported-search");
        if (s) { s.focus(); s.setSelectionRange(s.value.length, s.value.length); }
      }), 300);
    });
    const STATUS = { new: "new", learning: "learning", known: "known", paused: "paused" };
    const rowFor = (r) => el("li", { class: "mined-row" },
      el("button", { type: "button", class: "secondary mined-play", "aria-label": "Play",
        onclick: () => play(r.text, r.audio_url ? { clip: r.audio_url } : {}) }, "▶"),
      el("div", { class: "mined-main" },
        el("p", { class: "mined-text", lang: "ja", text: r.text }),
        el("p", { class: "mined-en", text: `${r.word ? `${r.word} · ` : ""}${r.en}` }),
        el("p", { class: "mined-meta" },
          el("span", { class: `mined-chip ${r.status === "known" ? "ready" : ""}`, text: STATUS[r.status] }),
          r.status === "paused" ? el("button", { type: "button", class: "link-button", onclick: async () => {
            await postJson(`/api/course/imported/${deck}/unpause`, { ids: [r.id] }).catch(() => {});
            runImported(deck, { q, paused });
          } }, "Unpause") : null)));
    const c = d.counts;
    root.replaceChildren(el("div", { class: "home mining" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => runDecks() }, "Back"),
        el("h2", { class: "lesson-title", text: d.label })),
      el("p", { class: "stats-text", text: `${c.studied} studied, ${c.new} new, ${c.paused} paused (suspended in Anki).` }),
      el("div", { class: "deck-actions" },
        search,
        el("label", { class: "home-romaji" }, el("input", { type: "checkbox", checked: paused, onchange: (e) => runImported(deck, { q, paused: e.target.checked }) }), " Paused only"),
        c.paused ? el("button", { type: "button", class: "secondary", onclick: async (e) => {
          const b = e.currentTarget;
          if (b.dataset.armed !== "1") { b.dataset.armed = "1"; b.textContent = `Unpause all ${c.paused}: click again`; return; }
          await postJson(`/api/course/imported/${deck}/unpause`, {}).catch(() => {});
          runImported(deck, { q, paused });
        } }, "Unpause all") : null),
      d.rows.length ? el("ul", { class: "mined-list" }, d.rows.map(rowFor)) : el("p", { class: "status", text: "Nothing matches." }),
      d.rows.length >= 200 ? el("p", { class: "stats-caption", text: "Showing the first 200. Search to find others." }) : null));
    keys.primary = () => runDecks();
  }

  /**
   * Mined lines: how to point asbplayer here, and what's come in. No due counts:
   * this page is for what you caught, not what you owe.
   */
  async function runMining() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    clearKeys();
    root.replaceChildren(el("div", { class: "home" }, el("p", { class: "pending", text: "Loading…" })));
    let d;
    try {
      d = await api("/api/course/mined");
    } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    const url = `${location.protocol}//${location.hostname === "localhost" ? "127.0.0.1" : location.hostname}:${location.port || 80}${d.path}`;
    const copy = el("button", { type: "button", class: "secondary", onclick: async () => {
      try { await navigator.clipboard.writeText(url); copy.textContent = "Copied"; } catch (_) { copy.textContent = "Select and copy it"; }
    } }, "Copy");
    const step = (...parts) => el("li", {}, ...parts);
    const code = (t) => el("code", { text: t });
    const setup = el("details", { class: "mining-setup", open: d.total === 0 },
      el("summary", {}, "Set up asbplayer"),
      el("p", { class: "stats-text", text: "In Tsugi, turn on Mining in the player: it fetches Japanese subtitles and sends lines here with one key, no setup here needed. For YouTube and other sites, use asbplayer, a browser extension that mines from any video with subtitles. Kaiwa stands in for Anki, so it sends them here instead." }),
      el("ol", { class: "mining-steps" },
        step("Install asbplayer in your browser, then open its settings and go to ", el("strong", { text: "Anki" }), "."),
        step("Set the AnkiConnect URL to ", el("span", { class: "mining-url" }, code(url), copy)),
        step("Pick deck ", code("Kaiwa"), " and note type ", code("Kaiwa Mining"), "."),
        step("Map the fields: Sentence → ", code("Sentence"), ", Definition → ", code("Translation"), ", Audio → ", code("Audio"),
          ", Image → ", code("Image"), ", Word → ", code("Word"), ", Source → ", code("Source"), ", URL → ", code("URL"), "."),
        step("Watch something with Japanese subtitles and mine a line. It shows up below, and in your day once it's ready.")),
      el("p", { class: "stats-caption", text: "This only works on this PC, from browser extensions. Websites can't send lines here." }));
    const notes = [
      !d.has_key ? el("p", { class: "home-note", text: "Lines are waiting for your DeepSeek key (Settings) to work out their meaning and reading. They'll be ready a minute after it's saved." }) : null,
      d.refused ? el("p", { class: "home-note", text: `Kaiwa turned away a request from ${d.refused.origin}: only browser extensions can send lines here. If that was your mining tool, use its extension rather than its website.` }) : null,
    ];
    const STATUS = { ready: "ready", pending: "getting ready", failed: "couldn't prepare" };
    const rowFor = (r) => {
      const remove = el("button", { type: "button", class: "link-button mined-remove" }, "Remove");
      let armed = false;
      remove.onclick = async () => {
        if (!armed) { armed = true; remove.textContent = "Remove: click again"; return; }
        remove.disabled = true;
        try { await api(`/api/course/mined/${encodeURIComponent(r.id)}`, { method: "DELETE" }); } catch (_) {}
        runMining();
      };
      const retry = r.status === "failed" ? el("button", { type: "button", class: "link-button", onclick: async () => {
        try { await postJson(`/api/course/mined/${encodeURIComponent(r.id)}/retry`, {}); } catch (_) {}
        runMining();
      } }, "Retry") : null;
      return el("li", { class: "mined-row" },
        el("button", { type: "button", class: "secondary mined-play", "aria-label": "Play",
          onclick: () => play(r.text, r.audio_url ? { clip: r.audio_url } : {}) }, "▶"),
        el("div", { class: "mined-main" },
          el("p", { class: "mined-text", lang: "ja", text: r.text }),
          r.status === "ready" ? el("p", { class: "mined-en", text: r.en }) : null,
          el("p", { class: "mined-meta" },
            el("span", { class: `mined-chip ${r.status}`, text: STATUS[r.status] || r.status }),
            sourceLine(r.source) ? el("span", { text: sourceLine(r.source) }) : null,
            retry, remove)));
    };
    const list = d.rows.length
      ? el("ul", { class: "mined-list" }, d.rows.map(rowFor))
      : el("p", { class: "status", text: "Nothing mined yet. Once asbplayer is set up, lines you mine appear here." });
    const more = d.total > d.rows.length ? el("p", { class: "stats-caption", text: `Showing the newest ${d.rows.length} of ${d.total}.` }) : null;
    root.replaceChildren(el("div", { class: "home mining" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => runDecks() }, "Back"),
        el("h2", { class: "lesson-title", text: "Mined lines" })),
      notes, setup, list, more));
    keys.primary = showHome;
    if (d.counts.pending) {
      // Lines being prepared: look again shortly, while this page is still open.
      const here = screenId;
      setTimeout(() => { if (screenId === here && learnVisible()) runMining(); }, 8000);
    }
  }

  async function runStats() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    clearKeys();
    root.replaceChildren(el("div", { class: "home" }, el("p", { class: "pending", text: "Loading…" })));
    let s;
    try {
      s = await api("/api/course/stats");
    } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    const section = (name, ...body) => el("section", { class: "stats-section" }, el("h3", { class: "stats-h", text: name }), ...body);
    const r = s.retention;

    const today = section("Today",
      el("div", { class: "stats-figures" },
        figure(String(s.today.answers), "answers"),
        figure(s.today.answers ? `${Math.round((100 * s.today.right) / s.today.answers)}%` : "–", "remembered"),
        figure(`${s.today.minutes}`, "minutes answering"),
        figure(`${s.today.listening}`, `minutes listening (${s.listening_total} in all)`),
        figure(String(s.today.talk), "lines spoken in talk practice"),
        figure(String(s.streak), s.streak === 1 ? "day in a row" : "days in a row")));

    const retention = section("Remembered in reviews",
      r ? el("div", { class: "stats-figures" },
            figure(`${r.percent}%`, `last ${r.days} days (${r.reviews} reviews)`),
            ...Object.entries(r.by_kind).map(([k, v]) => figure(`${v}%`, k)))
        : el("p", { class: "status", text: "Shows up once you've done 20 reviews of cards you've already learned." }),
      el("p", { class: "stats-caption", text: `Per week (scale 50–100%), against the ${s.target}% target (dashed line):` }),
      barChart(s.weeks.map((w) => w.percent), {
        max: 100, min: 50, line: s.target, // 50–100%: the useful range, so differences show
        labels: Object.fromEntries(s.weeks.map((w, i) => [i, i === s.weeks.length - 1 ? "this week" : `${s.weeks.length - 1 - i}w ago`])),
        title: (i, v) => (v == null ? "No reviews that week" : `${v}% of ${s.weeks[i].reviews} reviews`),
      }));

    const forecast = section("Coming up",
      el("p", { class: "stats-caption", text: `Reviews due each day for the next 30 days (${s.forecast.reduce((a, b) => a + b, 0)} in all).` }),
      barChart(s.forecast, {
        labels: { 0: "today", 7: "+7", 14: "+14", 21: "+21", 29: "+29" },
        title: (i, v) => `${i === 0 ? "Today" : i === 1 ? "Tomorrow" : `In ${i} days`}: ${v} review${v === 1 ? "" : "s"}`,
      }));

    const stageNames = { new: "New", learning: "Learning", young: "Growing", mature: "Strong" };
    const cardsTable = section("Your cards",
      el("table", { class: "stats-table" },
        el("thead", {}, el("tr", {}, el("th"), Object.values(stageNames).map((n) => el("th", { text: n })))),
        el("tbody", {}, Object.entries(s.stages).map(([kind, row]) => el("tr", {},
          el("th", { text: kind }), Object.keys(stageNames).map((k) => el("td", { text: String(row[k]) })))))),
      el("p", { class: "stats-caption", text: "Learning: in its first short steps. Growing: remembered for under 3 weeks. Strong: 3 weeks or more." }));

    const intervals = section("How long your cards last",
      el("div", { class: "hbars" }, s.intervals.map((b) => {
        const most = Math.max(1, ...s.intervals.map((x) => x.count));
        return el("div", { class: "hbar" },
          el("span", { class: "hbar-label", text: b.label }),
          el("span", { class: "hbar-track" }, el("span", { class: "hbar-fill", style: `width:${(100 * b.count) / most}%` })),
          el("span", { class: "hbar-n", text: String(b.count) }));
      })));

    const most = Math.max(1, ...s.activity.map((a) => a.answers));
    const calendar = section("Activity",
      el("div", { class: "calendar", role: "img", "aria-label": "Answers per day, last 16 weeks" },
        s.activity.map((a) => el("span", {
          class: "day" + (a.studied || a.answers ? " on" : ""),
          style: a.answers ? `--level:${(0.25 + (0.75 * a.answers) / most).toFixed(2)}` : null,
          title: `${a.d}: ${a.answers} answer${a.answers === 1 ? "" : "s"}`,
        }))));

    const tricky = section("Tricky cards",
      s.leeches.length
        ? [el("ul", { class: "leech-list" }, s.leeches.map((c) => {
            const item = c.word || c.phrase || (c.grammar && c.grammar.items[0]) || { jp: c.kana.char, en: c.kana.ro };
            return el("li", {},
              el("span", { class: "leech-jp", lang: "ja", text: item.jp }),
              el("span", { class: "leech-en", text: item.en }),
              el("span", { class: "leech-lapses", text: `forgotten ${c.lapses}×` }),
              c.hook ? el("span", { class: "leech-hook-line", text: c.hook.hook }) : null);
          })),
          el("button", { type: "button", class: "secondary", onclick: () =>
            runReview(s.leeches, { title: "Tricky cards", planStep: "tricky" }) }, "Practise these now")]
        : el("p", { class: "status", text: "None. A card shows up here after you've forgotten it 4 times." }));

    const grading = section("How Kaiwa grades you",
      el("ul", { class: "stats-rules" }, s.grading.lines.map((line) => el("li", { text: line }))),
      el("p", { class: "stats-caption", text: s.grading.basis + (s.grading.tuned ? "" : " Changing a grade with 1–4 teaches it.") }));

    const slips = (s.slips || []).length ? section("What trips you up lately",
      el("ul", { class: "slip-list" }, s.slips.map((slip) => el("li", {},
        el("span", { class: "slip-name", text: slip.label }),
        el("span", { class: "slip-count", text: `${slip.count} times` }),
        slip.example ? el("span", { class: "slip-example", lang: "ja", text: slip.example }) : null,
        slip.cards.length ? el("button", { type: "button", class: "secondary", onclick: () =>
          runReview(slip.cards, { title: "Practice", planStep: "practice" }) }, "Practise this") : null))),
      el("p", { class: "stats-caption", text: "Noticed across your speaking, talk practice and Chat over the last 30 days. Mistakes like these are normal, and knowing which is yours is half of fixing it." })) : null;

    const can = section("What you can do now",
      s.can_do.length
        ? el("ul", { class: "stats-rules" }, s.can_do.map((line) => el("li", { text: line })))
        : el("p", { class: "status", text: "Finish a unit and it shows up here." }),
      s.milestones.length ? el("p", { class: "stats-caption", text: s.milestones.map((m) => m.text).join(" ") }) : null);

    const how = section("How scheduling works",
      el("p", { class: "stats-text", text: "Kaiwa estimates how long you'll remember each card and brings it back just before you'd forget, aiming for 87% recall." }),
      el("p", { class: "stats-text", text: "New and missed cards come back within minutes, then the next day, then further apart each time you get them right. That's why you see some cards twice in a session." }),
      el("p", { class: "stats-text", text: "The grade after each answer comes from how you did: wrong is Again; right but slow, close, or with help is Hard; right at your usual speed is Good; much faster than usual is Easy. Press 1–4 to change it, Ctrl+Z to undo an answer." }));

    root.replaceChildren(el("div", { class: "home stats" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Back"),
        el("h2", { class: "lesson-title", text: "Stats" })),
      can, slips, today, forecast, calendar, tricky, retention,
      el("details", { class: "stats-more" }, el("summary", {}, "More detail"), cardsTable, intervals, grading, how)));
    keys.primary = showHome;
  }
  function figure(value, label) {
    return el("div", { class: "figure" }, el("span", { class: "figure-value", text: value }), el("span", { class: "figure-label", text: label }));
  }

  // ---------- placement test ----------
  const SKILL_INFO = {
    words: { title: "Words by ear", prompt: "Type what this word means, in English." },
    sentences: { title: "Sentences by ear", prompt: "Type what this means, in English." },
    imitate: { title: "Repeat after me", prompt: "Listen, then hold and say it back." },
  };

  /**
   * Adaptive placement: a short kana check, then three skills that each home in
   * on a course unit (see placement.py). No options to pick from: every answer
   * is typed or spoken. Nothing is changed until the learner presses Apply.
   */
  function runPlacement() {
    track("open", { activity: "placement" });
    const histories = { words: [], sentences: [], imitate: [] };
    const kanaAnswers = [];
    const unitTitle = (n) => (n >= 1 && UNIT_TITLES[n - 1]) || "";

    function intro() {
      frame({
        title: "Placement test",
        body: el("div", { class: "card-body" },
          el("h3", { class: "end-title", text: "Find your starting point" }),
          el("p", { class: "lesson-note", text: "About 6–10 minutes. Each part adjusts to your answers and stops once it knows your level, so it won't drag on." }),
          el("ul", { class: "stats-rules" },
            el("li", { text: "Kana: type the sound of a few characters." }),
            el("li", { text: "Words and sentences: listen, then type what they mean in English. Stuck? Leave it empty and press Enter for a hint: slower audio, then the kana, then a first letter." }),
            el("li", { text: "Repeat after me: say a few phrases back (skip it if you have no microphone)." })),
          el("p", { class: "lesson-note", text: "Don't guess: an empty Enter gets you a hint, and how much help you needed tells the test a lot. Nothing changes until you press Apply at the end." })),
        actions: [el("button", { type: "button", class: "secondary", onclick: showHome }, "Not now"), primaryButton("Start", kana)],
        primary: kana,
      });
    }

    // 1. Kana: see a character, type its romaji.
    async function kana() {
      let items;
      try { items = (await api("/api/course/placement/kana")).items; } catch (err) { return fail(err); }
      let i = 0;
      function ask() {
        if (i >= items.length) return skill("words");
        const k = items[i];
        const input = el("input", { type: "text", class: "produce-input", placeholder: "Its sound in romaji (empty = don't know)",
          autocomplete: "off", spellcheck: "false" });
        const submit = () => {
          const typed = input.value.trim().toLowerCase().replace(/[^a-z]/g, "");
          const want = k.ro.replace(/ \(.*\)/, "");
          const correct = !!typed && (typed === want || kanaKey(toKana(typed, { final: true })) === kanaKey(k.char)
            || (k.char === "を" && typed === "o") || (k.char === "ヲ" && typed === "o"));
          kanaAnswers.push({ group: k.group, correct });
          i += 1;
          ask();
        };
        frame({
          title: "Placement: kana", index: i, total: items.length,
          body: el("div", { class: "card-body" },
            el("p", { class: "kana-big", lang: "ja", text: k.char }),
            el("form", { class: "produce-form", onsubmit: (e) => { e.preventDefault(); submit(); } }, input,
              el("button", { type: "submit", class: "secondary" }, "Next"))),
          actions: [],
        });
        setTimeout(() => input.focus(), 0);
      }
      ask();
    }

    // 2–4. The adaptive skills, each item with graduated hints: every "don't know"
    // or miss makes the same item easier (slowed audio, then the kana, then the
    // first letter of the meaning) and an answer earns less credit per hint.
    const HINT_CREDIT = [1, 0.75, 0.5, 0.25];
    const MAX_HINT = { words: 3, sentences: 2, imitate: 2 };
    async function skill(name) {
      let item;
      try {
        item = (await postJson("/api/course/placement/next", { skill: name, history: histories[name] })).item;
      } catch (err) { return fail(err); }
      if (!item) return name === "words" ? skill("sentences") : name === "sentences" ? imitateIntro() : results();
      const info = SKILL_INFO[name];
      const n = histories[name].length;
      // One voice for every item, the easiest to make out: a word is heard once, with no context.
      const voice = { voice: "clear" };
      let hint = 0;
      const record = (judged) => {
        histories[name].push({ id: item.id, unit: item.unit, judged, hint, score: judged * HINT_CREDIT[hint] });
        skill(name);
      };
      const hintBox = el("div", { class: "hint-steps" });
      const slow = () => play(item.jp, { ...voice, slow: true });
      // One step easier: returns false when there are no hints left.
      function easier() {
        if (hint >= MAX_HINT[name]) return false;
        hint += 1;
        if (hint === 1) {
          hintBox.append(el("div", { class: "hint-row" }, el("p", { class: "hint-step", text: "Slower:" }),
            el("button", { type: "button", class: "secondary", onclick: slow }, "Play slowly")));
          slow();
        } else if (hint === 2) {
          hintBox.append(el("p", { class: "hint-step" }, "In kana: ", el("span", { lang: "ja", class: "hint-jp", text: item.jp })));
        } else if (hint === 3) {
          const first = item.en.replace(/^\W+/, "").charAt(0).toUpperCase();
          hintBox.append(el("p", { class: "hint-step", text: `The meaning starts with "${first}"` }));
        }
        return true;
      }
      const replay = el("button", { type: "button", class: "secondary", onclick: () => play(item.jp, voice) }, "Play again", kbd("R"));

      if (name === "imitate") {
        const result = el("div", { class: "result", "aria-live": "polite" });
        const hold = holdControl("Hold and say it", async (blob, ext) => {
          result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
          try {
            const r = await api("/api/course/check_text", { method: "POST", body: audioForm(blob, ext, { target: item.jp, strict: 1 }) });
            const judged = r.credit ?? (r.band === "good" ? 1 : r.band === "close" ? 0.5 : 0);
            if (judged === 0 && easier()) {
              result.replaceChildren(el("p", { class: "status", text: "Here's some help. Try again." }));
              return;
            }
            record(judged);
          } catch (err) {
            result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
          }
        }, showProblem(result));
        frame({
          title: `Placement: ${info.title}`, index: n, total: 8,
          body: el("div", { class: "card-body" }, el("p", { class: "prompt", text: info.prompt }),
            el("div", { class: "lesson-play" }, replay), hintBox, hold, micRow(), result),
          actions: [el("button", { type: "button", class: "secondary", onclick: () => { if (!easier()) record(0); } }, "Can't say it"),
            el("button", { type: "button", class: "secondary", onclick: results }, "Skip this part")],
          hold,
        });
      } else {
        const input = el("input", { type: "text", class: "produce-input placement-input",
          placeholder: "In English (empty = don't know)", autocomplete: "off", spellcheck: "true" });
        const status = el("p", { class: "status" });
        const submit = async () => {
          const answer = input.value.trim();
          if (!answer) {
            if (!easier()) return record(0);
            input.focus();
            return;
          }
          input.disabled = true;
          status.textContent = "…";
          let judged;
          try {
            judged = (await postJson("/api/course/placement/judge", { jp: item.jp, expected: item.en, answer, kind: name })).score;
          } catch (err) {
            input.disabled = false;
            status.textContent = String(err.message || err);
            return;
          }
          status.textContent = "";
          if (judged === 0 && easier()) {
            // A miss is treated like "don't know": one step easier, same item.
            input.disabled = false;
            input.value = "";
            input.focus();
            return;
          }
          record(judged);
        };
        frame({
          title: `Placement: ${info.title}`, index: n, total: 8,
          body: el("div", { class: "card-body" }, el("p", { class: "prompt", text: info.prompt }),
            el("div", { class: "lesson-play" }, replay), hintBox,
            el("form", { class: "produce-form", onsubmit: (e) => { e.preventDefault(); submit(); } }, input,
              el("button", { type: "submit", class: "secondary" }, "Next")),
            status),
          actions: [],
        });
        setTimeout(() => input.focus(), 0);
      }
      keys.replay = () => play(item.jp, voice);
      play(item.jp, voice);
    }

    function imitateIntro() {
      frame({
        title: "Placement: Repeat after me",
        body: el("div", { class: "card-body" },
          el("p", { class: "lesson-note", text: "Last part: hear a phrase, then hold the bar and say it back. It measures how much you can take in and reproduce." }),
          micRow()),
        actions: [el("button", { type: "button", class: "secondary", onclick: results }, "Skip (no microphone)"),
          primaryButton("Start", () => skill("imitate"))],
        primary: () => skill("imitate"),
      });
    }

    async function results() {
      let r;
      try {
        r = await postJson("/api/course/placement/summary", { histories, kana: kanaAnswers });
      } catch (err) { return fail(err); }
      const describe = (e) => (e.level < 0.75 ? "before unit 1"
        : `about unit ${Math.round(e.level)}${e.low !== e.high ? ` (range ${Math.max(0, e.low)}–${e.high})` : ""}`);
      const rows = [];
      for (const [k, e] of Object.entries(r.skills)) {
        const ch = (r.channels || {})[k];
        if (ch) {
          const noun = k === "words" ? "Words" : "Sentences";
          rows.push(el("tr", {}, el("th", { text: `${noun} by ear` }), el("td", { text: describe(ch.ear) })));
          rows.push(el("tr", {}, el("th", { text: `${noun} once shown in kana` }), el("td", { text: describe(ch.read) })));
        } else {
          rows.push(el("tr", {}, el("th", { text: SKILL_INFO[k].title }), el("td", { text: describe(e) })));
        }
      }
      const kanaRows = Object.entries(r.kana).map(([g, k]) => el("tr", {},
        el("th", { text: { hiragana: "Hiragana", "hiragana+": "Voiced and blended hiragana", katakana: "Katakana" }[g] }),
        el("td", { text: `${k.right} of ${k.of}${k.passed ? " (lessons skipped)" : ""}` })));
      const start = r.known_units
        ? `Start at unit ${r.start_unit}${unitTitle(r.start_unit) ? `: ${unitTitle(r.start_unit)}` : ""}. Units 1–${r.known_units} are marked as known; their phrases and words come up in reviews over the next two weeks, so anything shaky gets caught.`
        : "Start at unit 1. The early units are where your answers put you.";
      const apply = async () => {
        try {
          await postJson("/api/course/placement/apply", { histories, kana: kanaAnswers });
        } catch (err) { return fail(err); }
        showHome();
      };
      const gapNote = r.listening_gap >= 1.5
        ? el("p", { class: "lesson-note", text: `You understand more when you can see the kana than by ear (about ${Math.round(r.listening_gap)} units more). `
            + "The course starts at your listening level, and the "
            + (r.reading_only.length ? `${r.reading_only.length} word${r.reading_only.length === 1 ? "" : "s"} you only got from the kana come up as listening reviews first.` : "gap closes as you review by ear.") })
        : null;
      frame({
        title: "Placement result",
        body: el("div", { class: "card-body" },
          el("table", { class: "stats-table" }, el("tbody", {}, rows, kanaRows)),
          el("p", { class: "lesson-note", text: start }),
          gapNote,
          el("p", { class: "status", text: "Chat's difficulty is set from these results too. You can retake the test any time from Settings → Level." })),
        actions: [el("button", { type: "button", class: "secondary", onclick: showHome }, "Don't apply"), primaryButton("Apply", apply)],
        primary: apply,
      });
    }

    function fail(err) {
      frame({
        title: "Placement test",
        body: el("p", { class: "verdict off", text: String(err.message || err) }),
        actions: [primaryButton("Back", showHome)],
        primary: showHome,
      });
    }

    intro();
  }
  window.KaiwaPlacement = () => runPlacement();

  // ---------- new phrases ----------
  function runLearn(unit) {
    const spot = `learn:${unit.id}`;
    const phrases = unit.phrases;
    let i = Math.min(spotIn(spot), phrases.length - 1);
    prefetch(phrases.map((p) => [p.jp, {}]));
    const spoken = new Set();

    function show() {
      keepSpot(spot, i);
      const p = phrases[i];
      const say = voiceCycler(p.jp);
      const result = el("div", { class: "result", "aria-live": "polite" });
      const hold = holdControl("Hold and say it", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          result.replaceChildren(...[verdictLine(r.band), heardLine("Sounded like ", r.heard), diffLine(r.diff),
            r.tip ? el("p", { class: "tip", text: r.tip }) : null].filter(Boolean));
          noteResult({ said: r.heard, band: r.band, tip: r.tip });
          if (!spoken.has(p.id)) {
            spoken.add(p.id); // repeating right after hearing it: no timing, just whether it came out
            lessonGrade(`${p.id}:speak`, { correct: r.band !== "off", band: r.band, fmt: "phrase:speak:learn" });
          }
          if (r.band !== "good") play(p.jp);
          promoteNext();
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        }
      }, showProblem(result));
      const last = i === phrases.length - 1;
      const actions = [];
      if (i > 0) actions.push(el("button", { type: "button", class: "secondary", onclick: () => { i -= 1; show(); } }, "Back"));
      // Saying it is the point of this card, so Next stays quiet until it has been said once.
      // Enter still moves on: nothing is blocked, only the emphasis changes.
      const nextBtn = primaryButton(last ? "Quick check" : "Next", next);
      const promoteNext = () => nextBtn.classList.remove("secondary");
      if (!spoken.has(p.id)) nextBtn.classList.add("secondary");
      actions.push(nextBtn);
      frame({
        title: `New phrases, unit ${unit.number}`,
        index: i,
        total: phrases.length,
        body: el("div", { class: "card-body" }, phraseBlock(p),
          el("div", { class: "lesson-play" },
            el("button", { class: "secondary", type: "button", onclick: say, "data-tip": "Each play is a different voice, so you get used to more than one speaker" }, "Play", kbd("R")),
            el("button", { class: "secondary", type: "button", onclick: () => play(p.jp, { slow: true }) }, "Slow")),
          hold, micRow(), result),
        actions,
        primary: next,
        hold,
        ask: { screen: "new phrase", jp: p.jp, en: p.en, note: p.note },
      });
      keys.replay = say;
      say();
    }
    function next() {
      if (i < phrases.length - 1) {
        i += 1;
        return show();
      }
      return check();
    }

    // Straight after meeting them: can you catch each one by ear? Misses come back once.
    function check() {
      const queue = shuffle(phrases).map((p) => ({ p, retried: false }));
      let n = 0;
      function ask() {
        if (n >= queue.length) return finish();
        const { p, retried } = queue[n];
        const shown = performance.now();
        const nextBtn = primaryButton("Next", advance);
        nextBtn.hidden = true;
        const after = el("div", { class: "result" });
        function advance() { n += 1; ask(); }
        frame({
          title: `Quick check, unit ${unit.number}`, index: Math.min(n, phrases.length - 1), total: phrases.length,
          ask: { screen: "phrase check", jp: p.jp, en: p.en, note: p.note },
          body: el("div", { class: "card-body" },
            el("p", { class: "prompt", text: "What did you hear?" }),
            el("div", { class: "lesson-play" },
              el("button", { class: "secondary", type: "button", onclick: () => play(p.jp) }, "Play again", kbd("R"))),
            choiceBlock({
              options: shuffle(phrases.map((x) => x.en)), answer: p.en,
              onAnswer: async (right) => {
                if (!retried) lessonGrade(`${p.id}:listen`, { correct: right, ms: Math.round(performance.now() - shown), fmt: "phrase:listen" });
                if (!right && !queue[n].retried) queue.push({ p, retried: true });
                if (right) { const here = onThisScreen(); await wait(600); if (here()) advance(); }
                else {
                  after.replaceChildren(phraseBlock(p));
                  nextBtn.hidden = false;
                  keys.primary = advance;
                }
              },
            }),
            after),
          actions: [nextBtn],
        });
        keys.primary = null;
        keys.replay = () => play(p.jp);
        play(p.jp);
      }
      ask();
    }
    function finish() {
      return saveThen("/api/course/step", { unit_id: unit.id, step: "learn" }, continuePlan);
    }
    show();
  }

  // ---------- listen ----------
  function runListen(unit) {
    listenView({
      title: `Listen, unit ${unit.number}`,
      dialogue: unit.dialogue,
      questions: unit.questions,
      doneLabel: "Continue",
      onDone: () => saveThen("/api/course/step", { unit_id: unit.id, step: "listen" }, continuePlan),
    });
  }

  async function runExtraListening(autoplay = false) {
    track("open", { activity: "extra_listening", next: autoplay });
    frame({ title: "Extra listening", body: el("p", { class: "pending", text: "Writing something at your level…" }) });
    let story;
    try {
      story = await api("/api/course/story", { method: "POST" });
    } catch (err) {
      frame({
        title: "Extra listening",
        body: el("p", { class: "verdict off", text: String(err.message || err) }),
        actions: [primaryButton("Try again", () => runExtraListening())],
        primary: () => runExtraListening(),
      });
      return;
    }
    listenView({
      title: "Extra listening",
      dialogue: { scene: story.replay ? `Again: ${story.scene}` : story.scene, lines: story.lines, form: story.form, known: story.known_share },
      questions: story.questions,
      doneLabel: "Next one",
      onDone: () => runExtraListening(true),
      autoplay,
      remember: true,
    });
  }

  /**
   * A listening exercise laid out as a message thread of voice bubbles.
   * Lines arrive one by one as they're spoken. Text is per line and only offered
   * after one full listen (Japanese first, English on a second click); questions
   * appear after that first listen too, and a miss offers another listen, not text.
   */
  function listenView({ title, dialogue: d, questions: qs, doneLabel, onDone, autoplay = false, remember = false }) {
    // Up to four speakers: A and C on the left, B and D on the right, each its own voice.
    const who = (line) => ("abcd".includes(line.who) && line.who ? line.who : "a");
    const side = (line) => ("bd".includes(who(line)) ? "right" : "left");
    const voice = (line) => ({ voice: who(line) });
    prefetch(d.lines.map((line) => [line.jp, voice(line)]));
    const here = () => thread.isConnected;
    let playing = false;
    let heard = 0;
    let peeked = false;
    let slow = false;
    const lineVoice = (line) => ({ ...voice(line), slow });
    let revealed = 0; // how many bubbles have arrived in the thread
    const answered = new Map();
    const linePlays = d.lines.map(() => 0);
    const peeks = d.lines.map(() => 0); // 0 none, 1 Japanese, 2 English
    const firstPicks = new Map();
    const finishListen = () => {
      track("listen", {
        scene: d.scene || "", form: d.form || "dialogue", unit: remember ? null : title,
        full_plays: heard, line_plays: linePlays, by_ear: !peeked,
        peeks: peeks.map((level, i) => (level ? { line: i, level, jp: d.lines[i].jp } : null)).filter(Boolean),
        questions: qs.map((q, qi) => ({ q: q.q, right: answered.get(qi), first_pick: firstPicks.get(qi) })),
      });
      return onDone();
    };

    const thread = el("div", { class: "thread", "data-empty": "Press play and just listen." });
    const bubbles = d.lines.map((line, idx) => {
      const textBox = el("div", { class: "bubble-text", hidden: true });
      let level = 0; // 0 voice only, 1 + Japanese, 2 + English
      const peek = el("button", { class: "bubble-peek", type: "button", hidden: true, "aria-label": "Show text",
        "data-tip": "Show this line", onclick: (e) => {
          e.stopPropagation();
          level = Math.min(2, level + 1);
          peeked = true;
          peeks[idx] = level;
          textBox.hidden = false;
          textBox.replaceChildren(...[
            el("span", { class: "bubble-jp", lang: "ja", text: line.jp }),
            line.gloss ? el("span", { class: "bubble-gloss", text: line.gloss }) : null,
            level >= 2 ? el("span", { class: "bubble-en", text: line.en }) : null,
          ].filter(Boolean));
          peek.hidden = level >= 2;
          peek.dataset.tip = "Show the meaning";
          peek.textContent = "EN";
        } }, "あ");
      const bubble = el("div", { class: "bubble-voice", role: "button", tabindex: "0", "aria-label": "Play this line",
        onclick: () => playLine(idx), onkeydown: (e) => { if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); playLine(idx); } } },
        el("span", { class: "bubble-icon", "aria-hidden": "true" }),
        waveform(line.jp),
        textBox);
      const row = el("div", { class: `msg msg-${side(line)} who-${who(line)}`, hidden: true },
        el("span", { class: "msg-avatar", text: who(line).toUpperCase() }),
        bubble, peek);
      return { row, bubble, peek };
    });
    const typing = el("div", { class: "msg msg-left typing", hidden: true },
      el("span", { class: "msg-avatar" }), el("span", { class: "typing-dots" }, el("i"), el("i"), el("i")));
    thread.append(...bubbles.map((b) => b.row), typing);

    function waveform(text) {
      // Bars sized from the line itself: longer lines, longer messages.
      const n = Math.max(8, Math.min(30, Math.round(text.length * 1.4)));
      const bars = [];
      for (let i = 0; i < n; i++) {
        const c = text.charCodeAt(i % text.length);
        bars.push(el("i", { style: `--h:${30 + ((c * 37 + i * 53) % 70)}%` }));
      }
      return el("span", { class: "wave" }, bars);
    }

    function listened(since, scene = "") {
      const seconds = (Date.now() - since) / 1000;
      postJson("/api/course/listened", { seconds, scene }).catch(() => {});
    }

    async function playLine(idx) {
      if (playing) return;
      const b = bubbles[idx];
      const since = Date.now();
      linePlays[idx] += 1;
      b.bubble.classList.add("speaking");
      await play(d.lines[idx].jp, lineVoice(d.lines[idx]));
      b.bubble.classList.remove("speaking");
      listened(since);
    }

    async function playAll() {
      if (playing) return;
      playing = true;
      playBtn.disabled = true;
      const since = Date.now();
      for (let idx = 0; idx < d.lines.length; idx++) {
        if (!here()) return;
        const b = bubbles[idx];
        if (idx >= revealed) {
          // Lines arrive as they're spoken, like a conversation happening now.
          typing.className = `msg msg-${side(d.lines[idx])} typing`;
          typing.hidden = false;
          thread.append(typing);
          await wait(450);
          typing.hidden = true;
          b.row.hidden = false;
          revealed = idx + 1;
          b.row.scrollIntoView({ block: "nearest" });
        }
        b.bubble.classList.add("speaking");
        await play(d.lines[idx].jp, lineVoice(d.lines[idx]));
        b.bubble.classList.remove("speaking");
        await wait(350);
      }
      playing = false;
      playBtn.disabled = false;
      heard += 1;
      listened(since, remember && heard === 1 ? d.scene || "" : "");
      playBtn.firstChild.textContent = "Play again";
      heardNote.textContent = heard === 1 ? "Heard once" : `Heard ${heard} times`;
      if (heard === 1) {
        // Only now: per-line text, and the questions.
        for (const b of bubbles) b.peek.hidden = false;
        questionsBox.hidden = false;
      }
    }

    const playBtn = el("button", { type: "button", onclick: playAll }, d.form === "story" ? "Play the story" : "Play the conversation", kbd("R"));
    const heardNote = el("span", { class: "heard-note" });
    const slowBtn = el("button", { type: "button", class: "secondary", "aria-pressed": "false", "data-tip": "Everyone speaks slower. Real speed is the goal, but this helps you catch the shape of it first.",
      onclick: () => { slow = !slow; slowBtn.setAttribute("aria-pressed", String(slow)); slowBtn.classList.toggle("pressed", slow); } }, "Slower");

    const doneBtn = primaryButton(doneLabel, finishListen, { disabled: true });
    const shadowBtn = el("button", { type: "button", class: "secondary", hidden: true,
      "data-tip": "Repeat each line right after hearing it. Good for rhythm and for catching words at speed.",
      onclick: () => runShadow(d.lines, voice, finishListen) }, "Say it with them");
    const speakers = [...new Set(d.lines.map(who))];
    const roleBtn = speakers.length >= 2 ? el("button", { type: "button", class: "secondary", hidden: true,
      "data-tip": "Now you're one of them: the other person speaks, you say your lines from their meaning. Your real answers don't need to be word for word.",
      onclick: () => runRole(d.lines, who, voice, finishListen) }, "Take a part") : null;
    const byEar = el("p", { class: "by-ear", hidden: true, text: "Caught by ear." });
    const questionsBox = el("div", { class: "questions", hidden: true },
      el("h3", { class: "questions-title", text: "Did you catch it?" }),
      qs.map((q, qi) => {
        const feedback = el("p", { class: "verdict" });
        const again = el("button", { class: "secondary", type: "button", hidden: true, onclick: playAll }, "Listen again");
        const choices = el("div", { class: "choices" }, q.choices.map((choice, ci) =>
          el("button", {
            class: "secondary", type: "button",
            onclick: (e) => {
              const right = ci === q.answer;
              answered.set(qi, right);
              firstPicks.set(qi, choice);
              for (const b of choices.children) b.disabled = true;
              e.currentTarget.classList.add(right ? "right" : "wrong");
              if (!right) choices.children[q.answer].classList.add("right");
              feedback.className = "verdict " + (right ? "good" : "off");
              feedback.textContent = right ? "Right." : "Not quite.";
              again.hidden = right;
              if (answered.size === qs.length) {
                doneBtn.disabled = false;
                shadowBtn.hidden = false;
                if (roleBtn) roleBtn.hidden = false;
                keys.primary = finishListen;
                byEar.hidden = peeked || [...answered.values()].some((v) => !v);
              }
            },
          }, choice)));
        return el("div", { class: "question" }, el("p", { class: "question-q", text: q.q }), choices,
          el("div", { class: "verdict-row" }, feedback, again));
      }),
      byEar);

    frame({
      title,
      ask: { screen: "listening", scene: d.scene, lines: d.lines.map((l) => `${l.who}: ${l.jp} (${l.en})`), questions: qs.map((q) => q.q) },
      body: el("div", { class: "card-body listen" },
        d.scene ? el("p", { class: "prompt", text: d.scene }) : null,
        d.known ? el("p", { class: "status", text: `Built from what you know: about ${Math.round(d.known * 100)}% should be familiar.` }) : null,
        el("div", { class: "listen-bar" }, playBtn, slowBtn, heardNote),
        thread,
        questionsBox,
      ),
      actions: [roleBtn, shadowBtn, doneBtn].filter(Boolean),
    });
    keys.replay = playAll;
    if (autoplay) playAll();
  }

  /**
   * Take one speaker's part: the other voice speaks, and you say your line from its
   * meaning. The step between repeating and a free conversation: real timing and a real
   * partner, with the words still known. No LLM, so it always works.
   */
  function runRole(lines, who, voice, onDone) {
    const mine = who(lines[0]) === "a" && lines.filter((l) => who(l) === "a").length >= 2 ? "a" : who(lines[lines.length - 1]);
    const lineFor = lines.filter((l) => who(l) === mine);
    let i = 0;
    let at = 0;
    track("shadow", { role: mine, lines: lineFor.length });
    const shown = [];
    async function step() {
      if (at >= lines.length) return end();
      const line = lines[at];
      if (who(line) !== mine) {
        shown.push(line);
        draw(null);
        const here = onThisScreen();
        await play(line.jp, voice(line));
        await wait(250);
        if (!here()) return undefined;
        at += 1;
        return step();
      }
      return draw(line);
    }
    function draw(line) {
      const result = el("div", { class: "result", "aria-live": "polite" });
      const answer = el("p", { class: "phrase-jp", lang: "ja", hidden: true, text: line ? line.jp : "" });
      const onward = () => { shown.push(line); at += 1; i += 1; step(); };
      const nextBtn = primaryButton("Next", onward);
      nextBtn.hidden = true;
      const reveal = () => {
        answer.hidden = false;
        nextBtn.hidden = false;
        keys.primary = onward;
        play(line.jp, voice(line));
      };
      const hold = line ? holdControl("Hold and say your line", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check_text", { method: "POST", body: audioForm(blob, ext, { target: line.jp.slice(0, 80) }) });
          result.replaceChildren(...[verdictLine(r.band), heardLine("Sounded like ", r.heard), diffLine(r.diff)].filter(Boolean));
          reveal();
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        }
      }, showProblem(result)) : null;
      const past = el("div", { class: "role-log" }, shown.map((l) => el("p", { class: who(l) === mine ? "role-mine" : "role-other", lang: "ja", text: l.jp })));
      frame({
        title: "Your part", index: i, total: lineFor.length,
        ask: line ? { screen: "role play", jp: line.jp, en: line.en } : { screen: "role play" },
        body: el("div", { class: "card-body" }, past,
          line ? [el("p", { class: "prompt", text: "Your turn. Say:" }), el("p", { class: "prompt-en", text: line.en }), answer, hold, micRow(), result] : el("p", { class: "status", text: "Listen…" })),
        actions: line
          ? [el("button", { type: "button", class: "secondary", onclick: reveal }, "Show me"), nextBtn]
          : [],
        hold,
      });
    }
    function end() {
      frame({
        title: "Your part",
        body: el("div", { class: "card-body" }, el("h3", { class: "end-title", text: "You held up your side." }),
          el("p", { class: "prompt", text: "That's what a real exchange feels like. Doing it again from memory is worth it." })),
        actions: [el("button", { type: "button", class: "secondary", onclick: () => runRole(lines, who, voice, onDone) }, "Again"), primaryButton("Continue", onDone)],
        primary: onDone,
      });
    }
    step();
  }

  /** Shadowing: hear a line, say it straight back, see which sounds didn't come through. */
  function runShadow(lines, voice, onDone) {
    let i = 0;
    track("shadow", { lines: lines.length });
    function show() {
      if (i >= lines.length) return onDone();
      const line = lines[i];
      const say = () => play(line.jp, voice(line));
      const result = el("div", { class: "result", "aria-live": "polite" });
      const next = () => { i += 1; show(); };
      const hold = holdControl("Hold and say it back", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check_text", { method: "POST", body: audioForm(blob, ext, { target: line.jp.slice(0, 80) }) });
          result.replaceChildren(...[verdictLine(r.band), heardLine("Sounded like ", r.heard), diffLine(r.diff)].filter(Boolean));
          if (r.band !== "good") say();
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        }
      }, showProblem(result));
      frame({
        title: "Say it with them", index: i, total: lines.length,
        ask: { screen: "shadowing", jp: line.jp, en: line.en },
        body: el("div", { class: "card-body" },
          el("p", { class: "prompt", text: "Copy the rhythm, not just the words." }),
          el("p", { class: "phrase-jp", lang: "ja", text: line.jp }),
          el("p", { class: "phrase-en", text: line.en }),
          playRow(line.jp, voice(line)),
          hold, micRow(), result),
        actions: [
          el("button", { type: "button", class: "secondary", onclick: onDone }, "Finish now"),
          primaryButton(i === lines.length - 1 ? "Finish" : "Next line", next)],
        primary: next,
        hold,
      });
      keys.replay = say;
      say();
    }
    show();
  }

  // ---------- talk practice ----------
  /**
   * A few spoken turns with a partner in a small scene. After each turn: what you
   * said and meant, one fix and a natural version, then the partner answers.
   * A suggested reply is always one click away. Partner lines are voice first;
   * their text is one click (Japanese) or two (English) away, as in listening.
   */
  async function runTalk(missionId) {
    const mission = typeof missionId === "string" ? missionId : null; // a click handler passes an event
    const talkTitle = mission ? "Mission" : "Talk practice";
    track("open", { activity: mission ? "mission" : "talk", unit: mission });
    frame({ title: talkTitle, body: el("p", { class: "pending", text: "Setting the scene…" }) });
    let scene;
    try {
      scene = mission ? await api(`/api/course/mission/${encodeURIComponent(mission)}`) : await api("/api/course/talk/start", { method: "POST" });
    } catch (err) {
      const again = () => runTalk(mission);
      frame({
        title: talkTitle,
        body: el("p", { class: "verdict off", text: String(err.message || err) }),
        actions: [primaryButton("Try again", again)],
        primary: again,
      });
      return;
    }
    const PARTNER = { voice: "b" };
    const MAX_TRIES = 10; // retries included; the scene closes on its own long before
    const history = [];
    const fixes = []; // corrected versions from this talk, to look back at once it's over
    let suggest = scene.suggest;
    let tries = 0;
    let pending = false;
    let turnShown = Date.now();
    let hintUsed = false;
    let finished = false;
    prefetch([[scene.opener, PARTNER]]);

    const thread = el("div", { class: "thread talk-thread" });
    function partnerLine(jp, en) {
      const textBox = el("div", { class: "bubble-text", hidden: true });
      let level = 0;
      const peek = el("button", { class: "bubble-peek", type: "button", "aria-label": "Show text", "data-tip": "Show this line",
        onclick: (e) => {
          e.stopPropagation();
          level = Math.min(2, level + 1);
          textBox.hidden = false;
          textBox.replaceChildren(el("span", { class: "bubble-jp", lang: "ja", text: jp }),
            level >= 2 && en ? el("span", { class: "bubble-en", text: en }) : "");
          peek.hidden = level >= 2 || !en;
          peek.dataset.tip = "Show the meaning";
          peek.textContent = "EN";
        } }, "あ");
      const bubble = el("div", { class: "bubble-voice", role: "button", tabindex: "0", "aria-label": "Play this line",
        onclick: () => say(), onkeydown: (e) => { if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); say(); } } },
        el("span", { class: "bubble-icon", "aria-hidden": "true" }),
        el("span", { class: "wave" }, [...jp].slice(0, 24).map((c, i) => el("i", { style: `--h:${30 + ((c.charCodeAt(0) * 37 + i * 53) % 70)}%` }))),
        textBox);
      async function say() {
        bubble.classList.add("speaking");
        await play(jp, PARTNER);
        bubble.classList.remove("speaking");
      }
      history.push({ who: "them", jp, en });
      thread.append(el("div", { class: "msg msg-left who-b" },
        el("span", { class: "msg-avatar", text: (scene.partner || "B").charAt(0) }), bubble, peek));
      keys.replay = say;
      return say;
    }
    function myLine(heard, verdict) {
      const cls = { great: "good", ok: "close", retry: "off" }[verdict] || "off";
      thread.append(el("div", { class: "msg msg-right who-a" },
        el("span", { class: "msg-avatar", text: "You" }),
        el("div", { class: `bubble-mine mine-${cls}`, lang: "ja", text: heard })));
    }

    const feedback = el("div", { class: "result", "aria-live": "polite" });
    const hintBox = el("div", { class: "hint", hidden: true });
    const hintBtn = el("button", { class: "secondary hint-toggle", type: "button", onclick: () => {
      hintBox.hidden = !hintBox.hidden;
      if (!hintBox.hidden) {
        if (!hintUsed) track("talk_hint", { suggest, turn: tries + 1 });
        hintUsed = true;
        play(suggest);
      }
    } }, "Show a hint");
    function setSuggest(text) {
      suggest = text;
      hintBox.hidden = true;
      hintBtn.hidden = !text;
      hintBox.replaceChildren(el("p", { class: "model-label", text: "You could say" }),
        el("p", { lang: "ja", text: text }),
        el("button", { class: "secondary", type: "button", onclick: () => play(text) }, "Play"));
    }

    function renderFeedback(r) {
      noteResult({ said: r.heard, verdict: r.verdict, model: r.model, tip: r.tip });
      const label = { great: "Natural.", ok: "Understood. One thing to fix.", retry: "Not understood. Try again." }[r.verdict];
      const cls = { great: "good", ok: "close", retry: "off" }[r.verdict];
      const sameAsSaid = normalizeKana(r.model) === normalizeKana(r.heard);
      feedback.replaceChildren(...[
        el("p", { class: "verdict " + cls, text: label }),
        r.said_en ? heardLine("You said ", r.heard, `, which means “${r.said_en}”`) : null,
        r.model && !sameAsSaid ? el("div", { class: "model" },
          el("p", { class: "model-label", text: r.verdict === "great" ? "Also natural" : "Try saying" }),
          el("p", { class: "model-jp", lang: "ja", text: r.model }),
          el("button", { class: "secondary", type: "button", onclick: () => play(r.model) }, "Play")) : null,
        r.tip ? el("p", { class: "tip", text: r.tip }) : null,
      ].filter(Boolean));
    }

    async function send(fields) {
      if (pending) return;
      pending = true;
      hold.disabled = true;
      feedback.replaceChildren(el("p", { class: "pending", text: "Listening to your answer…" }));
      const form = fields instanceof FormData ? fields : new FormData();
      form.append("scene", JSON.stringify(scene));
      form.append("history", JSON.stringify(history.map(({ who, jp }) => ({ who, jp }))));
      form.append("ms", String(Date.now() - turnShown));
      form.append("hint_open", hintUsed ? "true" : "false");
      let r;
      try {
        r = await api("/api/course/talk/turn", { method: "POST", body: form });
      } catch (err) {
        feedback.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        pending = false;
        hold.disabled = false;
        return;
      }
      tries += 1;
      typed.value = "";
      if (r.verdict !== "great" && r.model && normalizeKana(r.model) !== normalizeKana(r.heard) && !fixes.some((f) => f.jp === r.model)) {
        fixes.push({ jp: r.model, en: r.model_en || "", tip: r.tip });  // what the corrected line says, not what was said
      }
      myLine(r.heard, r.verdict);
      renderFeedback(r);
      if (r.verdict === "retry") {
        // The partner asks again; the failed exchange stays out of the history.
        thread.append(el("div", { class: "msg msg-left who-b talk-reask" },
          el("span", { class: "msg-avatar", text: (scene.partner || "B").charAt(0) }),
          el("div", { class: "bubble-mine", lang: "ja", text: r.reply })));
        play(r.reply, PARTNER);
      } else {
        history.push({ who: "me", jp: r.heard });
        partnerLine(r.reply, r.reply_en)();
      }
      thread.lastChild.scrollIntoView({ block: "nearest" });
      setSuggest(r.suggest);
      turnShown = Date.now();
      hintUsed = false;
      pending = false;
      hold.disabled = false;
      if (r.done || tries >= MAX_TRIES) finish();
    }

    const hold = holdControl("Hold and answer", (blob, ext) => send(audioForm(blob, ext, {})), showProblem(feedback));
    const typed = el("input", { type: "text", maxlength: "120", placeholder: "Or type your answer", lang: "ja" });
    const typedForm = el("form", { class: "typed", onsubmit: (e) => {
      e.preventDefault();
      if (!typed.value.trim()) return;
      const f = new FormData();
      f.append("text", typed.value.trim());
      send(f);
    } }, typed, el("button", { class: "secondary", type: "submit" }, "Send"));
    const controls = el("div", { class: "talk-controls" }, hold, micRow(), typedForm, hintBtn, hintBox);
    const leave = mission ? () => continuePlan() : () => runTalk();
    const nextBtn = primaryButton(mission ? "Continue" : "Another conversation", leave, { disabled: true });

    function finish() {
      finished = true;
      track("talk_end", { goal: scene.goal, tries, done: true });
      controls.hidden = true;
      thread.after(el("p", { class: "by-ear", text: mission ? `Mission done: ${scene.goal} Click any line to hear it again.` : "Conversation done. Click any line to hear it again." }));
      if (mission) postJson("/api/course/mission_done", { unit_id: mission }).catch(() => {});
      if (fixes.length) {
        feedback.replaceChildren(el("div", { class: "talk-fixes" },
          el("p", { class: "model-label", text: "Worth keeping from this talk" }),
          fixes.map((f) => el("div", { class: "ask-example" },
            el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(f.jp) }, "▶"),
            el("span", { lang: "ja", text: f.jp }),
            el("span", { class: "ask-example-en", text: f.en }),
            f.en && f.jp.length <= 40 && !/[一-鿿]/.test(f.jp) ? keepButton(f.jp, f.en) : null))));
      }
      nextBtn.disabled = false;
      keys.primary = leave;
      keys.hold = null;
    }

    frame({
      title: talkTitle,
      ask: { screen: "talk practice", scene: scene.scene, goal: scene.goal, partner: scene.partner },
      body: el("div", { class: "card-body listen" },
        el("p", { class: "situation", text: scene.scene }),
        el("p", { class: "prompt talk-goal", text: `Your goal: ${scene.goal}` }),
        thread,
        feedback,
        controls),
      actions: [el("button", { type: "button", class: "secondary", onclick: () => {
        if (!finished) track("talk_end", { goal: scene.goal, tries, done: false });
        showHome();
      } }, "End"), nextBtn],
      hold,
    });
    setSuggest(suggest);
    partnerLine(scene.opener, scene.opener_en)();
  }

  /** For "is the natural version the same as what you said": kana and punctuation only. */
  function normalizeKana(s) {
    return String(s || "").replace(/[、。！？!?\s「」]/g, "");
  }

  // ---------- kana lesson ----------
  function runKana(lesson) {
    const items = lesson.kana;
    const title = lesson.script === "katakana" ? "Katakana" : "Hiragana";
    prefetch([...items.map((k) => [k.char, {}]), ...lesson.words.map((w) => [w.jp, {}])]);

    // 1. Meet each character (a rules-only lesson goes straight to the note).
    const spot = `kana:${lesson.id}`;
    let i = Math.min(spotIn(spot), Math.max(0, items.length - 1));
    function intro() {
      if (!items.length) return note();
      keepSpot(spot, i);
      const k = items[i];
      const last = i === items.length - 1;
      const actions = [];
      if (i > 0) actions.push(el("button", { type: "button", class: "secondary", onclick: () => { i -= 1; intro(); } }, "Back"));
      const go = () => { if (last) note(); else { i += 1; intro(); } };
      actions.push(primaryButton("Next", go));
      frame({
        title: `${title}: ${lesson.title}`, index: i, total: items.length,
        body: el("div", { class: "card-body kana-intro" },
          el("p", { class: "kana-big", lang: "ja", text: k.char }),
          el("p", { class: "kana-ro", text: k.ro }),
          k.hook ? el("p", { class: "kana-hook", text: k.hook }) : null,
          playRow(k.char),
          i === 0 ? el("p", { class: "phrase-note", text: lesson.note }) : null),
        actions, primary: go,
        ask: { screen: "kana", jp: k.char, reading: k.ro, note: lesson.note },
      });
      keys.replay = () => play(k.char);
      play(k.char);
    }
    function note() {
      if (items.length) return drill();
      frame({
        title: `${title}: ${lesson.title}`,
        body: el("div", { class: "card-body" }, el("p", { class: "lesson-note", text: lesson.note })),
        actions: [primaryButton("Practice", drill)], primary: drill,
      });
    }

    // 2. Drill: each new character twice (see → sound, hear → character), wrong ones come back.
    function drill() {
      if (!items.length) return words();
      const pool = [...items, ...lesson.known];
      const queue = shuffle([
        ...items.map((k) => ({ k, mode: "read" })),
        ...items.map((k) => ({ k, mode: "hear" })),
      ]);
      let n = 0;
      const total = queue.length;
      const graded = new Set();
      function ask() {
        if (n >= queue.length) return words();
        const { k, mode } = queue[n];
        const shown = performance.now();
        const nextBtn = primaryButton("Next", advance);
        nextBtn.hidden = true;
        const help = el("div", { class: "result" });
        function advance() { n += 1; ask(); }
        const block = mode === "read"
          ? choiceBlock({
              options: choicesFor(k.ro, pool.filter((x) => x.ro !== k.ro).map((x) => x.ro), 4, alikeIn(k, pool).map((x) => x.ro)),
              answer: k.ro,
              onAnswer: onAnswer,
            })
          : choiceBlock({
              options: choicesFor(k.char, pool.filter((x) => x.ro !== k.ro).map((x) => x.char), 4, alikeIn(k, pool).map((x) => x.char)),
              answer: k.char, jp: true,
              onAnswer: onAnswer,
            });
        async function onAnswer(right) {
          play(k.char);
          if (mode === "read" && !graded.has(k.char)) {
            graded.add(k.char);
            lessonGrade(`kana.${k.char}:read`, { correct: right, ms: Math.round(performance.now() - shown), fmt: "kana:choice" });
          }
          if (!right) { queue.push(queue[n]); help.replaceChildren(kanaHelp(k, pool)); }
          if (right) { const here = onThisScreen(); await wait(600); if (here()) advance(); }
          else { nextBtn.hidden = false; keys.primary = advance; }
        }
        frame({
          title: `${title}: practice`, index: Math.min(n, total - 1), total,
          ask: { screen: "kana drill", jp: mode === "read" ? k.char : "", note: lesson.note },
          body: el("div", { class: "card-body" },
            el("p", { class: "prompt", text: mode === "read" ? "How do you read this?" : "Which one did you hear?" }),
            mode === "read"
              ? el("p", { class: "kana-big", lang: "ja", text: k.char })
              : el("div", { class: "lesson-play" },
                  el("button", { class: "secondary", type: "button", onclick: () => play(k.char) }, "Play again", kbd("R"))),
            block, help),
          actions: [nextBtn],
        });
        keys.primary = null;
        if (mode === "hear") { keys.replay = () => play(k.char); play(k.char); }
      }
      ask();
    }

    // 3. Read real words made only of kana you know.
    function words() {
      const list = shuffle(lesson.words);
      let n = 0;
      function ask() {
        if (n >= list.length) return finish();
        const w = list[n];
        const reveal = el("div", { class: "result" });
        const nextBtn = primaryButton(n === list.length - 1 ? "Finish" : "Next", advance);
        nextBtn.hidden = true;
        function advance() { n += 1; ask(); }
        // Hand-picked near misses (kite for きって) first, other words of the lesson after.
        const near = (w.confuse || []).slice(0, 2);
        const others = shuffle(lesson.words.map((x) => x.ro).filter((r) => r !== w.ro && !near.includes(r)));
        const options = shuffle([w.ro, ...near, ...others].slice(0, 4));
        frame({
          title: `${title}: read words`, index: n, total: list.length,
          ask: { screen: "kana reading", jp: w.jp, reading: w.ro, en: w.en },
          body: el("div", { class: "card-body" },
            el("p", { class: "prompt", text: "Read this word." }),
            el("p", { class: "kana-big kana-word", lang: "ja", text: w.jp }),
            choiceBlock({
              options,
              answer: w.ro,
              onAnswer: () => {
                reveal.replaceChildren(el("p", { class: "phrase-en", text: `${w.jp} (${w.ro}): ${w.en}` }), playRow(w.jp));
                play(w.jp);
                nextBtn.hidden = false;
                keys.primary = advance;
                keys.replay = () => play(w.jp);
              },
            }),
            reveal),
          actions: [nextBtn],
        });
        keys.primary = null;
      }
      ask();
    }

    function finish() {
      return saveThen("/api/course/kana", { lesson_id: lesson.id }, finished);
    }
    function finished() {
      const chars = items.map((k) => k.char).join(" ");
      frame({
        title: `${title}: ${lesson.title} done`,
        body: el("div", { class: "card-body" },
          el("h3", { class: "end-title", text: chars || lesson.title }),
          el("p", { class: "prompt", text: items.length ? `${items.length} new kana. They're in tomorrow's review.` : "Done." })),
        actions: [primaryButton("Continue", continuePlan)],
        primary: continuePlan,
      });
    }

    intro();
  }

  // ---------- words ----------
  /**
   * Teach a few, test those, teach a few more: retrieval right after first exposure
   * beats reading twenty and being quizzed on all of them. The day's recap then
   * mixes them up. Long word lists can split across days (see state.plan_today).
   */
  function runWords(unit, row) {
    const redo = !!row.words;
    const seen = redo ? 0 : row.words_seen || 0;
    const left = unit.words.length - seen;
    const planned = today.unit && today.unit.id === unit.id ? today.words_today : 0;
    const count = redo ? left : Math.min(left, planned || Math.min(left, 10));
    teachWords({
      heading: `Words, unit ${unit.number}`,
      words: unit.words.slice(seen, seen + count),
      others: unit.words,
      spot: `words:${unit.id}:${seen}`,
      onFinish: () => saveThen("/api/course/step", redo ? { unit_id: unit.id, step: "words" } : { unit_id: unit.id, step: "words", count }, continuePlan),
    });
  }
  /** The teach-then-test loop, for a unit's words or a word pack. */
  function teachWords({ heading, words, others, spot, onFinish }) {
    const BATCH = 5;
    prefetch(words.map((w) => [w.jp, {}]));
    const batches = [];
    for (let i = 0; i < words.length; i += BATCH) batches.push(words.slice(i, i + BATCH));
    let b = Math.min(spotIn(spot), Math.max(0, batches.length - 1));
    const known = () => [...batches.slice(0, b + 1).flat(), ...(today.words_pool || []), ...others];

    function intro() {
      keepSpot(spot, b);
      const slice = batches[b];
      const go = () => quiz();
      const actions = [];
      if (b > 0) actions.push(el("button", { type: "button", class: "secondary", onclick: () => { b -= 1; intro(); } }, "Back"));
      actions.push(primaryButton("Test these", go));
      frame({
        title: heading, index: b, total: batches.length,
        ask: { screen: "word list", words: slice.map((w) => `${w.jp} = ${w.en}`) },
        body: el("div", { class: "card-body" },
          el("table", { class: "word-table" },
            el("tbody", {}, slice.map((w) => el("tr", {},
              el("td", {}, el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(w.jp) }, "▶")),
              el("td", { class: "word-jp", lang: "ja", text: w.jp }),
              el("td", { class: "word-ro", text: needsRomaji(w.jp) ? w.ro : "" }),
              el("td", { class: "word-en", text: w.en })))))),
        actions, primary: go,
      });
    }

    // Hear + see each word, pick its meaning. Misses come back once.
    function quiz() {
      const queue = shuffle(batches[b]).map((w) => ({ w, retried: false }));
      let n = 0;
      function ask() {
        if (n >= queue.length) return afterBatch();
        const { w, retried } = queue[n];
        const shown = performance.now();
        const nextBtn = primaryButton("Next", advance);
        nextBtn.hidden = true;
        function advance() { n += 1; ask(); }
        frame({
          title: heading, index: b, total: batches.length,
          ask: { screen: "word quiz", jp: w.jp, en: w.en },
          body: el("div", { class: "card-body" },
            el("p", { class: "kana-big kana-word", lang: "ja", text: w.jp }),
            needsRomaji(w.jp) ? el("p", { class: "phrase-ro", text: w.ro }) : null,
            playRow(w.jp),
            choiceBlock({
              ...meaningChoices(w, known()),
              onAnswer: async (right) => {
                if (!retried && w.id) lessonGrade(`${w.id}:mean`, { correct: right, ms: Math.round(performance.now() - shown), fmt: "word:choice" });
                if (!right && !queue[n].retried) queue.push({ w, retried: true });
                if (right) { const here = onThisScreen(); await wait(600); if (here()) advance(); }
                else { nextBtn.hidden = false; keys.primary = advance; }
              },
            })),
          actions: [nextBtn],
        });
        keys.primary = null;
        keys.replay = () => play(w.jp);
        play(w.jp);
      }
      ask();
    }
    function afterBatch() {
      if (b < batches.length - 1) { b += 1; return intro(); }
      return onFinish();
    }
    intro();
  }

  // ---------- grammar ----------
  function runGrammar(unit) {
    const points = unit.grammar;
    prefetch(points.flatMap((g) => g.examples.map((ex) => [ex.jp, {}])));
    const spot = `grammar:${unit.id}`;
    let gi = Math.min(spotIn(spot), points.length - 1);

    // 1. Each point: a short explanation and examples you can play.
    function explain() {
      keepSpot(spot, gi);
      const g = points[gi];
      const last = gi === points.length - 1;
      const go = () => { if (last) drill(); else { gi += 1; explain(); } };
      const actions = [];
      if (gi > 0) actions.push(el("button", { type: "button", class: "secondary", onclick: () => { gi -= 1; explain(); } }, "Back"));
      actions.push(primaryButton(last ? "Practice" : "Next", go));
      const list = el("ul", { class: "examples meanings-hidden" }, g.examples.map((ex) => el("li", {},
        el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(ex.jp) }, "▶"),
        el("span", { class: "example-jp", lang: "ja", text: ex.jp }),
        el("span", { class: "example-en", text: ex.en }))));
      const [lead, ...rest] = g.explain;
      const explainBox = el("div", { class: "grammar-explain", hidden: true },
        rest.map((para) => el("p", { class: "grammar-text", text: para })));
      const meaningsBtn = el("button", { class: "secondary", type: "button", "aria-pressed": "false", onclick: () => {
        const on = list.classList.toggle("meanings-hidden");
        meaningsBtn.setAttribute("aria-pressed", String(!on));
      } }, "Meanings", kbd("M"));
      const explainBtn = el("button", { class: "secondary", type: "button", "aria-pressed": "false", onclick: () => {
        explainBox.hidden = !explainBox.hidden;
        explainBtn.setAttribute("aria-pressed", String(!explainBox.hidden));
      } }, "More");
      async function playAll() {
        for (const ex of g.examples) {
          if (!here()) return;
          await play(ex.jp);
          await wait(250);
        }
      }
      frame({
        title: `Grammar, unit ${unit.number}`, index: gi, total: points.length,
        ask: { screen: "grammar", title: g.title, rule: g.rule, explanation: g.explain, examples: g.examples },
        body: el("div", { class: "card-body grammar" },
          el("h3", { class: "grammar-title", text: g.title }),
          g.rule ? el("p", { class: "grammar-rule", text: g.rule }) : null,
          lead ? el("p", { class: "grammar-text", text: lead }) : null,
          list,
          el("div", { class: "lesson-play" },
            el("button", { class: "secondary", type: "button", onclick: playAll }, "Play all", kbd("R")),
            meaningsBtn, rest.length ? explainBtn : null),
          explainBox),
        actions, primary: go,
      });
      const here = onThisScreen();
      keys.replay = playAll;
      keys.meanings = () => meaningsBtn.click();

    }

    // 2. Practice questions with a one-line reason after each answer. A few from
    // earlier units are mixed in: patterns only stay apart if you keep telling them apart.
    function drill() {
      const earlier = shuffle(unit.earlier_drill || []).slice(0, 3);
      const qs = earlier.length ? shuffle([...unit.drill, ...earlier]) : unit.drill;
      let n = 0;
      let right = 0;
      function ask() {
        if (n >= qs.length) return buildRound();
        const q = qs[n];
        const nextBtn = primaryButton("Next", advance);
        nextBtn.hidden = true;
        function advance() { n += 1; ask(); }
        const answer = q.choices[q.answer];
        frame({
          title: `Grammar practice, unit ${unit.number}`, index: n, total: qs.length,
          ask: { screen: "grammar question", question: q.q, choices: q.choices, correct: answer, explain: q.explain },
          body: el("div", { class: "card-body" },
            el("p", { class: "question-q", text: q.q }),
            q.say ? el("div", { class: "scene-line" },
              el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(q.say) }, "▶"),
              el("span", { lang: "ja", text: q.say })) : null,
            choiceBlock({
              options: shuffle(q.choices), answer, jp: true, explain: q.explain,
              onAnswer: (ok) => {
                if (ok) right += 1;
                if (/[ぁ-ゟ]/.test(answer)) play(answer);
                nextBtn.hidden = false;
                keys.primary = advance;
              },
            })),
          actions: [nextBtn],
        });
        keys.primary = null;
        if (q.say) { keys.replay = () => play(q.say); play(q.say); }
      }

      // 3. Put sentences together yourself. One per point counts as its first review.
      function buildRound() {
        const items = unit.build || [];
        if (!items.length) return finish();
        const perPoint = new Map();
        for (const item of shuffle(items)) {
          const got = perPoint.get(item.point) || [];
          if (got.length < 2) perPoint.set(item.point, [...got, item]);
        }
        const round = shuffle([...perPoint.values()].flat());
        const graded = new Set();
        let at = 0;
        function show() {
          if (at >= round.length) return finish();
          const item = round[at];
          const shown = performance.now();
          const nextBtn = primaryButton(at === round.length - 1 ? "Finish" : "Next", () => { at += 1; show(); });
          nextBtn.hidden = true;
          const ex = buildExercise(item, ({ right: ok, helped, answer }) => {
            if (ok) right += 1;
            if (!graded.has(item.point)) {
              graded.add(item.point);
              lessonGrade(item.card_id, { correct: ok, helped, ms: Math.round(performance.now() - shown), fmt: "grammar:build", answer });
            }
            nextBtn.hidden = false;
            keys.primary = () => nextBtn.click();
          });
          frame({
            title: `Put it together, unit ${unit.number}`, index: at, total: round.length,
            ask: { screen: "grammar build", jp: item.jp, en: item.en },
            body: el("div", { class: "card-body" }, ex.node),
            actions: [nextBtn],
          });
          ex.keys();
        }
        show();
      }
      function finish() {
        return saveThen("/api/course/step", { unit_id: unit.id, step: "grammar" }, finished);
      }
      function finished() {
        const total = qs.length + Math.min((unit.build || []).length, new Set((unit.build || []).map((b) => b.point)).size * 2);
        frame({
          title: `Grammar, unit ${unit.number}`,
          body: el("div", { class: "card-body" },
            el("h3", { class: "end-title", text: `${right} of ${total} right` }),
            el("p", { class: "prompt", text: "These patterns come back in your reviews, as new sentences to put together." })),
          actions: [primaryButton("Continue", continuePlan)],
          primary: continuePlan,
        });
      }
      ask();
    }
    explain();
  }

  // ---------- speak ----------
  function runSpeak(unit) {
    const tasks = unit.speak;
    const spot = `speak:${unit.id}`;
    let t = Math.min(spotIn(spot), tasks.length - 1);
    prefetch(tasks.map((task) => [task.say, {}]));

    function show() {
      keepSpot(spot, t);
      const task = tasks[t];
      const result = el("div", { class: "result", "aria-live": "polite" });
      const hint = el("div", { class: "hint", hidden: true },
        el("p", { lang: "ja", text: task.hint }),
        el("button", { class: "secondary", type: "button", onclick: () => play(task.hint.replace(/＿/g, "")) }, "Play"),
      );
      let pending = false;
      async function submit(fields) {
        if (pending) return;
        pending = true;
        hold.disabled = true;
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/speak", { method: "POST", body: fields });
          renderVerdict(r);
          typed.value = "";
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        } finally {
          pending = false;
          hold.disabled = false;
        }
      }
      function renderVerdict(r) {
        noteResult({ said: r.heard, verdict: r.verdict, model: r.model, tip: r.tip });
        const label = { great: "Great answer.", ok: "Understood. One thing to fix.", retry: "Try that again." }[r.verdict] || "";
        const cls = { great: "good", ok: "close", retry: "off" }[r.verdict] || "off";
        result.replaceChildren(...[
          el("p", { class: "verdict " + cls, text: label }),
          heardLine("You said ", r.heard, r.said_en ? `, which means “${r.said_en}”` : ""),
          r.model ? el("div", { class: "model" },
            el("p", { class: "model-label", text: r.verdict === "great" ? "Natural way to say it" : "Try saying" }),
            el("p", { class: "model-jp", lang: "ja", text: r.model }),
            el("button", { class: "secondary", type: "button", onclick: () => play(r.model) }, "Play")) : null,
          r.tip ? el("p", { class: "tip", text: r.tip }) : null,
        ].filter(Boolean));
        if (r.verdict !== "great" && r.model) play(r.model);
      }
      const hold = holdControl("Hold and answer", (blob, ext) => submit(audioForm(blob, ext, { unit_id: unit.id, task: t })), showProblem(result));
      const typed = el("input", { type: "text", maxlength: "120", placeholder: "Or type your answer", lang: "ja" });
      const typedForm = el("form", { class: "typed", onsubmit: (e) => {
        e.preventDefault();
        if (!typed.value.trim()) return;
        const f = new FormData();
        f.append("unit_id", unit.id);
        f.append("task", String(t));
        f.append("text", typed.value.trim());
        submit(f);
      } }, typed, el("button", { class: "secondary", type: "submit" }, "Send"));
      const last = t === tasks.length - 1;

      frame({
        title: `Speak, unit ${unit.number}`,
        index: t,
        total: tasks.length,
        ask: { screen: "speaking task", jp: task.say, situation: task.situation, model_answer: task.hint },
        body: el("div", { class: "card-body" },
          el("p", { class: "situation", text: task.situation }),
          el("div", { class: "says" },
            el("p", { class: "says-label", text: "Kaiwa says" }),
            el("p", { class: "says-jp", lang: "ja", text: task.say }),
            playRow(task.say)),
          hold,
          micRow(),
          typedForm,
          el("button", { class: "secondary hint-toggle", type: "button", onclick: () => { hint.hidden = !hint.hidden; } }, "Show a hint"),
          hint,
          result,
        ),
        actions: [primaryButton(last ? "Finish unit" : "Next", next)],
        primary: next,
        hold,
      });
      keys.replay = () => play(task.say);
      play(task.say);
    }
    function next() {
      if (t < tasks.length - 1) {
        t += 1;
        return show();
      }
      return saveThen("/api/course/step", { unit_id: unit.id, step: "speak" }, () => done(unit));
    }
    show();
  }

  /** A unit's end: what you can now do, and the mission that puts it to use. */
  function done(unit) {
    const back = () => continuePlan();
    const canMission = today.has_tutor;
    frame({
      title: `Unit ${unit.number} done`,
      body: el("div", { class: "card-body" },
        el("h3", { class: "end-title", text: unit.title }),
        el("div", { class: "can-do" },
          el("p", { class: "can-do-label", text: "You can now:" }),
          el("p", { class: "can-do-text", text: unit.goal })),
        unit.culture ? el("p", { class: "culture-note" }, el("strong", { text: "Did you know? " }), unit.culture) : null,
        canMission ? el("p", { class: "prompt", text: "Want to try it for real? A short scene where you need exactly this, with a partner who reacts to what you say." }) : null),
      actions: [
        canMission ? el("button", { type: "button", class: "secondary", onclick: back }, "Not now") : null,
        canMission ? primaryButton("Start the mission", () => runTalk(unit.id)) : primaryButton("Continue", back),
      ].filter(Boolean),
      primary: canMission ? () => runTalk(unit.id) : back,
    });
  }

  // ---------- course map ----------
  async function runMap() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    clearKeys();
    root.replaceChildren(el("div", { class: "home" }, el("p", { class: "pending", text: "Loading…" })));
    let m;
    let packs = [];
    try {
      [m, { packs }] = await Promise.all([api("/api/course/map"), api("/api/course/packs")]);
    } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    const doneCount = m.units.filter((u) => u.status === "done").length;
    root.replaceChildren(el("div", { class: "home map" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Back"),
        el("h2", { class: "lesson-title", text: "Course map" }),
        el("span", { class: "lesson-count", text: `${doneCount} of ${m.units.length}` })),
      el("ol", { class: "map-units" }, m.units.map((u) => el("li", { class: `map-unit ${u.status}` },
        el("span", { class: "map-mark", "aria-hidden": "true", text: u.status === "done" ? "✓" : String(u.number) }),
        el("div", { class: "map-main" },
          el("p", { class: "map-title" }, u.title, " ", el("span", { lang: "ja", text: u.title_jp }),
            u.mission ? el("span", { class: "map-star", title: "Mission done", text: " ★" }) : null),
          el("p", { class: "map-goal", text: u.goal }),
          u.status !== "later" ? el("span", { class: "map-strength", title: `${u.strength}% of this unit is well remembered (3+ weeks)` },
            el("span", { style: `width:${u.strength}%` })) : null),
        u.status !== "later"
          ? el("button", { type: "button", class: "secondary", onclick: () => unitPage(u.id) }, "Open")
          : el("span")))),
      el("h3", { class: "stats-h", text: "Word packs" }),
      el("p", { class: "stats-caption", text: "Extra words the units don't reach. Add one when you want it: they join your reviews like any other word." }),
      el("ul", { class: "pack-list" }, packs.map((p) => el("li", { class: "pack" + (p.taught >= p.words.length ? " done" : "") },
        el("div", {},
          el("p", { class: "map-title", text: p.title }),
          el("p", { class: "map-goal", text: `${p.blurb} ${p.words.length} words.` })),
        p.taught >= p.words.length
          ? el("span", { class: "map-star", text: "✓" })
          : el("button", { type: "button", class: "secondary", onclick: () => runPack(p) }, "Learn")))),
      el("h3", { class: "stats-h", text: "Kana" }),
      el("ol", { class: "map-kana" }, m.kana_lessons.map((k) => el("li", { class: k.done ? "done" : "" },
        el("button", { type: "button", class: "secondary", onclick: () => kanaFromMap(k.id) },
          el("span", { lang: "ja", text: k.chars.split(" ").slice(0, 5).join(" ") || k.title }))))),
    ));
    keys.primary = showHome;
  }
  function runPack(pack) {
    track("open", { activity: "pack", pack: pack.id });
    teachWords({
      heading: pack.title, words: pack.words, others: pack.words, spot: `pack:${pack.id}`,
      onFinish: () => saveThen("/api/course/pack", { pack_id: pack.id }, async () => {
        await refresh();
        frame({
          title: pack.title,
          body: el("div", { class: "card-body" },
            el("h3", { class: "end-title", text: `${pack.words.length} new words` }),
            el("p", { class: "prompt", text: "They'll come up in your next recap, then in your reviews." })),
          actions: [primaryButton("Back to the map", runMap)],
          primary: runMap,
        });
      }),
    });
  }
  async function kanaFromMap(id) {
    try {
      const lesson = await api(`/api/course/kana_lesson/${encodeURIComponent(id)}`);
      afterLesson = runMap;
      runKana(lesson);
    } catch (err) { root.prepend(el("p", { class: "verdict off", text: String(err.message || err) })); }
  }
  /** One unit from the map: its steps, its mission, its conversation to hear again. */
  async function unitPage(id) {
    let data;
    try { data = await api(`/api/course/unit/${encodeURIComponent(id)}`); } catch (err) { return runMap(); }
    const unit = data.unit;
    const row = data.unit_steps;
    const open = (step) => () => { afterLesson = () => unitPage(id); runUnitStep(unit, step, row); };
    const startMission = () => { afterLesson = () => unitPage(id); runTalk(unit.id); };
    root.replaceChildren(el("div", { class: "home" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: runMap }, "Back"),
        el("h2", { class: "lesson-title", text: `Unit ${unit.number}: ${unit.title}` })),
      el("p", { class: "home-goal", text: unit.goal }),
      el("ol", { class: "plan" }, unit.steps.map((step) => planRow(STEP_NAMES[step], row[step] ? "Done" : "Not yet", !!row[step], open(step), row[step] ? "Redo" : "Open")),
        today && today.has_tutor ? planRow("Mission", row.mission ? "Done" : "Use it in a real exchange", !!row.mission, startMission, row.mission ? "Again" : "Start") : null),
    ));
    clearKeys();
    keys.primary = runMap;
  }

  // ---------- phrasebook ----------
  async function runBook() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    clearKeys();
    root.replaceChildren(el("div", { class: "home" }, el("p", { class: "pending", text: "Loading…" })));
    let book;
    try { book = await api("/api/course/phrasebook"); } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    let tab = "phrases";
    const list = el("div", { class: "book-list" });
    const mineBox = minePanel(async () => { book = await api("/api/course/phrasebook"); tab = "mine"; draw(); }, today && today.has_tutor);
    const search = el("input", { type: "search", class: "book-search", placeholder: "Search in English, kana or romaji", "aria-label": "Search", oninput: draw });
    const tabs = el("div", { class: "book-tabs", role: "tablist" });
    const STRENGTH = { new: "New", growing: "Growing", strong: "Strong" };
    function row(item) {
      return el("div", { class: "book-row" },
        el("button", { class: "secondary line-play", type: "button", "aria-label": `Play ${item.jp}`, onclick: () => play(item.jp) }, "▶"),
        el("span", { class: "book-jp", lang: "ja", text: item.jp }),
        el("span", { class: "book-en" }, item.en, item.note ? el("span", { class: "book-note", text: item.note }) : null),
        el("span", { class: `book-strength ${item.strength}`, title: "How well you remember it", text: STRENGTH[item.strength] }));
    }
    function mineRow(item) {
      const r = row(item);
      r.append(el("button", { type: "button", class: "grade-change", "aria-label": `Remove ${item.jp}`, onclick: async () => {
        await api(`/api/course/mine/${encodeURIComponent(item.id)}`, { method: "DELETE" }).catch(() => {});
        book = await api("/api/course/phrasebook");
        draw();
      } }, "Remove"));
      return r;
    }
    function grammarRow(g) {
      return el("details", { class: "book-grammar" },
        el("summary", {}, el("strong", { text: g.title }), g.rule ? el("span", { class: "book-rule", text: ` ${g.rule}` }) : null),
        g.explain.map((p) => el("p", { class: "grammar-text", text: p })),
        el("ul", { class: "examples" }, g.examples.map((ex) => el("li", {},
          el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(ex.jp) }, "▶"),
          el("span", { class: "example-jp", lang: "ja", text: ex.jp }),
          el("span", { class: "example-en", text: ex.en })))));
    }
    function draw() {
      const q = search.value.trim().toLowerCase();
      const hits = (it) => !q || [it.jp, it.en, it.ro, it.title, it.rule, it.note].some((v) => v && v.toLowerCase().includes(q));
      const counts = { mine: book.mine.filter(hits).length, phrases: book.phrases.filter(hits).length, words: book.words.filter(hits).length, grammar: book.grammar.filter(hits).length };
      mineBox.hidden = tab !== "mine";
      tabs.replaceChildren(...["phrases", "words", "grammar", "mine"].map((t) => el("button", {
        type: "button", role: "tab", "aria-selected": String(t === tab), class: "pace-chip" + (t === tab ? " on" : ""),
        onclick: () => { tab = t; draw(); } }, `${t[0].toUpperCase()}${t.slice(1)} (${counts[t]})`)));
      const items = book[tab].filter(hits);
      list.replaceChildren(...(items.length
        ? items.map(tab === "grammar" ? grammarRow : tab === "mine" ? mineRow : row)
        : [el("p", { class: "status", text: q ? "Nothing matches." : tab === "mine" ? "Add the things you actually want to say: your job, your hobby, your dog's name." : "Nothing here yet. It fills up as you learn." })]));
    }
    draw();
    root.replaceChildren(el("div", { class: "home" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Back"),
        el("h2", { class: "lesson-title", text: "Phrasebook" })),
      search, tabs, mineBox, list));
  }

  /** "How do I say…?": ask, hear it, keep it. Kept phrases become normal review cards. */
  function minePanel(onKept, hasTutor) {
    const out = el("div", { class: "result" });
    const input = el("input", { type: "text", maxlength: "160", placeholder: "I work in IT. My dog is called Rex.", "aria-label": "What do you want to be able to say?" });
    const form = el("form", { class: "typed", onsubmit: async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      out.replaceChildren(el("p", { class: "pending", text: "Working out how you'd say it…" }));
      try {
        const r = await postJson("/api/course/mine/suggest", { text });
        const keep = el("button", { type: "button", onclick: async () => {
          keep.disabled = true;
          try {
            await postJson("/api/course/mine", r);
            input.value = "";
            out.replaceChildren(el("p", { class: "verdict good", text: "Kept. It comes up in your next recap." }));
            onKept();
          } catch (err) {
            keep.disabled = false;
            out.append(el("p", { class: "verdict off", text: String(err.message || err) }));
          }
        } }, "Keep it");
        out.replaceChildren(
          el("p", { class: "phrase-jp", lang: "ja", text: r.jp }),
          el("p", { class: "phrase-en", text: r.en }),
          r.note ? el("p", { class: "phrase-note", text: r.note }) : "",
          el("div", { class: "lesson-play" },
            el("button", { class: "secondary", type: "button", onclick: () => play(r.jp) }, "Play"),
            el("button", { class: "secondary", type: "button", onclick: () => play(r.jp, { slow: true }) }, "Slow"),
            keep));
        play(r.jp);
      } catch (err) {
        out.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
      }
    } }, input, el("button", { class: "secondary", type: "submit" }, "How do I say it?"));
    return el("div", { class: "mine-panel", hidden: true },
      el("p", { class: "lesson-note", text: "What do you want to be able to say? Write it in English." }),
      hasTutor ? form : el("p", { class: "status", text: "This needs your DeepSeek key (Settings → DeepSeek)." }),
      out);
  }

  // ---------- fluency ----------
  const SPEED_MIN = 12;
  const SPEED_SECONDS = 60;
  /**
   * One minute of known words and phrases: hear it, tap the meaning, next, no pause.
   * Fluency practice is known material under time pressure, so it never touches the
   * review schedule, and a miss costs nothing but a moment.
   */
  async function runSpeed() {
    track("drill", { kind: "speed" });
    const pool = [...(today.words_pool || []), ...(today.phrases_pool || [])].filter((x) => x.jp && x.en);
    const queue = shuffle(pool);
    const meanings = pool.map((x) => x.en);
    prefetch(queue.slice(0, 16).map((x) => [x.jp, {}]));
    let score = 0;
    let misses = 0;
    let at = 0;
    let endsAt = 0;
    let ticker = 0;
    const clock = el("span", { class: "speed-clock", text: String(SPEED_SECONDS) });
    const tally = el("span", { class: "speed-score", text: "0" });
    const stage = el("div", { class: "speed-stage" });

    function ask() {
      if (Date.now() >= endsAt) return end();
      const item = queue[at % queue.length];
      at += 1;
      prefetch(queue.slice(at, at + 3).map((x) => [x.jp, {}]));
      const here = onThisScreen();
      const options = choicesFor(item.en, meanings);
      const buttons = options.map((opt, i) => el("button", { class: "secondary choice", type: "button", onclick: () => pick(i) },
        el("span", { class: "choice-key", text: String(i + 1) }), opt));
      let answered = false;
      async function pick(i) {
        if (answered || i >= options.length) return;
        answered = true;
        const right = options[i] === item.en;
        buttons[i].classList.add(right ? "right" : "wrong");
        if (right) {
          score += 1;
          tally.textContent = String(score);
        } else {
          misses += 1;
          buttons[options.indexOf(item.en)].classList.add("right");
        }
        await wait(right ? 180 : 700);
        if (here()) ask();
      }
      stage.replaceChildren(
        el("div", { class: "lesson-play" }, el("button", { class: "secondary", type: "button", onclick: () => play(item.jp) }, "Play again", kbd("R"))),
        el("div", { class: "choice-block" }, el("div", { class: "choices" }, buttons)));
      keys.choice = pick;
      keys.replay = () => play(item.jp);
      play(item.jp);
    }
    async function end() {
      clearInterval(ticker);
      stopAudio();
      let result = { best: score, previous: 0 };
      try { result = await postJson("/api/course/best", { key: "speed", value: score }); } catch (_) {}
      const again = () => runSpeed();
      frame({
        title: "Speed round",
        body: el("div", { class: "card-body" },
          el("h3", { class: "end-title", text: `${score} in a minute` }),
          el("p", { class: "prompt", text: score > result.previous && result.previous
            ? `A new best, up from ${result.previous}.`
            : result.previous ? `Your best is ${result.best}.` : "That's your score to beat." }),
          misses ? el("p", { class: "status", text: `${misses} missed. These don't affect your reviews.` }) : null),
        actions: [el("button", { type: "button", class: "secondary", onclick: showHome }, "Done"), primaryButton("Again", again)],
        primary: again,
      });
    }
    function begin() {
      frame({ title: "Speed round",
        body: el("div", { class: "card-body" }, el("div", { class: "speed-head" }, clock, tally), stage),
        actions: [] });
      endsAt = Date.now() + SPEED_SECONDS * 1000;
      const here = onThisScreen();
      ticker = setInterval(() => {
        if (!here()) return clearInterval(ticker);
        const left = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
        clock.textContent = String(left);
        if (left <= 0) { clearInterval(ticker); end(); }
      }, 250);
      ask();
    }
    frame({
      title: "Speed round",
      body: el("div", { class: "card-body" },
        el("h3", { class: "end-title", text: "One minute, by ear" }),
        el("p", { class: "prompt", text: "Hear it, tap what it means. Number keys work too. Don't translate word by word; go with your first impression." }),
        today.bests && today.bests.speed ? el("p", { class: "status", text: `Your best: ${today.bests.speed}` }) : null),
      actions: [primaryButton("Go", begin)],
      primary: begin,
    });
  }

  /** Prices and times at full speed: hear it, type the number. Gets harder as you get them right. */
  function runNumbers() {
    track("drill", { kind: "numbers" });
    const kinds = Object.entries(today.drills || {}).filter(([, on]) => on).map(([k]) => k);
    const names = { price: "Prices", time: "Times" };
    function pick() {
      frame({
        title: "Numbers by ear",
        body: el("div", { class: "card-body" },
          el("p", { class: "prompt", text: "Ten rounds. Listen and type what you hear. You can replay as often as you need." }),
          el("div", { class: "lesson-play" }, kinds.map((k) => el("button", { type: "button", class: "secondary", onclick: () => start(k, levelOf(k)) }, names[k])))),
        actions: [el("button", { type: "button", class: "secondary", onclick: showHome }, "Back")],
      });
    }
    function levelOf(kind) {
      return Number(readPref(`kaiwa_numbers_${kind}`, "1")) || 1;
    }
    async function start(kind, level) {
      frame({ title: "Numbers by ear", body: el("p", { class: "pending", text: "Getting ready…" }) });
      let items;
      try { items = (await api(`/api/course/drill/${kind}?level=${level}`)).items; } catch (err) {
        return frame({ title: "Numbers by ear", body: el("p", { class: "verdict off", text: String(err.message || err) }), actions: [primaryButton("Back", showHome)], primary: showHome });
      }
      prefetch(items.slice(0, 4).map((it) => [it.say, {}]));
      let n = 0;
      let right = 0;
      function ask() {
        if (n >= items.length) return end();
        const it = items[n];
        prefetch(items.slice(n + 1, n + 3).map((x) => [x.say, {}]));
        const result = el("div", { class: "result", "aria-live": "polite" });
        const nextBtn = primaryButton("Next", () => { n += 1; ask(); });
        nextBtn.hidden = true;
        const clean = (v) => v.replace(/[,，¥円\s]/g, "").replace(/[：.]/g, ":").replace(/^(\d{1,2})$/, kind === "time" ? "$1:00" : "$1").replace(/^0(\d):/, "$1:");
        const input = el("input", { type: "text", class: "produce-input", inputmode: kind === "price" ? "numeric" : "text", autocomplete: "off",
          placeholder: kind === "price" ? "How much? e.g. 300" : "What time? e.g. 4:30" });
        const form = el("form", { class: "produce-form", onsubmit: (e) => {
          e.preventDefault();
          if (!input.value.trim() || input.disabled) return;
          input.disabled = true;
          const ok = clean(input.value.trim()) === it.answer;
          if (ok) right += 1;
          result.replaceChildren(
            el("p", { class: "verdict " + (ok ? "good" : "off"), text: ok ? "Right." : `It was ${it.show}.` }),
            el("p", { class: "phrase-jp", lang: "ja", text: it.say }));
          play(it.say);
          nextBtn.hidden = false;
          keys.primary = () => nextBtn.click();
        } }, input, el("button", { type: "submit", class: "secondary" }, "Check"));
        frame({
          title: `${names[kind]} by ear`, index: n, total: items.length,
          ask: { screen: "numbers by ear", jp: it.say, en: it.show },
          body: el("div", { class: "card-body" },
            el("div", { class: "lesson-play" },
              el("button", { type: "button", class: "secondary", onclick: () => play(it.say) }, "Play again", kbd("R")),
              el("button", { type: "button", class: "secondary", onclick: () => play(it.say, { slow: true }) }, "Slow")),
            form, result),
          actions: [nextBtn],
        });
        keys.primary = null;
        keys.replay = () => play(it.say);
        play(it.say);
        setTimeout(() => input.focus(), 0);
      }
      async function end() {
        const moved = right >= 9 && level < 3;
        if (moved) writePref(`kaiwa_numbers_${kind}`, String(level + 1));
        await postJson("/api/course/best", { key: `numbers_${kind}`, value: right }).catch(() => {});
        const again = () => start(kind, moved ? level + 1 : level);
        frame({
          title: "Numbers by ear",
          body: el("div", { class: "card-body" },
            el("h3", { class: "end-title", text: `${right} of ${items.length}` }),
            el("p", { class: "prompt", text: moved ? "Bigger numbers next time." : right >= 7 ? "Nearly automatic. Numbers come from repetition more than from thinking." : "Numbers take a lot of hearing. A few rounds a week adds up fast." })),
          actions: [el("button", { type: "button", class: "secondary", onclick: showHome }, "Done"), primaryButton("Again", again)],
          primary: again,
        });
      }
      ask();
    }
    kinds.length === 1 ? start(kinds[0], levelOf(kinds[0])) : pick();
  }

  /**
   * Hands-free: the English, a pause to say the Japanese out loud, the Japanese twice in
   * two voices. Saying it before hearing it is what makes this recall and not just
   * listening. Ungraded; time counts as listening. English uses the device's own voice.
   */
  async function runHandsFree() {
    track("drill", { kind: "handsfree" });
    let book;
    frame({ title: "Hands-free", body: el("p", { class: "pending", text: "Getting ready…" }) });
    try { book = await api("/api/course/phrasebook"); } catch (err) {
      return frame({ title: "Hands-free", body: el("p", { class: "verdict off", text: String(err.message || err) }), actions: [primaryButton("Back", showHome)], primary: showHome });
    }
    const rank = { new: 0, growing: 1, strong: 2 };
    const items = [...book.phrases, ...book.mine].sort((a, b) => rank[a.strength] - rank[b.strength]);
    const list = [...shuffle(items.slice(0, 30)), ...shuffle(items.slice(30))];
    prefetch(list.slice(0, 6).map((p) => [p.jp, {}]));
    const canSpeak = "speechSynthesis" in window;
    let running = false;
    let at = 0;
    const en = el("p", { class: "prompt-en", text: "" });
    const jp = el("p", { class: "phrase-jp", lang: "ja", hidden: true });
    const status = el("p", { class: "status", text: "" });
    const toggle = el("button", { type: "button", class: "lesson-primary", onclick: () => (running ? stop() : go()) }, "Start");
    function sayEnglish(text) {
      return new Promise((resolve) => {
        if (!canSpeak) return resolve();
        const u = new SpeechSynthesisUtterance(text.replace(/\(.*?\)/g, ""));
        u.lang = "en-US";
        u.onend = u.onerror = () => resolve();
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
      });
    }
    function stop() {
      running = false;
      toggle.textContent = "Resume";
      if (canSpeak) window.speechSynthesis.cancel();
      stopAudio();
    }
    async function go() {
      running = true;
      toggle.textContent = "Pause";
      const here = onThisScreen();
      const live = () => running && here();
      while (live()) {
        const p = list[at % list.length];
        prefetch(list.slice(at + 1, at + 3).map((x) => [x.jp, {}]));
        const since = Date.now();
        jp.hidden = true;
        en.textContent = p.en;
        status.textContent = "Say it out loud…";
        await sayEnglish(p.en);
        await wait(Math.min(5000, 1800 + p.jp.length * 200));
        if (!live()) break;
        jp.textContent = p.jp;
        jp.hidden = false;
        status.textContent = "";
        await play(p.jp, { voice: "a" });
        await wait(600);
        if (!live()) break;
        await play(p.jp, { voice: "b" });
        await wait(1000);
        postJson("/api/course/listened", { seconds: (Date.now() - since) / 1000, scene: "" }).catch(() => {});
        at += 1;
      }
    }
    frame({
      title: "Hands-free",
      body: el("div", { class: "card-body" },
        el("p", { class: "lesson-note", text: "It says the English. You say the Japanese out loud. Then it says it back, twice. Nothing is graded." }),
        canSpeak ? null : el("p", { class: "status", text: "This device can't read English aloud, so watch the screen for the prompt." }),
        en, jp, status,
        el("div", { class: "home-actions" }, toggle)),
      actions: [el("button", { type: "button", class: "secondary", onclick: () => { stop(); showHome(); } }, "End")],
    });
  }

  // Settings → Level → Take the placement test: switch to Learn, then open the test
  // once the home screen has loaded (otherwise the home render would cover it).
  document.getElementById("placementOpen")?.addEventListener("click", () => {
    placementAfterHome = true;
    const tab = document.querySelector('.tab[data-mode="learn"]');
    if (tab && document.body.dataset.mode !== "learn") tab.click();
    else showHome();
  });
  const autoBox = document.getElementById("autoAdvanceToggle");
  if (autoBox) {
    autoBox.checked = autoAdvance();
    autoBox.addEventListener("change", () => writePref("kaiwa_auto_advance", autoBox.checked ? "1" : "0"));
  }
  const answerSelect = document.getElementById("answerModeSelect");
  if (answerSelect) {
    answerSelect.value = answerMode();
    answerSelect.addEventListener("change", () => writePref("kaiwa_answer_mode", answerSelect.value));
  }

  window.KaiwaCourse = { show: showHome };

  if (document.getElementById("modeLearn")?.classList.contains("active")) {
    showHome();
  }
})();

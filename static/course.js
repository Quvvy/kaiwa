/* Kaiwa daily lesson (Learn tab): Review → New phrases → Listen → Speak.
 * Self-contained: own audio player, hold-to-speak recorder with a live mic
 * meter, and keyboard shortcuts (Enter = primary, hold Space = speak, R = replay).
 * index.html calls KaiwaCourse.show() when the tab opens. */
(() => {
  "use strict";

  const root = document.getElementById("course");
  if (!root) return;

  let today = null;
  let showRomaji = readPref("kaiwa_course_romaji", "1") === "1";
  const keys = { primary: null, hold: null, replay: null, choice: null, meanings: null, text: null };

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
  function learnVisible() {
    return document.body.dataset.mode === "learn";
  }

  // ---------- keyboard ----------
  document.addEventListener("keydown", (e) => {
    if (!learnVisible() || e.ctrlKey || e.metaKey || e.altKey) return;
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
    if (e.key === " " && keys.hold) {
      e.preventDefault();
      if (!e.repeat) keys.hold.start();
    } else if (e.key === "Enter" && keys.primary && !(tag === "BUTTON" && e.target.matches(":focus-visible"))) {
      e.preventDefault();
      keys.primary();
    } else if ((e.key === "r" || e.key === "R") && keys.replay && !e.repeat) {
      e.preventDefault();
      keys.replay();
    } else if ((e.key === "t" || e.key === "T") && keys.text && !e.repeat) {
      e.preventDefault();
      keys.text();
    } else if ((e.key === "m" || e.key === "M") && keys.meanings && !e.repeat) {
      e.preventDefault();
      keys.meanings();
    } else if (/^[1-9]$/.test(e.key) && keys.choice && !e.repeat) {
      e.preventDefault();
      keys.choice(Number(e.key) - 1);
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
      currentAudio.pause();
      currentAudio = null;
    }
  }
  async function play(text, opts) {
    stopAudio();
    let b64;
    try {
      b64 = await audioFor(text, opts);
    } catch (err) {
      setAudioProblem(err);
      return;
    }
    setAudioProblem(null);
    await new Promise((resolve) => {
      const audio = new Audio("data:audio/wav;base64," + b64);
      currentAudio = audio;
      audio.addEventListener("ended", resolve, { once: true });
      audio.addEventListener("error", resolve, { once: true });
      audio.play().catch(resolve);
    });
  }
  function prefetch(items) {
    for (const [text, opts] of items) audioFor(text, opts).catch(() => {});
  }
  function setAudioProblem(err) {
    audioProblem = err === "starting" ? STARTING_NOTE
      : err ? "No audio: the voice engine isn't running. Restart Kaiwa or switch engines in Settings → Speech." : "";
    const note = root.querySelector(".lesson-audio-note");
    if (note) {
      note.textContent = audioProblem;
      note.hidden = !audioProblem;
    }
  }
  function playRow(text, opts = {}) {
    return el("div", { class: "lesson-play" },
      el("button", { class: "secondary", type: "button", onclick: () => play(text, opts) }, "Play", kbd("R")),
      el("button", { class: "secondary", type: "button", onclick: () => play(text, { ...opts, slow: true }) }, "Slow"),
    );
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
        onProblem("Released before the microphone opened. Hold until the bar turns red.");
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
        const mic = window.KaiwaMic.currentLabel() || "the selected microphone";
        onProblem(`No sound from ${mic}. Pick another microphone below.`);
      } else {
        onAudio(res.blob, res.ext);
      }
    }
    btn.addEventListener("pointerdown", (e) => { e.preventDefault(); btn.setPointerCapture?.(e.pointerId); start(); });
    btn.addEventListener("pointerup", stop);
    btn.addEventListener("pointercancel", stop);
    btn.holdApi = { start, stop };
    return btn;
  }

  function micRow() {
    return window.KaiwaMic.picker({ compact: true });
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
  function choicesFor(answer, pool, n = 4) {
    const others = shuffle([...new Set(pool)].filter((v) => v !== answer)).slice(0, n - 1);
    return shuffle([answer, ...others]);
  }
  /**
   * One multiple-choice question. Calls onAnswer(right) after showing the result.
   * Number keys pick an option; a right answer moves on by itself.
   */
  function choiceBlock({ options, answer, onAnswer, jp = false, explain = "", pics = false }) {
    const feedback = el("p", { class: "verdict" });
    let done = false;
    const buttons = options.map((opt, i) =>
      el("button", { class: "secondary choice" + (pics ? " choice-pic" : ""), type: "button", lang: jp ? "ja" : null, onclick: () => pick(i) },
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
      onAnswer(right);
    }
    pendingChoice = pick; // frame() hands it to the number keys once the screen is up
    return el("div", { class: "choice-block" }, el("div", { class: "choices" }, buttons), feedback);
  }
  /** Picture choices when this word and at least three others have one; else English. */
  function meaningChoices(word, pool) {
    const pics = pool.filter((w) => w.pic && w.jp !== word.jp).map((w) => w.pic);
    if (word.pic && new Set(pics).size >= 3) {
      return { options: choicesFor(word.pic, pics), answer: word.pic, pics: true };
    }
    return { options: choicesFor(word.en, pool.map((w) => w.en)), answer: word.en, pics: false };
  }

  let pendingChoice = null;
  function wait(ms) {
    return new Promise((r) => setTimeout(r, ms));
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
  function heardLine(prefix, heard, extra) {
    return el("p", { class: "heard-line" }, prefix, el("span", { lang: "ja", text: heard }), extra || null);
  }

  // ---------- ask ----------
  // What the current screen is about; frame() sets it, results add to it.
  let askContext = null;
  function noteResult(result) {
    if (askContext) askContext = { ...askContext, result };
  }

  const askPanel = (() => {
    const list = el("div", { class: "ask-list" });
    const about = el("p", { class: "ask-about" });
    const input = el("input", { type: "text", maxlength: "500", placeholder: "Ask anything about this" });
    const quick = (label, key) => el("button", { type: "button", class: "secondary", onclick: () => send("", key) }, label);
    const wrongBtn = quick("What did I get wrong?", "wrong");
    const panel = el("aside", { class: "ask-panel", hidden: true, "aria-label": "Ask" },
      el("div", { class: "ask-head" },
        el("span", { class: "ask-title", text: "Ask" }),
        el("button", { type: "button", class: "secondary", onclick: () => close() }, "Close", kbd("Esc"))),
      about,
      el("div", { class: "ask-quick" }, quick("Break this down", "breakdown"), quick("Why?", "why"), wrongBtn),
      el("form", { class: "ask-form", onsubmit: (e) => { e.preventDefault(); send(input.value, ""); } },
        input, el("button", { type: "submit" }, "Ask")),
      list);
    document.body.append(panel);

    function refresh() {
      if (!askContext) return close();
      about.textContent = askContext.jp || askContext.title || "";
      about.lang = askContext.jp ? "ja" : "";
      wrongBtn.hidden = !askContext.result;
    }
    function open() {
      if (!askContext) return;
      refresh();
      panel.hidden = false;
      input.focus();
    }
    function close() {
      panel.hidden = true;
      if (document.activeElement && panel.contains(document.activeElement)) document.activeElement.blur();
    }
    async function send(question, key) {
      if (!askContext || (!key && !question.trim())) return;
      const entry = el("div", { class: "ask-entry" },
        el("p", { class: "ask-q", text: key ? { breakdown: "Break this down", why: "Why?", wrong: "What did I get wrong?" }[key] : question }),
        el("p", { class: "pending", text: "Thinking…" }));
      list.prepend(entry);
      input.value = "";
      try {
        const r = await postJson("/api/course/ask", { question, quick: key, context: askContext });
        entry.replaceChildren(entry.firstChild, ...renderAnswer(r));
      } catch (err) {
        entry.replaceChildren(entry.firstChild, el("p", { class: "verdict off", text: String(err.message || err) }));
      }
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
          el("span", { class: "ask-example-en", text: ex.en })));
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
    keys.text = null;
    keys.choice = pendingChoice;
    pendingChoice = null;
    const top = el("div", { class: "lesson-top" },
      el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Exit"),
      el("h2", { class: "lesson-title", text: title }),
      total ? el("span", { class: "lesson-count", text: `${index + 1} of ${total}` }) : null,
      el("button", { class: "secondary lesson-ask", type: "button", onclick: () => askPanel.toggle(),
        "data-tip": "Ask a question about this screen" }, "Ask", kbd("?")),
    );
    const steps = total
      ? el("div", { class: "lesson-steps", "aria-hidden": "true" },
          Array.from({ length: total }, (_, i) => el("span", { class: i < index ? "done" : i === index ? "now" : "" })))
      : null;
    const note = el("p", { class: "lesson-audio-note", hidden: !audioProblem, text: audioProblem });
    root.replaceChildren(
      el("div", { class: "lesson" },
        top,
        steps,
        note,
        el("div", { class: "lesson-body" }, body),
        actions.length ? el("div", { class: "lesson-actions" }, actions) : null,
      ),
    );
    askPanel.refresh();
  }
  function primaryButton(label, onclick, { disabled = false } = {}) {
    return el("button", { type: "button", class: "lesson-primary", disabled, onclick }, label, kbd("Enter"));
  }

  // ---------- home ----------
  const STEP_NAMES = { learn: "New phrases", words: "Words", grammar: "Grammar", listen: "Listen", speak: "Speak" };
  function planSteps() {
    const steps = [];
    if (today.review.length) steps.push("review");
    if (today.kana && !today.kana_done_today) steps.push("kana");
    if (today.unit) {
      const done = today.unit_steps || {};
      for (const s of today.unit.steps) if (!done[s]) steps.push(s);
    }
    return steps;
  }
  function runStep(step) {
    if (step === "review") return runReview(today.review);
    if (step === "kana") return runKana(today.kana);
    if (step === "learn") return runLearn(today.unit);
    if (step === "words") return runWords(today.unit);
    if (step === "grammar") return runGrammar(today.unit);
    if (step === "listen") return runListen(today.unit);
    return runSpeak(today.unit);
  }
  /** After a step: refresh progress, then go straight to the next planned step. */
  async function continuePlan() {
    await refresh();
    const next = planSteps()[0];
    return next ? runStep(next) : showHome();
  }
  function runNext() {
    const next = planSteps()[0];
    return next ? runStep(next) : showHome();
  }
  async function refresh() {
    today = await api("/api/course/today");
  }

  async function showHome() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.close();
    keys.primary = keys.hold = keys.replay = keys.choice = null;
    try {
      await refresh();
    } catch (err) {
      root.replaceChildren(el("div", { class: "home" }, el("p", { class: "verdict off", text: String(err.message || err) })));
      return;
    }
    const s = today.stats;
    const unit = today.unit;
    const done = today.unit_steps || {};
    const steps = planSteps();
    const pct = Math.round((100 * s.phrases_learned) / Math.max(1, s.phrases_total));

    // The next step is started by the main button, so its row gets no button of its own.
    const open = (key, fn) => (key === steps[0] ? null : fn);
    const rows = [];
    if (today.review.length) {
      // Only today's share is shown: the rest waits for later days, never piles up here.
      const secs = today.review.reduce((n, c) => n + ({ kana: 4, word: 4, listen: 8, speak: 12 }[c.kind === "phrase" ? c.skill : c.kind] || 8), 0);
      const n = today.review.length;
      rows.push(planRow("Review", `${n} card${n === 1 ? "" : "s"}, about ${Math.max(1, Math.round(secs / 60))} min`, false, open("review", () => runReview(today.review))));
    } else if (s.phrases_learned) {
      rows.push(planRow("Review", "Nothing left today", false, null));
    }
    const kp = today.kana_progress;
    if (today.kana) {
      const k = today.kana;
      const detail = `${k.title}: ${k.kana.map((x) => x.char).join(" ") || "reading practice"}`;
      rows.push(planRow("Kana", today.kana_done_today ? "Done for today" : detail, today.kana_done_today,
        today.kana_done_today ? () => runKana(k) : open("kana", () => runKana(k)),
        today.kana_done_today ? "Next lesson" : null));
    }
    if (unit) {
      const details = {
        learn: `${unit.phrases.length} phrases to learn`,
        words: `${unit.words.length} words`,
        grammar: `${unit.grammar.length} grammar point${unit.grammar.length === 1 ? "" : "s"}, ${unit.drill.length} questions`,
        listen: "A short conversation",
        speak: `Answer ${unit.speak.length} questions out loud`,
      };
      for (const step of unit.steps) {
        const ready = step === "learn" || done.learn;
        rows.push(planRow(STEP_NAMES[step], details[step], !!done[step], ready ? open(step, () => runStep(step)) : null));
      }
    }

    const kanaText = kp ? ` Hiragana ${kp.hiragana[0]}/${kp.hiragana[1]}, katakana ${kp.katakana[0]}/${kp.katakana[1]}.` : "";
    const progressText = s.phrases_learned
      ? `${s.phrases_learned} phrases and ${s.words_learned} words learned, ${s.phrases_strong} phrases remembered well.${kanaText} ${s.streak} day${s.streak === 1 ? "" : "s"} in a row.`
      : "About 15 minutes a day.";

    if (steps.length) keys.primary = runNext;
    root.replaceChildren(
      el("div", { class: "home" },
        unit
          ? el("div", { class: "home-unit" },
              el("p", { class: "home-kicker", text: `Unit ${unit.number} of ${s.units_total}` }),
              el("h1", { class: "home-title" }, unit.title, " ", el("span", { lang: "ja", text: unit.title_jp })),
              el("p", { class: "home-goal", text: unit.goal }))
          : el("div", { class: "home-unit" },
              el("h1", { class: "home-title", text: "You've finished all ten units" }),
              el("p", { class: "home-goal", text: "Reviews continue daily. Use Extra listening and Chat for more practice." })),
        el("p", { class: "home-progress", text: progressText }),
        el("div", { class: "home-bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
          el("span", { style: `width:${pct}%` })),
        rows.length ? el("ol", { class: "plan" }, rows) : null,
        steps.length
          ? el("div", { class: "home-actions" },
              el("button", { type: "button", class: "lesson-primary", onclick: runNext },
                s.studied_today ? "Continue" : "Start today's lesson", kbd("Enter")))
          : el("p", { class: "home-done", text: "Done for today. Next review: tomorrow." }),
        s.phrases_learned
          ? el("div", { class: "home-more" },
              el("button", { type: "button", class: "secondary", onclick: runExtraListening,
                "data-tip": "A new short conversation using only phrases you've learned" }, "Extra listening"),
              el("button", { type: "button", class: "secondary", onclick: goChat,
                "data-tip": "Free conversation. Kaiwa sticks to the phrases you've learned." }, "Open Chat"))
          : null,
        el("label", { class: "home-romaji" },
          el("input", { type: "checkbox", checked: showRomaji, onchange: (e) => { showRomaji = e.target.checked; writePref("kaiwa_course_romaji", showRomaji ? "1" : "0"); } }),
          " Show romaji for kana you haven't learned"),
      ),
    );
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
  function goChat() {
    const tab = document.querySelector('.tab[data-mode="chat"]');
    if (tab) tab.click();
  }

  // ---------- review ----------
  function runReview(cards) {
    const queue = cards.map((c) => ({ ...c, retried: false }));
    let index = 0;
    let right = 0;
    let total = queue.length;
    prefetch(queue.map((c) => [c.phrase ? c.phrase.jp : c.word ? c.word.jp : c.kana.char, {}]));

    // Word cards you haven't reached yet get swapped for short listening sentences
    // built from them (fetched in the background; the plain cards stay if it fails).
    const wordIds = queue.filter((c) => c.kind === "word").map((c) => c.card_id);
    if (wordIds.length >= 2) {
      postJson("/api/course/sentences", { card_ids: wordIds }).then(({ sentences }) => {
        for (const s of sentences || []) {
          const at = s.card_ids.map((id) => queue.findIndex((c, i) => i > index && c.card_id === id && !c.retried));
          if (at.some((i) => i < 0)) continue; // one of its words is already done
          for (const i of [...at].sort((a, b) => b - a)) queue.splice(i, 1);
          queue.splice(Math.min(...at), 0, { kind: "sentence", sentence: s, retried: false,
            covers: cards.filter((c) => s.card_ids.includes(c.card_id)) });
          total -= s.card_ids.length - 1;
          prefetch([[s.jp, {}]]);
        }
      }).catch(() => {});
    }

    function next() {
      if (index >= queue.length) return finish();
      const card = queue[index];
      if (card.kind === "sentence") sentenceCard(card);
      else if (card.kind === "kana") kanaCard(card);
      else if (card.kind === "word") wordCard(card);
      else if (card.skill === "listen") listenCard(card);
      else speakCard(card);
    }
    function gradeCard(card, good) {
      if (card.kind === "sentence") {
        // One answer grades every word the sentence covered; misses come back as single cards.
        for (const c of card.covers) postJson("/api/course/grade", { card_id: c.card_id, good }).catch(() => {});
        if (good) right += 1;
        else queue.push(...card.covers.map((c) => ({ ...c, retried: true })));
        index += 1;
        return next();
      }
      if (!card.retried) {
        postJson("/api/course/grade", { card_id: card.card_id, good }).catch(() => {});
        if (good) right += 1;
      }
      if (!good && !card.retried) queue.push({ ...card, retried: true });
      index += 1;
      next();
    }
    function gradeActions(card, suggestGood) {
      const missed = el("button", { type: "button", class: suggestGood ? "secondary" : "", onclick: () => gradeCard(card, false) }, "I missed it");
      const got = el("button", { type: "button", class: suggestGood ? "lesson-primary" : "secondary", onclick: () => gradeCard(card, true) }, "I knew it");
      return { buttons: [missed, got], primary: () => gradeCard(card, !!suggestGood) };
    }

    /** Auto-graded cards (kana, words): answer, see the result, move on. */
    function choiceCard(card, { prompt, big, bigJp, answer, pool, options, pics = false, after, audio, extra = null }) {
      const result = el("div", { class: "result" });
      const nextBtn = primaryButton("Next", () => gradeCard(card, lastRight));
      nextBtn.hidden = true;
      let lastRight = false;
      const body = el("div", { class: "card-body" },
        prompt ? el("p", { class: "prompt", text: prompt }) : null,
        big ? el("p", { class: bigJp ? "kana-big" : "prompt-en", lang: bigJp ? "ja" : null, text: big }) : null,
        audio ? playRow(audio) : null,
        extra,
        choiceBlock({
          options: options || choicesFor(answer, pool),
          answer,
          pics,
          onAnswer: async (right) => {
            lastRight = right;
            if (after) result.replaceChildren(after());
            if (audio) play(audio);
            if (right && !card.retried) {
              const here = onThisScreen();
              await wait(700);
              if (here()) advance();
            } else {
              nextBtn.hidden = false;
              keys.primary = advance;
            }
          },
        }),
        result,
      );
      function advance() { keys.primary = null; gradeCard(card, lastRight); }
      frame({ title: "Review", index: Math.min(index, queue.length - 1), total: queue.length, body, actions: [nextBtn],
        ask: { screen: "review " + card.kind, jp: card.word ? card.word.jp : card.kana ? card.kana.char : card.sentence ? card.sentence.jp : "", answer } });
      if (audio && !card.retried && card.kind === "sentence") play(audio);
      keys.primary = null;
      if (audio) keys.replay = () => play(audio);
    }
    function sentenceCard(card) {
      const s = card.sentence;
      const text = el("p", { class: "sentence-jp", lang: "ja", hidden: true, text: s.jp });
      const showText = el("button", { class: "secondary", type: "button", onclick: () => { text.hidden = false; showText.hidden = true; } },
        "Show text", kbd("T"));
      choiceCard(card, {
        prompt: "", big: "", answer: s.en, options: s.choices,
        audio: s.jp,
        extra: [el("div", { class: "lesson-play" }, showText), text],
        after: () => {
          text.hidden = false;
          showText.hidden = true;
          return el("p", { class: "sentence-words" }, s.words.map((w) =>
            el("span", {}, el("span", { lang: "ja", text: w.jp }), ` ${w.en}`)));
        },
      });
      keys.text = () => showText.click();
    }
    function kanaCard(card) {
      const k = card.kana;
      const pool = (today.kana_pool || []).filter((x) => x.ro !== k.ro).map((x) => x.ro);
      choiceCard(card, { prompt: "", big: k.char, bigJp: true, answer: k.ro, pool, audio: k.char });
    }
    function wordCard(card) {
      const w = card.word;
      const m = meaningChoices(w, today.words_pool || []);
      choiceCard(card, {
        prompt: "", big: w.jp, bigJp: true, answer: m.answer, options: m.options, pics: m.pics, audio: w.jp,
        after: () => needsRomaji(w.jp) ? el("p", { class: "phrase-ro", text: w.ro }) : el("span"),
      });
    }

    function listenCard(card) {
      const p = card.phrase;
      const answer = el("div", { class: "reveal", hidden: true }, phraseBlock(p));
      function reveal() {
        answer.hidden = false;
        const g = gradeActions(card, true);
        frameRefresh(g.buttons, g.primary);
      }
      const body = el("div", { class: "card-body" },
        el("p", { class: "prompt", text: card.retried ? "Once more. What does this mean?" : "Listen. What does it mean?" }),
        playRow(p.jp),
        answer,
      );
      const showBtn = primaryButton("Show meaning", reveal);
      function frameRefresh(buttons, primary) {
        root.querySelector(".lesson-actions").replaceChildren(...buttons);
        keys.primary = primary;
      }
      frame({ title: "Review", index: Math.min(index, queue.length - 1), total: queue.length, body, actions: [showBtn], primary: reveal,
        ask: { screen: "review listen", jp: p.jp, en: p.en, note: p.note } });
      keys.replay = () => play(p.jp);
      play(p.jp);
    }

    function speakCard(card) {
      const p = card.phrase;
      const result = el("div", { class: "result" });
      const answer = el("div", { class: "reveal", hidden: true });
      function showAnswer(suggestGood) {
        answer.hidden = false;
        answer.replaceChildren(phraseBlock(p), playRow(p.jp));
        keys.replay = () => play(p.jp);
        const g = gradeActions(card, suggestGood);
        root.querySelector(".lesson-actions").replaceChildren(...g.buttons);
        keys.primary = g.primary;
      }
      const hold = holdControl("Hold to say it", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          result.replaceChildren(verdictLine(r.band), heardLine("Sounded like ", r.heard), r.tip ? el("p", { class: "tip", text: r.tip }) : null);
          noteResult({ said: r.heard, band: r.band, tip: r.tip });
          showAnswer(r.band === "good");
          if (r.band !== "good") play(p.jp);
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        }
      }, showProblem(result));
      const body = el("div", { class: "card-body" },
        el("p", { class: "prompt", text: "Say this in Japanese" }),
        el("p", { class: "prompt-en", text: p.en }),
        hold,
        micRow(),
        result,
        answer,
      );
      const giveUp = el("button", { type: "button", class: "secondary", onclick: () => { showAnswer(false); play(p.jp); } }, "Show me");
      frame({ title: "Review", index: Math.min(index, queue.length - 1), total: queue.length, body, actions: [giveUp], hold,
        ask: { screen: "review speak", jp: p.jp, en: p.en, note: p.note } });
    }

    function finish() {
      const go = async () => { await refresh(); today.review = []; runNext(); };
      frame({
        title: "Review",
        body: el("div", { class: "card-body" },
          el("h3", { class: "end-title", text: `${right} of ${total} on the first try` }),
          el("p", { class: "prompt", text: "Missed phrases come back tomorrow." })),
        actions: [primaryButton("Continue", go)],
        primary: go,
      });
    }

    if (!queue.length) return showHome();
    next();
  }

  // ---------- new phrases ----------
  function runLearn(unit) {
    let i = 0;
    const phrases = unit.phrases;
    prefetch(phrases.map((p) => [p.jp, {}]));

    function show() {
      const p = phrases[i];
      const result = el("div", { class: "result" });
      const hold = holdControl("Hold and say it", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          result.replaceChildren(verdictLine(r.band), heardLine("Sounded like ", r.heard), r.tip ? el("p", { class: "tip", text: r.tip }) : null);
          noteResult({ said: r.heard, band: r.band, tip: r.tip });
          if (r.band !== "good") play(p.jp);
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        }
      }, showProblem(result));
      const last = i === phrases.length - 1;
      const actions = [];
      if (i > 0) actions.push(el("button", { type: "button", class: "secondary", onclick: () => { i -= 1; show(); } }, "Back"));
      actions.push(primaryButton(last ? "Finish" : "Next", next));
      frame({
        title: `New phrases, unit ${unit.number}`,
        index: i,
        total: phrases.length,
        body: el("div", { class: "card-body" }, phraseBlock(p), playRow(p.jp), hold, micRow(), result),
        actions,
        primary: next,
        hold,
        ask: { screen: "new phrase", jp: p.jp, en: p.en, note: p.note },
      });
      keys.replay = () => play(p.jp);
      play(p.jp);
    }
    async function next() {
      if (i < phrases.length - 1) {
        i += 1;
        return show();
      }
      await postJson("/api/course/step", { unit_id: unit.id, step: "learn" });
      continuePlan();
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
      onDone: async () => {
        await postJson("/api/course/step", { unit_id: unit.id, step: "listen" });
        continuePlan();
      },
    });
  }

  async function runExtraListening() {
    frame({ title: "Extra listening", body: el("p", { class: "pending", text: "Generating a conversation…" }) });
    let story;
    try {
      story = await api("/api/course/story", { method: "POST" });
    } catch (err) {
      frame({
        title: "Extra listening",
        body: el("p", { class: "verdict off", text: String(err.message || err) }),
        actions: [primaryButton("Try again", runExtraListening)],
        primary: runExtraListening,
      });
      return;
    }
    listenView({
      title: "Extra listening",
      dialogue: { scene: story.scene, lines: story.lines },
      questions: story.questions,
      doneLabel: "Another conversation",
      onDone: runExtraListening,
    });
  }

  function listenView({ title, dialogue: d, questions: qs, doneLabel, onDone }) {
    let showJp = false;
    let showEn = false;
    let playing = false;
    const answered = new Map();
    const lineEls = [];
    const voice = (line) => ({ voice: line.who === "b" ? "b" : "a" });
    prefetch(d.lines.map((line) => [line.jp, voice(line)]));

    const linesBox = el("ol", { class: "dialogue" });
    function renderLines() {
      linesBox.replaceChildren(...d.lines.map((line, idx) => {
        const row = el("li", { class: `line who-${line.who}` },
          el("button", { class: "line-play", type: "button", "aria-label": "Play this line", onclick: () => play(line.jp, voice(line)) },
            line.who === "b" ? "B" : "A"),
          el("div", { class: "line-text" },
            showJp
              ? el("span", { class: "line-jp", lang: "ja", text: line.jp })
              : el("span", { class: "line-hidden", text: "Text hidden" }),
            showEn ? el("span", { class: "line-en", text: line.en }) : null,
            showJp && line.gloss ? el("span", { class: "line-gloss", text: line.gloss }) : null,
          ),
        );
        lineEls[idx] = row;
        return row;
      }));
    }
    async function playAll() {
      if (playing) return;
      playing = true;
      playAllBtn.disabled = true;
      for (let idx = 0; idx < d.lines.length; idx++) {
        lineEls[idx]?.classList.add("speaking");
        await play(d.lines[idx].jp, voice(d.lines[idx]));
        lineEls[idx]?.classList.remove("speaking");
        await new Promise((r) => setTimeout(r, 300));
      }
      playing = false;
      playAllBtn.disabled = false;
      playAllBtn.firstChild.textContent = "Play again";
    }
    const playAllBtn = el("button", { type: "button", onclick: playAll }, "Play the conversation", kbd("R"));
    const toggleJp = el("button", { class: "secondary", type: "button", "aria-pressed": "false", onclick: () => {
      showJp = !showJp; toggleJp.setAttribute("aria-pressed", String(showJp)); renderLines();
    } }, "Japanese text");
    const toggleEn = el("button", { class: "secondary", type: "button", "aria-pressed": "false", onclick: () => {
      showEn = !showEn; toggleEn.setAttribute("aria-pressed", String(showEn)); renderLines();
    } }, "English");

    const doneBtn = primaryButton(doneLabel, onDone, { disabled: true });
    const questionsBox = el("div", { class: "questions" }, qs.map((q, qi) => {
      const feedback = el("p", { class: "verdict" });
      const choices = el("div", { class: "choices" }, q.choices.map((choice, ci) =>
        el("button", {
          class: "secondary", type: "button",
          onclick: (e) => {
            const right = ci === q.answer;
            answered.set(qi, right);
            for (const b of choices.children) b.disabled = true;
            e.currentTarget.classList.add(right ? "right" : "wrong");
            if (!right) choices.children[q.answer].classList.add("right");
            feedback.className = "verdict " + (right ? "good" : "off");
            feedback.textContent = right ? "Right." : "Not quite. Play it again and listen for it.";
            if (answered.size === qs.length) {
              doneBtn.disabled = false;
              keys.primary = onDone;
            }
          },
        }, choice)));
      return el("div", { class: "question" }, el("p", { class: "question-q", text: q.q }), choices, feedback);
    }));

    renderLines();
    frame({
      title,
      ask: { screen: "listening", scene: d.scene, lines: d.lines.map((l) => `${l.who}: ${l.jp} (${l.en})`), questions: qs.map((q) => q.q) },
      body: el("div", { class: "card-body" },
        el("p", { class: "prompt", text: d.scene || "Listen before showing the text." }),
        el("div", { class: "lesson-play" }, playAllBtn, toggleJp, toggleEn),
        linesBox,
        el("h3", { class: "questions-title", text: "Did you catch it?" }),
        questionsBox,
      ),
      actions: [doneBtn],
    });
    keys.replay = playAll;
  }

  // ---------- kana lesson ----------
  function runKana(lesson) {
    const items = lesson.kana;
    const title = lesson.script === "katakana" ? "Katakana" : "Hiragana";
    prefetch([...items.map((k) => [k.char, {}]), ...lesson.words.map((w) => [w.jp, {}])]);

    // 1. Meet each character (a rules-only lesson goes straight to the note).
    let i = 0;
    function intro() {
      if (!items.length) return note();
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
      function ask() {
        if (n >= queue.length) return words();
        const { k, mode } = queue[n];
        const nextBtn = primaryButton("Next", advance);
        nextBtn.hidden = true;
        function advance() { n += 1; ask(); }
        const block = mode === "read"
          ? choiceBlock({
              options: choicesFor(k.ro, pool.filter((x) => x.ro !== k.ro).map((x) => x.ro)),
              answer: k.ro,
              onAnswer: onAnswer,
            })
          : choiceBlock({
              options: choicesFor(k.char, pool.filter((x) => x.ro !== k.ro).map((x) => x.char)),
              answer: k.char, jp: true,
              onAnswer: onAnswer,
            });
        async function onAnswer(right) {
          play(k.char);
          if (!right) queue.push(queue[n]);
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
            block),
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

    async function finish() {
      await postJson("/api/course/kana", { lesson_id: lesson.id });
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
  function runWords(unit) {
    const words = unit.words;
    const PAGE = 5;
    prefetch(words.map((w) => [w.jp, {}]));
    let page = 0;
    const pages = Math.ceil(words.length / PAGE);

    // 1. Meet the words, five per screen.
    function intro() {
      const slice = words.slice(page * PAGE, page * PAGE + PAGE);
      const last = page === pages - 1;
      const go = () => { if (last) quiz(); else { page += 1; intro(); } };
      const actions = [];
      if (page > 0) actions.push(el("button", { type: "button", class: "secondary", onclick: () => { page -= 1; intro(); } }, "Back"));
      actions.push(primaryButton(last ? "Practice" : "Next", go));
      frame({
        title: `Words, unit ${unit.number}`, index: page, total: pages,
        ask: { screen: "word list", words: slice.map((w) => `${w.jp} = ${w.en}`) },
        body: el("div", { class: "card-body" },
          el("table", { class: "word-table" },
            el("tbody", {}, slice.map((w) => el("tr", {},
              el("td", {}, el("button", { class: "secondary line-play", type: "button", "aria-label": "Play", onclick: () => play(w.jp) }, "▶")),
              el("td", { class: "word-jp", lang: "ja", text: w.jp }),
              el("td", { class: "word-ro", text: needsRomaji(w.jp) ? w.ro : "" }),
              el("td", { class: "word-pic", text: w.pic || "" }),
              el("td", { class: "word-en", text: w.en })))))),
        actions, primary: go,
      });
    }

    // 2. Hear + see each word, pick its meaning. Misses come back once.
    function quiz() {
      const queue = shuffle(words).map((w) => ({ w, retried: false }));
      let n = 0;
      const total = queue.length;
      function ask() {
        if (n >= queue.length) return finish();
        const { w } = queue[n];
        const nextBtn = primaryButton("Next", advance);
        nextBtn.hidden = true;
        function advance() { n += 1; ask(); }
        frame({
          title: `Words, unit ${unit.number}`, index: Math.min(n, total - 1), total,
          ask: { screen: "word quiz", jp: w.jp, en: w.en },
          body: el("div", { class: "card-body" },
            el("p", { class: "kana-big kana-word", lang: "ja", text: w.jp }),
            needsRomaji(w.jp) ? el("p", { class: "phrase-ro", text: w.ro }) : null,
            playRow(w.jp),
            choiceBlock({
              ...meaningChoices(w, words),
              explain: w.pic ? w.en : "",
              onAnswer: async (right) => {
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

    async function finish() {
      await postJson("/api/course/step", { unit_id: unit.id, step: "words" });
      continuePlan();
    }
    intro();
  }

  // ---------- grammar ----------
  function runGrammar(unit) {
    const points = unit.grammar;
    prefetch(points.flatMap((g) => g.examples.map((ex) => [ex.jp, {}])));
    let gi = 0;

    // 1. Each point: a short explanation and examples you can play.
    function explain() {
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
      const explainBox = el("div", { class: "grammar-explain", hidden: true },
        g.explain.map((para) => el("p", { class: "grammar-text", text: para })));
      const meaningsBtn = el("button", { class: "secondary", type: "button", "aria-pressed": "false", onclick: () => {
        const on = list.classList.toggle("meanings-hidden");
        meaningsBtn.setAttribute("aria-pressed", String(!on));
      } }, "Meanings", kbd("M"));
      const explainBtn = el("button", { class: "secondary", type: "button", "aria-pressed": "false", onclick: () => {
        explainBox.hidden = !explainBox.hidden;
        explainBtn.setAttribute("aria-pressed", String(!explainBox.hidden));
      } }, "Explain");
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
          list,
          g.rule ? el("p", { class: "grammar-rule", text: g.rule }) : null,
          el("div", { class: "lesson-play" },
            el("button", { class: "secondary", type: "button", onclick: playAll }, "Play all", kbd("R")),
            meaningsBtn, explainBtn),
          explainBox),
        actions, primary: go,
      });
      const here = onThisScreen();
      keys.replay = playAll;
      keys.meanings = () => meaningsBtn.click();
      if (!g.rule) explainBox.hidden = false; // older content without a rule line
    }

    // 2. Practice questions with a one-line reason after each answer.
    function drill() {
      const qs = unit.drill;
      let n = 0;
      let right = 0;
      function ask() {
        if (n >= qs.length) return finish();
        const q = qs[n];
        const nextBtn = primaryButton(n === qs.length - 1 ? "Finish" : "Next", advance);
        nextBtn.hidden = true;
        function advance() { n += 1; ask(); }
        const answer = q.choices[q.answer];
        frame({
          title: `Grammar practice, unit ${unit.number}`, index: n, total: qs.length,
          ask: { screen: "grammar question", question: q.q, choices: q.choices, correct: answer, explain: q.explain },
          body: el("div", { class: "card-body" },
            q.scene
              ? el("p", { class: "scene", "data-tip": q.q, text: q.scene })
              : el("p", { class: "question-q", text: q.q }),
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
      async function finish() {
        await postJson("/api/course/step", { unit_id: unit.id, step: "grammar" });
        frame({
          title: `Grammar, unit ${unit.number}`,
          body: el("div", { class: "card-body" },
            el("h3", { class: "end-title", text: `${right} of ${qs.length} right` })),
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
    let t = 0;
    const tasks = unit.speak;
    prefetch(tasks.map((task) => [task.say, {}]));

    function show() {
      const task = tasks[t];
      const result = el("div", { class: "result" });
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
    async function next() {
      if (t < tasks.length - 1) {
        t += 1;
        return show();
      }
      await postJson("/api/course/step", { unit_id: unit.id, step: "speak" });
      done(unit);
    }
    show();
  }

  function done(unit) {
    frame({
      title: `Unit ${unit.number} done`,
      body: el("div", { class: "card-body" },
        el("h3", { class: "end-title", text: unit.title }),
        el("p", { class: "prompt", text: `${unit.phrases.length} phrases learned. They're in tomorrow's review.` })),
      actions: [
        el("button", { type: "button", class: "secondary", onclick: goChat }, "Use them in Chat"),
        primaryButton("Back to today", showHome),
      ],
      primary: showHome,
    });
  }

  window.KaiwaCourse = { show: showHome };

  if (document.getElementById("modeLearn")?.classList.contains("active")) {
    showHome();
  }
})();

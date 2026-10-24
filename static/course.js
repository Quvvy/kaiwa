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
  const keys = { primary: null, hold: null, replay: null, choice: null, meanings: null, text: null, tab: null,
    grade: null, space: null, undo: null };

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
  function choiceBlock({ options, answer, onAnswer, jp = false, explain = "" }) {
    const feedback = el("p", { class: "verdict" });
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
      onAnswer(right);
    }
    pendingChoice = pick; // frame() hands it to the number keys once the screen is up
    return el("div", { class: "choice-block" }, el("div", { class: "choices" }, buttons), feedback);
  }
  function meaningChoices(word, pool) {
    return { options: choicesFor(word.en, pool.map((w) => w.en)), answer: word.en };
  }

  /** First answers inside lessons count as each new card's first review. */
  function lessonGrade(cardId, outcome) {
    postJson("/api/course/grade", { card_id: cardId, ...outcome }).catch(() => {});
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
    keys.tab = null;
    keys.grade = null;
    keys.space = null;
    keys.undo = null;
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
  /** Today's steps, decided by the server's pacing (state.plan_today). */
  function planSteps() {
    return [...(today.plan || [])];
  }
  function runStep(step) {
    if (step === "review") return runReview(today.review);
    if (step === "recap") return runReview(today.recap || [], { title: "Recap", planStep: "recap" });
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
  let UNIT_TITLES = [];
  async function refresh() {
    today = await api("/api/course/today");
    if (today.unit_titles) UNIT_TITLES = today.unit_titles;
  }

  async function showHome() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
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
    if ((today.recap || []).length) {
      const n = today.recap.length;
      rows.push(planRow("Recap", `${n} new card${n === 1 ? "" : "s"}, a second look`, false,
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
        words: `${unit.words.length} words`,
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

    const kanaText = kp ? ` Hiragana ${kp.hiragana[0]}/${kp.hiragana[1]}, katakana ${kp.katakana[0]}/${kp.katakana[1]}.` : "";
    const progressText = s.phrases_learned
      ? `${s.phrases_learned} phrases and ${s.words_learned} words learned, ${s.phrases_strong} phrases remembered well.${kanaText} ${s.streak} day${s.streak === 1 ? "" : "s"} in a row.`
      : "About 15 minutes a day.";

    if (placementAfterHome) {
      placementAfterHome = false;
      return runPlacement();
    }
    if (steps.length) keys.primary = runNext;
    root.replaceChildren(
      el("div", { class: "home" },
        unit
          ? el("div", { class: "home-unit" },
              el("p", { class: "home-kicker", text: `Unit ${unit.number} of ${s.units_total}` }),
              el("h1", { class: "home-title" }, unit.title, " ", el("span", { lang: "ja", text: unit.title_jp })),
              el("p", { class: "home-goal", text: unit.goal }))
          : el("div", { class: "home-unit" },
              el("h1", { class: "home-title", text: `You've finished all ${s.units_total} units` }),
              el("p", { class: "home-goal", text: "Reviews continue daily. Use Extra listening and Chat for more practice." })),
        el("p", { class: "home-progress", text: progressText }),
        el("div", { class: "home-bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
          el("span", { style: `width:${pct}%` })),
        rows.length ? el("ol", { class: "plan" }, rows) : null,
        steps.length
          ? el("div", { class: "home-actions" },
              el("button", { type: "button", class: "lesson-primary", onclick: runNext },
                s.studied_today ? "Continue" : "Start today's lesson", kbd("Enter")))
          : el("p", { class: "home-done", text: "Done for today. More tomorrow." }),
        !today.placement && !s.phrases_learned && !(today.kana_progress && today.kana_progress.lessons_done)
          ? el("div", { class: "home-placement" },
              el("p", { text: "Already know some Japanese? A short test finds where to start." }),
              el("button", { type: "button", class: "secondary", onclick: runPlacement }, "Take the placement test (about 8 min)"))
          : null,
        today.retention ? retentionLine(today.retention) : null,
        today.catching_up
          ? el("p", { class: "home-note", text: "Reviews only today: there's a backlog to clear first. New lessons are still one click away below." })
          : null,
        s.phrases_learned || (today.kana_progress && today.kana_progress.lessons_done)
          ? el("div", { class: "home-more" },
              el("button", { type: "button", class: "secondary", onclick: runStats,
                "data-tip": "Retention, what's coming up, your cards, and how scheduling works" }, "Stats"),
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
  /** "You remember 88% of reviews" with a per-kind breakdown in the tooltip. */
  function retentionLine(r) {
    const parts = Object.entries(r.by_kind).map(([k, v]) => `${k} ${v}%`).join(", ");
    const tip = `Out of ${r.reviews} reviews in the last ${r.days} days. Kaiwa aims for ${r.target}%: `
      + `higher means reviews could be spread further, lower means more help is due.`
      + (parts ? ` By kind: ${parts}.` : "")
      + (r.leeches ? ` ${r.leeches} card${r.leeches === 1 ? " is" : "s are"} getting extra help.` : "");
    return el("p", { class: "home-retention", "data-tip": tip },
      el("strong", { text: `${r.percent}%` }), ` remembered in reviews (last ${r.days} days)`);
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
      const what = r.card.word ? r.card.word.jp : r.card.phrase ? r.card.phrase.jp : r.card.kana ? r.card.kana.char : "";
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
    box.hold = hold;
    if (typing) setTimeout(() => input.focus(), 0);
    return box;
  }
  function answerMode() {
    return readPref("kaiwa_answer_mode", "speak") === "type" ? "type" : "speak";
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
    prefetch(queue.map((c) => [c.phrase ? c.phrase.jp : c.word ? c.word.jp : c.kana.char, {}]));

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
      else if (card.kind === "phrase" && card.skill === "speak") speakCard(card);
      else if (card.kind === "phrase") listenCard(card);
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
      bar.replaceChildren(...[
        el("span", { class: "grade-label", text: gradeLabel(r) }),
        el("span", { class: "grade-chips", "aria-label": "Change the grade" }, chips),
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
    function choiceCard(card, { big, bigJp, answer, options, audio, after, extra = null, fmt, askJp }) {
      const result = el("div", { class: "result" });
      const slot = el("div", { class: "grade-slot" });
      let helped = false;
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      const body = el("div", { class: "card-body" },
        repeatTag(card),
        big ? el("p", { class: bigJp ? "kana-big" : "prompt-en", lang: bigJp ? "ja" : null, text: big }) : null,
        audio ? playRow(audio) : null,
        typeof extra === "function" ? extra(() => { helped = true; }) : extra,
        choiceBlock({
          options, answer,
          onAnswer: (correct) => {
            if (after) result.replaceChildren(after());
            if (audio) play(audio);
            answered(card, { correct, ms: elapsed(), helped, fmt }, slot, nextBtn);
          },
        }),
        result,
        slot,
      );
      frame({ title, ...counter(), body, actions: [nextBtn],
        ask: { screen: `${title.toLowerCase()} ${card.kind}`, jp: askJp || "", answer } });
      if (audio) keys.replay = () => play(audio);
    }
    function kanaChoice(card) {
      const k = card.kana;
      const pool = (today.kana_pool || []).filter((x) => x.ro !== k.ro).map((x) => x.ro);
      choiceCard(card, { big: k.char, bigJp: true, answer: k.ro, options: choicesFor(k.ro, pool), audio: k.char,
        fmt: "kana:choice", askJp: k.char });
    }
    function wordChoice(card) {
      const w = card.word;
      const m = meaningChoices(w, today.words_pool || []);
      choiceCard(card, { big: w.jp, bigJp: true, answer: m.answer, options: m.options, audio: w.jp, fmt: "word:choice", askJp: w.jp,
        after: () => needsRomaji(w.jp) ? el("p", { class: "phrase-ro", text: w.ro }) : el("span") });
      play(w.jp);
    }
    function listenCard(card) {
      const p = card.phrase;
      const pool = (today.phrases_pool || []).map((x) => x.en);
      choiceCard(card, { answer: p.en, options: choicesFor(p.en, pool), audio: p.jp, fmt: "phrase:listen", askJp: p.jp,
        after: () => phraseBlock(p) });
      play(p.jp);
    }
    function sentenceCard(card) {
      const s = card.sentence;
      const text = el("p", { class: "sentence-jp", lang: "ja", hidden: true, text: s.jp });
      choiceCard(card, {
        answer: s.en, options: s.choices, audio: s.jp, fmt: "sentence", askJp: s.jp,
        extra: (markHelped) => {
          const showText = el("button", { class: "secondary", type: "button", onclick: () => {
            markHelped(); text.hidden = false; showText.hidden = true; } }, "Show text", kbd("T"));
          keys.text = () => showText.click();
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

    /** Known kana and words: produce the answer (say it, or type it). */
    function produceCard(card) {
      const isKana = card.kind === "kana";
      const target = isKana ? card.kana.char : card.word.jp;
      const result = el("div", { class: "result" });
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
        ];
      }
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
          settle({ correct, ms }, reveal(correct, ""));
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
            settle({ correct, ms, band: r.band, spoken: true },
              [...reveal(correct, r.band), heardLine("Sounded like ", r.heard), r.tip ? el("p", { class: "tip", text: r.tip }) : null].filter(Boolean));
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
        settle({ correct: false, ms: elapsed() }, reveal(false, "")) }, "Show me");
      frame({
        title, ...counter(),
        body: el("div", { class: "card-body" },
          repeatTag(card),
          isKana
            ? el("p", { class: "kana-big", lang: "ja", text: target })
            : el("p", { class: "prompt-en", text: card.word.en }),
          el("p", { class: "prompt", text: isKana ? "Say or type its sound." : "Say it in Japanese, or type it." }),
          box, micRow(), result, slot),
        actions: [dontKnow, nextBtn],
        hold: box.hold,
        ask: { screen: `${title.toLowerCase()} produce ${card.kind}`, jp: isKana ? target : "", en: isKana ? "" : card.word.en },
      });
      keys.tab = () => box.focusTyping();
    }

    function speakCard(card) {
      const p = card.phrase;
      const result = el("div", { class: "result" });
      const slot = el("div", { class: "grade-slot" });
      const answer = el("div", { class: "reveal", hidden: true });
      const nextBtn = primaryButton("Next", () => advance());
      nextBtn.hidden = true;
      let startedAt = 0;
      function settle(o) {
        if (current.answered) return;
        answer.hidden = false;
        answer.replaceChildren(phraseBlock(p), playRow(p.jp));
        keys.replay = () => play(p.jp);
        giveUp.hidden = true;
        answered(card, { ...o, fmt: "phrase:speak" }, slot, nextBtn);
      }
      const hold = holdControl("Hold to say it", async (blob, ext) => {
        const ms = Math.round(startedAt - shownAt);
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          result.replaceChildren(verdictLine(r.band), heardLine("Sounded like ", r.heard), r.tip ? el("p", { class: "tip", text: r.tip }) : null);
          noteResult({ said: r.heard, band: r.band, tip: r.tip });
          settle({ correct: r.band !== "off", ms, band: r.band });
          if (r.band !== "good") play(p.jp);
        } catch (err) {
          result.replaceChildren(el("p", { class: "verdict off", text: String(err.message || err) }));
        }
      }, showProblem(result));
      hold.addEventListener("pointerdown", () => { startedAt = performance.now(); }, true);
      const holdStart = hold.holdApi.start;
      hold.holdApi.start = () => { startedAt = performance.now(); return holdStart(); };
      const giveUp = el("button", { type: "button", class: "secondary", onclick: () => {
        settle({ correct: false, ms: elapsed() }); play(p.jp); } }, "Show me");
      frame({ title, ...counter(),
        body: el("div", { class: "card-body" },
          repeatTag(card),
          el("p", { class: "prompt", text: "Say this in Japanese" }),
          el("p", { class: "prompt-en", text: p.en }),
          hold, micRow(), result, answer, slot),
        actions: [giveUp, nextBtn], hold,
        ask: { screen: `${title.toLowerCase()} speak`, jp: p.jp, en: p.en, note: p.note } });
    }

    /**
     * After answering a card you keep forgetting: a new way in (its parts and a
     * memory hook, written once by Flash and kept), then on with the review.
     */
    async function leechHelp(card) {
      const item = card.word || card.phrase || (card.kana && { jp: card.kana.char, en: card.kana.ro });
      const hookBox = el("div", { class: "leech-hook" }, el("p", { class: "pending", text: "Writing a memory hook…" }));
      current = null;
      frame({
        title, ...counter(),
        body: el("div", { class: "card-body leech" },
          el("p", { class: "leech-note", text: "This one keeps slipping. Here's another way in." }),
          el("p", { class: "kana-big kana-word", lang: "ja", text: item.jp }),
          el("p", { class: "phrase-en", text: item.en }),
          playRow(item.jp),
          hookBox),
        actions: [primaryButton("Continue", next)],
        primary: next,
        ask: { screen: "leech help", jp: item.jp, en: item.en },
      });
      keys.undo = undoLast;
      keys.replay = () => play(item.jp);
      play(item.jp);
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
      const go = async () => {
        await refresh();
        today.plan = (today.plan || []).filter((s) => s !== planStep);
        runNext();
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

  async function runStats() {
    stopAudio();
    screenId += 1;
    askContext = null;
    askPanel.refresh();
    keys.primary = keys.hold = keys.replay = keys.choice = null;
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
        figure(s.today.answers ? `${Math.round((100 * s.today.right) / s.today.answers)}%` : "–", "not Again"),
        figure(`${s.today.minutes}`, "minutes answering"),
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

    const stageNames = { new: "New", learning: "Learning", young: "Young", mature: "Mature" };
    const cardsTable = section("Your cards",
      el("table", { class: "stats-table" },
        el("thead", {}, el("tr", {}, el("th"), Object.values(stageNames).map((n) => el("th", { text: n })))),
        el("tbody", {}, Object.entries(s.stages).map(([kind, row]) => el("tr", {},
          el("th", { text: kind }), Object.keys(stageNames).map((k) => el("td", { text: String(row[k]) })))))),
      el("p", { class: "stats-caption", text: "Learning: in its first short steps. Young: remembered for under 3 weeks. Mature: 3 weeks or more." }));

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
            const item = c.word || c.phrase || { jp: c.kana.char, en: c.kana.ro };
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

    const how = section("How scheduling works",
      el("p", { class: "stats-text", text: "Kaiwa estimates how long you'll remember each card and brings it back just before you'd forget, aiming for 90% recall." }),
      el("p", { class: "stats-text", text: "New and missed cards come back within minutes, then the next day, then further apart each time you get them right. That's why you see some cards twice in a session." }),
      el("p", { class: "stats-text", text: "The grade after each answer comes from how you did: wrong is Again; right but slow, close, or with help is Hard; right at your usual speed is Good; much faster than usual is Easy. Press 1–4 to change it, Ctrl+Z to undo an answer." }));

    root.replaceChildren(el("div", { class: "home stats" },
      el("div", { class: "lesson-top" },
        el("button", { class: "secondary lesson-exit", type: "button", onclick: () => showHome() }, "Back"),
        el("h2", { class: "lesson-title", text: "Stats" })),
      today, retention, forecast, cardsTable, intervals, calendar, tricky, grading, how));
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
        const result = el("div", { class: "result" });
        const hold = holdControl("Hold and say it", async (blob, ext) => {
          result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
          try {
            const r = await api("/api/course/check_text", { method: "POST", body: audioForm(blob, ext, { target: item.jp }) });
            const judged = r.band === "good" ? 1 : r.band === "close" ? 0.5 : 0;
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
          el("p", { class: "lesson-note", text: "Last part: hear a phrase, then hold the bar (or Space) and say it back. It measures how much you can take in and reproduce." }),
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
    let i = 0;
    const phrases = unit.phrases;
    prefetch(phrases.map((p) => [p.jp, {}]));
    const spoken = new Set();

    function show() {
      const p = phrases[i];
      const result = el("div", { class: "result" });
      const hold = holdControl("Hold and say it", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "pending", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          result.replaceChildren(verdictLine(r.band), heardLine("Sounded like ", r.heard), r.tip ? el("p", { class: "tip", text: r.tip }) : null);
          noteResult({ said: r.heard, band: r.band, tip: r.tip });
          if (!spoken.has(p.id)) {
            spoken.add(p.id); // repeating right after hearing it: no timing, just whether it came out
            lessonGrade(`${p.id}:speak`, { correct: r.band !== "off", band: r.band, fmt: "phrase:speak:learn" });
          }
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

  /**
   * A listening exercise laid out as a message thread of voice bubbles.
   * Lines arrive one by one as they're spoken. Text is per line and only offered
   * after one full listen (Japanese first, English on a second click); questions
   * appear after that first listen too, and a miss offers another listen, not text.
   */
  function listenView({ title, dialogue: d, questions: qs, doneLabel, onDone }) {
    // Up to four speakers: A and C on the left, B and D on the right, each its own voice.
    const who = (line) => ("abcd".includes(line.who) && line.who ? line.who : "a");
    const side = (line) => ("bd".includes(who(line)) ? "right" : "left");
    const voice = (line) => ({ voice: who(line) });
    prefetch(d.lines.map((line) => [line.jp, voice(line)]));
    const here = () => thread.isConnected;
    let playing = false;
    let heard = 0;
    let peeked = false;
    let revealed = 0; // how many bubbles have arrived in the thread
    const answered = new Map();

    const thread = el("div", { class: "thread", "data-empty": "Press play and just listen." });
    const bubbles = d.lines.map((line, idx) => {
      const textBox = el("div", { class: "bubble-text", hidden: true });
      let level = 0; // 0 voice only, 1 + Japanese, 2 + English
      const peek = el("button", { class: "bubble-peek", type: "button", hidden: true, "aria-label": "Show text",
        "data-tip": "Show this line", onclick: (e) => {
          e.stopPropagation();
          level = Math.min(2, level + 1);
          peeked = true;
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

    async function playLine(idx) {
      if (playing) return;
      const b = bubbles[idx];
      b.bubble.classList.add("speaking");
      await play(d.lines[idx].jp, voice(d.lines[idx]));
      b.bubble.classList.remove("speaking");
    }

    async function playAll() {
      if (playing) return;
      playing = true;
      playBtn.disabled = true;
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
        await play(d.lines[idx].jp, voice(d.lines[idx]));
        b.bubble.classList.remove("speaking");
        await wait(350);
      }
      playing = false;
      playBtn.disabled = false;
      heard += 1;
      playBtn.firstChild.textContent = "Play again";
      heardNote.textContent = heard === 1 ? "Heard once" : `Heard ${heard} times`;
      if (heard === 1) {
        // Only now: per-line text, and the questions.
        for (const b of bubbles) b.peek.hidden = false;
        questionsBox.hidden = false;
      }
    }

    const playBtn = el("button", { type: "button", onclick: playAll }, "Play the conversation", kbd("R"));
    const heardNote = el("span", { class: "heard-note" });

    const doneBtn = primaryButton(doneLabel, onDone, { disabled: true });
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
              for (const b of choices.children) b.disabled = true;
              e.currentTarget.classList.add(right ? "right" : "wrong");
              if (!right) choices.children[q.answer].classList.add("right");
              feedback.className = "verdict " + (right ? "good" : "off");
              feedback.textContent = right ? "Right." : "Not quite.";
              again.hidden = right;
              if (answered.size === qs.length) {
                doneBtn.disabled = false;
                keys.primary = onDone;
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
        el("div", { class: "listen-bar" }, playBtn, heardNote),
        thread,
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
      const graded = new Set();
      function ask() {
        if (n >= queue.length) return words();
        const { k, mode } = queue[n];
        const shown = performance.now();
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
          if (mode === "read" && !graded.has(k.char)) {
            graded.add(k.char);
            lessonGrade(`kana.${k.char}:read`, { correct: right, ms: Math.round(performance.now() - shown), fmt: "kana:choice" });
          }
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
        const { w, retried } = queue[n];
        const shown = performance.now();
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
              onAnswer: async (right) => {
                if (!retried) lessonGrade(`${w.id}:mean`, { correct: right, ms: Math.round(performance.now() - shown), fmt: "word:choice" });
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

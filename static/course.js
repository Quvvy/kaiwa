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
  const keys = { primary: null, hold: null, replay: null };

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
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === " " && keys.hold) {
      e.preventDefault();
      if (!e.repeat) keys.hold.start();
    } else if (e.key === "Enter" && keys.primary && !(tag === "BUTTON" && e.target.matches(":focus-visible"))) {
      e.preventDefault();
      keys.primary();
    } else if ((e.key === "r" || e.key === "R") && keys.replay && !e.repeat) {
      e.preventDefault();
      keys.replay();
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

  function audioFor(text, { slow = false, voice = "a" } = {}) {
    const key = `${voice}|${slow ? 1 : 0}|${text}`;
    if (!audioCache.has(key)) {
      const pending = postJson("/api/course/tts", { text, slow, voice }).then((d) => d.audio_base64);
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
    audioProblem = err ? "No audio: the voice engine isn't running. Restart Kaiwa or switch engines in Settings → Speech." : "";
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
  function phraseBlock(p) {
    return el("div", { class: "phrase" },
      el("p", { class: "phrase-jp", lang: "ja", text: p.jp }),
      showRomaji && p.ro ? el("p", { class: "phrase-ro", text: p.ro }) : null,
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

  // ---------- frame ----------
  /** One screen of a lesson: top bar, optional sequence bar, content, action footer. */
  function frame({ title, index, total, body, actions = [], primary = null, hold = null }) {
    stopAudio();
    keys.primary = primary;
    keys.hold = hold ? hold.holdApi : null;
    keys.replay = null;
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
  }
  function primaryButton(label, onclick, { disabled = false } = {}) {
    return el("button", { type: "button", class: "lesson-primary", disabled, onclick }, label, kbd("Enter"));
  }

  // ---------- home ----------
  function planSteps() {
    const steps = [];
    if (today.review.length) steps.push("review");
    if (today.unit) {
      const done = today.unit_steps || {};
      for (const s of ["learn", "listen", "speak"]) if (!done[s]) steps.push(s);
    }
    return steps;
  }
  function runNext() {
    const next = planSteps()[0];
    if (!next) return showHome();
    if (next === "review") return runReview(today.review);
    if (next === "learn") return runLearn(today.unit);
    if (next === "listen") return runListen(today.unit);
    return runSpeak(today.unit);
  }
  async function refresh() {
    today = await api("/api/course/today");
  }

  async function showHome() {
    stopAudio();
    keys.primary = keys.hold = keys.replay = null;
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
    if (today.review_total) {
      rows.push(planRow("Review", `${today.review_total} phrase${today.review_total === 1 ? "" : "s"} due`, false, open("review", () => runReview(today.review))));
    } else if (s.phrases_learned) {
      rows.push(planRow("Review", "Nothing due today", false, null));
    }
    if (unit) {
      rows.push(planRow("New phrases", `${unit.phrases.length} phrases to learn`, !!done.learn, open("learn", () => runLearn(unit))));
      rows.push(planRow("Listen", "A short conversation", !!done.listen, done.learn ? open("listen", () => runListen(unit)) : null));
      rows.push(planRow("Speak", `Answer ${unit.speak.length} questions out loud`, !!done.speak, done.learn ? open("speak", () => runSpeak(unit)) : null));
    }

    const progressText = s.phrases_learned
      ? `${s.phrases_learned} of ${s.phrases_total} phrases learned, ${s.phrases_strong} remembered well. ${s.streak} day${s.streak === 1 ? "" : "s"} in a row.`
      : "About 10 minutes per lesson.";

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
          " Show romaji"),
      ),
    );
  }
  function planRow(name, detail, isDone, onOpen) {
    return el("li", { class: "plan-row" + (isDone ? " done" : "") },
      el("span", { class: "plan-name", text: name }),
      el("span", { class: "plan-detail", text: isDone ? "Done" : detail }),
      onOpen
        ? el("button", { class: "secondary", type: "button", onclick: onOpen }, isDone ? "Redo" : "Open")
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
    const total = queue.length;
    prefetch(queue.map((c) => [c.phrase.jp, {}]));

    function next() {
      if (index >= queue.length) return finish();
      const card = queue[index];
      if (card.skill === "listen") listenCard(card);
      else speakCard(card);
    }
    function gradeCard(card, good) {
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
      frame({ title: "Review", index: Math.min(index, queue.length - 1), total: queue.length, body, actions: [showBtn], primary: reveal });
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
      frame({ title: "Review", index: Math.min(index, queue.length - 1), total: queue.length, body, actions: [giveUp], hold });
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
      await refresh();
      runListen(unit);
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
        await refresh();
        runSpeak(unit);
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

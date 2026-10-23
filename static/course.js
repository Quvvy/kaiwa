/* Kaiwa daily lesson (Learn tab): Review → Learn → Listen → Speak.
 * Self-contained: its own audio player and hold-to-talk recorder.
 * Mounted into #course; index.html calls KaiwaCourse.show() when the tab opens. */
(() => {
  "use strict";

  const root = document.getElementById("course");
  if (!root) return;

  const STEP_LABELS = { review: "Review", learn: "New phrases", listen: "Listen", speak: "Speak" };
  let today = null;
  let showRomaji = readPref("kaiwa_course_romaji", "1") === "1";

  // ---------- small helpers ----------
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
  async function api(path, opts) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    return data;
  }
  function postJson(path, body) {
    return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  function shuffle(items) {
    const a = items.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // ---------- audio ----------
  const audioCache = new Map();
  let currentAudio = null;
  let audioNotice = null;

  async function audioFor(text, { slow = false, voice = "a" } = {}) {
    const key = `${voice}|${slow ? 1 : 0}|${text}`;
    if (!audioCache.has(key)) {
      audioCache.set(key, postJson("/api/course/tts", { text, slow, voice }).then((d) => d.audio_base64));
    }
    try {
      return await audioCache.get(key);
    } catch (err) {
      audioCache.delete(key);
      throw err;
    }
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
      showAudioProblem(err);
      return;
    }
    clearAudioProblem();
    await new Promise((resolve) => {
      const audio = new Audio("data:audio/wav;base64," + b64);
      currentAudio = audio;
      audio.addEventListener("ended", resolve, { once: true });
      audio.addEventListener("error", resolve, { once: true });
      audio.play().catch(resolve);
    });
  }
  function prefetch(text, opts) {
    audioFor(text, opts).catch(() => {});
  }
  function showAudioProblem(err) {
    if (audioNotice) return;
    audioNotice = el("p", { class: "course-alert", text: "No audio: the voice engine isn't running. " + String(err.message || err).split(".")[0] + "." });
    root.prepend(audioNotice);
  }
  function clearAudioProblem() {
    if (audioNotice) audioNotice.remove();
    audioNotice = null;
  }
  function playButtons(text, opts = {}) {
    return el("div", { class: "course-play-row" },
      el("button", { class: "secondary course-play", type: "button", onclick: () => play(text, opts) }, "▶ Play"),
      el("button", { class: "secondary course-play", type: "button", onclick: () => play(text, { ...opts, slow: true }) }, "Slow"),
    );
  }

  // ---------- hold-to-talk recorder ----------
  function holdButton(label, onAudio) {
    const btn = el("button", { class: "course-hold", type: "button" }, label);
    let rec = null;
    let chunks = [];
    let stream = null;
    let startedAt = 0;
    let wantStop = false;
    let starting = false;

    async function start() {
      if (rec || starting || btn.disabled) return;
      starting = true;
      wantStop = false;
      stopAudio();
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
      } catch (err) {
        starting = false;
        btn.textContent = "Microphone blocked — allow it and try again";
        return;
      }
      starting = false;
      if (wantStop) { stream.getTracks().forEach((t) => t.stop()); return; }
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m)) || "";
      rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      chunks = [];
      rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const type = rec.mimeType || mime || "audio/webm";
        const blob = new Blob(chunks, { type });
        const held = Date.now() - startedAt;
        rec = null;
        btn.classList.remove("recording");
        btn.textContent = label;
        if (blob.size < 800 || held < 300) {
          btn.textContent = "Hold a little longer";
          setTimeout(() => { btn.textContent = label; }, 1400);
          return;
        }
        onAudio(blob, type.includes("mp4") ? "m4a" : "webm");
      };
      rec.start(250);
      startedAt = Date.now();
      btn.classList.add("recording");
      btn.textContent = "Listening… release when done";
      if (wantStop) stop();
    }
    function stop() {
      if (starting) { wantStop = true; return; }
      if (rec && rec.state === "recording") {
        rec.requestData();
        rec.stop();
      }
    }
    btn.addEventListener("pointerdown", (e) => { e.preventDefault(); btn.setPointerCapture?.(e.pointerId); start(); });
    btn.addEventListener("pointerup", stop);
    btn.addEventListener("pointercancel", stop);
    btn.addEventListener("keydown", (e) => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); start(); } });
    btn.addEventListener("keyup", (e) => { if (e.key === " " || e.key === "Enter") stop(); });
    return btn;
  }

  function audioForm(blob, ext, fields) {
    const form = new FormData();
    form.append("audio", blob, "utterance." + ext);
    for (const [k, v] of Object.entries(fields)) form.append(k, String(v));
    return form;
  }

  // ---------- phrase display ----------
  function phraseBlock(p, { big = true } = {}) {
    return el("div", { class: "course-phrase" },
      el("p", { class: big ? "course-jp course-jp-big" : "course-jp", lang: "ja", text: p.jp }),
      showRomaji && p.ro ? el("p", { class: "course-ro", text: p.ro }) : null,
      el("p", { class: "course-en", text: p.en }),
      p.note ? el("p", { class: "course-note", text: p.note }) : null,
    );
  }
  function romajiToggle(rerender) {
    return el("label", { class: "course-toggle" },
      el("input", {
        type: "checkbox",
        checked: showRomaji,
        onchange: (e) => { showRomaji = e.target.checked; writePref("kaiwa_course_romaji", showRomaji ? "1" : "0"); rerender(); },
      }),
      " Romaji",
    );
  }
  function bandMessage(band) {
    if (band === "good") return { cls: "good", text: "Nice — that's it." };
    if (band === "close") return { cls: "close", text: "Close. Listen once more and try again." };
    return { cls: "off", text: "Not quite. Play it slowly, then try again." };
  }

  // ---------- frame ----------
  function frame(title, progressText, body, { onBack } = {}) {
    stopAudio();
    root.replaceChildren(
      el("div", { class: "course-top" },
        el("button", { class: "secondary course-back", type: "button", onclick: onBack || (() => showHome()) }, "← Today"),
        el("div", { class: "course-top-title" }, el("span", { class: "meta", text: title }), progressText ? el("span", { class: "course-count", text: progressText }) : null),
      ),
      body,
    );
    if (audioNotice) root.prepend(audioNotice);
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
    const steps = planSteps();
    const next = steps[0];
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
    try {
      await refresh();
    } catch (err) {
      root.replaceChildren(el("p", { class: "course-alert", text: String(err.message || err) }));
      return;
    }
    const s = today.stats;
    const unit = today.unit;
    const steps = planSteps();
    const done = today.unit_steps || {};

    const rows = [];
    if (today.review_total) {
      rows.push(planRow("Review", `${today.review_total} phrase${today.review_total === 1 ? "" : "s"} due`, false, () => runReview(today.review)));
    } else if (s.phrases_learned) {
      rows.push(planRow("Review", "Nothing due — reviews come back on their own schedule", true, null, false));
    }
    if (unit) {
      rows.push(planRow("New phrases", `${unit.phrases.length} phrases`, !!done.learn, () => runLearn(unit)));
      rows.push(planRow("Listen", "A short conversation", !!done.listen, () => runListen(unit), !!done.learn));
      rows.push(planRow("Speak", `Answer ${unit.speak.length} questions`, !!done.speak, () => runSpeak(unit), !!done.learn));
    }

    const pct = Math.round((100 * s.phrases_learned) / Math.max(1, s.phrases_total));
    root.replaceChildren(
      el("div", { class: "course-home" },
        el("div", { class: "course-hero" },
          el("div", { class: "meta", text: "Today" }),
          unit
            ? el("h2", { class: "course-title" }, `Unit ${unit.number} · ${unit.title} `, el("span", { class: "course-title-jp", lang: "ja", text: unit.title_jp }))
            : el("h2", { class: "course-title", text: "Course complete — keep reviewing" }),
          unit ? el("p", { class: "course-goal", text: unit.goal }) : null,
        ),
        el("div", { class: "course-stats" },
          stat(s.phrases_learned, "phrases learned"),
          stat(s.phrases_strong, "remembered well"),
          stat(s.streak, s.streak === 1 ? "day streak" : "days in a row"),
          stat(`${s.units_done}/${s.units_total}`, "units"),
        ),
        el("div", { class: "course-bar", title: `${pct}% of the beginner course` }, el("span", { style: `width:${pct}%` })),
        el("ol", { class: "course-plan" }, rows),
        steps.length
          ? el("button", { class: "course-cta", type: "button", onclick: runNext }, s.studied_today ? "Continue" : "Start today's lesson")
          : el("div", { class: "course-done-today" },
              el("p", { text: "You're done for today. Come back tomorrow for your reviews." }),
              el("button", { class: "secondary", type: "button", onclick: () => goChat() }, "Try your phrases in Chat"),
            ),
        s.phrases_learned
          ? el("button", { class: "secondary course-extra", type: "button", onclick: runExtraListening },
              el("strong", { text: "Extra listening" }),
              el("span", { text: "A new short conversation using only what you know. As many as you like." }))
          : null,
        el("p", { class: "course-foot" }, romajiToggle(showHome)),
      ),
    );
    if (audioNotice) root.prepend(audioNotice);
  }
  function stat(value, label) {
    return el("div", { class: "course-stat" }, el("strong", { text: String(value) }), el("span", { text: label }));
  }
  function planRow(name, detail, isDone, onOpen, enabled = true) {
    return el("li", { class: "course-plan-row" + (isDone ? " done" : "") },
      el("span", { class: "course-check", text: isDone ? "✓" : "" }),
      el("div", { class: "course-plan-text" }, el("strong", { text: name }), el("span", { text: detail })),
      onOpen ? el("button", { class: "secondary", type: "button", disabled: !enabled, onclick: onOpen }, isDone ? "Again" : "Open") : el("span"),
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

    function next() {
      if (index >= queue.length) return finish();
      const card = queue[index];
      if (card.skill === "listen") listenCard(card);
      else speakCard(card);
      const upcoming = queue[index + 1];
      if (upcoming) prefetch(upcoming.phrase.jp);
    }
    async function gradeCard(card, good) {
      if (!card.retried) {
        postJson("/api/course/grade", { card_id: card.card_id, good }).catch(() => {});
        if (good) right += 1;
      }
      if (!good && !card.retried) queue.push({ ...card, retried: true });
      index += 1;
      next();
    }
    function counter() {
      return `${Math.min(index + 1, queue.length)} / ${queue.length}`;
    }
    function gradeButtons(card, suggestGood) {
      return el("div", { class: "course-actions" },
        el("button", { class: suggestGood === false ? "" : "secondary", type: "button", onclick: () => gradeCard(card, false) }, "✗ Didn't know"),
        el("button", { class: suggestGood === false ? "secondary" : "", type: "button", onclick: () => gradeCard(card, true) }, "✓ Got it"),
      );
    }

    function listenCard(card) {
      const p = card.phrase;
      const answer = el("div", { class: "course-answer", hidden: true }, phraseBlock(p), gradeButtons(card));
      const reveal = el("button", { class: "course-cta", type: "button", onclick: () => { reveal.hidden = true; answer.hidden = false; } }, "Show meaning");
      frame("Review · listen", counter(), el("div", { class: "course-card" },
        el("p", { class: "course-prompt", text: card.retried ? "Once more — what does this mean?" : "Listen. What does it mean?" }),
        playButtons(p.jp),
        reveal,
        answer,
      ));
      play(p.jp);
    }

    function speakCard(card) {
      const p = card.phrase;
      const result = el("div", { class: "course-result" });
      const answer = el("div", { class: "course-answer", hidden: true });
      function showAnswer(suggestGood) {
        answer.hidden = false;
        answer.replaceChildren(phraseBlock(p), playButtons(p.jp), gradeButtons(card, suggestGood));
      }
      const hold = holdButton("Hold and say it", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "course-muted", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          const msg = bandMessage(r.band);
          result.replaceChildren(
            el("p", { class: "course-verdict " + msg.cls, text: msg.text }),
            el("p", { class: "course-heard" }, "Heard: ", el("span", { lang: "ja", text: r.heard })),
          );
          showAnswer(r.band === "good");
          if (r.band !== "good") play(p.jp);
        } catch (err) {
          result.replaceChildren(el("p", { class: "course-verdict off", text: String(err.message || err) }));
        }
      });
      frame("Review · speak", counter(), el("div", { class: "course-card" },
        el("p", { class: "course-prompt", text: "Say this in Japanese:" }),
        el("p", { class: "course-en course-en-big", text: p.en }),
        hold,
        result,
        el("button", { class: "secondary course-link", type: "button", onclick: () => { showAnswer(false); play(p.jp); } }, "I don't remember — show me"),
        answer,
      ));
    }

    function finish() {
      frame("Review", "", el("div", { class: "course-card course-center" },
        el("h3", { text: "Review done" }),
        el("p", { text: `${right} of ${total} remembered on the first try.` }),
        el("p", { class: "course-muted", text: "Missed ones come back tomorrow; remembered ones come back later and later." }),
        el("button", { class: "course-cta", type: "button", onclick: async () => { await refresh(); today.review = []; runNext(); } }, "Continue"),
      ));
    }

    if (!queue.length) return showHome();
    next();
  }

  // ---------- learn new phrases ----------
  function runLearn(unit) {
    let i = 0;
    const phrases = unit.phrases;

    function show() {
      const p = phrases[i];
      const result = el("div", { class: "course-result" });
      const hold = holdButton("Hold and say it", async (blob, ext) => {
        result.replaceChildren(el("p", { class: "course-muted", text: "Checking…" }));
        try {
          const r = await api("/api/course/check", { method: "POST", body: audioForm(blob, ext, { phrase_id: p.id }) });
          const msg = bandMessage(r.band);
          result.replaceChildren(
            el("p", { class: "course-verdict " + msg.cls, text: msg.text }),
            el("p", { class: "course-heard" }, "Heard: ", el("span", { lang: "ja", text: r.heard })),
          );
        } catch (err) {
          result.replaceChildren(el("p", { class: "course-verdict off", text: String(err.message || err) }));
        }
      });
      const last = i === phrases.length - 1;
      frame(`New phrases · Unit ${unit.number}`, `${i + 1} / ${phrases.length}`, el("div", { class: "course-card" },
        phraseBlock(p),
        playButtons(p.jp),
        el("p", { class: "course-prompt", text: "Listen, then say it out loud:" }),
        hold,
        result,
        el("div", { class: "course-actions" },
          i > 0 ? el("button", { class: "secondary", type: "button", onclick: () => { i -= 1; show(); } }, "← Back") : null,
          el("button", { type: "button", onclick: next }, last ? "Done" : "Next →"),
        ),
        el("p", { class: "course-foot" }, romajiToggle(show)),
      ));
      play(p.jp);
      if (!last) prefetch(phrases[i + 1].jp);
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
      title: `Listen · Unit ${unit.number}`,
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
    frame("Extra listening", "", el("div", { class: "course-card course-center" },
      el("p", { class: "course-muted", text: "Writing a new conversation from the phrases you know…" })));
    let story;
    try {
      story = await api("/api/course/story", { method: "POST" });
    } catch (err) {
      frame("Extra listening", "", el("div", { class: "course-card course-center" },
        el("p", { class: "course-verdict off", text: String(err.message || err) }),
        el("button", { type: "button", onclick: runExtraListening }, "Try again")));
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

  function listenView({ title, dialogue, questions: qs, doneLabel, onDone }) {
    const d = dialogue;
    let showJp = false;
    let showEn = false;
    let playing = false;
    const answered = new Map();
    const lineEls = [];

    const linesBox = el("div", { class: "course-dialogue" });
    function renderLines() {
      linesBox.replaceChildren(...d.lines.map((line, idx) => {
        const row = el("button", { class: `course-line who-${line.who}`, type: "button", onclick: () => play(line.jp, { voice: line.who === "b" ? "b" : "a" }) },
          el("span", { class: "course-who", text: line.who === "b" ? "B" : "A" }),
          el("span", { class: "course-line-body" },
            el("span", { class: "course-jp" + (showJp ? "" : " course-hidden"), lang: "ja", text: showJp ? line.jp : "・・・・・" }),
            showEn ? el("span", { class: "course-en", text: line.en }) : null,
            showJp && line.gloss ? el("span", { class: "course-note", text: line.gloss }) : null,
          ),
        );
        lineEls[idx] = row;
        return row;
      }));
    }
    async function playAll() {
      if (playing) return;
      playing = true;
      playBtn.disabled = true;
      for (let idx = 0; idx < d.lines.length; idx++) {
        lineEls[idx]?.classList.add("speaking");
        await play(d.lines[idx].jp, { voice: d.lines[idx].who === "b" ? "b" : "a" });
        lineEls[idx]?.classList.remove("speaking");
        await new Promise((r) => setTimeout(r, 350));
      }
      playing = false;
      playBtn.disabled = false;
      playBtn.textContent = "▶ Play again";
    }
    const playBtn = el("button", { class: "course-cta", type: "button", onclick: playAll }, "▶ Play the conversation");
    const toggles = el("div", { class: "course-play-row" },
      el("button", { class: "secondary", type: "button", onclick: (e) => { showJp = !showJp; e.target.textContent = showJp ? "Hide Japanese" : "Show Japanese"; renderLines(); } }, "Show Japanese"),
      el("button", { class: "secondary", type: "button", onclick: (e) => { showEn = !showEn; e.target.textContent = showEn ? "Hide English" : "Show English"; renderLines(); } }, "Show English"),
    );

    const questions = el("div", { class: "course-questions" }, qs.map((q, qi) => {
      const feedback = el("p", { class: "course-verdict" });
      const choices = el("div", { class: "course-choices" }, q.choices.map((choice, ci) =>
        el("button", {
          class: "secondary", type: "button",
          onclick: (e) => {
            const right = ci === q.answer;
            answered.set(qi, right);
            for (const b of choices.children) b.disabled = true;
            e.target.classList.add(right ? "right" : "wrong");
            if (!right) choices.children[q.answer].classList.add("right");
            feedback.className = "course-verdict " + (right ? "good" : "off");
            feedback.textContent = right ? "Right." : "Not quite — replay the conversation and listen for it.";
            if (answered.size === qs.length) doneBtn.disabled = false;
          },
        }, choice)));
      return el("div", { class: "course-question" }, el("p", { class: "course-q", text: q.q }), choices, feedback);
    }));
    const doneBtn = el("button", { class: "course-cta", type: "button", disabled: true, onclick: onDone }, doneLabel);

    renderLines();
    frame(title, "", el("div", { class: "course-card" },
      el("p", { class: "course-prompt", text: (d.scene ? d.scene + " " : "") + "Listen first — try to follow before showing any text." }),
      playBtn,
      toggles,
      linesBox,
      el("h3", { class: "course-sub", text: "Did you catch it?" }),
      questions,
      doneBtn,
    ));
    d.lines.forEach((line) => prefetch(line.jp, { voice: line.who === "b" ? "b" : "a" }));
  }

  // ---------- speak ----------
  function runSpeak(unit) {
    let t = 0;
    const tasks = unit.speak;

    function show() {
      const task = tasks[t];
      const result = el("div", { class: "course-result" });
      const hint = el("div", { class: "course-hint", hidden: true },
        el("p", { class: "course-jp", lang: "ja", text: task.hint }),
        el("button", { class: "secondary course-play", type: "button", onclick: () => play(task.hint.replace(/＿/g, "")) }, "▶ Play"),
      );
      let pending = false;
      async function submit(fields) {
        if (pending) return;
        pending = true;
        hold.disabled = true;
        result.replaceChildren(el("p", { class: "course-muted", text: "Kaiwa is listening…" }));
        try {
          const r = await api("/api/course/speak", { method: "POST", body: fields });
          renderVerdict(r);
          typed.value = "";
        } catch (err) {
          result.replaceChildren(el("p", { class: "course-verdict off", text: String(err.message || err) }));
        } finally {
          pending = false;
          hold.disabled = false;
        }
      }
      function renderVerdict(r) {
        const label = { great: "Great answer!", ok: "Understood — one thing to fix", retry: "Let's try that again" }[r.verdict] || "";
        const cls = { great: "good", ok: "close", retry: "off" }[r.verdict] || "off";
        result.replaceChildren(...[
          el("p", { class: "course-verdict " + cls, text: label }),
          el("p", { class: "course-heard" }, "You said: ", el("span", { lang: "ja", text: r.heard }), r.said_en ? ` — “${r.said_en}”` : ""),
          r.model ? el("div", { class: "course-model" },
            el("span", { class: "meta", text: r.verdict === "great" ? "Natural way to say it" : "Try saying" }),
            el("p", { class: "course-jp", lang: "ja", text: r.model }),
            el("button", { class: "secondary course-play", type: "button", onclick: () => play(r.model) }, "▶ Play"),
          ) : null,
          r.tip ? el("p", { class: "course-tip", text: r.tip }) : null,
        ].filter(Boolean));
        if (r.verdict !== "great" && r.model) play(r.model);
      }
      const hold = holdButton("Hold and answer", (blob, ext) => submit(audioForm(blob, ext, { unit_id: unit.id, task: t })));
      const typed = el("input", { type: "text", maxlength: "120", placeholder: "…or type your answer", lang: "ja" });
      const typedForm = el("form", { class: "course-typed", onsubmit: (e) => {
        e.preventDefault();
        if (!typed.value.trim()) return;
        const f = new FormData();
        f.append("unit_id", unit.id);
        f.append("task", String(t));
        f.append("text", typed.value.trim());
        submit(f);
      } }, typed, el("button", { class: "secondary", type: "submit" }, "Send"));
      const last = t === tasks.length - 1;

      frame(`Speak · Unit ${unit.number}`, `${t + 1} / ${tasks.length}`, el("div", { class: "course-card" },
        el("p", { class: "course-situation", text: task.situation }),
        el("div", { class: "course-kaiwa-says" },
          el("span", { class: "meta", text: "Kaiwa says" }),
          el("p", { class: "course-jp", lang: "ja", text: task.say }),
          playButtons(task.say),
        ),
        hold,
        typedForm,
        el("button", { class: "secondary course-link", type: "button", onclick: () => { hint.hidden = !hint.hidden; } }, "Need a hint?"),
        hint,
        result,
        el("div", { class: "course-actions" },
          el("button", { type: "button", onclick: next }, last ? "Finish unit" : "Next →"),
        ),
      ));
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
    frame(`Unit ${unit.number} complete`, "", el("div", { class: "course-card course-center" },
      el("h3", { text: `${unit.title} — done` }),
      el("p", { text: `You learned ${unit.phrases.length} phrases. They'll come back in tomorrow's review so they stick.` }),
      el("div", { class: "course-actions course-actions-center" },
        el("button", { class: "secondary", type: "button", onclick: () => goChat() }, "Use them in Chat"),
        el("button", { type: "button", onclick: () => showHome() }, "Back to Today"),
      ),
    ));
  }

  window.KaiwaCourse = { show: showHome };
})();

// First paint: Learn is the default tab.
if (document.getElementById("modeLearn")?.classList.contains("active")) {
  window.KaiwaCourse.show();
}

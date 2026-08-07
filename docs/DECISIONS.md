# Decisions

Captured from the 2026-08-05 planning conversation (Pingo-like personal Japanese AI partner).

## Product

1. **Personal use only** — not a commercial Pingo clone.
2. **Name / repo:** `kaiwa` at `E:\cursor\kaiwa` (会話 = conversation).
3. **MVP shape:** turn-based voice practice, not full realtime product polish.
4. **Inspiration:** [Pingo AI](https://pingo.ai) — immersive spoken practice with an AI partner — but scope-cut aggressively for one user.

## Speech / models

5. **DeepSeek V4 is not a speech model.** It is text-only; use it as the brain behind STT→TTS.
6. **Do not expect local models on a 3090 to beat DeepSeek V4 API** at the top end. Local mid-size models can be good enough; API wins for quality + consistency when cost is acceptable.
7. **Owner is okay spending on DeepSeek** → prefer API for LLM rather than forcing full-local LLM.
8. **Hybrid default:** local Whisper + DeepSeek V4 + local Japanese TTS.
9. **DeepSeek usage split:** Flash for normal conversation; Pro for deeper grammar/correction moments.

## STT

10. **Run Whisper locally** on the RTX 3090 via faster-whisper.
11. Prefer **`large-v3-turbo` or `large-v3`**, enable VAD when practical. **Practice** forces `language=ja`. **Chat** auto-detects language first — clear English is kept as English; otherwise Japanese-forced (so English help asks are not “translated” into JP).
12. Hardware check (2026-08-05): Ryzen 7 7800X3D, ~31 GB RAM, RTX 3090 (+ 2060) — more than enough for local Whisper.
13. Whisper is accurate enough to converse; **not** a reliable pronunciation scorer for learners.

## TTS

14. Prefer **local Japanese TTS** — Phase 1 used **VOICEVOX**; Phase 3 default is **AivisSpeech** (VOICEVOX-compatible API on `:10101`), with VOICEVOX kept as Settings fallback.
15. Cloud fallbacks with DeepSeek-comparable personal spend: OpenAI TTS, Google/Azure Neural.
16. ElevenLabs = quality upgrade, **not** thrift-tier pricing.
17. Stream TTS when possible; keep LLM replies short so speech starts sooner and feels conversational.

## Phase 1 implementation notes (2026-08-05)

18. Project `.env` overrides machine-wide `DEEPSEEK_API_KEY` (`load_dotenv(..., override=True)`).
19. Default LLM id: `deepseek-v4-flash` with thinking disabled for snappy turns.
20. Default app port **8787** (8765 conflicts with Anki on this machine).
21. Windows CUDA Whisper needs pip `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` (DLL path wired in `stt.py`).

## Practice mode (2026-08-05)

22. MVP+ includes **intelligibility** scoring in a separate Practice tab (target vs Whisper transcript, kana-normalized).
23. UI must label scores as intelligibility — never “pronunciation accuracy” / pitch accent.
24. Pitch-accent / dedicated assessment APIs remain deferred.

## Phase 2 tutor prefs (2026-08-05)

25. Correction style swap: **gentle** vs **critique** (explicit mistake → correct form → brief why; still short).
26. Personality editor: named presets + optional custom notes; stored in `data/user_prefs.json`.
27. Prompt assembled per turn from prefs (`persona.build_tutor_system_prompt`); reply length is soft/adaptive (conversation tempo), not a hard `max_sentences` cap.
28. Built-ins added: `anime_club`, `funny_friend` (loving roast when hilariously wrong, then correct; never mean).
29. User-created named presets in `data/user_personalities.json` with CRUD API; ids prefixed `user_`.
30. `language_policy`: **immerse** (JP only) vs **adaptive** (brief EN corrections when struggling); English kept minimal.
31. `speech_register`: **formal** vs **casual**, independent of personality vibe.
32. `naturalness_tips` toggle: correct textbook-stiff but grammatical lines toward the selected register.
33. No stage-direction emotes in tutor output; strip before TTS (`text_clean.clean_reply_for_speech`).
34. VOICEVOX voice selectable in Settings (`voicevox_speaker_id`; list via `GET /api/voices`).
35. `goal_level` (`pre_n5`/`n5`/`n4`) + `topic_preferences` for pacing and topics.
36. Dynamic `learner_profile.json`: heuristics each turn + occasional Flash assess; separate speaking vs comprehension.
37. `model_routing`: **auto** uses Pro for hard correction moments; otherwise Flash (`DEEPSEEK_MODEL_PRO`).
38. Phase 2 complete.

## Placement / Place me (2026-08-06)

39. **Self-assessment** Place me (stage / listening / speaking / chat pace) sets `speaking_level`, `comprehension_level`, and `goal_level` directly — no listening MCQ, no scored answers.
40. Placement is a meta onboarding tool (English self-ratings) — not part of immersion chat.

## Long-term memory (2026-08-06)

41. Lightweight `learner_memory.json`: comfort prefs (name/vibe/do/dont), topics, vocab, grammar notes.
42. Occasional Flash JSON extract after chat turns (every ~6 turns / struggle); injected into tutor prompt on top of personality.
43. Manual view/edit/reset via Settings + `GET/PUT /api/memory`.

## Non-goals (for now)

44. No pitch-accent / F0 grading yet (**deferred past Phase 3** — Practice stays intelligibility-only).
45. No full Pingo feature parity (memory plans, 200 scenarios, store apps).
46. No full-local DeepSeek V4-Pro hosting attempt.
47. No multi-user **accounts** / passwords / cloud sync. Local **named profiles** (prefs + learner state + memory + personalities) are allowed for backup/switch on one machine.

## Phase 3 close (2026-08-06)

48. TTS upgrade: `tts_engine` pref — **aivisspeech** (default) or **voicevox**; same VOICEVOX-compatible HTTP client; no silent cross-engine failover.
49. Realtime evaluation: `/api/turn` logs `timing` (stt/llm/tts/total ms); `scripts/eval_turn_latency.py` summarizes. **Stay turn-based** — OpenAI Realtime cost/complexity not justified while practice latency is acceptable.
50. Pitch-accent assessment explicitly deferred past Phase 3.

## Post–Phase 3 direction (2026-08-06)

51. Phase 4 focuses on **daily-use polish** (first-run, startup helper, TTS error clarity) and **conversation comfort** (soft phrase reuse, clearer corrections later) — not new product platforms.
52. Pitch accent and realtime speech remain deferred; revisit only if daily friction demands them.

## User profiles (2026-08-06)

53. Named local profiles under `data/profiles/<id>/` bundle prefs, learner profile, memory, and custom personalities; registry in `data/profiles.json`.
54. Chat `sessions/*.jsonl` stay global (not in profile backup). Profile switch/reset clears browser chat session id.
55. One-time migration moves flat `data/*.json` into `profiles/default/`. Export/import uses versioned `kaiwa-profile` JSON (never silently overwrite active).

## Soft phrase reuse (2026-08-06)

56. **North star:** make the user comfortable enough for genuine JP conversation. Chat is primary; Practice is optional warm-up — never quiz/drill pressure.
57. Practice can reuse lines from chat: `last_reply`, memory `vocab`, and soft `recycle_items` (unclear/close attempts stay available to “say again”; clear eases them off). UI copy: From our chats / Say again / Last reply — not “weak/fail.”
58. Empty Practice states nudge toward more chatting, not grinding.

## Adaptive reply length (2026-08-06)

59. No hard sentence quota in the tutor prompt. Length guidance is soft and turn-aware (1–2 short spoken sentences by default; up to ~2–3 when the user said more; shorter when struggling/help). `max_sentences` remains in prefs JSON for compatibility but is unused in the prompt.

## Desktop tray (2026-08-06)

60. Windows system-tray launcher (`python -m kaiwa.desktop` / `kaiwa-desktop`): idle tray uses no Whisper/TTS/server. Open starts prefs TTS engine + Kaiwa in a WebView window; closing the window stops processes we started and returns to tray; Quit exits.
61. If TTS was already running before Open, Close does not kill it (`started_by_us` tracking).

## Chat text fallback (2026-08-06)

62. Hold-to-talk stays primary. A quiet Chat text row (`POST /api/turn/text`) lets the user type or correct a turn when Whisper mishears — same turn pipeline as voice, `stt_ms: 0`. Not a second chat mode; no edit-past-bubbles / Practice text entry in this slice.

## Per-profile first-run Place me (2026-08-06)

63. Soft first-run per named profile: auto-open Place me when `placement_completed` is false; **Skip** dismisses for the browser session; Chat still works.
64. Expanded English self-assessment (kana / reading / grammar / follow / topics / help style) — still no scored JP items. Answers soft-min comprehension, set topics + `language_policy`, and store a `placement` dict.
65. Until Place me finishes, the tutor prompt treats level as **unknown** (do not trust default `pre_n5`). After finish, trust placement strongly and protect levels for ~15 chat turns.
66. Missing `placement_completed` on load → grandfather **true** (existing profiles). Create / reset write **false**.
67. Place me free text: topics **Other…** (short typed tag) + optional final “Anything else?” note → `placement` / `notes` only (never level enums).

## Related wiki

Ingested into personal llm-wiki under tag `kaiwa` (`C:\Users\elifs\Projects\llm-wiki`). See sync map in `docs/WIKI_SYNC.md`.

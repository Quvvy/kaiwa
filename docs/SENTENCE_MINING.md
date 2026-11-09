# Sentence mining + Anki sync (plan)

Status: **planning, no code yet.** Branch `sentence-mining` (from `study-lab` 58a7b4c).

## Why

Kaiwa should replace Anki for the owner: the part of learning after the beginner course (real anime, YouTube) has to stay enjoyable and grow with them. Anki got dropped because sitting through it was dreaded (Kaishi 1.5k, untouched for months). So every piece below is judged by: **does it make studying something you look forward to, without a backlog wall?**

Anki stays available for studying away from the PC (iPhone, AnkiMobile), synced both ways.

## Decisions so far (2026-11-09)

| Topic | Decision |
|---|---|
| Sources | Tsugi's browser player (anime), YouTube, subtitle files |
| Build order | Kaiwa ingest + AnkiConnect-compatible adapter first; Tsugi-native mining second |
| Review | **Listen → meaning** (the real speaker's clip on the front) |
| Card back | Original text with kanji (**no furigana**), a separate full kana reading line, meaning |
| Limits | Fully adjustable like Anki: **per deck** (Course, Mined, Kaishi…) plus one **global daily cap**; current pace presets become editable starting values |
| Anki sync | **Kaiwa ↔ AnkiWeb directly** with Anki's official Python library (no Anki desktop needed) |
| License | **Relicense Kaiwa to AGPL-3.0** (the sync library is AGPL; the owner is the sole contributor) |
| Sync scope | Mined sentences + course word/phrase cards; kana drills and speech checks stay Kaiwa-only |
| Kaishi 1.5k | Import with history, **no backlog wall** |
| Phone | iPhone, AnkiMobile, existing AnkiWeb account |
| Speaking step | **Later, opt-in**: Listen → meaning first; shadowing the real clip comes as an optional per-card or per-deck step once mining works |
| Kaishi vs course | **Course first, then Kaishi**: Kaishi takes over new vocab after the course's units; Kaishi words the course already taught are skipped |
| Yomitan word mines | **Sentence card with the word marked**: still Listen → meaning on the whole line; the looked-up word drives the note and the wrong answers, and is tracked as a learning word |
| Jimaku key | **In Tsugi** (server-side, like the MAL key); Kaiwa only receives mined lines |
| Content conflicts | **Kaiwa wins** card content (text, meaning, audio); a conflicting Anki edit is dropped and noted in a sync log. Review history from both sides is always kept |

## Shape

```
asbplayer / Yomitan / mpvacious ──AnkiConnect──┐
                                               ├─► Kaiwa mining ingest ─► card builder ─► decks + FSRS ─► review
Tsugi (Jimaku subs + helper ext) ──/api/mine───┘                                               ▲
                                                                                               │ revlog merge
                                                         AnkiWeb ◄──► Kaiwa's local Anki collection
                                                            ▲
                                                       AnkiMobile (phone)
```

### 1. Decks and limits (foundation)

Course state today is one pool with a pace-driven budget (`course/state.py` `PACES`, `due_cards`, `plan_today`). Add decks:

- **Course** (existing cards), **Mined**, **Kaishi 1.5k** (and any later import).
- Per deck: new/day, max reviews/day, desired retention, learning steps. Global: max reviews/day and new/day across all decks.
- Pace presets (Intensive / Regular) only fill in the Course deck's starting values. The labels stay estimates.
- Kaiwa still derives the grade from how you answered (no Again/Hard/Good/Easy buttons by default).

### 2. Mining ingest (phase 1)

- `POST /api/mine` is the native shape: `{text, start_ms, end_ms, audio, image?, source: {kind, title, url?, anilist_id?, episode?}, target_word?, en_sub?}`.
- **AnkiConnect adapter** at e.g. `http://127.0.0.1:8787/ankiconnect` (not 8765, which Anki uses). It covers just what the mining tools call: `version`, `requestPermission`, `deckNames`, `modelNames`, `modelFieldNames`, `findNotes`, `notesInfo`, `canAddNotes`, `addNote`, `updateNoteFields`, `storeMediaFile`, `guiBrowse`, `multi`. A fake "Kaiwa Mining" note type maps its fields onto `/api/mine`.
  - Result: **asbplayer** works on YouTube (it loads the subtitles itself) and on the video in Tsugi's player (with a Jimaku file dropped in). **Yomitan** works for single words. **mpvacious** works for mpv.
- Security: a local server that takes posts from the browser. Allow only extension origins plus a pairing token (like AnkiConnect's `requestPermission`), and no wildcard CORS.

### 3. Card builder

The capture is saved at once and enrichment runs in the background (the card shows "getting ready" until it's done):

- **Kana reading line**: pykakasi (already used in `my_phrases.romaji`), checked by Flash where kanji readings are ambiguous.
- **Meaning**: a Flash translation (an English subtitle line, if the tool sent one, is a hint, not the answer), plus a short note on the one or two words that make the line hard.
- **Distractors**: two wrong meanings with the same shape, like `course/sentences.py`.
- **Audio**: the clip normalized with ffmpeg (trim, loudness, opus). With no clip (Yomitan on a web page), fall back to TTS.
- **Screenshot**: stored for Anki and possible later use, not shown on the Kaiwa back for now.
- **Difficulty**: the number of unknown words against what you know. It's never a gate: mining what you liked is the motivation. It sets intro order and the note.

### 4. Tsugi-native mining (phase 2, in the tsugi repo)

- Tsugi already knows the AniList ID + episode. Fetch Japanese subs from **Jimaku** (`jimaku.cc`, needs a free API key) and pick the matching file.
- A JP line overlay in the player (off, on, or only while paused) with a sync offset nudge, remembered per show or release.
- Mine hotkey: the **helper extension** (it already runs in the player frame and sees the `<video>`) records that line's audio (seek to line start → `captureStream()` + `MediaRecorder` for the line's length → restore position) and takes a frame grab, then posts to Kaiwa `/api/mine` with show/episode metadata.
- Optionally show Kaiwa's word status in the overlay (known / learning / new) later.

### 5. Anki sync (phase 3)

- Kaiwa uses the `anki` pip package (pinned version) to keep a **local copy of your AnkiWeb collection** and sync it like any Anki client. You log in once in Settings; the hkey goes in `secrets_store`.
- AnkiWeb syncs whole collections, so Kaiwa's copy is your real collection (Kaishi included), not a separate one.
- Kaiwa cards ↔ Anki notes linked by a stable GUID. Note type "Kaiwa Listen" (audio front; kanji text + kana line + meaning back) for Mined and Course vocab.
- **Review history merge**: union both revlogs by timestamp per card, then recompute FSRS state from the merged history on both sides. Kaiwa's derived grades map 1:1 to Again/Hard/Good/Easy.
- Order of a sync: AnkiWeb → local collection → merge into Kaiwa → write Kaiwa's new reviews + due dates back → AnkiWeb.
- What happens if a card is reviewed on both sides between syncs: both reviews are kept (history is append-only), with FSRS replaying them in time order.

### 6. Kaishi 1.5k takeover

- After the first sync, Kaiwa reads Kaishi's notes (word, sentence, audio fields) and their revlog into a Kaishi deck: Listen → meaning on the sentence audio.
- **No backlog wall**:
  - FSRS re-estimates each overdue card from its history.
  - Overdue cards come back a few a day inside your review limit, easiest-to-recover first, so early sessions feel like wins.
  - The total overdue count is never shown.
  - Kaiwa also spreads those due dates in the Anki collection, so AnkiMobile doesn't show the wall either.

### 7. License

Relicense Kaiwa MIT → AGPL-3.0 in the PR that adds the `anki` dependency. Update `LICENSE`, `NOTICE.md`, README and the installer license page. Make sure no bundled component is AGPL-incompatible. The owner is the only author, so no outside consent is needed.

## Phases

1. **Decks + adjustable limits.** Course becomes a deck; there's a settings UI; budget logic moves per deck. *Built 2026-11-09:*
   - `DECKS` and `deck_of` in `course/state.py`; `state["limits"]` stores only the numbers the learner set.
   - Fields per deck: new per day, max reviews per day, lesson minutes, desired retention. All decks: new per day and max reviews per day.
   - A blank field follows the pace. A set review limit is a plain card count and a hard cap: no catch-up doubling.
   - A limit of 0 for new per day or lesson minutes means no lessons that day.
   - Retention is used per deck by `srs.scheduler()`.
   - `GET`/`PUT /api/course/limits`; the panel is under Learn → Options; checks are in `smoke_course.limits()`.
2. **Mining ingest + card builder + AnkiConnect adapter.** Try it with asbplayer on YouTube and on Tsugi's player.
3. **Mined review**: Listen → meaning for mined cards in the daily review, plus a Mined deck browser (edit, delete, re-cut audio).
4. **Tsugi**: Jimaku subs, overlay, mine hotkey in the helper extension.
5. **Anki sync** + AGPL relicense.
6. **Kaishi takeover** with gradual backlog intake.

Each phase is usable on its own. Phase 2 alone already replaces "mine into Anki".

## Open questions

All five first-round questions were settled on 2026-11-09 (see Decisions). Still to work out during the build:

- How Kaishi notes map to Kaiwa's word list, so "skip words the course already taught" can match them (by kanji and reading, probably).
- Where the kana line comes from for Kaishi cards: the deck's own reading field, or generated like mined cards.

## Risks

- `captureStream()` can fail on some players (DRM, cross-origin media without CORS). Fallback: let asbplayer do the recording, or ask Kaiwa to cut the clip server-side when the media URL can be read.
- Jimaku files come from different releases than the stream, so timing is off (opening and ad offsets). Overlay sync controls are needed.
- The AnkiWeb sync protocol follows Anki versions. Pin `anki` and test before each bump. A bad merge would damage the real collection, so keep a backup before every write.
- AnkiConnect clients assume Anki's behavior in edge cases (duplicate checks, media names). Test the adapter against real asbplayer and Yomitan.

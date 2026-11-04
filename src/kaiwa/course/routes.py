"""HTTP API for the daily lesson (Learn tab)."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from kaiwa import stt, tts
from kaiwa.config import get_settings
from kaiwa.course import ask, coach, hooks, kana_judge, placement, prerender, roleplay, sentences, state, stories
from kaiwa.course import drills, learner_log, missions, my_phrases
from kaiwa.course.kana import KANA_ROMAJI
from kaiwa.course.speech_check import check_phrase, normalize, spot_differences
from kaiwa.secrets_store import user_data_dir

router = APIRouter(prefix="/api/course")



class TtsBody(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    slow: bool = False
    voice: str = "a"


class StepBody(BaseModel):
    unit_id: str
    step: str
    count: int | None = Field(default=None, ge=1, le=100)  # words taught, when split across days


class PaceBody(BaseModel):
    pace: str


class GradeBody(BaseModel):
    """What happened on one answer; the server turns it into an FSRS grade."""

    card_id: str
    correct: bool | None = None
    good: bool | None = None  # older clients
    ms: int | None = Field(default=None, ge=0, le=600_000)  # time to answer
    helped: bool = False   # revealed text, opened a hint…
    guessed: bool = False  # pressed "I guessed"
    band: str = ""         # speech check: good / close / off
    fmt: str = ""          # answer format, for per-format speed baselines
    rating: int | None = Field(default=None, ge=1, le=4)  # set only when the learner chose the grade
    answer: str = Field(default="", max_length=300)  # what was picked, typed or heard (for the learner log)
    gave_up: bool = False  # pressed "Show me" / "Don't know"


class UndoBody(BaseModel):
    card_id: str | None = None


class RegradeBody(BaseModel):
    card_id: str
    rating: int = Field(ge=1, le=4)


class PlacementNextBody(BaseModel):
    skill: str
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class PlacementJudgeBody(BaseModel):
    jp: str = Field(max_length=120)
    expected: str = Field(max_length=300)
    answer: str = Field(default="", max_length=300)
    kind: str = "words"


class PlacementSummaryBody(BaseModel):
    histories: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    kana: list[dict[str, Any]] = Field(default_factory=list, max_length=40)


class HookBody(BaseModel):
    card_id: str


class KanaBody(BaseModel):
    lesson_id: str


class SentencesBody(BaseModel):
    card_ids: list[str] = Field(default_factory=list, max_length=20)


class AskBody(BaseModel):
    question: str = Field(default="", max_length=500)
    quick: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


@router.get("/today")
def today() -> dict[str, Any]:
    return {**state.today_payload(), "has_tutor": bool(get_settings().deepseek_api_key)}


@router.post("/tts")
async def speak(body: TtsBody) -> dict[str, Any]:
    settings = get_settings()
    speaker, engine = await asyncio.to_thread(prerender.speaker_for, settings, body.voice)
    try:
        wav = await asyncio.to_thread(
            tts.synthesize_cached,
            settings,
            body.text,
            speaker_id=speaker,
            engine=engine,
            speed=prerender.SLOW_SPEED if body.slow else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"audio_base64": base64.b64encode(wav).decode("ascii"), "audio_mime": "audio/wav"}


async def _transcribe(audio: UploadFile) -> str:
    raw = await audio.read()
    await audio.seek(0)
    if not raw:
        raise HTTPException(status_code=400, detail="Empty recording — hold the button while you speak.")
    suffix = Path(audio.filename or "utterance.webm").suffix or ".webm"
    try:
        heard, _meta = await asyncio.to_thread(
            stt.transcribe_audio_bytes, get_settings(), raw, suffix, mode="ja"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Speech recognition failed: {exc}") from exc
    heard = (heard or "").strip()
    if not heard:
        raise HTTPException(status_code=400, detail="Couldn't hear you — try again, a little louder.")
    return heard


def _keep_clip(audio: UploadFile, phrase_id: str, target: str, heard: str, band: str) -> None:
    """With KAIWA_SAVE_CLIPS=1, keep each say-it-back recording for testing recognisers."""
    if os.environ.get("KAIWA_SAVE_CLIPS") != "1":
        return
    try:
        folder = user_data_dir() / "clips"
        folder.mkdir(parents=True, exist_ok=True)
        stem = f"{time.strftime('%Y%m%d-%H%M%S')}_{phrase_id}"
        audio.file.seek(0)
        suffix = Path(audio.filename or "clip.webm").suffix or ".webm"
        (folder / (stem + suffix)).write_bytes(audio.file.read())
        row = {"file": stem + suffix, "target": target, "whisper": heard, "band": band}
        with open(folder / "clips.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


@router.post("/check")
async def check(audio: UploadFile = File(...), phrase_id: str = Form(...)) -> dict[str, Any]:
    """Say-it-back check for one phrase (new-phrase step and speak reviews)."""
    phrase = state.phrase(phrase_id)
    if phrase is None:
        raise HTTPException(status_code=404, detail="Unknown phrase")
    heard = await _transcribe(audio)
    result = check_phrase(phrase["jp"], heard, phrase.get("accept"))
    band, shown, tip = result.band, heard, ""
    verdict = await asyncio.to_thread(_judge, audio, phrase, heard)
    if verdict is not None:
        shown = verdict.sounded_like
        if verdict.band == "heard":
            # The audio agrees with Whisper's different hearing: never a pass.
            band = "close" if band == "good" else band
        else:
            band, tip = verdict.band, verdict.tip
    _keep_clip(audio, phrase_id, phrase["jp"], heard, band)
    learner_log.log("say", phrase=phrase_id, target=phrase["jp"], whisper=heard, sounded=shown, band=band,
                    score=result.score, tip=tip, kana_band=verdict.band if verdict else None)
    diff = spot_differences(phrase["jp"], shown) if band != "good" else []
    return {"heard": shown, "whisper": heard, "score": result.score, "band": band, "tip": tip, "diff": diff}


@router.post("/check_typed")
def check_typed(phrase_id: str = Form(...), text: str = Form(..., max_length=120)) -> dict[str, Any]:
    """The typed version of /check, for a learner without a microphone at hand."""
    phrase = state.phrase(phrase_id)
    if phrase is None:
        raise HTTPException(status_code=404, detail="Unknown phrase")
    result = check_phrase(phrase["jp"], text, phrase.get("accept"))
    learner_log.log("say", phrase=phrase_id, target=phrase["jp"], typed=text, band=result.band, score=result.score)
    diff = spot_differences(phrase["jp"], text) if result.band != "good" else []
    return {"heard": text, "score": result.score, "band": result.band, "tip": "", "diff": diff}


def _judge(
    audio: UploadFile, phrase: dict[str, Any], heard: str, rivals: tuple[str, ...] = ()
) -> kana_judge.Verdict | None:
    """Ask the kana model which of the target / Whisper's hearing / a typical slip fits."""
    if not kana_judge.available():
        return None
    try:
        from faster_whisper.audio import decode_audio

        audio.file.seek(0)
        samples = decode_audio(io.BytesIO(audio.file.read()), sampling_rate=16000)
        targets = list(phrase.get("kana") or [phrase["jp"]])
        targets += [a for a in phrase.get("accept") or [] if "*" not in a]
        return kana_judge.judge(samples, [normalize(x) for x in targets], normalize(heard), rivals)
    except Exception:
        return None


@router.post("/check_text")
async def check_text(
    audio: UploadFile = File(...), target: str = Form(..., max_length=80), strict: bool = Form(default=False)
) -> dict[str, Any]:
    """Say-it check against any short kana target (known kana and words in review).

    Single kana are too short for Whisper to be reliable, so for those the kana
    model's verdict decides and an empty transcript is not an error.
    """
    short = target in KANA_ROMAJI  # one kana card (blends like きゃ included), not a word
    try:
        heard = await _transcribe(audio)
    except HTTPException:
        if not short:
            raise
        heard = ""
    result = check_phrase(target, heard) if heard else None
    band = result.band if result else "off"
    shown, tip = heard, ""
    # A single kana has no "typical slip" variants, so every other kana competes.
    rivals = tuple(sorted({normalize(ch) for ch in KANA_ROMAJI if len(ch) <= 2})) if short else ()
    if short and kana_judge.available():
        band = "off"  # the kana model decides for single sounds
    verdict = await asyncio.to_thread(_judge, audio, {"jp": target}, heard, rivals)
    if verdict is not None:
        shown = verdict.sounded_like
        if verdict.band == "heard":
            band = "close" if band == "good" else band
        else:
            band, tip = verdict.band, verdict.tip
    if short and heard and normalize(heard) == normalize(target):
        # Whisper heard exactly this sound: trust it over the kana model, which
        # can mistake a short, quiet vowel for a neighbouring kana.
        band, shown = "good", heard
    learner_log.log("say", target=target, whisper=heard, sounded=shown, band=band, tip=tip, strict=strict,
                    score=result.score if result else 0, kana_band=verdict.band if verdict else None)
    if strict:
        # Placement imitation: score how exactly it was repeated, not whether it's close enough to practise on.
        sim = result.score if result else 0
        return {"heard": shown or heard, "band": band, "tip": tip,
                "credit": placement.imitation_credit(sim, verdict.band if verdict else None)}
    if short and band != "good":
        # One kana is too short to judge reliably by ear (measured on clean TTS:
        # correct あ, し and ん were each rejected in some runs). Speech may confirm
        # a single kana but never fail it; the learner is asked to type it instead.
        band = "unsure"
    diff = spot_differences(target, shown or heard) if band in ("close", "off") and not short else []
    return {"heard": shown or heard, "band": band, "tip": tip, "diff": diff}


@router.post("/speak")
async def speak_task(
    unit_id: str = Form(...),
    task: int = Form(...),
    audio: UploadFile | None = File(default=None),
    text: str = Form(default=""),
) -> dict[str, Any]:
    """Answer one of the unit's Speak prompts (voice, or typed as a fallback)."""
    unit = state.unit_by_id(unit_id)
    if unit is None or not 0 <= task < len(unit["speak"]):
        raise HTTPException(status_code=404, detail="Unknown speaking task")
    heard = await _transcribe(audio) if audio is not None else text.strip()
    if not heard:
        raise HTTPException(status_code=400, detail="Say or type an answer first.")
    r = await asyncio.to_thread(coach.judge, get_settings(), task=unit["speak"][task], heard=heard)
    learner_log.log("speak", unit=unit_id, task=task, prompt=unit["speak"][task]["say"], typed=audio is None,
                    heard=heard, verdict=r["verdict"], said_en=r["said_en"], model=r["model"], tip=r["tip"],
                    mistakes=r["mistakes"])
    return r


@router.post("/story")
async def story() -> dict[str, Any]:
    """Extra listening built from learned phrases."""
    settings = get_settings()
    data = await asyncio.to_thread(stories.take, settings) if settings.deepseek_api_key else None
    if data is None:
        st = state.load_state()
        if not state.learned_phrase_ids(st):
            raise HTTPException(status_code=400, detail="Learn your first phrases, then extra listening unlocks.")
        # No key or no connection: hearing a finished unit's conversation again is still real listening.
        data = state.old_dialogue(st)
        if data is None:
            detail = "Couldn't make a conversation this time — try again." if settings.deepseek_api_key else "Extra listening needs your DeepSeek key (Settings → DeepSeek), or a finished unit's conversation to replay."
            raise HTTPException(status_code=502 if settings.deepseek_api_key else 400, detail=detail)
    learner_log.log("story", scene=data["scene"], form=data.get("form"), known_share=data.get("known_share"),
                    lines=[line["jp"] for line in data["lines"]], glosses=[line.get("gloss") for line in data["lines"] if line.get("gloss")])
    return data


class ListenedBody(BaseModel):
    seconds: float
    scene: str = ""


@router.post("/listened")
def listened(body: ListenedBody) -> dict[str, Any]:
    """Time spent listening (and the scene, once heard through), for the listening total."""
    return state.record_listening(body.seconds, scene=body.scene[:200])


class LogBody(BaseModel):
    kind: str
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/log")
def log_event(body: LogBody) -> dict[str, Any]:
    """Events only the page sees: listening behaviour, hints, ending early, which activity was opened."""
    if body.kind not in learner_log.CLIENT_KINDS:
        raise HTTPException(status_code=400, detail="Unknown event")
    learner_log.log(body.kind, **{k: v for k, v in body.data.items() if k not in ("t", "s", "kind", "hour", "dow")})
    return {"ok": True}


@router.post("/talk/start")
async def talk_start() -> dict[str, Any]:
    """A new talk-practice scene."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=400, detail="Talk practice needs your DeepSeek key (Settings → DeepSeek).")
    data = await asyncio.to_thread(roleplay.start, settings)
    if data is None:
        if not state.learned_phrase_ids(state.load_state()):
            raise HTTPException(status_code=400, detail="Learn your first phrases, then talk practice unlocks.")
        raise HTTPException(status_code=502, detail="Couldn't set up a conversation this time. Try again.")
    learner_log.log("talk_start", scene=data["scene"], goal=data["goal"], opener=data["opener"])
    return data


@router.post("/talk/turn")
async def talk_turn(
    scene: str = Form(...),
    history: str = Form("[]"),
    audio: UploadFile | None = File(default=None),
    text: str = Form(default=""),
    ms: int = Form(default=0),
    hint_open: bool = Form(default=False),
) -> dict[str, Any]:
    """The learner's turn (voice, or typed): one correction and the partner's answer."""
    try:
        scene_data = json.loads(scene)
        turns = [h for h in json.loads(history) if isinstance(h, dict)][-20:]
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Bad conversation data") from exc
    if not isinstance(scene_data, dict):
        raise HTTPException(status_code=400, detail="Bad conversation data")
    heard = await _transcribe(audio) if audio is not None else text.strip()[:200]
    if not heard:
        raise HTTPException(status_code=400, detail="Say or type an answer first.")
    data = await asyncio.to_thread(roleplay.turn, get_settings(), scene=scene_data, history=turns, heard=heard)
    if data is None:
        raise HTTPException(status_code=502, detail="Couldn't get an answer this time. Try that line again.")
    data["talk_today"] = await asyncio.to_thread(state.record_talk)
    partner = next((h.get("jp") for h in reversed(turns) if h.get("who") != "me"), "")
    learner_log.log("talk", goal=scene_data.get("goal"), partner_said=partner, turn=sum(1 for h in turns if h.get("who") == "me") + 1,
                    typed=audio is None, ms=ms, hint_open=hint_open, heard=heard, verdict=data["verdict"],
                    said_en=data["said_en"], model=data["model"], tip=data["tip"], mistakes=data["mistakes"], done=data["done"])
    return data


@router.post("/step")
def step(body: StepBody) -> dict[str, Any]:
    try:
        row = state.complete_step(body.unit_id, body.step, count=body.count)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    learner_log.log("lesson_step", unit=body.unit_id, step=body.step)
    prerender.start(get_settings())  # the "next lesson" window may have moved
    return {"unit": row, "stats": state.stats(state.load_state())}


@router.get("/map")
def course_map() -> dict[str, Any]:
    return state.course_map()


@router.get("/unit/{unit_id}")
def open_unit(unit_id: str) -> dict[str, Any]:
    data = state.unit_payload(unit_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Unknown unit")
    return data


@router.get("/kana_lesson/{lesson_id}")
def kana_lesson(lesson_id: str) -> dict[str, Any]:
    data = state.kana_lesson_payload(lesson_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Unknown lesson")
    return data


@router.get("/phrasebook")
def phrasebook() -> dict[str, Any]:
    return state.phrasebook()


@router.get("/mission/{unit_id}")
def mission(unit_id: str) -> dict[str, Any]:
    if not get_settings().deepseek_api_key:
        raise HTTPException(status_code=400, detail="Missions need your DeepSeek key (Settings → DeepSeek).")
    data = missions.mission_for(unit_id)
    if data is None:
        raise HTTPException(status_code=404, detail="This unit has no mission.")
    learner_log.log("talk_start", scene=data["scene"], goal=data["goal"], opener=data["opener"], mission=unit_id)
    return data


class MissionBody(BaseModel):
    unit_id: str


@router.post("/mission_done")
def mission_done(body: MissionBody) -> dict[str, Any]:
    try:
        return {"mission": state.complete_mission(body.unit_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class BestBody(BaseModel):
    key: str = Field(pattern=r"^[a-z_]{1,24}$")
    value: int = Field(ge=0, le=100_000)


@router.post("/best")
def best(body: BestBody) -> dict[str, Any]:
    return state.record_best(body.key, body.value)


@router.get("/drill/{kind}")
def number_drill(kind: str, level: int = 1) -> dict[str, Any]:
    if kind not in ("price", "time"):
        raise HTTPException(status_code=404, detail="Unknown drill")
    return {"items": drills.round_items(kind, max(1, min(3, level)))}


class MineSuggestBody(BaseModel):
    text: str = Field(min_length=1, max_length=160)


class MineKeepBody(BaseModel):
    jp: str = Field(min_length=1, max_length=my_phrases.MAX_LEN)
    en: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=200)


@router.post("/mine/suggest")
async def mine_suggest(body: MineSuggestBody) -> dict[str, Any]:
    """How a beginner could say what the learner wants to say."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=400, detail="This needs your DeepSeek key (Settings → DeepSeek).")
    known = await asyncio.to_thread(state.known_phrases_for_chat)
    data = await asyncio.to_thread(my_phrases.suggest, settings, body.text, known)
    if data is None:
        raise HTTPException(status_code=502, detail="Couldn't work that out this time. Try again, or say it more simply.")
    learner_log.log("mine_suggest", asked=body.text, jp=data["jp"], en=data["en"])
    return data


@router.post("/mine")
def mine_keep(body: MineKeepBody) -> dict[str, Any]:
    try:
        row = state.keep_my_phrase(body.jp, body.en, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    learner_log.log("mine_keep", jp=row["jp"], en=row["en"])
    return row


@router.delete("/mine/{phrase_id}")
def mine_remove(phrase_id: str) -> dict[str, Any]:
    if not state.remove_my_phrase(phrase_id):
        raise HTTPException(status_code=404, detail="Not in your phrases")
    return {"ok": True}


@router.get("/reminder.ics")
def reminder(time: str = "19:00") -> Response:
    """A daily calendar event for study time: works on any device, no notification service."""
    try:
        hour, minute = [int(x) for x in time.split(":")[:2]]
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Time should look like 19:30") from exc
    today = state._today().strftime("%Y%m%d")
    body = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Kaiwa//Study time//EN", "BEGIN:VEVENT",
        f"UID:kaiwa-study-{today}@kaiwa", f"DTSTAMP:{today}T000000Z", f"DTSTART:{today}T{hour:02d}{minute:02d}00",
        "DURATION:PT15M", "RRULE:FREQ=DAILY", "SUMMARY:Japanese with Kaiwa",
        "DESCRIPTION:Fifteen minutes. If you're busy\\, just two.", "BEGIN:VALARM", "TRIGGER:PT0M", "ACTION:DISPLAY",
        "DESCRIPTION:Japanese with Kaiwa", "END:VALARM", "END:VEVENT", "END:VCALENDAR", "",
    ])
    return Response(content=body, media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="kaiwa-study-time.ics"'})


@router.post("/pace")
def set_pace(body: PaceBody) -> dict[str, Any]:
    try:
        return {"pace": state.set_pace(body.pace)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class SkipBody(BaseModel):
    unit_id: str


@router.post("/skip_unit")
def skip_unit(body: SkipBody) -> dict[str, Any]:
    """Mark the next unit known without its lessons; its reviews check that it really is."""
    try:
        out = state.skip_unit(body.unit_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prerender.start(get_settings())
    return out


@router.post("/ask")
async def ask_question(body: AskBody) -> dict[str, Any]:
    """Short English explanation of whatever is on the lesson screen."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=400, detail="Ask needs your DeepSeek key (Settings → DeepSeek).")
    known = await asyncio.to_thread(state.known_phrases_for_chat)
    try:
        result = await asyncio.to_thread(
            ask.ask, settings, question=body.question, quick=body.quick, context=body.context, known=known
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await asyncio.to_thread(state.log_question, result["question"], body.context)
    learner_log.log("ask", question=result["question"], quick=body.quick, screen=body.context.get("screen"),
                    context=body.context)
    return result


@router.post("/sentences")
async def review_sentences(body: SentencesBody) -> dict[str, Any]:
    """Short listening sentences that review several due word cards at once."""
    targets = await asyncio.to_thread(state.word_targets, body.card_ids)
    known_words, known_phrases = await asyncio.to_thread(state.known_vocab)
    items = await asyncio.to_thread(
        sentences.generate, get_settings(), targets=targets, known_words=known_words, known_phrases=known_phrases
    )
    return {"sentences": items}


@router.get("/placement/kana")
def placement_kana() -> dict[str, Any]:
    return {"items": placement.kana_items()}


@router.post("/placement/next")
def placement_next(body: PlacementNextBody) -> dict[str, Any]:
    """The next adaptive item for one skill (None once the skill is pinned down)."""
    try:
        item = placement.next_item(body.skill, body.history)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item, "estimate": placement.estimate(body.history)}


@router.post("/placement/judge")
async def placement_judge(body: PlacementJudgeBody) -> dict[str, Any]:
    score = await asyncio.to_thread(
        placement.judge_meaning, get_settings(), jp=body.jp, expected=body.expected, answer=body.answer, kind=body.kind
    )
    learner_log.log("placement_item", jp=body.jp, expected=body.expected, answer=body.answer, skill=body.kind, score=score)
    return {"score": score}


@router.post("/placement/summary")
def placement_summary(body: PlacementSummaryBody) -> dict[str, Any]:
    return placement.summarize(body.histories, body.kana)


@router.post("/placement/apply")
def placement_apply(body: PlacementSummaryBody) -> dict[str, Any]:
    summary = placement.summarize(body.histories, body.kana)
    applied = state.apply_placement(summary)
    learner_log.log("placement", summary=summary, histories=body.histories)
    prerender.start(get_settings())
    return {"summary": summary, "applied": applied}


@router.post("/hook")
async def leech_hook(body: HookBody) -> dict[str, Any]:
    """A memory hook and breakdown for a card the learner keeps forgetting (cached)."""
    item = state.card_item(body.card_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Unknown card")
    cached = (state.load_state()["cards"].get(body.card_id) or {}).get("hook")
    if cached:
        return {"hook": cached}
    hook = await asyncio.to_thread(hooks.write_hook, get_settings(), item)
    if hook is None:
        raise HTTPException(status_code=502, detail="Couldn't write a memory hook this time.")
    await asyncio.to_thread(state.save_hook, body.card_id, hook)
    return {"hook": hook}


@router.post("/undo")
def undo_answer(body: UndoBody) -> dict[str, Any]:
    """Ctrl+Z: take back the latest answer (optionally for one card)."""
    result = state.undo(card_id=body.card_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Nothing to undo.")
    return result


@router.post("/regrade")
def regrade_answer(body: RegradeBody) -> dict[str, Any]:
    """The learner picked a different grade for their last answer on this card."""
    try:
        return {"card": state.regrade(body.card_id, body.rating)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/stats")
def stats_page() -> dict[str, Any]:
    slips = state.slip_summary(learner_log.read(kinds={"speak", "talk", "chat_turn", "chat"}))
    return {**state.course_stats(), "slips": slips}


@router.post("/kana")
def kana_done(body: KanaBody) -> dict[str, Any]:
    try:
        progress = state.complete_kana(body.lesson_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    prerender.start(get_settings())
    return {"kana_progress": progress}


@router.post("/grade")
def grade(body: GradeBody) -> dict[str, Any]:
    try:
        correct = body.correct if body.correct is not None else bool(body.good)
        card = state.grade(
            body.card_id, correct=correct, ms=body.ms, helped=body.helped,
            guessed=body.guessed, band=body.band, fmt=body.fmt, rating=body.rating,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    learner_log.log("review", card=body.card_id, fmt=body.fmt, correct=correct, ms=body.ms, helped=body.helped,
                    guessed=body.guessed, gave_up=body.gave_up, band=body.band, answer=body.answer,
                    chosen_grade=body.rating, grade=card.get("rating"), auto_grade=card.get("auto_rating"),
                    reps=card.get("reps"), lapses=card.get("lapses"),
                    stability=round(float((card.get("fsrs") or {}).get("stability") or 0), 2))
    return {"card": card}

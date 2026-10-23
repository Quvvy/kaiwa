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

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from kaiwa import stt, tts
from kaiwa.config import get_settings
from kaiwa.course import ask, coach, hooks, kana_judge, placement, prerender, sentences, state, stories
from kaiwa.course.kana import KANA_ROMAJI
from kaiwa.course.speech_check import check_phrase, normalize
from kaiwa.secrets_store import user_data_dir

router = APIRouter(prefix="/api/course")



class TtsBody(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    slow: bool = False
    voice: str = "a"


class StepBody(BaseModel):
    unit_id: str
    step: str


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
    return state.today_payload()


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
    return {"heard": shown, "whisper": heard, "score": result.score, "band": band, "tip": tip}


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
async def check_text(audio: UploadFile = File(...), target: str = Form(..., max_length=60)) -> dict[str, Any]:
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
    if short and band != "good":
        # One kana is too short to judge reliably by ear (measured on clean TTS:
        # correct あ, し and ん were each rejected in some runs). Speech may confirm
        # a single kana but never fail it; the learner is asked to type it instead.
        band = "unsure"
    return {"heard": shown or heard, "band": band, "tip": tip}


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
    return await asyncio.to_thread(coach.judge, get_settings(), task=unit["speak"][task], heard=heard)


@router.post("/story")
async def story() -> dict[str, Any]:
    """Extra listening built from learned phrases."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=400, detail="Extra listening needs your DeepSeek key (Settings → Your data).")
    data = await asyncio.to_thread(stories.generate, settings)
    if data is None:
        if not state.learned_phrase_ids(state.load_state()):
            raise HTTPException(status_code=400, detail="Learn your first phrases, then extra listening unlocks.")
        raise HTTPException(status_code=502, detail="Couldn't make a conversation this time — try again.")
    return data


@router.post("/step")
def step(body: StepBody) -> dict[str, Any]:
    try:
        row = state.complete_step(body.unit_id, body.step)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prerender.start(get_settings())  # the "next lesson" window may have moved
    return {"unit": row, "stats": state.stats(state.load_state())}


@router.post("/ask")
async def ask_question(body: AskBody) -> dict[str, Any]:
    """Short English explanation of whatever is on the lesson screen."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=400, detail="Ask needs your DeepSeek key (Settings → General).")
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
    return {"score": score}


@router.post("/placement/summary")
def placement_summary(body: PlacementSummaryBody) -> dict[str, Any]:
    return placement.summarize(body.histories, body.kana)


@router.post("/placement/apply")
def placement_apply(body: PlacementSummaryBody) -> dict[str, Any]:
    summary = placement.summarize(body.histories, body.kana)
    applied = state.apply_placement(summary)
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
    return state.course_stats()


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
    return {"card": card}

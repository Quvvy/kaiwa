"""HTTP API for the daily lesson (Learn tab)."""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from kaiwa import stt, tts
from kaiwa.config import get_settings
from kaiwa.course import coach, prerender, state, stories
from kaiwa.course.speech_check import check_phrase

router = APIRouter(prefix="/api/course")



class TtsBody(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    slow: bool = False
    voice: str = "a"


class StepBody(BaseModel):
    unit_id: str
    step: str


class GradeBody(BaseModel):
    card_id: str
    good: bool


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


@router.post("/check")
async def check(audio: UploadFile = File(...), phrase_id: str = Form(...)) -> dict[str, Any]:
    """Say-it-back check for one phrase (new-phrase step and speak reviews)."""
    phrase = state.phrase(phrase_id)
    if phrase is None:
        raise HTTPException(status_code=404, detail="Unknown phrase")
    heard = await _transcribe(audio)
    result = check_phrase(phrase["jp"], heard, phrase.get("accept"))
    return {"heard": heard, "score": result.score, "band": result.band}


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
    return {"unit": row, "stats": state.stats(state.load_state())}


@router.post("/grade")
def grade(body: GradeBody) -> dict[str, Any]:
    try:
        card = state.grade(body.card_id, body.good)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"card": card}

from __future__ import annotations

import base64
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kaiwa.config import ROOT, get_settings
from kaiwa import llm, stt, tts
from kaiwa.persona import PERSONALITY_PRESETS, infer_learner_state, preset_public_list
from kaiwa.personalities_store import (
    create_user_preset,
    delete_user_preset,
    list_user_presets,
    update_user_preset,
)
from kaiwa.practice import next_phrase, score_intelligibility
from kaiwa.prefs import load_prefs, save_prefs, validate_prefs_dict
from kaiwa.learner_profile import (
    apply_chat_signals,
    apply_manual_override,
    apply_practice_score,
    load_profile,
    maybe_run_assess,
    reset_profile,
    save_profile,
)
from kaiwa.learner_memory import (
    apply_manual_memory,
    load_memory,
    maybe_run_extract,
    note_chat_turn,
    reset_memory,
    save_memory,
)
from kaiwa.session_log import append_session_log
from kaiwa.text_clean import clean_reply_for_speech
from kaiwa.quiz import (
    QUIZ_SIZE,
    answer_item,
    apply_self_assessment,
    discard_session,
    get_session,
    public_items,
    start_quiz_session,
)

settings = get_settings()
settings.sessions_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Kaiwa", version="0.1.0")
static_dir = ROOT / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# In-memory chat history keyed by browser session id.
_sessions: dict[str, list[dict[str, str]]] = {}
_practice_cursor: dict[str, str] = {}


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)
    speaker_id: int | None = None


class PrefsUpdate(BaseModel):
    correction_style: str = "gentle"
    personality_id: str = "patient_tutor"
    personality_custom: str = ""
    max_sentences: int = 3
    language_policy: str = "adaptive"
    speech_register: str = "casual"
    naturalness_tips: bool = True
    help_language: str = "en"
    tts_engine: str = "aivisspeech"
    voicevox_speaker_id: int = 888753760
    goal_level: str = "pre_n5"
    topic_preferences: list[str] = Field(default_factory=list)
    model_routing: str = "auto"


class ProfileUpdate(BaseModel):
    speaking_level: str | None = None
    comprehension_level: str | None = None
    topic_tags: list[str] | None = None
    notes: str | None = None
    confidence: float | None = None
    reset: bool = False


class MemoryUpdate(BaseModel):
    preferred_name: str | None = None
    vibe_notes: str | None = None
    do: list[str] | None = None
    dont: list[str] | None = None
    topics: list[str] | None = None
    reset: bool = False


class QuizAnswerRequest(BaseModel):
    session_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    choice_index: int


class QuizFinishRequest(BaseModel):
    session_id: str = Field(min_length=1)


class PersonalityCreate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=200)
    prompt_blurb: str = Field(min_length=1, max_length=2000)


class PersonalityUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=200)
    prompt_blurb: str = Field(min_length=1, max_length=2000)


def _last_assistant_text(session_id: str) -> str | None:
    history = _sessions.get(session_id) or []
    for message in reversed(history):
        if message.get("role") == "assistant" and message.get("content"):
            return message["content"]
    return None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.deepseek_model}


@app.get("/api/voices")
def get_voices() -> dict[str, Any]:
    prefs = load_prefs()
    engine = tts.normalize_engine(prefs.tts_engine, settings.tts_engine)
    try:
        raw = tts.list_speakers(settings, engine=engine)
        voices = tts.flatten_speaker_styles(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    selected = prefs.voicevox_speaker_id
    ids = {int(v["id"]) for v in voices}
    if selected not in ids and voices:
        selected = tts.engine_default_speaker(settings, engine)
        if selected not in ids:
            selected = int(voices[0]["id"])
    return {
        "engine": engine,
        "engine_label": tts.ENGINE_LABELS[engine],
        "voices": voices,
        "selected_id": selected,
        "default_id": tts.engine_default_speaker(settings, engine),
        "base_url": tts.engine_base_url(settings, engine),
    }


@app.get("/api/prefs")
def get_prefs() -> dict[str, Any]:
    prefs = load_prefs()
    return {
        "prefs": prefs.to_dict(),
        "personalities": preset_public_list(),
    }


@app.put("/api/prefs")
def put_prefs(body: PrefsUpdate) -> dict[str, Any]:
    try:
        prefs = validate_prefs_dict(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prefs.voicevox_speaker_id = tts.resolve_speaker_id(
        settings,
        engine=prefs.tts_engine,
        preferred_id=prefs.voicevox_speaker_id,
    )
    save_prefs(prefs)
    return {
        "prefs": prefs.to_dict(),
        "personalities": preset_public_list(),
    }


@app.get("/api/profile")
def get_profile() -> dict[str, Any]:
    prefs = load_prefs()
    profile = load_profile()
    return {
        "profile": profile.to_dict(),
        "goal_level": prefs.goal_level,
        "topic_preferences": prefs.topic_preferences,
    }


@app.put("/api/profile")
def put_profile(body: ProfileUpdate) -> dict[str, Any]:
    prefs = load_prefs()
    if body.reset:
        profile = reset_profile()
    else:
        profile = load_profile()
        try:
            profile = apply_manual_override(
                profile,
                speaking_level=body.speaking_level,
                comprehension_level=body.comprehension_level,
                topic_tags=body.topic_tags,
                notes=body.notes,
                confidence=body.confidence,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        save_profile(profile)
    return {
        "profile": profile.to_dict(),
        "goal_level": prefs.goal_level,
        "topic_preferences": prefs.topic_preferences,
    }


@app.get("/api/memory")
def get_memory() -> dict[str, Any]:
    return {"memory": load_memory().to_dict()}


@app.put("/api/memory")
def put_memory(body: MemoryUpdate) -> dict[str, Any]:
    if body.reset:
        memory = reset_memory()
    else:
        memory = load_memory()
        memory = apply_manual_memory(
            memory,
            preferred_name=body.preferred_name,
            vibe_notes=body.vibe_notes,
            do=body.do,
            dont=body.dont,
            topics=body.topics,
        )
        save_memory(memory)
    return {"memory": memory.to_dict()}


@app.get("/api/personalities")
def get_personalities() -> dict[str, Any]:
    builtins = [
        {
            "id": p.id,
            "label": p.label,
            "description": p.description,
            "source": "builtin",
        }
        for p in PERSONALITY_PRESETS
    ]
    user = [p.public_dict() for p in list_user_presets()]
    return {"builtins": builtins, "user": user}


@app.post("/api/personalities")
def post_personality(body: PersonalityCreate) -> dict[str, Any]:
    try:
        preset = create_user_preset(
            label=body.label,
            description=body.description,
            prompt_blurb=body.prompt_blurb,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"preset": preset.public_dict(), "personalities": preset_public_list()}


@app.put("/api/personalities/{preset_id}")
def put_personality(preset_id: str, body: PersonalityUpdate) -> dict[str, Any]:
    try:
        preset = update_user_preset(
            preset_id,
            label=body.label,
            description=body.description,
            prompt_blurb=body.prompt_blurb,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"preset": preset.public_dict(), "personalities": preset_public_list()}


@app.delete("/api/personalities/{preset_id}")
def remove_personality(preset_id: str) -> dict[str, Any]:
    try:
        deleted = delete_user_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"preset not found: {preset_id}")

    prefs = load_prefs()
    if prefs.personality_id == preset_id:
        prefs.personality_id = "patient_tutor"
        save_prefs(prefs)

    return {
        "deleted": preset_id,
        "prefs": prefs.to_dict(),
        "personalities": preset_public_list(),
    }


@app.post("/api/turn")
async def turn(
    audio: UploadFile = File(...),
    session_id: str = Form(default=""),
) -> dict[str, Any]:
    sid = session_id.strip() or uuid.uuid4().hex
    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    suffix = Path(audio.filename or "utterance.webm").suffix or ".webm"
    t0 = time.perf_counter()
    try:
        transcript = stt.transcribe_audio_bytes(settings, raw, suffix=suffix, mode="chat")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc
    stt_ms = int((time.perf_counter() - t0) * 1000)

    if not transcript:
        raise HTTPException(status_code=400, detail="Could not hear any speech")

    history = _sessions.setdefault(sid, [])
    history.append({"role": "user", "content": transcript})
    prefs = load_prefs()
    profile = load_profile()
    memory = load_memory()
    learner_state = infer_learner_state(transcript)
    profile = apply_chat_signals(profile, learner_state, transcript)
    profile = maybe_run_assess(
        settings,
        profile,
        transcript=transcript,
        learner_state=learner_state,
        prefs=prefs,
    )
    save_profile(profile)

    t1 = time.perf_counter()
    try:
        reply, model_used = llm.chat(
            settings,
            history,
            prefs=prefs,
            profile=profile,
            memory=memory,
            learner_state=learner_state,
        )
    except Exception as exc:
        history.pop()
        raise HTTPException(status_code=502, detail=f"LLM failed: {exc}") from exc
    llm_ms = int((time.perf_counter() - t1) * 1000)

    reply = clean_reply_for_speech(reply)
    history.append({"role": "assistant", "content": reply})

    audio_b64 = ""
    tts_error = None
    t2 = time.perf_counter()
    try:
        wav = tts.synthesize(
            settings,
            reply,
            speaker_id=prefs.voicevox_speaker_id,
            engine=prefs.tts_engine,
        )
        audio_b64 = base64.b64encode(wav).decode("ascii")
    except Exception as exc:
        tts_error = str(exc)
    tts_ms = int((time.perf_counter() - t2) * 1000)
    total_ms = int((time.perf_counter() - t0) * 1000)
    timing = {
        "stt_ms": stt_ms,
        "llm_ms": llm_ms,
        "tts_ms": tts_ms,
        "total_ms": total_ms,
    }

    # Post-TTS memory extract so chat latency stays snappy.
    memory = note_chat_turn(memory)
    memory, memory_updated = maybe_run_extract(
        settings,
        memory,
        prefs=prefs,
        profile=profile,
        recent_messages=history,
    )
    save_memory(memory)

    append_session_log(
        settings.sessions_dir,
        sid,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "chat",
            "transcript": transcript,
            "reply": reply,
            "tts_ok": not tts_error,
            "tts_error": tts_error,
            "tts_engine": prefs.tts_engine,
            "correction_style": prefs.correction_style,
            "personality_id": prefs.personality_id,
            "learner_state": learner_state,
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
            "model_used": model_used,
            "memory_updated": memory_updated,
            "timing": timing,
        },
    )

    return {
        "session_id": sid,
        "transcript": transcript,
        "reply_text": reply,
        "audio_base64": audio_b64,
        "audio_mime": "audio/wav",
        "tts_error": tts_error,
        "learner_state": learner_state,
        "speaking_level": profile.speaking_level,
        "comprehension_level": profile.comprehension_level,
        "model_used": model_used,
        "memory_updated": memory_updated,
        "timing": timing,
    }


@app.get("/api/practice/next")
def practice_next(
    session_id: str = "",
    source: str = "bank",
    after_id: str = "",
) -> dict[str, Any]:
    sid = session_id.strip()
    src = (source or "bank").strip().lower()

    if src == "last_reply":
        text = _last_assistant_text(sid) if sid else None
        if not text:
            raise HTTPException(
                status_code=404,
                detail="No chat reply to practice yet. Chat first, or use the phrase bank.",
            )
        # Prefer first sentence for repeat practice.
        short = text.split("。")[0].strip()
        if short and not short.endswith("。") and "。" in text:
            short = short + "。"
        target = short or text
        return {"phrase_id": "last_reply", "text": target, "source": "last_reply"}

    after = after_id.strip() or _practice_cursor.get(sid or "_", "")
    phrase = next_phrase(after or None)
    if sid:
        _practice_cursor[sid] = phrase["id"]
    else:
        _practice_cursor["_"] = phrase["id"]
    return {"phrase_id": phrase["id"], "text": phrase["text"], "source": "bank"}


@app.post("/api/practice/speak")
def practice_speak(body: SpeakRequest) -> dict[str, Any]:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    prefs = load_prefs()
    speaker = body.speaker_id if body.speaker_id is not None else prefs.voicevox_speaker_id
    try:
        wav = tts.synthesize(
            settings,
            text,
            speaker_id=speaker,
            engine=prefs.tts_engine,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
    return {
        "text": text,
        "audio_base64": base64.b64encode(wav).decode("ascii"),
        "audio_mime": "audio/wav",
        "speaker_id": speaker,
        "tts_engine": prefs.tts_engine,
    }


@app.post("/api/practice")
async def practice(
    audio: UploadFile = File(...),
    target_text: str = Form(...),
    session_id: str = Form(default=""),
) -> dict[str, Any]:
    sid = session_id.strip() or uuid.uuid4().hex
    target = (target_text or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="target_text is required")

    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    suffix = Path(audio.filename or "utterance.webm").suffix or ".webm"
    try:
        heard = stt.transcribe_audio_bytes(settings, raw, suffix=suffix, mode="ja")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc

    if not heard:
        raise HTTPException(status_code=400, detail="Could not hear any Japanese speech")

    result = score_intelligibility(target, heard)
    prefs = load_prefs()
    profile = load_profile()
    profile = apply_practice_score(profile, result.score, result.band)
    save_profile(profile)

    tip = ""
    tip_error = None
    try:
        tip = llm.practice_tip(
            settings,
            target=target,
            heard=heard,
            score=result.score,
            band=result.band,
            prefs=prefs,
        )
        tip = clean_reply_for_speech(tip)
    except Exception as exc:
        tip_error = str(exc)

    append_session_log(
        settings.sessions_dir,
        sid,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "practice",
            "target": target,
            "heard": heard,
            "score": result.score,
            "band": result.band,
            "score_kind": result.score_kind,
            "target_norm": result.target_norm,
            "heard_norm": result.heard_norm,
            "tip": tip,
            "tip_error": tip_error,
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
        },
    )

    return {
        "session_id": sid,
        "target_text": target,
        "heard_text": heard,
        "score": result.score,
        "band": result.band,
        "score_kind": result.score_kind,
        "tip": tip,
        "tip_error": tip_error,
        "reference_audio_base64": None,
    }


@app.post("/api/quiz/start")
def quiz_start() -> dict[str, Any]:
    prefs = load_prefs()
    profile = load_profile()
    session = start_quiz_session(prefs, profile)
    return {
        "session_id": session.id,
        "total": QUIZ_SIZE,
        "items": public_items(session),
        "comprehension_level": profile.comprehension_level,
        "goal_level": prefs.goal_level,
    }


@app.post("/api/quiz/answer")
def quiz_answer(body: QuizAnswerRequest) -> dict[str, Any]:
    session = get_session(body.session_id.strip())
    if session is None:
        raise HTTPException(status_code=404, detail="Placement session not found or expired")
    try:
        result = answer_item(session, body.item_id.strip(), int(body.choice_index))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **result,
        "answered_count": sum(1 for row in session.items if row.answered),
        "total": len(session.items),
    }


@app.post("/api/quiz/finish")
def quiz_finish(body: QuizFinishRequest) -> dict[str, Any]:
    session = get_session(body.session_id.strip())
    if session is None:
        raise HTTPException(status_code=404, detail="Placement session not found or expired")
    if session.finished:
        raise HTTPException(status_code=400, detail="Placement already finished")

    unanswered = [row.id for row in session.items if not row.answered]
    if unanswered:
        raise HTTPException(
            status_code=400,
            detail=f"Answer all questions first ({len(unanswered)} remaining)",
        )

    prefs = load_prefs()
    profile = load_profile()
    profile, prefs, summary = apply_self_assessment(profile, prefs, session.answers())
    save_profile(profile)
    save_prefs(prefs)
    session.finished = True

    append_session_log(
        settings.sessions_dir,
        body.session_id.strip(),
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "placement",
            "answers": session.answers(),
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
            "goal_level": prefs.goal_level,
            "item_ids": [row.id for row in session.items],
        },
    )
    discard_session(session.id)

    return {
        "summary": summary,
        "speaking_level": profile.speaking_level,
        "comprehension_level": profile.comprehension_level,
        "goal_level": prefs.goal_level,
        "profile": profile.to_dict(),
        "prefs": {"goal_level": prefs.goal_level},
        "message": profile.notes,
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "kaiwa.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

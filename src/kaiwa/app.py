from __future__ import annotations

import asyncio
import base64
import json
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kaiwa.config import ROOT, get_settings, reload_settings
from kaiwa import __version__, llm, profiles, secrets_store, stt, tts, updates
from kaiwa import prompt_stamp
from kaiwa.persona import PERSONALITY_PRESETS, infer_learner_state, preset_public_list
from kaiwa.personalities_store import (
    create_user_preset,
    delete_user_preset,
    list_user_presets,
    update_user_preset,
)
from kaiwa.practice import next_phrase, score_intelligibility
from kaiwa.prefs import load_prefs, save_prefs, validate_prefs_dict
from kaiwa.reply_shape import analyze_reply_shape
from kaiwa import ptt_events
from kaiwa import ptt_sounds
from kaiwa.learner_profile import (
    apply_chat_signals,
    apply_manual_override,
    apply_practice_score,
    load_profile,
    maybe_run_assess,
    reset_profile,
    save_profile,
)
from kaiwa.rescue import apply_rescue_signals, next_rescue_step
from kaiwa.learner_memory import (
    apply_manual_memory,
    clip_preferred_name,
    load_memory,
    maybe_run_extract,
    next_recycle_target,
    next_vocab_target,
    note_chat_turn,
    note_practice_result,
    reset_memory,
    save_memory,
)
from kaiwa import leftovers
from kaiwa import session_store
from kaiwa.stream_util import SentenceBuffer
from kaiwa.text_clean import clean_reply_for_speech, split_try_phrase
from kaiwa.quiz import (
    QUIZ_SIZE,
    answer_item,
    apply_self_assessment,
    discard_session,
    get_session,
    public_items,
    start_quiz_session,
)

profiles.ensure_migrated()
settings = get_settings()
settings.sessions_dir.mkdir(parents=True, exist_ok=True)


def _refresh_settings() -> None:
    global settings
    settings = reload_settings()
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)


def _preferred_name_for_stt() -> str:
    try:
        return (load_memory().comfort.preferred_name or "").strip()
    except Exception:
        return ""


def _require_deepseek_key() -> None:
    if not get_settings().deepseek_api_key.strip():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API key required. Paste it on the first-run screen or in Settings → Profiles.",
        )


app = FastAPI(title="Kaiwa", version=__version__)
static_dir = ROOT / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# In-memory chat history keyed by browser session id.
_sessions: dict[str, list[dict[str, str]]] = {}
_practice_cursor: dict[str, str] = {}
# Live Chat still keeps full RAM history for the UI; the LLM only sees the tail.
CHAT_LLM_HISTORY = 16


def _llm_messages(history: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(history) <= CHAT_LLM_HISTORY:
        return history
    return history[-CHAT_LLM_HISTORY:]


def _known_profile_ids() -> set[str]:
    listing = profiles.list_profiles()
    return {str(p.get("id") or "") for p in listing.get("profiles") or [] if p.get("id")}


def _mint_session() -> str:
    meta = session_store.create_session(
        settings.sessions_dir, profiles.active_profile_id()
    )
    _sessions[meta.id] = []
    ptt_events.register_session(meta.id)
    return meta.id


def _resolve_session(sid: str) -> str:
    """Bind or hydrate a Chat session for the active profile.

    Mints a new id when the client sent none, or when the id belongs to
    another named profile. A stale prompt_revision does not mint — the
    thread continues with the current system prompt (#118).
    """
    active = profiles.active_profile_id()
    sid = (sid or "").strip()
    if not sid:
        return _mint_session()
    meta = session_store.load_meta(settings.sessions_dir, sid)
    if meta is None and session_store.session_exists(settings.sessions_dir, sid):
        meta = session_store.attach_legacy(settings.sessions_dir, sid, active)
    if meta is None:
        session_store.create_session(
            settings.sessions_dir, active, session_id=sid
        )
        _sessions.setdefault(sid, [])
        ptt_events.register_session(sid)
        return sid
    if session_store.other_named_profile(meta, active, _known_profile_ids()):
        return _mint_session()
    session_store.ensure_ram(_sessions, settings.sessions_dir, sid)
    return sid


def _replay_prompt_questions(
    sid: str, history: list[dict[str, str]]
) -> list[str] | None:
    meta = session_store.load_meta(settings.sessions_dir, sid)
    if meta is None or not (meta.replay_of or "").strip():
        return None
    return session_store.replay_remaining(meta.replay_questions, history)


def _append_session(sid: str, record: dict[str, Any], *, kind: str) -> None:
    pid = profiles.active_profile_id()
    title = str(record.get("transcript") or "") if kind == "chat" else ""
    session_store.append_record(
        settings.sessions_dir,
        sid,
        record,
        profile_id=pid,
        bump_turns=(kind == "chat"),
        title_hint=title,
    )


@app.on_event("startup")
async def _warm_stt() -> None:
    """Load Whisper in a worker thread so the first chat turn doesn't freeze the server."""

    prompt_stamp.apply_on_startup(_sessions)

    def _load() -> None:
        try:
            stt.get_model(settings)
        except Exception:
            pass

    asyncio.create_task(asyncio.to_thread(_load))


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
    ui_theme: str = "night"
    ptt_enabled: bool = False
    ptt_binding: str = ""
    ptt_play_reply: bool = True
    ptt_blips_enabled: bool = True
    ptt_blip_volume: float = 0.6
    chat_pace: str = "easy"


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
    choice_index: int | None = None
    choice_indices: list[int] | None = None
    text: str | None = Field(default=None, max_length=300)


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


class ProfileCreateBody(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    activate: bool = False


class TextTurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    session_id: str = ""


def _active_state_payload() -> dict[str, Any]:
    prefs = load_prefs()
    listing = profiles.list_profiles()
    return {
        **listing,
        "prefs": prefs.to_dict(),
        "personalities": preset_public_list(),
        "profile": load_profile().to_dict(),
        "memory": load_memory().to_dict(),
        "goal_level": prefs.goal_level,
        "topic_preferences": prefs.topic_preferences,
    }


def _export_filename(label: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label.strip())
    safe = safe.strip("-_") or "profile"
    return f"kaiwa-profile-{safe[:40]}.json"


def _last_assistant_text(session_id: str) -> str | None:
    if not session_id:
        return None
    history = session_store.ensure_ram(_sessions, settings.sessions_dir, session_id)
    for message in reversed(history):
        if message.get("role") == "assistant" and message.get("content"):
            return message["content"]
    return None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    ico = static_dir / "icons" / "kaiwa.ico"
    if ico.is_file():
        return FileResponse(ico, media_type="image/x-icon")
    return FileResponse(static_dir / "icons" / "kaiwa-text-only.png", media_type="image/png")


@app.get("/api/health")
def health() -> dict[str, Any]:
    s = get_settings()
    info = stt.get_stt_runtime_info()
    return {
        "status": "ok",
        "version": __version__,
        "model": s.deepseek_model,
        "deepseek_configured": "true" if s.deepseek_api_key.strip() else "false",
        "whisper_requested": str(info.get("requested") or s.whisper_device),
        "whisper_device": str(info.get("active_device") or ""),
        "whisper_compute": str(info.get("active_compute") or ""),
        "whisper_reason": str(info.get("reason") or ""),
        "whisper_cuda_available": "true" if info.get("cuda_available") else "false",
        "whisper_local_model": "true" if info.get("local_model") else "false",
        "prompt_revision": prompt_stamp.PROMPT_REVISION,
        "chat_reset": bool(prompt_stamp.chat_reset_this_process),
    }


class UpdateDismissBody(BaseModel):
    version: str = ""


@app.get("/api/updates/check")
def updates_check(force: int = 0) -> dict[str, Any]:
    return updates.check_for_updates(force=bool(force))


@app.post("/api/updates/dismiss")
def updates_dismiss(body: UpdateDismissBody) -> dict[str, Any]:
    try:
        return updates.dismiss_update(body.version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/updates/install")
def updates_install() -> dict[str, Any]:
    return updates.download_and_launch_installer(force_check=True)


class DeepseekKeyBody(BaseModel):
    api_key: str = ""


@app.get("/api/secrets/status")
def secrets_status() -> dict[str, Any]:
    s = get_settings()
    key = s.deepseek_api_key.strip()
    source = s.deepseek_key_source if key else "none"
    return {
        "configured": bool(key),
        "masked_key": secrets_store.masked_key(key) if key else "",
        "source": source,
    }


@app.put("/api/secrets/deepseek")
def secrets_put_deepseek(body: DeepseekKeyBody) -> dict[str, Any]:
    key = (body.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="api_key is required")
    try:
        secrets_store.save_secret_key(key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    base = get_settings().deepseek_base_url
    validation = secrets_store.soft_validate_deepseek(key, base)
    _refresh_settings()
    s = get_settings()
    return {
        "ok": True,
        "configured": bool(s.deepseek_api_key.strip()),
        "masked_key": secrets_store.masked_key(s.deepseek_api_key),
        "source": s.deepseek_key_source,
        "validation_ok": bool(validation.get("ok")),
        "warning": None if validation.get("ok") else str(validation.get("detail") or "Validation failed"),
    }


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
    profile = load_profile()
    listing = profiles.list_profiles()
    return {
        "prefs": prefs.to_dict(),
        "personalities": preset_public_list(),
        "profile": profile.to_dict(),
        "placement_completed": profile.placement_completed,
        "active_id": listing.get("active_id") or listing.get("active") or "",
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


class PttRegisterBody(BaseModel):
    session_id: str = ""


class PttBindCaptureBody(BaseModel):
    active: bool = False


@app.get("/api/ptt/state")
def ptt_state() -> dict[str, Any]:
    prefs = load_prefs()
    return {
        "session_id": ptt_events.registered_session(),
        "bind_capture": ptt_events.bind_capture_active(),
        "ptt_enabled": prefs.ptt_enabled,
        "ptt_binding": prefs.ptt_binding,
        "ptt_play_reply": prefs.ptt_play_reply,
        "hook_alive": ptt_events.hook_alive(),
        **ptt_sounds.blip_state(),
    }


@app.post("/api/ptt/register")
def ptt_register(body: PttRegisterBody) -> dict[str, Any]:
    ptt_events.register_session(body.session_id.strip())
    return {"ok": True, "session_id": ptt_events.registered_session()}


@app.post("/api/ptt/bind_capture")
def ptt_bind_capture(body: PttBindCaptureBody) -> dict[str, Any]:
    ptt_events.set_bind_capture(body.active)
    return {"ok": True, "bind_capture": ptt_events.bind_capture_active()}


@app.post("/api/ptt/heartbeat")
def ptt_heartbeat() -> dict[str, Any]:
    ptt_events.heartbeat()
    return {"ok": True, "hook_alive": True}


class PttStatusBody(BaseModel):
    message: str = ""
    level: str = "info"


@app.post("/api/ptt/status")
def ptt_status(body: PttStatusBody) -> dict[str, Any]:
    msg = (body.message or "").strip()
    if msg:
        ptt_events.push_status(msg, level=body.level or "info")
    return {"ok": True}


@app.post("/api/ptt/blip/{which}")
async def ptt_blip_upload(which: str, file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        slot = ptt_sounds.normalize_which(which)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raw = await file.read()
    try:
        path = ptt_sounds.save_custom_blip(
            slot,
            raw,
            filename=file.filename,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "which": slot,
        "custom": True,
        "label": "Custom",
        "path": str(path),
    }


@app.delete("/api/ptt/blip/{which}")
def ptt_blip_reset(which: str) -> dict[str, Any]:
    try:
        slot = ptt_sounds.normalize_which(which)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ptt_sounds.clear_custom_blip(slot)
    return {
        "ok": True,
        "which": slot,
        "custom": False,
        "label": "Default",
        "path": str(ptt_sounds.resolve_blip_path(slot) or ""),
    }


@app.get("/api/ptt/events")
def ptt_events_list(after: int = 0) -> dict[str, Any]:
    rows = ptt_events.events_after(after)
    return {"events": rows, "after": after, "hook_alive": ptt_events.hook_alive()}


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
        try:
            memory = apply_manual_memory(
                memory,
                preferred_name=body.preferred_name,
                vibe_notes=body.vibe_notes,
                do=body.do,
                dont=body.dont,
                topics=body.topics,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@app.get("/api/profiles")
def get_profiles() -> dict[str, Any]:
    return profiles.list_profiles()


@app.post("/api/profiles")
def post_profile(body: ProfileCreateBody) -> dict[str, Any]:
    try:
        meta = profiles.create_profile(body.label, activate=body.activate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = profiles.list_profiles()
    if body.activate:
        return {**_active_state_payload(), "created": meta.to_dict()}
    return {**payload, "created": meta.to_dict()}


@app.post("/api/profiles/{profile_id}/activate")
def activate_profile(profile_id: str) -> dict[str, Any]:
    try:
        meta = profiles.switch_profile(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {**_active_state_payload(), "activated": meta.to_dict()}


@app.delete("/api/profiles/{profile_id}")
def remove_user_profile(profile_id: str) -> dict[str, Any]:
    try:
        new_active = profiles.delete_profile(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **_active_state_payload(),
        "deleted": profile_id,
        "active_id": new_active,
    }


@app.post("/api/profiles/{profile_id}/reset")
def reset_user_profile(profile_id: str) -> dict[str, Any]:
    try:
        meta = profiles.reset_profile(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if profile_id == profiles.active_profile_id():
        return {**_active_state_payload(), "reset": meta.to_dict()}
    return {**profiles.list_profiles(), "reset": meta.to_dict()}


@app.get("/api/profiles/{profile_id}/export")
def export_user_profile(profile_id: str) -> Response:
    try:
        bundle = profiles.export_bundle(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    filename = _export_filename(str(bundle.get("label") or profile_id))
    body = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/profiles/import")
async def import_user_profile(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    bundle: dict[str, Any] | None = None
    use_label: str | None = None
    use_activate = False

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="multipart import requires a file field")
        raw_bytes = await upload.read()
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="invalid JSON file") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="bundle must be a JSON object")
        bundle = parsed
        label_val = form.get("label")
        if isinstance(label_val, str) and label_val.strip():
            use_label = label_val.strip()
        act_val = form.get("activate")
        if isinstance(act_val, str):
            use_activate = act_val.strip().lower() in {"1", "true", "yes", "on"}
        elif isinstance(act_val, bool):
            use_activate = act_val
    else:
        try:
            data = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid JSON body") from exc
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="body must be a JSON object")
        # Accept either wrapped {bundle, label, activate} or a raw export bundle
        if data.get("format") == profiles.BUNDLE_FORMAT or (
            "prefs" in data and "learner_profile" in data
        ):
            bundle = data
            use_label = str(data.get("label") or "").strip() or None
        else:
            raw_bundle = data.get("bundle")
            if not isinstance(raw_bundle, dict):
                raise HTTPException(status_code=400, detail="provide bundle object or raw export JSON")
            bundle = raw_bundle
            if data.get("label"):
                use_label = str(data["label"]).strip() or None
            use_activate = bool(data.get("activate", False))

    try:
        meta = profiles.import_bundle(bundle, label=use_label)
        if use_activate:
            profiles.switch_profile(meta.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if use_activate:
        return {**_active_state_payload(), "imported": meta.to_dict()}
    return {**profiles.list_profiles(), "imported": meta.to_dict()}


class ChatNewBody(BaseModel):
    session_id: str = ""


class RescueBody(BaseModel):
    session_id: str = ""


@app.post("/api/chat/new")
def chat_new(body: ChatNewBody) -> dict[str, Any]:
    """Start a new durable chat. Keeps profile memory and the old JSONL."""
    old = (body.session_id or "").strip()
    if old:
        _sessions.pop(old, None)
    new_id = _mint_session()
    return {"ok": True, "session_id": new_id}


@app.get("/api/sessions")
def list_chat_sessions() -> dict[str, Any]:
    active = profiles.active_profile_id()
    metas = session_store.list_sessions(settings.sessions_dir, active)
    return {
        "active_id": active,
        "sessions": [m.to_dict() for m in metas],
    }


@app.post("/api/sessions")
def post_chat_session(body: ChatNewBody) -> dict[str, Any]:
    return chat_new(body)


@app.get("/api/sessions/{session_id}")
def get_chat_session(session_id: str) -> dict[str, Any]:
    sid = (session_id or "").strip()
    if not sid or not session_store.session_exists(settings.sessions_dir, sid):
        raise HTTPException(status_code=404, detail="session not found")
    active = profiles.active_profile_id()
    meta = session_store.load_meta(settings.sessions_dir, sid)
    if meta is None:
        meta = session_store.attach_legacy(settings.sessions_dir, sid, active)
    if session_store.other_named_profile(meta, active, _known_profile_ids()):
        raise HTTPException(
            status_code=409, detail="session belongs to another profile"
        )
    return {**meta.to_dict(), "messages": session_store.hydrate(settings.sessions_dir, sid)}


@app.get("/api/sessions/{session_id}/leftovers")
async def session_leftovers(session_id: str) -> dict[str, Any]:
    """Phrases from an ended chat. Alternatives are optional Flash and may be empty."""
    sid = (session_id or "").strip()
    if not sid or not session_store.session_exists(settings.sessions_dir, sid):
        raise HTTPException(status_code=404, detail="session not found")
    active = profiles.active_profile_id()
    meta = session_store.load_meta(settings.sessions_dir, sid)
    if meta is None:
        meta = session_store.attach_legacy(settings.sessions_dir, sid, active)
    if session_store.other_named_profile(meta, active, _known_profile_ids()):
        raise HTTPException(
            status_code=409, detail="session belongs to another profile"
        )
    messages = session_store.hydrate(settings.sessions_dir, sid)
    chunks = leftovers.leftover_chunks(messages)
    alternatives: list[str] = []
    if chunks:
        alternatives = await asyncio.to_thread(
            leftovers.suggest_alternatives,
            settings,
            chunks,
            last_assistant=leftovers.last_assistant_line(messages),
        )
    return {
        "session_id": sid,
        "chunks": [{"text": text} for text in chunks],
        "alternatives": [{"text": text} for text in alternatives],
    }


@app.post("/api/sessions/{session_id}/replay")
async def replay_chat_session(session_id: str) -> dict[str, Any]:
    """Fork a child session that re-asks the parent's Kaiwa questions."""
    sid = (session_id or "").strip()
    if not sid or not session_store.session_exists(settings.sessions_dir, sid):
        raise HTTPException(status_code=404, detail="session not found")
    active = profiles.active_profile_id()
    parent = session_store.load_meta(settings.sessions_dir, sid)
    if parent is None:
        parent = session_store.attach_legacy(settings.sessions_dir, sid, active)
    if session_store.other_named_profile(parent, active, _known_profile_ids()):
        raise HTTPException(
            status_code=409, detail="session belongs to another profile"
        )
    questions = session_store.questions_for_replay(settings.sessions_dir, sid)
    if not questions:
        raise HTTPException(
            status_code=400,
            detail="Nothing to try again yet — chat first",
        )
    child = session_store.create_replay_session(
        settings.sessions_dir,
        active,
        parent_id=sid,
        questions=questions,
        parent_title=parent.title,
    )
    first = questions[0]
    seed = [{"role": "assistant", "content": first}]
    _sessions[child.id] = seed
    ptt_events.register_session(child.id)

    prefs = load_prefs()
    audio_b64 = ""
    tts_error = None
    t0 = time.perf_counter()
    try:
        wav = await asyncio.to_thread(
            tts.synthesize,
            settings,
            first,
            speaker_id=prefs.voicevox_speaker_id,
            engine=prefs.tts_engine,
        )
        audio_b64 = base64.b64encode(wav).decode("ascii")
    except Exception as exc:
        tts_error = str(exc)
    tts_ms = int((time.perf_counter() - t0) * 1000)
    session_store.append_record(
        settings.sessions_dir,
        child.id,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "chat",
            "transcript": "",
            "reply": first,
            "tts_ok": not tts_error,
            "tts_error": tts_error,
            "tts_engine": prefs.tts_engine,
            "input": "replay_seed",
            "client_source": "ui",
            "timing": {"stt_ms": 0, "llm_ms": 0, "tts_ms": tts_ms, "total_ms": tts_ms},
        },
        profile_id=active,
        bump_turns=False,
    )
    stored = session_store.load_meta(settings.sessions_dir, child.id) or child
    return {
        **stored.to_dict(),
        "session_id": child.id,
        "replay_of": sid,
        "reply_text": first,
        "audio_base64": audio_b64,
        "audio_mime": "audio/wav",
        "tts_error": tts_error,
        "messages": seed,
    }


@app.post("/api/rescue")
async def rescue_turn(body: RescueBody) -> dict[str, Any]:
    """Rewrite the last Kaiwa line one step simpler. No fake user utterance."""
    _require_deepseek_key()
    sid = (body.session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    sid = _resolve_session(sid)
    history = session_store.ensure_ram(_sessions, settings.sessions_dir, sid)
    if (
        not history
        or history[-1].get("role") != "assistant"
        or not str(history[-1].get("content") or "").strip()
    ):
        raise HTTPException(
            status_code=400,
            detail="Nothing to simplify yet — chat first",
        )

    last_assistant = str(history[-1].get("content") or "").strip()
    last_user = ""
    for message in reversed(history[:-1]):
        if message.get("role") == "user" and str(message.get("content") or "").strip():
            last_user = str(message["content"]).strip()
            break

    prefs = load_prefs()
    profile = load_profile()
    memory = load_memory()
    profile = apply_rescue_signals(profile)
    save_profile(profile)
    step = next_rescue_step(last_assistant)

    t0 = time.perf_counter()
    try:
        gen = await asyncio.to_thread(
            llm.rescue_rewrite,
            settings,
            _llm_messages(history),
            prefs=prefs,
            profile=profile,
            memory=memory,
            last_user=last_user,
            last_assistant=last_assistant,
            step=step,
            replay_questions=_replay_prompt_questions(sid, history),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM failed: {exc}") from exc
    llm_ms = int((time.perf_counter() - t0) * 1000)

    reply = clean_reply_for_speech(gen.reply)
    reply, better_phrase = split_try_phrase(reply)
    if not reply.strip():
        reply = better_phrase or last_assistant
    history[-1] = {"role": "assistant", "content": reply}
    reply_shape = analyze_reply_shape(
        reply=reply,
        user_text=last_user,
        locked=gen.locked,
        retry=gen.retry,
    )

    audio_b64 = ""
    tts_error = None
    t1 = time.perf_counter()
    try:
        wav = await asyncio.to_thread(
            tts.synthesize,
            settings,
            reply,
            speaker_id=prefs.voicevox_speaker_id,
            engine=prefs.tts_engine,
        )
        audio_b64 = base64.b64encode(wav).decode("ascii")
    except Exception as exc:
        tts_error = str(exc)
    tts_ms = int((time.perf_counter() - t1) * 1000)
    total_ms = int((time.perf_counter() - t0) * 1000)
    timing: dict[str, Any] = {
        "stt_ms": 0,
        "llm_ms": llm_ms,
        "tts_ms": tts_ms,
        "total_ms": total_ms,
    }

    _append_session(
        sid,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "chat",
            "rescue": True,
            "rescue_step": step,
            "transcript": "",
            "reply": reply,
            "better_phrase": better_phrase,
            "tts_ok": not tts_error,
            "tts_error": tts_error,
            "tts_engine": prefs.tts_engine,
            "correction_style": prefs.correction_style,
            "personality_id": prefs.personality_id,
            "learner_state": "help_request",
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
            "model_used": gen.model,
            "memory_updated": False,
            "timing": timing,
            "input": "rescue",
            "client_source": "ui",
            "reply_shape": reply_shape,
        },
        kind="rescue",
    )

    return {
        "session_id": sid,
        "rescue": True,
        "rescue_step": step,
        "transcript": "",
        "reply_text": reply,
        "better_phrase": better_phrase,
        "audio_base64": audio_b64,
        "audio_mime": "audio/wav",
        "tts_error": tts_error,
        "learner_state": "help_request",
        "speaking_level": profile.speaking_level,
        "comprehension_level": profile.comprehension_level,
        "model_used": gen.model,
        "memory_updated": False,
        "timing": timing,
    }


@app.post("/api/turn")
async def turn(
    audio: UploadFile = File(...),
    session_id: str = Form(default=""),
    client_source: str = Form(default=""),
) -> dict[str, Any]:
    sid = _resolve_session(session_id.strip())
    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    suffix = Path(audio.filename or "utterance.webm").suffix or ".webm"
    t0 = time.perf_counter()
    try:
        transcript, stt_meta = await asyncio.to_thread(
            stt.transcribe_audio_bytes,
            settings,
            raw,
            suffix,
            mode="chat",
            preferred_name=_preferred_name_for_stt(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc
    stt_ms = int((time.perf_counter() - t0) * 1000)

    if not transcript:
        raise HTTPException(status_code=400, detail="Could not hear any speech")

    return await _run_chat_turn(
        sid,
        transcript,
        stt_ms=stt_ms,
        stt_meta=stt_meta,
        client_source=client_source.strip().lower(),
    )


@app.post("/api/turn/text")
async def turn_text(body: TextTurnRequest) -> dict[str, Any]:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="text must be ≤ 500 characters")
    sid = _resolve_session((body.session_id or "").strip())
    return await _run_chat_turn(sid, text, stt_ms=0)


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stt_timing_fields(stt_meta: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not stt_meta:
        return out
    try:
        passes = int(stt_meta.get("passes") or 0)
    except (TypeError, ValueError):
        passes = 0
    if passes:
        out["stt_passes"] = passes
    detected = str(stt_meta.get("detected") or "").strip()
    if detected:
        out["stt_lang"] = detected
    accepted = str(stt_meta.get("accepted") or "").strip()
    if accepted:
        out["stt_accepted"] = accepted
    return out


def _stream_chat_events(
    sid: str,
    transcript: str,
    *,
    stt_ms: int,
    stt_meta: dict[str, Any] | None = None,
) -> Iterator[str]:
    """Yield SSE chunks for UI Chat (LLM deltas + sentence TTS). Not used by PTT."""
    turn_t0 = time.perf_counter()
    try:
        _require_deepseek_key()
    except HTTPException as exc:
        yield _sse_pack("error", {"detail": exc.detail})
        return

    history = session_store.ensure_ram(_sessions, settings.sessions_dir, sid)
    history.append({"role": "user", "content": transcript})
    prefs = load_prefs()
    profile = load_profile()
    memory = load_memory()
    learner_state = infer_learner_state(transcript)
    profile = apply_chat_signals(profile, learner_state, transcript)
    save_profile(profile)

    yield _sse_pack(
        "transcript",
        {
            "session_id": sid,
            "transcript": transcript,
            "stt_ms": stt_ms,
            **_stt_timing_fields(stt_meta),
        },
    )

    llm_t0 = time.perf_counter()
    raw_parts: list[str] = []
    model_used = ""
    tts_error: str | None = None
    tts_ms_total = 0
    tts_first_ms: int | None = None
    ttfa_ms: int | None = None
    audio_index = 0
    buf = SentenceBuffer()
    llm_ms = 0
    shape_retry = False
    shape_locked = False

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending_jobs: deque[tuple[float, Future[bytes]]] = deque()

            def submit_sentence(sentence: str) -> None:
                spoken = clean_reply_for_speech(sentence)
                if not spoken.strip():
                    return
                started = time.perf_counter()
                pending_jobs.append(
                    (
                        started,
                        pool.submit(
                            tts.synthesize,
                            settings,
                            spoken,
                            speaker_id=prefs.voicevox_speaker_id,
                            engine=prefs.tts_engine,
                        ),
                    )
                )

            def drain_done(*, block: bool = False) -> Iterator[str]:
                nonlocal audio_index, tts_ms_total, tts_first_ms, ttfa_ms, tts_error
                while pending_jobs and (block or pending_jobs[0][1].done()):
                    started, fut = pending_jobs.popleft()
                    try:
                        wav = fut.result()
                    except Exception as exc:
                        tts_error = str(exc)
                        continue
                    elapsed = int((time.perf_counter() - started) * 1000)
                    tts_ms_total += elapsed
                    if tts_first_ms is None:
                        tts_first_ms = elapsed
                    if ttfa_ms is None:
                        ttfa_ms = int((time.perf_counter() - turn_t0) * 1000) + int(
                            stt_ms
                        )
                    yield _sse_pack(
                        "audio",
                        {
                            "index": audio_index,
                            "audio_base64": base64.b64encode(wav).decode("ascii"),
                            "audio_mime": "audio/wav",
                        },
                    )
                    audio_index += 1

            try:
                stream = llm.chat_stream(
                    settings,
                    _llm_messages(history),
                    prefs=prefs,
                    profile=profile,
                    memory=memory,
                    learner_state=learner_state,
                    replay_questions=_replay_prompt_questions(sid, history),
                )
                model_used = stream.model
                shape_retry = stream.retry
                shape_locked = stream.locked
                for delta in stream.deltas:
                    raw_parts.append(delta)
                    yield _sse_pack("delta", {"text": delta})
                    for sentence in buf.push(delta):
                        submit_sentence(sentence)
                    yield from drain_done(block=False)
            except Exception as exc:
                history.pop()
                yield _sse_pack("error", {"detail": f"LLM failed: {exc}"})
                return

            llm_ms = int((time.perf_counter() - llm_t0) * 1000)
            remainder = buf.flush()
            if remainder:
                submit_sentence(remainder)
            yield from drain_done(block=True)
    except Exception as exc:
        if history and history[-1].get("role") == "user" and not raw_parts:
            history.pop()
        yield _sse_pack("error", {"detail": f"Stream failed: {exc}"})
        return

    raw_reply = "".join(raw_parts)
    reply = clean_reply_for_speech(raw_reply)
    reply, better_phrase = split_try_phrase(reply)
    if not reply.strip():
        reply = better_phrase or "うん。"
    history.append({"role": "assistant", "content": reply})
    reply_shape = analyze_reply_shape(
        reply=reply,
        user_text=transcript,
        locked=shape_locked,
        retry=shape_retry,
    )

    memory = note_chat_turn(memory)
    save_memory(memory)
    history_snapshot = [{"role": m["role"], "content": m["content"]} for m in history]
    threading.Thread(
        target=_chat_sidework,
        args=(transcript, learner_state, history_snapshot),
        daemon=True,
        name="kaiwa-chat-sidework",
    ).start()

    total_ms = int((time.perf_counter() - turn_t0) * 1000) + int(stt_ms)
    timing: dict[str, Any] = {
        "stt_ms": stt_ms,
        "llm_ms": llm_ms,
        "tts_ms": tts_first_ms if tts_first_ms is not None else tts_ms_total,
        "tts_total_ms": tts_ms_total,
        "total_ms": total_ms,
    }
    if ttfa_ms is not None:
        timing["ttfa_ms"] = ttfa_ms
    timing.update(_stt_timing_fields(stt_meta))

    _append_session(
        sid,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "chat",
            "transcript": transcript,
            "reply": reply,
            "better_phrase": better_phrase,
            "tts_ok": not tts_error,
            "tts_error": tts_error,
            "tts_engine": prefs.tts_engine,
            "correction_style": prefs.correction_style,
            "personality_id": prefs.personality_id,
            "learner_state": learner_state,
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
            "model_used": model_used,
            "memory_updated": False,
            "timing": timing,
            "input": "text" if stt_ms == 0 else "voice",
            "client_source": "ui_stream",
            "streamed": True,
            "reply_shape": reply_shape,
        },
        kind="chat",
    )

    yield _sse_pack(
        "final",
        {
            "session_id": sid,
            "transcript": transcript,
            "reply_text": reply,
            "better_phrase": better_phrase,
            "tts_error": tts_error,
            "learner_state": learner_state,
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
            "model_used": model_used,
            "memory_updated": False,
            "timing": timing,
        },
    )


def _sse_response(events: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/turn/stream")
async def turn_stream(
    audio: UploadFile = File(...),
    session_id: str = Form(default=""),
) -> StreamingResponse:
    sid = _resolve_session(session_id.strip())
    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    suffix = Path(audio.filename or "utterance.webm").suffix or ".webm"
    t0 = time.perf_counter()
    try:
        transcript, stt_meta = await asyncio.to_thread(
            stt.transcribe_audio_bytes,
            settings,
            raw,
            suffix,
            mode="chat",
            preferred_name=_preferred_name_for_stt(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc
    stt_ms = int((time.perf_counter() - t0) * 1000)

    if not transcript:
        raise HTTPException(status_code=400, detail="Could not hear any speech")

    return _sse_response(
        _stream_chat_events(sid, transcript, stt_ms=stt_ms, stt_meta=stt_meta)
    )


@app.post("/api/turn/text/stream")
async def turn_text_stream(body: TextTurnRequest) -> StreamingResponse:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="text must be ≤ 500 characters")
    sid = _resolve_session((body.session_id or "").strip())
    return _sse_response(_stream_chat_events(sid, text, stt_ms=0))


def _chat_sidework(
    transcript: str,
    learner_state: str,
    history_snapshot: list[dict[str, str]],
) -> None:
    """Assess + extract after the reply is already returned (soft-fail)."""
    try:
        prefs = load_prefs()
        profile = load_profile()
        profile = maybe_run_assess(
            settings,
            profile,
            transcript=transcript,
            learner_state=learner_state,
            prefs=prefs,
        )
        save_profile(profile)
    except Exception:
        pass
    try:
        prefs = load_prefs()
        profile = load_profile()
        memory = load_memory()
        memory, _ = maybe_run_extract(
            settings,
            memory,
            prefs=prefs,
            profile=profile,
            recent_messages=history_snapshot,
        )
        save_memory(memory)
    except Exception:
        pass


async def _run_chat_turn(
    sid: str,
    transcript: str,
    *,
    stt_ms: int,
    client_source: str = "",
    stt_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _require_deepseek_key()
    t0 = time.perf_counter()
    history = session_store.ensure_ram(_sessions, settings.sessions_dir, sid)
    history.append({"role": "user", "content": transcript})
    prefs = load_prefs()
    profile = load_profile()
    memory = load_memory()
    learner_state = infer_learner_state(transcript)
    # Persist streak/signals before LLM; defer assess off the critical path.
    profile = apply_chat_signals(profile, learner_state, transcript)
    save_profile(profile)

    t1 = time.perf_counter()
    try:
        gen = await asyncio.to_thread(
            llm.chat,
            settings,
            _llm_messages(history),
            prefs=prefs,
            profile=profile,
            memory=memory,
            learner_state=learner_state,
            replay_questions=_replay_prompt_questions(sid, history),
        )
    except Exception as exc:
        history.pop()
        raise HTTPException(status_code=502, detail=f"LLM failed: {exc}") from exc
    llm_ms = int((time.perf_counter() - t1) * 1000)
    model_used = gen.model

    reply = clean_reply_for_speech(gen.reply)
    reply, better_phrase = split_try_phrase(reply)
    if not reply.strip():
        # Model only emitted TRY: — keep a minimal spoken fallback
        reply = better_phrase or "うん。"
    history.append({"role": "assistant", "content": reply})
    reply_shape = analyze_reply_shape(
        reply=reply,
        user_text=transcript,
        locked=gen.locked,
        retry=gen.retry,
    )

    audio_b64 = ""
    tts_error = None
    t2 = time.perf_counter()
    try:
        wav = await asyncio.to_thread(
            tts.synthesize,
            settings,
            reply,
            speaker_id=prefs.voicevox_speaker_id,
            engine=prefs.tts_engine,
        )
        audio_b64 = base64.b64encode(wav).decode("ascii")
    except Exception as exc:
        tts_error = str(exc)
    tts_ms = int((time.perf_counter() - t2) * 1000)
    # Timing = what the user waited for (through TTS); side-work is not included.
    total_ms = int((time.perf_counter() - t0) * 1000) + int(stt_ms)
    timing: dict[str, Any] = {
        "stt_ms": stt_ms,
        "llm_ms": llm_ms,
        "tts_ms": tts_ms,
        "total_ms": total_ms,
    }
    if stt_meta:
        try:
            passes = int(stt_meta.get("passes") or 0)
        except (TypeError, ValueError):
            passes = 0
        if passes:
            timing["stt_passes"] = passes
        detected = str(stt_meta.get("detected") or "").strip()
        if detected:
            timing["stt_lang"] = detected
        accepted = str(stt_meta.get("accepted") or "").strip()
        if accepted:
            timing["stt_accepted"] = accepted


    memory = note_chat_turn(memory)
    save_memory(memory)
    history_snapshot = [{"role": m["role"], "content": m["content"]} for m in history]
    threading.Thread(
        target=_chat_sidework,
        args=(transcript, learner_state, history_snapshot),
        daemon=True,
        name="kaiwa-chat-sidework",
    ).start()

    _append_session(
        sid,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "chat",
            "transcript": transcript,
            "reply": reply,
            "better_phrase": better_phrase,
            "tts_ok": not tts_error,
            "tts_error": tts_error,
            "tts_engine": prefs.tts_engine,
            "correction_style": prefs.correction_style,
            "personality_id": prefs.personality_id,
            "learner_state": learner_state,
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
            "model_used": model_used,
            "memory_updated": False,
            "timing": timing,
            "input": "text" if stt_ms == 0 else "voice",
            "client_source": client_source or "ui",
            "reply_shape": reply_shape,
        },
        kind="chat",
    )

    if client_source == "ptt":
        ptt_events.push_event(
            user_text=transcript,
            reply_text=reply,
            better_phrase=better_phrase,
            session_id=sid,
        )

    return {
        "session_id": sid,
        "transcript": transcript,
        "reply_text": reply,
        "better_phrase": better_phrase,
        "audio_base64": audio_b64,
        "audio_mime": "audio/wav",
        "tts_error": tts_error,
        "learner_state": learner_state,
        "speaking_level": profile.speaking_level,
        "comprehension_level": profile.comprehension_level,
        "model_used": model_used,
        "memory_updated": False,
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
    after = after_id.strip()

    if src == "last_reply":
        text = _last_assistant_text(sid) if sid else None
        if not text:
            raise HTTPException(
                status_code=404,
                detail="Chat a little first, then you can say the last reply again.",
            )
        # Prefer first sentence for repeat practice.
        short = text.split("。")[0].strip()
        if short and not short.endswith("。") and "。" in text:
            short = short + "。"
        target = short or text
        return {"phrase_id": "last_reply", "text": target, "source": "last_reply", "note": ""}

    if src == "vocab":
        memory = load_memory()
        picked = next_vocab_target(memory, after_id=after)
        if not picked:
            raise HTTPException(
                status_code=404,
                detail="Chat a little more — useful lines will show up here.",
            )
        return picked

    if src == "recycle":
        memory = load_memory()
        picked = next_recycle_target(memory, after_id=after)
        if picked:
            return picked
        picked = next_vocab_target(memory, after_id="")
        if picked:
            return picked
        text = _last_assistant_text(sid) if sid else None
        if text:
            short = text.split("。")[0].strip()
            if short and not short.endswith("。") and "。" in text:
                short = short + "。"
            return {
                "phrase_id": "last_reply",
                "text": short or text,
                "source": "last_reply",
                "note": "",
            }
        raise HTTPException(
            status_code=404,
            detail="Nothing to say again yet — chat a bit, or try a light phrase from the bank.",
        )

    after_bank = after or _practice_cursor.get(sid or "_", "")
    phrase = next_phrase(after_bank or None)
    if sid:
        _practice_cursor[sid] = phrase["id"]
    else:
        _practice_cursor["_"] = phrase["id"]
    return {
        "phrase_id": phrase["id"],
        "text": phrase["text"],
        "source": "bank",
        "note": "",
    }


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
    practice_source: str = Form(default=""),
) -> dict[str, Any]:
    sid = _resolve_session(session_id.strip())
    target = (target_text or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="target_text is required")

    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    suffix = Path(audio.filename or "utterance.webm").suffix or ".webm"
    try:
        heard, _stt_meta = await asyncio.to_thread(
            stt.transcribe_audio_bytes,
            settings,
            raw,
            suffix=suffix,
            mode="ja",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc

    if not heard:
        raise HTTPException(status_code=400, detail="Could not hear any Japanese speech")

    result = score_intelligibility(target, heard)
    prefs = load_prefs()
    profile = load_profile()
    profile = apply_practice_score(profile, result.score, result.band)
    save_profile(profile)

    memory = load_memory()
    memory = note_practice_result(
        memory,
        target=target,
        band=result.band,
        practice_source=practice_source,
    )
    save_memory(memory)

    tip = ""
    tip_error = None
    try:
        _require_deepseek_key()
        tip = llm.practice_tip(
            settings,
            target=target,
            heard=heard,
            score=result.score,
            band=result.band,
            prefs=prefs,
        )
        tip = clean_reply_for_speech(tip)
    except HTTPException as exc:
        tip_error = str(exc.detail)
    except Exception as exc:
        tip_error = str(exc)

    _append_session(
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
            "practice_source": (practice_source or "").strip() or "bank",
            "speaking_level": profile.speaking_level,
            "comprehension_level": profile.comprehension_level,
        },
        kind="practice",
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
        result = answer_item(
            session,
            body.item_id.strip(),
            choice_index=body.choice_index,
            choice_indices=body.choice_indices,
            text=body.text,
        )
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
    raw_name = clip_preferred_name(str(session.answers().get("preferred_name") or ""))
    if raw_name:
        memory = load_memory()
        try:
            memory = apply_manual_memory(memory, preferred_name=raw_name)
            save_memory(memory)
        except ValueError:
            raw_name = ""
    if raw_name:
        summary["preferred_name"] = raw_name
    session.finished = True

    _append_session(
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
        kind="placement",
    )
    discard_session(session.id)

    return {
        "summary": summary,
        "speaking_level": profile.speaking_level,
        "comprehension_level": profile.comprehension_level,
        "goal_level": prefs.goal_level,
        "placement_completed": profile.placement_completed,
        "profile": profile.to_dict(),
        "prefs": {
            "goal_level": prefs.goal_level,
            "language_policy": prefs.language_policy,
            "topic_preferences": prefs.topic_preferences,
        },
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

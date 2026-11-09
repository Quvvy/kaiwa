"""Kaiwa as a stand-in for AnkiConnect, so mining tools send lines here instead of Anki.

asbplayer (YouTube, Tsugi's player, any site with a subtitle file) is pointed at
http://127.0.0.1:8787/ankiconnect. It sees one deck, "Kaiwa", and one note type,
"Kaiwa Mining"; whatever it sends becomes a mined line (course/state.py), its clip
and screenshot go to the profile's mined_media folder, and mined_enrich prepares the
card in the background.

Only browser extensions and local tools may call this: a request with a web page's
Origin (or "null") is refused, even a "simple" text/plain POST that never had a
preflight, and so is anything from the phone. The protocol follows AnkiConnect:
version ≥ 5 replies {"result", "error"}, older versions the bare result, and errors
always come back as {"result": null, "error": "..."} with status 200.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from kaiwa import phone_access
from kaiwa.course import mined, mined_enrich, mined_media
from kaiwa.course import state as course_state

router = APIRouter()

API_VERSION = 6
MAX_BODY = 20 * 1024 * 1024
EXTENSION_SCHEMES = ("chrome-extension://", "moz-extension://", "safari-web-extension://")
_last_refused: dict[str, Any] = {}


class AnkiError(Exception):
    pass


def origin_allowed(origin: str | None) -> bool:
    """No Origin (a local tool, or an extension's background worker) or an extension's own."""
    if origin is None:
        return True
    return origin.strip().lower().startswith(EXTENSION_SCHEMES)


def last_refused() -> dict[str, Any] | None:
    return dict(_last_refused) if _last_refused else None


def _cors(request: Request) -> dict[str, str]:
    headers = {"Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "POST, GET, OPTIONS", "Vary": "Origin"}
    origin = request.headers.get("origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    if request.headers.get("access-control-request-private-network"):
        headers["Access-Control-Allow-Private-Network"] = "true"
    return headers


def _refusal(request: Request) -> JSONResponse | None:
    if phone_access.is_remote(request.headers.get("host"), request.headers.get("tailscale-user-login")):
        return JSONResponse({"result": None, "error": "Kaiwa only takes mined lines on this PC"}, status_code=403)
    origin = request.headers.get("origin")
    if not origin_allowed(origin):
        _last_refused.update({"origin": origin, "at": time.time()})
        return JSONResponse({"result": None, "error": "Kaiwa only takes requests from browser extensions"},
                            status_code=403)
    return None


def fmt(version: Any, result: Any = None, error: str | None = None) -> Any:
    if error is not None:
        return {"result": None, "error": error}
    try:
        v = int(version)
    except (TypeError, ValueError):
        v = 4
    return {"result": result, "error": None} if v >= 5 else result


# ---------- media ----------

def _base():
    return mined_media.media_dir(course_state.state_path())


def _store_items(items: list[dict[str, Any]]) -> tuple[str, int]:
    """Save the first media object that carries data. Returns (stored name, audio ms)."""
    for item in items:
        if item.get("url") or item.get("path"):
            raise AnkiError("Kaiwa only accepts media sent as data")
        if item.get("data") and item.get("filename"):
            try:
                name, meta = mined_media.store(_base(), str(item["filename"]), str(item["data"]))
            except mined_media.MediaError as exc:
                raise AnkiError(str(exc)) from exc
            return name, meta.get("audio_ms", 0)
    return "", 0


def _from_refs(refs: list[str]) -> tuple[str, int]:
    """A [sound:x] or <img src=x> pointing at a file sent earlier with storeMediaFile."""
    base = _base()
    for ref in refs:
        try:
            name = mined_media.safe_name(ref)
        except mined_media.MediaError:
            continue
        if mined_media.path_for(base, name):
            ms = mined_media.audio_seconds_of(base, name) if mined_media.kind_of(ref) == "audio" else 0
            return name, ms
    return "", 0


def _media_for(capture: dict[str, Any]) -> dict[str, Any]:
    audio, audio_ms = _store_items(capture["audio"])
    if not audio:
        audio, audio_ms = _from_refs(capture["audio_refs"])
    image, _ = _store_items(capture["image"])
    if not image:
        image, _ = _from_refs(capture["image_refs"])
    return {"audio": audio, "audio_ms": audio_ms, "image": image}


# ---------- actions ----------

def _rows() -> list[dict[str, Any]]:
    return course_state.mined_rows()


def _by_note_id(note_id: Any) -> dict[str, Any] | None:
    try:
        nid = int(note_id)
    except (TypeError, ValueError):
        return None
    return next((r for r in _rows() if r["note_id"] == nid), None)


def _can_add(note: dict[str, Any]) -> str | None:
    """Why this note can't be added, or None."""
    capture = mined.note_to_capture(note if isinstance(note, dict) else {})
    try:
        mined.validate_capture(capture)
    except ValueError as exc:
        return str(exc)
    allow = bool(((note.get("options") or {}) if isinstance(note, dict) else {}).get("allowDuplicate"))
    key = mined.normalize_key(capture["text"])
    if not allow and any(r["key"] == key for r in _rows()):
        return course_state.DUPLICATE
    return None


def add_note(note: dict[str, Any]) -> int:
    if not isinstance(note, dict):
        raise AnkiError("note is missing")
    capture = mined.note_to_capture(note)
    try:
        mined.validate_capture(capture)
    except ValueError as exc:
        raise AnkiError(str(exc)) from exc
    allow = bool((note.get("options") or {}).get("allowDuplicate"))
    reason = _can_add(note)
    if reason == course_state.DUPLICATE and not allow:
        raise AnkiError(reason)
    media = _media_for(capture)
    try:
        row, _created = course_state.add_mined(capture, media, allow_dup=allow)
    except ValueError as exc:
        raise AnkiError(str(exc)) from exc
    mined_enrich.kick()
    return row["note_id"]


def update_note(note: dict[str, Any]) -> None:
    if not isinstance(note, dict) or _by_note_id(note.get("id")) is None:
        raise AnkiError(f"note was not found: {note.get('id') if isinstance(note, dict) else ''}")
    fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
    capture = mined.note_to_capture(note)
    present = {str(k).strip().casefold() for k in fields}
    changes: dict[str, Any] = {}
    if "sentence" in present and capture["text"]:
        changes["text"] = capture["text"]
    if "word" in present:
        changes["word"] = capture["word"]
    if "translation" in present:
        changes["en_sub"] = capture["en_sub"]
    if "source" in present or "url" in present:
        changes["source"] = {k: capture["source"][k] for k in ("title", "url", "start_ms")}
    media = _media_for(capture)
    if media["audio"]:
        changes.update({"audio": media["audio"], "audio_ms": media["audio_ms"]})
    if media["image"]:
        changes["image"] = media["image"]
    if note.get("tags") is not None:
        changes["tags"] = note.get("tags") or []
    try:
        _row, unused = course_state.update_mined(int(note["id"]), changes)
    except (KeyError, ValueError) as exc:
        raise AnkiError(str(exc).strip("'\"")) from exc
    mined_media.delete(_base(), unused)
    mined_enrich.kick()


def _tags(params: dict[str, Any], add: bool) -> None:
    tags = str(params.get("tags") or "").split()
    for nid in params.get("notes") or []:
        row = _by_note_id(nid)
        if row is None:
            continue
        now = [t for t in row["tags"] if t not in tags] + (tags if add else [])
        course_state.update_mined(row["note_id"], {"tags": list(dict.fromkeys(now))})


def store_media_file(params: dict[str, Any]) -> str:
    filename = str(params.get("filename") or "")
    if params.get("url") or params.get("path"):
        raise AnkiError("Kaiwa only accepts media sent as data")
    if not params.get("data"):
        raise AnkiError("storeMediaFile needs data")
    try:
        mined_media.store(_base(), filename, str(params["data"]))
    except mined_media.MediaError as exc:
        raise AnkiError(str(exc)) from exc
    return filename  # the tool writes [sound:<its own name>]; safe_name maps it back to this file


def retrieve_media_file(params: dict[str, Any]) -> str | bool:
    try:
        path = mined_media.path_for(_base(), mined_media.safe_name(str(params.get("filename") or "")))
    except mined_media.MediaError:
        return False
    return base64.b64encode(path.read_bytes()).decode("ascii") if path else False


def _notes_info(params: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for nid in params.get("notes") or []:
        row = _by_note_id(nid)
        out.append(mined.note_info(row) if row else {})
    return out


def _cards_info(params: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for cid in params.get("cards") or []:
        row = _by_note_id(cid)
        if row is None:
            out.append({})
            continue
        info = mined.note_info(row)
        out.append({"cardId": row["note_id"], "note": row["note_id"], "deckName": mined.DECK,
                    "modelName": mined.MODEL, "fields": info["fields"], "mod": info["mod"], "interval": 0})
    return out


def _model_fields(params: dict[str, Any]) -> list[str]:
    name = params.get("modelName")
    if name != mined.MODEL:
        raise AnkiError(f"model was not found: {name}")
    return list(mined.FIELDS)


def _multi(params: dict[str, Any]) -> list[Any]:
    out = []
    for sub in params.get("actions") or []:
        sub = sub if isinstance(sub, dict) else {}
        if sub.get("action") == "multi":
            out.append(fmt(4, error="multi can't contain multi"))
            continue
        out.append(dispatch(sub))
    return out


ACTIONS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "version": lambda p: API_VERSION,
    "requestPermission": lambda p: {"permission": "granted", "requireApiKey": False, "version": API_VERSION},
    "deckNames": lambda p: [mined.DECK],
    "deckNamesAndIds": lambda p: {mined.DECK: 1},
    "modelNames": lambda p: [mined.MODEL],
    "modelNamesAndIds": lambda p: {mined.MODEL: 1},
    "modelFieldNames": _model_fields,
    "findModelsByName": lambda p: [{"name": mined.MODEL, "flds": [{"name": f, "ord": i} for i, f in enumerate(mined.FIELDS)]}],
    "findNotes": lambda p: mined.match_query(_rows(), str(p.get("query") or "")),
    "findCards": lambda p: mined.match_query(_rows(), str(p.get("query") or "")),
    "notesInfo": _notes_info,
    "cardsInfo": _cards_info,
    "notesModTime": lambda p: [{"noteId": i["noteId"], "mod": i["mod"]} for i in _notes_info(p) if i],
    "cardsModTime": lambda p: [{"cardId": i["noteId"], "mod": i["mod"]} for i in _notes_info({"notes": p.get("cards")}) if i],
    "areSuspended": lambda p: [False for _ in p.get("cards") or []],
    "getIntervals": lambda p: [0 for _ in p.get("cards") or []],
    "canAddNotes": lambda p: [_can_add(n) is None for n in p.get("notes") or []],
    "canAddNotesWithErrorDetail": lambda p: [
        {"canAdd": r is None, "error": r} for r in (_can_add(n) for n in p.get("notes") or [])],
    "addNote": lambda p: add_note(p.get("note")),
    "guiAddCards": lambda p: add_note(p.get("note")),
    "addNotes": lambda p: [_add_or_none(n) for n in p.get("notes") or []],
    "updateNoteFields": lambda p: update_note(p.get("note")),
    "updateNote": lambda p: update_note(p.get("note")),
    "addTags": lambda p: _tags(p, True),
    "removeTags": lambda p: _tags(p, False),
    "getTags": lambda p: sorted({t for r in _rows() for t in r["tags"]}),
    "storeMediaFile": store_media_file,
    "retrieveMediaFile": retrieve_media_file,
    "createDeck": lambda p: 1,
    "changeDeck": lambda p: None,
    "createModel": lambda p: _refuse(f"Kaiwa has one note type: {mined.MODEL}"),
    "guiBrowse": lambda p: [],
    "guiEditNote": lambda p: None,
    "guiSelectedNotes": lambda p: [],
    "sync": lambda p: None,
    "getProfiles": lambda p: ["Kaiwa"],
    "loadProfile": lambda p: True,
    "multi": _multi,
}


def _refuse(message: str) -> Any:
    raise AnkiError(message)


def _add_or_none(note: Any) -> int | None:
    try:
        return add_note(note)
    except AnkiError:
        return None


def dispatch(payload: Any) -> Any:
    """One AnkiConnect request → its reply, formatted for the version it asked for."""
    if not isinstance(payload, dict):
        return fmt(4, error="request must be a JSON object")
    version = payload.get("version", 4)
    action = payload.get("action")
    handler = ACTIONS.get(str(action))
    if handler is None:
        return fmt(version, error="unsupported action")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    try:
        return fmt(version, handler(params))
    except AnkiError as exc:
        return fmt(version, error=str(exc))
    except Exception as exc:  # a tool should get an error, never a broken connection
        return fmt(version, error=f"Kaiwa couldn't do {action}: {exc}")


@router.get("/ankiconnect")
@router.get("/ankiconnect/")
async def info(request: Request) -> Response:
    refused = _refusal(request)
    if refused:
        return refused
    return PlainTextResponse(f"Kaiwa AnkiConnect v.{API_VERSION}", headers=_cors(request))


@router.options("/ankiconnect")
@router.options("/ankiconnect/")
async def preflight(request: Request) -> Response:
    refused = _refusal(request)
    if refused:
        return refused
    return Response(status_code=200, headers=_cors(request))


@router.post("/ankiconnect")
@router.post("/ankiconnect/")
async def handle(request: Request) -> Response:
    refused = _refusal(request)
    if refused:
        return refused
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > MAX_BODY:
        return JSONResponse({"result": None, "error": "request too large"}, status_code=413)
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            return JSONResponse({"result": None, "error": "request too large"}, status_code=413)
    if not body.strip():
        return PlainTextResponse(f"Kaiwa AnkiConnect v.{API_VERSION}", headers=_cors(request))
    try:
        payload = json.loads(bytes(body).decode("utf-8"))  # whatever the Content-Type says
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JSONResponse(fmt(6, error="request body isn't valid JSON"), headers=_cors(request))
    reply = await asyncio.to_thread(dispatch, payload)
    return JSONResponse(reply, headers=_cors(request))

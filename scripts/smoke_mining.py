"""Sentence mining: the AnkiConnect adapter asbplayer talks to, media, and card preparation. No network."""

from __future__ import annotations

import base64
import dataclasses
import io
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["KAIWA_DATA_DIR"] = tempfile.mkdtemp(prefix="kaiwa-mining-smoke-")

import av  # noqa: E402
import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from kaiwa import ankiconnect  # noqa: E402
from kaiwa.app import app  # noqa: E402
from kaiwa.config import get_settings  # noqa: E402
from kaiwa.course import mined, mined_enrich, mined_media  # noqa: E402
from kaiwa.course import state as course_state  # noqa: E402

EXT = {"origin": "chrome-extension://asbplayerid"}


def _check(ok: bool, label: str) -> None:
    line = ("ok  " if ok else "FAIL") + label
    sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()
    if not ok:
        raise SystemExit(f"smoke_mining failed: {label}")


def _clip(seconds: float, fmt: str = "mp4") -> bytes:
    """A sine tone as m4a/aac (asbplayer's mp3 stand-in) or ogg/opus."""
    rate = 48000
    out = io.BytesIO()
    opts = {"movflags": "frag_keyframe+empty_moov"} if fmt == "mp4" else {}
    with av.open(out, "w", format=fmt, options=opts) as dst:
        stream = dst.add_stream("aac" if fmt == "mp4" else "libopus", rate=rate)
        stream.layout = "mono"
        t = np.arange(int(rate * seconds)) / rate
        samples = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        for i in range(0, len(samples), 1024):
            frame = av.AudioFrame.from_ndarray(samples[i:i + 1024].reshape(1, -1), format="fltp", layout="mono")
            frame.sample_rate = rate
            for packet in stream.encode(frame):
                dst.mux(packet)
        for packet in stream.encode(None):
            dst.mux(packet)
    return out.getvalue()


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
B64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731


def _post(client: TestClient, body, *, headers=None, raw: str | None = None):
    # No Content-Type, like asbplayer's fetch: the body arrives as text/plain.
    data = raw if raw is not None else json.dumps(body)
    return client.post("/ankiconnect", content=data.encode("utf-8"), headers={**EXT, **(headers or {})})


def _note(text: str, **extra) -> dict:
    fields = {"Sentence": text, "Translation": "No way.", "Source": "Frieren E03 (12:34)", "URL": "https://youtu.be/x"}
    fields.update(extra.pop("fields", {}))
    return {"deckName": "Kaiwa", "modelName": "Kaiwa Mining", "fields": fields, "tags": ["asbplayer"], **extra}


def protocol(client: TestClient) -> None:
    r = _post(client, {"action": "version", "version": 6})
    _check(r.status_code == 200 and r.json() == {"result": 6, "error": None}, "version 6 gets {result, error}")
    _check(_post(client, {"action": "deckNames"}).json() == ["Kaiwa"], "no version (4) gets the bare result")
    _check(_post(client, {"action": "requestPermission", "version": 6}).json()["result"]["permission"] == "granted",
           "requestPermission is granted")
    fields = _post(client, {"action": "modelFieldNames", "version": 6, "params": {"modelName": "Kaiwa Mining"}}).json()
    _check(fields["result"] == list(mined.FIELDS), "the note type's fields are listed")
    bad = _post(client, {"action": "modelFieldNames", "version": 6, "params": {"modelName": "Basic"}}).json()
    _check(bad["result"] is None and "not found" in bad["error"], "other note types aren't found")
    _check(_post(client, {"action": "deleteDecks", "version": 6}).json()["error"] == "unsupported action",
           "unknown actions are unsupported")
    _check(_post(client, None, raw="{nope").json()["error"].startswith("request body"), "bad JSON is an error, not a crash")
    multi = _post(client, {"action": "multi", "version": 6, "params": {"actions": [
        {"action": "version"}, {"action": "deckNames", "version": 6}, {"action": "nope", "version": 6}]}}).json()
    _check(multi["result"][0] == 6 and multi["result"][1] == {"result": ["Kaiwa"], "error": None}
           and multi["result"][2]["error"] == "unsupported action", "multi answers each action in its own version")


def access(client: TestClient) -> None:
    pre = client.options("/ankiconnect", headers={**EXT, "access-control-request-private-network": "true",
                                                  "access-control-request-method": "POST"})
    _check(pre.status_code == 200 and pre.headers.get("access-control-allow-origin") == EXT["origin"]
           and pre.headers.get("access-control-allow-private-network") == "true", "preflight from an extension is allowed")
    before = len(course_state.mined_rows())
    for origin in ("https://evil.example", "null", "http://127.0.0.1:8787"):
        r = client.post("/ankiconnect", content=json.dumps({"action": "addNote", "version": 6,
                        "params": {"note": _note("悪いページの文")}}).encode(), headers={"origin": origin})
        _check(r.status_code == 403, f"a POST from {origin} is refused (no preflight needed to be refused)")
    _check(len(course_state.mined_rows()) == before, "nothing was kept from a web page")
    _check(ankiconnect.last_refused()["origin"] == "http://127.0.0.1:8787", "the last refused origin is remembered")
    ok = client.post("/ankiconnect", content=b'{"action":"version"}', headers={"origin": "moz-extension://abc"})
    _check(ok.status_code == 200 and ok.json() == 6, "Firefox extensions are allowed")
    local = client.post("/ankiconnect", content=b'{"action":"version"}')
    _check(local.status_code == 200, "a local tool with no Origin is allowed")
    remote = client.post("/ankiconnect", content=b'{"action":"version"}', headers={"host": "pc.tail1234.ts.net"})
    phone = client.post("/ankiconnect", content=b'{"action":"version"}', headers={"tailscale-user-login": "me@x"})
    _check(remote.status_code == 403 and phone.status_code == 403, "the phone can't mine into the PC")
    big = client.post("/ankiconnect", content=b"{}", headers={**EXT, "content-length": str(ankiconnect.MAX_BODY + 1)})
    _check(big.status_code == 413, "an oversized body is refused")


def adding(client: TestClient) -> None:
    clip = B64(_clip(2.0))
    r = _post(client, {"action": "storeMediaFile", "version": 6, "params": {"filename": "asbp_a.m4a", "data": clip}})
    _check(r.json() == {"result": "asbp_a.m4a", "error": None}, "storeMediaFile returns the tool's own name")
    for bad in ({"filename": "x.mp3", "path": "/etc/passwd"}, {"filename": "x.mp3", "url": "http://example.com/x"}):
        _check("as data" in _post(client, {"action": "storeMediaFile", "version": 6, "params": bad}).json()["error"],
               "media by path or URL is refused")
    long = _post(client, {"action": "storeMediaFile", "version": 6, "params": {"filename": "long.m4a",
                                                                             "data": B64(_clip(40))}}).json()
    _check(long["result"] is None and "30 seconds" in long["error"], "a clip over 30 s is refused")
    junk = _post(client, {"action": "storeMediaFile", "version": 6, "params": {"filename": "x.exe", "data": clip}}).json()
    _check(junk["error"] and "audio and images" in junk["error"], "other file types are refused")

    # asbplayer's default: media inside addNote, as objects.
    note = _note("今日は<b>無理</b>だよ。<br>また明日ね",
                 audio={"filename": "asbp_1.mp4", "data": clip, "fields": ["Audio"]},
                 picture={"filename": "asbp_1.jpeg", "data": B64(JPEG), "fields": ["Image"]})
    added = _post(client, {"action": "addNote", "version": 6, "params": {"note": note}}).json()
    _check(isinstance(added["result"], int) and added["error"] is None, "addNote returns a note id")
    row = course_state.mined_rows()[-1]
    _check(row["text"] == "今日は無理だよ。また明日ね" and row["word"] == "無理", "<br> joins Japanese lines; <b> marks the word")
    _check(row["status"] == "pending" and row["audio"] and row["image"] and 1500 < row["audio_ms"] < 2600,
           "the line waits to be prepared, with its clip and screenshot")
    _check(row["source"]["title"] == "Frieren E03" and row["source"]["start_ms"] == 754000, "the source and time are kept")
    media = client.get(f"/api/course/mined/media/{row['audio']}")
    _check(media.status_code == 200 and media.headers["content-type"].startswith("audio/"), "the clip is served")
    for bad in ("..%2Fcourse_state.json", "../course_state.json", mined_media.safe_name("never.mp3")):
        got = client.get(f"/api/course/mined/media/{bad}")
        _check(got.status_code in (404, 405) and b"cards" not in got.content, f"no file outside the kept ones ({bad})")

    dup = _post(client, {"action": "addNote", "version": 6, "params": {"note": _note("今日は無理だよ。また明日ね")}}).json()
    _check(dup["result"] is None and "duplicate" in dup["error"], "the same line twice is a duplicate")
    again = _post(client, {"action": "addNote", "version": 6, "params": {"note": _note(
        "今日は無理だよ。 また明日ね!", options={"allowDuplicate": True})}}).json()
    _check(again["result"] == added["result"] and len(course_state.mined_rows()) == 1,
           "allowDuplicate gives the same note back, never a second card")
    empty = _post(client, {"action": "addNote", "version": 6, "params": {"note": _note("Hello there")}}).json()
    _check(empty["result"] is None and "empty" in empty["error"], "a line with no Japanese isn't kept")
    can = _post(client, {"action": "canAddNotesWithErrorDetail", "version": 6, "params": {"notes": [
        _note("今日は無理だよ。また明日ね"), _note("新しい文です")]}}).json()["result"]
    _check(can[0]["canAdd"] is False and "duplicate" in can[0]["error"] and can[1] == {"canAdd": True, "error": None},
           "canAddNotesWithErrorDetail explains duplicates")

    # storeMediaFile first, then a [sound:] reference in a field (asbplayer's update/GUI modes).
    _post(client, {"action": "storeMediaFile", "version": 6, "params": {"filename": "asbp_2.ogg", "data": B64(_clip(1.5, "ogg"))}})
    ref = _post(client, {"action": "addNote", "version": 6, "params": {"note": _note(
        "行くぞ", fields={"Audio": "[sound:asbp_2.ogg]"})}}).json()
    ref_row = next(r for r in course_state.mined_rows() if r["note_id"] == ref["result"])
    _check(ref_row["audio"] == mined_media.safe_name("asbp_2.ogg") and ref_row["audio_ms"] > 1000,
           "a [sound:] reference links a file stored earlier")

    # "Update last card": findNotes added:1 → notesInfo → updateNoteFields.
    found = _post(client, {"action": "findNotes", "version": 6, "params": {"query": "deck:Kaiwa added:1"}}).json()["result"]
    _check(set(found) == {added["result"], ref["result"]}, "findNotes added:1 finds today's lines")
    info = _post(client, {"action": "notesInfo", "version": 6, "params": {"notes": [ref["result"]]}}).json()["result"][0]
    _check(info["noteId"] == ref["result"] and info["fields"]["Sentence"]["value"] == "行くぞ"
           and info["fields"]["Audio"]["value"].startswith("[sound:"), "notesInfo describes the line like a note")
    rev = ref_row["rev"]
    up = _post(client, {"action": "updateNoteFields", "version": 6, "params": {"note": {
        "id": ref["result"], "fields": {"Sentence": "行くぞ、みんな"},
        "picture": [{"filename": "asbp_2.png", "data": B64(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32), "fields": ["Image"]}]}}}).json()
    after = next(r for r in course_state.mined_rows() if r["note_id"] == ref["result"])
    _check(up == {"result": None, "error": None} and after["text"] == "行くぞ、みんな" and after["rev"] == rev + 1
           and after["image"], "updateNoteFields changes the line, adds the screenshot, and re-prepares it")
    _post(client, {"action": "addTags", "version": 6, "params": {"notes": [ref["result"]], "tags": "anime frieren"}})
    tagged = next(r for r in course_state.mined_rows() if r["note_id"] == ref["result"])
    _check({"anime", "frieren"} <= set(tagged["tags"]), "addTags keeps tags")

    listing = client.get("/api/course/mined").json()
    _check(listing["counts"]["pending"] == 2 and listing["path"] == "/ankiconnect" and listing["rows"][0]["text"] == "行くぞ、みんな",
           "the Mined lines page lists newest first, with status counts")

    base = mined_media.media_dir(course_state.state_path())
    gone = client.delete(f"/api/course/mined/{ref_row['id']}")
    _check(gone.status_code == 200 and not mined_media.path_for(base, ref_row["audio"]), "removing a line deletes its files")
    stray = base / mined_media.safe_name("stray.mp3")
    stray.write_bytes(b"x")
    os.utime(stray, (time.time() - 2 * 86400,) * 2)
    _check(mined_media.sweep_orphans(base, {after["audio"], row["audio"], row["image"]}) >= 1 and not stray.exists(),
           "old uploads no line uses are swept")


def preparation() -> None:
    real = mined_enrich.llm.complete_json
    with_key = dataclasses.replace(get_settings(), deepseek_api_key="test")
    no_key = dataclasses.replace(get_settings(), deepseek_api_key="")
    good = {"kana": "きょうはむりだよ。またあしたね", "en": "Today's no good. See you tomorrow.",
            "note": "無理 (むり): impossible, no way.", "wrong": ["Today is fine. See you later.", "I'm busy today. Bye."]}
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "course_state.json"
        row, _ = course_state.add_mined({"text": "今日は無理だよ。また明日ね", "word": "無理"}, path=path)
        try:
            mined_enrich.llm.complete_json = lambda *a, **k: good
            _check(mined_enrich.run(path, settings=no_key) == 0 and course_state.mined_rows(path=path)[0]["attempts"] == 0,
                   "with no DeepSeek key, lines wait without using up tries")
            mined_enrich.run(path, settings=with_key)
            r = course_state.mined_rows(path=path)[0]
            _check(r["status"] == "ready" and r["kana"] == good["kana"] and r["kana_src"] == "llm" and len(r["wrong"]) == 2,
                   "a good reply makes the line ready")

            row2, _ = course_state.add_mined({"text": "空が青い"}, path=path)
            mined_enrich.llm.complete_json = lambda *a, **k: {**good, "kana": "空がアオい"}
            mined_enrich.run(path, settings=with_key)
            r2 = next(r for r in course_state.mined_rows(path=path) if r["id"] == row2["id"])
            _check(r2["status"] == "ready" and r2["kana_src"] == "auto" and "空" not in r2["kana"],
                   "a reading with kanji left in falls back to the automatic one")

            row3, _ = course_state.add_mined({"text": "どうしてここに"}, path=path)
            calls = []
            mined_enrich.llm.complete_json = lambda *a, **k: calls.append(1) or {**good, "wrong": [good["en"], "x y"]}
            mined_enrich.run(path, settings=with_key)
            r3 = next(r for r in course_state.mined_rows(path=path) if r["id"] == row3["id"])
            _check(len(calls) == 2 and r3["status"] == "pending" and r3["attempts"] == 1 and r3["next_try"],
                   "wrong answers equal to the meaning are retried once, then wait to try again later")
            _check(mined_enrich.run(path, settings=with_key) == 0, "a line waiting for its next try isn't retried early")
            for _ in range(3):
                course_state.store_enrichment(row3["id"], r3["rev"], None, path=path)
            r3 = next(r for r in course_state.mined_rows(path=path) if r["id"] == row3["id"])
            _check(r3["status"] == "failed" and r3["error"], "after four failed tries a line is marked couldn't prepare")
            _check(course_state.retry_mined(row3["id"], path=path)
                   and next(r for r in course_state.mined_rows(path=path) if r["id"] == row3["id"])["status"] == "pending",
                   "Retry puts it back in line")
            _check(course_state.store_enrichment(row3["id"], 999, good, path=path) is None,
                   "a result for an older version of the line is thrown away")
            _check(mined_enrich.check({"text": "テスト"}, {**good, "en": "テスト"}) is None, "a meaning in Japanese is refused")
            _check(mined_enrich.check({"text": "テスト"}, good)["kana"] == "テスト", "a line without kanji is its own reading")
        finally:
            mined_enrich.llm.complete_json = real


def main() -> None:
    client = TestClient(app)  # no `with`: startup would warm Whisper and the voice engine
    protocol(client)
    access(client)
    adding(client)
    preparation()
    print("smoke_mining ok")


if __name__ == "__main__":
    main()

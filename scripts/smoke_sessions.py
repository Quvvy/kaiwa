from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.session_log import append_session_log
from kaiwa.session_store import (
    TITLE_MAX,
    append_record,
    attach_legacy,
    create_session,
    hydrate,
    jsonl_path,
    list_sessions,
    load_meta,
    other_named_profile,
    revision_stale,
)


def _check(ok: bool, label: str) -> None:
    status = "ok  " if ok else "FAIL"
    line = status + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if not ok:
        raise SystemExit(f"smoke_sessions failed: {label}")


def main() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        meta = create_session(root, "alice")
        _check(meta.profile_id == "alice", "create binds profile_id")
        _check(jsonl_path(root, meta.id).is_file(), "create touches jsonl")
        _check(not revision_stale(meta), "new session is current revision")

        append_record(
            root,
            meta.id,
            {
                "ts": "2026-08-13T00:00:00+00:00",
                "mode": "chat",
                "transcript": "猫好きです",
                "reply": "そうなんだ。猫好き？",
            },
            profile_id="alice",
            bump_turns=True,
            title_hint="猫好きです",
        )
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-08-13T00:00:01+00:00",
                "mode": "chat",
                "rescue": True,
                "transcript": "",
                "reply": "猫、好き？それとも犬？",
            },
            profile_id="alice",
            bump_turns=False,
        )
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-08-13T00:00:02+00:00",
                "mode": "practice",
                "target": "猫好きです",
            },
            profile_id="alice",
            bump_turns=False,
        )

        messages = hydrate(root, meta.id)
        _check(len(messages) == 2, "hydrate is one exchange")
        _check(
            [m["role"] for m in messages] == ["user", "assistant"],
            "hydrate user then assistant",
        )
        _check(messages[0] == {"role": "user", "content": "猫好きです"}, "user line kept")
        _check(
            messages[1]["content"] == "猫、好き？それとも犬？",
            "rescue replaces last assistant",
        )
        _check(all(m["role"] != "user" or m["content"] != "わかりません" for m in messages), "no fake user line")

        stored = load_meta(root, meta.id)
        assert stored is not None
        _check(stored.turn_count == 1, "rescue does not bump turn_count")
        _check(stored.title == "猫好きです", "title from first user line")
        _check(len(stored.title) <= TITLE_MAX, "title capped")

        listed = list_sessions(root, "alice")
        _check(len(listed) == 1 and listed[0].id == meta.id, "list by profile")
        row = listed[0].to_dict()
        _check(row.get("title") == "猫好きです", "list payload has title")
        _check(bool(row.get("updated")), "list payload has updated")
        _check(row.get("turn_count") == 1, "list payload has turn_count")
        _check(list_sessions(root, "bob") == [], "other profile sees nothing")

        old_id = meta.id
        create_session(root, "alice")
        _check(jsonl_path(root, old_id).is_file(), "new chat leaves old jsonl")
        _check(len(list_sessions(root, "alice")) == 2, "both sessions listed")

        legacy_id = "legacyfile"
        append_session_log(
            root,
            legacy_id,
            {
                "ts": "2026-01-01T00:00:00+00:00",
                "mode": "chat",
                "transcript": "こんにちは",
                "reply": "元気？",
            },
        )
        attached = list_sessions(root, "alice")
        ids = {m.id for m in attached}
        _check(legacy_id in ids, "legacy jsonl attaches to active profile")
        legacy_meta = load_meta(root, legacy_id)
        assert legacy_meta is not None
        _check(legacy_meta.profile_id == "alice", "legacy meta profile_id written")
        _check(legacy_meta.title == "こんにちは", "legacy title from first transcript")
        _check(revision_stale(legacy_meta), "legacy revision is stale")

        other = create_session(root, "bob")
        _check(
            other_named_profile(other, "alice", {"alice", "bob"}),
            "bob session is other named profile for alice",
        )
        _check(
            not other_named_profile(stored, "alice", {"alice", "bob"}),
            "own session is not other profile",
        )

        line = jsonl_path(root, meta.id).read_text(encoding="utf-8").splitlines()[0]
        row = json.loads(line)
        _check(row.get("profile_id") == "alice", "jsonl lines include profile_id")

    print("smoke_sessions ok")


if __name__ == "__main__":
    main()

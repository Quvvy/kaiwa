from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.session_store import (
    append_record,
    assistant_questions,
    create_replay_session,
    create_session,
    hydrate,
    jsonl_path,
    questions_for_replay,
    replay_remaining,
    replay_title,
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
        raise SystemExit(f"smoke_replay failed: {label}")


def main() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        empty = create_session(root, "alice")
        _check(questions_for_replay(root, empty.id) == [], "empty parent has no questions")
        _check(replay_title("") == "Again: Untitled chat", "empty title becomes Untitled")
        _check(replay_title("猫好きです").startswith("Again: "), "title prefixed")
        _check(replay_title("Again: 猫") == "Again: 猫", "do not double-prefix")

        parent = create_session(root, "alice")
        append_record(
            root,
            parent.id,
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
            parent.id,
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
            parent.id,
            {
                "ts": "2026-08-13T00:00:02+00:00",
                "mode": "chat",
                "transcript": "猫",
                "reply": "いいね。何色？",
            },
            profile_id="alice",
            bump_turns=True,
        )
        parent_jsonl = jsonl_path(root, parent.id).read_text(encoding="utf-8")

        messages = hydrate(root, parent.id)
        qs = assistant_questions(messages)
        _check(qs == ["猫、好き？それとも犬？", "いいね。何色？"], "extract uses rescue text")
        _check(questions_for_replay(root, parent.id) == qs, "parent questions from hydrate")

        child = create_replay_session(
            root,
            "alice",
            parent_id=parent.id,
            questions=qs,
            parent_title="猫好きです",
        )
        _check(child.replay_of == parent.id, "child replay_of parent")
        _check(child.replay_questions == qs, "child copies question list")
        _check(child.title == "Again: 猫好きです", "child title")
        _check(child.turn_count == 0, "seed does not bump turns")

        append_record(
            root,
            child.id,
            {
                "ts": "2026-08-13T00:01:00+00:00",
                "mode": "chat",
                "transcript": "",
                "reply": qs[0],
                "input": "replay_seed",
            },
            profile_id="alice",
            bump_turns=False,
        )
        seeded = hydrate(root, child.id)
        _check(len(seeded) == 1 and seeded[0]["role"] == "assistant", "seed hydrate is one assistant")
        _check(seeded[0]["content"] == qs[0], "seed is first question")
        _check(replay_remaining(qs, seeded) == qs, "before answers remaining is all questions")
        _check(
            jsonl_path(root, parent.id).read_text(encoding="utf-8") == parent_jsonl,
            "parent jsonl unchanged",
        )

        after_one = seeded + [{"role": "user", "content": "猫"}]
        _check(replay_remaining(qs, after_one) == [qs[1]], "after one answer remaining is the rest")
        after_all = after_one + [
            {"role": "assistant", "content": qs[1]},
            {"role": "user", "content": "白"},
        ]
        _check(replay_remaining(qs, after_all) == [], "after last answer remaining is empty")

        grandchild = create_replay_session(
            root,
            "alice",
            parent_id=child.id,
            questions=questions_for_replay(root, child.id),
            parent_title=child.title,
        )
        _check(grandchild.replay_questions == qs, "again on child copies stored list")
        _check(grandchild.replay_of == child.id, "grandchild replay_of child")

    print("smoke_replay ok")


if __name__ == "__main__":
    main()

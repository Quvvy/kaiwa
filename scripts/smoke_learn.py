from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.persona import PROMPT_REVISION
from kaiwa.practice.cards import (
    SPEAKABLE_ETTO,
    append_card,
    build_card,
    is_practice_worthy,
    maybe_write_card,
    newest_unused,
)
from kaiwa.practice.learn import STARTER_CARDS, LINES_CAP, today_payload
from kaiwa.practice.sitting import finish_sitting, recent_practiced_lines, start_sitting


def _check(cond: bool, label: str) -> None:
    if not cond:
        raise SystemExit(f"fail {label}")
    print(f"ok   {label}")


def _write(path: Path, *, session_id: str, line: str, speakable: str, ts: str) -> dict:
    card = build_card(
        session_id=session_id,
        signal="struggling",
        learner_line=line,
        tutor_reply=speakable,
        speakable=speakable,
        help_type="particle",
    )
    card["ts"] = ts
    return append_card(card, path=path)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cards_file = Path(tmpdir) / "struggle_cards.jsonl"
        empty = today_payload(cards_path=cards_file)
        _check(empty.get("source") == "starter", "empty cards use starters")
        speakables = [row.get("speakable") for row in (empty.get("lines") or [])]
        _check(
            speakables == [card["speakable"] for card in STARTER_CARDS],
            "starter speakables are canned",
        )
        _check(
            all(set(row.keys()) == {"speakable", "card_id"} for row in empty["lines"]),
            "starter line objects have speakable and card_id only",
        )
        _check(
            all(str(row.get("card_id") or "").startswith("learn:") for row in empty["lines"]),
            "starter ids use learn prefix",
        )
        _check(
            all("help_type" not in row and "signal" not in row for row in empty["lines"]),
            "starter lines have no tags",
        )

        freeze = maybe_write_card(
            session_id="s-freeze",
            history=[{"role": "assistant", "content": "ゆっくりでいいよ。"}],
            learner_state="flowing",
            transcript="えっと",
            reply="ゆっくりでいいよ。",
            path=cards_file,
        )
        _check(freeze is not None, "freeze card writes")
        freeze_only = today_payload(cards_path=cards_file)
        _check(freeze_only.get("source") == "starter", "freeze-only cards still use starters")
        _check(
            SPEAKABLE_ETTO not in [row.get("speakable") for row in freeze_only["lines"]],
            "freeze speakable is not a Learn line",
        )

        junk = maybe_write_card(
            session_id="s-junk",
            history=[
                {"role": "user", "content": "わからない"},
                {"role": "assistant", "content": "ごめん。"},
            ],
            learner_state="help_request",
            transcript="わからない",
            reply="ごめん。",
            path=cards_file,
        )
        _check(junk is not None, "junk help card writes")
        assert junk is not None
        _check(not is_practice_worthy(junk), "junk help is not practice-worthy")
        _check(newest_unused(path=cards_file) is None, "junk-only unused does not win today")
        gloss = build_card(
            session_id="s-gloss",
            signal="help_request",
            learner_line="眠い",
            tutor_reply="「眠い」は sleepy。",
            help_type="vocabulary",
        )
        append_card(gloss, path=cards_file)
        junk_only = today_payload(cards_path=cards_file)
        _check(junk_only.get("source") == "starter", "junk/gloss cards still use starters")
        junk_speak = [row.get("speakable") for row in junk_only["lines"]]
        _check("ごめん。" not in junk_speak, "gomen is not a Learn line")
        _check("「眠い」は sleepy。" not in junk_speak, "gloss is not a Learn line")

        recast = _write(
            cards_file,
            session_id="s-recast",
            line="コーヒーを好きです",
            speakable="コーヒーが好きです",
            ts="2026-08-15T10:00:00+00:00",
        )
        mixed = today_payload(cards_path=cards_file)
        _check(mixed.get("source") == "chat", "recast card is Learn-eligible")
        mixed_speak = [row.get("speakable") for row in mixed["lines"]]
        _check("コーヒーが好きです" in mixed_speak, "recast speakable is listed")
        _check(SPEAKABLE_ETTO not in mixed_speak, "freeze line skipped when recast exists")
        _check("ごめん。" not in mixed_speak, "junk gomen skipped when recast exists")
        picked = newest_unused(path=cards_file)
        _check(
            picked is not None and picked.get("id") == recast["id"],
            "recast-family wins newest_unused over junk",
        )
        _check(
            all("help_type" not in row and "signal" not in row for row in mixed["lines"]),
            "chat lines have no tags",
        )

        _write(
            cards_file,
            session_id="s-recast-2",
            line="猫を好きです",
            speakable="コーヒーが好きです",
            ts="2026-08-15T11:00:00+00:00",
        )
        duped = today_payload(cards_path=cards_file)
        coffee_rows = [
            row for row in duped["lines"] if row.get("speakable") == "コーヒーが好きです"
        ]
        _check(len(coffee_rows) == 1, "duplicate speakable is one row")
        _check(duped.get("source") == "chat", "clustered cards stay chat source")

        extra_ids = []
        for i in range(6):
            card = _write(
                cards_file,
                session_id=f"s-cap-{i}",
                line=f"miss {i}",
                speakable=f"線{i}です。",
                ts=f"2026-08-15T12:0{i}:00+00:00",
            )
            extra_ids.append(card["id"])
        capped = today_payload(cards_path=cards_file)
        _check(LINES_CAP == 5, "Learn cap is 5")
        _check(len(capped["lines"]) == LINES_CAP, "Learn list is capped at 5")
        _check(
            capped["lines"][0].get("speakable") == "コーヒーが好きです",
            "higher count ranks first",
        )

        used_state = Path(tmpdir) / "practice_state.json"
        used_state.write_text(
            json.dumps({"used_card_ids": [recast["id"]], "sitting": None}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        used_ok = today_payload(cards_path=cards_file)
        used_ids = {row.get("card_id") for row in used_ok["lines"]}
        _check(recast["id"] in used_ids or "コーヒーが好きです" in {
            row.get("speakable") for row in used_ok["lines"]
        }, "used Chat card is still Learn-eligible")

        finish_sitting(state_path_override=used_state)
        chosen = start_sitting(
            card_id=recast["id"],
            cards_path=cards_file,
            state_path_override=used_state,
        )
        _check(chosen.get("card_id") == recast["id"], "start_sitting uses chosen Chat card")
        again = start_sitting(
            card_id=STARTER_CARDS[1]["id"],
            cards_path=cards_file,
            state_path_override=used_state,
        )
        _check(again.get("card_id") == STARTER_CARDS[1]["id"], "Learn tap replaces in-progress sitting")
        finish_sitting(state_path_override=used_state)

        starter_sit = start_sitting(
            card_id=STARTER_CARDS[0]["id"],
            cards_path=cards_file,
            state_path_override=used_state,
        )
        _check(
            starter_sit.get("card_id") == STARTER_CARDS[0]["id"],
            "start_sitting uses Learn starter id",
        )
        finish_sitting(state_path_override=used_state, mark_used=True)
        used_json = json.loads(used_state.read_text(encoding="utf-8"))
        practiced = recent_practiced_lines(
            used_json.get("used_card_ids"),
            cards_path=cards_file,
        )
        _check(
            any(row.get("speakable") == STARTER_CARDS[0]["speakable"] for row in practiced),
            "finished Learn starter appears in Things you can say",
        )

        today = start_sitting(
            cards_path=cards_file,
            state_path_override=used_state,
        )
        _check(
            not str(today.get("card_id") or "").startswith("learn:"),
            "Practice Start without id is not a Learn starter",
        )
        _check(
            str(today.get("card_id") or "") != recast["id"],
            "Practice Start prefers unused over a used recast",
        )
        finish_sitting(state_path_override=used_state)

        try:
            start_sitting(
                card_id="missing-card",
                cards_path=cards_file,
                state_path_override=used_state,
            )
            _check(False, "unknown card_id raises")
        except LookupError:
            _check(True, "unknown card_id raises")

    _check(PROMPT_REVISION == 10, "Chat PROMPT_REVISION is 10")
    print("smoke_learn ok")


if __name__ == "__main__":
    main()

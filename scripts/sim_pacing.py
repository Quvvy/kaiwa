"""Simulate a learner taking the course, using the real planner and the real FSRS scheduler.

No network, no files. A virtual learner follows plan_today each day and recalls each
card with the probability FSRS gives it, so pacing changes can be judged before anyone
lives through them: how long a day really takes, how often a day is catch-up only, and
how far the course gets in N days.

    python scripts/sim_pacing.py [--days 120] [--skip 0.15] [--seed 1] [--weekly]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-sim-"))

from kaiwa.course import srs  # noqa: E402
from kaiwa.course import state as cs  # noqa: E402

# Seconds a real learner spends, roughly: answering plus reading the result.
SECONDS = {"kana": 6, "word": 7, "listen": 11, "speak": 18, "grammar": 25}
STEP_SECONDS = {"grammar": 240, "listen": 200, "speak": 200}
PHRASE_INTRO = 25
WORD_INTRO = 9
KANA_CHAR = 22
HARD_SHARE = 0.15   # right answers that come out Hard (slow, helped, close)
START = date(2027, 1, 4)


class Clock:
    now = datetime(2027, 1, 4, 18, 0, tzinfo=timezone.utc)


def run(days: int, skip: float, seed: int, quiet: bool = True) -> dict:
    rng = random.Random(seed)
    srs._now = lambda: Clock.now
    cs._today = lambda: Clock.now.date()
    state = cs._empty()
    log = []

    def answer(cid: str) -> bool:
        card = state["cards"].get(cid) or cs._new_card()
        kind = cs._card_kind(cid)
        fs = srs._card(card)
        r = srs.SCHEDULER.get_card_retrievability(fs, Clock.now) if card.get("reps") else 0.75
        right = rng.random() < max(0.0, r)
        hard = right and rng.random() < HARD_SHARE
        out = {"correct": right, "ms": None, "helped": hard, "guessed": False, "band": "", "fmt": f"{kind[0]}:{kind[2]}"}
        cs._apply_grade(state, cid, kind, out, None)
        cost = SECONDS.get(kind[0] if kind[0] != "phrase" else kind[2], 8)
        Clock.now += timedelta(seconds=cost)
        return right

    for d in range(days):
        Clock.now = datetime.combine(START + timedelta(days=d), datetime.min.time(), timezone.utc) + timedelta(hours=18)
        started = Clock.now
        entry = {"day": d, "studied": False, "catch_up": False, "new": 0, "reviews": 0, "minutes": 0.0, "due": 0}
        if rng.random() < skip:
            log.append(entry)
            continue
        entry["studied"] = True
        before = len(state["cards"])
        plan = cs.plan_today(state)
        entry["catch_up"] = plan["catching_up"]
        entry["due"] = len(cs.due_cards(state, limit=100_000))
        for step in plan["plan"]:
            unit = cs.next_unit(state)
            if step == "review":
                for c in cs.todays_reviews(state):
                    entry["reviews"] += 1
                    if not answer(c["card_id"]):
                        Clock.now += timedelta(minutes=2)
                        answer(c["card_id"])
            elif step == "kana":
                lesson = cs.next_kana_lesson(state)
                Clock.now += timedelta(seconds=KANA_CHAR * len(lesson["kana"]) + 60)
                state["kana"].setdefault(lesson["id"], cs._today().isoformat())
                for ch, _ in lesson["kana"]:
                    state["cards"].setdefault(f"kana.{ch}:read", cs._new_card())
            elif step == "recap":
                continue  # below, after everything new
            else:
                row = state["units"].setdefault(unit["id"], {})
                row[step] = True
                row[f"{step}_on"] = cs._today().isoformat()
                if step == "learn":
                    Clock.now += timedelta(seconds=PHRASE_INTRO * len(unit["phrases"]))
                    for p in unit["phrases"]:
                        for skill in cs.SKILLS:
                            state["cards"].setdefault(f"{p['id']}:{skill}", cs._new_card())
                elif step == "words":
                    Clock.now += timedelta(seconds=WORD_INTRO * len(unit.get("words", [])))
                    for w in unit.get("words", []):
                        state["cards"].setdefault(f"{w['id']}:mean", cs._new_card())
                else:
                    Clock.now += timedelta(seconds=STEP_SECONDS.get(step, 120))
                if cs.unit_done(state, unit):
                    row.setdefault("done_at", Clock.now.isoformat())
        Clock.now += timedelta(minutes=2)
        for c in cs.recap_cards(state):
            answer(c["card_id"])
        cs._mark_day(state)
        entry["new"] = len(state["cards"]) - before
        entry["minutes"] = (Clock.now - started).total_seconds() / 60
        log.append(entry)

    studied = [e for e in log if e["studied"]]
    ok = [r for r in state["log"]]
    return {
        "log": log,
        "units": sum(1 for u in cs.UNITS if cs.unit_done(state, u)),
        "kana": len(state["kana"]),
        "cards": len(state["cards"]),
        "retention": round(100 * sum(1 for r in ok if r["ok"]) / max(1, len(ok))),
        "avg_min": round(mean(e["minutes"] for e in studied), 1),
        "p90_min": round(sorted(e["minutes"] for e in studied)[int(len(studied) * 0.9)], 1),
        "catch_up_days": sum(1 for e in log if e["catch_up"]),
        "studied": len(studied),
        "due_end": log[-1]["due"] if log else 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--skip", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--weekly", action="store_true")
    args = ap.parse_args()
    r = run(args.days, args.skip, args.seed)
    print(f"{args.days} days, {args.skip:.0%} skipped: units {r['units']}/20, kana lessons {r['kana']}, cards {r['cards']}, "
          f"recall in reviews {r['retention']}%")
    print(f"studied {r['studied']} days: avg {r['avg_min']} min, 90th pct {r['p90_min']} min, "
          f"catch-up days {r['catch_up_days']}, due at the end {r['due_end']}")
    if args.weekly:
        for w in range(0, args.days, 7):
            part = r["log"][w:w + 7]
            st = [e for e in part if e["studied"]]
            if st:
                print(f"week {w // 7 + 1:2d}: {mean(e['minutes'] for e in st):5.1f} min/day  new {sum(e['new'] for e in part):3d}  "
                      f"reviews {sum(e['reviews'] for e in part):3d}  catch-up {sum(e['catch_up'] for e in part)}  due {part[-1]['due']}")


if __name__ == "__main__":
    main()

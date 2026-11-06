"""Simulate a learner taking the course, using the real planner and the real FSRS scheduler.

No network, no files. A virtual learner follows plan_today through the day as the app
does, working it out again after every step, and recalls each card with the probability
FSRS gives it. It shows what the plan does: how long a day takes, how often a day is
catch-up only, and how far the course gets in N days.

What it can't show is whether a pace is too fast. Forgetting follows FSRS exactly, nothing
models overload, and the seconds per card and per lesson are guesses nobody has timed.
Real recall and session lengths outrank anything printed here.

    python scripts/sim_pacing.py [--days 120] [--skip 0.15] [--seed 1] [--weekly] [--seeds 5] [--forget 0.7]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-sim-"))

from kaiwa.course import srs  # noqa: E402
from kaiwa.course import state as cs  # noqa: E402

# Rough guesses, nobody has timed these: a lesson's introduction, including its first answers.
STEP_SECONDS = {"grammar": 330, "listen": 200, "speak": 200}
PHRASE_INTRO = 25
WORD_INTRO = 9
KANA_CHAR = 22
FIRST_ANSWER = 0.85  # right on a card's first answer, straight after being taught it
HARD_SHARE = 0.15   # right answers that come out Hard (slow, helped, close)
REPEATS = 2         # a card due again within minutes comes back this many times in a sitting, as in course.js
START = date(2027, 1, 4)


class Clock:
    now = datetime(2027, 1, 4, 18, 0, tzinfo=timezone.utc)


def run(days: int, skip: float, seed: int, pace: str = cs.DEFAULT_PACE, forget: float = 1.0) -> dict:
    """`forget` below 1 is a learner who forgets faster than FSRS predicts: recall r becomes r^(1/forget)."""
    rng = random.Random(seed)
    srs._now = lambda: Clock.now
    state = cs._empty()
    state["pace"] = pace
    cs._with_state = lambda fn, path=None: fn(state)  # the real step functions, on this learner, in memory
    log = []

    def answer(cid: str, timed: bool = True) -> dict:
        card = state["cards"].get(cid) or cs._new_card()
        kind = cs._card_kind(cid)
        r = srs.SCHEDULER.get_card_retrievability(srs._card(card), Clock.now) if card.get("reps") else FIRST_ANSWER
        right = rng.random() < max(0.0, r) ** (1 / forget)
        hard = right and rng.random() < HARD_SHARE
        out = {"correct": right, "ms": None, "helped": hard, "guessed": False, "band": "", "fmt": f"{kind[0]}:{kind[2]}"}
        result = cs._apply_grade(state, cid, kind, out, None)
        if timed:
            Clock.now += timedelta(seconds=cs.REVIEW_SECONDS.get(kind[0] if kind[0] != "phrase" else kind[2], 8))
        return result

    def sitting(cards: list[dict]) -> int:
        """Like runReview in course.js: a card due again within minutes comes back a few cards later."""
        queue = [(c["card_id"], 0) for c in cards]
        i = 0
        while i < len(queue):
            cid, repeat = queue[i]
            if answer(cid)["again_soon"] and repeat < REPEATS:
                queue.insert(min(len(queue), i + 5), (cid, repeat + 1))
            i += 1
        return i

    def lesson(step: str, words_today: int) -> None:
        """One lesson step and its first answers, which its introduction time already covers."""
        unit = cs.next_unit(state)
        if step == "kana":
            chars = cs.next_kana_lesson(state)
            Clock.now += timedelta(seconds=KANA_CHAR * len(chars["kana"]) + 60)
            cs.complete_kana(chars["id"])
            for ch, _ in chars["kana"]:
                answer(f"kana.{ch}:read", timed=False)
        elif step == "learn":
            Clock.now += timedelta(seconds=PHRASE_INTRO * len(unit["phrases"]))
            cs.complete_step(unit["id"], "learn")
            for p in unit["phrases"]:
                for skill in cs.SKILLS:
                    answer(f"{p['id']}:{skill}", timed=False)
        elif step == "words":
            seen = int(state["units"].get(unit["id"], {}).get("words_seen") or 0)
            batch = unit["words"][seen:seen + words_today]
            Clock.now += timedelta(seconds=WORD_INTRO * len(batch))
            cs.complete_step(unit["id"], "words", count=words_today)
            for w in batch:
                answer(f"{w['id']}:mean", timed=False)
        else:
            Clock.now += timedelta(seconds=STEP_SECONDS.get(step, 120))
            cs.complete_step(unit["id"], step)
            if step == "grammar":
                for g in unit.get("grammar", []):
                    if g["id"] in cs._GRAMMAR:
                        answer(f"{g['id']}:build", timed=False)

    for d in range(days):
        Clock.now = datetime.combine(START + timedelta(days=d), datetime.min.time(), timezone.utc) + timedelta(hours=18)
        started = Clock.now
        entry = {"day": d, "studied": False, "catch_up": False, "new": 0, "reviews": 0, "minutes": 0.0, "due": 0, "promised": 0, "slipping": False, "steps": []}
        if rng.random() < skip:
            log.append(entry)
            continue
        entry["studied"] = True
        before = len(state["cards"])
        first = cs.plan_today(state)
        entry.update(catch_up=first["catching_up"], promised=first["minutes"], slipping=first["slipping"] is not None,
                     due=len(cs.due_cards(state, limit=100_000)))
        # The app works the plan out again after every step, and so does this.
        plan = first
        left_after_recap: int | None = None
        skip_step = ""
        for _ in range(60):
            steps = [s for s in plan["plan"] if s != skip_step]
            if left_after_recap is not None and len(cs.recap_cards(state)) <= left_after_recap:
                steps = [s for s in steps if s != "recap"]  # see recapSettled in course.js
            if not steps:
                break
            step = steps[0]
            skip_step = ""
            if step == "review":
                entry["reviews"] += sitting(cs.todays_reviews(state))
                skip_step = "review"
            elif step == "recap":
                sitting(cs.recap_cards(state))
                left_after_recap = len(cs.recap_cards(state))
                skip_step = "recap"
            else:
                entry["steps"].append(step)
                lesson(step, plan["words_today"])
            plan = cs.plan_today(state)
        entry["new"] = len(state["cards"]) - before
        entry["words"] = sum(1 for w in cs._WORDS if f"{w}:mean" in state["cards"])
        entry["minutes"] = (Clock.now - started).total_seconds() / 60
        log.append(entry)

    studied = [e for e in log if e["studied"]]
    # While lessons are still coming: the number a pace's label has to be honest about.
    last_new = max((i for i, e in enumerate(log) if e["new"]), default=0)
    active = [e for e in log[:last_new + 1] if e["studied"]] or [{"minutes": 0.0, "promised": 1, "steps": [], "slipping": False, "catch_up": False}]
    ok = [r for r in state["log"]]
    minutes = sorted(e["minutes"] for e in active)
    return {
        "log": log,
        "units": sum(1 for u in cs.UNITS if cs.unit_done(state, u)),
        "kana": len(state["kana"]),
        "cards": len(state["cards"]),
        "retention": round(100 * sum(1 for r in ok if r["ok"]) / max(1, len(ok))),
        "avg_min": round(mean(e["minutes"] for e in studied), 1),
        "active_min": round(mean(minutes), 1),
        "active_p90": round(minutes[int(len(minutes) * 0.9)], 1),
        "active_days": last_new + 1,
        "active_studied": len(active),
        "reviews_only": sum(1 for e in active if not e["steps"]),
        "slipping_days": sum(1 for e in active if e["slipping"]),
        "hours": round(sum(minutes) / 60, 1),
        "vs_promised": round(sum(minutes) / max(1, sum(e["promised"] for e in active)), 2),
        "words_30": next((e.get("words", 0) for e in reversed(log[:30]) if e["studied"]), 0),
        "reviews": sum(e["reviews"] for e in log),
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
    ap.add_argument("--pace", default=cs.DEFAULT_PACE, choices=sorted(cs.PACES))
    ap.add_argument("--seeds", type=int, default=0, help="print medians over this many seeds, for setting the labels")
    ap.add_argument("--forget", type=float, default=1.0, help="below 1: forgets faster than FSRS predicts")
    args = ap.parse_args()
    if args.seeds:
        runs = [run(args.days, args.skip, s, args.pace, args.forget) for s in range(1, args.seeds + 1)]
        keys = ("active_days", "active_min", "active_p90", "reviews_only", "active_studied", "words_30", "retention", "slipping_days", "hours", "vs_promised", "reviews")
        print(args.pace, {k: median(r[k] for r in runs) for k in keys})
        return
    r = run(args.days, args.skip, args.seed, args.pace, args.forget)
    print(f"{args.pace}, {args.days} days, {args.skip:.0%} skipped: units {r['units']}/20, kana lessons {r['kana']}, cards {r['cards']}, "
          f"recall in reviews {r['retention']}%")
    print(f"while lessons last ({r['active_days']} days): {r['active_min']} min a day, {r['reviews_only']} of {r['active_studied']} studied days reviews only")
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

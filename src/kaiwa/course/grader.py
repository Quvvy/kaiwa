"""Tune the automatic grader to the learner's own sense of Hard / Good / Easy.

Every graded answer leaves a row: how long it took compared with the learner's
usual time for that answer format (`ratio`), which signals were present
(close / helped), what Kaiwa picked (`auto`) and the grade that stuck
(`final`: the learner's change if they made one, otherwise Kaiwa's pick, which
counts as agreement).

From those rows we fit, per answer format when there's enough data and for all
formats together otherwise:
  hard  answers slower than hard × usual are Hard
  easy  answers faster than easy × usual are Easy (cards with a track record)
and whether a "close" speech check or needing help should still mean Hard.

Guard rails: nothing changes until there are MIN_ROWS usable answers including
MIN_CORRECTIONS changes; small samples are pulled toward the defaults; the
thresholds stay within sensible bounds.
"""

from __future__ import annotations

from typing import Any

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4

DEFAULT = {"hard": 2.0, "easy": 0.6, "close": HARD, "helped": HARD}
HARD_RANGE = (1.3, 3.5)
EASY_RANGE = (0.3, 0.85)
MIN_ROWS = 30
MIN_CORRECTIONS = 5
FORMAT_MIN_ROWS = 40
SIGNAL_MIN_ROWS = 5
SIGNAL_SWITCH = 0.7      # share of "close"/"helped" answers kept at Good before it stops meaning Hard
PRIOR_WEIGHT = 20        # pseudo-answers at the default, so a few rows can't swing a threshold far
ROWS_KEPT = 1500


def _grid(lo: float, hi: float, step: float) -> list[float]:
    out, x = [], lo
    while x <= hi + 1e-9:
        out.append(round(x, 2))
        x += step
    return out


HARD_GRID = _grid(*HARD_RANGE, 0.1)
EASY_GRID = _grid(*EASY_RANGE, 0.05)


def _speed_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Right, unhelped, unguessed answers with a speed ratio: the ones speed decides."""
    return [r for r in rows if r.get("ratio") and r.get("correct") and not r.get("close")
            and not r.get("helped") and not r.get("guessed") and r.get("final") in (HARD, GOOD, EASY)]


def _fit(rows: list[dict[str, Any]], key: str, grid: list[float], default: float) -> float:
    """Threshold that best reproduces the final grades, pulled toward the default by a prior."""
    if key == "hard":
        def miss(t: float) -> float:
            return sum(1 for r in rows if (r["ratio"] > t) != (r["final"] == HARD))
    else:
        rows = [r for r in rows if r.get("seasoned")]  # Easy needs a track record anyway

        def miss(t: float) -> float:
            return sum(1 for r in rows if (r["ratio"] < t) != (r["final"] == EASY))
    if not rows:
        return default
    best = min(grid, key=lambda t: (miss(t), abs(t - default)))
    n = len(rows)
    return round((best * n + default * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT), 2)


def _signal(rows: list[dict[str, Any]], flag: str) -> int:
    part = [r for r in rows if r.get(flag) and r.get("correct") and not r.get("guessed")]
    if len(part) < SIGNAL_MIN_ROWS:
        return DEFAULT[flag]
    kept_good = sum(1 for r in part if r.get("final") in (GOOD, EASY)) / len(part)
    return GOOD if kept_good >= SIGNAL_SWITCH else HARD


def tune(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fitted grader settings from the answer log (defaults until there's enough evidence)."""
    corrections = sum(1 for r in rows if r.get("final") != r.get("auto"))
    usable = _speed_rows(rows)
    params: dict[str, Any] = {**DEFAULT, "formats": {}, "rows": len(rows), "corrections": corrections, "tuned": False}
    if len(rows) < MIN_ROWS or corrections < MIN_CORRECTIONS:
        return params
    params["tuned"] = True
    params["hard"] = _fit(usable, "hard", HARD_GRID, DEFAULT["hard"])
    params["easy"] = _fit(usable, "easy", EASY_GRID, DEFAULT["easy"])
    params["close"] = _signal(rows, "close")
    params["helped"] = _signal(rows, "helped")
    by_fmt: dict[str, list[dict[str, Any]]] = {}
    for r in usable:
        by_fmt.setdefault(str(r.get("fmt")), []).append(r)
    for fmt, part in by_fmt.items():
        if len(part) >= FORMAT_MIN_ROWS:
            # Per-format fits start from the overall fit, not the defaults.
            params["formats"][fmt] = {
                "hard": _fit(part, "hard", HARD_GRID, params["hard"]),
                "easy": _fit(part, "easy", EASY_GRID, params["easy"]),
            }
    return params


def for_format(params: dict[str, Any] | None, fmt: str) -> dict[str, Any]:
    """The settings rating_for should use for one answer format."""
    params = params or DEFAULT
    own = (params.get("formats") or {}).get(fmt, {})
    return {
        "hard_ratio": own.get("hard", params.get("hard", DEFAULT["hard"])),
        "easy_ratio": own.get("easy", params.get("easy", DEFAULT["easy"])),
        "close_grade": params.get("close", DEFAULT["close"]),
        "helped_grade": params.get("helped", DEFAULT["helped"]),
    }


def describe(params: dict[str, Any] | None) -> dict[str, Any]:
    """Plain-language summary for the stats page."""
    p = params or {**DEFAULT, "tuned": False, "rows": 0, "corrections": 0, "formats": {}}
    lines = [
        f"Hard when you take more than {p['hard']:g}× your usual time.",
        f"Easy when you answer in under {p['easy']:g}× your usual time, on a card you've got right a few times.",
        "A \"close\" spoken answer counts as " + ("Good." if p.get("close") == GOOD else "Hard."),
        "Needing help (like revealing the text) counts as " + ("Good." if p.get("helped") == GOOD else "Hard."),
    ]
    if p.get("tuned"):
        basis = f"Tuned from {p['rows']} answers, including your {p['corrections']} grade changes."
    else:
        need = []
        changes = max(0, MIN_CORRECTIONS - int(p.get("corrections") or 0))
        answers = max(0, MIN_ROWS - int(p.get("rows") or 0))
        if changes:
            need.append(f"{changes} more grade change{'s' if changes != 1 else ''}")
        if answers:
            need.append(f"{answers} more answer{'s' if answers != 1 else ''}")
        basis = "Default settings. They start adjusting to you after " + " and ".join(need) + "."
    return {"lines": lines, "basis": basis, "tuned": bool(p.get("tuned"))}

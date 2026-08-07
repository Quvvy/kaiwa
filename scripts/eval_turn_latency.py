from __future__ import annotations

"""Summarize recent /api/turn timing from session logs (realtime evaluation helper)."""

import json
import sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.config import get_settings


def main() -> None:
    settings = get_settings()
    sessions = settings.sessions_dir
    if not sessions.exists():
        print(f"No sessions dir at {sessions}")
        raise SystemExit(1)

    samples: list[dict] = []
    for path in sorted(sessions.glob("*.jsonl"))[-20:]:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("mode") != "chat":
                continue
            timing = row.get("timing")
            if isinstance(timing, dict) and timing.get("total_ms") is not None:
                samples.append(timing)

    if not samples:
        print("No chat turns with timing yet.")
        print("Have a chat turn on the restarted server, then re-run this script.")
        print("Decision default without samples: stay turn-based (see docs/DECISIONS.md).")
        raise SystemExit(0)

    totals = [int(s["total_ms"]) for s in samples]
    stt = [int(s.get("stt_ms", 0)) for s in samples]
    llm = [int(s.get("llm_ms", 0)) for s in samples]
    tts_ms = [int(s.get("tts_ms", 0)) for s in samples]
    print(f"samples={len(samples)}")
    print(f"total_ms  mean={mean(totals):.0f} median={median(totals):.0f} min={min(totals)} max={max(totals)}")
    print(f"stt_ms    mean={mean(stt):.0f} median={median(stt):.0f}")
    print(f"llm_ms    mean={mean(llm):.0f} median={median(llm):.0f}")
    print(f"tts_ms    mean={mean(tts_ms):.0f} median={median(tts_ms):.0f}")
    print()
    print("Guideline: turn-based ~1.5–4s is fine for practice; OpenAI Realtime is costly.")
    if median(totals) < 5000:
        print("Outcome: stay turn-based — latency is acceptable for Kaiwa’s practice loop.")
    else:
        print("Outcome: still prefer turn-based unless latency feels bad in daily use; revisit Realtime only then.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.config import get_settings
from kaiwa import stt


def main() -> None:
    settings = get_settings()
    sample = ROOT / "recordings" / "smoke_stt.wav"
    sample.parent.mkdir(parents=True, exist_ok=True)

    # Generate 1s of soft noise if no sample exists — Whisper should return empty/near-empty.
    # Prefer replacing this file with a real Japanese recording for a meaningful check.
    if not sample.exists():
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        # Simple tone; not speech — use for pipeline wiring. Real JP clip recommended.
        tone = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        stt.write_wav_mono(sample, tone, sr)
        print(f"wrote placeholder wav: {sample}")
        print("Replace with a Japanese speech recording for a real accuracy check.")

    print(
        f"model={settings.whisper_model} device={settings.whisper_device} "
        f"compute={settings.whisper_compute_type}"
    )
    print(f"transcribing {sample} ...")
    text = stt.transcribe_file(settings, sample)
    print("--- transcript ---")
    print(text if text else "(empty)")


if __name__ == "__main__":
    main()

"""Chat speech: which pass's text is kept, with Whisper's answers scripted. No model needed."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa import stt  # noqa: E402


def _check(ok: bool, label: str) -> None:
    sys.stdout.buffer.write((("ok    " if ok else "FAIL  ") + label + "\n").encode("utf-8"))
    sys.stdout.flush()
    if not ok:
        raise SystemExit(f"smoke_chat_stt failed: {label}")


def _run(auto, lang, prob, forced=("", -0.5), only_japanese="", confidence=-0.5):
    """Transcribe with scripted (text, confidence) answers for each pass."""

    def segment(text, logprob):
        return SimpleNamespace(text=text, tokens=[1, 2], avg_logprob=logprob)

    def fake(_model, _path, kwargs):
        if "suppress_tokens" in kwargs:
            seg = segment(only_japanese, -0.5)
        elif kwargs.get("language") == "ja":
            seg = segment(*forced)
        else:
            seg = segment(auto, confidence)
        return [seg], SimpleNamespace(language=lang, language_probability=prob)

    stt.get_model = lambda _settings: object()
    stt._transcribe = fake
    stt._foreign_token_ids = lambda _model: [1, 2]
    return stt.transcribe_chat_file(None, "clip.webm")


# Each line is a real clip's shape: what Whisper said, how sure, and what should be kept.
CASES = [
    # Real English
    ("sentence", ("Can you speak more slowly, please?", "en", 1.0, ("Can you speak", -0.5), "", -0.18), "Can you speak more slowly, please?", 1),
    ("I don't know", ("I don't know.", "en", 1.0, ("I don't know", -0.5), "", -0.25), "I don't know.", 1),
    ("Yes: the Japanese pass still writes English", ("Yes.", "en", 0.93, ("YES", -0.74), "", -0.68), "Yes.", 2),
    ("Okay: same, though that pass scored higher", ("Okay.", "en", 0.96, ("OK", -0.70), "", -0.72), "Okay.", 2),
    ("Thanks: the Japanese pass fits worse", ("Thanks.", "en", 0.98, ("デイ", -1.37), "", -0.72), "Thanks.", 2),
    # Japanese that Whisper took for English
    ("ゆっくり", ("You could eat on your screen.", "en", 0.83, ("ユクディオンイルス", -0.93), "", -0.68), "ユクディオンイルス", 2),
    ("「dog」は…", ("Dog wa nihongo de nan desu ka?", "en", 0.92, ("ダーグは日本語でなんですか?", -0.47), "", -0.52), "ダーグは日本語でなんですか?", 2),
    ("げんきです", ("Thank you this", "en", 0.53, ("けんきです", -0.61), "", -0.50), "けんきです", 2),
    # Other languages
    ("clear Japanese", ("すみません お元気ですか", "ja", 0.9), "すみません お元気ですか", 1),
    ("Japanese mis-tagged as Korean", ("もう一度お願いします。", "ko", 0.4), "もう一度お願いします。", 1),
    ("mixed alphabets", ("Mmm, genkigです.", "no", 0.4, ("えー、元気です。", -0.5)), "えー、元気です。", 2),
    ("wrong language", ("Og gengirðu, ska?", "is", 0.5, ("おげんきですか", -0.5)), "おげんきですか", 2),
    ("a Japanese pass in another alphabet", ("Og gengirðu, ska?", "is", 0.5, ("Og gengirðu, ska?", -0.5), "おげんきですか"), "おげんきですか", 3),
]
for label, args, want, passes in CASES:
    text, meta = _run(*args)
    _check(text == want and meta["passes"] == passes, f"{label} → {text} ({meta['passes']} passes)")
print("smoke_chat_stt ok")

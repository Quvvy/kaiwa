"""Second opinion on say-it-back attempts from a character-level kana model.

Whisper predicts the most likely *sentence*, so it quietly turns おはよございます
back into おはようございます and hears いや for a learner's いえ. A CTC model that
outputs one hiragana per sound has no such pull. It is too noisy to transcribe
on its own, but it is good at a narrower question: which of a few given kana
strings fits this audio best? We ask it to choose between the target, what
Whisper heard, and the target with one typical beginner slip applied.

Model: vumichien/wav2vec2-large-xlsr-japanese-hiragana, exported to ONNX and
int8-quantized (scripts/export_kana_model.py). Optional: without it, Kaiwa
falls back to the Whisper-only check.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_log = logging.getLogger("kaiwa.course.kana_judge")

# A rival must beat the target by this much (CTC cost, nats) before we believe it.
MARGIN = 5.0

_lock = threading.Lock()
_session = None
_vocab: dict[str, int] = {}
_blank = 0
_normalize = True
_failed = False


def model_dir() -> Path:
    from kaiwa.secrets_store import user_data_dir

    return user_data_dir() / "models" / "kana-ctc"


def available() -> bool:
    d = model_dir()
    return (d / "model.onnx").is_file() and (d / "vocab.json").is_file()


def _load() -> bool:
    global _session, _vocab, _blank, _normalize, _failed
    if _session is not None:
        return True
    if _failed or not available():
        return False
    with _lock:
        if _session is not None:
            return True
        try:
            import onnxruntime as ort

            meta = json.loads((model_dir() / "vocab.json").read_text(encoding="utf-8"))
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 8
            _session = ort.InferenceSession(
                str(model_dir() / "model.onnx"), opts, providers=["CPUExecutionProvider"]
            )
            _vocab = meta["vocab"]
            _blank = int(meta["blank"])
            _normalize = bool(meta.get("normalize", True))
        except Exception as exc:
            _failed = True
            _log.warning("kana model unavailable: %s", exc)
            return False
    return True


def warm() -> None:
    """Load the model and run it once so the first real check isn't slow."""
    if _load():
        try:
            _log_probs(np.zeros(16000, dtype=np.float32))
        except Exception:
            pass


def _log_probs(audio: np.ndarray) -> np.ndarray:
    x = audio.astype(np.float32)
    if _normalize:
        x = (x - x.mean()) / np.sqrt(x.var() + 1e-7)
    logits = _session.run(None, {"audio": x[None, :]})[0][0]
    m = logits.max(axis=-1, keepdims=True)
    return logits - m - np.log(np.exp(logits - m).sum(axis=-1, keepdims=True))


def _ctc_cost(logp: np.ndarray, ids: list[int]) -> float:
    """Negative log-likelihood of `ids` under CTC (standard forward pass)."""
    t_len = logp.shape[0]
    ext = [_blank]
    for i in ids:
        ext += [i, _blank]
    s_len = len(ext)
    if not ids or t_len < len(ids):
        return float("inf")
    neg = -np.inf
    alpha = np.full(s_len, neg)
    alpha[0] = logp[0, ext[0]]
    alpha[1] = logp[0, ext[1]]
    ext_a = np.array(ext)
    # Positions where a skip (s-2 → s) is allowed: non-blank, differs from s-2.
    skip = np.zeros(s_len, dtype=bool)
    skip[2:] = (ext_a[2:] != _blank) & (ext_a[2:] != ext_a[:-2])
    for t in range(1, t_len):
        prev1 = np.concatenate(([neg], alpha[:-1]))
        prev2 = np.concatenate(([neg, neg], alpha[:-2]))
        prev2 = np.where(skip, prev2, neg)
        alpha = np.logaddexp(np.logaddexp(alpha, prev1), prev2) + logp[t, ext_a]
    return float(-np.logaddexp(alpha[-1], alpha[-2]))


# ---------- typical slips ----------

_O_ROW = set("おこごそぞとどのほぼぽもよろょ")
_U_ROW = set("うくぐすずつづぬふぶぷむゆるゅ")
_E_ROW = set("えけげせぜてでねへべぺめれ")
_SMALL_TO_BIG = {"ゃ": "や", "ゅ": "ゆ", "ょ": "よ"}


def slips(target: str) -> list[tuple[str, str]]:
    """(variant, tip) for one typical beginner slip at a time."""
    out: list[tuple[str, str]] = []
    for i, ch in enumerate(target):
        prev = target[i - 1] if i else ""
        nxt = target[i + 1] if i + 1 < len(target) else ""
        cut = target[:i] + target[i + 1:]
        if ch == "っ":
            out.append((cut, f"Pause on the small っ: {target[max(0, i - 1):i + 2]} has a tiny stop before {nxt}."))
        elif ch == "ん":
            out.append((cut, f"Don't drop the ん in {target[max(0, i - 1):i + 2]}: it's a full beat of its own."))
        elif ch == "う" and (prev in _O_ROW or prev in _U_ROW):
            out.append((cut, f"Stretch the vowel in {prev}う: hold it for two beats."))
        elif ch == "い" and prev in _E_ROW:
            out.append((cut, f"Stretch the vowel in {prev}い: hold it for two beats."))
        elif prev and ch == prev and ch in "あいうえお":
            out.append((cut, f"Hold the {ch} longer: {prev}{ch} is two beats, not one."))
        elif ch in _SMALL_TO_BIG and prev:
            big = target[:i] + _SMALL_TO_BIG[ch] + target[i + 1:]
            out.append((big, f"{prev}{ch} is one sound blended together, not {prev}-{_SMALL_TO_BIG[ch]}."))
    seen: set[str] = set()
    return [(v, tip) for v, tip in out if v and not (v in seen or seen.add(v))]


@dataclass(frozen=True)
class Verdict:
    band: str  # good | close | heard (Whisper's different hearing fits better)
    sounded_like: str  # kana that fit best
    tip: str


def judge(audio: np.ndarray, targets_kana: list[str], heard_kana: str, rivals_kana: tuple[str, ...] = ()) -> Verdict | None:
    """Pick the band from the audio itself. None when the model isn't available.

    `targets_kana[0]` is the phrase; the rest are accepted variants (おはよう for
    おはようございます), which count as correct too. `rivals_kana` are extra
    wrong answers to compete against (other kana, for a single-kana target).
    """
    if not _load():
        return None
    targets = [t for t in ("".join(c for c in x if c in _vocab) for x in targets_kana) if t]
    if not targets or audio.size < 1600:
        return None
    logp = _log_probs(audio)

    def cost(text: str) -> float:
        return _ctc_cost(logp, [_vocab[c] for c in text if c in _vocab])

    target_cost, target = min((cost(t), t) for t in dict.fromkeys(targets))
    rivals: list[tuple[float, str, str]] = []
    for variant, tip in slips(targets[0]):
        if variant not in targets:
            rivals.append((cost(variant), variant, tip))
    heard = "".join(c for c in heard_kana if c in _vocab)
    if heard and heard not in targets and heard not in {r[1] for r in rivals}:
        rivals.append((cost(heard), heard, ""))
    for rival in rivals_kana:
        rival = "".join(c for c in rival if c in _vocab)
        if rival and rival not in targets and rival not in {r[1] for r in rivals}:
            rivals.append((cost(rival), rival, ""))
    if not rivals:
        return Verdict("good", target, "")
    best_cost, best, tip = min(rivals)
    if best_cost > target_cost - MARGIN:
        return Verdict("good", target, "")
    if tip:
        return Verdict("close", best, tip)
    return Verdict("heard", best, "")

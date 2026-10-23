"""State-file safety: atomic writes, corrupt-file quarantine, sidework races. No network."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_DATA = Path(tempfile.mkdtemp(prefix="kaiwa-state-smoke-"))
os.environ["KAIWA_DATA_DIR"] = str(_DATA)
os.environ["DEEPSEEK_API_KEY"] = "sk-smoke-not-real"

from kaiwa import jsonio, llm, profiles  # noqa: E402
from kaiwa import learner_memory, learner_profile  # noqa: E402
from kaiwa.learner_memory import load_memory, note_chat_turn, save_memory  # noqa: E402
from kaiwa.learner_profile import default_profile, load_profile, save_profile  # noqa: E402


def _check(ok: bool, label: str) -> None:
    status = "ok  " if ok else "FAIL"
    line = status + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if not ok:
        raise SystemExit(f"smoke_state_files failed: {label}")


def _atomic_roundtrip(tmp: Path) -> None:
    path = tmp / "a" / "state.json"
    jsonio.write_json_atomic(path, {"k": "眠い"})
    _check(jsonio.read_json_dict(path) == {"k": "眠い"}, "atomic write round-trips (creates parent)")
    _check("眠い" in path.read_text(encoding="utf-8"), "ensure_ascii=False keeps Japanese readable")
    leftovers = [p.name for p in path.parent.iterdir() if p.name.endswith(".tmp")]
    _check(not leftovers, "no temp files left behind")
    _check(jsonio.read_json_dict(tmp / "missing.json") is None, "missing file → None")


def _quarantine(tmp: Path) -> None:
    path = tmp / "learner_profile.json"
    path.write_text('{"speaking_level": "n5", "placement_comp', encoding="utf-8")
    profile = load_profile(path)
    _check(profile.to_dict() == default_profile().to_dict() | {"updated_at": profile.updated_at},
           "torn profile loads as default")
    moved = list(tmp.glob("learner_profile.json.corrupt-*"))
    _check(len(moved) == 1 and not path.exists(), "torn file moved aside, not left in place")
    save_profile(profile, path)
    _check("placement_comp" in moved[0].read_text(encoding="utf-8"),
           "saving defaults afterwards leaves the quarantined copy intact")

    arr = tmp / "list.json"
    arr.write_text("[1, 2]", encoding="utf-8")
    _check(jsonio.read_json_dict(arr) is None and list(tmp.glob("list.json.corrupt-*")),
           "non-object JSON quarantined")


def _hammer(tmp: Path) -> None:
    path = tmp / "hammer_profile.json"
    seed = default_profile()
    seed.placement_completed = True
    save_profile(seed, path)
    errors: list[str] = []
    lost: list[int] = []

    def writer() -> None:
        for _ in range(150):
            try:
                p = load_profile(path)
                p.notes = "w"
                save_profile(p, path)
            except Exception as exc:  # noqa: BLE001
                errors.append(repr(exc))

    def reader() -> None:
        for i in range(300):
            try:
                if not load_profile(path).placement_completed:
                    lost.append(i)
            except Exception as exc:  # noqa: BLE001
                errors.append(repr(exc))

    threads = [threading.Thread(target=writer) for _ in range(3)]
    threads += [threading.Thread(target=reader) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    _check(not errors, f"concurrent load/save raised nothing ({errors[:2]})")
    _check(not lost, "readers never saw a reset profile under concurrent saves")
    _check(not list(tmp.glob("hammer_profile.json.corrupt-*")), "hammer never produced a corrupt file")


def _sidework_race() -> None:
    from kaiwa import app as kaiwa_app

    profile_file = profiles.learner_profile_path()
    memory_file = profiles.memory_path()
    save_profile(default_profile(), profile_file)
    save_memory(learner_memory.default_memory(), memory_file)

    # What a quiz finish / the next Chat turn does while sidework waits on the LLM.
    def finish_placement() -> None:
        p = load_profile(profile_file)
        p.placement_completed = True
        save_profile(p, profile_file)

    def count_turn() -> None:
        save_memory(note_chat_turn(load_memory(memory_file)), memory_file)

    def fake_completion(_settings, system, _messages, **_kw) -> str:
        count_turn()
        if system == learner_profile.ASSESS_SYSTEM:
            finish_placement()
            return '{"speaking_level": "n5", "topic_tags": ["cats"]}'
        return "{}"

    patches = [
        (llm, "_completion", fake_completion),
        (kaiwa_app, "should_assess", lambda *_a, **_k: True),
        (kaiwa_app, "should_extract", lambda *_a, **_k: True),
        (learner_profile, "should_assess", lambda *_a, **_k: True),
        (learner_memory, "should_extract", lambda *_a, **_k: True),
    ]
    saved = [(mod, name, getattr(mod, name, None)) for mod, name, _ in patches]
    for mod, name, value in patches:
        setattr(mod, name, value)
    try:
        before_turns = load_memory(memory_file).stats.chat_turns
        kaiwa_app._chat_sidework("猫が好き", "flowing", [{"role": "user", "content": "猫が好き"}])
    finally:
        for mod, name, value in saved:
            setattr(mod, name, value)

    profile = load_profile(profile_file)
    memory = load_memory(memory_file)
    _check(profile.placement_completed, "placement saved during the assess call survives sidework")
    _check(profile.speaking_level == "n5" and "cats" in profile.topic_tags, "assess result still merged")
    _check(memory.stats.chat_turns == before_turns + 2,
           "chat turns counted during both sidework calls survive")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="kaiwa-jsonio-") as raw:
        tmp = Path(raw)
        _atomic_roundtrip(tmp)
        _quarantine(tmp)
        _hammer(tmp)
    _sidework_race()
    print("smoke_state_files ok")


if __name__ == "__main__":
    main()

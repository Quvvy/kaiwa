"""First-run bootstrap: Whisper weights + AivisSpeech Engine (resume-safe)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from kaiwa.secrets_store import user_data_dir

ProgressFn = Callable[[dict[str, Any]], None]

DEFAULT_WHISPER_MODEL = "large-v3-turbo"
WHISPER_REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"

AIVIS_ENGINE_VERSION = "1.2.0"
AIVIS_ASSET = f"AivisSpeech-Engine-Windows-x64-{AIVIS_ENGINE_VERSION}.7z.001"
AIVIS_URL = (
    "https://github.com/Aivis-Project/AivisSpeech-Engine/releases/download/"
    f"{AIVIS_ENGINE_VERSION}/{AIVIS_ASSET}"
)

BOOTSTRAP_FILENAME = "bootstrap.json"


def models_dir() -> Path:
    return user_data_dir() / "models" / "whisper"


def whisper_model_dir(model_id: str = DEFAULT_WHISPER_MODEL) -> Path:
    safe = model_id.replace("/", "--")
    return models_dir() / safe


def downloads_dir() -> Path:
    return user_data_dir() / "downloads"


def aivis_install_root() -> Path:
    return user_data_dir() / "tts" / "aivisspeech"


def aivis_run_candidates_under_install() -> list[Path]:
    root = aivis_install_root()
    return [
        root / "engine" / "Windows-x64" / "run.exe",
        root / "Windows-x64" / "run.exe",
        root / "AivisSpeech-Engine" / "run.exe",
        root / "run.exe",
    ]


def aivis_appdata_run_exe() -> Path | None:
    for path in aivis_run_candidates_under_install():
        if path.is_file():
            return path
    return None


def recorded_aivis_path() -> Path | None:
    """Path saved by last successful bootstrap (`aivis_path` in bootstrap.json)."""
    raw = str(_load_state().get("aivis_path") or "").strip()
    if not raw:
        return None
    return Path(raw)


def bootstrap_state_path() -> Path:
    return user_data_dir() / BOOTSTRAP_FILENAME


def _emit(on_progress: ProgressFn | None, **payload: Any) -> None:
    row = {k: v for k, v in payload.items() if v is not None}
    if on_progress:
        on_progress(row)
    # CLI / desktop subprocess: one JSON object per line on stdout.
    print(json.dumps(row, ensure_ascii=False), flush=True)


def _load_state() -> dict[str, Any]:
    path = bootstrap_state_path()
    # Do not gate on path.is_file() — frozen Kaiwa.exe has been observed to get
    # false negatives from exists()/is_file() on AppData while open()/read works.
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def _save_state(patch: dict[str, Any]) -> None:
    path = bootstrap_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    state.update(patch)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def whisper_ready(model_id: str = DEFAULT_WHISPER_MODEL) -> bool:
    dest = whisper_model_dir(model_id)
    return (dest / "model.bin").is_file() and (dest / "config.json").is_file()


def _find_existing_aivis_elsewhere() -> Path | None:
    """Reuse desktop candidate list when available (Program Files / tools / …)."""
    try:
        from kaiwa.config import ROOT

        tool = ROOT / "tools" / "aivisspeech" / "engine" / "Windows-x64" / "run.exe"
        if tool.is_file():
            return tool
    except Exception:
        pass
    try:
        from kaiwa.desktop.services import find_engine

        found = find_engine("aivisspeech")
        if found is not None:
            return found
    except Exception:
        pass
    home = Path.home()
    for path in (
        home / "AppData/Local/Programs/AivisSpeech/AivisSpeech-Engine/run.exe",
        home / "AppData/Local/Programs/AivisSpeech/engine/run.exe",
        Path("C:/Program Files/AivisSpeech/AivisSpeech-Engine/run.exe"),
        Path("C:/Program Files/AivisSpeech/engine/run.exe"),
    ):
        if path.is_file():
            return path
    return None


def aivis_ready() -> bool:
    if aivis_appdata_run_exe() is not None:
        return True
    return _find_existing_aivis_elsewhere() is not None


def ensure_whisper(
    *,
    model_id: str = DEFAULT_WHISPER_MODEL,
    on_progress: ProgressFn | None = None,
) -> Path:
    dest = whisper_model_dir(model_id)
    if whisper_ready(model_id):
        _emit(
            on_progress,
            step="whisper",
            label="Speech model ready",
            pct=100,
            done=1,
            total=1,
        )
        return dest

    dest.mkdir(parents=True, exist_ok=True)
    _emit(
        on_progress,
        step="whisper",
        label="Downloading speech model...",
        pct=0,
        done=0,
        total=None,
    )

    from huggingface_hub import snapshot_download
    from tqdm.auto import tqdm

    class _ReportTqdm(tqdm):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["disable"] = False
            super().__init__(*args, **kwargs)

        def update(self, n: float | int = 1) -> bool | None:
            result = super().update(n)
            total = int(self.total or 0)
            done = int(self.n or 0)
            pct = int(min(100, (done * 100) // total)) if total else None
            _emit(
                on_progress,
                step="whisper",
                label="Downloading speech model...",
                done=done,
                total=total or None,
                pct=pct,
            )
            return result

    try:
        snapshot_download(
            repo_id=WHISPER_REPO if model_id in {"large-v3-turbo", "turbo"} else model_id,
            local_dir=str(dest),
            allow_patterns=[
                "config.json",
                "preprocessor_config.json",
                "model.bin",
                "tokenizer.json",
                "vocabulary.*",
            ],
            tqdm_class=_ReportTqdm,
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not download the speech model. Check your internet connection "
            "and free disk space (~2 GB), then close Kaiwa and relaunch to resume.\n"
            f"Detail: {exc}"
        ) from exc

    if not whisper_ready(model_id):
        raise RuntimeError(
            "Speech model download finished but files are incomplete. "
            "Close Kaiwa and relaunch to resume."
        )

    _save_state({"whisper_model": model_id, "whisper_ready": True})
    _emit(
        on_progress,
        step="whisper",
        label="Speech model ready",
        pct=100,
        done=1,
        total=1,
    )
    return dest


def _http_download(url: str, dest: Path, *, on_progress: ProgressFn | None, label: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    existing = partial.stat().st_size if partial.is_file() else 0
    headers: dict[str, str] = {}
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"

    try:
        with httpx.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=True,
            timeout=httpx.Timeout(60.0, read=300.0),
        ) as res:
            if res.status_code == 416:
                # Already complete according to server
                if partial.is_file():
                    partial.replace(dest)
                return
            if res.status_code not in (200, 206):
                raise RuntimeError(f"Download failed (HTTP {res.status_code})")

            total_header = res.headers.get("Content-Length")
            content_range = res.headers.get("Content-Range")
            total: int | None = None
            if content_range and "/" in content_range:
                try:
                    total = int(content_range.rsplit("/", 1)[-1])
                except ValueError:
                    total = None
            elif total_header and res.status_code == 200:
                try:
                    total = int(total_header)
                except ValueError:
                    total = None
            elif total_header and res.status_code == 206 and existing:
                try:
                    total = existing + int(total_header)
                except ValueError:
                    total = None

            mode = "ab" if res.status_code == 206 and existing else "wb"
            if mode == "wb" and partial.is_file():
                partial.unlink()
                existing = 0

            done = existing if mode == "ab" else 0
            with partial.open(mode) as out:
                for chunk in res.iter_bytes(1024 * 256):
                    out.write(chunk)
                    done += len(chunk)
                    pct = int(min(100, (done * 100) // total)) if total else None
                    _emit(
                        on_progress,
                        step="aivis",
                        label=label,
                        done=done,
                        total=total,
                        pct=pct,
                    )
        partial.replace(dest)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Could not download AivisSpeech Engine. Check your internet connection "
            "and free disk space, then close Kaiwa and relaunch to resume.\n"
            f"Detail: {exc}"
        ) from exc


def _extract_aivis_archive(archive: Path, dest_root: Path) -> Path:
    try:
        import py7zr
    except ImportError as exc:
        raise RuntimeError(
            "Missing py7zr (needed to install AivisSpeech). "
            "Reinstall Kaiwa runtime deps, then relaunch."
        ) from exc

    staging = dest_root.parent / (dest_root.name + "_extracting")
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    # Some tools expect a .7z suffix.
    open_path = archive
    alias: Path | None = None
    if archive.suffix == ".001":
        alias = archive.with_suffix("").with_suffix(".7z")
        if not alias.exists():
            try:
                os.link(archive, alias)
            except OSError:
                shutil.copy2(archive, alias)
        open_path = alias

    try:
        with py7zr.SevenZipFile(open_path, mode="r") as zf:
            zf.extractall(path=staging)
    except Exception as exc:
        raise RuntimeError(
            "Could not extract AivisSpeech Engine. Close Kaiwa and relaunch to retry.\n"
            f"Detail: {exc}"
        ) from exc
    finally:
        if alias is not None and alias.exists() and alias != archive:
            try:
                alias.unlink()
            except OSError:
                pass

    # Find run.exe in the extract tree.
    runs = list(staging.rglob("run.exe"))
    if not runs:
        raise RuntimeError(
            "AivisSpeech archive extracted but run.exe was not found. "
            "Close Kaiwa and relaunch to retry."
        )
    run = runs[0]

    if dest_root.exists():
        shutil.rmtree(dest_root, ignore_errors=True)
    dest_root.mkdir(parents=True, exist_ok=True)

    # Prefer layout: engine/Windows-x64/run.exe matching tools/ and candidates.
    win64 = run.parent
    if win64.name.lower() == "windows-x64":
        target = dest_root / "engine" / "Windows-x64"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.move(str(win64), str(target))
    else:
        target = dest_root / "engine" / "Windows-x64"
        target.mkdir(parents=True, exist_ok=True)
        for item in win64.iterdir():
            shutil.move(str(item), str(target / item.name))

    shutil.rmtree(staging, ignore_errors=True)
    found = aivis_appdata_run_exe()
    if found is None:
        raise RuntimeError("AivisSpeech install finished but run.exe is missing.")
    return found


def ensure_aivis(*, on_progress: ProgressFn | None = None) -> Path | None:
    existing = aivis_appdata_run_exe() or _find_existing_aivis_elsewhere()
    if existing is not None:
        _save_state({"aivis_ready": True, "aivis_path": str(existing)})
        _emit(
            on_progress,
            step="aivis",
            label="Voice engine ready",
            pct=100,
            done=1,
            total=1,
            aivis_path=str(existing),
        )
        return existing

    if sys.platform != "win32":
        raise RuntimeError("Automatic AivisSpeech install is only supported on Windows.")

    downloads_dir().mkdir(parents=True, exist_ok=True)
    archive = downloads_dir() / AIVIS_ASSET
    if not archive.is_file():
        _http_download(
            AIVIS_URL,
            archive,
            on_progress=on_progress,
            label="Downloading voice engine...",
        )
    else:
        _emit(
            on_progress,
            step="aivis",
            label="Voice engine archive ready",
            pct=50,
            done=1,
            total=2,
        )

    _emit(
        on_progress,
        step="aivis",
        label="Installing voice engine...",
        pct=75,
        done=None,
        total=None,
    )
    run = _extract_aivis_archive(archive, aivis_install_root())
    _save_state(
        {
            "aivis_ready": True,
            "aivis_version": AIVIS_ENGINE_VERSION,
            "aivis_path": str(run),
        }
    )
    _emit(
        on_progress,
        step="aivis",
        label="Voice engine ready",
        pct=100,
        done=1,
        total=1,
        aivis_path=str(run),
    )
    return run


def ensure_all(
    *,
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    on_progress: ProgressFn | None = None,
    skip_aivis: bool = False,
) -> dict[str, Any]:
    user_data_dir().mkdir(parents=True, exist_ok=True)
    _emit(on_progress, step="start", label="Preparing Kaiwa...", pct=0)
    whisper_path = ensure_whisper(model_id=whisper_model, on_progress=on_progress)
    aivis_path: Path | None = None
    if not skip_aivis:
        aivis_path = ensure_aivis(on_progress=on_progress)
    _emit(
        on_progress,
        step="done",
        label="Ready",
        pct=100,
        aivis_path=str(aivis_path) if aivis_path else None,
    )
    return {
        "ok": True,
        "whisper_dir": str(whisper_path),
        "aivis_path": str(aivis_path) if aivis_path else None,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        print("Usage: python -m kaiwa.bootstrap ensure [--skip-aivis]", file=sys.stderr)
        return 2
    cmd = args[0]
    if cmd != "ensure":
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2
    skip = "--skip-aivis" in args
    try:
        ensure_all(skip_aivis=skip)
    except Exception as exc:
        _emit(None, step="error", label=str(exc), pct=None)
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

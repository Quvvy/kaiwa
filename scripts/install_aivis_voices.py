from __future__ import annotations

"""Install extra AivisSpeech voices from AivisHub into the local Engine.

Requires AivisSpeech Engine running on :10101.
Usage:
  .\\.venv\\Scripts\\python.exe scripts\\install_aivis_voices.py
  .\\.venv\\Scripts\\python.exe scripts\\install_aivis_voices.py --uuid <aivm-model-uuid>
"""

import argparse
from typing import Iterable

import httpx

ENGINE = "http://127.0.0.1:10101"
API_DOWNLOAD = "https://api.aivis-project.com/v1/aivm-models/{uuid}/download?model_type=AIVMX"

# Popular public AivisHub models (ACML / free personal use). Already-installed are skipped.
DEFAULT_VOICES: dict[str, str] = {
    "らせつん": "9f36ec0d-8dac-42dc-aff4-149c5f99faad",
    "花音": "a670e6b8-0852-45b2-8704-1bc9862f2fe6",
    "阿井田 茂": "47e53151-a378-46f3-abee-ce13aa07feb1",
    "fumifumi": "71e72188-2726-4739-9aa9-39567396fb2a",
    "凛音エル": "f5017410-fbb5-49e1-97cb-e785f42e15f5",
    "桜音": "3328da9a-8124-4619-a853-f7fc2f37889f",
    "にせ": "6d11c6c2-f4a4-4435-887e-23dd60f8b8dd",
}


def current_speaker_names() -> set[str]:
    resp = httpx.get(f"{ENGINE}/speakers", timeout=15.0)
    resp.raise_for_status()
    return {str(row.get("name") or "") for row in resp.json()}


def install_uuid(uuid: str, *, label: str | None = None) -> None:
    download_url = API_DOWNLOAD.format(uuid=uuid)
    print(f"Installing {label or uuid} …")
    resp = httpx.post(
        f"{ENGINE}/aivm_models/install",
        data={"url": download_url},
        timeout=600.0,
    )
    if resp.status_code not in {200, 204}:
        raise RuntimeError(f"Install failed ({resp.status_code}): {resp.text}")
    print(f"  ok ({resp.status_code})")


def install_many(items: Iterable[tuple[str, str]]) -> None:
    try:
        version = httpx.get(f"{ENGINE}/version", timeout=5.0).text
    except Exception as exc:
        print(f"AivisSpeech Engine not reachable at {ENGINE}: {exc}")
        print("Start it with: .\\.venv\\Scripts\\python.exe scripts\\start_aivisspeech.py")
        raise SystemExit(1) from exc
    print(f"Engine {version.strip()}")

    have = current_speaker_names()
    print(f"Current speakers: {', '.join(sorted(have)) or '(none)'}")

    for name, uuid in items:
        if name in have:
            print(f"Skip {name} (already loaded)")
            continue
        install_uuid(uuid, label=name)

    have_after = current_speaker_names()
    print(f"Speakers now ({len(have_after)}): {', '.join(sorted(have_after))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install AivisHub voices into local Engine")
    parser.add_argument("--uuid", action="append", default=[], help="Extra AivisHub model UUID(s)")
    parser.add_argument(
        "--only-defaults",
        action="store_true",
        help="Install only the curated default set (ignore --uuid)",
    )
    args = parser.parse_args()

    items: list[tuple[str, str]] = list(DEFAULT_VOICES.items())
    if args.uuid and not args.only_defaults:
        for uid in args.uuid:
            items.append((uid, uid))
    install_many(items)


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.config import get_settings
from kaiwa import llm


def main() -> None:
    settings = get_settings()
    print(f"model={settings.deepseek_model} base={settings.deepseek_base_url}")
    reply = llm.chat(
        settings,
        [{"role": "user", "content": "こんにちは！今日は短い日本語で話しましょう。"}],
    )
    print("--- reply ---")
    sys.stdout.buffer.write((reply + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()

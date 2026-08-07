from __future__ import annotations

PHRASES: list[dict[str, str]] = [
    {"id": "p01", "text": "こんにちは。"},
    {"id": "p02", "text": "おはようございます。"},
    {"id": "p03", "text": "こんばんは。"},
    {"id": "p04", "text": "はじめまして。"},
    {"id": "p05", "text": "よろしくお願いします。"},
    {"id": "p06", "text": "わたしは学生です。"},
    {"id": "p07", "text": "日本語を勉強しています。"},
    {"id": "p08", "text": "今日はいい天気ですね。"},
    {"id": "p09", "text": "お元気ですか。"},
    {"id": "p10", "text": "はい、元気です。"},
    {"id": "p11", "text": "ありがとうございます。"},
    {"id": "p12", "text": "すみません。"},
    {"id": "p13", "text": "水をください。"},
    {"id": "p14", "text": "これは何ですか。"},
    {"id": "p15", "text": "もう一度お願いします。"},
    {"id": "p16", "text": "わかりません。"},
    {"id": "p17", "text": "ゆっくり話してください。"},
    {"id": "p18", "text": "駅はどこですか。"},
    {"id": "p19", "text": "トイレはどこですか。"},
    {"id": "p20", "text": "また明日。"},
    {"id": "p21", "text": "いただきます。"},
    {"id": "p22", "text": "ごちそうさまでした。"},
]


def phrase_by_id(phrase_id: str) -> dict[str, str] | None:
    for phrase in PHRASES:
        if phrase["id"] == phrase_id:
            return phrase
    return None


def next_phrase(after_id: str | None = None) -> dict[str, str]:
    if not after_id:
        return PHRASES[0]
    for i, phrase in enumerate(PHRASES):
        if phrase["id"] == after_id:
            return PHRASES[(i + 1) % len(PHRASES)]
    return PHRASES[0]

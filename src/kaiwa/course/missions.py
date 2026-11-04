"""A real little exchange at the end of each unit: the unit's point, used for something.

Task-based teaching (Ellis 2003, Long 2015): language sticks when it's used to get
something done, and finishing a task is a truer sign of progress than a score. Each
mission uses the unit's phrases in a small scene with a goal. It runs on the same
engine as talk practice (roleplay.turn), so the partner reacts to whatever the learner
says, keeps to known material and gives one fix per turn. The scene itself is written
by hand, which means the opener and goal are always right for the unit.
"""

from __future__ import annotations

from typing import Any

MISSIONS: dict[str, dict[str, str]] = {
    "u1": {"scene": "It's 8 a.m. at the station. You bump into your teacher.",
           "goal": "Greet her, thank her for the note she hands you, and say goodbye.",
           "partner": "タナカ", "opener": "おはようございます。これ、どうぞ。", "opener_en": "Good morning. Here, this is for you.",
           "suggest": "ありがとうございます。"},
    "u2": {"scene": "You're at a welcome party. Someone new walks over to you.",
           "goal": "Introduce yourself: your name and where you're from.",
           "partner": "ユキ", "opener": "はじめまして。ユキです。おなまえは？", "opener_en": "Nice to meet you. I'm Yuki. What's your name?",
           "suggest": "はじめまして。わたしは＿です。"},
    "u3": {"scene": "A stranger on the street starts talking to you far too fast.",
           "goal": "Don't give up: say you don't understand and get them to say it again slowly.",
           "partner": "ケン", "opener": "すみません、えきは、どこですか。", "opener_en": "Excuse me, where's the station?",
           "suggest": "すみません、もういちど、おねがいします。"},
    "u4": {"scene": "You're chatting with a new friend during a break.",
           "goal": "Find out what your friend likes, and say what you like.",
           "partner": "ミカ", "opener": "ねこがすきです。ねこ、すきですか。", "opener_en": "I like cats. Do you like cats?",
           "suggest": "はい、すきです。なにがすきですか。"},
    "u5": {"scene": "You sit down in a small café. The waiter comes over.",
           "goal": "Order something to drink, and ask how much it is.",
           "partner": "サトウ", "opener": "いらっしゃいませ。なににしますか。", "opener_en": "Welcome. What would you like?",
           "suggest": "コーヒーをください。"},
    "u6": {"scene": "A classmate is asking about your mornings.",
           "goal": "Say what you eat and drink, and ask what they do.",
           "partner": "リサ", "opener": "あさごはんをたべますか。", "opener_en": "Do you eat breakfast?",
           "suggest": "はい、パンをたべます。"},
    "u7": {"scene": "You've just got off the train in a town you don't know. You need a convenience store.",
           "goal": "Ask a passer-by where the convenience store is.",
           "partner": "ヤマダ", "opener": "こんにちは。どこにいきますか。", "opener_en": "Hello. Where are you going?",
           "suggest": "コンビニにいきます。コンビニは、どこですか。"},
    "u8": {"scene": "A friend wants to know what you're up to.",
           "goal": "Say what you're doing tomorrow and ask about their weekend.",
           "partner": "ハル", "opener": "あした、なにをしますか。", "opener_en": "What are you doing tomorrow?",
           "suggest": "あした、えいがをみます。"},
    "u9": {"scene": "A friend asks how your Japanese study is going.",
           "goal": "Say how it is, and ask about the anime they're watching.",
           "partner": "ナオ", "opener": "にほんごは、どうですか。", "opener_en": "How is Japanese?",
           "suggest": "たのしいです。でも、むずかしいです。"},
    "u10": {"scene": "It's Monday morning at work. A colleague asks about your weekend.",
            "goal": "Say one thing you did and how it was, then ask about theirs.",
            "partner": "ミキ", "opener": "しゅうまつ、なにをしましたか。", "opener_en": "What did you do at the weekend?",
            "suggest": "えいがをみました。たのしかったです。"},
    "u11": {"scene": "You're in a clothes shop looking for a shirt.",
            "goal": "Ask if they have shirts, ask the price, and decide.",
            "partner": "カトウ", "opener": "いらっしゃいませ。", "opener_en": "Welcome.",
            "suggest": "シャツはありますか。"},
    "u12": {"scene": "A friend shows you a photo of their family.",
            "goal": "Say who's in your family and ask about theirs.",
            "partner": "アヤ", "opener": "これは、ははのしゃしんです。きょうだいは、いますか。", "opener_en": "This is a photo of my mother. Do you have brothers or sisters?",
            "suggest": "はい、あにがいます。"},
    "u13": {"scene": "It's a free afternoon, and your friend asks what you feel like doing.",
            "goal": "Say what you want to eat and what you want to do.",
            "partner": "ソラ", "opener": "きょう、なにがしたいですか。", "opener_en": "What do you want to do today?",
            "suggest": "すしがたべたいです。"},
    "u14": {"scene": "You're at a hotel front desk and the receptionist is speaking quickly.",
            "goal": "Ask them to wait, to speak slowly, and to show you where to write your name.",
            "partner": "ホテルのひと", "opener": "ここに、なまえをかいてください。", "opener_en": "Please write your name here.",
            "suggest": "すこしまってください。"},
    "u15": {"scene": "A friend invites you out, but tomorrow doesn't work for you.",
            "goal": "Turn down tomorrow politely and agree on another day.",
            "partner": "ユウ", "opener": "あした、いっしょに、えいがをみませんか。", "opener_en": "Want to watch a movie together tomorrow?",
            "suggest": "あしたは、ちょっと…。いつがいいですか。"},
    "u16": {"scene": "You've lost your keys at a friend's place, and they're helping you look.",
            "goal": "Ask where your keys are and say where things are.",
            "partner": "レン", "opener": "かぎは、かばんのなかですか。", "opener_en": "Are your keys in your bag?",
            "suggest": "いいえ。かぎは、どこにありますか。"},
    "u17": {"scene": "A new colleague asks about your daily routine.",
            "goal": "Say when you get up and work, and ask when they go to bed.",
            "partner": "マイ", "opener": "まいあさ、なんじにおきますか。", "opener_en": "What time do you get up every morning?",
            "suggest": "しちじにおきます。"},
    "u18": {"scene": "You're at a bus stop, trying to reach the bank across town.",
            "goal": "Ask how to get there and how long it takes.",
            "partner": "タケシ", "opener": "こんにちは。どこにいきますか。", "opener_en": "Hello. Where are you going?",
            "suggest": "ぎんこうにいきます。どのくらい、かかりますか。"},
    "u19": {"scene": "You're waiting for the elevator with a neighbour, making small talk.",
            "goal": "Talk about the weather, and find out which season they like.",
            "partner": "スズキ", "opener": "きょうは、さむいですね。", "opener_en": "It's cold today, isn't it.",
            "suggest": "そうですね。どのきせつが、すきですか。"},
    "u20": {"scene": "You and a friend are planning a day out on Saturday.",
            "goal": "Agree on a time and a place to meet.",
            "partner": "アキ", "opener": "どようび、なんじに、あいましょうか。", "opener_en": "What time shall we meet on Saturday?",
            "suggest": "じゅうじに、あいましょう。えきで、あいましょう。"},
}


def mission_for(unit_id: str) -> dict[str, Any] | None:
    m = MISSIONS.get(unit_id)
    return {**m, "turns": 4, "mission": unit_id} if m else None

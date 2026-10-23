"""Beginner course content (pre-N5 → early N5). Hand-written, not generated.

Each unit teaches ~6 high-frequency phrases, then a short listening dialogue
built from them (with at most a couple of glossed new words), then speaking
tasks that can be answered with what the unit just taught.

Japanese is written in kana on purpose: the learner is pre-N5. Romaji is
generated at load time. `expect` patterns are matched against kana-normalized
speech; "*" stands for "anything here" (a name, a food, a country…).
"""

from __future__ import annotations

from typing import Any

UNITS: list[dict[str, Any]] = [
    {
        "id": "u1",
        "title": "Greetings",
        "title_jp": "あいさつ",
        "goal": "Greet people at any time of day, say thanks, say sorry, say bye.",
        "phrases": [
            {"id": "u1.ohayou", "jp": "おはようございます。", "en": "Good morning.",
             "note": "Polite. With friends just say おはよう。", "accept": ["おはよう"]},
            {"id": "u1.konnichiwa", "jp": "こんにちは。", "en": "Hello. (daytime)",
             "note": "The last は is read “wa”.", "accept": ["こんにちわ"]},
            {"id": "u1.konbanwa", "jp": "こんばんは。", "en": "Good evening.",
             "note": "The last は is read “wa”.", "accept": ["こんばんわ"]},
            {"id": "u1.arigatou", "jp": "ありがとうございます。", "en": "Thank you.",
             "note": "With friends: ありがとう。", "accept": ["ありがとう"]},
            {"id": "u1.sumimasen", "jp": "すみません。", "en": "Excuse me. / Sorry.",
             "note": "Also how you get someone's attention in a shop."},
            {"id": "u1.jaamata", "jp": "じゃあ、また。", "en": "See you.",
             "note": "Friendly goodbye. さようなら sounds more final."},
        ],
        "words": [
            {"id": "u1w.asa", "jp": "あさ", "ro": "asa", "en": "morning"},
            {"id": "u1w.hiru", "jp": "ひる", "ro": "hiru", "en": "noon, daytime"},
            {"id": "u1w.yoru", "jp": "よる", "ro": "yoru", "en": "night, evening"},
            {"id": "u1w.kyou", "jp": "きょう", "ro": "kyou", "en": "today"},
            {"id": "u1w.ashita", "jp": "あした", "ro": "ashita", "en": "tomorrow"},
            {"id": "u1w.ima", "jp": "いま", "ro": "ima", "en": "now"},
            {"id": "u1w.watashi", "jp": "わたし", "ro": "watashi", "en": "I, me"},
            {"id": "u1w.hito", "jp": "ひと", "ro": "hito", "en": "person"},
            {"id": "u1w.tomodachi", "jp": "ともだち", "ro": "tomodachi", "en": "friend"},
            {"id": "u1w.sensei", "jp": "せんせい", "ro": "sensei", "en": "teacher"},
            {"id": "u1w.gakusei", "jp": "がくせい", "ro": "gakusei", "en": "student"},
            {"id": "u1w.minasan", "jp": "みなさん", "ro": "minasan", "en": "everyone"},
            {"id": "u1w.douzo", "jp": "どうぞ", "ro": "douzo", "en": "please, go ahead, here you are"},
            {"id": "u1w.doumo", "jp": "どうも", "ro": "doumo", "en": "thanks (short)"},
            {"id": "u1w.oyasumi", "jp": "おやすみなさい", "ro": "oyasuminasai", "en": "good night"},
            {"id": "u1w.ittekimasu", "jp": "いってきます", "ro": "ittekimasu", "en": "I'm off (leaving home)"},
            {"id": "u1w.itterasshai", "jp": "いってらっしゃい", "ro": "itterasshai", "en": "see you later (to someone leaving)"},
            {"id": "u1w.tadaima", "jp": "ただいま", "ro": "tadaima", "en": "I'm home"},
            {"id": "u1w.okaeri", "jp": "おかえりなさい", "ro": "okaerinasai", "en": "welcome back"},
            {"id": "u1w.itadakimasu", "jp": "いただきます", "ro": "itadakimasu", "en": "said before eating"},
        ],
        "grammar": [
            {
                "id": "u1g.polite",
                "rule": "＋ございます = polite. Drop it with friends.",
                "title": "Polite and casual",
                "explain": [
                    "Japanese has two everyday speech styles. Polite style is for strangers, shop staff, "
                    "teachers and anyone older. Casual style is for friends and family.",
                    "Many greetings get their polite form by adding ございます. Drop it with friends.",
                    "When unsure, use polite. It's never rude, only a little distant.",
                ],
                "examples": [
                    {"jp": "おはようございます。", "en": "Good morning. (polite)"},
                    {"jp": "おはよう。", "en": "Morning. (casual)"},
                    {"jp": "ありがとうございます。", "en": "Thank you. (polite)"},
                    {"jp": "ありがとう。", "en": "Thanks. (casual)"},
                ],
            },
            {
                "id": "u1g.desu",
                "rule": "Noun ＋ です = it is / I am. ＋か = question.",
                "title": "Noun + です: it is, I am",
                "explain": [
                    "Put です after a noun to say what something or someone is. It covers it is, "
                    "I am, she is: Japanese leaves out who you mean when it's obvious.",
                    "です is polite. The u is nearly silent, so it sounds like dess.",
                    "To ask a question, add か: がくせいですか。 Are you a student?",
                ],
                "examples": [
                    {"jp": "がくせいです。", "en": "I'm a student."},
                    {"jp": "せんせいです。", "en": "She's the teacher."},
                    {"jp": "ともだちです。", "en": "He's my friend."},
                    {"jp": "あさです。", "en": "It's morning."},
                    {"jp": "がくせいですか。", "en": "Are you a student?"},
                ],
            },
        ],
        # Drill: a one-line situation and (usually) a spoken line to answer.
        # `explain` shows after answering.
        "drill": [
            {"q": "Your friend greets you in the morning.", "say": "おはよう！",
             "choices": ["おはよう！", "おはようございます。", "こんばんは。"], "answer": 0,
             "explain": "Friend → casual: just おはよう。"},
            {"q": "Your teacher hands back your homework.", "say": "はい、どうぞ。",
             "choices": ["ありがとう。", "ありがとうございます。", "どうぞ。"], "answer": 1,
             "explain": "Teacher → polite: ありがとうございます。"},
            {"q": "It's 9 p.m. You pass a neighbour.",
             "choices": ["おはようございます。", "こんにちは。", "こんばんは。"], "answer": 2,
             "explain": "Evening → こんばんは。"},
            {"q": "Someone asks if you're a student. You are.", "say": "がくせいですか。",
             "choices": ["はい、がくせいです。", "はい、がくせいか。", "はい、です、がくせい。"], "answer": 0,
             "explain": "Noun first, then です."},
            {"q": "Ask the person in front of you whether they're the teacher.",
             "choices": ["せんせいですか。", "せんせいです。", "か、せんせいです。"], "answer": 0,
             "explain": "＋か at the end makes a question."},
            {"q": "You're leaving home in the morning.",
             "choices": ["ただいま。", "いってきます。", "いただきます。"], "answer": 1,
             "explain": "Leaving → いってきます. Coming back → ただいま."},
            {"q": "You just got home.",
             "choices": ["ただいま。", "いってきます。", "おやすみなさい。"], "answer": 0,
             "explain": "Coming back → ただいま."},
            {"q": "Dinner is on the table. Before eating:",
             "choices": ["いただきます。", "おやすみなさい。", "どうぞ。"], "answer": 0,
             "explain": "Before a meal → いただきます."},
        ],
        "dialogue": {
            "scene": "A student meets her teacher at the station in the morning, then gets home in the evening.",
            "lines": [
                {"who": "a", "jp": "せんせい、おはようございます。", "en": "Good morning, teacher."},
                {"who": "b", "jp": "あ、おはようございます。きょうは、がっこうですか。",
                 "en": "Oh, good morning. Are you going to school today?", "gloss": "がっこう = school"},
                {"who": "a", "jp": "はい。じゃあ、また。", "en": "Yes. See you.", "gloss": "はい = yes"},
                {"who": "a", "jp": "ただいま。", "en": "I'm home.", "gloss": "(that evening, at home)"},
                {"who": "b", "jp": "おかえりなさい。これ、どうぞ。", "en": "Welcome back. Here, this is for you.",
                 "gloss": "これ = this (her mother is speaking now)"},
                {"who": "a", "jp": "わあ、ありがとう。いただきます。", "en": "Wow, thanks. Let's eat.",
                 "gloss": "わあ = wow"},
            ],
        },
        "questions": [
            {"q": "Who does the student meet in the morning?", "choices": ["A friend", "Her teacher", "Her mother"], "answer": 1},
            {"q": "Where is the student going today?", "choices": ["School", "Home", "The station"], "answer": 0},
            {"q": "Why does she say ありがとう, not ありがとうございます, at home?",
             "choices": ["It's the evening", "It's family, so casual is fine", "It's a question"], "answer": 1},
        ],
        "speak": [
            {"say": "おはようございます。", "situation": "It's 8 a.m. Your neighbour greets you. Greet them back.",
             "hint": "おはようございます。", "expect": ["おはよう*"]},
            {"say": "これ、どうぞ。", "situation": "They hand you a small gift. Thank them politely.",
             "hint": "ありがとうございます。", "expect": ["ありがとう*"]},
            {"say": "せんせいですか。", "situation": "Someone asks if you're the teacher. Say you're a student.",
             "hint": "がくせいです。", "expect": ["*がくせいです*"]},
            {"say": "ただいま。", "situation": "A family member just got home. Welcome them back.",
             "hint": "おかえりなさい。／おかえり。", "expect": ["おかえり*"]},
            {"say": "じゃあ、また。", "situation": "They're leaving. Say bye.",
             "hint": "じゃあ、また。", "expect": ["*また*", "さようなら", "ばいばい"]},
        ],
    },
    {
        "id": "u2",
        "title": "Introducing yourself",
        "title_jp": "じこしょうかい",
        "goal": "Say your name and where you're from, and ask someone's name.",
        "phrases": [
            {"id": "u2.hajimemashite", "jp": "はじめまして。", "en": "Nice to meet you. (first meeting)",
             "note": "Only the first time you meet someone."},
            {"id": "u2.watashiwa", "jp": "わたしはアレックスです。", "en": "I'm Alex.",
             "note": "Use your own name: わたしは＿です。", "accept": ["わたしは*です"]},
            {"id": "u2.yoroshiku", "jp": "よろしくおねがいします。", "en": "Nice to meet you. (said after your name)",
             "note": "Ends almost every self-introduction."},
            {"id": "u2.kara", "jp": "アメリカからきました。", "en": "I'm from America.",
             "note": "＿からきました = I came from ＿. Use your country.", "accept": ["*からきました"]},
            {"id": "u2.onamae", "jp": "おなまえは？", "en": "What's your name?",
             "note": "Short and polite. The お makes it polite."},
            {"id": "u2.san", "jp": "ユキさんですか。", "en": "Are you Yuki?",
             "note": "さん goes after other people's names — never your own."},
        ],
        "words": [
            {
                "id": "u2w.namae",
                "jp": "なまえ",
                "ro": "namae",
                "en": "name"
            },
            {
                "id": "u2w.kuni",
                "jp": "くに",
                "ro": "kuni",
                "en": "country"
            },
            {
                "id": "u2w.nihon",
                "jp": "にほん",
                "ro": "nihon",
                "en": "Japan"
            },
            {
                "id": "u2w.nihonjin",
                "jp": "にほんじん",
                "ro": "nihonjin",
                "en": "Japanese person"
            },
            {
                "id": "u2w.amerikajin",
                "jp": "アメリカじん",
                "ro": "amerikajin",
                "en": "American (person)"
            },
            {
                "id": "u2w.igirisu",
                "jp": "イギリス",
                "ro": "igirisu",
                "en": "the UK"
            },
            {
                "id": "u2w.kankoku",
                "jp": "かんこく",
                "ro": "kankoku",
                "en": "Korea"
            },
            {
                "id": "u2w.chuugoku",
                "jp": "ちゅうごく",
                "ro": "chuugoku",
                "en": "China"
            },
            {
                "id": "u2w.doko",
                "jp": "どこ",
                "ro": "doko",
                "en": "where"
            },
            {
                "id": "u2w.dare",
                "jp": "だれ",
                "ro": "dare",
                "en": "who"
            },
            {
                "id": "u2w.anata",
                "jp": "あなた",
                "ro": "anata",
                "en": "you"
            },
            {
                "id": "u2w.shigoto",
                "jp": "しごと",
                "ro": "shigoto",
                "en": "job, work"
            },
            {
                "id": "u2w.kaishain",
                "jp": "かいしゃいん",
                "ro": "kaishain",
                "en": "office worker"
            },
            {
                "id": "u2w.daigaku",
                "jp": "だいがく",
                "ro": "daigaku",
                "en": "university"
            },
            {
                "id": "u2w.daigakusei",
                "jp": "だいがくせい",
                "ro": "daigakusei",
                "en": "university student"
            },
            {
                "id": "u2w.soudesuka",
                "jp": "そうですか",
                "ro": "sou desu ka",
                "en": "I see"
            }
        ],
        "grammar": [
            {
                "id": "u2g.wa",
                "title": "は: the topic",
                "rule": "A は B です = A is B. は is read wa.",
                "explain": [
                    "は marks what you're talking about: わたしは = as for me. It's written は but read wa.",
                    "Once the topic is clear, drop it: アレックスです on its own is fine.",
                    "Never put さん on your own name, only on other people's."
                ],
                "examples": [
                    {
                        "jp": "わたしはアレックスです。",
                        "en": "I'm Alex."
                    },
                    {
                        "jp": "ユキさんは、がくせいです。",
                        "en": "Yuki is a student."
                    },
                    {
                        "jp": "わたしは、かいしゃいんです。",
                        "en": "I'm an office worker."
                    },
                    {
                        "jp": "アレックスさんは、アメリカじんです。",
                        "en": "Alex is American."
                    }
                ]
            },
            {
                "id": "u2g.kara",
                "title": "から: from",
                "rule": "Place ＋ から = from (place). Country ＋ じん = a person from there.",
                "explain": [
                    "から means from: アメリカから = from America. からきました = I came from, the usual way to say where you're from.",
                    "Add じん to a country for nationality: にほんじん, a Japanese person."
                ],
                "examples": [
                    {
                        "jp": "アメリカからきました。",
                        "en": "I'm from America."
                    },
                    {
                        "jp": "イギリスからきました。",
                        "en": "I'm from the UK."
                    },
                    {
                        "jp": "どこからきましたか。",
                        "en": "Where are you from?"
                    },
                    {
                        "jp": "にほんじんです。",
                        "en": "I'm Japanese."
                    },
                    {
                        "jp": "かんこくじんですか。",
                        "en": "Are you Korean?"
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Someone asks your name.",
                "say": "おなまえは？",
                "choices": [
                    "わたしはアレックスです。",
                    "わたしはアレックスさんです。",
                    "わたしはアレックスか。"
                ],
                "answer": 0,
                "explain": "Never さん on your own name."
            },
            {
                "q": "Say you're from the UK.",
                "choices": [
                    "イギリスからきました。",
                    "イギリスにきました。",
                    "イギリスです、から。"
                ],
                "answer": 0,
                "explain": "から = from."
            },
            {
                "q": "Ask where someone is from.",
                "choices": [
                    "どこからきましたか。",
                    "どこからきました。",
                    "どこですか、から。"
                ],
                "answer": 0,
                "explain": "か at the end makes it a question."
            },
            {
                "q": "You're meeting someone for the first time.",
                "choices": [
                    "はじめまして。",
                    "ただいま。",
                    "おやすみなさい。"
                ],
                "answer": 0
            },
            {
                "q": "Ask whether Yuki is a student.",
                "choices": [
                    "ユキさんは、がくせいですか。",
                    "ユキは、がくせいさんですか。",
                    "ユキさん、がくせいか。"
                ],
                "answer": 0,
                "explain": "さん goes on other people's names; か makes the question."
            },
            {
                "q": "Finish your self-introduction.",
                "choices": [
                    "よろしくおねがいします。",
                    "いただきます。",
                    "すみません。"
                ],
                "answer": 0
            },
            {
                "q": "Say you're Japanese.",
                "choices": [
                    "にほんじんです。",
                    "にほんです。",
                    "にほんからじんです。"
                ],
                "answer": 0,
                "explain": "Country ＋ じん = a person from there."
            },
            {
                "q": "They tell you where they're from. Say \"I see.\"",
                "say": "アメリカからきました。",
                "choices": [
                    "そうですか。",
                    "はじめまして。",
                    "どうぞ。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Meeting a new classmate.",
            "lines": [
                {"who": "a", "jp": "はじめまして。わたしはユキです。", "en": "Nice to meet you. I'm Yuki."},
                {"who": "b", "jp": "はじめまして。アレックスです。", "en": "Nice to meet you. I'm Alex."},
                {"who": "a", "jp": "アレックスさんは、どこからきましたか。", "en": "Where are you from, Alex?",
                 "gloss": "どこ = where"},
                {"who": "b", "jp": "アメリカからきました。", "en": "I'm from America."},
                {"who": "a", "jp": "そうですか。よろしくおねがいします。", "en": "I see. Nice to meet you.",
                 "gloss": "そうですか = I see"},
                {"who": "b", "jp": "よろしくおねがいします。", "en": "Nice to meet you too."},
            ],
        },
        "questions": [
            {"q": "What is the first speaker's name?", "choices": ["Alex", "Yuki", "Amelia"], "answer": 1},
            {"q": "Where is Alex from?", "choices": ["Japan", "England", "America"], "answer": 2},
        ],
        "speak": [
            {"say": "はじめまして。ユキです。", "situation": "Yuki introduces herself. Greet her and say your name.",
             "hint": "はじめまして。わたしは＿です。", "expect": ["はじめまして*", "わたしは*です"]},
            {"say": "おなまえは？", "situation": "She asks your name.",
             "hint": "わたしは＿です。", "expect": ["わたしは*です", "*です"]},
            {"say": "どこからきましたか。", "situation": "She asks where you're from.",
             "hint": "＿からきました。", "expect": ["*からきました", "*から"]},
        ],
    },
    {
        "id": "u3",
        "title": "When you're stuck",
        "title_jp": "こまったとき",
        "goal": "Keep a conversation alive when you don't understand.",
        "phrases": [
            {"id": "u3.wakarimasen", "jp": "わかりません。", "en": "I don't understand. / I don't know.",
             "note": "Totally normal to say. Better than silence."},
            {"id": "u3.mouichido", "jp": "もういちど、おねがいします。", "en": "One more time, please.",
             "note": "もういちど = once more."},
            {"id": "u3.yukkuri", "jp": "ゆっくり、おねがいします。", "en": "Slowly, please.",
             "note": "ゆっくり = slowly."},
            {"id": "u3.nihongode", "jp": "「dog」は、にほんごでなんですか。", "en": "How do you say “dog” in Japanese?",
             "note": "Say the English word first, then はにほんごでなんですか。",
             # The English word must sound like "dog" (ドッグ / ダーグ…): "*にほんご…" alone
             # passed 僕は日本語で何ですか. `kana` is what the kana model listens for.
             "accept": ["どっぐ*にほんごでなんですか", "どぐ*にほんごでなんですか", "だぐ*にほんごでなんですか",
                        "どっく*にほんごでなんですか", "どく*にほんごでなんですか", "dog*にほんごでなんですか"],
             "kana": ["どっぐはにほんごでなんですか", "どぐはにほんごでなんですか", "だぐはにほんごでなんですか"]},
            {"id": "u3.hai", "jp": "はい。", "en": "Yes.", "note": "Also “I'm listening” / “OK”."},
            {"id": "u3.iie", "jp": "いいえ。", "en": "No.", "note": "In speech people often soften it: いえいえ, ううん."},
        ],
        "words": [
            {
                "id": "u3w.eki",
                "jp": "えき",
                "ro": "eki",
                "en": "station"
            },
            {
                "id": "u3w.koko",
                "jp": "ここ",
                "ro": "koko",
                "en": "here"
            },
            {
                "id": "u3w.soko",
                "jp": "そこ",
                "ro": "soko",
                "en": "there (near you)"
            },
            {
                "id": "u3w.nihongo",
                "jp": "にほんご",
                "ro": "nihongo",
                "en": "Japanese (language)"
            },
            {
                "id": "u3w.eigo",
                "jp": "えいご",
                "ro": "eigo",
                "en": "English (language)"
            },
            {
                "id": "u3w.kotoba",
                "jp": "ことば",
                "ro": "kotoba",
                "en": "word"
            },
            {
                "id": "u3w.imi",
                "jp": "いみ",
                "ro": "imi",
                "en": "meaning"
            },
            {
                "id": "u3w.yukkuri",
                "jp": "ゆっくり",
                "ro": "yukkuri",
                "en": "slowly"
            },
            {
                "id": "u3w.mouichido",
                "jp": "もういちど",
                "ro": "mou ichido",
                "en": "once more"
            },
            {
                "id": "u3w.sukoshi",
                "jp": "すこし",
                "ro": "sukoshi",
                "en": "a little"
            },
            {
                "id": "u3w.shitsumon",
                "jp": "しつもん",
                "ro": "shitsumon",
                "en": "question"
            },
            {
                "id": "u3w.kotae",
                "jp": "こたえ",
                "ro": "kotae",
                "en": "answer"
            },
            {
                "id": "u3w.wakarimasu",
                "jp": "わかります",
                "ro": "wakarimasu",
                "en": "understand"
            },
            {
                "id": "u3w.eeto",
                "jp": "ええと",
                "ro": "eeto",
                "en": "um, let me see"
            },
            {
                "id": "u3w.chottomattekudasai",
                "jp": "ちょっとまってください",
                "ro": "chotto matte kudasai",
                "en": "wait a moment, please"
            },
            {
                "id": "u3w.daijoubu",
                "jp": "だいじょうぶ",
                "ro": "daijoubu",
                "en": "OK, all right"
            }
        ],
        "grammar": [
            {
                "id": "u3g.onegai",
                "title": "Asking: ＿、おねがいします",
                "rule": "Thing ＋ おねがいします = (thing), please.",
                "explain": [
                    "おねがいします is a polite please. Put what you want, or how you want it, in front: もういちど (once more), ゆっくり (slowly).",
                    "With friends, just おねがい."
                ],
                "examples": [
                    {
                        "jp": "もういちど、おねがいします。",
                        "en": "One more time, please."
                    },
                    {
                        "jp": "ゆっくり、おねがいします。",
                        "en": "Slowly, please."
                    },
                    {
                        "jp": "えいごで、おねがいします。",
                        "en": "In English, please."
                    },
                    {
                        "jp": "ちょっとまってください。",
                        "en": "Wait a moment, please."
                    }
                ]
            },
            {
                "id": "u3g.masen",
                "title": "ます and ません: yes and no",
                "rule": "わかります = I understand. わかりません = I don't.",
                "explain": [
                    "Polite verbs end in ます. Change ます to ません for the negative.",
                    "Answer a yes/no question with はい or いいえ and repeat the verb. わかりません is normal and polite; it's better than silence."
                ],
                "examples": [
                    {
                        "jp": "わかりますか。",
                        "en": "Do you understand?"
                    },
                    {
                        "jp": "はい、わかります。",
                        "en": "Yes, I understand."
                    },
                    {
                        "jp": "いいえ、わかりません。",
                        "en": "No, I don't understand."
                    },
                    {
                        "jp": "すこし、わかります。",
                        "en": "I understand a little."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "You didn't catch what they said.",
                "say": "えきは、あっちですよ。",
                "choices": [
                    "もういちど、おねがいします。",
                    "いただきます。",
                    "わかります。"
                ],
                "answer": 0
            },
            {
                "q": "They're talking too fast.",
                "choices": [
                    "ゆっくり、おねがいします。",
                    "ゆっくりです。",
                    "ゆっくりか。"
                ],
                "answer": 0,
                "explain": "Thing ＋ おねがいします = please."
            },
            {
                "q": "They ask if you understand. You don't.",
                "say": "わかりますか。",
                "choices": [
                    "いいえ、わかりません。",
                    "いいえ、わかります。",
                    "はい、わかりません。"
                ],
                "answer": 0,
                "explain": "ます → ません for no."
            },
            {
                "q": "You understand a little.",
                "say": "わかりますか。",
                "choices": [
                    "すこし、わかります。",
                    "すこし、わかりません。",
                    "わかりますか、すこし。"
                ],
                "answer": 0
            },
            {
                "q": "Ask how to say \"cat\" in Japanese.",
                "choices": [
                    "「cat」は、にほんごでなんですか。",
                    "「cat」は、えいごでなんですか。",
                    "にほんごは「cat」ですか。"
                ],
                "answer": 0,
                "explain": "にほんごで = in Japanese."
            },
            {
                "q": "Ask them to say it in English.",
                "choices": [
                    "えいごで、おねがいします。",
                    "にほんごで、おねがいします。",
                    "えいごです。"
                ],
                "answer": 0
            },
            {
                "q": "Someone apologises to you. Say it's OK.",
                "say": "すみません。",
                "choices": [
                    "だいじょうぶです。",
                    "わかりません。",
                    "もういちど。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Someone asks you for directions.",
            "lines": [
                {"who": "a", "jp": "すみません、えきは、どこですか。", "en": "Excuse me, where is the station?",
                 "gloss": "えき = station"},
                {"who": "b", "jp": "え？ もういちど、おねがいします。", "en": "Huh? One more time, please."},
                {"who": "a", "jp": "えき は どこ ですか。", "en": "Where — is — the station?"},
                {"who": "b", "jp": "あ、すみません。わかりません。", "en": "Oh, sorry. I don't know."},
                {"who": "a", "jp": "そうですか。ありがとうございます。", "en": "I see. Thank you."},
            ],
        },
        "questions": [
            {"q": "What does B ask for first?", "choices": ["To say it again", "To speak English", "Directions"], "answer": 0},
            {"q": "Does B know where the station is?", "choices": ["Yes", "No"], "answer": 1},
        ],
        "speak": [
            {"say": "きょうはほんとうにいいてんきですね、どこかにでかけるよていはありますか。",
             "situation": "She said something long and fast. Ask her to say it again.",
             "hint": "もういちど、おねがいします。", "expect": ["もういちど*", "わかりません"]},
            {"say": "えきはあっちのほうにまっすぐいって、ふたつめのかどをみぎにまがるとすぐですよ。",
             "situation": "Way too fast. Ask her to speak slowly.",
             "hint": "ゆっくり、おねがいします。", "expect": ["ゆっくり*"]},
            {"say": "なにか、しつもんはありますか。",
             "situation": "She asks if you have questions. Ask how to say “cat” in Japanese.",
             "hint": "「cat」は、にほんごでなんですか。", "expect": ["*にほんごでなんですか", "*にほんごで*"]},
        ],
    },
    {
        "id": "u4",
        "title": "Things you like",
        "title_jp": "すきなもの",
        "goal": "Say what you like and don't, and ask others.",
        "phrases": [
            {"id": "u4.gasuki", "jp": "ねこがすきです。", "en": "I like cats.",
             "note": "＿がすきです = I like ＿. It's が, not を.", "accept": ["*がすきです"]},
            {"id": "u4.sukidesuka", "jp": "いぬがすきですか。", "en": "Do you like dogs?",
             "note": "Add か at the end to make a question."},
            {"id": "u4.haisuki", "jp": "はい、すきです。", "en": "Yes, I like them."},
            {"id": "u4.amari", "jp": "いいえ、あまりすきじゃないです。", "en": "No, I don't really like them.",
             "note": "あまり ＋ negative = not really. Softer than a flat no."},
            {"id": "u4.nanigasuki", "jp": "なにがすきですか。", "en": "What do you like?", "note": "なに = what"},
            {"id": "u4.watashimo", "jp": "わたしも。", "en": "Me too.", "note": "Polite version: わたしもです。"},
        ],
        "words": [
            {
                "id": "u4w.suki",
                "jp": "すき",
                "ro": "suki",
                "en": "like"
            },
            {
                "id": "u4w.kirai",
                "jp": "きらい",
                "ro": "kirai",
                "en": "dislike"
            },
            {
                "id": "u4w.neko",
                "jp": "ねこ",
                "ro": "neko",
                "en": "cat"
            },
            {
                "id": "u4w.inu",
                "jp": "いぬ",
                "ro": "inu",
                "en": "dog"
            },
            {
                "id": "u4w.ongaku",
                "jp": "おんがく",
                "ro": "ongaku",
                "en": "music"
            },
            {
                "id": "u4w.anime",
                "jp": "アニメ",
                "ro": "anime",
                "en": "anime"
            },
            {
                "id": "u4w.supootsu",
                "jp": "スポーツ",
                "ro": "supootsu",
                "en": "sports"
            },
            {
                "id": "u4w.eiga",
                "jp": "えいが",
                "ro": "eiga",
                "en": "movie"
            },
            {
                "id": "u4w.geemu",
                "jp": "ゲーム",
                "ro": "geemu",
                "en": "game"
            },
            {
                "id": "u4w.hon",
                "jp": "ほん",
                "ro": "hon",
                "en": "book"
            },
            {
                "id": "u4w.ryouri",
                "jp": "りょうり",
                "ro": "ryouri",
                "en": "cooking, food"
            },
            {
                "id": "u4w.sushi",
                "jp": "すし",
                "ro": "sushi",
                "en": "sushi"
            },
            {
                "id": "u4w.raamen",
                "jp": "ラーメン",
                "ro": "raamen",
                "en": "ramen"
            },
            {
                "id": "u4w.demo",
                "jp": "でも",
                "ro": "demo",
                "en": "but"
            },
            {
                "id": "u4w.amari",
                "jp": "あまり",
                "ro": "amari",
                "en": "not much (with a negative)"
            },
            {
                "id": "u4w.totemo",
                "jp": "とても",
                "ro": "totemo",
                "en": "very"
            }
        ],
        "grammar": [
            {
                "id": "u4g.ga",
                "title": "＿が すきです",
                "rule": "Thing ＋ が すきです = I like (thing). が, not を.",
                "explain": [
                    "The thing you like takes が: ねこがすきです. Ask with か: いぬがすきですか.",
                    "To say you love it: だいすきです."
                ],
                "examples": [
                    {
                        "jp": "ねこがすきです。",
                        "en": "I like cats."
                    },
                    {
                        "jp": "アニメがすきです。",
                        "en": "I like anime."
                    },
                    {
                        "jp": "なにがすきですか。",
                        "en": "What do you like?"
                    },
                    {
                        "jp": "おんがくが、だいすきです。",
                        "en": "I love music."
                    }
                ]
            },
            {
                "id": "u4g.janai",
                "title": "Not really: じゃないです, あまり",
                "rule": "すきじゃないです = don't like. あまり softens it: not really.",
                "explain": [
                    "すき becomes すきじゃないです in the negative. あまり with a negative means not very, not really; it's softer than きらいです.",
                    "も means also: わたしも = me too, スポーツも = sports too."
                ],
                "examples": [
                    {
                        "jp": "スポーツは、すきじゃないです。",
                        "en": "I don't like sports."
                    },
                    {
                        "jp": "あまりすきじゃないです。",
                        "en": "I don't really like it."
                    },
                    {
                        "jp": "きらいです。",
                        "en": "I hate it."
                    },
                    {
                        "jp": "わたしも、すきです。",
                        "en": "I like it too."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you like cats.",
                "choices": [
                    "ねこがすきです。",
                    "ねこをすきです。",
                    "ねこはすきか。"
                ],
                "answer": 0,
                "explain": "すき takes が."
            },
            {
                "q": "Ask what they like.",
                "choices": [
                    "なにがすきですか。",
                    "なにがすきです。",
                    "なにをすきですか。"
                ],
                "answer": 0
            },
            {
                "q": "You don't really like sports.",
                "say": "スポーツがすきですか。",
                "choices": [
                    "いいえ、あまりすきじゃないです。",
                    "はい、あまりすきです。",
                    "いいえ、とてもすきです。"
                ],
                "answer": 0,
                "explain": "あまり goes with a negative."
            },
            {
                "q": "Your friend likes anime. So do you.",
                "say": "アニメがすきです。",
                "choices": [
                    "わたしも。",
                    "わたしは。",
                    "わたしが。"
                ],
                "answer": 0,
                "explain": "も = also, too."
            },
            {
                "q": "Say you love music.",
                "choices": [
                    "おんがくが、だいすきです。",
                    "おんがくを、だいすきです。",
                    "だいすき、おんがくです。"
                ],
                "answer": 0
            },
            {
                "q": "Say you like games but not movies.",
                "choices": [
                    "ゲームがすきです。でも、えいがはすきじゃないです。",
                    "ゲームがすきじゃないです。でも、えいががすきです。",
                    "ゲームとえいががすきです。"
                ],
                "answer": 0,
                "explain": "でも = but."
            },
            {
                "q": "Ask whether they like ramen.",
                "choices": [
                    "ラーメンがすきですか。",
                    "ラーメンがすきです。",
                    "ラーメンですか、すき。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Small talk with a new friend.",
            "lines": [
                {"who": "a", "jp": "なにがすきですか。", "en": "What do you like?"},
                {"who": "b", "jp": "アニメがすきです。", "en": "I like anime."},
                {"who": "a", "jp": "わたしも！ おんがくも、すきですか。", "en": "Me too! Do you like music too?",
                 "gloss": "おんがく = music, も = also"},
                {"who": "b", "jp": "はい、すきです。でも、スポーツはあまりすきじゃないです。",
                 "en": "Yes, I do. But I don't really like sports.", "gloss": "でも = but"},
            ],
        },
        "questions": [
            {"q": "What does B like?", "choices": ["Sports", "Anime", "Cats"], "answer": 1},
            {"q": "What does B not really like?", "choices": ["Music", "Anime", "Sports"], "answer": 2},
        ],
        "speak": [
            {"say": "なにがすきですか。", "situation": "Tell her something you like.",
             "hint": "＿がすきです。", "expect": ["*がすきです", "*すきです"]},
            {"say": "ねこがすきですか。", "situation": "Do you like cats? Answer yes or no.",
             "hint": "はい、すきです。／いいえ、あまりすきじゃないです。",
             "expect": ["はい*", "いいえ*", "*すきです", "*すきじゃないです"]},
            {"say": "わたしは、すしがすきです。", "situation": "She likes sushi. Say you do too.",
             "hint": "わたしも。", "expect": ["わたしも*"]},
        ],
    },
    {
        "id": "u5",
        "title": "Ordering food",
        "title_jp": "ちゅうもん",
        "goal": "Order in a café, ask what something is, say it's good.",
        "phrases": [
            {"id": "u5.kudasai", "jp": "コーヒーをください。", "en": "A coffee, please.",
             "note": "＿をください = Please give me ＿.", "accept": ["*をください"]},
            {"id": "u5.korewa", "jp": "これはなんですか。", "en": "What is this?", "note": "これ = this"},
            {"id": "u5.oishii", "jp": "おいしいです。", "en": "It's delicious."},
            {"id": "u5.omizu", "jp": "おみず、おねがいします。", "en": "Water, please.",
             "note": "＿、おねがいします also works for ordering."},
            {"id": "u5.ikura", "jp": "いくらですか。", "en": "How much is it?"},
            {"id": "u5.itadakimasu", "jp": "いただきます。", "en": "(said before eating)",
             "note": "Like “let's eat” / thanks for the food."},
        ],
        "words": [
            {
                "id": "u5w.mizu",
                "jp": "みず",
                "ro": "mizu",
                "en": "water"
            },
            {
                "id": "u5w.ocha",
                "jp": "おちゃ",
                "ro": "ocha",
                "en": "green tea"
            },
            {
                "id": "u5w.koucha",
                "jp": "こうちゃ",
                "ro": "koucha",
                "en": "black tea"
            },
            {
                "id": "u5w.koohii",
                "jp": "コーヒー",
                "ro": "koohii",
                "en": "coffee"
            },
            {
                "id": "u5w.keeki",
                "jp": "ケーキ",
                "ro": "keeki",
                "en": "cake"
            },
            {
                "id": "u5w.menyuu",
                "jp": "メニュー",
                "ro": "menyuu",
                "en": "menu"
            },
            {
                "id": "u5w.kore",
                "jp": "これ",
                "ro": "kore",
                "en": "this"
            },
            {
                "id": "u5w.sore",
                "jp": "それ",
                "ro": "sore",
                "en": "that (near you)"
            },
            {
                "id": "u5w.are",
                "jp": "あれ",
                "ro": "are",
                "en": "that (over there)"
            },
            {
                "id": "u5w.ikura",
                "jp": "いくら",
                "ro": "ikura",
                "en": "how much"
            },
            {
                "id": "u5w.en",
                "jp": "えん",
                "ro": "en",
                "en": "yen"
            },
            {
                "id": "u5w.oishii",
                "jp": "おいしい",
                "ro": "oishii",
                "en": "delicious"
            },
            {
                "id": "u5w.hitotsu",
                "jp": "ひとつ",
                "ro": "hitotsu",
                "en": "one (thing)"
            },
            {
                "id": "u5w.futatsu",
                "jp": "ふたつ",
                "ro": "futatsu",
                "en": "two (things)"
            },
            {
                "id": "u5w.okaikei",
                "jp": "おかいけい",
                "ro": "okaikei",
                "en": "the bill"
            },
            {
                "id": "u5w.mise",
                "jp": "みせ",
                "ro": "mise",
                "en": "shop"
            }
        ],
        "grammar": [
            {
                "id": "u5g.kudasai",
                "title": "＿を ください",
                "rule": "Thing ＋ を ください = (thing), please.",
                "explain": [
                    "ください means please give me. The thing comes first, with を (read o). Put a count before ください: コーヒーをひとつください.",
                    "＿、おねがいします works the same way and sounds a little softer."
                ],
                "examples": [
                    {
                        "jp": "コーヒーをください。",
                        "en": "A coffee, please."
                    },
                    {
                        "jp": "ケーキをひとつください。",
                        "en": "One cake, please."
                    },
                    {
                        "jp": "おみずをふたつください。",
                        "en": "Two waters, please."
                    },
                    {
                        "jp": "メニュー、おねがいします。",
                        "en": "The menu, please."
                    }
                ]
            },
            {
                "id": "u5g.kosoa",
                "title": "これ, それ, あれ",
                "rule": "これ = this (near me), それ = that (near you), あれ = that over there.",
                "explain": [
                    "Japanese splits this and that by distance: near the speaker, near the listener, or far from both.",
                    "Point and order with it: これをください (this one, please)."
                ],
                "examples": [
                    {
                        "jp": "これはなんですか。",
                        "en": "What is this?"
                    },
                    {
                        "jp": "それは、まっちゃラテです。",
                        "en": "That's a matcha latte."
                    },
                    {
                        "jp": "あれは、なんですか。",
                        "en": "What's that over there?"
                    },
                    {
                        "jp": "これをください。",
                        "en": "This one, please."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Order a coffee.",
                "say": "いらっしゃいませ。",
                "choices": [
                    "コーヒーをください。",
                    "コーヒーがください。",
                    "ください、コーヒー。"
                ],
                "answer": 0,
                "explain": "Thing ＋ を ください."
            },
            {
                "q": "Order two cakes.",
                "choices": [
                    "ケーキをふたつください。",
                    "ケーキをふたつです。",
                    "ふたつケーキですか。"
                ],
                "answer": 0
            },
            {
                "q": "Hold something up and ask what it is.",
                "choices": [
                    "これはなんですか。",
                    "それはなんですか。",
                    "あれはなんですか。"
                ],
                "answer": 0,
                "explain": "これ = near you."
            },
            {
                "q": "Point at something far across the shop and ask.",
                "choices": [
                    "あれはなんですか。",
                    "これはなんですか。",
                    "それはなんですか。"
                ],
                "answer": 0,
                "explain": "あれ = far from both of you."
            },
            {
                "q": "Ask the price.",
                "choices": [
                    "いくらですか。",
                    "なんですか。",
                    "どこですか。"
                ],
                "answer": 0
            },
            {
                "q": "The staff asks how it is. It's delicious.",
                "say": "どうですか。",
                "choices": [
                    "おいしいです。",
                    "いただきます。",
                    "いくらですか。"
                ],
                "answer": 0
            },
            {
                "q": "Ask for the bill.",
                "choices": [
                    "おかいけい、おねがいします。",
                    "おかいけいです。",
                    "おかいけいをたべます。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "At a café counter.",
            "lines": [
                {"who": "a", "jp": "いらっしゃいませ。", "en": "Welcome!", "gloss": "what shop staff say when you enter"},
                {"who": "b", "jp": "すみません、これはなんですか。", "en": "Excuse me, what is this?"},
                {"who": "a", "jp": "それは、まっちゃラテです。", "en": "That's a matcha latte.", "gloss": "それ = that"},
                {"who": "b", "jp": "じゃあ、まっちゃラテをください。", "en": "Then a matcha latte, please.",
                 "gloss": "じゃあ = then / well"},
                {"who": "a", "jp": "はい。よんひゃくごじゅうえんです。", "en": "Sure. That's 450 yen."},
            ],
        },
        "questions": [
            {"q": "What does B order?", "choices": ["Coffee", "A matcha latte", "Water"], "answer": 1},
            {"q": "How much is it?", "choices": ["150 yen", "450 yen", "540 yen"], "answer": 1},
        ],
        "speak": [
            {"say": "いらっしゃいませ。", "situation": "You walk into a café. Order a coffee.",
             "hint": "コーヒーをください。", "expect": ["*をください", "*おねがいします"]},
            {"say": "これ、どうぞ。", "situation": "They hand you a sample you don't recognise. Ask what it is.",
             "hint": "これはなんですか。", "expect": ["*なんですか"]},
            {"say": "どうですか。", "situation": "They ask how it tastes. Say it's delicious.",
             "hint": "おいしいです。", "expect": ["*おいしい*"]},
        ],
    },
    {
        "id": "u6",
        "title": "Everyday actions",
        "title_jp": "まいにちのこと",
        "goal": "Say what you eat, drink, watch and do — and what you don't.",
        "phrases": [
            {"id": "u6.tabemasu", "jp": "パンをたべます。", "en": "I eat bread.",
             "note": "The verb goes at the end. ＿をたべます = eat ＿.", "accept": ["*をたべます"]},
            {"id": "u6.nomimasu", "jp": "コーヒーをのみます。", "en": "I drink coffee.", "accept": ["*をのみます"]},
            {"id": "u6.mimasu", "jp": "テレビをみます。", "en": "I watch TV.", "accept": ["*をみます"]},
            {"id": "u6.shimasu", "jp": "しゅくだいをします。", "en": "I do homework.",
             "note": "します = do. Very useful verb.", "accept": ["*をします"]},
            {"id": "u6.tabemasuka", "jp": "あさごはんをたべますか。", "en": "Do you eat breakfast?",
             "note": "あさごはん = breakfast"},
            {"id": "u6.tabemasen", "jp": "いいえ、たべません。", "en": "No, I don't (eat it).",
             "note": "ます → ません = don't."},
        ],
        "words": [
            {
                "id": "u6w.tabemasu",
                "jp": "たべます",
                "ro": "tabemasu",
                "en": "eat"
            },
            {
                "id": "u6w.nomimasu",
                "jp": "のみます",
                "ro": "nomimasu",
                "en": "drink"
            },
            {
                "id": "u6w.mimasu",
                "jp": "みます",
                "ro": "mimasu",
                "en": "watch, see"
            },
            {
                "id": "u6w.shimasu",
                "jp": "します",
                "ro": "shimasu",
                "en": "do"
            },
            {
                "id": "u6w.yomimasu",
                "jp": "よみます",
                "ro": "yomimasu",
                "en": "read"
            },
            {
                "id": "u6w.kikimasu",
                "jp": "ききます",
                "ro": "kikimasu",
                "en": "listen"
            },
            {
                "id": "u6w.kakimasu",
                "jp": "かきます",
                "ro": "kakimasu",
                "en": "write"
            },
            {
                "id": "u6w.nemasu",
                "jp": "ねます",
                "ro": "nemasu",
                "en": "sleep"
            },
            {
                "id": "u6w.okimasu",
                "jp": "おきます",
                "ro": "okimasu",
                "en": "get up"
            },
            {
                "id": "u6w.pan",
                "jp": "パン",
                "ro": "pan",
                "en": "bread"
            },
            {
                "id": "u6w.terebi",
                "jp": "テレビ",
                "ro": "terebi",
                "en": "TV"
            },
            {
                "id": "u6w.shukudai",
                "jp": "しゅくだい",
                "ro": "shukudai",
                "en": "homework"
            },
            {
                "id": "u6w.asagohan",
                "jp": "あさごはん",
                "ro": "asagohan",
                "en": "breakfast"
            },
            {
                "id": "u6w.hirugohan",
                "jp": "ひるごはん",
                "ro": "hirugohan",
                "en": "lunch"
            },
            {
                "id": "u6w.bangohan",
                "jp": "ばんごはん",
                "ro": "bangohan",
                "en": "dinner"
            },
            {
                "id": "u6w.dake",
                "jp": "だけ",
                "ro": "dake",
                "en": "only"
            }
        ],
        "grammar": [
            {
                "id": "u6g.wo",
                "title": "＿を ＋ verb",
                "rule": "Object ＋ を ＋ verb. The verb comes last.",
                "explain": [
                    "Japanese puts the verb at the end: パンをたべます is bread を eat. を (read o) marks what the action is done to.",
                    "Who is doing it is left out when it's obvious."
                ],
                "examples": [
                    {
                        "jp": "パンをたべます。",
                        "en": "I eat bread."
                    },
                    {
                        "jp": "コーヒーをのみます。",
                        "en": "I drink coffee."
                    },
                    {
                        "jp": "ほんをよみます。",
                        "en": "I read books."
                    },
                    {
                        "jp": "おんがくをききます。",
                        "en": "I listen to music."
                    }
                ]
            },
            {
                "id": "u6g.masu",
                "title": "ます, ません, ますか",
                "rule": "ます = do, ません = don't, ますか = do you?",
                "explain": [
                    "Swap ます for ません to say don't. Add か to ask.",
                    "Answer by repeating the verb: はい、たべます。 or いいえ、たべません。"
                ],
                "examples": [
                    {
                        "jp": "あさごはんをたべますか。",
                        "en": "Do you eat breakfast?"
                    },
                    {
                        "jp": "はい、たべます。",
                        "en": "Yes, I do."
                    },
                    {
                        "jp": "いいえ、たべません。",
                        "en": "No, I don't."
                    },
                    {
                        "jp": "コーヒーだけ、のみます。",
                        "en": "I only drink coffee."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you drink coffee.",
                "choices": [
                    "コーヒーをのみます。",
                    "のみます、コーヒーを。",
                    "コーヒーがのみます。"
                ],
                "answer": 0,
                "explain": "Verb last; を marks the drink."
            },
            {
                "q": "Say you don't eat breakfast.",
                "choices": [
                    "あさごはんをたべません。",
                    "あさごはんをたべます。",
                    "あさごはんをたべませんか。"
                ],
                "answer": 0
            },
            {
                "q": "Ask whether they watch TV.",
                "choices": [
                    "テレビをみますか。",
                    "テレビをみます。",
                    "テレビですか、みます。"
                ],
                "answer": 0
            },
            {
                "q": "Answer no.",
                "say": "ゲームをしますか。",
                "choices": [
                    "いいえ、しません。",
                    "いいえ、します。",
                    "はい、しません。"
                ],
                "answer": 0
            },
            {
                "q": "Say you read books.",
                "choices": [
                    "ほんをよみます。",
                    "ほんをききます。",
                    "ほんをかきます。"
                ],
                "answer": 0,
                "explain": "よみます = read."
            },
            {
                "q": "Say you listen to music.",
                "choices": [
                    "おんがくをききます。",
                    "おんがくをみます。",
                    "おんがくをよみます。"
                ],
                "answer": 0
            },
            {
                "q": "Say you only drink coffee.",
                "choices": [
                    "コーヒーだけ、のみます。",
                    "コーヒーも、のみます。",
                    "コーヒーを、だけのみます。"
                ],
                "answer": 0,
                "explain": "だけ = only; も = also."
            },
            {
                "q": "Say you go to sleep at night.",
                "choices": [
                    "よる、ねます。",
                    "よる、おきます。",
                    "よる、たべます。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Talking about mornings.",
            "lines": [
                {"who": "a", "jp": "あさ、なにをたべますか。", "en": "What do you eat in the morning?", "gloss": "あさ = morning"},
                {"who": "b", "jp": "パンをたべます。コーヒーも、のみます。", "en": "I eat bread. I also drink coffee."},
                {"who": "a", "jp": "そうですか。わたしは、あさごはんをたべません。", "en": "I see. I don't eat breakfast."},
                {"who": "b", "jp": "え、たべませんか。", "en": "What, you don't?"},
                {"who": "a", "jp": "はい。コーヒーだけ、のみます。", "en": "Right. I only drink coffee.", "gloss": "だけ = only"},
            ],
        },
        "questions": [
            {"q": "What does B eat in the morning?", "choices": ["Rice", "Bread", "Nothing"], "answer": 1},
            {"q": "What does A have in the morning?", "choices": ["Only coffee", "Bread and coffee", "Nothing at all"], "answer": 0},
        ],
        "speak": [
            {"say": "あさ、なにをたべますか。", "situation": "Say what you eat in the morning (or that you don't).",
             "hint": "＿をたべます。／たべません。", "expect": ["*たべます", "*たべません"]},
            {"say": "コーヒーをのみますか。", "situation": "Do you drink coffee? Answer.",
             "hint": "はい、のみます。／いいえ、のみません。", "expect": ["はい*", "いいえ*", "*のみます", "*のみません"]},
            {"say": "よる、なにをしますか。", "situation": "What do you do at night? (よる = night)",
             "hint": "テレビをみます。／しゅくだいをします。", "expect": ["*ます"]},
        ],
    },
    {
        "id": "u7",
        "title": "Places",
        "title_jp": "どこ",
        "goal": "Say where you're going and ask where things are.",
        "phrases": [
            {"id": "u7.ikimasu", "jp": "がっこうにいきます。", "en": "I go to school.",
             "note": "＿にいきます = go to ＿.", "accept": ["*にいきます"]},
            {"id": "u7.doko", "jp": "どこにいきますか。", "en": "Where are you going?"},
            {"id": "u7.kaerimasu", "jp": "うちにかえります。", "en": "I'm going home.",
             "note": "かえります = go back (home). うち = home."},
            {"id": "u7.eki", "jp": "えきは、どこですか。", "en": "Where is the station?",
             "note": "＿はどこですか = Where is ＿?", "accept": ["*はどこですか"]},
            {"id": "u7.konbini", "jp": "コンビニにいきます。", "en": "I'm going to the convenience store."},
            {"id": "u7.asoko", "jp": "あそこです。", "en": "It's over there."},
        ],
        "words": [
            {
                "id": "u7w.ikimasu",
                "jp": "いきます",
                "ro": "ikimasu",
                "en": "go"
            },
            {
                "id": "u7w.kimasu",
                "jp": "きます",
                "ro": "kimasu",
                "en": "come"
            },
            {
                "id": "u7w.kaerimasu",
                "jp": "かえります",
                "ro": "kaerimasu",
                "en": "go home"
            },
            {
                "id": "u7w.uchi",
                "jp": "うち",
                "ro": "uchi",
                "en": "home"
            },
            {
                "id": "u7w.gakkou",
                "jp": "がっこう",
                "ro": "gakkou",
                "en": "school"
            },
            {
                "id": "u7w.kaisha",
                "jp": "かいしゃ",
                "ro": "kaisha",
                "en": "company, office"
            },
            {
                "id": "u7w.konbini",
                "jp": "コンビニ",
                "ro": "konbini",
                "en": "convenience store"
            },
            {
                "id": "u7w.suupaa",
                "jp": "スーパー",
                "ro": "suupaa",
                "en": "supermarket"
            },
            {
                "id": "u7w.byouin",
                "jp": "びょういん",
                "ro": "byouin",
                "en": "hospital"
            },
            {
                "id": "u7w.ginkou",
                "jp": "ぎんこう",
                "ro": "ginkou",
                "en": "bank"
            },
            {
                "id": "u7w.toire",
                "jp": "トイレ",
                "ro": "toire",
                "en": "toilet"
            },
            {
                "id": "u7w.kouen",
                "jp": "こうえん",
                "ro": "kouen",
                "en": "park"
            },
            {
                "id": "u7w.migi",
                "jp": "みぎ",
                "ro": "migi",
                "en": "right"
            },
            {
                "id": "u7w.hidari",
                "jp": "ひだり",
                "ro": "hidari",
                "en": "left"
            },
            {
                "id": "u7w.asoko",
                "jp": "あそこ",
                "ro": "asoko",
                "en": "over there"
            },
            {
                "id": "u7w.korekara",
                "jp": "これから",
                "ro": "korekara",
                "en": "from now, next"
            }
        ],
        "grammar": [
            {
                "id": "u7g.ni",
                "title": "＿に いきます",
                "rule": "Place ＋ に ＋ いきます / きます / かえります = go / come / go home to (place).",
                "explain": [
                    "に marks where you're going: がっこうに = to school. いきます = go, きます = come, かえります = go back home.",
                    "Ask with どこ: どこにいきますか。"
                ],
                "examples": [
                    {
                        "jp": "がっこうにいきます。",
                        "en": "I go to school."
                    },
                    {
                        "jp": "うちにかえります。",
                        "en": "I'm going home."
                    },
                    {
                        "jp": "どこにいきますか。",
                        "en": "Where are you going?"
                    },
                    {
                        "jp": "にほんにきました。",
                        "en": "I came to Japan."
                    }
                ]
            },
            {
                "id": "u7g.doko",
                "title": "＿は どこですか, ここ / そこ / あそこ",
                "rule": "Thing ＋ は どこですか = Where is (thing)? ここ / そこ / あそこ = here / there / over there.",
                "explain": [
                    "Same distance rule as これ / それ / あれ: ここ near me, そこ near you, あそこ far from both.",
                    "Say すみません first to stop someone politely, and answer with the place word ＋ です."
                ],
                "examples": [
                    {
                        "jp": "えきは、どこですか。",
                        "en": "Where's the station?"
                    },
                    {
                        "jp": "トイレは、どこですか。",
                        "en": "Where's the toilet?"
                    },
                    {
                        "jp": "あそこです。",
                        "en": "It's over there."
                    },
                    {
                        "jp": "すみません、コンビニはどこですか。",
                        "en": "Excuse me, where's the convenience store?"
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you're going to school.",
                "choices": [
                    "がっこうにいきます。",
                    "がっこうをいきます。",
                    "がっこうがいきます。"
                ],
                "answer": 0,
                "explain": "に marks where you're going."
            },
            {
                "q": "Ask where they're going.",
                "choices": [
                    "どこにいきますか。",
                    "どこがいきますか。",
                    "どこですか、いきます。"
                ],
                "answer": 0
            },
            {
                "q": "Say you're going home.",
                "choices": [
                    "うちにかえります。",
                    "うちにきます。",
                    "うちをかえります。"
                ],
                "answer": 0,
                "explain": "かえります = go back home."
            },
            {
                "q": "Ask where the toilet is.",
                "choices": [
                    "トイレは、どこですか。",
                    "トイレに、どこですか。",
                    "どこは、トイレですか。"
                ],
                "answer": 0
            },
            {
                "q": "It's across the street, far from both of you.",
                "say": "えきは、どこですか。",
                "choices": [
                    "あそこです。",
                    "ここです。",
                    "そこです。"
                ],
                "answer": 0,
                "explain": "あそこ = over there."
            },
            {
                "q": "It's right where you're standing.",
                "say": "コンビニは、どこですか。",
                "choices": [
                    "ここです。",
                    "あそこです。",
                    "どこです。"
                ],
                "answer": 0
            },
            {
                "q": "Your friend asks if you're going to the park. You aren't.",
                "say": "こうえんにいきますか。",
                "choices": [
                    "いいえ、いきません。",
                    "いいえ、いきます。",
                    "はい、いきません。"
                ],
                "answer": 0
            },
            {
                "q": "Stop a stranger politely and ask the way to the station.",
                "choices": [
                    "すみません、えきはどこですか。",
                    "ただいま、えきはどこですか。",
                    "えき、どこ？"
                ],
                "answer": 0,
                "explain": "すみません first; です and ですか keep it polite."
            }
        ],
        "dialogue": {
            "scene": "On the street.",
            "lines": [
                {"who": "a", "jp": "すみません、コンビニは、どこですか。", "en": "Excuse me, where's the convenience store?"},
                {"who": "b", "jp": "コンビニですか。あそこです。", "en": "The convenience store? It's over there."},
                {"who": "a", "jp": "ありがとうございます。", "en": "Thank you."},
                {"who": "b", "jp": "これから、がっこうにいきますか。", "en": "Are you going to school now?",
                 "gloss": "これから = from now"},
                {"who": "a", "jp": "いいえ、うちにかえります。", "en": "No, I'm going home."},
            ],
        },
        "questions": [
            {"q": "Where is the convenience store?", "choices": ["Over there", "Next to the station", "They don't know"], "answer": 0},
            {"q": "Where is A going next?", "choices": ["School", "Home", "The station"], "answer": 1},
        ],
        "speak": [
            {"say": "どこにいきますか。", "situation": "Say where you're going.",
             "hint": "＿にいきます。", "expect": ["*いきます", "*かえります"]},
            {"say": "どうしましたか。", "situation": "You're lost. Ask where the station is.",
             "hint": "えきは、どこですか。", "expect": ["*どこですか"]},
            {"say": "がっこうにいきますか。", "situation": "Are you going to school? Answer.",
             "hint": "はい、いきます。／いいえ、いきません。", "expect": ["はい*", "いいえ*", "*いきます", "*いきません"]},
        ],
    },
    {
        "id": "u8",
        "title": "Time",
        "title_jp": "いつ",
        "goal": "Talk about today, tomorrow, every day, and the time.",
        "phrases": [
            {"id": "u8.kyou", "jp": "きょう、なにをしますか。", "en": "What are you doing today?"},
            {"id": "u8.ashita", "jp": "あした、えいがをみます。", "en": "Tomorrow I'll watch a movie.",
             "note": "ます also means “will”: みます = watch / will watch."},
            {"id": "u8.mainichi", "jp": "まいにち、にほんごをべんきょうします。", "en": "I study Japanese every day.",
             "note": "まいにち = every day. べんきょう = study."},
            {"id": "u8.nanji", "jp": "いま、なんじですか。", "en": "What time is it now?"},
            {"id": "u8.sanji", "jp": "さんじです。", "en": "It's three o'clock.",
             "note": "4 o'clock is よじ, 9 o'clock is くじ — the odd ones.", "accept": ["*じです"]},
            {"id": "u8.shuumatsu", "jp": "しゅうまつ、なにをしますか。", "en": "What are you doing this weekend?"},
        ],
        "words": [
            {
                "id": "u8w.nanji",
                "jp": "なんじ",
                "ro": "nanji",
                "en": "what time"
            },
            {
                "id": "u8w.ichiji",
                "jp": "いちじ",
                "ro": "ichiji",
                "en": "one o'clock"
            },
            {
                "id": "u8w.yoji",
                "jp": "よじ",
                "ro": "yoji",
                "en": "four o'clock"
            },
            {
                "id": "u8w.shichiji",
                "jp": "しちじ",
                "ro": "shichiji",
                "en": "seven o'clock"
            },
            {
                "id": "u8w.kuji",
                "jp": "くじ",
                "ro": "kuji",
                "en": "nine o'clock"
            },
            {
                "id": "u8w.han",
                "jp": "はん",
                "ro": "han",
                "en": "half past"
            },
            {
                "id": "u8w.gozen",
                "jp": "ごぜん",
                "ro": "gozen",
                "en": "a.m."
            },
            {
                "id": "u8w.gogo",
                "jp": "ごご",
                "ro": "gogo",
                "en": "p.m."
            },
            {
                "id": "u8w.mainichi",
                "jp": "まいにち",
                "ro": "mainichi",
                "en": "every day"
            },
            {
                "id": "u8w.maiasa",
                "jp": "まいあさ",
                "ro": "maiasa",
                "en": "every morning"
            },
            {
                "id": "u8w.shuumatsu",
                "jp": "しゅうまつ",
                "ro": "shuumatsu",
                "en": "weekend"
            },
            {
                "id": "u8w.konshuu",
                "jp": "こんしゅう",
                "ro": "konshuu",
                "en": "this week"
            },
            {
                "id": "u8w.raishuu",
                "jp": "らいしゅう",
                "ro": "raishuu",
                "en": "next week"
            },
            {
                "id": "u8w.benkyou",
                "jp": "べんきょう",
                "ro": "benkyou",
                "en": "study"
            },
            {
                "id": "u8w.shiken",
                "jp": "しけん",
                "ro": "shiken",
                "en": "test, exam"
            },
            {
                "id": "u8w.arimasu",
                "jp": "あります",
                "ro": "arimasu",
                "en": "there is, have (a thing or event)"
            }
        ],
        "grammar": [
            {
                "id": "u8g.ji",
                "title": "Telling the time: ＿じ",
                "rule": "Number ＋ じ = o'clock. Special ones: よじ (4), しちじ (7), くじ (9). はん = half past.",
                "explain": [
                    "Say the number then じ: さんじ is 3:00, じゅうじ is 10:00. Three hours have special readings: よじ, しちじ, くじ.",
                    "はん means half past: さんじはん is 3:30. ごぜん and ごご (a.m. and p.m.) go before the time."
                ],
                "examples": [
                    {
                        "jp": "いま、なんじですか。",
                        "en": "What time is it now?"
                    },
                    {
                        "jp": "さんじです。",
                        "en": "It's three o'clock."
                    },
                    {
                        "jp": "よじはんです。",
                        "en": "It's half past four."
                    },
                    {
                        "jp": "ごご、くじです。",
                        "en": "It's 9 p.m."
                    }
                ]
            },
            {
                "id": "u8g.time",
                "title": "Time words with ます",
                "rule": "Time word ＋、＋ ます verb. ます covers habits and the future.",
                "explain": [
                    "Put the time word first: あした、えいがをみます。 Words like きょう, あした and まいにち need no particle.",
                    "ます covers what you do regularly and what you will do: まいにち、べんきょうします / あした、べんきょうします."
                ],
                "examples": [
                    {
                        "jp": "あした、えいがをみます。",
                        "en": "I'll watch a movie tomorrow."
                    },
                    {
                        "jp": "まいにち、にほんごをべんきょうします。",
                        "en": "I study Japanese every day."
                    },
                    {
                        "jp": "しゅうまつ、なにをしますか。",
                        "en": "What are you doing this weekend?"
                    },
                    {
                        "jp": "らいしゅう、しけんがあります。",
                        "en": "I have a test next week."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "It's 4:00.",
                "say": "いま、なんじですか。",
                "choices": [
                    "よじです。",
                    "よんじです。",
                    "しじです。"
                ],
                "answer": 0,
                "explain": "4 o'clock is よじ."
            },
            {
                "q": "It's 9:30.",
                "choices": [
                    "くじはんです。",
                    "きゅうじはんです。",
                    "くじさんじゅうです。"
                ],
                "answer": 0,
                "explain": "9 o'clock is くじ; はん = half past."
            },
            {
                "q": "It's 7:00.",
                "choices": [
                    "しちじです。",
                    "なのじです。",
                    "しじです。"
                ],
                "answer": 0,
                "explain": "7 o'clock is しちじ."
            },
            {
                "q": "Say you'll watch a movie tomorrow.",
                "choices": [
                    "あした、えいがをみます。",
                    "あした、えいがをみました。",
                    "えいがをみます、あしたか。"
                ],
                "answer": 0,
                "explain": "ます also covers the future."
            },
            {
                "q": "Say you study every day.",
                "choices": [
                    "まいにち、べんきょうします。",
                    "まいにちを、べんきょうします。",
                    "まいにちに、べんきょうします。"
                ],
                "answer": 0,
                "explain": "まいにち takes no particle."
            },
            {
                "q": "Ask what they're doing this weekend.",
                "choices": [
                    "しゅうまつ、なにをしますか。",
                    "しゅうまつ、なにがしますか。",
                    "しゅうまつは、なんじですか。"
                ],
                "answer": 0
            },
            {
                "q": "Say you have a test next week.",
                "choices": [
                    "らいしゅう、しけんがあります。",
                    "らいしゅう、しけんをあります。",
                    "らいしゅう、しけんです。あります。"
                ],
                "answer": 0,
                "explain": "あります takes が."
            },
            {
                "q": "Ask the time.",
                "choices": [
                    "いま、なんじですか。",
                    "いま、なんですか。",
                    "いま、いくらですか。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "After class.",
            "lines": [
                {"who": "a", "jp": "いま、なんじですか。", "en": "What time is it now?"},
                {"who": "b", "jp": "よじです。", "en": "It's four o'clock."},
                {"who": "a", "jp": "あ、じゃあ、うちにかえります。あした、しけんがあります。",
                 "en": "Oh, then I'm going home. I have a test tomorrow.", "gloss": "しけん = test"},
                {"who": "b", "jp": "そうですか。しゅうまつは、なにをしますか。", "en": "I see. What are you doing this weekend?"},
                {"who": "a", "jp": "えいがをみます。", "en": "I'm going to watch a movie."},
            ],
        },
        "questions": [
            {"q": "What time is it?", "choices": ["3 o'clock", "4 o'clock", "9 o'clock"], "answer": 1},
            {"q": "What is A doing on the weekend?", "choices": ["Studying for a test", "Watching a movie", "Going to school"], "answer": 1},
        ],
        "speak": [
            {"say": "いま、なんじですか。", "situation": "Tell her the time (any time is fine).",
             "hint": "＿じです。", "expect": ["*じです", "*じ*"]},
            {"say": "きょう、なにをしますか。", "situation": "Say something you'll do today.",
             "hint": "＿をします。／＿にいきます。", "expect": ["*ます"]},
            {"say": "まいにち、にほんごをべんきょうしますか。", "situation": "Do you study Japanese every day? Answer.",
             "hint": "はい、べんきょうします。", "expect": ["はい*", "いいえ*", "*します", "*しません"]},
        ],
    },
    {
        "id": "u9",
        "title": "How is it?",
        "title_jp": "どうですか",
        "goal": "Say whether something is fun, hard, interesting, expensive or cheap.",
        "phrases": [
            {"id": "u9.tanoshii", "jp": "たのしいです。", "en": "It's fun."},
            {"id": "u9.muzukashii", "jp": "にほんごは、むずかしいです。", "en": "Japanese is difficult."},
            {"id": "u9.omoshiroi", "jp": "このアニメは、おもしろいです。", "en": "This anime is interesting.",
             "note": "おもしろい = interesting or funny. この = this ＿."},
            {"id": "u9.takai", "jp": "たかいです。", "en": "It's expensive."},
            {"id": "u9.yasui", "jp": "やすいです。", "en": "It's cheap."},
            {"id": "u9.doudesuka", "jp": "にほんごは、どうですか。", "en": "How is Japanese (for you)?",
             "note": "＿はどうですか = How is ＿?", "accept": ["*はどうですか"]},
        ],
        "words": [
            {
                "id": "u9w.tanoshii",
                "jp": "たのしい",
                "ro": "tanoshii",
                "en": "fun"
            },
            {
                "id": "u9w.muzukashii",
                "jp": "むずかしい",
                "ro": "muzukashii",
                "en": "difficult"
            },
            {
                "id": "u9w.yasashii",
                "jp": "やさしい",
                "ro": "yasashii",
                "en": "easy; kind"
            },
            {
                "id": "u9w.omoshiroi",
                "jp": "おもしろい",
                "ro": "omoshiroi",
                "en": "interesting, funny"
            },
            {
                "id": "u9w.tsumaranai",
                "jp": "つまらない",
                "ro": "tsumaranai",
                "en": "boring"
            },
            {
                "id": "u9w.takai",
                "jp": "たかい",
                "ro": "takai",
                "en": "expensive; tall"
            },
            {
                "id": "u9w.yasui",
                "jp": "やすい",
                "ro": "yasui",
                "en": "cheap"
            },
            {
                "id": "u9w.ookii",
                "jp": "おおきい",
                "ro": "ookii",
                "en": "big"
            },
            {
                "id": "u9w.chiisai",
                "jp": "ちいさい",
                "ro": "chiisai",
                "en": "small"
            },
            {
                "id": "u9w.atarashii",
                "jp": "あたらしい",
                "ro": "atarashii",
                "en": "new"
            },
            {
                "id": "u9w.furui",
                "jp": "ふるい",
                "ro": "furui",
                "en": "old (things)"
            },
            {
                "id": "u9w.ii",
                "jp": "いい",
                "ro": "ii",
                "en": "good"
            },
            {
                "id": "u9w.warui",
                "jp": "わるい",
                "ro": "warui",
                "en": "bad"
            },
            {
                "id": "u9w.kono",
                "jp": "この",
                "ro": "kono",
                "en": "this ＿"
            },
            {
                "id": "u9w.sono",
                "jp": "その",
                "ro": "sono",
                "en": "that ＿"
            },
            {
                "id": "u9w.kaban",
                "jp": "かばん",
                "ro": "kaban",
                "en": "bag"
            }
        ],
        "grammar": [
            {
                "id": "u9g.adj",
                "title": "Describing words ＋ です",
                "rule": "Describing word ＋ です. Most end in い: たかい, やすい.",
                "explain": [
                    "Words like たのしい and たかい describe things; add です to be polite. Ask how something is with どうですか.",
                    "Put them right before a noun to describe it: たかいかばん, an expensive bag."
                ],
                "examples": [
                    {
                        "jp": "たのしいです。",
                        "en": "It's fun."
                    },
                    {
                        "jp": "このかばんは、たかいです。",
                        "en": "This bag is expensive."
                    },
                    {
                        "jp": "にほんごは、どうですか。",
                        "en": "How is Japanese?"
                    },
                    {
                        "jp": "おもしろいアニメです。",
                        "en": "It's an interesting anime."
                    }
                ]
            },
            {
                "id": "u9g.kunai",
                "title": "Not ＿: い → くないです",
                "rule": "たかい → たかくないです (not expensive). いい → よくないです.",
                "explain": [
                    "To say not, change the final い to くないです: やすい → やすくないです. いい is irregular: よくないです.",
                    "この, その and あの go before a noun: このかばん (this bag), そのかばん (that bag)."
                ],
                "examples": [
                    {
                        "jp": "たかくないです。",
                        "en": "It's not expensive."
                    },
                    {
                        "jp": "むずかしくないです。",
                        "en": "It's not difficult."
                    },
                    {
                        "jp": "よくないです。",
                        "en": "It's not good."
                    },
                    {
                        "jp": "そのかばんは、やすいです。",
                        "en": "That bag is cheap."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say Japanese is difficult.",
                "choices": [
                    "にほんごは、むずかしいです。",
                    "にほんごは、むずかしいだです。",
                    "にほんごを、むずかしいです。"
                ],
                "answer": 0
            },
            {
                "q": "Say it's not expensive.",
                "choices": [
                    "たかくないです。",
                    "たかいないです。",
                    "たかいじゃないです。"
                ],
                "answer": 0,
                "explain": "い → くないです."
            },
            {
                "q": "Say it's not good.",
                "choices": [
                    "よくないです。",
                    "いくないです。",
                    "いいじゃないです。"
                ],
                "answer": 0,
                "explain": "いい is irregular: よくない."
            },
            {
                "q": "Ask how the anime is.",
                "choices": [
                    "このアニメは、どうですか。",
                    "このアニメは、なんですか。",
                    "このアニメは、いくらですか。"
                ],
                "answer": 0
            },
            {
                "q": "A bag costs 50,000 yen.",
                "say": "このかばん、ごまんえんです。",
                "choices": [
                    "たかいです！",
                    "やすいです！",
                    "ちいさいです！"
                ],
                "answer": 0
            },
            {
                "q": "Say it's an interesting anime.",
                "choices": [
                    "おもしろいアニメです。",
                    "アニメおもしろいです。",
                    "おもしろいのアニメです。"
                ],
                "answer": 0,
                "explain": "The describing word goes right before the noun."
            },
            {
                "q": "Say this bag is small.",
                "choices": [
                    "このかばんは、ちいさいです。",
                    "これかばんは、ちいさいです。",
                    "このは、ちいさいかばんです。"
                ],
                "answer": 0,
                "explain": "この ＋ noun."
            },
            {
                "q": "Say it's difficult, but fun.",
                "choices": [
                    "むずかしいです。でも、たのしいです。",
                    "むずかしいです。も、たのしいです。",
                    "むずかしくないです。でも、たのしいです。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Chatting about studying.",
            "lines": [
                {"who": "a", "jp": "にほんごのべんきょうは、どうですか。", "en": "How's studying Japanese going?"},
                {"who": "b", "jp": "むずかしいです。でも、たのしいです。", "en": "It's hard. But it's fun."},
                {"who": "a", "jp": "そうですか。このアニメ、みますか。おもしろいですよ。",
                 "en": "I see. Do you watch this anime? It's good, you know.", "gloss": "よ = “you know”"},
                {"who": "b", "jp": "あ、しっています！ わたしも、すきです。", "en": "Oh, I know it! I like it too.",
                 "gloss": "しっています = I know (it)"},
            ],
        },
        "questions": [
            {"q": "How does B find studying Japanese?", "choices": ["Easy and fun", "Hard but fun", "Boring"], "answer": 1},
            {"q": "What does A recommend?", "choices": ["A book", "An anime", "A café"], "answer": 1},
        ],
        "speak": [
            {"say": "にほんごは、どうですか。", "situation": "How is Japanese for you?",
             "hint": "むずかしいです。でも、たのしいです。", "expect": ["*むずかしい*", "*たのしい*", "*おもしろい*", "*です"]},
            {"say": "このかばん、ごまんえんです。", "situation": "A bag costs 50,000 yen. React.",
             "hint": "たかいです！", "expect": ["*たかい*"]},
            {"say": "このアニメ、どうですか。", "situation": "Give your opinion of an anime you've seen.",
             "hint": "おもしろいです。", "expect": ["*です", "*い"]},
        ],
    },
    {
        "id": "u10",
        "title": "Yesterday",
        "title_jp": "きのう",
        "goal": "Say what you did and how it was.",
        "phrases": [
            {"id": "u10.tabemashita", "jp": "きのう、すしをたべました。", "en": "Yesterday I ate sushi.",
             "note": "ます → ました = did (past).", "accept": ["*ました"]},
            {"id": "u10.ikimashita", "jp": "しゅうまつ、とうきょうにいきました。", "en": "On the weekend I went to Tokyo."},
            {"id": "u10.nanio", "jp": "きのう、なにをしましたか。", "en": "What did you do yesterday?"},
            {"id": "u10.tanoshikatta", "jp": "たのしかったです。", "en": "It was fun.",
             "note": "い-words: たのしい → たのしかった."},
            {"id": "u10.masendeshita", "jp": "べんきょうしませんでした。", "en": "I didn't study.",
             "note": "ません → ませんでした = didn't."},
            {"id": "u10.doudeshita", "jp": "どうでしたか。", "en": "How was it?"},
        ],
        "words": [
            {
                "id": "u10w.kinou",
                "jp": "きのう",
                "ro": "kinou",
                "en": "yesterday"
            },
            {
                "id": "u10w.ototoi",
                "jp": "おととい",
                "ro": "ototoi",
                "en": "the day before yesterday"
            },
            {
                "id": "u10w.senshuu",
                "jp": "せんしゅう",
                "ro": "senshuu",
                "en": "last week"
            },
            {
                "id": "u10w.kyonen",
                "jp": "きょねん",
                "ro": "kyonen",
                "en": "last year"
            },
            {
                "id": "u10w.toukyou",
                "jp": "とうきょう",
                "ro": "toukyou",
                "en": "Tokyo"
            },
            {
                "id": "u10w.ryokou",
                "jp": "りょこう",
                "ro": "ryokou",
                "en": "trip, travel"
            },
            {
                "id": "u10w.kaimono",
                "jp": "かいもの",
                "ro": "kaimono",
                "en": "shopping"
            },
            {
                "id": "u10w.sanpo",
                "jp": "さんぽ",
                "ro": "sanpo",
                "en": "a walk"
            },
            {
                "id": "u10w.tabemashita",
                "jp": "たべました",
                "ro": "tabemashita",
                "en": "ate"
            },
            {
                "id": "u10w.ikimashita",
                "jp": "いきました",
                "ro": "ikimashita",
                "en": "went"
            },
            {
                "id": "u10w.mimashita",
                "jp": "みました",
                "ro": "mimashita",
                "en": "watched, saw"
            },
            {
                "id": "u10w.shimashita",
                "jp": "しました",
                "ro": "shimashita",
                "en": "did"
            },
            {
                "id": "u10w.kaimashita",
                "jp": "かいました",
                "ro": "kaimashita",
                "en": "bought"
            },
            {
                "id": "u10w.imashita",
                "jp": "いました",
                "ro": "imashita",
                "en": "was (somewhere)"
            },
            {
                "id": "u10w.yokatta",
                "jp": "よかった",
                "ro": "yokatta",
                "en": "it was good; glad"
            },
            {
                "id": "u10w.dou",
                "jp": "どう",
                "ro": "dou",
                "en": "how"
            }
        ],
        "grammar": [
            {
                "id": "u10g.mashita",
                "title": "ました, ませんでした: did, didn't",
                "rule": "ます → ました (did). ません → ませんでした (didn't).",
                "explain": [
                    "The past tense is one small change: たべます → たべました. The negative past: たべません → たべませんでした.",
                    "Ask with か: なにをしましたか。"
                ],
                "examples": [
                    {
                        "jp": "きのう、すしをたべました。",
                        "en": "Yesterday I ate sushi."
                    },
                    {
                        "jp": "しゅうまつ、とうきょうにいきました。",
                        "en": "I went to Tokyo at the weekend."
                    },
                    {
                        "jp": "べんきょうしませんでした。",
                        "en": "I didn't study."
                    },
                    {
                        "jp": "ともだちと、えいがをみました。",
                        "en": "I watched a movie with a friend."
                    }
                ]
            },
            {
                "id": "u10g.katta",
                "title": "Was ＿: い → かったです",
                "rule": "たのしい → たのしかったです (it was fun). いい → よかったです.",
                "explain": [
                    "For describing words, change the final い to かったです: おもしろい → おもしろかったです. いい is irregular again: よかったです.",
                    "Ask how something was with どうでしたか."
                ],
                "examples": [
                    {
                        "jp": "たのしかったです。",
                        "en": "It was fun."
                    },
                    {
                        "jp": "おもしろかったです。",
                        "en": "It was interesting."
                    },
                    {
                        "jp": "よかったです。",
                        "en": "It was good."
                    },
                    {
                        "jp": "どうでしたか。",
                        "en": "How was it?"
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you ate sushi yesterday.",
                "choices": [
                    "きのう、すしをたべました。",
                    "きのう、すしをたべます。",
                    "きのう、すしをたべませんでした。"
                ],
                "answer": 0
            },
            {
                "q": "Say you didn't study.",
                "choices": [
                    "べんきょうしませんでした。",
                    "べんきょうしました。",
                    "べんきょうしませんでしたか。"
                ],
                "answer": 0
            },
            {
                "q": "Ask how it was.",
                "choices": [
                    "どうでしたか。",
                    "どうですか。",
                    "なんでしたか。"
                ],
                "answer": 0,
                "explain": "でした = was."
            },
            {
                "q": "It was fun.",
                "say": "どうでしたか。",
                "choices": [
                    "たのしかったです。",
                    "たのしいでした。",
                    "たのしくないです。"
                ],
                "answer": 0,
                "explain": "い → かったです."
            },
            {
                "q": "It was good.",
                "choices": [
                    "よかったです。",
                    "いかったです。",
                    "いいでした。"
                ],
                "answer": 0,
                "explain": "いい → よかった."
            },
            {
                "q": "Say you went to Tokyo last week.",
                "choices": [
                    "せんしゅう、とうきょうにいきました。",
                    "せんしゅう、とうきょうにいきます。",
                    "せんしゅう、とうきょうをいきました。"
                ],
                "answer": 0
            },
            {
                "q": "Ask what they did at the weekend.",
                "choices": [
                    "しゅうまつ、なにをしましたか。",
                    "しゅうまつ、なにをしますか。",
                    "しゅうまつ、なにがしましたか。"
                ],
                "answer": 0
            },
            {
                "q": "Say you went shopping.",
                "choices": [
                    "かいものにいきました。",
                    "かいものをいきました。",
                    "かいものがいきました。"
                ],
                "answer": 0,
                "explain": "Activity ＋ に いきます = go to do it."
            }
        ],
        "dialogue": {
            "scene": "Monday morning.",
            "lines": [
                {"who": "a", "jp": "きのう、なにをしましたか。", "en": "What did you do yesterday?"},
                {"who": "b", "jp": "ともだちと、えいがをみました。", "en": "I watched a movie with a friend.",
                 "gloss": "ともだちと = with a friend"},
                {"who": "a", "jp": "いいですね。どうでしたか。", "en": "Nice. How was it?"},
                {"who": "b", "jp": "おもしろかったです！ Aさんは？", "en": "It was great! And you?"},
                {"who": "a", "jp": "わたしは、うちにいました。べんきょうしませんでした。",
                 "en": "I stayed home. I didn't study.", "gloss": "いました = was (somewhere)"},
            ],
        },
        "questions": [
            {"q": "What did B do yesterday?", "choices": ["Studied", "Watched a movie", "Went to Tokyo"], "answer": 1},
            {"q": "Did A study yesterday?", "choices": ["Yes", "No"], "answer": 1},
        ],
        "speak": [
            {"say": "きのう、なにをしましたか。", "situation": "Say one thing you did yesterday.",
             "hint": "＿をたべました。／＿にいきました。", "expect": ["*ました"]},
            {"say": "どうでしたか。", "situation": "How was it?",
             "hint": "たのしかったです。", "expect": ["*かったです", "*でした", "*かった"]},
            {"say": "きのう、べんきょうしましたか。", "situation": "Did you study yesterday? Answer.",
             "hint": "はい、しました。／いいえ、しませんでした。",
             "expect": ["はい*", "いいえ*", "*しました", "*しませんでした"]},
        ],
    },
]

# Hand-written romaji (particles as learners hear them: は→wa, を→o, へ→e).
ROMAJI: dict[str, str] = {
    "u1.ohayou": "ohayou gozaimasu.",
    "u1.konnichiwa": "konnichiwa.",
    "u1.konbanwa": "konbanwa.",
    "u1.arigatou": "arigatou gozaimasu.",
    "u1.sumimasen": "sumimasen.",
    "u1.jaamata": "jaa, mata.",
    "u2.hajimemashite": "hajimemashite.",
    "u2.watashiwa": "watashi wa Arekkusu desu.",
    "u2.yoroshiku": "yoroshiku onegai shimasu.",
    "u2.kara": "Amerika kara kimashita.",
    "u2.onamae": "onamae wa?",
    "u2.san": "Yuki-san desu ka.",
    "u3.wakarimasen": "wakarimasen.",
    "u3.mouichido": "mou ichido, onegai shimasu.",
    "u3.yukkuri": "yukkuri, onegai shimasu.",
    "u3.nihongode": "“dog” wa, nihongo de nan desu ka.",
    "u3.hai": "hai.",
    "u3.iie": "iie.",
    "u4.gasuki": "neko ga suki desu.",
    "u4.sukidesuka": "inu ga suki desu ka.",
    "u4.haisuki": "hai, suki desu.",
    "u4.amari": "iie, amari suki ja nai desu.",
    "u4.nanigasuki": "nani ga suki desu ka.",
    "u4.watashimo": "watashi mo.",
    "u5.kudasai": "koohii o kudasai.",
    "u5.korewa": "kore wa nan desu ka.",
    "u5.oishii": "oishii desu.",
    "u5.omizu": "omizu, onegai shimasu.",
    "u5.ikura": "ikura desu ka.",
    "u5.itadakimasu": "itadakimasu.",
    "u6.tabemasu": "pan o tabemasu.",
    "u6.nomimasu": "koohii o nomimasu.",
    "u6.mimasu": "terebi o mimasu.",
    "u6.shimasu": "shukudai o shimasu.",
    "u6.tabemasuka": "asagohan o tabemasu ka.",
    "u6.tabemasen": "iie, tabemasen.",
    "u7.ikimasu": "gakkou ni ikimasu.",
    "u7.doko": "doko ni ikimasu ka.",
    "u7.kaerimasu": "uchi ni kaerimasu.",
    "u7.eki": "eki wa, doko desu ka.",
    "u7.konbini": "konbini ni ikimasu.",
    "u7.asoko": "asoko desu.",
    "u8.kyou": "kyou, nani o shimasu ka.",
    "u8.ashita": "ashita, eiga o mimasu.",
    "u8.mainichi": "mainichi, nihongo o benkyou shimasu.",
    "u8.nanji": "ima, nanji desu ka.",
    "u8.sanji": "sanji desu.",
    "u8.shuumatsu": "shuumatsu, nani o shimasu ka.",
    "u9.tanoshii": "tanoshii desu.",
    "u9.muzukashii": "nihongo wa, muzukashii desu.",
    "u9.omoshiroi": "kono anime wa, omoshiroi desu.",
    "u9.takai": "takai desu.",
    "u9.yasui": "yasui desu.",
    "u9.doudesuka": "nihongo wa, dou desu ka.",
    "u10.tabemashita": "kinou, sushi o tabemashita.",
    "u10.ikimashita": "shuumatsu, Toukyou ni ikimashita.",
    "u10.nanio": "kinou, nani o shimashita ka.",
    "u10.tanoshikatta": "tanoshikatta desu.",
    "u10.masendeshita": "benkyou shimasen deshita.",
    "u10.doudeshita": "dou deshita ka.",
}

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
    {
        "id": "u11",
        "title": "Shopping",
        "title_jp": "おみせで",
        "goal": "Ask for things in a shop, count them, and understand prices.",
        "phrases": [
            {
                "id": "u11.arimasuka",
                "jp": "シャツはありますか。",
                "en": "Do you have shirts?",
                "note": "＿はありますか = Do you have ＿? / Is there ＿?",
                "accept": [
                    "*はありますか"
                ]
            },
            {
                "id": "u11.futatsu",
                "jp": "これをふたつください。",
                "en": "Two of these, please.",
                "note": "Count things with ひとつ, ふたつ, みっつ before ください.",
                "accept": [
                    "これを*ください"
                ]
            },
            {
                "id": "u11.zenbu",
                "jp": "ぜんぶで、いくらですか。",
                "en": "How much is it altogether?",
                "note": "ぜんぶで = in total."
            },
            {
                "id": "u11.chotto",
                "jp": "ちょっと、たかいですね。",
                "en": "It's a bit expensive, isn't it.",
                "note": "ね asks the other person to agree."
            },
            {
                "id": "u11.dake",
                "jp": "みているだけです。",
                "en": "I'm just looking.",
                "note": "Handy when shop staff offer help."
            },
            {
                "id": "u11.kaado",
                "jp": "カードで、いいですか。",
                "en": "Is card OK?",
                "note": "＿で いいですか = Is ＿ OK? で = by, with."
            }
        ],
        "words": [
            {
                "id": "u11w.hyaku",
                "jp": "ひゃく",
                "ro": "hyaku",
                "en": "hundred"
            },
            {
                "id": "u11w.sen",
                "jp": "せん",
                "ro": "sen",
                "en": "thousand"
            },
            {
                "id": "u11w.man",
                "jp": "まん",
                "ro": "man",
                "en": "ten thousand"
            },
            {
                "id": "u11w.mittsu",
                "jp": "みっつ",
                "ro": "mittsu",
                "en": "three (things)"
            },
            {
                "id": "u11w.yottsu",
                "jp": "よっつ",
                "ro": "yottsu",
                "en": "four (things)"
            },
            {
                "id": "u11w.zenbu",
                "jp": "ぜんぶ",
                "ro": "zenbu",
                "en": "all, everything"
            },
            {
                "id": "u11w.shatsu",
                "jp": "シャツ",
                "ro": "shatsu",
                "en": "shirt"
            },
            {
                "id": "u11w.kutsu",
                "jp": "くつ",
                "ro": "kutsu",
                "en": "shoes"
            },
            {
                "id": "u11w.boushi",
                "jp": "ぼうし",
                "ro": "boushi",
                "en": "hat"
            },
            {
                "id": "u11w.kasa",
                "jp": "かさ",
                "ro": "kasa",
                "en": "umbrella"
            },
            {
                "id": "u11w.tokei",
                "jp": "とけい",
                "ro": "tokei",
                "en": "watch, clock"
            },
            {
                "id": "u11w.akai",
                "jp": "あかい",
                "ro": "akai",
                "en": "red"
            },
            {
                "id": "u11w.aoi",
                "jp": "あおい",
                "ro": "aoi",
                "en": "blue"
            },
            {
                "id": "u11w.shiroi",
                "jp": "しろい",
                "ro": "shiroi",
                "en": "white"
            },
            {
                "id": "u11w.kuroi",
                "jp": "くろい",
                "ro": "kuroi",
                "en": "black"
            },
            {
                "id": "u11w.kaado",
                "jp": "カード",
                "ro": "kaado",
                "en": "card"
            }
        ],
        "grammar": [
            {
                "id": "u11g.price",
                "title": "Prices: ひゃく, せん, まん",
                "rule": "Number ＋ ひゃく / せん / まん ＋ えん. Watch: さんびゃく, ろっぴゃく, はっぴゃく, さんぜん, はっせん.",
                "explain": [
                    "Prices are built from ひゃく (100), せん (1,000) and まん (10,000): にせんごひゃくえん is 2,500 yen.",
                    "A few combinations change sound: さんびゃく (300), ろっぴゃく (600), はっぴゃく (800), さんぜん (3,000), はっせん (8,000). Big numbers count in まん: 50,000 is ごまん."
                ],
                "examples": [
                    {
                        "jp": "ひゃくえんです。",
                        "en": "It's 100 yen."
                    },
                    {
                        "jp": "さんびゃくえんです。",
                        "en": "It's 300 yen."
                    },
                    {
                        "jp": "せんごひゃくえんです。",
                        "en": "It's 1,500 yen."
                    },
                    {
                        "jp": "いちまんえんです。",
                        "en": "It's 10,000 yen."
                    }
                ]
            },
            {
                "id": "u11g.arimasu",
                "title": "＿はありますか and counting",
                "rule": "＿はありますか = Do you have ＿? Count things with ひとつ, ふたつ, みっつ… before ください.",
                "explain": [
                    "あります means there is or have, for things. ＿はありますか asks a shop if they have it; the answer is はい、あります or いいえ、ありません.",
                    "Count general things with ひとつ, ふたつ, みっつ, よっつ: これをみっつください (three of these, please)."
                ],
                "examples": [
                    {
                        "jp": "シャツはありますか。",
                        "en": "Do you have shirts?"
                    },
                    {
                        "jp": "はい、あります。",
                        "en": "Yes, we do."
                    },
                    {
                        "jp": "いいえ、ありません。",
                        "en": "No, we don't."
                    },
                    {
                        "jp": "ケーキをみっつください。",
                        "en": "Three cakes, please."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Ask if they have hats.",
                "choices": [
                    "ぼうしはありますか。",
                    "ぼうしをありますか。",
                    "ぼうしがいますか。"
                ],
                "answer": 0,
                "explain": "Things: あります."
            },
            {
                "q": "You work in the shop. You have none.",
                "say": "かさはありますか。",
                "choices": [
                    "いいえ、ありません。",
                    "いいえ、あります。",
                    "いいえ、いません。"
                ],
                "answer": 0,
                "explain": "ありません = there isn't."
            },
            {
                "q": "Say 300 yen.",
                "choices": [
                    "さんびゃくえんです。",
                    "さんひゃくえんです。",
                    "さんぜんえんです。"
                ],
                "answer": 0,
                "explain": "3 ＋ ひゃく = さんびゃく."
            },
            {
                "q": "Say 8,000 yen.",
                "choices": [
                    "はっせんえんです。",
                    "はちせんえんです。",
                    "はっぴゃくえんです。"
                ],
                "answer": 0,
                "explain": "8 ＋ せん = はっせん."
            },
            {
                "q": "Order three of these.",
                "choices": [
                    "これをみっつください。",
                    "これをさんください。",
                    "みっつをこれください。"
                ],
                "answer": 0,
                "explain": "Things count ひとつ, ふたつ, みっつ."
            },
            {
                "q": "Ask how much it is altogether.",
                "choices": [
                    "ぜんぶで、いくらですか。",
                    "ぜんぶは、なんですか。",
                    "ぜんぶで、どこですか。"
                ],
                "answer": 0
            },
            {
                "q": "A clerk offers help. You're just looking.",
                "say": "なにか、おさがしですか。",
                "choices": [
                    "みているだけです。",
                    "みています、ください。",
                    "みるだけですか。"
                ],
                "answer": 0
            },
            {
                "q": "Ask if you can pay by card.",
                "choices": [
                    "カードで、いいですか。",
                    "カードを、いいですか。",
                    "カードは、いますか。"
                ],
                "answer": 0,
                "explain": "で = by, with."
            }
        ],
        "dialogue": {
            "scene": "Buying a hat at a small shop.",
            "lines": [
                {
                    "who": "a",
                    "jp": "いらっしゃいませ。",
                    "en": "Welcome."
                },
                {
                    "who": "b",
                    "jp": "すみません、ぼうしはありますか。",
                    "en": "Excuse me, do you have hats?"
                },
                {
                    "who": "a",
                    "jp": "はい、こちらです。",
                    "en": "Yes, this way.",
                    "gloss": "こちら = this way (polite)"
                },
                {
                    "who": "b",
                    "jp": "これ、いくらですか。",
                    "en": "How much is this one?"
                },
                {
                    "who": "a",
                    "jp": "にせんはっぴゃくえんです。",
                    "en": "It's 2,800 yen."
                },
                {
                    "who": "b",
                    "jp": "ちょっと、たかいですね。じゃあ、みているだけです。",
                    "en": "That's a bit expensive. I'm just looking, then."
                }
            ]
        },
        "questions": [
            {
                "q": "What is the customer looking for?",
                "choices": [
                    "Shoes",
                    "A hat",
                    "An umbrella"
                ],
                "answer": 1
            },
            {
                "q": "How much is it?",
                "choices": [
                    "800 yen",
                    "2,800 yen",
                    "2,300 yen"
                ],
                "answer": 1
            },
            {
                "q": "Does the customer buy it?",
                "choices": [
                    "Yes, two of them",
                    "Yes, by card",
                    "No, just looking"
                ],
                "answer": 2
            }
        ],
        "speak": [
            {
                "say": "いらっしゃいませ。",
                "situation": "You walk into a shop. Ask if they have umbrellas.",
                "hint": "かさはありますか。",
                "expect": [
                    "*はありますか*"
                ]
            },
            {
                "say": "はい、ありますよ。いくつですか。",
                "situation": "They have them. Ask for two.",
                "hint": "ふたつください。",
                "expect": [
                    "*ふたつ*"
                ]
            },
            {
                "say": "ぜんぶで、さんぜんえんです。",
                "situation": "Ask if you can pay by card.",
                "hint": "カードで、いいですか。",
                "expect": [
                    "*カード*"
                ]
            }
        ]
    },
    {
        "id": "u12",
        "title": "Family",
        "title_jp": "かぞく",
        "goal": "Talk about your family and ask about someone else's.",
        "phrases": [
            {
                "id": "u12.yonin",
                "jp": "かぞくは、よにんです。",
                "en": "There are four of us in my family.",
                "note": "People count ひとり, ふたり, さんにん, よにん."
            },
            {
                "id": "u12.ani",
                "jp": "あにがいます。",
                "en": "I have an older brother.",
                "note": "＿がいます = there is, I have (people and animals).",
                "accept": [
                    "*がいます"
                ]
            },
            {
                "id": "u12.kyoudai",
                "jp": "きょうだいは、いますか。",
                "en": "Do you have brothers or sisters?"
            },
            {
                "id": "u12.hitorikko",
                "jp": "ひとりっこです。",
                "en": "I'm an only child."
            },
            {
                "id": "u12.shashin",
                "jp": "これは、ははのしゃしんです。",
                "en": "This is a photo of my mother.",
                "note": "の joins nouns: ははのしゃしん = mother's photo."
            },
            {
                "id": "u12.okaasan",
                "jp": "おかあさんは、げんきですか。",
                "en": "Is your mother well?",
                "note": "Someone else's mother is おかあさん; your own is はは."
            }
        ],
        "words": [
            {
                "id": "u12w.kazoku",
                "jp": "かぞく",
                "ro": "kazoku",
                "en": "family"
            },
            {
                "id": "u12w.chichi",
                "jp": "ちち",
                "ro": "chichi",
                "en": "my father"
            },
            {
                "id": "u12w.haha",
                "jp": "はは",
                "ro": "haha",
                "en": "my mother"
            },
            {
                "id": "u12w.ani",
                "jp": "あに",
                "ro": "ani",
                "en": "my older brother"
            },
            {
                "id": "u12w.ane",
                "jp": "あね",
                "ro": "ane",
                "en": "my older sister"
            },
            {
                "id": "u12w.otouto",
                "jp": "おとうと",
                "ro": "otouto",
                "en": "younger brother"
            },
            {
                "id": "u12w.imouto",
                "jp": "いもうと",
                "ro": "imouto",
                "en": "younger sister"
            },
            {
                "id": "u12w.otousan",
                "jp": "おとうさん",
                "ro": "otousan",
                "en": "(someone's) father"
            },
            {
                "id": "u12w.okaasan",
                "jp": "おかあさん",
                "ro": "okaasan",
                "en": "(someone's) mother"
            },
            {
                "id": "u12w.kyoudai",
                "jp": "きょうだい",
                "ro": "kyoudai",
                "en": "brothers and sisters"
            },
            {
                "id": "u12w.hitori",
                "jp": "ひとり",
                "ro": "hitori",
                "en": "one person"
            },
            {
                "id": "u12w.futari",
                "jp": "ふたり",
                "ro": "futari",
                "en": "two people"
            },
            {
                "id": "u12w.shashin",
                "jp": "しゃしん",
                "ro": "shashin",
                "en": "photo"
            },
            {
                "id": "u12w.genki",
                "jp": "げんき",
                "ro": "genki",
                "en": "well, healthy"
            },
            {
                "id": "u12w.imasu",
                "jp": "います",
                "ro": "imasu",
                "en": "there is (people, animals)"
            },
            {
                "id": "u12w.imasen",
                "jp": "いません",
                "ro": "imasen",
                "en": "there isn't (people, animals)"
            }
        ],
        "grammar": [
            {
                "id": "u12g.imasu",
                "title": "います and あります",
                "rule": "People and animals: います. Things and events: あります.",
                "explain": [
                    "Japanese has two verbs for there is: います for living things (people, animals), あります for everything else. ＿がいます also means I have: あにがいます (I have an older brother).",
                    "Count people with ひとり, ふたり, then さんにん, よにん, ごにん."
                ],
                "examples": [
                    {
                        "jp": "あにがいます。",
                        "en": "I have an older brother."
                    },
                    {
                        "jp": "いぬがいます。",
                        "en": "I have a dog."
                    },
                    {
                        "jp": "きょうだいは、いません。",
                        "en": "I don't have any brothers or sisters."
                    },
                    {
                        "jp": "かぞくは、さんにんです。",
                        "en": "There are three of us."
                    }
                ]
            },
            {
                "id": "u12g.no",
                "title": "の: my, your, of",
                "rule": "A の B = A's B. わたしのかばん = my bag.",
                "explain": [
                    "の joins two nouns; the first owns or describes the second: わたしのかばん (my bag), ははのしゃしん (my mother's photo).",
                    "Japanese uses different words for your own family (はは, ちち) and someone else's (おかあさん, おとうさん)."
                ],
                "examples": [
                    {
                        "jp": "わたしのかばんです。",
                        "en": "It's my bag."
                    },
                    {
                        "jp": "ははのしゃしんです。",
                        "en": "It's my mother's photo."
                    },
                    {
                        "jp": "ともだちのいぬです。",
                        "en": "It's my friend's dog."
                    },
                    {
                        "jp": "にほんごのほんです。",
                        "en": "It's a Japanese book."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you have a younger sister.",
                "choices": [
                    "いもうとがいます。",
                    "いもうとがあります。",
                    "いもうとをいます。"
                ],
                "answer": 0,
                "explain": "People take います."
            },
            {
                "q": "Say you have a cat.",
                "choices": [
                    "ねこがいます。",
                    "ねこがあります。",
                    "ねこです、います。"
                ],
                "answer": 0,
                "explain": "Animals take います too."
            },
            {
                "q": "Say you have a test tomorrow.",
                "choices": [
                    "あした、しけんがあります。",
                    "あした、しけんがいます。",
                    "あした、しけんをいます。"
                ],
                "answer": 0,
                "explain": "Things and events take あります."
            },
            {
                "q": "Say it's your bag.",
                "choices": [
                    "わたしのかばんです。",
                    "わたしかばんです。",
                    "かばんのわたしです。"
                ],
                "answer": 0,
                "explain": "Owner ＋ の ＋ thing."
            },
            {
                "q": "Ask after a friend's mother.",
                "choices": [
                    "おかあさんは、げんきですか。",
                    "ははは、げんきですか。",
                    "わたしのおかあさんですか。"
                ],
                "answer": 0,
                "explain": "Someone else's mother is おかあさん."
            },
            {
                "q": "Say your own mother is a teacher.",
                "choices": [
                    "ははは、せんせいです。",
                    "おかあさんは、せんせいです。",
                    "わたしのおかあさんさんです。"
                ],
                "answer": 0,
                "explain": "Your own mother is はは."
            },
            {
                "q": "There are four people in your family.",
                "choices": [
                    "かぞくは、よにんです。",
                    "かぞくは、よんにんです。",
                    "かぞくは、よっつです。"
                ],
                "answer": 0,
                "explain": "People: ひとり, ふたり, さんにん, よにん."
            },
            {
                "q": "You have no brothers or sisters.",
                "say": "きょうだいは、いますか。",
                "choices": [
                    "ひとりっこです。",
                    "ひとりです、きょうだい。",
                    "きょうだいがあります。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Yuki and a friend look at photos on the friend's phone.",
            "lines": [
                {
                    "who": "a",
                    "jp": "これは、だれですか。",
                    "en": "Who's this?"
                },
                {
                    "who": "b",
                    "jp": "ははです。こっちは、あにです。",
                    "en": "That's my mother. This one is my older brother.",
                    "gloss": "こっち = this one (casual)"
                },
                {
                    "who": "a",
                    "jp": "やさしそうですね。",
                    "en": "They look kind.",
                    "gloss": "やさしそう = looks kind"
                },
                {
                    "who": "b",
                    "jp": "はい、やさしいです。ユキさんは、きょうだいがいますか。",
                    "en": "Yes, they are. Do you have brothers or sisters, Yuki?"
                },
                {
                    "who": "a",
                    "jp": "いいえ、ひとりっこです。でも、いぬがいます！",
                    "en": "No, I'm an only child. But I have a dog!"
                }
            ]
        },
        "questions": [
            {
                "q": "Who is in the first photo?",
                "choices": [
                    "The friend's mother",
                    "The friend's sister",
                    "Yuki's mother"
                ],
                "answer": 0
            },
            {
                "q": "Does Yuki have brothers or sisters?",
                "choices": [
                    "Yes, a brother",
                    "No, she's an only child",
                    "Yes, a sister"
                ],
                "answer": 1
            },
            {
                "q": "What does Yuki have?",
                "choices": [
                    "A photo of her brother",
                    "A dog",
                    "A cat"
                ],
                "answer": 1
            }
        ],
        "speak": [
            {
                "say": "かぞくは、なんにんですか。",
                "situation": "Say how many people are in your family.",
                "hint": "＿にんです。／よにんです。",
                "expect": [
                    "*にんです*",
                    "*りです*"
                ]
            },
            {
                "say": "きょうだいは、いますか。",
                "situation": "Answer about your brothers and sisters.",
                "hint": "あにがいます。／ひとりっこです。",
                "expect": [
                    "*います*",
                    "*いません*",
                    "ひとりっこ*"
                ]
            },
            {
                "say": "これ、わたしのいぬです。",
                "situation": "Your friend shows you their dog. Ask its name.",
                "hint": "なまえは、なんですか。",
                "expect": [
                    "*なまえ*"
                ]
            }
        ]
    },
    {
        "id": "u13",
        "title": "Wants",
        "title_jp": "ほしいもの",
        "goal": "Say what you want, and what you want to do.",
        "phrases": [
            {
                "id": "u13.tabetai",
                "jp": "すしがたべたいです。",
                "en": "I want to eat sushi.",
                "note": "Drop ます, add たいです: たべます → たべたいです.",
                "accept": [
                    "*たべたいです"
                ]
            },
            {
                "id": "u13.ikitai",
                "jp": "にほんにいきたいです。",
                "en": "I want to go to Japan."
            },
            {
                "id": "u13.shitai",
                "jp": "なにがしたいですか。",
                "en": "What do you want to do?"
            },
            {
                "id": "u13.hoshii",
                "jp": "あたらしいかばんがほしいです。",
                "en": "I want a new bag.",
                "note": "ほしい is for things; たい is for doing.",
                "accept": [
                    "*がほしいです"
                ]
            },
            {
                "id": "u13.nanika",
                "jp": "なにか、のみたいです。",
                "en": "I want to drink something.",
                "note": "なにか = something."
            },
            {
                "id": "u13.yasumitai",
                "jp": "つかれました。やすみたいです。",
                "en": "I'm tired. I want to rest.",
                "note": "つかれました = I'm tired (I got tired)."
            }
        ],
        "words": [
            {
                "id": "u13w.hoshii",
                "jp": "ほしい",
                "ro": "hoshii",
                "en": "want (a thing)"
            },
            {
                "id": "u13w.nanika",
                "jp": "なにか",
                "ro": "nanika",
                "en": "something"
            },
            {
                "id": "u13w.dokoka",
                "jp": "どこか",
                "ro": "dokoka",
                "en": "somewhere"
            },
            {
                "id": "u13w.yasumimasu",
                "jp": "やすみます",
                "ro": "yasumimasu",
                "en": "rest; take a day off"
            },
            {
                "id": "u13w.asobimasu",
                "jp": "あそびます",
                "ro": "asobimasu",
                "en": "play, hang out"
            },
            {
                "id": "u13w.aimasu",
                "jp": "あいます",
                "ro": "aimasu",
                "en": "meet"
            },
            {
                "id": "u13w.kaimasu",
                "jp": "かいます",
                "ro": "kaimasu",
                "en": "buy"
            },
            {
                "id": "u13w.tsukaremashita",
                "jp": "つかれました",
                "ro": "tsukaremashita",
                "en": "I'm tired"
            },
            {
                "id": "u13w.onakagasukimashita",
                "jp": "おなかがすきました",
                "ro": "onaka ga sukimashita",
                "en": "I'm hungry"
            },
            {
                "id": "u13w.nodogakawakimashita",
                "jp": "のどがかわきました",
                "ro": "nodo ga kawakimashita",
                "en": "I'm thirsty"
            },
            {
                "id": "u13w.umi",
                "jp": "うみ",
                "ro": "umi",
                "en": "the sea"
            },
            {
                "id": "u13w.yama",
                "jp": "やま",
                "ro": "yama",
                "en": "mountain"
            },
            {
                "id": "u13w.onsen",
                "jp": "おんせん",
                "ro": "onsen",
                "en": "hot spring"
            },
            {
                "id": "u13w.kuruma",
                "jp": "くるま",
                "ro": "kuruma",
                "en": "car"
            },
            {
                "id": "u13w.itsuka",
                "jp": "いつか",
                "ro": "itsuka",
                "en": "someday"
            },
            {
                "id": "u13w.yukkurishimasu",
                "jp": "ゆっくりします",
                "ro": "yukkuri shimasu",
                "en": "take it easy"
            }
        ],
        "grammar": [
            {
                "id": "u13g.tai",
                "title": "Want to: ＿たいです",
                "rule": "ます-stem ＋ たいです = want to. たべます → たべたいです.",
                "explain": [
                    "Drop ます and add たいです: たべます → たべたいです (want to eat), いきます → いきたいです (want to go).",
                    "Ask with か: なにがしたいですか。 What you want to eat or see can take が or を: すしがたべたいです."
                ],
                "examples": [
                    {
                        "jp": "すしがたべたいです。",
                        "en": "I want to eat sushi."
                    },
                    {
                        "jp": "にほんにいきたいです。",
                        "en": "I want to go to Japan."
                    },
                    {
                        "jp": "えいがをみたいです。",
                        "en": "I want to watch a movie."
                    },
                    {
                        "jp": "なにがしたいですか。",
                        "en": "What do you want to do?"
                    }
                ]
            },
            {
                "id": "u13g.hoshii",
                "title": "Want a thing: ＿がほしいです",
                "rule": "Thing ＋ が ほしいです = I want (thing). たい is for doing, ほしい for things.",
                "explain": [
                    "ほしい is for things: くるまがほしいです (I want a car). たい is for actions: くるまをかいたいです (I want to buy a car).",
                    "Not wanting follows the い rule from unit 9: ほしくないです, いきたくないです."
                ],
                "examples": [
                    {
                        "jp": "あたらしいかばんがほしいです。",
                        "en": "I want a new bag."
                    },
                    {
                        "jp": "くるまがほしいです。",
                        "en": "I want a car."
                    },
                    {
                        "jp": "なにがほしいですか。",
                        "en": "What do you want?"
                    },
                    {
                        "jp": "いきたくないです。",
                        "en": "I don't want to go."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you want to eat ramen.",
                "choices": [
                    "ラーメンがたべたいです。",
                    "ラーメンがたべますたいです。",
                    "ラーメンをほしいです。"
                ],
                "answer": 0,
                "explain": "Drop ます, add たいです."
            },
            {
                "q": "Say you want to go to the sea.",
                "choices": [
                    "うみにいきたいです。",
                    "うみにいきますたい。",
                    "うみがいきたいです。"
                ],
                "answer": 0,
                "explain": "に marks where you go."
            },
            {
                "q": "Say you want a new bag.",
                "choices": [
                    "あたらしいかばんがほしいです。",
                    "あたらしいかばんをたいです。",
                    "あたらしいかばんがほしいたいです。"
                ],
                "answer": 0,
                "explain": "Things: ほしい."
            },
            {
                "q": "Ask what they want to do.",
                "choices": [
                    "なにがしたいですか。",
                    "なにがほしいですか。",
                    "なにをしますか、たい。"
                ],
                "answer": 0,
                "explain": "したい = want to do."
            },
            {
                "q": "You're tired. Say you want to rest.",
                "choices": [
                    "やすみたいです。",
                    "やすみほしいです。",
                    "やすみますたいです。"
                ],
                "answer": 0
            },
            {
                "q": "Say you don't want to go.",
                "choices": [
                    "いきたくないです。",
                    "いきたいないです。",
                    "いきないたいです。"
                ],
                "answer": 0,
                "explain": "たい → たくない, like any い word."
            },
            {
                "q": "Say you're hungry.",
                "choices": [
                    "おなかがすきました。",
                    "のどがかわきました。",
                    "つかれました。"
                ],
                "answer": 0
            },
            {
                "q": "Your friend asks what you want for your birthday.",
                "say": "たんじょうび、なにがほしいですか。",
                "choices": [
                    "ゲームがほしいです。",
                    "ゲームがしたいです。",
                    "ゲームをたべたいです。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Two friends planning a day off.",
            "lines": [
                {
                    "who": "a",
                    "jp": "あした、やすみですね。なにがしたいですか。",
                    "en": "Tomorrow's a day off. What do you want to do?",
                    "gloss": "やすみ = day off"
                },
                {
                    "who": "b",
                    "jp": "うみにいきたいです！",
                    "en": "I want to go to the sea!"
                },
                {
                    "who": "a",
                    "jp": "いいですね。わたしは、おいしいものがたべたいです。",
                    "en": "Nice. I want to eat something tasty.",
                    "gloss": "もの = thing(s)"
                },
                {
                    "who": "b",
                    "jp": "じゃあ、うみで、すしをたべましょう。",
                    "en": "Then let's eat sushi at the sea.",
                    "gloss": "〜ましょう = let's"
                },
                {
                    "who": "a",
                    "jp": "いいですね！",
                    "en": "Sounds good!"
                }
            ]
        },
        "questions": [
            {
                "q": "Where does B want to go?",
                "choices": [
                    "A hot spring",
                    "The sea",
                    "The mountains"
                ],
                "answer": 1
            },
            {
                "q": "What does A want?",
                "choices": [
                    "To buy a bag",
                    "To rest at home",
                    "To eat something tasty"
                ],
                "answer": 2
            }
        ],
        "speak": [
            {
                "say": "しゅうまつ、なにがしたいですか。",
                "situation": "Say what you want to do this weekend.",
                "hint": "＿にいきたいです。／＿がしたいです。",
                "expect": [
                    "*たいです*",
                    "*たい*"
                ]
            },
            {
                "say": "なにがほしいですか。",
                "situation": "Say something you want.",
                "hint": "＿がほしいです。",
                "expect": [
                    "*ほしい*"
                ]
            },
            {
                "say": "つかれましたか。",
                "situation": "You're tired. Say so, and that you want to rest.",
                "hint": "はい、つかれました。やすみたいです。",
                "expect": [
                    "*つかれ*",
                    "*やすみたい*"
                ]
            }
        ]
    },
    {
        "id": "u14",
        "title": "Requests",
        "title_jp": "おねがい",
        "goal": "Ask people to do things, and ask them not to.",
        "phrases": [
            {
                "id": "u14.matte",
                "jp": "すこしまってください。",
                "en": "Please wait a moment.",
                "note": "て-form ＋ ください = please do."
            },
            {
                "id": "u14.mite",
                "jp": "これをみてください。",
                "en": "Please look at this."
            },
            {
                "id": "u14.kaite",
                "jp": "ここに、なまえをかいてください。",
                "en": "Please write your name here."
            },
            {
                "id": "u14.hanashite",
                "jp": "ゆっくりはなしてください。",
                "en": "Please speak slowly."
            },
            {
                "id": "u14.oshiete",
                "jp": "おしえてください。",
                "en": "Please tell me. / Please teach me."
            },
            {
                "id": "u14.tabenaide",
                "jp": "たべないでください。",
                "en": "Please don't eat it.",
                "note": "ないで ＋ ください = please don't."
            }
        ],
        "words": [
            {
                "id": "u14w.matte",
                "jp": "まって",
                "ro": "matte",
                "en": "wait (て-form)"
            },
            {
                "id": "u14w.mite",
                "jp": "みて",
                "ro": "mite",
                "en": "look (て-form)"
            },
            {
                "id": "u14w.kaite",
                "jp": "かいて",
                "ro": "kaite",
                "en": "write (て-form)"
            },
            {
                "id": "u14w.hanashite",
                "jp": "はなして",
                "ro": "hanashite",
                "en": "speak (て-form)"
            },
            {
                "id": "u14w.oshiete",
                "jp": "おしえて",
                "ro": "oshiete",
                "en": "tell, teach (て-form)"
            },
            {
                "id": "u14w.kiite",
                "jp": "きいて",
                "ro": "kiite",
                "en": "listen, ask (て-form)"
            },
            {
                "id": "u14w.yonde",
                "jp": "よんで",
                "ro": "yonde",
                "en": "read, call (て-form)"
            },
            {
                "id": "u14w.tatte",
                "jp": "たって",
                "ro": "tatte",
                "en": "stand up (て-form)"
            },
            {
                "id": "u14w.suwatte",
                "jp": "すわって",
                "ro": "suwatte",
                "en": "sit down (て-form)"
            },
            {
                "id": "u14w.akete",
                "jp": "あけて",
                "ro": "akete",
                "en": "open (て-form)"
            },
            {
                "id": "u14w.shimete",
                "jp": "しめて",
                "ro": "shimete",
                "en": "close (て-form)"
            },
            {
                "id": "u14w.mado",
                "jp": "まど",
                "ro": "mado",
                "en": "window"
            },
            {
                "id": "u14w.doa",
                "jp": "ドア",
                "ro": "doa",
                "en": "door"
            },
            {
                "id": "u14w.denwa",
                "jp": "でんわ",
                "ro": "denwa",
                "en": "phone"
            },
            {
                "id": "u14w.bangou",
                "jp": "ばんごう",
                "ro": "bangou",
                "en": "number"
            },
            {
                "id": "u14w.mochiron",
                "jp": "もちろん",
                "ro": "mochiron",
                "en": "of course"
            }
        ],
        "grammar": [
            {
                "id": "u14g.te",
                "title": "Please do: て-form ＋ ください",
                "rule": "て-form ＋ ください = please (do). みます → みて, かきます → かいて.",
                "explain": [
                    "To ask someone to do something, use the verb's て-form with ください: みてください (please look).",
                    "The て-form has a few patterns; for now learn these as words: みて, まって, かいて, よんで, はなして, おしえて, すわって. A later unit covers the rules."
                ],
                "examples": [
                    {
                        "jp": "これをみてください。",
                        "en": "Please look at this."
                    },
                    {
                        "jp": "すこしまってください。",
                        "en": "Please wait a moment."
                    },
                    {
                        "jp": "ここにすわってください。",
                        "en": "Please sit here."
                    },
                    {
                        "jp": "まどをあけてください。",
                        "en": "Please open the window."
                    }
                ]
            },
            {
                "id": "u14g.naide",
                "title": "Please don't: ＿ないでください",
                "rule": "ない-form ＋ でください = please don't. たべない → たべないでください.",
                "explain": [
                    "For please don't, use the ない form (not doing) with でください: たべないでください, みないでください.",
                    "Soften any request with すみません first; agree to one with はい or もちろん (of course)."
                ],
                "examples": [
                    {
                        "jp": "たべないでください。",
                        "en": "Please don't eat it."
                    },
                    {
                        "jp": "みないでください。",
                        "en": "Please don't look."
                    },
                    {
                        "jp": "ここで、たべないでください。",
                        "en": "Please don't eat here."
                    },
                    {
                        "jp": "はい、もちろん。",
                        "en": "Yes, of course."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Ask them to look at this.",
                "choices": [
                    "これをみてください。",
                    "これをみますください。",
                    "これがみてください。"
                ],
                "answer": 0,
                "explain": "て-form ＋ ください."
            },
            {
                "q": "Ask them to wait a moment.",
                "choices": [
                    "すこしまってください。",
                    "すこしまちますください。",
                    "すこしまってです。"
                ],
                "answer": 0
            },
            {
                "q": "Ask them to speak slowly.",
                "choices": [
                    "ゆっくりはなしてください。",
                    "ゆっくりはなしますください。",
                    "ゆっくりはなしてくださいか。"
                ],
                "answer": 0
            },
            {
                "q": "Ask them to write it here.",
                "choices": [
                    "ここにかいてください。",
                    "ここにかきてください。",
                    "ここでかいてです。"
                ],
                "answer": 0,
                "explain": "かきます → かいて."
            },
            {
                "q": "Ask them not to eat it.",
                "choices": [
                    "たべないでください。",
                    "たべませんください。",
                    "たべてないください。"
                ],
                "answer": 0,
                "explain": "ない ＋ でください = please don't."
            },
            {
                "q": "Ask them to sit down.",
                "choices": [
                    "すわってください。",
                    "すわりてください。",
                    "すわってます。"
                ],
                "answer": 0
            },
            {
                "q": "Someone asks you to wait. Agree.",
                "say": "すこしまってください。",
                "choices": [
                    "はい、もちろん。",
                    "いいえ、もちろん。",
                    "はい、まってください。"
                ],
                "answer": 0
            },
            {
                "q": "Ask them to teach you Japanese.",
                "choices": [
                    "にほんごをおしえてください。",
                    "にほんごをおしえますください。",
                    "にほんごがおしえてください。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "At a doctor's reception desk.",
            "lines": [
                {
                    "who": "a",
                    "jp": "こんにちは。ここに、なまえをかいてください。",
                    "en": "Hello. Please write your name here."
                },
                {
                    "who": "b",
                    "jp": "すみません、ゆっくりはなしてください。",
                    "en": "Sorry, please speak slowly."
                },
                {
                    "who": "a",
                    "jp": "あ、はい。ここに、なまえを、かいてください。",
                    "en": "Oh, sure. Please. Write. Your name. Here."
                },
                {
                    "who": "b",
                    "jp": "わかりました。",
                    "en": "Got it.",
                    "gloss": "わかりました = understood, OK"
                },
                {
                    "who": "a",
                    "jp": "ありがとうございます。そこにすわって、すこしまってください。",
                    "en": "Thank you. Please sit there and wait a moment."
                },
                {
                    "who": "b",
                    "jp": "はい。",
                    "en": "OK."
                }
            ]
        },
        "questions": [
            {
                "q": "What does the receptionist ask first?",
                "choices": [
                    "To write a name",
                    "To show a card",
                    "To wait outside"
                ],
                "answer": 0
            },
            {
                "q": "What does B ask for?",
                "choices": [
                    "Water",
                    "English",
                    "Slower speech"
                ],
                "answer": 2
            },
            {
                "q": "What should B do at the end?",
                "choices": [
                    "Sit and wait",
                    "Go home",
                    "Come back tomorrow"
                ],
                "answer": 0
            }
        ],
        "speak": [
            {
                "say": "ここに、なまえをかいてください。",
                "situation": "You didn't catch it. Ask them to speak slowly.",
                "hint": "ゆっくりはなしてください。",
                "expect": [
                    "*ゆっくり*"
                ]
            },
            {
                "say": "なにか、しつもんはありますか。",
                "situation": "Ask them to teach you how to say \"cat\".",
                "hint": "「cat」をおしえてください。／「cat」は、にほんごでなんですか。",
                "expect": [
                    "*おしえて*",
                    "*にほんごで*"
                ]
            },
            {
                "say": "これ、たべてもいいですか。",
                "situation": "Your friend wants to eat your cake. Ask them not to.",
                "hint": "たべないでください。",
                "expect": [
                    "*ないで*"
                ]
            }
        ]
    },
    {
        "id": "u15",
        "title": "Invitations",
        "title_jp": "さそう",
        "goal": "Invite people, say yes, and say no politely.",
        "phrases": [
            {
                "id": "u15.mimasenka",
                "jp": "いっしょに、えいがをみませんか。",
                "en": "Would you like to watch a movie together?",
                "note": "〜ませんか = won't you…? A soft invitation."
            },
            {
                "id": "u15.ikimashou",
                "jp": "いきましょう！",
                "en": "Let's go!",
                "note": "〜ましょう = let's."
            },
            {
                "id": "u15.iidesune",
                "jp": "いいですね。",
                "en": "Sounds good."
            },
            {
                "id": "u15.chotto",
                "jp": "あしたは、ちょっと…。",
                "en": "Tomorrow is a bit… (difficult).",
                "note": "Trailing off after ちょっと is the polite way to say no."
            },
            {
                "id": "u15.itsu",
                "jp": "いつがいいですか。",
                "en": "When is good for you?"
            },
            {
                "id": "u15.kondo",
                "jp": "また、こんど。",
                "en": "Next time, then."
            }
        ],
        "words": [
            {
                "id": "u15w.isshoni",
                "jp": "いっしょに",
                "ro": "issho ni",
                "en": "together"
            },
            {
                "id": "u15w.itsu",
                "jp": "いつ",
                "ro": "itsu",
                "en": "when"
            },
            {
                "id": "u15w.kondo",
                "jp": "こんど",
                "ro": "kondo",
                "en": "next time"
            },
            {
                "id": "u15w.hima",
                "jp": "ひま",
                "ro": "hima",
                "en": "free (not busy)"
            },
            {
                "id": "u15w.isogashii",
                "jp": "いそがしい",
                "ro": "isogashii",
                "en": "busy"
            },
            {
                "id": "u15w.zannen",
                "jp": "ざんねん",
                "ro": "zannen",
                "en": "too bad, a shame"
            },
            {
                "id": "u15w.paatii",
                "jp": "パーティー",
                "ro": "paatii",
                "en": "party"
            },
            {
                "id": "u15w.karaoke",
                "jp": "カラオケ",
                "ro": "karaoke",
                "en": "karaoke"
            },
            {
                "id": "u15w.konsaato",
                "jp": "コンサート",
                "ro": "konsaato",
                "en": "concert"
            },
            {
                "id": "u15w.shokuji",
                "jp": "しょくじ",
                "ro": "shokuji",
                "en": "a meal"
            },
            {
                "id": "u15w.yotei",
                "jp": "よてい",
                "ro": "yotei",
                "en": "plans"
            },
            {
                "id": "u15w.youji",
                "jp": "ようじ",
                "ro": "youji",
                "en": "something to do, an errand"
            },
            {
                "id": "u15w.doudesuka",
                "jp": "どうですか",
                "ro": "dou desu ka",
                "en": "how about…?"
            },
            {
                "id": "u15w.jaa",
                "jp": "じゃあ",
                "ro": "jaa",
                "en": "well then"
            },
            {
                "id": "u15w.mata",
                "jp": "また",
                "ro": "mata",
                "en": "again"
            },
            {
                "id": "u15w.zehi",
                "jp": "ぜひ",
                "ro": "zehi",
                "en": "definitely, I'd love to"
            }
        ],
        "grammar": [
            {
                "id": "u15g.masenka",
                "title": "Won't you…? ＿ませんか",
                "rule": "ます → ませんか = won't you…? (an invitation). ます → ましょう = let's.",
                "explain": [
                    "Asking in the negative is the polite way to invite: えいがをみませんか (won't you watch a movie?). It leaves room to say no.",
                    "Once you agree, switch to ましょう (let's): いきましょう！"
                ],
                "examples": [
                    {
                        "jp": "いっしょに、しょくじをしませんか。",
                        "en": "Shall we have a meal together?"
                    },
                    {
                        "jp": "カラオケにいきませんか。",
                        "en": "Want to go to karaoke?"
                    },
                    {
                        "jp": "いいですね。いきましょう！",
                        "en": "Sounds good. Let's go!"
                    },
                    {
                        "jp": "なんじにあいましょうか。",
                        "en": "What time shall we meet?"
                    }
                ]
            },
            {
                "id": "u15g.chotto",
                "title": "Saying no softly: ちょっと…",
                "rule": "Day ＋ は、ちょっと… = that day is difficult. No flat no.",
                "explain": [
                    "Japanese rarely answers an invitation with a flat いいえ. Name the problem day and trail off: あしたは、ちょっと….",
                    "Add a reason or a next time to stay friendly: ようじがあります (I have something on), また、こんど."
                ],
                "examples": [
                    {
                        "jp": "あしたは、ちょっと…。",
                        "en": "Tomorrow is a bit…"
                    },
                    {
                        "jp": "すみません、ようじがあります。",
                        "en": "Sorry, I have something on."
                    },
                    {
                        "jp": "ざんねんです。",
                        "en": "That's a shame."
                    },
                    {
                        "jp": "また、こんど。",
                        "en": "Next time, then."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Invite them to karaoke.",
                "choices": [
                    "カラオケにいきませんか。",
                    "カラオケにいきません。",
                    "カラオケにいきますか、いいえ。"
                ],
                "answer": 0,
                "explain": "ませんか = won't you…?"
            },
            {
                "q": "Agree enthusiastically.",
                "say": "カラオケにいきませんか。",
                "choices": [
                    "いいですね。いきましょう！",
                    "いいえ、いきましょう。",
                    "いいですね。いきません。"
                ],
                "answer": 0,
                "explain": "ましょう = let's."
            },
            {
                "q": "You're busy tomorrow. Decline politely.",
                "say": "あした、えいがをみませんか。",
                "choices": [
                    "あしたは、ちょっと…。",
                    "いいえ、いきません！",
                    "あしたは、いいですね。"
                ],
                "answer": 0,
                "explain": "Trail off after ちょっと."
            },
            {
                "q": "Ask when is good.",
                "choices": [
                    "いつがいいですか。",
                    "いつですか、いい。",
                    "なにがいいですか。"
                ],
                "answer": 0
            },
            {
                "q": "Suggest next time.",
                "choices": [
                    "また、こんど。",
                    "また、きのう。",
                    "こんど、ちょっと。"
                ],
                "answer": 0
            },
            {
                "q": "Ask: shall we eat together?",
                "choices": [
                    "いっしょに、しょくじをしませんか。",
                    "いっしょに、しょくじをしましたか。",
                    "いっしょに、しょくじですか。"
                ],
                "answer": 0
            },
            {
                "q": "Say you have something on.",
                "choices": [
                    "ようじがあります。",
                    "ようじがいます。",
                    "ようじをします。"
                ],
                "answer": 0,
                "explain": "Things and events take あります."
            },
            {
                "q": "Your friend can't come. Say that's a shame.",
                "say": "すみません、いそがしいです。",
                "choices": [
                    "ざんねんです。",
                    "よかったです。",
                    "いいですね。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Three friends making weekend plans.",
            "lines": [
                {
                    "who": "a",
                    "jp": "しゅうまつ、いっしょにカラオケにいきませんか。",
                    "en": "Want to go to karaoke together this weekend?"
                },
                {
                    "who": "b",
                    "jp": "いいですね！いきましょう。",
                    "en": "Sounds great! Let's go."
                },
                {
                    "who": "c",
                    "jp": "すみません、どようびは、ちょっと…。",
                    "en": "Sorry, Saturday is a bit…",
                    "gloss": "どようび = Saturday"
                },
                {
                    "who": "a",
                    "jp": "そうですか。にちようびは、どうですか。",
                    "en": "I see. How about Sunday?",
                    "gloss": "にちようび = Sunday"
                },
                {
                    "who": "c",
                    "jp": "にちようびは、ひまです！",
                    "en": "I'm free on Sunday!"
                },
                {
                    "who": "b",
                    "jp": "じゃあ、にちようびにいきましょう。",
                    "en": "Then let's go on Sunday."
                }
            ]
        },
        "questions": [
            {
                "q": "What's the plan?",
                "choices": [
                    "A movie",
                    "Karaoke",
                    "A meal"
                ],
                "answer": 1
            },
            {
                "q": "Why does the third friend hesitate?",
                "choices": [
                    "They're sick",
                    "Saturday doesn't work",
                    "They don't like karaoke"
                ],
                "answer": 1
            },
            {
                "q": "When will they go?",
                "choices": [
                    "Saturday",
                    "Sunday",
                    "Tomorrow"
                ],
                "answer": 1
            }
        ],
        "speak": [
            {
                "say": "しゅうまつ、ひまですか。",
                "situation": "You're free. Invite them to a movie.",
                "hint": "はい。えいがをみませんか。",
                "expect": [
                    "*ませんか*"
                ]
            },
            {
                "say": "あした、カラオケにいきませんか。",
                "situation": "You're busy tomorrow. Decline softly.",
                "hint": "あしたは、ちょっと…。",
                "expect": [
                    "*ちょっと*",
                    "*ようじ*",
                    "*いそがしい*"
                ]
            },
            {
                "say": "いっしょに、しょくじをしませんか。",
                "situation": "Accept: let's do it.",
                "hint": "いいですね。しましょう！",
                "expect": [
                    "*ましょう*",
                    "いいですね*"
                ]
            }
        ]
    },
    {
        "id": "u16",
        "title": "Where things are",
        "title_jp": "どこにありますか",
        "goal": "Say where things and people are: on, under, in, next to.",
        "phrases": [
            {
                "id": "u16.ue",
                "jp": "つくえのうえに、ほんがあります。",
                "en": "There's a book on the desk.",
                "note": "Place ＋ に ＋ thing ＋ があります."
            },
            {
                "id": "u16.shita",
                "jp": "いすのしたに、ねこがいます。",
                "en": "There's a cat under the chair."
            },
            {
                "id": "u16.kagi",
                "jp": "かぎは、どこにありますか。",
                "en": "Where are the keys?"
            },
            {
                "id": "u16.naka",
                "jp": "かばんのなかです。",
                "en": "In the bag."
            },
            {
                "id": "u16.mae",
                "jp": "えきのまえで、まっています。",
                "en": "I'm waiting in front of the station.",
                "note": "まっています = I'm waiting."
            },
            {
                "id": "u16.tonari",
                "jp": "ぎんこうのとなりです。",
                "en": "It's next to the bank."
            }
        ],
        "words": [
            {
                "id": "u16w.ue",
                "jp": "うえ",
                "ro": "ue",
                "en": "on, above"
            },
            {
                "id": "u16w.shita",
                "jp": "した",
                "ro": "shita",
                "en": "under, below"
            },
            {
                "id": "u16w.naka",
                "jp": "なか",
                "ro": "naka",
                "en": "inside"
            },
            {
                "id": "u16w.soto",
                "jp": "そと",
                "ro": "soto",
                "en": "outside"
            },
            {
                "id": "u16w.mae",
                "jp": "まえ",
                "ro": "mae",
                "en": "in front"
            },
            {
                "id": "u16w.ushiro",
                "jp": "うしろ",
                "ro": "ushiro",
                "en": "behind"
            },
            {
                "id": "u16w.tonari",
                "jp": "となり",
                "ro": "tonari",
                "en": "next to"
            },
            {
                "id": "u16w.chikaku",
                "jp": "ちかく",
                "ro": "chikaku",
                "en": "near"
            },
            {
                "id": "u16w.tsukue",
                "jp": "つくえ",
                "ro": "tsukue",
                "en": "desk"
            },
            {
                "id": "u16w.isu",
                "jp": "いす",
                "ro": "isu",
                "en": "chair"
            },
            {
                "id": "u16w.kagi",
                "jp": "かぎ",
                "ro": "kagi",
                "en": "key"
            },
            {
                "id": "u16w.heya",
                "jp": "へや",
                "ro": "heya",
                "en": "room"
            },
            {
                "id": "u16w.beddo",
                "jp": "ベッド",
                "ro": "beddo",
                "en": "bed"
            },
            {
                "id": "u16w.reizouko",
                "jp": "れいぞうこ",
                "ro": "reizouko",
                "en": "fridge"
            },
            {
                "id": "u16w.hako",
                "jp": "はこ",
                "ro": "hako",
                "en": "box"
            },
            {
                "id": "u16w.saifu",
                "jp": "さいふ",
                "ro": "saifu",
                "en": "wallet"
            }
        ],
        "grammar": [
            {
                "id": "u16g.ni",
                "title": "Place ＋ に ＋ ＿があります / います",
                "rule": "Place に thing が あります (things) / います (people, animals).",
                "explain": [
                    "To say where something is, start with the place and に: つくえのうえに、ほんがあります。",
                    "Same split as unit 12: あります for things, います for people and animals."
                ],
                "examples": [
                    {
                        "jp": "つくえのうえに、ほんがあります。",
                        "en": "There's a book on the desk."
                    },
                    {
                        "jp": "いすのしたに、ねこがいます。",
                        "en": "There's a cat under the chair."
                    },
                    {
                        "jp": "へやに、ともだちがいます。",
                        "en": "My friend is in the room."
                    },
                    {
                        "jp": "れいぞうこに、ケーキがあります。",
                        "en": "There's cake in the fridge."
                    }
                ]
            },
            {
                "id": "u16g.position",
                "title": "Position words with の",
                "rule": "Thing ＋ の ＋ うえ / した / なか / まえ / うしろ / となり.",
                "explain": [
                    "Position words come after the reference thing and の: つくえのうえ (on the desk), えきのまえ (in front of the station).",
                    "Ask with どこにありますか or どこにいますか; a short answer is enough: かばんのなかです。"
                ],
                "examples": [
                    {
                        "jp": "かばんのなかです。",
                        "en": "It's in the bag."
                    },
                    {
                        "jp": "えきのまえです。",
                        "en": "It's in front of the station."
                    },
                    {
                        "jp": "ぎんこうのとなりです。",
                        "en": "It's next to the bank."
                    },
                    {
                        "jp": "ドアのうしろに、いぬがいます。",
                        "en": "There's a dog behind the door."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say the book is on the desk.",
                "choices": [
                    "つくえのうえに、ほんがあります。",
                    "つくえのうえに、ほんがいます。",
                    "ほんのうえに、つくえがあります。"
                ],
                "answer": 0,
                "explain": "Things: あります."
            },
            {
                "q": "Say the cat is under the chair.",
                "choices": [
                    "いすのしたに、ねこがいます。",
                    "いすのしたに、ねこがあります。",
                    "ねこのしたに、いすがいます。"
                ],
                "answer": 0,
                "explain": "Animals: います."
            },
            {
                "q": "Ask where the keys are.",
                "choices": [
                    "かぎは、どこにありますか。",
                    "かぎは、どこにいますか。",
                    "かぎに、どこがありますか。"
                ],
                "answer": 0
            },
            {
                "q": "The wallet is in the bag.",
                "say": "さいふは、どこですか。",
                "choices": [
                    "かばんのなかです。",
                    "かばんのうえです。",
                    "かばんのそとです。"
                ],
                "answer": 0
            },
            {
                "q": "Say it's next to the bank.",
                "choices": [
                    "ぎんこうのとなりです。",
                    "ぎんこうのまえです。",
                    "ぎんこうのしたです。"
                ],
                "answer": 0,
                "explain": "となり = next to."
            },
            {
                "q": "Say you're waiting in front of the station.",
                "choices": [
                    "えきのまえで、まっています。",
                    "えきのうしろで、まっています。",
                    "えきのなかで、まっています。"
                ],
                "answer": 0
            },
            {
                "q": "Say your friend is in the room.",
                "choices": [
                    "へやに、ともだちがいます。",
                    "へやに、ともだちがあります。",
                    "ともだちに、へやがいます。"
                ],
                "answer": 0
            },
            {
                "q": "Say the dog is behind the door.",
                "choices": [
                    "ドアのうしろに、いぬがいます。",
                    "ドアのまえに、いぬがいます。",
                    "いぬのうしろに、ドアがいます。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Getting ready to leave; the keys are missing.",
            "lines": [
                {
                    "who": "a",
                    "jp": "あれ？かぎは、どこですか。",
                    "en": "Huh? Where are the keys?",
                    "gloss": "あれ？ = huh?"
                },
                {
                    "who": "b",
                    "jp": "つくえのうえに、ありませんか。",
                    "en": "Aren't they on the desk?"
                },
                {
                    "who": "a",
                    "jp": "ありません。",
                    "en": "They're not there."
                },
                {
                    "who": "b",
                    "jp": "じゃあ、かばんのなかは？",
                    "en": "Then what about in your bag?"
                },
                {
                    "who": "a",
                    "jp": "あ、ありました！",
                    "en": "Oh, here they are!",
                    "gloss": "ありました = (oh,) there it is"
                },
                {
                    "who": "b",
                    "jp": "よかった。じゃあ、いきましょう。",
                    "en": "Good. Let's go, then."
                }
            ]
        },
        "questions": [
            {
                "q": "What is missing?",
                "choices": [
                    "The wallet",
                    "The keys",
                    "The bag"
                ],
                "answer": 1
            },
            {
                "q": "Where were they in the end?",
                "choices": [
                    "On the desk",
                    "Under the chair",
                    "In the bag"
                ],
                "answer": 2
            }
        ],
        "speak": [
            {
                "say": "かぎは、どこですか。",
                "situation": "The keys are on the desk. Tell them.",
                "hint": "つくえのうえです。",
                "expect": [
                    "*うえ*"
                ]
            },
            {
                "say": "ねこは、どこにいますか。",
                "situation": "The cat is under the bed. Say so.",
                "hint": "ベッドのしたにいます。",
                "expect": [
                    "*した*"
                ]
            },
            {
                "say": "いま、どこですか。",
                "situation": "You're in front of the station. Say you're waiting there.",
                "hint": "えきのまえで、まっています。",
                "expect": [
                    "*まえ*"
                ]
            }
        ]
    },
    {
        "id": "u17",
        "title": "My day",
        "title_jp": "いちにち",
        "goal": "Describe your day: when you get up, work, and go to bed.",
        "phrases": [
            {
                "id": "u17.okimasu",
                "jp": "まいあさ、しちじにおきます。",
                "en": "I get up at seven every morning.",
                "note": "Clock time ＋ に = at."
            },
            {
                "id": "u17.karamade",
                "jp": "くじからごじまで、はたらきます。",
                "en": "I work from nine to five.",
                "note": "から = from, まで = until."
            },
            {
                "id": "u17.nemasu",
                "jp": "なんじにねますか。",
                "en": "What time do you go to bed?"
            },
            {
                "id": "u17.sorekara",
                "jp": "それから、あさごはんをたべます。",
                "en": "Then I eat breakfast.",
                "note": "それから = and then."
            },
            {
                "id": "u17.demasu",
                "jp": "はちじに、うちをでます。",
                "en": "I leave home at eight.",
                "note": "＿をでます = leave ＿."
            },
            {
                "id": "u17.tokidoki",
                "jp": "ときどき、ジムにいきます。",
                "en": "Sometimes I go to the gym.",
                "note": "ときどき = sometimes."
            }
        ],
        "words": [
            {
                "id": "u17w.hatarakimasu",
                "jp": "はたらきます",
                "ro": "hatarakimasu",
                "en": "work"
            },
            {
                "id": "u17w.demasu",
                "jp": "でます",
                "ro": "demasu",
                "en": "leave, go out"
            },
            {
                "id": "u17w.shawaa",
                "jp": "シャワー",
                "ro": "shawaa",
                "en": "shower"
            },
            {
                "id": "u17w.abimasu",
                "jp": "あびます",
                "ro": "abimasu",
                "en": "take (a shower)"
            },
            {
                "id": "u17w.sorekara",
                "jp": "それから",
                "ro": "sorekara",
                "en": "and then"
            },
            {
                "id": "u17w.tokidoki",
                "jp": "ときどき",
                "ro": "tokidoki",
                "en": "sometimes"
            },
            {
                "id": "u17w.itsumo",
                "jp": "いつも",
                "ro": "itsumo",
                "en": "always"
            },
            {
                "id": "u17w.yoku",
                "jp": "よく",
                "ro": "yoku",
                "en": "often"
            },
            {
                "id": "u17w.zenzen",
                "jp": "ぜんぜん",
                "ro": "zenzen",
                "en": "not at all (with a negative)"
            },
            {
                "id": "u17w.jimu",
                "jp": "ジム",
                "ro": "jimu",
                "en": "gym"
            },
            {
                "id": "u17w.goji",
                "jp": "ごじ",
                "ro": "goji",
                "en": "five o'clock"
            },
            {
                "id": "u17w.hachiji",
                "jp": "はちじ",
                "ro": "hachiji",
                "en": "eight o'clock"
            },
            {
                "id": "u17w.juuji",
                "jp": "じゅうじ",
                "ro": "juuji",
                "en": "ten o'clock"
            },
            {
                "id": "u17w.made",
                "jp": "まで",
                "ro": "made",
                "en": "until"
            },
            {
                "id": "u17w.maiban",
                "jp": "まいばん",
                "ro": "maiban",
                "en": "every night"
            },
            {
                "id": "u17w.osoku",
                "jp": "おそく",
                "ro": "osoku",
                "en": "late"
            }
        ],
        "grammar": [
            {
                "id": "u17g.ni",
                "title": "At a time: ＿じに",
                "rule": "Clock time ＋ に ＋ verb = at that time. まいあさ, きょう, あした take no に.",
                "explain": [
                    "Put に after a clock time: しちじにおきます (I get up at 7). Words like まいあさ, きょう and あした don't take に.",
                    "Ask with なんじに: なんじにねますか。"
                ],
                "examples": [
                    {
                        "jp": "しちじにおきます。",
                        "en": "I get up at seven."
                    },
                    {
                        "jp": "じゅうじにねます。",
                        "en": "I go to bed at ten."
                    },
                    {
                        "jp": "なんじにねますか。",
                        "en": "What time do you go to bed?"
                    },
                    {
                        "jp": "まいあさ、はちじにうちをでます。",
                        "en": "I leave home at eight every morning."
                    }
                ]
            },
            {
                "id": "u17g.karamade",
                "title": "From… until…: から まで, and how often",
                "rule": "A から B まで = from A until B. いつも, よく, ときどき, ぜんぜん say how often.",
                "explain": [
                    "から means from and まで means until: くじからごじまで (from 9 to 5). It works for places too.",
                    "How-often words go near the front: いつも (always), よく (often), ときどき (sometimes), ぜんぜん with a negative (never)."
                ],
                "examples": [
                    {
                        "jp": "くじからごじまで、はたらきます。",
                        "en": "I work from nine to five."
                    },
                    {
                        "jp": "いつも、しちじにおきます。",
                        "en": "I always get up at seven."
                    },
                    {
                        "jp": "ときどき、ジムにいきます。",
                        "en": "Sometimes I go to the gym."
                    },
                    {
                        "jp": "ぜんぜん、テレビをみません。",
                        "en": "I never watch TV."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you get up at seven.",
                "choices": [
                    "しちじにおきます。",
                    "しちじをおきます。",
                    "しちじがおきます。"
                ],
                "answer": 0,
                "explain": "Clock time ＋ に."
            },
            {
                "q": "Ask what time they go to bed.",
                "choices": [
                    "なんじにねますか。",
                    "なんじがねますか。",
                    "なんじですか、ねます。"
                ],
                "answer": 0
            },
            {
                "q": "Say you work from nine to five.",
                "choices": [
                    "くじからごじまで、はたらきます。",
                    "くじまでごじから、はたらきます。",
                    "くじにごじに、はたらきます。"
                ],
                "answer": 0,
                "explain": "から = from, まで = until."
            },
            {
                "q": "Say you leave home at eight.",
                "choices": [
                    "はちじに、うちをでます。",
                    "はちじに、うちにでます。",
                    "はちじを、うちをでます。"
                ],
                "answer": 0,
                "explain": "＿をでます = leave ＿."
            },
            {
                "q": "Say you sometimes go to the gym.",
                "choices": [
                    "ときどき、ジムにいきます。",
                    "いつも、ジムにいきません。",
                    "ときどき、ジムをいきます。"
                ],
                "answer": 0
            },
            {
                "q": "Say you never watch TV.",
                "choices": [
                    "ぜんぜん、テレビをみません。",
                    "ぜんぜん、テレビをみます。",
                    "いつも、テレビをみません。"
                ],
                "answer": 0,
                "explain": "ぜんぜん goes with a negative."
            },
            {
                "q": "Say you always get up at six.",
                "choices": [
                    "いつも、ろくじにおきます。",
                    "いつも、ろくじをおきます。",
                    "いつもに、ろくじおきます。"
                ],
                "answer": 0
            },
            {
                "q": "Say: then I eat breakfast.",
                "choices": [
                    "それから、あさごはんをたべます。",
                    "それから、あさごはんがたべます。",
                    "あさごはんを、それからです。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Two coworkers, Ken and Mika, compare their mornings.",
            "lines": [
                {
                    "who": "a",
                    "jp": "まいあさ、なんじにおきますか。",
                    "en": "What time do you get up every morning?"
                },
                {
                    "who": "b",
                    "jp": "ろくじにおきます。それから、ジムにいきます。",
                    "en": "I get up at six. Then I go to the gym."
                },
                {
                    "who": "a",
                    "jp": "え、まいにちですか。",
                    "en": "What, every day?"
                },
                {
                    "who": "b",
                    "jp": "いいえ、ときどきです。ケンさんは？",
                    "en": "No, sometimes. What about you, Ken?"
                },
                {
                    "who": "a",
                    "jp": "わたしは、はちじにおきます。いつも、おそくねますから。",
                    "en": "I get up at eight. I always go to bed late.",
                    "gloss": "から = because"
                },
                {
                    "who": "b",
                    "jp": "ああ、なるほど。",
                    "en": "Ah, I see.",
                    "gloss": "なるほど = I see, that makes sense"
                }
            ]
        },
        "questions": [
            {
                "q": "What time does Mika get up?",
                "choices": [
                    "Seven",
                    "Eight",
                    "Six"
                ],
                "answer": 2
            },
            {
                "q": "Does Mika go to the gym every day?",
                "choices": [
                    "Yes, every day",
                    "No, sometimes",
                    "Never"
                ],
                "answer": 1
            },
            {
                "q": "Why does Ken get up late?",
                "choices": [
                    "He works at night",
                    "He hates mornings",
                    "He always goes to bed late"
                ],
                "answer": 2
            }
        ],
        "speak": [
            {
                "say": "まいあさ、なんじにおきますか。",
                "situation": "Say what time you get up.",
                "hint": "＿じにおきます。",
                "expect": [
                    "*じにおきます*",
                    "*おきます*"
                ]
            },
            {
                "say": "なんじから、なんじまで、はたらきますか。",
                "situation": "Say your work or school hours.",
                "hint": "＿じから＿じまでです。",
                "expect": [
                    "*から*まで*"
                ]
            },
            {
                "say": "よく、ジムにいきますか。",
                "situation": "Say how often you go.",
                "hint": "ときどきいきます。／ぜんぜんいきません。",
                "expect": [
                    "*いき*"
                ]
            }
        ]
    },
    {
        "id": "u18",
        "title": "Getting around",
        "title_jp": "のりもの",
        "goal": "Say how you travel and how long it takes, and ask the way.",
        "phrases": [
            {
                "id": "u18.densha",
                "jp": "でんしゃで、がっこうにいきます。",
                "en": "I go to school by train.",
                "note": "Vehicle ＋ で = by."
            },
            {
                "id": "u18.kakarimasu",
                "jp": "どのくらい、かかりますか。",
                "en": "How long does it take?"
            },
            {
                "id": "u18.juppun",
                "jp": "じゅっぷんぐらいです。",
                "en": "About ten minutes.",
                "note": "ぐらい = about."
            },
            {
                "id": "u18.massugu",
                "jp": "このみちを、まっすぐです。",
                "en": "It's straight along this road."
            },
            {
                "id": "u18.noriba",
                "jp": "バスのりばは、どこですか。",
                "en": "Where's the bus stop?",
                "note": "のりば = place to get on."
            },
            {
                "id": "u18.aruite",
                "jp": "あるいて、いきます。",
                "en": "I'll walk.",
                "note": "あるいて = on foot."
            }
        ],
        "words": [
            {
                "id": "u18w.densha",
                "jp": "でんしゃ",
                "ro": "densha",
                "en": "train"
            },
            {
                "id": "u18w.basu",
                "jp": "バス",
                "ro": "basu",
                "en": "bus"
            },
            {
                "id": "u18w.takushii",
                "jp": "タクシー",
                "ro": "takushii",
                "en": "taxi"
            },
            {
                "id": "u18w.jitensha",
                "jp": "じてんしゃ",
                "ro": "jitensha",
                "en": "bicycle"
            },
            {
                "id": "u18w.hikouki",
                "jp": "ひこうき",
                "ro": "hikouki",
                "en": "airplane"
            },
            {
                "id": "u18w.chikatetsu",
                "jp": "ちかてつ",
                "ro": "chikatetsu",
                "en": "subway"
            },
            {
                "id": "u18w.aruite",
                "jp": "あるいて",
                "ro": "aruite",
                "en": "on foot"
            },
            {
                "id": "u18w.michi",
                "jp": "みち",
                "ro": "michi",
                "en": "road, way"
            },
            {
                "id": "u18w.massugu",
                "jp": "まっすぐ",
                "ro": "massugu",
                "en": "straight ahead"
            },
            {
                "id": "u18w.magarimasu",
                "jp": "まがります",
                "ro": "magarimasu",
                "en": "turn"
            },
            {
                "id": "u18w.kakarimasu",
                "jp": "かかります",
                "ro": "kakarimasu",
                "en": "take (time)"
            },
            {
                "id": "u18w.gofun",
                "jp": "ごふん",
                "ro": "gofun",
                "en": "five minutes"
            },
            {
                "id": "u18w.juppun",
                "jp": "じゅっぷん",
                "ro": "juppun",
                "en": "ten minutes"
            },
            {
                "id": "u18w.ichijikan",
                "jp": "いちじかん",
                "ro": "ichijikan",
                "en": "one hour"
            },
            {
                "id": "u18w.gurai",
                "jp": "ぐらい",
                "ro": "gurai",
                "en": "about"
            },
            {
                "id": "u18w.tooi",
                "jp": "とおい",
                "ro": "tooi",
                "en": "far"
            }
        ],
        "grammar": [
            {
                "id": "u18g.de",
                "title": "By: ＿で",
                "rule": "Vehicle ＋ で = by (vehicle). On foot is あるいて, with no で.",
                "explain": [
                    "で marks how you do something: でんしゃでいきます (go by train), バスでかえります (go home by bus).",
                    "Walking is the exception: あるいていきます."
                ],
                "examples": [
                    {
                        "jp": "でんしゃで、がっこうにいきます。",
                        "en": "I go to school by train."
                    },
                    {
                        "jp": "バスで、かえります。",
                        "en": "I go home by bus."
                    },
                    {
                        "jp": "ひこうきで、にほんにいきます。",
                        "en": "I'll go to Japan by plane."
                    },
                    {
                        "jp": "あるいて、いきます。",
                        "en": "I'll walk."
                    }
                ]
            },
            {
                "id": "u18g.kakaru",
                "title": "How long: どのくらい かかりますか",
                "rule": "どのくらいかかりますか = how long does it take? Answer: time ＋ ぐらいです (about).",
                "explain": [
                    "かかります means it takes (time or money). Ask with どのくらい, answer with a length of time and ぐらい (about).",
                    "Minutes: いっぷん, にふん, さんぷん, ごふん, じゅっぷん. Hours: いちじかん, にじかん. いちじかん is one hour; いちじ is one o'clock."
                ],
                "examples": [
                    {
                        "jp": "どのくらい、かかりますか。",
                        "en": "How long does it take?"
                    },
                    {
                        "jp": "じゅっぷんぐらいです。",
                        "en": "About ten minutes."
                    },
                    {
                        "jp": "でんしゃで、いちじかんぐらいかかります。",
                        "en": "It takes about an hour by train."
                    },
                    {
                        "jp": "ごふんぐらいです。",
                        "en": "About five minutes."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say you go to school by bus.",
                "choices": [
                    "バスで、がっこうにいきます。",
                    "バスに、がっこうでいきます。",
                    "バスを、がっこうにいきます。"
                ],
                "answer": 0,
                "explain": "で = by."
            },
            {
                "q": "Say you'll walk.",
                "choices": [
                    "あるいて、いきます。",
                    "あるいてで、いきます。",
                    "あるきで、いきます。"
                ],
                "answer": 0,
                "explain": "On foot: あるいて, no で."
            },
            {
                "q": "Ask how long it takes.",
                "choices": [
                    "どのくらい、かかりますか。",
                    "どのくらい、ありますか。",
                    "いくら、かかりますか。"
                ],
                "answer": 0,
                "explain": "いくら would ask how much money."
            },
            {
                "q": "Say about ten minutes.",
                "say": "どのくらい、かかりますか。",
                "choices": [
                    "じゅっぷんぐらいです。",
                    "じゅうふんぐらいです。",
                    "じゅっぷんまでです。"
                ],
                "answer": 0,
                "explain": "Ten minutes is じゅっぷん."
            },
            {
                "q": "Say it takes about an hour by train.",
                "choices": [
                    "でんしゃで、いちじかんぐらいかかります。",
                    "でんしゃに、いちじかんぐらいかかります。",
                    "でんしゃで、いちじぐらいかかります。"
                ],
                "answer": 0,
                "explain": "いちじかん = one hour; いちじ = one o'clock."
            },
            {
                "q": "Ask where the bus stop is.",
                "choices": [
                    "バスのりばは、どこですか。",
                    "バスのりばに、どこですか。",
                    "バスは、のりばですか。"
                ],
                "answer": 0
            },
            {
                "q": "Tell them it's straight ahead.",
                "say": "えきは、どっちですか。",
                "choices": [
                    "まっすぐです。",
                    "みぎです。",
                    "とおいです。"
                ],
                "answer": 0
            },
            {
                "q": "Say you'll go to Japan by plane.",
                "choices": [
                    "ひこうきで、にほんにいきます。",
                    "ひこうきに、にほんでいきます。",
                    "ひこうきを、にほんにいきます。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Asking a stranger the way to the station.",
            "lines": [
                {
                    "who": "a",
                    "jp": "すみません、えきは、とおいですか。",
                    "en": "Excuse me, is the station far?"
                },
                {
                    "who": "b",
                    "jp": "いいえ、ちかいですよ。このみちを、まっすぐです。",
                    "en": "No, it's close. Straight along this road.",
                    "gloss": "ちかい = near"
                },
                {
                    "who": "a",
                    "jp": "あるいて、どのくらいかかりますか。",
                    "en": "How long does it take on foot?"
                },
                {
                    "who": "b",
                    "jp": "ごふんぐらいです。",
                    "en": "About five minutes."
                },
                {
                    "who": "a",
                    "jp": "ありがとうございます。",
                    "en": "Thank you."
                },
                {
                    "who": "b",
                    "jp": "いいえ。きをつけて。",
                    "en": "Not at all. Take care.",
                    "gloss": "きをつけて = take care"
                }
            ]
        },
        "questions": [
            {
                "q": "Is the station far?",
                "choices": [
                    "No, it's close",
                    "Yes, very far",
                    "Only by train"
                ],
                "answer": 0
            },
            {
                "q": "How long is the walk?",
                "choices": [
                    "About ten minutes",
                    "About five minutes",
                    "About an hour"
                ],
                "answer": 1
            }
        ],
        "speak": [
            {
                "say": "がっこうに、なんでいきますか。",
                "situation": "Say how you get to school or work.",
                "hint": "＿でいきます。／あるいていきます。",
                "expect": [
                    "*でいきます*",
                    "*あるいて*",
                    "*で*"
                ]
            },
            {
                "say": "うちから、どのくらいかかりますか。",
                "situation": "Say how long it takes from your home.",
                "hint": "＿ぐらいです。／じゅっぷんぐらいです。",
                "expect": [
                    "*ぐらい*",
                    "*くらい*"
                ]
            },
            {
                "say": "どうしましたか。",
                "situation": "You're lost. Ask where the bus stop is.",
                "hint": "バスのりばは、どこですか。",
                "expect": [
                    "*どこ*"
                ]
            }
        ]
    },
    {
        "id": "u19",
        "title": "Weather",
        "title_jp": "てんき",
        "goal": "Talk about the weather and the seasons.",
        "phrases": [
            {
                "id": "u19.iitenki",
                "jp": "いいてんきですね。",
                "en": "Nice weather, isn't it.",
                "note": "ね invites agreement. The classic small-talk opener."
            },
            {
                "id": "u19.samui",
                "jp": "きょうは、さむいですね。",
                "en": "It's cold today, isn't it."
            },
            {
                "id": "u19.ame",
                "jp": "あしたは、あめです。",
                "en": "It'll rain tomorrow."
            },
            {
                "id": "u19.deshita",
                "jp": "きのうは、あめでした。",
                "en": "It rained yesterday.",
                "note": "Noun ＋ でした = was."
            },
            {
                "id": "u19.kisetsu",
                "jp": "どのきせつが、すきですか。",
                "en": "Which season do you like?"
            },
            {
                "id": "u19.ichiban",
                "jp": "はるが、いちばんすきです。",
                "en": "I like spring best.",
                "note": "いちばん = most, best."
            }
        ],
        "words": [
            {
                "id": "u19w.tenki",
                "jp": "てんき",
                "ro": "tenki",
                "en": "weather"
            },
            {
                "id": "u19w.hare",
                "jp": "はれ",
                "ro": "hare",
                "en": "sunny"
            },
            {
                "id": "u19w.ame",
                "jp": "あめ",
                "ro": "ame",
                "en": "rain"
            },
            {
                "id": "u19w.yuki",
                "jp": "ゆき",
                "ro": "yuki",
                "en": "snow"
            },
            {
                "id": "u19w.kumori",
                "jp": "くもり",
                "ro": "kumori",
                "en": "cloudy"
            },
            {
                "id": "u19w.kaze",
                "jp": "かぜ",
                "ro": "kaze",
                "en": "wind"
            },
            {
                "id": "u19w.atsui",
                "jp": "あつい",
                "ro": "atsui",
                "en": "hot"
            },
            {
                "id": "u19w.samui",
                "jp": "さむい",
                "ro": "samui",
                "en": "cold"
            },
            {
                "id": "u19w.atatakai",
                "jp": "あたたかい",
                "ro": "atatakai",
                "en": "warm"
            },
            {
                "id": "u19w.suzushii",
                "jp": "すずしい",
                "ro": "suzushii",
                "en": "cool"
            },
            {
                "id": "u19w.haru",
                "jp": "はる",
                "ro": "haru",
                "en": "spring"
            },
            {
                "id": "u19w.natsu",
                "jp": "なつ",
                "ro": "natsu",
                "en": "summer"
            },
            {
                "id": "u19w.aki",
                "jp": "あき",
                "ro": "aki",
                "en": "autumn"
            },
            {
                "id": "u19w.fuyu",
                "jp": "ふゆ",
                "ro": "fuyu",
                "en": "winter"
            },
            {
                "id": "u19w.kisetsu",
                "jp": "きせつ",
                "ro": "kisetsu",
                "en": "season"
            },
            {
                "id": "u19w.ichiban",
                "jp": "いちばん",
                "ro": "ichiban",
                "en": "most, best"
            }
        ],
        "grammar": [
            {
                "id": "u19g.deshita",
                "title": "Was: noun ＋ でした",
                "rule": "Noun ＋ でした = was. Noun ＋ じゃなかったです = wasn't.",
                "explain": [
                    "Nouns use でした for the past: あめでした (it was rainy). Describing words still use かった: さむかったです (unit 10).",
                    "Not: あめじゃなかったです (it wasn't rainy)."
                ],
                "examples": [
                    {
                        "jp": "きのうは、あめでした。",
                        "en": "It rained yesterday."
                    },
                    {
                        "jp": "やすみでした。",
                        "en": "It was a day off."
                    },
                    {
                        "jp": "いいてんきでした。",
                        "en": "The weather was nice."
                    },
                    {
                        "jp": "ゆきじゃなかったです。",
                        "en": "It didn't snow."
                    }
                ]
            },
            {
                "id": "u19g.neyo",
                "title": "ね and よ",
                "rule": "ね = …isn't it? (a shared feeling). よ = …you know (news for them).",
                "explain": [
                    "End with ね when you expect the other person agrees: さむいですね (cold, isn't it).",
                    "End with よ when you're telling them something they don't know: あしたは、あめですよ (it's going to rain tomorrow, you know)."
                ],
                "examples": [
                    {
                        "jp": "いいてんきですね。",
                        "en": "Nice weather, isn't it."
                    },
                    {
                        "jp": "あついですね。",
                        "en": "Hot, isn't it."
                    },
                    {
                        "jp": "あしたは、あめですよ。",
                        "en": "It's going to rain tomorrow, you know."
                    },
                    {
                        "jp": "このラーメン、おいしいですよ。",
                        "en": "This ramen is good, you know."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "Say it rained yesterday.",
                "choices": [
                    "きのうは、あめでした。",
                    "きのうは、あめかったです。",
                    "きのうは、あめです。"
                ],
                "answer": 0,
                "explain": "Nouns: でした."
            },
            {
                "q": "Say it was cold yesterday.",
                "choices": [
                    "きのうは、さむかったです。",
                    "きのうは、さむいでした。",
                    "きのうは、さむでした。"
                ],
                "answer": 0,
                "explain": "い words: かったです."
            },
            {
                "q": "You both feel the heat. Say it's hot.",
                "choices": [
                    "あついですね。",
                    "あついですよ。",
                    "あついですか。"
                ],
                "answer": 0,
                "explain": "ね = a shared feeling."
            },
            {
                "q": "Your friend doesn't know it'll rain tomorrow. Tell them.",
                "choices": [
                    "あしたは、あめですよ。",
                    "あしたは、あめですね。",
                    "あしたは、あめでした。"
                ],
                "answer": 0,
                "explain": "よ = telling them something new."
            },
            {
                "q": "Say you like winter best.",
                "choices": [
                    "ふゆが、いちばんすきです。",
                    "ふゆを、いちばんすきです。",
                    "ふゆは、いちばんですか。"
                ],
                "answer": 0
            },
            {
                "q": "Ask which season they like.",
                "choices": [
                    "どのきせつが、すきですか。",
                    "どのきせつを、すきですか。",
                    "きせつは、どこですか。"
                ],
                "answer": 0
            },
            {
                "q": "Say it didn't snow.",
                "choices": [
                    "ゆきじゃなかったです。",
                    "ゆきくなかったです。",
                    "ゆきでしたじゃない。"
                ],
                "answer": 0,
                "explain": "Nouns: じゃなかったです."
            },
            {
                "q": "It's a lovely day. Start some small talk.",
                "choices": [
                    "いいてんきですね。",
                    "いいてんきでした。",
                    "いいてんきですか。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Small talk with a neighbour in the morning.",
            "lines": [
                {
                    "who": "a",
                    "jp": "おはようございます。きょうは、いいてんきですね。",
                    "en": "Good morning. Nice weather today, isn't it."
                },
                {
                    "who": "b",
                    "jp": "そうですね。でも、ちょっとさむいですね。",
                    "en": "It is. A little cold, though.",
                    "gloss": "そうですね = yes, it is"
                },
                {
                    "who": "a",
                    "jp": "ええ。あしたは、ゆきですよ。",
                    "en": "Yes. It's going to snow tomorrow, you know.",
                    "gloss": "ええ = yes (soft)"
                },
                {
                    "who": "b",
                    "jp": "え、ほんとうですか。",
                    "en": "Really?",
                    "gloss": "ほんとう = really, true"
                },
                {
                    "who": "a",
                    "jp": "はい。もう、ふゆですね。",
                    "en": "Yes. It's winter already.",
                    "gloss": "もう = already"
                },
                {
                    "who": "b",
                    "jp": "わたしは、ふゆがいちばんすきです。",
                    "en": "Winter is my favourite season."
                }
            ]
        },
        "questions": [
            {
                "q": "How is the weather today?",
                "choices": [
                    "Rainy",
                    "Nice but a little cold",
                    "Hot"
                ],
                "answer": 1
            },
            {
                "q": "What will the weather be tomorrow?",
                "choices": [
                    "Snow",
                    "Sunny",
                    "Rain"
                ],
                "answer": 0
            },
            {
                "q": "Which season does the neighbour like best?",
                "choices": [
                    "Spring",
                    "Summer",
                    "Winter"
                ],
                "answer": 2
            }
        ],
        "speak": [
            {
                "say": "いいてんきですね。",
                "situation": "Agree with your neighbour.",
                "hint": "そうですね。",
                "expect": [
                    "そうですね*",
                    "*いいてんき*"
                ]
            },
            {
                "say": "きのうは、どうでしたか。",
                "situation": "It rained yesterday. Say so.",
                "hint": "あめでした。",
                "expect": [
                    "*あめ*"
                ]
            },
            {
                "say": "どのきせつが、すきですか。",
                "situation": "Say your favourite season.",
                "hint": "＿がいちばんすきです。／なつがすきです。",
                "expect": [
                    "*すきです*"
                ]
            }
        ]
    },
    {
        "id": "u20",
        "title": "Making plans",
        "title_jp": "やくそく",
        "goal": "Plan a day out with a friend: when, where and why not.",
        "phrases": [
            {
                "id": "u20.kara",
                "jp": "あめですから、うちにいます。",
                "en": "It's raining, so I'm staying home.",
                "note": "Reason ＋ から = because. The reason comes first."
            },
            {
                "id": "u20.doushite",
                "jp": "どうしてですか。",
                "en": "Why?"
            },
            {
                "id": "u20.aimashouka",
                "jp": "なんじに、あいましょうか。",
                "en": "What time shall we meet?",
                "note": "ましょうか = shall we?"
            },
            {
                "id": "u20.ekide",
                "jp": "えきで、あいましょう。",
                "en": "Let's meet at the station.",
                "note": "Place where something happens ＋ で."
            },
            {
                "id": "u20.tanoshimi",
                "jp": "たのしみです！",
                "en": "I'm looking forward to it!"
            },
            {
                "id": "u20.mataashita",
                "jp": "じゃあ、またあした。",
                "en": "See you tomorrow, then."
            }
        ],
        "words": [
            {
                "id": "u20w.doushite",
                "jp": "どうして",
                "ro": "doushite",
                "en": "why"
            },
            {
                "id": "u20w.tanoshimi",
                "jp": "たのしみ",
                "ro": "tanoshimi",
                "en": "something to look forward to"
            },
            {
                "id": "u20w.yakusoku",
                "jp": "やくそく",
                "ro": "yakusoku",
                "en": "a promise, plans"
            },
            {
                "id": "u20w.jikan",
                "jp": "じかん",
                "ro": "jikan",
                "en": "time"
            },
            {
                "id": "u20w.choudo",
                "jp": "ちょうど",
                "ro": "choudo",
                "en": "exactly, just"
            },
            {
                "id": "u20w.hayaku",
                "jp": "はやく",
                "ro": "hayaku",
                "en": "early, quickly"
            },
            {
                "id": "u20w.okuremasu",
                "jp": "おくれます",
                "ro": "okuremasu",
                "en": "be late"
            },
            {
                "id": "u20w.machimasu",
                "jp": "まちます",
                "ro": "machimasu",
                "en": "wait"
            },
            {
                "id": "u20w.basho",
                "jp": "ばしょ",
                "ro": "basho",
                "en": "place"
            },
            {
                "id": "u20w.doyoubi",
                "jp": "どようび",
                "ro": "doyoubi",
                "en": "Saturday"
            },
            {
                "id": "u20w.nichiyoubi",
                "jp": "にちようび",
                "ro": "nichiyoubi",
                "en": "Sunday"
            },
            {
                "id": "u20w.getsuyoubi",
                "jp": "げつようび",
                "ro": "getsuyoubi",
                "en": "Monday"
            },
            {
                "id": "u20w.kin'youbi",
                "jp": "きんようび",
                "ro": "kin'youbi",
                "en": "Friday"
            },
            {
                "id": "u20w.gomennasai",
                "jp": "ごめんなさい",
                "ro": "gomennasai",
                "en": "sorry"
            },
            {
                "id": "u20w.atode",
                "jp": "あとで",
                "ro": "atode",
                "en": "later"
            },
            {
                "id": "u20w.sonoato",
                "jp": "そのあと",
                "ro": "sono ato",
                "en": "after that"
            }
        ],
        "grammar": [
            {
                "id": "u20g.kara",
                "title": "Because: ＿から",
                "rule": "Reason ＋ から、result. The reason comes first.",
                "explain": [
                    "Put から after the reason: あめですから、うちにいます (it's raining, so I'm staying home). Japanese gives the reason before the result.",
                    "Answer どうして (why?) with the reason and から: いそがしいですから。"
                ],
                "examples": [
                    {
                        "jp": "あめですから、うちにいます。",
                        "en": "It's raining, so I'm staying home."
                    },
                    {
                        "jp": "いそがしいですから、いきません。",
                        "en": "I'm busy, so I'm not going."
                    },
                    {
                        "jp": "どうしてですか。",
                        "en": "Why?"
                    },
                    {
                        "jp": "じかんがありませんから。",
                        "en": "Because I don't have time."
                    }
                ]
            },
            {
                "id": "u20g.mashouka",
                "title": "Shall we? ＿ましょうか, and place ＋ で",
                "rule": "ます → ましょうか = shall we? Place ＋ で = where something happens.",
                "explain": [
                    "ましょう is let's; add か to make it a suggestion: なんじにあいましょうか (what time shall we meet?).",
                    "で marks the place where an action happens: えきであいましょう (let's meet at the station). に is for where you go or where something is."
                ],
                "examples": [
                    {
                        "jp": "なんじに、あいましょうか。",
                        "en": "What time shall we meet?"
                    },
                    {
                        "jp": "えきで、あいましょう。",
                        "en": "Let's meet at the station."
                    },
                    {
                        "jp": "どこで、たべましょうか。",
                        "en": "Where shall we eat?"
                    },
                    {
                        "jp": "こうえんで、まちます。",
                        "en": "I'll wait at the park."
                    }
                ]
            }
        ],
        "drill": [
            {
                "q": "It's raining, so you're staying home.",
                "choices": [
                    "あめですから、うちにいます。",
                    "うちにいますから、あめです。",
                    "あめですまで、うちにいます。"
                ],
                "answer": 0,
                "explain": "Reason first, then から."
            },
            {
                "q": "Ask why.",
                "choices": [
                    "どうしてですか。",
                    "どこですか。",
                    "どうですか。"
                ],
                "answer": 0
            },
            {
                "q": "You're busy, so you won't go.",
                "choices": [
                    "いそがしいですから、いきません。",
                    "いきませんから、いそがしいです。",
                    "いそがしいですね、いきません。"
                ],
                "answer": 0
            },
            {
                "q": "Ask what time you should meet.",
                "choices": [
                    "なんじに、あいましょうか。",
                    "なんじで、あいましょうか。",
                    "なんじ、あいましたか。"
                ],
                "answer": 0
            },
            {
                "q": "Suggest meeting at the station.",
                "choices": [
                    "えきで、あいましょう。",
                    "えきに、あいましょう。",
                    "えきを、あいましょう。"
                ],
                "answer": 0,
                "explain": "で = where something happens."
            },
            {
                "q": "You'll be late. Apologise.",
                "choices": [
                    "ごめんなさい、おくれます。",
                    "ごめんなさい、はやくです。",
                    "たのしみです、おくれます。"
                ],
                "answer": 0
            },
            {
                "q": "Say you're looking forward to it.",
                "say": "じゃあ、どようびに！",
                "choices": [
                    "たのしみです！",
                    "たのしかったです！",
                    "たのしみでした！"
                ],
                "answer": 0
            },
            {
                "q": "Say you'll wait at the park.",
                "choices": [
                    "こうえんで、まちます。",
                    "こうえんに、まちます。",
                    "こうえんを、まちます。"
                ],
                "answer": 0
            }
        ],
        "dialogue": {
            "scene": "Two friends make plans on the phone.",
            "lines": [
                {
                    "who": "a",
                    "jp": "どようび、ひまですか。",
                    "en": "Are you free on Saturday?"
                },
                {
                    "who": "b",
                    "jp": "どようびは、ちょっと…。しごとがありますから。",
                    "en": "Saturday's a bit… I have work."
                },
                {
                    "who": "a",
                    "jp": "そうですか。じゃあ、にちようびは？",
                    "en": "I see. Then how about Sunday?"
                },
                {
                    "who": "b",
                    "jp": "にちようびは、だいじょうぶです！",
                    "en": "Sunday works!"
                },
                {
                    "who": "a",
                    "jp": "じゃあ、じゅうじに、えきであいましょう。",
                    "en": "Then let's meet at the station at ten."
                },
                {
                    "who": "b",
                    "jp": "はい。たのしみです！",
                    "en": "OK. I'm looking forward to it!"
                }
            ]
        },
        "questions": [
            {
                "q": "Why can't B do Saturday?",
                "choices": [
                    "B is sick",
                    "B has a test",
                    "B has work"
                ],
                "answer": 2
            },
            {
                "q": "When and where will they meet?",
                "choices": [
                    "Sunday at noon, at home",
                    "Sunday at ten, at the station",
                    "Saturday at ten, at the park"
                ],
                "answer": 1
            }
        ],
        "speak": [
            {
                "say": "どようび、えいがをみませんか。",
                "situation": "You're busy on Saturday. Decline and give a reason.",
                "hint": "いそがしいですから、ちょっと…。",
                "expect": [
                    "*から*",
                    "*ちょっと*"
                ]
            },
            {
                "say": "なんじに、あいましょうか。",
                "situation": "Suggest a time.",
                "hint": "＿じにあいましょう。／じゅうじはどうですか。",
                "expect": [
                    "*ましょう*",
                    "*どうですか*"
                ]
            },
            {
                "say": "どこで、あいましょうか。",
                "situation": "Suggest meeting at the station.",
                "hint": "えきで、あいましょう。",
                "expect": [
                    "*えき*"
                ]
            }
        ]
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
    "u11.arimasuka": "shatsu wa arimasu ka.",
    "u11.futatsu": "kore o futatsu kudasai.",
    "u11.zenbu": "zenbu de, ikura desu ka.",
    "u11.chotto": "chotto, takai desu ne.",
    "u11.dake": "mite iru dake desu.",
    "u11.kaado": "kaado de, ii desu ka.",
    "u12.yonin": "kazoku wa, yonin desu.",
    "u12.ani": "ani ga imasu.",
    "u12.kyoudai": "kyoudai wa, imasu ka.",
    "u12.hitorikko": "hitorikko desu.",
    "u12.shashin": "kore wa, haha no shashin desu.",
    "u12.okaasan": "okaasan wa, genki desu ka.",
    "u13.tabetai": "sushi ga tabetai desu.",
    "u13.ikitai": "nihon ni ikitai desu.",
    "u13.shitai": "nani ga shitai desu ka.",
    "u13.hoshii": "atarashii kaban ga hoshii desu.",
    "u13.nanika": "nanika, nomitai desu.",
    "u13.yasumitai": "tsukaremashita. yasumitai desu.",
    "u14.matte": "sukoshi matte kudasai.",
    "u14.mite": "kore o mite kudasai.",
    "u14.kaite": "koko ni, namae o kaite kudasai.",
    "u14.hanashite": "yukkuri hanashite kudasai.",
    "u14.oshiete": "oshiete kudasai.",
    "u14.tabenaide": "tabenaide kudasai.",
    "u15.mimasenka": "issho ni, eiga o mimasen ka.",
    "u15.ikimashou": "ikimashou!",
    "u15.iidesune": "ii desu ne.",
    "u15.chotto": "ashita wa, chotto...",
    "u15.itsu": "itsu ga ii desu ka.",
    "u15.kondo": "mata, kondo.",
    "u16.ue": "tsukue no ue ni, hon ga arimasu.",
    "u16.shita": "isu no shita ni, neko ga imasu.",
    "u16.kagi": "kagi wa, doko ni arimasu ka.",
    "u16.naka": "kaban no naka desu.",
    "u16.mae": "eki no mae de, matte imasu.",
    "u16.tonari": "ginkou no tonari desu.",
    "u17.okimasu": "maiasa, shichiji ni okimasu.",
    "u17.karamade": "kuji kara goji made, hatarakimasu.",
    "u17.nemasu": "nanji ni nemasu ka.",
    "u17.sorekara": "sorekara, asagohan o tabemasu.",
    "u17.demasu": "hachiji ni, uchi o demasu.",
    "u17.tokidoki": "tokidoki, jimu ni ikimasu.",
    "u18.densha": "densha de, gakkou ni ikimasu.",
    "u18.kakarimasu": "dono kurai, kakarimasu ka.",
    "u18.juppun": "juppun gurai desu.",
    "u18.massugu": "kono michi o, massugu desu.",
    "u18.noriba": "basu noriba wa, doko desu ka.",
    "u18.aruite": "aruite, ikimasu.",
    "u19.iitenki": "ii tenki desu ne.",
    "u19.samui": "kyou wa, samui desu ne.",
    "u19.ame": "ashita wa, ame desu.",
    "u19.deshita": "kinou wa, ame deshita.",
    "u19.kisetsu": "dono kisetsu ga, suki desu ka.",
    "u19.ichiban": "haru ga, ichiban suki desu.",
    "u20.kara": "ame desu kara, uchi ni imasu.",
    "u20.doushite": "doushite desu ka.",
    "u20.aimashouka": "nanji ni, aimashou ka.",
    "u20.ekide": "eki de, aimashou.",
    "u20.tanoshimi": "tanoshimi desu!",
    "u20.mataashita": "jaa, mata ashita.",
}

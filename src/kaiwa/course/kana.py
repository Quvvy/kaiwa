"""Kana track: hiragana, then katakana, a few characters per lesson.

Each lesson teaches its characters (sound + a note on anything tricky), drills
them both ways (see → sound, hear → character), then reads real words built
only from kana taught so far. Every character becomes a review card.

Romaji follows the course convention: long vowels as typed (おう → ou, えい → ei).
`extra` lists marks a lesson makes readable without giving them their own card
(small ゃゅょ, っ, ー), so romaji can fade once everything in a phrase is known.
`confuse` gives hand-picked wrong readings for the word drill.
"""

from __future__ import annotations

from typing import Any

KANA_LESSONS: list[dict[str, Any]] = [
    # ---------------- hiragana ----------------
    {
        "id": "h1", "script": "hiragana", "title": "Vowels",
        "kana": [("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o")],
        "note": "Five vowels, always the same sound: a as in father, i as in machine, "
                "u as in food (lips relaxed, not rounded), e as in get, o as in go but short.",
        "words": [
            {"jp": "あい", "ro": "ai", "en": "love"},
            {"jp": "いえ", "ro": "ie", "en": "house"},
            {"jp": "うえ", "ro": "ue", "en": "above"},
            {"jp": "あお", "ro": "ao", "en": "blue"},
            {"jp": "いいえ", "ro": "iie", "en": "no", "confuse": ["ie", "iee"]},
        ],
    },
    {
        "id": "h2", "script": "hiragana", "title": "K row",
        "kana": [("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko")],
        "note": "Each kana is one consonant plus one vowel, said in one beat.",
        "words": [
            {"jp": "かお", "ro": "kao", "en": "face"},
            {"jp": "あかい", "ro": "akai", "en": "red"},
            {"jp": "いく", "ro": "iku", "en": "to go"},
            {"jp": "こえ", "ro": "koe", "en": "voice"},
            {"jp": "えき", "ro": "eki", "en": "station"},
            {"jp": "きく", "ro": "kiku", "en": "to listen"},
        ],
    },
    {
        "id": "h3", "script": "hiragana", "title": "S row",
        "kana": [("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so")],
        "note": "し is shi, not si. The u in す is often almost silent: です sounds like \"dess\".",
        "words": [
            {"jp": "あさ", "ro": "asa", "en": "morning"},
            {"jp": "すし", "ro": "sushi", "en": "sushi"},
            {"jp": "かさ", "ro": "kasa", "en": "umbrella"},
            {"jp": "せかい", "ro": "sekai", "en": "world"},
            {"jp": "そこ", "ro": "soko", "en": "there"},
            {"jp": "おかし", "ro": "okashi", "en": "sweets"},
        ],
    },
    {
        "id": "h4", "script": "hiragana", "title": "T row",
        "kana": [("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to")],
        "note": "ち is chi and つ is tsu (like the end of \"cats\").",
        "words": [
            {"jp": "くつ", "ro": "kutsu", "en": "shoes"},
            {"jp": "たかい", "ro": "takai", "en": "tall, expensive"},
            {"jp": "て", "ro": "te", "en": "hand"},
            {"jp": "そと", "ro": "soto", "en": "outside"},
            {"jp": "あした", "ro": "ashita", "en": "tomorrow"},
            {"jp": "ちかてつ", "ro": "chikatetsu", "en": "subway"},
        ],
    },
    {
        "id": "h5", "script": "hiragana", "title": "N row",
        "kana": [("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no")],
        "note": "ぬ and め look alike: ぬ has a loop at the end.",
        "words": [
            {"jp": "なに", "ro": "nani", "en": "what"},
            {"jp": "いぬ", "ro": "inu", "en": "dog"},
            {"jp": "ねこ", "ro": "neko", "en": "cat"},
            {"jp": "なつ", "ro": "natsu", "en": "summer"},
            {"jp": "おかね", "ro": "okane", "en": "money"},
            {"jp": "あなた", "ro": "anata", "en": "you"},
        ],
    },
    {
        "id": "h6", "script": "hiragana", "title": "H row",
        "kana": [("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho")],
        "note": "ふ is a soft fu, between f and h, blowing gently. As a particle (a little "
                "grammar word), は is read wa and へ is read e.",
        "words": [
            {"jp": "はな", "ro": "hana", "en": "flower"},
            {"jp": "ひと", "ro": "hito", "en": "person"},
            {"jp": "ふね", "ro": "fune", "en": "boat"},
            {"jp": "ほし", "ro": "hoshi", "en": "star"},
            {"jp": "はなし", "ro": "hanashi", "en": "story, talk"},
            {"jp": "へた", "ro": "heta", "en": "bad at"},
        ],
    },
    {
        "id": "h7", "script": "hiragana", "title": "M row",
        "kana": [("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo")],
        "note": "め and ぬ look alike: め has no loop.",
        "words": [
            {"jp": "まち", "ro": "machi", "en": "town"},
            {"jp": "みみ", "ro": "mimi", "en": "ear"},
            {"jp": "むし", "ro": "mushi", "en": "bug"},
            {"jp": "め", "ro": "me", "en": "eye"},
            {"jp": "もも", "ro": "momo", "en": "peach"},
            {"jp": "あたま", "ro": "atama", "en": "head"},
        ],
    },
    {
        "id": "h8", "script": "hiragana", "title": "Y, W and N",
        "kana": [("や", "ya"), ("ゆ", "yu"), ("よ", "yo"), ("わ", "wa"), ("を", "o (wo)"), ("ん", "n")],
        "note": "を is read o and only appears as a particle (it marks the object: ほんをよむ, "
                "read a book). ん is a full beat of its own: ほん is ho-n, two beats.",
        "words": [
            {"jp": "やま", "ro": "yama", "en": "mountain"},
            {"jp": "ゆき", "ro": "yuki", "en": "snow"},
            {"jp": "よむ", "ro": "yomu", "en": "to read"},
            {"jp": "わたし", "ro": "watashi", "en": "I, me"},
            {"jp": "ほん", "ro": "hon", "en": "book"},
            {"jp": "ほんをよむ", "ro": "hon o yomu", "en": "read a book", "confuse": ["hon wo yomu", "honwoyomu"]},
        ],
    },
    {
        "id": "h9", "script": "hiragana", "title": "R row",
        "kana": [("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro")],
        "note": "Japanese r is a light tap of the tongue, close to the tt in American \"butter\". "
                "It is neither an English r nor an l.",
        "words": [
            {"jp": "さくら", "ro": "sakura", "en": "cherry blossom"},
            {"jp": "よる", "ro": "yoru", "en": "night"},
            {"jp": "これ", "ro": "kore", "en": "this"},
            {"jp": "ろく", "ro": "roku", "en": "six"},
            {"jp": "くるま", "ro": "kuruma", "en": "car"},
            {"jp": "りす", "ro": "risu", "en": "squirrel"},
        ],
    },
    {
        "id": "h10", "script": "hiragana", "title": "G and Z",
        "kana": [("が", "ga"), ("ぎ", "gi"), ("ぐ", "gu"), ("げ", "ge"), ("ご", "go"),
                 ("ざ", "za"), ("じ", "ji"), ("ず", "zu"), ("ぜ", "ze"), ("ぞ", "zo")],
        "note": "The two small marks (゛) make the sound voiced: か ka → が ga, さ sa → ざ za. "
                "じ is ji.",
        "words": [
            {"jp": "かぎ", "ro": "kagi", "en": "key"},
            {"jp": "ごご", "ro": "gogo", "en": "afternoon (p.m.)"},
            {"jp": "みず", "ro": "mizu", "en": "water"},
            {"jp": "かぜ", "ro": "kaze", "en": "wind; a cold"},
            {"jp": "じかん", "ro": "jikan", "en": "time"},
            {"jp": "りんご", "ro": "ringo", "en": "apple"},
        ],
    },
    {
        "id": "h11", "script": "hiragana", "title": "D, B and P",
        "kana": [("だ", "da"), ("ぢ", "ji"), ("づ", "zu"), ("で", "de"), ("ど", "do"),
                 ("ば", "ba"), ("び", "bi"), ("ぶ", "bu"), ("べ", "be"), ("ぼ", "bo"),
                 ("ぱ", "pa"), ("ぴ", "pi"), ("ぷ", "pu"), ("ぺ", "pe"), ("ぽ", "po")],
        "note": "゛ makes た ta → だ da and は ha → ば ba. The small circle ゜ makes は ha → ぱ pa. "
                "ぢ and づ are rare and sound the same as じ and ず.",
        "words": [
            {"jp": "でんわ", "ro": "denwa", "en": "phone"},
            {"jp": "まど", "ro": "mado", "en": "window"},
            {"jp": "ともだち", "ro": "tomodachi", "en": "friend"},
            {"jp": "ぶた", "ro": "buta", "en": "pig"},
            {"jp": "ぱん", "ro": "pan", "en": "bread"},
            {"jp": "えんぴつ", "ro": "enpitsu", "en": "pencil"},
        ],
    },
    {
        "id": "h12", "script": "hiragana", "title": "Blended sounds",
        "kana": [("きゃ", "kya"), ("きゅ", "kyu"), ("きょ", "kyo"),
                 ("しゃ", "sha"), ("しゅ", "shu"), ("しょ", "sho"),
                 ("ちゃ", "cha"), ("ちゅ", "chu"), ("ちょ", "cho"),
                 ("じゃ", "ja"), ("じゅ", "ju"), ("じょ", "jo")],
        "extra": ["ゃ", "ゅ", "ょ"],
        "note": "A small ゃ, ゅ or ょ blends with the kana before it into one beat: き + ゃ = きゃ kya. "
                "The same works with に, ひ, み, り, ぎ, び and ぴ (にゃ nya, りょ ryo…).",
        "words": [
            {"jp": "しゃしん", "ro": "shashin", "en": "photo"},
            {"jp": "おちゃ", "ro": "ocha", "en": "tea"},
            {"jp": "きょう", "ro": "kyou", "en": "today", "confuse": ["kiyou", "kyo"]},
            {"jp": "しゅくだい", "ro": "shukudai", "en": "homework"},
            {"jp": "じゃあね", "ro": "jaa ne", "en": "bye (casual)"},
            {"jp": "でんしゃ", "ro": "densha", "en": "train", "confuse": ["denshiya", "densya"]},
        ],
    },
    {
        "id": "h13", "script": "hiragana", "title": "Small っ and long vowels",
        "kana": [],
        "extra": ["っ"],
        "note": "Small っ is a short pause that doubles the next consonant: きって is kit-te. "
                "A long vowel is held for two beats: おかあさん is o-ka-a-sa-n. "
                "えい and おう are usually said as a long e and a long o. "
                "Getting the length right changes the word: おばさん aunt, おばあさん grandmother.",
        "words": [
            {"jp": "きって", "ro": "kitte", "en": "stamp", "confuse": ["kite", "kiite"]},
            {"jp": "がっこう", "ro": "gakkou", "en": "school", "confuse": ["gakou", "gakko"]},
            {"jp": "ちょっと", "ro": "chotto", "en": "a little", "confuse": ["choto", "chouto"]},
            {"jp": "おかあさん", "ro": "okaasan", "en": "mother", "confuse": ["okasan", "okaasaan"]},
            {"jp": "せんせい", "ro": "sensei", "en": "teacher", "confuse": ["sense", "senseii"]},
            {"jp": "おばあさん", "ro": "obaasan", "en": "grandmother", "confuse": ["obasan", "obaasaan"]},
        ],
    },
    # ---------------- katakana ----------------
    {
        "id": "k1", "script": "katakana", "title": "Katakana: vowels and K",
        "kana": [("ア", "a"), ("イ", "i"), ("ウ", "u"), ("エ", "e"), ("オ", "o"),
                 ("カ", "ka"), ("キ", "ki"), ("ク", "ku"), ("ケ", "ke"), ("コ", "ko")],
        "extra": ["ー"],
        "note": "Katakana spells foreign words and names. Same sounds as hiragana, sharper shapes. "
                "The dash ー holds the vowel for an extra beat: ケーキ is ke-e-ki.",
        "words": [
            {"jp": "ケーキ", "ro": "keeki", "en": "cake", "confuse": ["keki", "keeeki"]},
            {"jp": "ココア", "ro": "kokoa", "en": "cocoa"},
            {"jp": "キウイ", "ro": "kiui", "en": "kiwi"},
            {"jp": "カカオ", "ro": "kakao", "en": "cacao"},
        ],
    },
    {
        "id": "k2", "script": "katakana", "title": "Katakana: S and T",
        "kana": [("サ", "sa"), ("シ", "shi"), ("ス", "su"), ("セ", "se"), ("ソ", "so"),
                 ("タ", "ta"), ("チ", "chi"), ("ツ", "tsu"), ("テ", "te"), ("ト", "to")],
        "note": "シ and ツ look alike: シ's strokes rise from the left, ツ's fall from the top. "
                "ソ and ン are the same pair later.",
        "words": [
            {"jp": "アイス", "ro": "aisu", "en": "ice cream"},
            {"jp": "スキー", "ro": "sukii", "en": "skiing"},
            {"jp": "テスト", "ro": "tesuto", "en": "test"},
            {"jp": "タクシー", "ro": "takushii", "en": "taxi"},
            {"jp": "セーター", "ro": "seetaa", "en": "sweater"},
        ],
    },
    {
        "id": "k3", "script": "katakana", "title": "Katakana: N and H",
        "kana": [("ナ", "na"), ("ニ", "ni"), ("ヌ", "nu"), ("ネ", "ne"), ("ノ", "no"),
                 ("ハ", "ha"), ("ヒ", "hi"), ("フ", "fu"), ("ヘ", "he"), ("ホ", "ho")],
        "note": "Foreign f-sounds use フ: ナイフ (knife) is naifu.",
        "words": [
            {"jp": "ネクタイ", "ro": "nekutai", "en": "necktie"},
            {"jp": "ノート", "ro": "nooto", "en": "notebook"},
            {"jp": "ナイフ", "ro": "naifu", "en": "knife"},
            {"jp": "コーヒー", "ro": "koohii", "en": "coffee"},
            {"jp": "ハート", "ro": "haato", "en": "heart"},
        ],
    },
    {
        "id": "k4", "script": "katakana", "title": "Katakana: M, Y, W and N",
        "kana": [("マ", "ma"), ("ミ", "mi"), ("ム", "mu"), ("メ", "me"), ("モ", "mo"),
                 ("ヤ", "ya"), ("ユ", "yu"), ("ヨ", "yo"), ("ワ", "wa"), ("ヲ", "o (wo)"), ("ン", "n")],
        "note": "ン and ソ look alike: ン's short stroke is flatter and its long stroke rises from below.",
        "words": [
            {"jp": "メモ", "ro": "memo", "en": "memo"},
            {"jp": "アニメ", "ro": "anime", "en": "anime"},
            {"jp": "マスク", "ro": "masuku", "en": "face mask"},
            {"jp": "ワイン", "ro": "wain", "en": "wine"},
            {"jp": "ハム", "ro": "hamu", "en": "ham"},
        ],
    },
    {
        "id": "k5", "script": "katakana", "title": "Katakana: R",
        "kana": [("ラ", "ra"), ("リ", "ri"), ("ル", "ru"), ("レ", "re"), ("ロ", "ro")],
        "note": "English l and r both become the R row: hotel → ホテル.",
        "words": [
            {"jp": "カメラ", "ro": "kamera", "en": "camera"},
            {"jp": "ホテル", "ro": "hoteru", "en": "hotel"},
            {"jp": "トイレ", "ro": "toire", "en": "toilet"},
            {"jp": "ラーメン", "ro": "raamen", "en": "ramen"},
            {"jp": "アメリカ", "ro": "amerika", "en": "America"},
            {"jp": "レストラン", "ro": "resutoran", "en": "restaurant"},
        ],
    },
    {
        "id": "k6", "script": "katakana", "title": "Katakana: voiced sounds",
        "kana": [("ガ", "ga"), ("ギ", "gi"), ("グ", "gu"), ("ゲ", "ge"), ("ゴ", "go"),
                 ("ザ", "za"), ("ジ", "ji"), ("ズ", "zu"), ("ゼ", "ze"), ("ゾ", "zo"),
                 ("ダ", "da"), ("ヂ", "ji"), ("ヅ", "zu"), ("デ", "de"), ("ド", "do"),
                 ("バ", "ba"), ("ビ", "bi"), ("ブ", "bu"), ("ベ", "be"), ("ボ", "bo"),
                 ("パ", "pa"), ("ピ", "pi"), ("プ", "pu"), ("ペ", "pe"), ("ポ", "po")],
        "note": "Same marks as hiragana: ゛ voices the sound, ゜ turns H into P.",
        "words": [
            {"jp": "ゲーム", "ro": "geemu", "en": "game"},
            {"jp": "テレビ", "ro": "terebi", "en": "TV"},
            {"jp": "パン", "ro": "pan", "en": "bread"},
            {"jp": "ドア", "ro": "doa", "en": "door"},
            {"jp": "バス", "ro": "basu", "en": "bus"},
            {"jp": "ギター", "ro": "gitaa", "en": "guitar"},
        ],
    },
    {
        "id": "k7", "script": "katakana", "title": "Katakana: blends and small ッ",
        "kana": [("キャ", "kya"), ("キュ", "kyu"), ("キョ", "kyo"),
                 ("シャ", "sha"), ("シュ", "shu"), ("ショ", "sho"),
                 ("チャ", "cha"), ("チュ", "chu"), ("チョ", "cho"),
                 ("ジャ", "ja"), ("ジュ", "ju"), ("ジョ", "jo")],
        "extra": ["ャ", "ュ", "ョ", "ッ"],
        "note": "Small ャュョ blend and small ッ pauses, exactly as in hiragana.",
        "words": [
            {"jp": "シャツ", "ro": "shatsu", "en": "shirt"},
            {"jp": "ジュース", "ro": "juusu", "en": "juice", "confuse": ["jusu", "jiyuusu"]},
            {"jp": "チョコ", "ro": "choko", "en": "chocolate"},
            {"jp": "ベッド", "ro": "beddo", "en": "bed", "confuse": ["bedo", "beddoo"]},
            {"jp": "カップ", "ro": "kappu", "en": "cup", "confuse": ["kapu", "kaappu"]},
            {"jp": "チケット", "ro": "chiketto", "en": "ticket", "confuse": ["chiketo", "chikeetto"]},
        ],
    },
]

KANA_ROMAJI: dict[str, str] = {ch: ro for lesson in KANA_LESSONS for ch, ro in lesson["kana"]}
LESSON_BY_ID: dict[str, dict[str, Any]] = {lesson["id"]: lesson for lesson in KANA_LESSONS}


def lesson_chars(lesson: dict[str, Any]) -> set[str]:
    """Characters a lesson makes readable (blends count as their parts)."""
    chars = {c for ch, _ in lesson["kana"] for c in ch}
    return chars | set(lesson.get("extra", []))


def chars_through(index: int) -> set[str]:
    """Everything readable after finishing lessons 0..index."""
    out: set[str] = set()
    for lesson in KANA_LESSONS[: index + 1]:
        out |= lesson_chars(lesson)
    return out

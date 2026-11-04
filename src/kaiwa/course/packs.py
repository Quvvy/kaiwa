"""Optional word packs: common beginner words the 20 units don't reach.

An audit of the units against everyday N5 vocabulary found holes: the numbers 1-10 as
words, basic food, the body and feeling ill, colours, more verbs. Rather than reorder a
course people are part-way through, these are small sets the learner picks when they
want them. Choosing what to learn next is motivating in itself (Deci & Ryan), and
"I need food words for my trip" is the best reason there is to learn something.

Learned pack words are ordinary word cards, so reviews, Chat and extra listening use
them like any other known word.
"""

from __future__ import annotations

from typing import Any


def _w(pack: str, rows: str) -> list[dict[str, str]]:
    out = []
    for row in rows.strip().splitlines():
        jp, ro, en = [p.strip() for p in row.split("|")]
        out.append({"id": f"p.{pack}.{ro}", "jp": jp, "ro": ro, "en": en})
    return out


PACKS: list[dict[str, Any]] = [
    {"id": "numbers", "title": "Numbers 1 to 10", "blurb": "Prices, times, ages and phone numbers all start here. Best before the Time unit.",
     "words": _w("numbers", """
        いち | ichi | one
        に | ni | two
        さん | san | three
        よん | yon | four
        ご | go | five
        ろく | roku | six
        なな | nana | seven
        はち | hachi | eight
        きゅう | kyuu | nine
        じゅう | juu | ten
     """)},
    {"id": "food", "title": "Food and drink", "blurb": "What's on the table and on the menu.",
     "words": _w("food", """
        ごはん | gohan | rice, a meal
        さかな | sakana | fish
        にく | niku | meat
        とりにく | toriniku | chicken
        やさい | yasai | vegetables
        くだもの | kudamono | fruit
        たまご | tamago | egg
        りんご | ringo | apple
        ぎゅうにゅう | gyuunyuu | milk
        ビール | biiru | beer
        ジュース | juusu | juice
     """)},
    {"id": "health", "title": "Body and feeling ill", "blurb": "The words you hope you won't need, and will be glad of if you do.",
     "words": _w("health", """
        あたま | atama | head
        め | me | eye
        みみ | mimi | ear
        くち | kuchi | mouth
        て | te | hand
        あし | ashi | leg, foot
        おなか | onaka | stomach
        いたい | itai | it hurts, painful
        びょうき | byouki | sick, illness
        ねつ | netsu | fever
        くすり | kusuri | medicine
     """)},
    {"id": "people", "title": "People", "blurb": "Talking about who's around you.",
     "words": _w("people", """
        こども | kodomo | child
        あかちゃん | akachan | baby
        おとこのひと | otokonohito | man
        おんなのひと | onnanohito | woman
        おじいさん | ojiisan | grandfather, old man
        おばあさん | obaasan | grandmother, old woman
     """)},
    {"id": "colours", "title": "Colours", "blurb": "Asking for the red one.",
     "words": _w("colours", """
        あか | aka | red (the colour)
        あお | ao | blue
        しろ | shiro | white
        くろ | kuro | black
        きいろ | kiiro | yellow
        みどり | midori | green
     """)},
    {"id": "verbs", "title": "More things you do", "blurb": "Verbs for talking about your life and hobbies.",
     "words": _w("verbs", """
        はなします | hanashimasu | speak, talk
        つくります | tsukurimasu | make
        あるきます | arukimasu | walk
        はしります | hashirimasu | run
        うたいます | utaimasu | sing
        およぎます | oyogimasu | swim
        のります | norimasu | ride, get on
        ならいます | naraimasu | learn (from someone)
     """)},
    {"id": "describe", "title": "More describing words", "blurb": "Beyond good and bad.",
     "words": _w("describe", """
        ながい | nagai | long
        みじかい | mijikai | short
        まずい | mazui | tastes bad
        かんたん | kantan | easy, simple
        じょうず | jouzu | good at
        へた | heta | bad at
        しずか | shizuka | quiet
        にぎやか | nigiyaka | lively
        きれい | kirei | pretty, clean
     """)},
    {"id": "things", "title": "Everyday things", "blurb": "What's on your desk and in your pocket, and the days you didn't get yet.",
     "words": _w("things", """
        スマホ | sumaho | smartphone
        パソコン | pasokon | computer
        ペン | pen | pen
        おかね | okane | money
        かみ | kami | paper
        かようび | kayoubi | Tuesday
        すいようび | suiyoubi | Wednesday
        もくようび | mokuyoubi | Thursday
     """)},
    {"id": "nature", "title": "Outdoors", "blurb": "For walks, trips and small talk.",
     "words": _w("nature", """
        かわ | kawa | river
        そら | sora | sky
        はな | hana | flower
        き | ki | tree
     """)},
]

PACK_BY_ID = {p["id"]: p for p in PACKS}

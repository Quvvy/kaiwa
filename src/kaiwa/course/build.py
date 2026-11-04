"""Sentence building: the grammar points as things to say, not facts to recognise.

Each grammar point has sentences cut into tiles. Given the English, the learner puts
the Japanese together, with one wrong particle or ending in the pile, and hears it
when it's right. These are the grammar review cards: a point comes back on an FSRS
schedule with a different sentence each time, so what's practised is the pattern
rather than one memorised line. Choosing a form yourself is what makes a pattern
stick (Swain's output hypothesis), and mixing old points with new beats practising
one at a time (Nakata & Suzuki 2019).

A line is "tiles | English" with optional "| another natural order" when Japanese
word order really does allow it.
"""

from __future__ import annotations

from typing import Any

_LINES: dict[str, list[str]] = {
    "u1g.polite": [],
    "u1g.desu": ["がくせい です か | Are you a student?", "せんせい です か | Are you the teacher?", "ともだち です か | Is he your friend?"],
    "u2g.wa": ["わたし は アレックス です | I'm Alex.", "ユキさん は がくせい です | Yuki is a student.",
               "わたし は かいしゃいん です | I'm an office worker.", "アレックスさん は アメリカじん です | Alex is American."],
    "u2g.kara": ["アメリカ から きました | I'm from America.", "イギリス から きました | I'm from the UK.", "どこ から きました か | Where are you from?",
                 "かんこくじん です か | Are you Korean?"],
    "u3g.onegai": ["もういちど おねがい します | One more time, please.", "えいご で おねがい します | In English, please.",
                   "ちょっと まって ください | Wait a moment, please."],
    "u3g.masen": ["わかります か | Do you understand?", "はい わかります | Yes, I understand.", "いいえ わかりません | No, I don't understand.",
                  "すこし わかります | I understand a little."],
    "u4g.ga": ["ねこ が すき です | I like cats.", "アニメ が すき です | I like anime.", "なに が すき です か | What do you like?",
               "おんがく が だいすき です | I love music."],
    "u4g.janai": ["スポーツ は すき じゃない です | I don't like sports.", "あまり すき じゃない です | I don't really like it.",
                  "わたし も すき です | I like it too."],
    "u5g.kudasai": ["コーヒー を ください | A coffee, please.", "ケーキ を ひとつ ください | One cake, please.", "おみず を ふたつ ください | Two waters, please."],
    "u5g.kosoa": ["これ は なん です か | What is this?", "それ は まっちゃラテ です | That's a matcha latte.", "あれ は なん です か | What's that over there?",
                  "これ を ください | This one, please."],
    "u6g.wo": ["パン を たべます | I eat bread.", "コーヒー を のみます | I drink coffee.", "ほん を よみます | I read books.", "おんがく を ききます | I listen to music."],
    "u6g.masu": ["あさごはん を たべます か | Do you eat breakfast?", "はい たべます | Yes, I do.", "いいえ たべません | No, I don't.", "コーヒー だけ のみます | I only drink coffee."],
    "u7g.ni": ["がっこう に いきます | I go to school.", "うち に かえります | I'm going home.", "どこ に いきます か | Where are you going?", "にほん に きました | I came to Japan."],
    "u7g.doko": ["えき は どこ です か | Where's the station?", "トイレ は どこ です か | Where's the toilet?", "あそこ です | It's over there.",
                 "コンビニ は どこ です か | Where's the convenience store?"],
    "u8g.ji": ["いま なんじ です か | What time is it now?", "さんじ です | It's three o'clock.", "よじはん です | It's half past four.", "ごご くじ です | It's 9 p.m."],
    "u8g.time": ["あした えいが を みます | I'll watch a movie tomorrow. | えいが を あした みます",
                 "まいにち にほんご を べんきょう します | I study Japanese every day. | にほんご を まいにち べんきょう します",
                 "しゅうまつ なに を します か | What are you doing this weekend? | なに を しゅうまつ します か",
                 "らいしゅう しけん が あります | I have a test next week. | しけん が らいしゅう あります"],
    "u9g.adj": ["この かばん は たかい です | This bag is expensive.", "にほんご は どう です か | How is Japanese?", "おもしろい アニメ です | It's an interesting anime."],
    "u9g.kunai": ["たかくない です | It's not expensive.", "むずかしくない です | It's not difficult.", "その かばん は やすい です | That bag is cheap."],
    "u10g.mashita": ["きのう すし を たべました | Yesterday I ate sushi. | すし を きのう たべました",
                     "しゅうまつ とうきょう に いきました | I went to Tokyo at the weekend. | とうきょう に しゅうまつ いきました",
                     "べんきょう しません でした | I didn't study.", "ともだち と えいが を みました | I watched a movie with a friend. | えいが を ともだち と みました"],
    "u10g.katta": ["たのしかった です | It was fun.", "おもしろかった です | It was interesting.", "どう でした か | How was it?"],
    "u11g.price": ["ひゃくえん です | It's 100 yen.", "さんびゃくえん です | It's 300 yen.", "せんごひゃくえん です | It's 1,500 yen."],
    "u11g.arimasu": ["シャツ は あります か | Do you have shirts?", "はい あります | Yes, we do.", "いいえ ありません | No, we don't.", "ケーキ を みっつ ください | Three cakes, please."],
    "u12g.imasu": ["あに が います | I have an older brother.", "いぬ が います | I have a dog.", "きょうだい は いません | I don't have any brothers or sisters.",
                   "かぞく は さんにん です | There are three of us."],
    "u12g.no": ["わたし の かばん です | It's my bag.", "はは の しゃしん です | It's my mother's photo.", "ともだち の いぬ です | It's my friend's dog.", "にほんご の ほん です | It's a Japanese book."],
    "u13g.tai": ["すし が たべたい です | I want to eat sushi.", "にほん に いきたい です | I want to go to Japan.", "えいが を みたい です | I want to watch a movie.", "なに が したい です か | What do you want to do?"],
    "u13g.hoshii": ["あたらしい かばん が ほしい です | I want a new bag.", "くるま が ほしい です | I want a car.", "なに が ほしい です か | What do you want?", "いきたくない です | I don't want to go."],
    "u14g.te": ["これ を みて ください | Please look at this.", "すこし まって ください | Please wait a moment.", "ここ に すわって ください | Please sit here.", "まど を あけて ください | Please open the window."],
    "u14g.naide": ["たべないで ください | Please don't eat it.", "みないで ください | Please don't look.", "ここ で たべないで ください | Please don't eat here."],
    "u15g.masenka": ["いっしょに しょくじ を しません か | Shall we have a meal together?", "カラオケ に いきません か | Want to go to karaoke?",
                     "なんじ に あいましょう か | What time shall we meet?"],
    "u15g.chotto": ["あした は ちょっと | Tomorrow is a bit…", "すみません ようじ が あります | Sorry, I have something on."],
    "u16g.ni": ["つくえ の うえ に ほん が あります | There's a book on the desk.", "いす の した に ねこ が います | There's a cat under the chair.",
                "へや に ともだち が います | My friend is in the room.", "れいぞうこ に ケーキ が あります | There's cake in the fridge."],
    "u16g.position": ["かばん の なか です | It's in the bag.", "えき の まえ です | It's in front of the station.", "ぎんこう の となり です | It's next to the bank.",
                      "ドア の うしろ に いぬ が います | There's a dog behind the door."],
    "u17g.ni": ["しちじ に おきます | I get up at seven.", "じゅうじ に ねます | I go to bed at ten.", "なんじ に ねます か | What time do you go to bed?",
                "まいあさ はちじ に うち を でます | I leave home at eight every morning. | まいあさ うち を はちじ に でます"],
    "u17g.karamade": ["くじ から ごじ まで はたらきます | I work from nine to five.", "いつも しちじ に おきます | I always get up at seven.",
                      "ときどき ジム に いきます | Sometimes I go to the gym.", "ぜんぜん テレビ を みません | I never watch TV. | テレビ を ぜんぜん みません"],
    "u18g.de": ["でんしゃ で がっこう に いきます | I go to school by train. | がっこう に でんしゃ で いきます", "バス で かえります | I go home by bus.",
                "ひこうき で にほん に いきます | I'll go to Japan by plane. | にほん に ひこうき で いきます"],
    "u18g.kakaru": ["どのくらい かかります か | How long does it take?", "じゅっぷん ぐらい です | About ten minutes.", "でんしゃ で いちじかん ぐらい かかります | It takes about an hour by train.",
                    "ごふん ぐらい です | About five minutes."],
    "u19g.deshita": ["きのう は あめ でした | It rained yesterday.", "いい てんき でした | The weather was nice.", "ゆき じゃなかった です | It didn't snow."],
    "u19g.neyo": ["いい てんき です ね | Nice weather, isn't it.", "あつい です ね | Hot, isn't it.", "あした は あめ です よ | It's going to rain tomorrow, you know.",
                  "この ラーメン おいしい です よ | This ramen is good, you know."],
    "u20g.kara": ["あめ です から うち に います | It's raining, so I'm staying home.", "いそがしい です から いきません | I'm busy, so I'm not going.",
                  "じかん が ありません から | Because I don't have time."],
    "u20g.mashouka": ["なんじ に あいましょう か | What time shall we meet?", "えき で あいましょう | Let's meet at the station.", "どこ で たべましょう か | Where shall we eat?",
                      "こうえん で まちます | I'll wait at the park."],
}

# The wrong tile in the pile: the mistake a learner of this point actually makes.
_DECOYS = {
    "が": "を", "を": "が", "は": "が", "に": "で", "で": "に", "から": "まで", "まで": "から", "の": "は", "と": "を",
    "か": "よ", "ね": "か", "よ": "か", "です": "ます", "でした": "です", "じゃない": "くない", "ください": "します",
    "も": "は", "だけ": "も", "います": "あります", "あります": "います", "ぐらい": "から",
}


def _decoy(tiles: list[str]) -> str:
    """The first tile with a typical confusion gives the wrong option (never one that's needed)."""
    for tile in tiles:
        wrong = _DECOYS.get(tile)
        if wrong and wrong not in tiles:
            return wrong
    return ""


def _parse(line: str) -> dict[str, Any]:
    tiles, en, *alt = [part.strip() for part in line.split("|")]
    parts = tiles.split()
    return {"tiles": parts, "jp": "".join(parts), "en": en, "decoy": _decoy(parts),
            "also": ["".join(a.split()) for a in alt]}


BUILD: dict[str, list[dict[str, Any]]] = {pid: [_parse(line) for line in lines] for pid, lines in _LINES.items() if lines}


def items_for(point_id: str) -> list[dict[str, Any]]:
    return BUILD.get(point_id, [])

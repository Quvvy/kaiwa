"""A picture for every basic kana, and which kana get mistaken for which.

Learners given a shape-and-sound picture learn kana much faster than by rote
(Quackenbush et al. 1989, Matsunaga 2003). The capitals in each hook mark the sound.
Voiced kana (が, ぱ…) and blends (きゃ…) have no hook of their own: their lesson note
teaches the rule that turns the base kana into them.

LOOKALIKES drives the wrong options in kana drills. A kana mostly gets confused with
what it looks like, so a drill that offers those trains the difference, where random
options can be answered from a rough impression of the shape.
"""

from __future__ import annotations

HOOKS: dict[str, str] = {
    # hiragana
    "あ": "A cross stuck in a swirl of string. AH, it's tangled.",
    "い": "Two Icicles hanging side by side.",
    "う": "A small dash over a bowed back: someone winded, going OOF.",
    "え": "Someone running with one arm out: EH? Wait for me!",
    "お": "A swirl with a dot flying off: OH, my earring!",
    "か": "A KArate chop, with a spark flying off beside it.",
    "き": "A KEY: two teeth at the top, a curved handle below.",
    "く": "A bird's open beak: KOO-koo.",
    "け": "A post next to a hanging flag on a KEbab stand.",
    "こ": "Two COrds lying one above the other.",
    "さ": "A SAil: a crossed mast above a curved hull.",
    "し": "A fishhook. SHE caught something with it.",
    "す": "A rope SWing with a knot tied in it. Say it SU.",
    "せ": "An open mouth with one big tooth: SAY ahh.",
    "そ": "A zigzag of thread: you SOw it back and forth.",
    "た": "A little t and a little a, side by side: TA.",
    "ち": "A round belly in profile, cheeks up: say CHEEse.",
    "つ": "One curling wave: a TSUnami rolling in.",
    "て": "A bar with a curved handle under it: a TEapot handle.",
    "と": "A thorn stuck in a big TOE.",
    "な": "A NAil (the cross) holding a knotted rope.",
    "に": "A leg and two bent KNEEs.",
    "ぬ": "A tangle of NOOdles, with a loop at the end.",
    "ね": "A NEko (cat) curling its tail around a post.",
    "の": "A NO-entry sign, just the circle and slash.",
    "は": "A post and someone laughing with their belly out: HA!",
    "ひ": "One huge grin: HEE hee.",
    "ふ": "Four little pieces scattering when you blow: FOO.",
    "へ": "A small hill: HEY, come up here.",
    "ほ": "は with an extra roof bar: a HOtel with a rooftop.",
    "ま": "MAma with two arms out and a baby curled up below.",
    "み": "A loop with a long tail: a MEerkat sitting up.",
    "む": "A cow's face with a loop for a nose: MOO.",
    "め": "An eye, and め really does mean eye. Say MAY: may I look? No end loop.",
    "も": "A fishhook with two worms: MOre bait.",
    "や": "A YAk's head with its horns sticking out.",
    "ゆ": "A YOU-turn arrow with a line cut through it.",
    "よ": "A YO-yo hanging from a finger: bar on top, loop below.",
    "ら": "A RApper with one hand up, leaning back.",
    "り": "Two REEds swaying in the wind.",
    "る": "ろ with a loop: a long ROUTE ending in a roundabout.",
    "れ": "Someone down on one knee, RAYsing a leg.",
    "ろ": "る without the loop: this ROad just ends.",
    "わ": "A stick figure with a round belly, WAddling.",
    "を": "Someone sprinting, with a ball flying past: WHOA. Read o.",
    "ん": "A handwritten n with a flick at the end.",
    # katakana
    "ア": "An Axe: a blade with a long handle. AH!",
    "イ": "An EAsel leaning on one leg.",
    "ウ": "う wearing a flat cap. OOF, tight cap.",
    "エ": "A steel beam, like the one in an Elevator shaft.",
    "オ": "An OPera singer, arms flung wide: OH!",
    "カ": "か without the spark: a KArate chop, sharper.",
    "キ": "A KEY with two cuts across its shaft.",
    "ク": "A bite out of a COOkie.",
    "ケ": "A KEg on a slanted ramp.",
    "コ": "A COrner: two sides of a box.",
    "サ": "A SAddle on a crossbar, with a strap hanging down.",
    "シ": "SHE smiles: two short lashes and a smile rising from the left.",
    "ス": "The legs of a SUit, walking away.",
    "セ": "A person in profile, mouth open: SAY it.",
    "ソ": "Two stitches falling down: SEW. Long stroke falls from the top.",
    "タ": "A TAco, folded, with a filling line across it.",
    "チ": "A CHEerleader, arms up, one leg kicking.",
    "ツ": "Three drops falling from the top: a TSUnami of rain.",
    "テ": "A TElephone pole: two crossbars and a slanted leg.",
    "ト": "A TOtem pole with one branch.",
    "ナ": "A cross with a long slanted handle: a KNIfe.",
    "ニ": "Two lines, and に means two: KNEE, NEE, NEE.",
    "ヌ": "Chopsticks crossing over a NOOdle.",
    "ネ": "A NEcktie on a little hanger.",
    "ノ": "One stroke. A clean NO.",
    "ハ": "Two lines opening like a laughing mouth: HA!",
    "ヒ": "The HEEl of a shoe, seen from the side.",
    "フ": "A hook blown sideways: FOO.",
    "ヘ": "The same small hill as へ: HEY.",
    "ホ": "A HOly cross with two candles beside it.",
    "マ": "MAma's folded apron.",
    "ミ": "Three lines. ME, ME, ME.",
    "ム": "A cow's snout pointing up: MOO.",
    "メ": "An X crossing out an eye. Say MAY.",
    "モ": "も with straighter lines: MOre bait.",
    "ヤ": "A YAk's horn, slanted.",
    "ユ": "A U on its side: U, YOU.",
    "ヨ": "Three shelves of YOghurt.",
    "ラ": "A RApper in a flat hat.",
    "リ": "Two REEds, stiffer than り.",
    "ル": "Two ROOts hanging down, one hooking outward.",
    "レ": "A RElaxing chair: one back, one seat.",
    "ロ": "A square ROom with no door.",
    "ワ": "A WAter tap: flat top, one long spout.",
    "ヲ": "ワ with an extra bar: WHOA, too heavy. Read o, and rarely seen.",
    "ン": "A flat dash and a stroke rising from the bottom: a tired 'nnn'.",
}

LOOKALIKES: list[tuple[str, ...]] = [
    ("ぬ", "め"), ("ね", "れ", "わ"), ("は", "ほ", "け"), ("さ", "き", "ち"), ("る", "ろ"), ("い", "り"),
    ("あ", "お"), ("ま", "も"), ("た", "な"), ("こ", "に"), ("す", "む"), ("つ", "し"), ("く", "へ"), ("ら", "う"),
    ("シ", "ツ"), ("ソ", "ン"), ("ノ", "メ"), ("ク", "ケ", "タ"), ("ス", "ヌ"), ("ア", "マ"), ("ウ", "ワ", "フ"),
    ("コ", "ユ", "ロ"), ("チ", "テ", "ナ"), ("ラ", "ヲ"), ("ル", "レ"), ("ニ", "ミ"), ("エ", "ヨ"), ("カ", "ヤ"),
]

_ALIKE: dict[str, list[str]] = {}
for _group in LOOKALIKES:
    for _ch in _group:
        _ALIKE.setdefault(_ch, []).extend(c for c in _group if c != _ch)


def hook_for(char: str) -> str:
    return HOOKS.get(char, "")


def alike(char: str) -> list[str]:
    """Kana this one gets mistaken for."""
    return list(_ALIKE.get(char, []))

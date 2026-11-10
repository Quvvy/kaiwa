"""Decks from Anki (Kaishi): reading a collection without changing it, carrying memory over,
easiest-first catch-up, paused cards, new words after the course. A fake collection, no network."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["KAIWA_DATA_DIR"] = tempfile.mkdtemp(prefix="kaiwa-kaishi-smoke-")

from fastapi.testclient import TestClient  # noqa: E402

from kaiwa import phone_access  # noqa: E402
from kaiwa.app import app  # noqa: E402
from kaiwa.course import anki_import, imported, srs  # noqa: E402
from kaiwa.course import state as course_state  # noqa: E402

FIELDS = ["Word", "Word Reading", "Word Meaning", "Word Furigana", "Word Audio", "Sentence", "Sentence Meaning",
          "Sentence Furigana", "Sentence Audio", "Notes", "Pitch Accent", "Pitch Accent Notes", "Frequency", "Picture"]
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _check(ok: bool, label: str) -> None:
    sys.stdout.buffer.write((("ok  " if ok else "FAIL") + label + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()
    if not ok:
        raise SystemExit(f"smoke_kaishi failed: {label}")


def _unicase(a: str, b: str) -> int:
    return (a.lower() > b.lower()) - (a.lower() < b.lower())


def fake_collection(root: Path) -> Path:
    """A tiny Anki profile: one Kaishi-shaped note type, a welcome note, studied / suspended / new
    cards with FSRS data, a revlog, media files, and a write-ahead log like a running Anki."""
    prof = root / "Anki2" / "User 1"
    media = prof / "collection.media"
    media.mkdir(parents=True)
    path = prof / "collection.anki2"
    db = sqlite3.connect(path)
    db.execute("pragma journal_mode=wal")
    db.create_collation("unicase", _unicase)
    db.executescript("""
      create table col (id integer primary key, crt integer);
      create table decks (id integer primary key, name text collate unicase);
      create table notetypes (id integer primary key, name text collate unicase);
      create table fields (ntid integer, ord integer, name text collate unicase);
      create table notes (id integer primary key, mid integer, flds text);
      create table cards (id integer primary key, nid integer, did integer, type integer, queue integer, due integer,
                          ivl integer, factor integer, reps integer, lapses integer, data text);
      create table revlog (id integer primary key, cid integer, type integer);
    """)
    db.execute("insert into col values (1, 1700000000)")
    db.execute("insert into decks values (1, 'Default'), (2, 'Decks Main\x1fKaishi 1.5k')")
    db.execute("insert into notetypes values (10, 'Kaishi 1.5k')")
    db.executemany("insert into fields values (10, ?, ?)", list(enumerate(FIELDS)))
    now = datetime.now(timezone.utc)

    def note(nid, word, reading, meaning, sentence, sent_meaning, furigana, n):
        vals = [word, reading, meaning, f"{word}[{reading}]", f"[sound:w{n}.mp3]", sentence, sent_meaning, furigana,
                f"[sound:s{n}.mp3]", f"Note {n}<br>more", "", "", str(n), f'<img src="p{n}.png">']
        (media / f"w{n}.mp3").write_bytes(MP3)
        (media / f"s{n}.mp3").write_bytes(MP3)
        (media / f"p{n}.png").write_bytes(PNG)
        db.execute("insert into notes values (?, 10, ?)", (nid, "\x1f".join(vals)))

    db.execute("insert into notes values (99, 10, ?)", ("\x1f".join(["Welcome!", "", "", "", "", "<br>Kaishi (開始) is a modular deck", "Good luck!", "", "", "", "", "", "0", ""]),))
    db.execute("insert into cards values (99, 99, 2, 2, 2, 0, 1, 2500, 1, 0, '{}')")
    sentences = [
        (1, "私", "わたし", "I", "<b>私</b>はアンです。", "I am Ann.", "<b>私[わたし]</b>はアンです。"),
        (2, "食べる", "たべる", "to eat", "パンを<b>食べる</b>。", "I eat bread.", "パンを<b>食[た]べる</b>。"),
        (3, "空", "そら", "sky", "<b>空</b>が青い。", "The sky is blue.", "<b>空[そら]</b>が 青[あお]い。"),
        (4, "猫", "ねこ", "cat", "<b>猫</b>がいる。", "There's a cat.", "<b>猫[ねこ]</b>がいる。"),
        (5, "おはよう", "おはよう", "good morning", "<b>おはよう</b>ございます。", "Good morning.", "<b>おはよう</b>ございます。"),
        (6, "本", "ほん", "book", "<b>本</b>を読む。", "I read a book.", "<b>本[ほん]</b>を 読[よ]む。"),
    ]
    for n, word, reading, meaning, sent, sm, furi in sentences:
        note(n, word, reading, meaning, sent, sm, furi, n)
    lrt = int((now - timedelta(days=60)).timestamp())
    # 1: studied, weak memory, long overdue. 2: studied, strong memory. 3: suspended. 4: new.
    # 5: new, but the course teaches おはよう (skipped). 6: an old SM-2 review card (no FSRS data).
    db.execute("insert into cards values (1, 1, 2, 2, 2, 0, 3, 2500, 9, 2, ?)", (json.dumps({"s": 2.0, "d": 7.0, "lrt": lrt}),))
    db.execute("insert into cards values (2, 2, 2, 2, 2, 0, 90, 2500, 6, 0, ?)", (json.dumps({"s": 120.0, "d": 4.0, "lrt": lrt}),))
    db.execute("insert into cards values (3, 3, 2, 2, -1, 0, 5, 2500, 4, 1, ?)", (json.dumps({"s": 5.0, "d": 6.0, "lrt": lrt}),))
    db.execute("insert into cards values (4, 4, 2, 0, 0, 1, 0, 0, 0, 0, '')")
    db.execute("insert into cards values (5, 5, 2, 0, 0, 2, 0, 0, 0, 0, '')")
    db.execute("insert into cards values (6, 6, 2, 2, 2, 0, 14, 2300, 3, 0, '')")
    ms = int((now - timedelta(days=60)).timestamp() * 1000)
    db.executemany("insert into revlog values (?, ?, 1)", [(ms + i, cid) for i, cid in enumerate([1, 1, 2, 3, 6])])
    db.commit()  # left open: the newest rows stay in the -wal file, as with a running Anki
    fake_collection.keep = db
    return path


def reader(coll: Path, roots: list[Path]) -> int:
    _check(anki_import.furigana_to_kana("<b>私[わたし]</b>は アン です。") == "わたしはアンです。", "furigana becomes a kana line")
    _check(anki_import.furigana_to_kana("お 茶[ちゃ]を 飲[の]みます") == "おちゃをのみます", "leading kana are kept, kanji replaced")
    roles = anki_import.detect_fields(FIELDS)
    _check({"sentence", "sentence_meaning", "sentence_furigana", "sentence_audio", "word", "word_reading", "word_meaning",
            "word_audio", "notes", "picture", "frequency"} <= roles.keys(), "Kaishi's fields are all recognised")
    _check(anki_import.detect_fields(["Front", "Back"]) == {}, "a deck with no sentence fields isn't offered")
    found = anki_import.find_collections(roots)
    _check(len(found) == 1 and found[0]["profile"] == "User 1", "the Anki profile is found")
    _check(anki_import.is_collection_path(str(coll), roots) and not anki_import.is_collection_path("/etc/passwd", roots)
           and not anki_import.is_collection_path(str(coll.parent / "collection.media" / "s1.mp3"), roots),
           "only real collections under Anki's folders may be opened")
    decks = anki_import.list_decks(coll)
    _check(len(decks) == 1 and decks[0]["name"] == "Decks Main::Kaishi 1.5k" and decks[0]["suspended"] == 1, "the deck is listed with its counts")
    read = anki_import.read_deck(coll, decks[0]["id"])
    rows = read["rows"]
    _check(len(rows) == 6 and all(r["text"] != "" for r in rows), "the welcome note is skipped; every sentence comes in")
    r1 = next(r for r in rows if r["anki_nid"] == 1)
    _check(r1["text"] == "私はアンです。" and r1["word"] == "私" and r1["kana"] == "わたしはアンです。" and r1["en"] == "I am Ann."
           and r1["sentence_audio"] == "s1.mp3" and r1["picture"] == "p1.png" and r1["notes"] == "Note 1 more",
           "a row has the sentence, word, kana line, meaning, media and note")
    _check(r1["anki"]["stability"] == 2.0 and r1["anki"]["last_review"], "Anki's FSRS memory is read")
    r6 = next(r for r in rows if r["anki_nid"] == 6)
    _check(r6["anki"]["stability"] == 14.0, "an old SM-2 card's interval stands in for its stability")
    return decks[0]["id"]


def importing(coll: Path, deck_id: int) -> Path:
    before = hashlib.sha256(coll.read_bytes()).hexdigest()
    wal = coll.with_name("collection.anki2-wal")
    wal_before = hashlib.sha256(wal.read_bytes()).hexdigest() if wal.exists() else ""
    path = course_state.state_path()
    out = course_state.import_anki_deck(str(coll), deck_id, path=path)
    _check(out["rows"] == 6 and out["added"] == 4 and out["paused"] == 1 and out["new"] == 2,
           "4 studied cards come in (1 paused), 2 new words wait")
    _check(hashlib.sha256(coll.read_bytes()).hexdigest() == before
           and (not wal.exists() or hashlib.sha256(wal.read_bytes()).hexdigest() == wal_before),
           "the Anki collection (and its WAL) is never changed")
    st = course_state.load_state(path)
    card1 = st["cards"]["kaishi.1:listen"]
    _check(abs(srs.stability(card1) - 2.0) < 1e-6 and card1["fsrs"]["difficulty"] == 7.0 and card1["reps"] == 9,
           "the memory carries over: stability, difficulty, reps")
    _check(st["cards"]["kaishi.3:listen"].get("paused") is True, "a suspended card comes in paused")
    _check("kaishi.4:listen" not in st["cards"], "a new word gets no card yet")
    media = imported.media_dir(path.parent)
    _check(len(list(media.iterdir())) == 18, "audio and pictures are copied (18 files)")
    data = imported.load(path.parent, "kaishi")
    _check(all(len(r["wrong"]) == 2 and r["en"] not in r["wrong"] and len(set(r["wrong"])) == 2 for r in data["rows"]),
           "every row has two different wrong meanings, none of them its own")
    return path


def scheduling(path: Path) -> None:
    st = course_state.load_state(path)
    lines = [c for c in course_state.todays_reviews(st) if c["kind"] == "line"]
    ids = [c["card_id"] for c in lines]
    _check("kaishi.3:listen" not in ids, "paused cards stay out of reviews")
    _check(ids and ids[0] != "kaishi.1:listen" and "kaishi.1:listen" in ids, "easiest to recover comes first, the weakest last")
    rs = [srs.retrievability(st["cards"][i]) for i in ids]
    _check(rs == sorted(rs, reverse=True), "ordered by how likely you are to remember")
    _check(all(c["line"]["audio_url"] and c["line"]["word_meaning"] and len(c["line"]["wrong"]) == 2 for c in lines),
           "a card carries its audio, word and options")
    _check(course_state.answer_format("line", "listen", st["cards"]["kaishi.1:listen"]) == "recall", "a known card is recalled")
    _check(not course_state.todays_imported_new(st), "new words wait until the course is done")
    lim = course_state.limits_view(st)["decks"]["kaishi"]["fields"]
    _check(lim["new_per_day"]["value"] == 10 and lim["max_reviews"]["value"] == 20 and "lesson_minutes" not in lim,
           "Kaishi starts at 10 new and 20 reviews a day")

    # The daily share stops at the deck's limit.
    course_state.set_limits("kaishi", {"max_reviews": 2}, path=path)
    st = course_state.load_state(path)
    _check(len([c for c in course_state.todays_reviews(st) if c["kind"] == "line"]) == 2, "the Kaishi review limit holds")
    course_state.set_limits("kaishi", {"max_reviews": None}, path=path)

    # Finish the course: now new words come, in Kaishi's order, skipping words the course taught.
    real_next = course_state.next_unit
    course_state.next_unit = lambda state: None
    try:
        st = course_state.load_state(path)
        taught = course_state._course_word_keys()
        expected = [f"kaishi.{n}:listen" for n, reading in ((4, "ねこ"), (5, "おはよう")) if reading not in taught]
        new = [c["card_id"] for c in course_state.todays_imported_new(st)]
        _check(new == expected and ("ねこ" not in taught or "kaishi.4:listen" not in new),
               "after the course, new Kaishi words come in order, skipping words the course taught")
        plan = course_state.plan_today(st)
        _check(("kaishi" in plan["plan"]) == bool(expected), "a 'New words' step appears in the day")
        first = expected[0]
        course_state.grade(first, correct=True, ms=4000, fmt="line:listen", path=path)
        st = course_state.load_state(path)
        by = st["daily"][course_state._today().isoformat()]["new_by_deck"]
        _check(first in st["cards"] and by.get("kaishi") == 1, "answering a new word makes its card, counted as Kaishi new")
    finally:
        course_state.next_unit = real_next

    _check(course_state.unpause_imported("kaishi", ["kaishi.3"], path=path) == 1
           and "paused" not in course_state.load_state(path)["cards"]["kaishi.3:listen"], "a paused card can be unpaused")
    stats = course_state.course_stats(path=path)
    _check("Kaishi" in stats["stages"], "stats know Kaishi cards")


def reimport(coll: Path, deck_id: int, path: Path) -> None:
    st = course_state.load_state(path)
    before = dict(st["cards"]["kaishi.1:listen"])
    course_state.grade("kaishi.2:listen", correct=False, ms=4000, fmt="line:recall", path=path)
    graded = dict(course_state.load_state(path)["cards"]["kaishi.2:listen"])
    out = course_state.import_anki_deck(str(coll), deck_id, path=path)
    st = course_state.load_state(path)
    _check(out["added"] == 0 and out["kept"] >= 4, "a re-import adds nothing that's already there")
    _check(st["cards"]["kaishi.2:listen"] == graded and st["cards"]["kaishi.1:listen"]["fsrs"] == before["fsrs"],
           "Kaiwa's progress is kept on re-import")


def routes(coll: Path, roots: list[Path]) -> None:
    client = TestClient(app)
    path = course_state.state_path()
    rows = imported.load(path.parent, "kaishi")["rows"]
    name = rows[0]["audio"]
    got = client.get(f"/api/course/imported/media/{name}")
    _check(got.status_code == 200 and got.headers["content-type"].startswith("audio/"), "an imported clip is served")
    for bad in ("..%2Fcourse_state.json", "0123456789ab-nope.mp3"):
        _check(client.get(f"/api/course/imported/media/{bad}").status_code in (404, 405), f"nothing else is served ({bad})")
    listing = client.get("/api/course/imported/kaishi").json()
    _check(listing["counts"]["rows"] == 6 and listing["rows"][0]["text"], "the deck page lists its cards")
    _check(client.get("/api/course/anki/decks", params={"path": "/etc/passwd"}).status_code == 400, "arbitrary files can't be read as Anki")
    _check(phone_access.refuses_remote("/api/course/anki/collections", "GET"), "the phone can't browse Anki on the PC")
    _check(not phone_access.refuses_remote("/api/course/imported/media/x.mp3", "GET"), "the phone can still play imported audio")


def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        coll = fake_collection(root)
        roots = [root / "Anki2"]
        deck_id = reader(coll, roots)
        path = importing(coll, deck_id)
        scheduling(path)
        reimport(coll, deck_id, path)
        routes(coll, roots)
    print("smoke_kaishi ok")


if __name__ == "__main__":
    main()

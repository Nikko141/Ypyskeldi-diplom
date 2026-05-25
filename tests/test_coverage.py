"""Запускает тестовый корпус и считает метрику Coverage.

Usage:  python -m tests.test_coverage
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from morphology import MorphDatabase, MorphAnalyzer, MorphGenerator


def load_corpus(path: Path) -> list:
    raw = path.read_bytes().replace(b"\x00", b"")
    last = raw.rfind(b"}")
    return json.loads(raw[: last + 1].decode("utf-8"))["items"]


def test_coverage():
    db = MorphDatabase(ROOT / "data")
    an = MorphAnalyzer(db)
    corpus = load_corpus(ROOT / "data" / "test_corpus.json")

    n = len(corpus)
    covered = 0
    lemma_ok = 0
    tag_ok = 0
    rows = []

    for item in corpus:
        form = item["form"]
        exp_lemma = item["expected_lemma"]
        exp_tags = set(item.get("tags", []))
        analyses = an.analyze(form)
        if analyses:
            covered += 1
            if any(a.lemma == exp_lemma for a in analyses):
                lemma_ok += 1
            if any(a.lemma == exp_lemma and set([a.pos, *a.tags]) == exp_tags
                   for a in analyses):
                tag_ok += 1
            best = analyses[0].pretty()
        else:
            best = "—"
        rows.append((form, exp_lemma, best))

    print(f"\n{'Слово':<20} {'Лемма ожид.':<15} {'Лучший разбор'}")
    print("-" * 80)
    for f, l, b in rows:
        print(f"{f:<20} {l:<15} {b}")

    print()
    print(f"Тестов:      {n}")
    print(f"Coverage:    {covered/n:.1%}  ({covered}/{n})")
    print(f"Lemma acc.:  {lemma_ok/n:.1%}  ({lemma_ok}/{n})")
    print(f"Full tag acc.: {tag_ok/n:.1%}  ({tag_ok}/{n})")
    return covered, n


def test_roundtrip():
    """Проверка: analyze(generate(lemma, tags)) содержит исходный (lemma, tags)?"""
    db = MorphDatabase(ROOT / "data")
    gen = MorphGenerator(db)
    an = MorphAnalyzer(db)
    samples = [
        ("бала", "N", ["Pl"]),
        ("бала", "N", ["Px1Sg"]),
        ("бала", "N", ["Pl", "Px1Sg", "Loc"]),
        ("үй", "N", ["Loc"]),
        ("үй", "N", ["Pl", "Loc"]),
        ("көл", "N", ["Dat"]),
        ("көл", "N", ["Pl", "Px1Sg", "Loc"]),
        ("бар", "V", ["Pst", "1Sg"]),
        ("кел", "V", ["Neg", "Pst", "1Sg"]),
        ("көр", "V", ["Pst", "3"]),
        ("көр", "V", ["Neg", "Pst", "1Sg"]),
        ("чоң", "ADJ", ["Comp"]),
    ]
    print("\nRoundtrip generate → analyze:")
    ok = 0
    for lemma, pos, tags in samples:
        g = gen.generate(lemma, pos, tags)
        if g is None:
            print(f"  ✗  {lemma}+{tags}: не сгенерировано")
            continue
        an_results = an.analyze(g.form)
        match = any(a.lemma == lemma and a.tags == tags for a in an_results)
        mark = "✓" if match else "✗"
        if match:
            ok += 1
        print(f"  {mark}  {lemma}+{tags} → {g.form} → {[a.pretty() for a in an_results[:1]]}")
    print(f"\nRoundtrip: {ok}/{len(samples)} = {ok/len(samples):.0%}")


if __name__ == "__main__":
    test_coverage()
    test_roundtrip()

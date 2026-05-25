"""Генератор словоформ кыргызского языка.

Обратная сторона двухуровневой модели:
    LEXICAL "бала<Pl><Px1Sg><Loc>"  ──►  SURFACE "балаларымда"

Алгоритм:
    1. На вход подаётся корень + список тегов.
    2. По автомату проверяем, что последовательность тегов допустима.
    3. Поочерёдно «приклеиваем» аллoморфы аффиксов, выбирая нужный по
       правилам сингармонизма от ТЕКУЩЕЙ накопленной основы.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from .database import MorphDatabase
from .harmony import HarmonyClassifier
from .automaton import build_master_automaton


@dataclass
class GenerationResult:
    form: str
    pos: str
    lemma: str
    tags: List[str]
    steps: List[str]   # промежуточные формы для трассировки


class MorphGenerator:
    """Генератор словоформ из (корень, теги)."""

    def __init__(self, db: MorphDatabase):
        self.db = db
        self.automata = build_master_automaton()
        self.harmony = HarmonyClassifier()
        # Индекс tag -> affix dict для каждой части речи
        self._tag_to_affix = {}
        for pos, autom in self.automata.items():
            by_tag = {}
            for af in db.affixes_for_category(pos):
                by_tag[af["tag"]] = af
            self._tag_to_affix[pos] = by_tag

    def generate(self, lemma: str, pos: str, tags: List[str]) -> Optional[GenerationResult]:
        """Сгенерировать словоформу.

        Возвращает None, если последовательность тегов не допускается
        автоматом или какого-то тега нет в базе аффиксов.
        """
        automaton = self.automata.get(pos)
        if automaton is None:
            return None
        affix_by_tag = self._tag_to_affix.get(pos, {})

        # Проверка корня
        if not self.db.get_root(lemma):
            # лемма не найдена в словаре, но всё равно попытаемся сгенерировать
            pass

        state = automaton.start
        form = lemma
        steps = [form]
        for tag in tags:
            af = affix_by_tag.get(tag)
            if af is None:
                return None
            category = af["category"]
            next_states = automaton.next_states(state, category)
            if not next_states:
                return None  # морфотактика не допускает этот тег здесь
            surface = self.harmony.pick_allomorph(form, af["variants"])
            form = form + surface
            steps.append(form)
            state = next_states[0]

        if not automaton.is_final(state):
            return None
        return GenerationResult(form=form, pos=pos, lemma=lemma, tags=list(tags), steps=steps)

    def paradigm(self, lemma: str, pos: str) -> List[GenerationResult]:
        """Сгенерировать минимальную парадигму для леммы."""
        out: List[GenerationResult] = []
        if pos in ("N", "PRON", "NUM"):
            cases = ["Nom", "Gen", "Dat", "Acc", "Loc", "Abl"]
            for case in cases:
                tags = [] if case == "Nom" else [case]
                r = self.generate(lemma, pos, tags)
                if r:
                    out.append(r)
            # Множественное число
            for case in cases:
                tags = ["Pl"] if case == "Nom" else ["Pl", case]
                r = self.generate(lemma, pos, tags)
                if r:
                    out.append(r)
            # Притяжательность
            for px in ["Px1Sg", "Px2Sg", "Px2SgPol", "Px3", "Px1Pl", "Px2Pl"]:
                r = self.generate(lemma, pos, [px])
                if r:
                    out.append(r)
        elif pos == "V":
            persons = ["1Sg", "2Sg", "3", "1Pl", "2Pl"]
            for tense in ["Pst", "Perf"]:
                for p in persons:
                    r = self.generate(lemma, pos, [tense, p])
                    if r:
                        out.append(r)
            # Отрицание
            for p in persons:
                r = self.generate(lemma, pos, ["Neg", "Pst", p])
                if r:
                    out.append(r)
        elif pos == "ADJ":
            for tag in ["Comp", "Abstr"]:
                r = self.generate(lemma, pos, [tag])
                if r:
                    out.append(r)
        return out

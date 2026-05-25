"""Морфологический анализатор кыргызского языка.

Алгоритм (две стороны двухуровневой модели Коскенниеми):
    SURFACE  ─── снятие аллoморфов (правая часть слова) ───►  LEXICAL
    "балаларымда"      lar — Px1Sg — Loc                 "бала<Pl><Px1Sg><Loc>"

Алгоритм работает СПРАВА НАЛЕВО:

   1. На вход подаётся словоформа w (поверхностная цепочка).
   2. Для каждой возможной длины суффикса k:
        s = w[: -k]   — остаток (будущая основа после снятия суффикса)
        a = w[-k:]    — суффикс
      проверяем: соответствует ли a какому-либо аллoморфу аффикса A,
      и был бы этот аллoморф выбран по сингармонизму к s?
   3. Если да — рекурсивно снимаем следующий суффикс с s.
   4. Когда s совпадает с корнем R из словаря, проверяем, что
      пройденный путь по морфотактическому автомату завершается в финальном
      состоянии. Если да — это валидный разбор.

Возвращается список всех валидных разборов (Analysis).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .database import MorphDatabase
from .harmony import HarmonyClassifier
from .automaton import MorphAutomaton, build_master_automaton


@dataclass
class MorphemeSegment:
    """Один сегмент разбора: либо корень, либо аффикс."""
    surface: str        # как выглядит в слове ('лар', 'м', 'да')
    lexical: str        # лексический тег ('Pl', 'Px1Sg', 'Loc') или сам корень
    category: str       # категория аффикса; для корня — pos
    is_root: bool = False
    gloss: str = ""

    def __str__(self) -> str:
        if self.is_root:
            return f"{self.surface}[{self.category}]"
        return f"-{self.surface}[{self.lexical}]"


@dataclass
class Analysis:
    """Один полный разбор словоформы."""
    lemma: str                      # лемма (исходный корень)
    pos: str                        # часть речи
    tags: List[str]                 # лексические теги в порядке (Pl, Px1Sg, Loc, …)
    segments: List[MorphemeSegment] # пошаговое разложение слева направо
    gloss: str = ""                 # подсказка

    def pretty(self) -> str:
        # Корень + теги в стандартной нотации: бала<N><Pl><Px1Sg><Loc>
        tag_str = "".join(f"<{t}>" for t in self.tags)
        return f"{self.lemma}<{self.pos}>{tag_str}"

    def segmentation(self) -> str:
        # бала-лар-ым-да
        return "-".join(s.surface for s in self.segments)


class MorphAnalyzer:
    """Анализатор словоформ."""

    def __init__(self, db: MorphDatabase):
        self.db = db
        self.automata = build_master_automaton()
        self.harmony = HarmonyClassifier()

    # ---------- основной интерфейс ----------
    def analyze(self, word: str) -> List[Analysis]:
        """Возвращает список всех валидных разборов словоформы."""
        word = word.strip().lower()
        results: List[Analysis] = []
        seen: set = set()
        # Перебираем все корни как кандидаты (от длинного к короткому)
        roots = sorted(self.db.all_roots(), key=lambda r: -len(r["root"]))
        for entry in roots:
            root = entry["root"].lower()
            if not word.startswith(root):
                continue
            pos = entry["pos"]
            automaton = self.automata.get(pos)
            if automaton is None:
                continue
            remainder = word[len(root):]
            # Пытаемся «надстраивать» суффиксы слева направо
            for analysis in self._build(
                root=root, pos=pos, entry=entry,
                state=automaton.start, automaton=automaton,
                stem_so_far=root, remainder=remainder,
                tags=[], segments=[],
            ):
                key = analysis.pretty() + "|" + analysis.segmentation()
                if key in seen:
                    continue
                seen.add(key)
                results.append(analysis)
        # Сортировка: чем короче список тегов, тем «проще» разбор
        results.sort(key=lambda a: (len(a.tags), len(a.lemma) * -1))
        return results

    # ---------- рекурсивный обход ----------
    def _build(
        self,
        root: str,
        pos: str,
        entry: dict,
        state: str,
        automaton: MorphAutomaton,
        stem_so_far: str,
        remainder: str,
        tags: List[str],
        segments: List[MorphemeSegment],
    ):
        """Генератор валидных разборов."""
        # Если суффиксов не осталось — попробовать завершить разбор
        if not remainder:
            if automaton.is_final(state):
                # начальный сегмент = корень
                root_seg = MorphemeSegment(
                    surface=root, lexical=root, category=pos,
                    is_root=True, gloss=entry.get("gloss", ""),
                )
                full_segments = [root_seg] + segments
                yield Analysis(
                    lemma=root, pos=pos,
                    tags=list(tags),
                    segments=full_segments, gloss=entry.get("gloss", ""),
                )
            return

        # Перебираем возможные следующие категории
        for category in automaton.allowed_categories(state):
            for affix in self._affixes_in_category(pos, category):
                # Перебираем все аллoморфы аффикса
                for surface in self._candidate_surfaces(affix):
                    if not remainder.startswith(surface) or surface == "":
                        continue
                    # Проверка сингармонизма: подходит ли surface к stem_so_far?
                    expected = self.harmony.pick_allomorph(stem_so_far, affix["variants"])
                    if expected != surface:
                        continue
                    new_stem = stem_so_far + surface
                    new_remainder = remainder[len(surface):]
                    seg = MorphemeSegment(
                        surface=surface, lexical=affix["tag"],
                        category=category, gloss=affix.get("gloss", ""),
                    )
                    for nxt in automaton.next_states(state, category):
                        yield from self._build(
                            root=root, pos=pos, entry=entry,
                            state=nxt, automaton=automaton,
                            stem_so_far=new_stem,
                            remainder=new_remainder,
                            tags=tags + [affix["tag"]],
                            segments=segments + [seg],
                        )

    def _affixes_in_category(self, pos: str, category: str):
        for af in self.db.affixes_for_category(pos):
            if af["category"] == category:
                yield af

    @staticmethod
    def _candidate_surfaces(affix: dict):
        """Уникальные поверхностные формы из всех групп вариантов аффикса."""
        seen = set()
        for group in affix["variants"].values():
            for v in group.values():
                if v and v not in seen:
                    seen.add(v)
                    yield v

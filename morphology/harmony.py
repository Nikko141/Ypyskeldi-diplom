"""Модуль сингармонизма кыргызского языка.

Математическая модель:

Алфавит гласных Σ_V = {а, е, и, о, у, ө, ү, ы}.
Бинарные признаки гласного:
    f_palatal : V → {back, front}
        back  = {а, о, у, ы}
        front = {е, и, ө, ү}
    f_round   : V → {round, unround}
        round   = {о, ө, у, ү}
        unround = {а, е, ы, и}

Класс гармонии H(v) ∈ {a, e, o, ö} определяется парой признаков:
    a  = back  & unround   (после а, ы)
    e  = front & unround   (после е, и)
    o  = back  & round     (после о, у)
    ö  = front & round     (после ө, ү)

Гармония слова определяется ПОСЛЕДНИМ гласным основы:
    harmony(stem) = H(last_vowel(stem))

Алфавит согласных делится на классы:
    voiceless = {п, т, к, с, ш, ч, ф, х, ц, щ}
    voiced    = {б, д, г, з, ж, в}
    sonorant  = {м, н, ң, р, л, й}

Эти классы определяют выбор аллoморфа по начальному согласному аффикса
(ассимиляция по глухости/звонкости).
"""

from __future__ import annotations
from typing import Optional


# ---------- Алфавит кыргызского языка ----------
VOWELS = set("аеиоуөүы")

BACK_VOWELS = set("аоуы")      # задний ряд
FRONT_VOWELS = set("еиөү")     # передний ряд
ROUND_VOWELS = set("оөуү")     # огублённые
UNROUND_VOWELS = set("аеыи")   # неогублённые

VOICELESS = set("птксшчфхцщ")  # глухие согласные
VOICED = set("бдгзжв")         # звонкие согласные
SONORANT = set("мнңрлй")       # сонорные


class HarmonyClassifier:
    """Классификатор фонем по правилам сингармонизма.

    Используется и анализатором (для проверки допустимости разбора),
    и генератором (для выбора нужного аллoморфа).
    """

    @staticmethod
    def last_vowel(stem: str) -> Optional[str]:
        """Возвращает последний гласный основы или None."""
        for ch in reversed(stem):
            if ch in VOWELS:
                return ch
        return None

    @classmethod
    def harmony_class(cls, stem: str) -> str:
        """Возвращает класс гармонии слова: 'a', 'e', 'o' или 'ö'.

        Если в основе нет гласных, по умолчанию возвращается 'a'
        (нейтральный задний неогублённый класс).
        """
        v = cls.last_vowel(stem)
        if v is None:
            return "a"
        back = v in BACK_VOWELS
        rnd = v in ROUND_VOWELS
        if back and not rnd:
            return "a"
        if not back and not rnd:
            return "e"
        if back and rnd:
            return "o"
        return "ö"

    @staticmethod
    def ends_with_vowel(stem: str) -> bool:
        return bool(stem) and stem[-1] in VOWELS

    @staticmethod
    def last_consonant(stem: str) -> Optional[str]:
        """Возвращает последний согласный основы или None."""
        for ch in reversed(stem):
            if ch not in VOWELS and ch.isalpha():
                return ch
        return None

    @classmethod
    def consonant_context(cls, stem: str) -> str:
        """Возвращает контекст для выбора аллoморфа аффикса по согласному.

        Возвращает один из ключей:
            'after_vowel'      — основа кончается на гласный
            'after_sonorant'   — на сонорный (м,н,ң,р,л,й)
            'after_voiced'     — на звонкий (б,д,г,з,ж,в)
            'after_voiceless'  — на глухой (п,т,к,с,ш,ч,ф,х)
            'after_consonant'  — общий контекст «после согласного»
        """
        if cls.ends_with_vowel(stem):
            return "after_vowel"
        c = cls.last_consonant(stem)
        if c is None:
            return "after_vowel"
        if c in SONORANT:
            return "after_sonorant"
        if c in VOICELESS:
            return "after_voiceless"
        if c in VOICED:
            return "after_voiced"
        return "after_consonant"

    @classmethod
    def pick_allomorph(cls, stem: str, variants: dict) -> str:
        """Выбрать конкретный аллoморф аффикса по основе.

        variants — словарь вида:
            {
              "after_vowel": {"a": "лар", "e": "лер", "o": "лор", "ö": "лөр"},
              "after_consonant": {...},
              ...
            }

        Алгоритм:
          1) Определяем контекст согласного.
          2) Если такого контекста нет — пробуем 'after_consonant' / 'after_any'.
          3) Из выбранной группы берём нужный класс гармонии.
        """
        ctx = cls.consonant_context(stem)
        # Каскадный поиск группы
        group = None
        for key in (ctx, "after_consonant", "after_any"):
            if key in variants:
                group = variants[key]
                break
        if group is None:
            # Берём первый попавшийся (запасной вариант)
            group = next(iter(variants.values()))
        hc = cls.harmony_class(stem)
        return group.get(hc, group.get("a", ""))


def classify_vowel(ch: str) -> str:
    """Описание гласного в виде строки 'передний/задний + огублённый/неогуб.'."""
    if ch not in VOWELS:
        return "—"
    row = "передний" if ch in FRONT_VOWELS else "задний"
    rnd = "огублённый" if ch in ROUND_VOWELS else "неогублённый"
    return f"{row} {rnd}"


def classify_consonant(ch: str) -> str:
    if ch in VOICELESS:
        return "глухой"
    if ch in VOICED:
        return "звонкий"
    if ch in SONORANT:
        return "сонорный"
    return "—"

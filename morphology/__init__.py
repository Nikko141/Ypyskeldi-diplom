"""Морфологический анализатор кыргызского языка.

Модули:
    harmony       — правила сингармонизма и ассимиляции согласных
    database      — загрузка корней и аффиксов из JSON
    automaton     — конечный автомат, описывающий морфотактику
    analyzer      — морфологический анализатор (справа налево)
    generator     — генератор словоформ
"""
from .database import MorphDatabase
from .harmony import HarmonyClassifier
from .automaton import MorphAutomaton
from .analyzer import MorphAnalyzer, Analysis
from .generator import MorphGenerator

__all__ = [
    "MorphDatabase",
    "HarmonyClassifier",
    "MorphAutomaton",
    "MorphAnalyzer",
    "MorphGenerator",
    "Analysis",
]

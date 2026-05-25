"""Конечный автомат, описывающий морфотактику кыргызского языка.

Формально определяется детерминированный конечный автомат

        M = (Q, Σ, δ, q₀, F),

где
    Q  — конечное множество состояний (морфологических позиций),
    Σ  — алфавит входных символов = множество морфологических тегов,
    δ  — функция переходов Q × Σ → Q ∪ {⊥},
    q₀ — начальное состояние,
    F  — множество допускающих (финальных) состояний.

Каждое состояние q ∈ Q соответствует «слоту» в словоформе:
    NOUN_ROOT → NOUN_PL → NOUN_POSS → NOUN_CASE → END
    VERB_ROOT → VERB_NEG → VERB_TENSE → VERB_PERS → END
    ADJ_ROOT  → ADJ_DEG / ADJ_ABSTR_AS_N → ...

Каждое переход δ(q, t) = q' помечен набором допустимых тегов t.
Слово допускается, если существует путь q₀ →* qf, где qf ∈ F,
вход которого представим как последовательность аффиксов слова.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


# Категории аффиксов (метки рёбер).
CAT_PL = "Plural"
CAT_POSS = "Possessive"
CAT_CASE = "Case"
CAT_NEG = "Negation"
CAT_TENSE = "Tense"
CAT_PERS = "PersonNumber"
CAT_IMP = "Imperative"
CAT_DEG = "Degree"
CAT_DERIV = "Derivation"


@dataclass(frozen=True)
class State:
    """Состояние FSA."""
    name: str
    is_final: bool = False  # допускающее состояние


@dataclass
class MorphAutomaton:
    """Морфотактический автомат.

    Граф представлен в виде словаря переходов:
        transitions[q] = [(category, q_next), ...]
    """

    states: Dict[str, State] = field(default_factory=dict)
    transitions: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    start: str = "START"

    # ---------- построение ----------
    def add_state(self, name: str, is_final: bool = False) -> None:
        self.states[name] = State(name=name, is_final=is_final)
        self.transitions.setdefault(name, [])

    def add_transition(self, src: str, category: str, dst: str) -> None:
        self.transitions[src].append((category, dst))

    # ---------- использование ----------
    def is_final(self, state: str) -> bool:
        st = self.states.get(state)
        return bool(st and st.is_final)

    def next_states(self, state: str, category: str) -> List[str]:
        return [dst for cat, dst in self.transitions.get(state, []) if cat == category]

    def allowed_categories(self, state: str) -> Set[str]:
        return {cat for cat, _ in self.transitions.get(state, [])}


# -------------------- построение автоматов для частей речи --------------------

def build_noun_automaton() -> MorphAutomaton:
    """Существительные / местоимения:
        ROOT → [Pl] → [Poss] → [Case] → END (все три слота опциональны).
    """
    M = MorphAutomaton(start="N_ROOT")

    M.add_state("N_ROOT", is_final=True)       # одна основа без суффиксов = слово в Nom
    M.add_state("N_AFTER_PL", is_final=True)
    M.add_state("N_AFTER_POSS", is_final=True)
    M.add_state("N_AFTER_CASE", is_final=True)

    # Pl — может быть, может не быть
    M.add_transition("N_ROOT", CAT_PL, "N_AFTER_PL")
    M.add_transition("N_ROOT", CAT_POSS, "N_AFTER_POSS")
    M.add_transition("N_ROOT", CAT_CASE, "N_AFTER_CASE")
    M.add_transition("N_ROOT", CAT_DERIV, "N_ROOT")  # деривация даёт новую основу

    # После Pl: Poss или Case
    M.add_transition("N_AFTER_PL", CAT_POSS, "N_AFTER_POSS")
    M.add_transition("N_AFTER_PL", CAT_CASE, "N_AFTER_CASE")

    # После Poss: Case
    M.add_transition("N_AFTER_POSS", CAT_CASE, "N_AFTER_CASE")

    return M


def build_verb_automaton() -> MorphAutomaton:
    """Глаголы:
        ROOT → [Neg] → Tense → [PersNumber] → END

    Tense обязателен (исключение — императив на голой основе).
    """
    M = MorphAutomaton(start="V_ROOT")

    M.add_state("V_ROOT", is_final=True)         # голая основа = повел. ты
    M.add_state("V_AFTER_NEG", is_final=False)
    M.add_state("V_AFTER_TENSE", is_final=True)
    M.add_state("V_AFTER_PERS", is_final=True)

    M.add_transition("V_ROOT", CAT_NEG, "V_AFTER_NEG")
    M.add_transition("V_ROOT", CAT_TENSE, "V_AFTER_TENSE")
    M.add_transition("V_ROOT", CAT_IMP, "V_AFTER_PERS")  # императив 2pl

    M.add_transition("V_AFTER_NEG", CAT_TENSE, "V_AFTER_TENSE")

    M.add_transition("V_AFTER_TENSE", CAT_PERS, "V_AFTER_PERS")

    return M


def build_adjective_automaton() -> MorphAutomaton:
    """Прилагательные:
        ROOT → [Deg] → END
        ROOT → [Abstr→ имя]  (происходит конверсия, дальше как существительное)
    """
    M = MorphAutomaton(start="ADJ_ROOT")

    M.add_state("ADJ_ROOT", is_final=True)
    M.add_state("ADJ_AFTER_DEG", is_final=True)
    M.add_state("ADJ_AS_N", is_final=True)  # после деривации в существительное

    M.add_transition("ADJ_ROOT", CAT_DEG, "ADJ_AFTER_DEG")
    M.add_transition("ADJ_ROOT", CAT_DERIV, "ADJ_AS_N")

    return M


def build_master_automaton() -> Dict[str, MorphAutomaton]:
    """Карта: часть речи → её автомат."""
    return {
        "N": build_noun_automaton(),
        "V": build_verb_automaton(),
        "ADJ": build_adjective_automaton(),
        "PRON": build_noun_automaton(),   # местоимения склоняются как сущ.
        "NUM": build_noun_automaton(),    # числительные тоже допускают падежные суффиксы
    }

"""Streamlit-интерфейс морфологического анализатора кыргызского языка.

Запуск:    streamlit run app.py
"""
from __future__ import annotations
import json
from pathlib import Path

import streamlit as st
import pandas as pd

from morphology import MorphDatabase, MorphAnalyzer, MorphGenerator
from morphology.automaton import build_master_automaton
from morphology.harmony import (
    VOWELS, BACK_VOWELS, FRONT_VOWELS, ROUND_VOWELS, UNROUND_VOWELS,
    VOICELESS, VOICED, SONORANT, classify_vowel, classify_consonant,
    HarmonyClassifier,
)

# ---------------------------- настройка страницы ----------------------------
st.set_page_config(
    page_title="Морфоанализатор кыргызского языка",
    page_icon="🪶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Простая стилизация
st.markdown(
    """
    <style>
    .big-form { font-size: 28px; font-weight: 700; color: #1f4e79; }
    .tag-chip {
        display: inline-block; padding: 3px 10px; margin: 2px 4px;
        background: #eaf2fb; border-radius: 12px; font-size: 14px;
        color: #1f4e79; border: 1px solid #c4daf2;
    }
    .seg-root { color: #b8000d; font-weight: 700; }
    .seg-affix { color: #155724; font-weight: 600; }
    .small-mono { font-family: monospace; font-size: 13px; color: #555; }
    .ok-badge { background:#e7f6ea; color:#22863a; padding:2px 8px;
                border-radius:8px; font-weight:600; }
    .fail-badge { background:#fde8ea; color:#cb2431; padding:2px 8px;
                  border-radius:8px; font-weight:600; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_engine():
    db = MorphDatabase("data")
    return db, MorphAnalyzer(db), MorphGenerator(db)


db, analyzer, generator = load_engine()
automata = build_master_automaton()
harmony = HarmonyClassifier()


# ---------------------------- боковая панель ----------------------------
st.sidebar.title("🪶 Морфоанализатор")
st.sidebar.markdown("Кыргызский язык · дипломная работа")
st.sidebar.divider()
page = st.sidebar.radio(
    "Раздел",
    [
        "🏠 Главная",
        "🔍 Анализ слова",
        "🛠 Генерация словоформы",
        "📐 Парадигма (склонение/спряжение)",
        "📚 База данных",
        "📊 Тестирование (Coverage)",
        "🧮 Математическая модель",
    ],
)

st.sidebar.divider()
stats = db.stats()
st.sidebar.metric("Корней в словаре", stats["roots_total"])
st.sidebar.metric("Аффиксных лемм", stats["affix_lemmas"])


# ============================================================================
#                                   ГЛАВНАЯ
# ============================================================================
if page == "🏠 Главная":
    st.title("Морфологический анализатор кыргызского языка")
    st.caption(
        "Прототип к дипломной работе: математическая модель + Python-реализация + GUI."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Корней", stats["roots_total"])
    c2.metric("Существ.", stats["roots_by_pos"].get("nouns", 0))
    c3.metric("Глаголов", stats["roots_by_pos"].get("verbs", 0))
    c4.metric("Прил./Мест./Числ.",
              stats["roots_by_pos"].get("adjectives", 0)
              + stats["roots_by_pos"].get("pronouns", 0)
              + stats["roots_by_pos"].get("numerals", 0))

    st.markdown("---")
    st.subheader("Возможности системы")
    st.markdown(
        """
- **Анализ словоформы** — разложение слова на корень и аффиксы с тегами
- **Генерация словоформ** из леммы и набора грамматических признаков
- **Парадигмы** — полное склонение существительных и спряжение глаголов
- **Метрика Coverage** — оценка покрытия на тестовом корпусе
- **Математическая модель** — описание правил сингармонизма и автомата морфотактики
"""
    )

    st.markdown("---")
    st.subheader("Попробуйте сразу")
    quick = st.selectbox(
        "Выберите слово или введите своё в разделе «Анализ слова»:",
        ["балаларымда", "көрбөдүм", "чоңураак", "үйдөрдөн", "мугалимдер",
         "келбедим", "окудум", "тоого", "досум", "китепти"],
    )
    if st.button("Разобрать"):
        results = analyzer.analyze(quick)
        if results:
            for r in results[:3]:
                st.markdown(
                    f"<span class='big-form'>{quick}</span> &nbsp;→&nbsp; "
                    f"<code>{r.pretty()}</code>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Сегментация: **{r.segmentation()}**")
        else:
            st.warning("Слово не разобрано базовой моделью.")


# ============================================================================
#                                  АНАЛИЗ
# ============================================================================
elif page == "🔍 Анализ слова":
    st.title("🔍 Анализ словоформы")
    st.caption("Алгоритм работает справа налево: снимает аффиксы и сверяет их с правилами сингармонизма.")

    word = st.text_input("Введите слово на кыргызском языке", value="балаларымда")
    do = st.button("Разобрать", type="primary")
    if do and word:
        results = analyzer.analyze(word)
        if not results:
            st.error("Слово не разобрано. Возможно, корня нет в базе или нужен расширенный набор правил.")
        else:
            st.success(f"Найдено разборов: **{len(results)}**")
            for i, r in enumerate(results, 1):
                with st.expander(f"Разбор #{i} — {r.pretty()}", expanded=(i == 1)):
                    # верхняя строка с леммой и тегами
                    chips = " ".join(
                        f"<span class='tag-chip'>{t}</span>" for t in r.tags
                    )
                    st.markdown(
                        f"**Лемма:** <span class='seg-root'>{r.lemma}</span> "
                        f"<span class='tag-chip'>{r.pos}</span>{chips}<br>"
                        f"**Перевод:** {r.gloss}",
                        unsafe_allow_html=True,
                    )
                    # сегментация
                    st.markdown("**Морфемная сегментация:**")
                    parts = []
                    for s in r.segments:
                        cls = "seg-root" if s.is_root else "seg-affix"
                        label = s.category if s.is_root else s.lexical
                        parts.append(
                            f"<span class='{cls}'>{s.surface}</span>"
                            f"<span class='small-mono'>[{label}]</span>"
                        )
                    st.markdown(" + ".join(parts), unsafe_allow_html=True)
                    # таблица сегментов
                    df = pd.DataFrame([
                        {
                            "Сегмент": s.surface,
                            "Тип": "корень" if s.is_root else "аффикс",
                            "Тег/POS": s.category if s.is_root else s.lexical,
                            "Категория": "—" if s.is_root else s.category,
                            "Перевод/гл.": s.gloss,
                        }
                        for s in r.segments
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("💡 Примеры: балаларымда, көрбөдүм, чоңураак, мугалимдер, тоого, көздөр")


# ============================================================================
#                                ГЕНЕРАЦИЯ
# ============================================================================
elif page == "🛠 Генерация словоформы":
    st.title("🛠 Генерация словоформы")
    st.caption("Из леммы и набора грамматических признаков строим конкретную форму, "
               "применяя правила гармонии и ассимиляции.")

    col1, col2 = st.columns([1, 1])
    with col1:
        pos = st.selectbox("Часть речи",
                           ["N", "V", "ADJ", "PRON", "NUM"],
                           format_func=lambda p: {
                               "N": "Существительное",
                               "V": "Глагол",
                               "ADJ": "Прилагательное",
                               "PRON": "Местоимение",
                               "NUM": "Числительное",
                           }[p])
        # подходящие корни
        root_map = {"N": "nouns", "V": "verbs", "ADJ": "adjectives",
                    "PRON": "pronouns", "NUM": "numerals"}
        roots = [r["root"] for r in db.roots_by_pos.get(root_map[pos], [])]
        lemma = st.selectbox("Лемма (корень)", roots)

    with col2:
        # допустимые теги для этой части речи
        affixes = db.affixes_for_category(pos)
        all_tags = [af["tag"] for af in affixes]
        tag_labels = {af["tag"]: f"{af['tag']} — {af['gloss']}" for af in affixes}
        chosen = st.multiselect(
            "Грамматические теги (в нужном порядке)",
            options=all_tags,
            format_func=lambda t: tag_labels[t],
        )

    if st.button("Сгенерировать", type="primary"):
        result = generator.generate(lemma, pos, chosen)
        if result is None:
            st.error("Невозможно построить такую форму: проверьте порядок тегов "
                     "или нет нужного аффикса в базе.")
        else:
            st.markdown(
                f"<div class='big-form'>{result.form}</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"{result.lemma}<{result.pos}>" +
                       "".join(f"<{t}>" for t in result.tags))
            st.markdown("**Пошаговое построение:**")
            steps_df = pd.DataFrame({
                "Шаг": list(range(len(result.steps))),
                "Форма": result.steps,
                "Гармония последнего гласного":
                    [harmony.harmony_class(s) for s in result.steps],
            })
            st.dataframe(steps_df, use_container_width=True, hide_index=True)


# ============================================================================
#                                ПАРАДИГМА
# ============================================================================
elif page == "📐 Парадигма (склонение/спряжение)":
    st.title("📐 Парадигма")
    st.caption("Автоматическая генерация полной парадигмы для леммы.")

    pos = st.selectbox("Часть речи",
                       ["N", "V", "ADJ", "PRON", "NUM"],
                       format_func=lambda p: {
                           "N": "Существительное",
                           "V": "Глагол",
                           "ADJ": "Прилагательное",
                           "PRON": "Местоимение",
                           "NUM": "Числительное",
                       }[p], key="par_pos")
    root_map = {"N": "nouns", "V": "verbs", "ADJ": "adjectives",
                "PRON": "pronouns", "NUM": "numerals"}
    roots = [r["root"] for r in db.roots_by_pos.get(root_map[pos], [])]
    lemma = st.selectbox("Лемма", roots, key="par_lemma")

    forms = generator.paradigm(lemma, pos)
    if not forms:
        st.info("Для этой части речи парадигма не определена.")
    else:
        df = pd.DataFrame([
            {"Форма": f.form, "Теги": " + ".join(f.tags) or "—"}
            for f in forms
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================================
#                                  БАЗА ДАННЫХ
# ============================================================================
elif page == "📚 База данных":
    st.title("📚 База данных морфологии")
    tab1, tab2 = st.tabs(["Корни", "Аффиксы"])
    with tab1:
        category = st.selectbox(
            "Категория",
            list(db.roots_by_pos.keys()),
            format_func=lambda c: {
                "nouns": "Существительные",
                "verbs": "Глаголы",
                "adjectives": "Прилагательные",
                "pronouns": "Местоимения",
                "numerals": "Числительные",
            }.get(c, c),
        )
        items = db.roots_by_pos[category]
        q = st.text_input("Фильтр (по корню или переводу)").strip().lower()
        if q:
            items = [it for it in items
                     if q in it["root"].lower() or q in it.get("gloss", "").lower()]
        st.caption(f"Записей: {len(items)}")
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)

    with tab2:
        affcat = st.selectbox("Группа аффиксов",
                              list(db.affixes_by_pos.keys()),
                              format_func=lambda c: {
                                  "noun_affixes": "Именные",
                                  "verb_affixes": "Глагольные",
                                  "adjective_affixes": "Адъективные",
                              }.get(c, c))
        rows = []
        for af in db.affixes_by_pos[affcat]:
            variants_flat = []
            for ctx, group in af["variants"].items():
                for hc, surf in group.items():
                    if surf:
                        variants_flat.append(f"{surf} ({ctx[6:]}/{hc})")
            rows.append({
                "ID": af["id"],
                "Тег": af["tag"],
                "Категория": af["category"],
                "Значение": af["gloss"],
                "Аллoморфы": ", ".join(variants_flat),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================================
#                              ТЕСТИРОВАНИЕ (COVERAGE)
# ============================================================================
elif page == "📊 Тестирование (Coverage)":
    st.title("📊 Тестирование и метрика Coverage")
    st.caption("Coverage = доля словоформ из тестового корпуса, у которых "
               "найден хотя бы один разбор с правильной леммой.")

    with open("data/test_corpus.json", "rb") as f:
        raw = f.read().rstrip(b"\x00")
    last = raw.rfind(b"}")
    corpus = json.loads(raw[:last + 1].decode("utf-8"))["items"]

    rows = []
    covered = 0
    exact_tag_match = 0
    for item in corpus:
        form = item["form"]
        expected = item["expected_lemma"]
        expected_tags = set(item.get("tags", []))
        analyses = analyzer.analyze(form)
        if analyses:
            covered += 1
            matched = any(a.lemma == expected for a in analyses)
            tag_match = any(
                a.lemma == expected and set([a.pos, *a.tags]) == expected_tags
                for a in analyses
            )
            if tag_match:
                exact_tag_match += 1
            status = "✅" if matched else "≈"
            best = analyses[0].pretty()
        else:
            status = "❌"
            best = "—"
        rows.append({
            "Слово": form,
            "Лемма ожид.": expected,
            "Теги ожид.": " ".join(item.get("tags", [])),
            "Лучший разбор": best,
            "Статус": status,
        })

    n = len(corpus)
    cov = covered / n if n else 0
    tag_acc = exact_tag_match / n if n else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Тестов всего", n)
    c2.metric("Покрытие (Coverage)", f"{cov:.1%}")
    c3.metric("Точное совпадение тегов", f"{tag_acc:.1%}")

    if cov >= 0.7:
        st.success(f"🎯 Coverage {cov:.1%} — целевой уровень (≥ 70%) достигнут.")
    elif cov >= 0.6:
        st.info(f"Coverage {cov:.1%} — в пределах целевого диапазона 60–70%.")
    else:
        st.warning(f"Coverage {cov:.1%} — ниже целевого порога.")

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================================
#                            МАТЕМАТИЧЕСКАЯ МОДЕЛЬ
# ============================================================================
elif page == "🧮 Математическая модель":
    st.title("🧮 Математическая модель")
    st.markdown(
        r"""
### 1. Алфавит и фонологические классы

Алфавит гласных $\Sigma_V = \{а, е, и, о, у, ө, ү, ы\}$.

Бинарные признаки:
$$
f_\text{palatal}(v) = \begin{cases} \text{back}, & v\in\{а,о,у,ы\}\\ \text{front}, & v\in\{е,и,ө,ү\}\end{cases},\quad
f_\text{round}(v) = \begin{cases} \text{round}, & v\in\{о,ө,у,ү\}\\ \text{unround}, & \text{иначе}\end{cases}
$$

Класс гармонии $H(v)\in\{a,e,o,\ddot{o}\}$:
"""
    )
    df_h = pd.DataFrame({
        "Класс": ["a", "e", "o", "ö"],
        "Признаки": ["back & unround", "front & unround", "back & round", "front & round"],
        "Гласные": ["а, ы", "е, и", "о, у", "ө, ү"],
    })
    st.table(df_h)

    st.markdown(
        r"""
### 2. Сингармонизм слова

Гармония слова определяется ПОСЛЕДНИМ гласным основы:
$$ H(\text{stem}) = H(\text{lastVowel}(\text{stem})). $$

Каждый аффикс представлен в виде функции $\alpha : C \times \{a,e,o,\ddot o\} \to \Sigma^*$,
где $C$ — контекст последнего согласного основы.

### 3. Конечный автомат морфотактики

Формально $M = (Q, \Sigma_T, \delta, q_0, F)$, где $\Sigma_T$ — алфавит морфологических
тегов (категорий аффиксов). Для существительных:
$$ \text{ROOT} \to [\text{Pl}] \to [\text{Poss}] \to [\text{Case}] \to \text{END}. $$

Для глаголов:
$$ \text{ROOT} \to [\text{Neg}] \to \text{Tense} \to [\text{PersNum}] \to \text{END}. $$

Слово допускается, если существует путь по автомату, оканчивающийся в финальном
состоянии $q_f\in F$, такой, что приклеенные на каждом шаге аллoморфы дают исходное
слово.

### 4. Двухуровневая модель (упрощённый Koskenniemi 1983)
$$
\text{LEXICAL: бала}^\wedge \text{<Pl><Px1Sg><Loc>} \;\longleftrightarrow\;
\text{SURFACE: балаларымда}.
$$

Перевод между уровнями делает каскад правил гармонии и ассимиляции —
именно то, что реализует функция `pick_allomorph` в модуле `harmony.py`.

### 5. Алгоритм анализа (справа налево)

Для входной словоформы $w$:
1. для каждого корня $r$ из словаря, такого что $w$ начинается на $r$;
2. на каждом шаге пытаемся снять самый правый суффикс $a$ так, что
   $a = \alpha(C(\text{stem}), H(\text{stem}))$ для какого-то аффикса;
3. одновременно обновляем состояние автомата $\delta(q, \text{cat}(a))$;
4. разбор валиден, если по окончании суффиксов мы оказались в $q_f\in F$.

"""
    )

    st.subheader("Гласные кыргызского языка")
    rows = []
    for v in "аеиоуөүы":
        rows.append({"Гласная": v, "Признаки": classify_vowel(v),
                     "Класс H(v)": harmony.harmony_class(v)})
    st.table(pd.DataFrame(rows))

    st.subheader("Согласные классы")
    cdf = pd.DataFrame({
        "Класс": ["глухие", "звонкие", "сонорные"],
        "Фонемы": [" ".join(sorted(VOICELESS)), " ".join(sorted(VOICED)),
                   " ".join(sorted(SONORANT))],
        "Влияние на аффикс": [
            "глухое начало (-та, -ка, -ты, -пе)",
            "звонкое начало (-да, -га, -ды, -бе)",
            "звонкое начало (-да, -га, -ды, -бе)",
        ],
    })
    st.table(cdf)

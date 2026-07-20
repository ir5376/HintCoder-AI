from __future__ import annotations

from collections.abc import Callable
from html import escape

import streamlit as st

from src.services.hint_service import HintService, ProblemContext
from src.services.problem_service import ProblemService

try:
    from streamlit_ace import st_ace
except ImportError:  # pragma: no cover
    st_ace = None


def build_hint_context(problem: dict, *, student_code: str = "", programming_language: str = "Python", hint_level: int = 1) -> ProblemContext:
    return ProblemContext(
        source_platform="HintCode", source_url=problem.get("source_reference", "") or "",
        title=problem.get("title", "") or "", description=problem.get("description", "") or "",
        constraints=problem.get("constraints", "") or "", examples=str(problem.get("test_cases", []) or ""),
        difficulty=problem.get("difficulty", "") or "", programming_language=programming_language or "Python",
        student_code=student_code or problem.get("starter_code", "") or "", hint_level=hint_level,
        problem_id=problem.get("id"),
    )


def _normalize_history_entry(entry: dict) -> dict:
    return {
        "generated_hint": entry.get("generated_hint") or entry.get("hint") or entry.get("hint_text") or "",
        "hint_level": entry.get("hint_level", 1),
        "programming_language": entry.get("programming_language", "Python"),
        "problem_title": entry.get("problem_title") or entry.get("title") or "Problem",
    }


def _render_code_editor(label: str, value: str, key: str, *, language: str = "python") -> str:
    if st_ace is not None:
        return st_ace(value=value, language=language, theme="monokai", key=key, height=330, auto_update=False, show_gutter=True)
    return st.text_area(label, value=value, height=330, key=key)


def _problem_or_error(service: ProblemService, problem_id: int | str | None) -> dict | None:
    if problem_id is None:
        st.error("No learning item is selected.")
        st.caption("Use the in-app Back button to return to Learning Sources.")
        return None
    if isinstance(problem_id, str) and problem_id.startswith("source-"):
        problem = next((item for item in st.session_state.get("added_sources", []) if item["id"] == problem_id), None)
    else:
        problem = service.get_problem(problem_id)
    if problem is None:
        st.error("We could not find that learning item.")
        st.caption("Use the in-app Back button to return to Learning Sources.")
    return problem


def _review_status(problem: dict) -> str:
    return st.session_state.get("review_statuses", {}).get(problem["id"], problem.get("review_status", "Not reviewed"))


def _set_review_status(problem: dict, status: str) -> None:
    statuses = dict(st.session_state.get("review_statuses", {}))
    statuses[problem["id"]] = status
    st.session_state["review_statuses"] = statuses


def render_problem_detail(service: ProblemService, problem_id: int | str | None, on_start_learning: Callable[[], None]) -> None:
    problem = _problem_or_error(service, problem_id)
    if problem is None:
        return
    provider = problem.get("provider") or problem.get("source_type") or "HintCode"
    concepts = ", ".join(problem.get("tags", []) or [problem["category"]])
    st.markdown('<div class="hc-eyebrow">Learning Item</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hc-title">{escape(str(problem["title"]))}</div><p class="hc-lede">A single, consistent learning space for every source type.</p>', unsafe_allow_html=True)
    fields = st.columns(5)
    for column, label, value in zip(fields, ["Source", "Provider", "Difficulty", "Concepts", "Status"], [problem.get("source_type") or "Learning item", provider, problem.get("difficulty") or "To assess", concepts, _review_status(problem)]):
        with column:
            st.markdown(f'<div class="hc-label">{label}</div><div class="hc-muted">{escape(str(value))}</div>', unsafe_allow_html=True)
    st.markdown("#### Problem")
    st.write(problem["description"])
    if problem.get("constraints"):
        st.markdown("#### Constraints")
        st.write(problem["constraints"])
    if problem.get("test_cases"):
        st.markdown("#### Examples")
        st.write(problem["test_cases"])
    if problem.get("explanation"):
        with st.expander("Concept explanation"):
            st.write(problem["explanation"])
    st.info("Before you code, name the input, the desired output, and one example you can trace by hand.")
    if st.button("Open learning workspace", type="primary"):
        on_start_learning()


def render_learning_workspace(service: ProblemService, problem_id: int | str | None, hint_service: HintService | None = None) -> None:
    problem = _problem_or_error(service, problem_id)
    if problem is None:
        return
    st.markdown('<div class="hc-eyebrow">Learning Item</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hc-title">{escape(str(problem["title"]))}</div><p class="hc-lede">The same learning workflow, whatever the source.</p>', unsafe_allow_html=True)
    tabs = st.tabs(["Problem", "Hint", "Memory Cards", "Review", "Quiz", "Generate Similar Problem"])
    templates = {
        "Python": problem.get("starter_code", "") or "",
        "JavaScript": "function solution() {\n    // Write your solution here\n}",
        "Java": "class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}",
        "C++": "#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}",
    }
    with tabs[0]:
        st.markdown("#### Problem")
        st.write(problem["description"])
        st.markdown("#### Make an attempt")
        st.caption("Your draft is used only to give the hint assistant useful context.")
        language = st.selectbox("Language", ["Python", "JavaScript", "Java", "C++"], key=f"language_{problem['id']}")
        editor_key = f"code_editor_{problem['id']}_{language}"
        if editor_key not in st.session_state:
            st.session_state[editor_key] = templates[language]
        language_map = {"Python": "python", "JavaScript": "javascript", "Java": "java", "C++": "c_cpp"}
        student_code = _render_code_editor("Your attempt", st.session_state[editor_key], editor_key, language=language_map[language])
        st.session_state[f"student_code_{problem['id']}"] = student_code
        st.session_state[f"student_language_{problem['id']}"] = language
    with tabs[1]:
        st.markdown("#### Ask for the smallest useful nudge")
        st.caption("Hints are progressive. Start small so your reasoning stays in the lead.")
        hint_level = st.select_slider("How direct should the hint be?", options=[1, 2, 3, 4], value=1, key=f"hint_level_{problem['id']}", format_func=lambda value: f"Level {value}")
        if st.button("Get a hint", type="primary", key=f"get_hint_{problem['id']}"):
            if hint_service is None:
                st.error("The hint assistant is unavailable. Please try again shortly.")
            else:
                code = st.session_state.get(f"student_code_{problem['id']}", problem.get("starter_code", ""))
                language = st.session_state.get(f"student_language_{problem['id']}", "Python")
                with st.spinner("Reading your attempt and preparing a hint..."):
                    try:
                        result = hint_service.generate_hint(build_hint_context(problem, student_code=code, programming_language=language, hint_level=hint_level), hint_level=hint_level)
                    except Exception:
                        st.error("We could not generate a hint right now. Your attempt is still here; please try again in a moment.")
                    else:
                        if result.get("hint"):
                            entry = {"generated_hint": result["hint"], "hint_level": result.get("hint_level", hint_level), "programming_language": language, "problem_title": problem["title"]}
                            st.session_state[f"latest_hint_{problem['id']}"] = entry
                            history = list(st.session_state.get("hint_history", []))
                            history.insert(0, entry)
                            st.session_state["hint_history"] = history[:8]
                        else:
                            st.warning("The assistant returned no hint. Please try again.")
        latest = st.session_state.get(f"latest_hint_{problem['id']}")
        if latest:
            st.success(latest["generated_hint"])
        else:
            st.markdown('<div class="hc-card"><b>No hint yet</b><p class="hc-muted">Write an attempt first, then choose the level of guidance you need.</p></div>', unsafe_allow_html=True)
    with tabs[2]:
        st.markdown("#### Memory Cards")
        st.markdown('<div class="hc-card"><b>Create a recall cue</b><p class="hc-muted">What signal tells you to use this concept? Add your answer after your first attempt.</p></div>', unsafe_allow_html=True)
        card_key = f"memory_card_{problem['id']}"
        clear_card_key = f"clear_memory_card_{problem['id']}"
        if st.session_state.pop(clear_card_key, False):
            st.session_state[card_key] = ""
        st.text_area("Memory card", key=card_key, placeholder="Front: When do I use this?  Back: ...", height=110)
        if st.button("Save memory card", key=f"save_memory_card_{problem['id']}"):
            card = st.session_state.get(card_key, "").strip()
            if card:
                cards = dict(st.session_state.get("memory_cards", {}))
                cards[problem["id"]] = [card, *cards.get(problem["id"], [])]
                st.session_state["memory_cards"] = cards
                st.session_state[clear_card_key] = True
                st.session_state[f"memory_card_saved_{problem['id']}"] = True
                st.rerun()
            else:
                st.warning("Write a recall cue before saving it.")
        if st.session_state.pop(f"memory_card_saved_{problem['id']}", False):
            st.success("Memory card saved.")
        for index, card in enumerate(st.session_state.get("memory_cards", {}).get(problem["id"], []), start=1):
            st.markdown(f'<div class="hc-card"><b>Card {index}</b><p class="hc-muted">{escape(card)}</p></div>', unsafe_allow_html=True)
    with tabs[3]:
        st.markdown("#### Review")
        status = _review_status(problem)
        st.markdown(f'<div class="hc-card"><b>{escape(status)}</b><p class="hc-muted">Choose when this item should return to your review queue.</p></div>', unsafe_allow_html=True)
        review_a, review_b = st.columns(2)
        with review_a:
            if st.button("Schedule review", key=f"schedule_review_{problem['id']}", use_container_width=True):
                _set_review_status(problem, "Ready for review")
                st.rerun()
        with review_b:
            if st.button("Mark reviewed", key=f"mark_reviewed_{problem['id']}", use_container_width=True):
                _set_review_status(problem, "Reviewed")
                st.rerun()
    with tabs[4]:
        st.markdown("#### Quiz")
        st.markdown('<div class="hc-card"><b>Check your understanding</b><p class="hc-muted">Explain the first decision you would make before looking at a solution.</p></div>', unsafe_allow_html=True)
        quiz_key = f"quiz_{problem['id']}"
        st.text_area("Your answer", key=quiz_key, height=100)
        if st.button("Check answer", key=f"check_quiz_{problem['id']}"):
            answer = st.session_state.get(quiz_key, "").strip()
            if not answer:
                st.warning("Write your reasoning before checking it.")
            else:
                st.session_state[f"quiz_feedback_{problem['id']}"] = "Saved. Compare your decision with the concept and constraints before continuing."
        if feedback := st.session_state.get(f"quiz_feedback_{problem['id']}"):
            st.success(feedback)
    with tabs[5]:
        st.markdown("#### Generate Similar Problem")
        st.markdown('<div class="hc-card"><b>Practice the same idea again</b><p class="hc-muted">Generate a fresh prompt that keeps this item\'s concepts while changing the scenario.</p></div>', unsafe_allow_html=True)
        if st.button("Generate similar problem", key=f"similar_problem_{problem['id']}", type="primary"):
            concepts = ", ".join(problem.get("tags", []) or [problem["category"]])
            st.session_state[f"similar_problem_{problem['id']}"] = (
                f"Create a new {problem.get('difficulty', 'practice')} problem using {concepts}. "
                f"Keep the core reasoning from \"{problem['title']}\", but use different inputs and an unfamiliar scenario."
            )
        if similar := st.session_state.get(f"similar_problem_{problem['id']}"):
            st.markdown(f'<div class="hc-card"><b>Similar practice prompt</b><p class="hc-muted">{escape(similar)}</p></div>', unsafe_allow_html=True)

    history = list(st.session_state.get("hint_history", []))
    if not history and hint_service is not None:
        try:
            st.session_state["hint_history"] = [_normalize_history_entry(item) for item in hint_service.list_hint_history()][:8]
        except Exception:
            pass

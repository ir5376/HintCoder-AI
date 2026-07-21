from __future__ import annotations

from collections.abc import Callable
from html import escape
import logging

import streamlit as st

from src.services.hint_service import HintService, ProblemContext
from src.services.problem_service import ProblemService
from src.ui.components.solution_link_review import SolutionActionCallback, render_solution_link_review
from src.ui.components.solution_link_view_models import (
    SolutionLinkReviewViewModel,
    SolutionLinkStatus,
    SolutionSourceStatus,
)

logger = logging.getLogger(__name__)

try:
    from streamlit_ace import st_ace
except ImportError:  # pragma: no cover
    st_ace = None


def build_hint_context(problem: dict, *, student_code: str = "", programming_language: str = "Python", hint_level: int = 1) -> ProblemContext:
    return ProblemContext(source_platform="HintCode", source_url=problem.get("source_reference", "") or "", title=problem.get("title", "") or "", description=problem.get("description", "") or "", constraints=problem.get("constraints", "") or "", examples=str(problem.get("test_cases", []) or ""), difficulty=problem.get("difficulty", "") or "", programming_language=programming_language or "Python", student_code=student_code or problem.get("starter_code", "") or "", hint_level=hint_level, problem_id=problem.get("id"))


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


def _is_exam_item(problem: dict) -> bool:
    return problem.get("problem_type") == "Exam PDF" or problem.get("source_type") == "PDF"


def _render_exam_attempt(problem: dict) -> None:
    questions = (problem.get("import_preview") or {}).get("questions") or []
    if not questions and (problem.get("question_text") or problem.get("choices")):
        questions = [
            {
                "number": problem.get("question_number") or "-",
                "text": problem.get("question_text") or problem.get("description") or "",
                "choices": problem.get("choices") or [],
                "answer_state": problem.get("answer_state", "No answer"),
                "source_page": problem.get("source_page"),
            }
        ]
    if not questions:
        st.markdown("#### Question")
        st.write(problem["description"])
        if problem.get("extraction_error"):
            st.error(problem["extraction_error"])
        else:
            st.info("No questions were extracted from this PDF yet.")
        st.text_area("Your answer", key=f"exam_answer_{problem['id']}", height=120)
        return
    for item in questions:
        number = item.get("number", "-")
        st.markdown(f"#### Question {number}")
        if item.get("passage"):
            st.caption(item["passage"])
        st.write(item.get("text", "Question text is unavailable."))
        if item.get("source_page") is not None:
            st.caption(f"Source page {item['source_page']}")
        choices = item.get("choices") or []
        if choices:
            st.radio("Choose an answer", choices, key=f"exam_choice_{problem['id']}_{number}")
        else:
            st.text_area("Your answer", key=f"exam_answer_{problem['id']}_{number}", height=100)
        st.caption(f"Answer state: {item.get('answer_state', 'No answer')}")


def render_problem_detail(service: ProblemService, problem_id: int | str | None, on_start_learning: Callable[[], None]) -> None:
    problem = _problem_or_error(service, problem_id)
    if not problem:
        return
    provider = problem.get("provider") or problem.get("source_type") or "HintCode"
    concepts = ", ".join(problem.get("tags", []) or [problem["category"]])
    st.markdown('<div class="hc-eyebrow">Learning Item</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hc-title">{escape(str(problem["title"]))}</div><p class="hc-lede">A single, consistent learning space for every source type.</p>', unsafe_allow_html=True)
    for column, label, value in zip(st.columns(5), ["Source", "Provider", "Difficulty", "Concepts", "Status"], [problem.get("source_type") or "Learning item", provider, problem.get("difficulty") or "To assess", concepts, _review_status(problem)]):
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
    if st.button("Open learning workspace", type="primary"):
        on_start_learning()


def render_learning_workspace(
    service: ProblemService,
    problem_id: int | str | None,
    hint_service: HintService | None = None,
    solution_review: SolutionLinkReviewViewModel | None = None,
    on_solution_action: SolutionActionCallback | None = None,
) -> None:
    problem = _problem_or_error(service, problem_id)
    if not problem:
        return
    st.markdown('<div class="hc-eyebrow">Learning Item</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hc-title">{escape(str(problem["title"]))}</div><p class="hc-lede">The same learning workflow, whatever the source.</p>', unsafe_allow_html=True)
    if event := st.session_state.pop("xp_event", None):
        if isinstance(event, dict) and event.get("amount") is not None:
            st.caption(f"+{event['amount']} XP - {event.get('reason', 'Learning activity')}")
    tabs = st.tabs(["Problem", "Hint", "Memory Cards", "Review", "Quiz", "Generate Similar Problem"])
    with tabs[0]:
        if _is_exam_item(problem):
            _render_exam_attempt(problem)
        else:
            st.markdown("#### Problem")
            st.write(problem["description"])
            st.markdown("#### Make an attempt")
            language = st.selectbox("Language", ["Python", "JavaScript", "Java", "C++"], key=f"language_{problem['id']}")
            editor_key = f"code_editor_{problem['id']}_{language}"
            templates = {"Python": problem.get("starter_code", "") or "", "JavaScript": "function solution() {\n}", "Java": "class Solution {\n}", "C++": "#include <iostream>\n"}
            if editor_key not in st.session_state:
                st.session_state[editor_key] = templates[language]
            mode = {"Python": "python", "JavaScript": "javascript", "Java": "java", "C++": "c_cpp"}[language]
            st.session_state[f"student_code_{problem['id']}"] = _render_code_editor("Your attempt", st.session_state[editor_key], editor_key, language=mode)
            st.session_state[f"student_language_{problem['id']}"] = language
    with tabs[1]:
        st.markdown("#### Ask for the smallest useful nudge")
        level = st.select_slider("How direct should the hint be?", options=[1, 2, 3, 4], value=1, key=f"hint_level_{problem['id']}", format_func=lambda value: f"Level {value}")
        st.text_area("What are you stuck on? (optional)", key=f"hint_question_{problem['id']}", placeholder="Ask for a specific direction, explain your current approach, or tell the coach what you do not understand.", height=90)
        if st.button("Get a hint", type="primary", key=f"get_hint_{problem['id']}"):
            if hint_service is None:
                st.error("The hint assistant is unavailable. Please try again shortly.")
            else:
                code = st.session_state.get(f"student_code_{problem['id']}", problem.get("starter_code", ""))
                question = st.session_state.get(f"hint_question_{problem['id']}", "").strip()
                context_code = f"{code}\n\nLearner question: {question}" if question else code
                try:
                    result = hint_service.generate_hint(build_hint_context(problem, student_code=context_code, programming_language=st.session_state.get(f"student_language_{problem['id']}", "Python"), hint_level=level), hint_level=level)
                except Exception as exc:
                    logger.exception(
                        "Hint generation failed for problem_id=%s public_id=%s hint_level=%s error_type=%s",
                        problem.get("id"),
                        problem_id,
                        level,
                        type(exc).__name__,
                    )
                    st.error("We could not generate a hint right now. Your attempt is still here; please try again in a moment.")
                else:
                    st.session_state[f"latest_hint_{problem['id']}"] = result.get("hint", "")
        latest = st.session_state.get(f"latest_hint_{problem['id']}")
        if latest:
            st.success(latest)
    with tabs[2]:
        key = f"memory_card_{problem['id']}"
        st.text_area("Memory card", key=key, placeholder="Front: When do I use this? Back: ...", height=110)
        if st.button("Save memory card", key=f"save_memory_card_{problem['id']}") and st.session_state.get(key, "").strip():
            cards = dict(st.session_state.get("memory_cards", {}))
            cards[problem["id"]] = [st.session_state[key].strip(), *cards.get(problem["id"], [])]
            st.session_state["memory_cards"] = cards
            st.success("Memory card saved.")
        for index, card in enumerate(st.session_state.get("memory_cards", {}).get(problem["id"], []), start=1):
            st.markdown(f'<div class="hc-card"><b>Card {index}</b><p class="hc-muted">{escape(card)}</p></div>', unsafe_allow_html=True)
    with tabs[3]:
        st.markdown(f'<div class="hc-card"><b>{escape(_review_status(problem))}</b><p class="hc-muted">Choose when this item should return to your review queue.</p></div>', unsafe_allow_html=True)
        left, right = st.columns(2)
        if left.button("Schedule review", key=f"schedule_review_{problem['id']}", use_container_width=True):
            _set_review_status(problem, "Ready for review")
            st.rerun()
        if right.button("Mark reviewed", key=f"mark_reviewed_{problem['id']}", use_container_width=True):
            _set_review_status(problem, "Reviewed")
            st.rerun()
        render_solution_link_review(
            solution_review
            or SolutionLinkReviewViewModel(
                question_id=str(problem["id"]),
                link_status=SolutionLinkStatus.NO_SOLUTION,
                source_status=SolutionSourceStatus.PENDING,
            ),
            on_solution_action,
        )
    with tabs[4]:
        key = f"quiz_{problem['id']}"
        st.text_area("Your answer", key=key, height=100)
        if st.button("Check answer", key=f"check_quiz_{problem['id']}"):
            st.success("Saved. Compare your decision with the concept and constraints before continuing.") if st.session_state.get(key, "").strip() else st.warning("Write your reasoning before checking it.")
    with tabs[5]:
        if st.button("Generate similar problem", key=f"similar_problem_{problem['id']}", type="primary"):
            concepts = ", ".join(problem.get("tags", []) or [problem["category"]])
            st.session_state[f"similar_problem_{problem['id']}"] = f"Create a new {problem.get('difficulty', 'practice')} problem using {concepts}, with different inputs and scenario."
        if prompt := st.session_state.get(f"similar_problem_{problem['id']}"):
            st.markdown(f'<div class="hc-card"><b>Similar practice prompt</b><p class="hc-muted">{escape(prompt)}</p></div>', unsafe_allow_html=True)

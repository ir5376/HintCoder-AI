from __future__ import annotations

import streamlit as st

from src.content_modules.registry import ContentModuleRegistry
from src.learning_engine.content import LearningContent
from src.learning_engine.engine import LearningEngine
from src.services.hint_service import COACHING_ACTIONS, HintService, ProblemContext


def render_module_practice(
    *,
    registry: ContentModuleRegistry,
    learning_engine: LearningEngine,
    hint_service: HintService,
    selected_module_id: str,
    app_mode: str,
) -> None:
    module = registry.get(selected_module_id)
    if not hasattr(module, "list_content"):
        st.info("This module uses the existing Coding problem list.")
        return

    content_items = module.list_content()
    if not content_items:
        st.warning("No content is available for this module yet.")
        return

    content = _select_content(content_items)
    st.subheader(module.display_name)
    st.markdown(f"## {content.title}")
    st.write(f"**Topic:** {content.topic} | **Difficulty:** {content.difficulty}")
    st.write(content.content)

    user_answer = _render_answer_input(content)
    confidence = st.slider("Confidence", min_value=0.0, max_value=1.0, value=0.6, step=0.1)
    action_label = st.selectbox("AI Coaching", [action.label for action in COACHING_ACTIONS.values()], index=0)
    question = st.text_area("Ask My Coach", value="", height=90)

    if st.button("AI Coaching", type="primary"):
        context = _content_to_problem_context(content, user_answer=user_answer)
        result = hint_service.coach(
            context,
            action=_action_key(action_label),
            user_question=question,
            hint_level=1,
        )
        st.info(result.get("response") or result.get("hint"))
        history = list(st.session_state.get("module_coach_history", []))
        history.append({"content_id": content.id, "action": result.get("action"), "response": result.get("response")})
        st.session_state["module_coach_history"] = history

    if st.button("Submit Session"):
        is_correct = _is_correct(content, user_answer)
        coach_history = [
            item for item in st.session_state.get("module_coach_history", []) if item.get("content_id") == content.id
        ]
        payload = {
            "mode": "exam" if app_mode == "Exam Mode" else "learning",
            "content_module": selected_module_id,
            "content_id": content.id,
            "problem_title": content.title,
            "topic": content.topic,
            "difficulty": content.difficulty,
            "confidence": confidence,
            "thinking_progress": 0.7 if user_answer else 0.3,
            "hints_used": len(coach_history),
            "hint_level_used": min(len(coach_history), 4),
            "solved": is_correct,
            "conceptual_mistakes": [] if is_correct else [f"Needs review: {content.topic}"],
            "insights": [f"Review the key idea for {content.topic}."],
            "execution_trace": {},
        }
        if app_mode == "Exam Mode":
            payload.update(
                {
                    "exam_timer_seconds": int(st.session_state.get("exam_timer_minutes", 30)) * 60,
                    "exam_hints_available": st.session_state.get("exam_hints_available", True),
                    "exam_hint_penalty_enabled": st.session_state.get("exam_hint_penalty_enabled", False),
                    "exam_hint_penalty_points": st.session_state.get("exam_hint_penalty_points", 0),
                }
            )
        result = learning_engine.record_session(payload)
        st.success("Session recorded.")
        st.json(result["reflection"])


def _select_content(content_items: list[LearningContent]) -> LearningContent:
    titles = [f"{item.id} - {item.title}" for item in content_items]
    selected = st.selectbox("Question", titles)
    selected_id = selected.split(" - ", 1)[0]
    return next(item for item in content_items if item.id == selected_id)


def _render_answer_input(content: LearningContent) -> str:
    if content.question_type == "multiple_choice" and content.choices:
        return st.radio("Answer", content.choices)
    return st.text_area("Answer", value="", height=120)


def _content_to_problem_context(content: LearningContent, *, user_answer: str) -> ProblemContext:
    choices = "\n".join(content.choices or [])
    return ProblemContext(
        source_platform=content.source,
        external_problem_id=content.id,
        title=content.title,
        description=content.content,
        constraints=f"Question type: {content.question_type}",
        examples=choices,
        difficulty=content.difficulty,
        programming_language=content.language or "General",
        student_code=user_answer,
        hint_level=1,
    )


def _is_correct(content: LearningContent, user_answer: str) -> bool:
    normalized_answer = user_answer.strip().lower()
    expected = content.answer.strip().lower()
    if not normalized_answer or not expected:
        return False
    return expected in normalized_answer or normalized_answer in expected


def _action_key(label: str) -> str:
    for key, action in COACHING_ACTIONS.items():
        if action.label == label:
            return key
    return "ask_coach"

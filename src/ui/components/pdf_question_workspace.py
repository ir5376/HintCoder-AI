"""Reusable, presentation-only Streamlit components for extracted questions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from html import escape

import streamlit as st

from src.ui.components.pdf_question_view_models import (
    DeletedQuestionViewModel,
    ExtractionStateViewModel,
    ExtractionStatus,
    FrontendAction,
    FrontendActionType,
    HintPanelViewModel,
    LearningProgressViewModel,
    LearningStatus,
    PdfQuestionWorkspaceData,
    QuestionNavigationViewModel,
    QuestionViewModel,
)

ActionCallback = Callable[[FrontendAction], None]


_EXTRACTION_COPY = {
    ExtractionStatus.PENDING: ("info", "PDF extraction is waiting to start."),
    ExtractionStatus.PROCESSING: ("info", "Extracting questions from the PDF..."),
    ExtractionStatus.COMPLETED: ("success", "Question extraction completed."),
    ExtractionStatus.PARTIAL: ("warning", "Some questions were extracted, but the result is incomplete."),
    ExtractionStatus.FAILED: ("error", "Question extraction failed."),
    ExtractionStatus.OCR_REQUIRED: ("warning", "This PDF appears to contain images only and requires OCR."),
    ExtractionStatus.EMPTY: ("warning", "No questions were extracted from this PDF."),
}


def extraction_message(state: ExtractionStateViewModel) -> tuple[str, str]:
    tone, default = _EXTRACTION_COPY[state.status]
    return tone, state.detail.strip() if state.detail and state.detail.strip() else default


def question_position_label(navigation: QuestionNavigationViewModel) -> str:
    if navigation.total <= 0:
        return "Question 0 of 0"
    current = min(max(navigation.current_index + 1, 1), navigation.total)
    return f"Question {current} of {navigation.total}"


def _emit(callback: ActionCallback | None, action: FrontendAction) -> None:
    if callback is not None:
        callback(action)


def render_extraction_state(state: ExtractionStateViewModel) -> None:
    tone, message = extraction_message(state)
    getattr(st, tone)(message)
    if state.status == ExtractionStatus.PROCESSING:
        st.progress(0, text="Processing PDF")


def render_question_display(question: QuestionViewModel, on_action: ActionCallback | None = None) -> str:
    if question.shared_passage:
        st.markdown("#### Shared passage")
        st.markdown(
            f'<div class="hc-card"><p class="hc-muted">{escape(question.shared_passage)}</p></div>',
            unsafe_allow_html=True,
        )

    heading, source = st.columns([4, 1])
    heading.markdown(f"#### Question {escape(question.number)}")
    source.caption(f"Source page {question.source_page}" if question.source_page is not None else "Source page unavailable")
    st.write(question.text)
    if question.is_uncertain:
        st.warning(question.uncertainty_message or "This extraction may be uncertain. Review it against the source PDF.")

    answer_key = f"pdf_question_answer_{question.id}"

    def emit_answer() -> None:
        _emit(
            on_action,
            FrontendAction(
                FrontendActionType.ANSWER_CHANGED,
                question.id,
                {"answer": st.session_state.get(answer_key, "")},
            ),
        )

    if question.choices:
        choice_ids = [choice.id for choice in question.choices]
        labels = {choice.id: f"{choice.label}. {choice.text}" for choice in question.choices}
        current = question.draft_answer if question.draft_answer in choice_ids else None
        if answer_key not in st.session_state and current is not None:
            st.session_state[answer_key] = current
        selected = st.radio(
            "Choose an answer",
            choice_ids,
            index=None,
            format_func=labels.get,
            key=answer_key,
            on_change=emit_answer,
        )
        return selected or ""

    if answer_key not in st.session_state:
        st.session_state[answer_key] = question.draft_answer
    return st.text_area(
        "Your answer",
        key=answer_key,
        height=120,
        placeholder="Write your answer here.",
        on_change=emit_answer,
    )


def render_question_navigation(navigation: QuestionNavigationViewModel, question_id: str, on_action: ActionCallback | None = None) -> None:
    previous, position, following = st.columns([1, 1.3, 1])
    if previous.button("Previous Question", disabled=not navigation.has_previous, use_container_width=True):
        _emit(on_action, FrontendAction(FrontendActionType.PREVIOUS_QUESTION, question_id))
    position.markdown(f"<div style='text-align:center;padding:.55rem'>{question_position_label(navigation)}</div>", unsafe_allow_html=True)
    if following.button("Next Question", disabled=not navigation.has_next, use_container_width=True):
        _emit(on_action, FrontendAction(FrontendActionType.NEXT_QUESTION, question_id))


def render_learning_progress(progress: LearningProgressViewModel) -> None:
    total = max(progress.total_count, 0)
    completed = min(max(progress.completed_count, 0), total) if total else 0
    percent = int((completed / total) * 100) if total else 0
    labels = {
        LearningStatus.DRAFT: "Draft answer saved",
        LearningStatus.COMPLETED: "Completed",
        LearningStatus.REVIEW_NEEDED: "Review needed",
    }
    last_opened = '<span class="hc-chip">Last opened</span>' if progress.is_last_opened else ""
    st.markdown(
        f'<div class="hc-card"><div class="hc-item"><div><b>{completed} of {total} questions completed</b><br>'
        f'<span class="hc-muted">{labels[progress.status]}</span></div>{last_opened}</div>'
        f'<div class="hc-progress"><div style="width:{percent}%"></div></div></div>',
        unsafe_allow_html=True,
    )


def render_hint_panel(hints: HintPanelViewModel, question_id: str, on_action: ActionCallback | None = None) -> None:
    st.markdown("#### Progressive hints")
    if not hints.has_reliable_solution:
        st.info("No reliable linked solution is available. Hints cannot be verified against an official answer.")
    by_level = {item.level: item for item in hints.levels}
    for level in range(1, 4):
        item = by_level.get(level)
        unlocked = bool(item and item.unlocked)
        st.markdown(f"**Hint {level}**")
        if item and item.viewed_text:
            st.success(item.viewed_text)
        elif item and item.is_loading:
            st.info(f"Loading Hint {level}...")
        elif st.button(f"Get Hint {level}", key=f"pdf_hint_{question_id}_{level}", disabled=not unlocked):
            _emit(on_action, FrontendAction(FrontendActionType.REQUEST_HINT, question_id, {"level": level}))
        if not unlocked:
            st.caption("Locked until the previous hint has been viewed." if level > 1 else "This hint is currently unavailable.")


def render_question_management(
    question: QuestionViewModel,
    deleted_questions: Sequence[DeletedQuestionViewModel] = (),
    on_action: ActionCallback | None = None,
) -> None:
    st.markdown("#### Manage extracted questions")
    with st.expander("Edit Question"):
        with st.form(f"edit_pdf_question_{question.id}"):
            number = st.text_input("Question number", value=question.number)
            passage = st.text_area("Shared passage", value=question.shared_passage or "")
            text = st.text_area("Question text", value=question.text)
            choices = [
                {"id": choice.id, "label": choice.label, "text": st.text_input(f"Choice {choice.label}", value=choice.text, key=f"edit_choice_{question.id}_{choice.id}")}
                for choice in question.choices
            ]
            source_page = st.number_input("Source page", min_value=1, value=question.source_page or 1)
            uncertain = st.checkbox("Mark extraction as uncertain", value=question.is_uncertain)
            if st.form_submit_button("Apply edits", type="primary"):
                _emit(on_action, FrontendAction(FrontendActionType.EDIT_QUESTION, question.id, {"number": number, "shared_passage": passage, "text": text, "choices": choices, "source_page": int(source_page), "is_uncertain": uncertain}))

    with st.expander("Delete Question"):
        confirmed = st.checkbox("I understand this question will be removed from normal navigation.", key=f"confirm_delete_{question.id}")
        if st.button("Delete Question", key=f"delete_pdf_question_{question.id}", disabled=not confirmed):
            _emit(on_action, FrontendAction(FrontendActionType.DELETE_QUESTION, question.id))

    with st.expander("Restore Question"):
        if not deleted_questions:
            st.caption("No deleted questions are available to restore.")
        for deleted in deleted_questions:
            label = f"Question {deleted.number}: {deleted.text[:80]}"
            if st.button(f"Restore {label}", key=f"restore_pdf_question_{deleted.id}"):
                _emit(on_action, FrontendAction(FrontendActionType.RESTORE_QUESTION, deleted.id))

    with st.expander("Reprocess PDF"):
        confirmed = st.checkbox("I understand extracted question text may change.", key=f"confirm_reprocess_pdf_{question.document_id or question.id}")
        if st.button("Reprocess PDF", disabled=not confirmed, key=f"reprocess_pdf_{question.document_id or question.id}"):
            _emit(on_action, FrontendAction(FrontendActionType.REPROCESS_PDF, payload={"document_id": question.document_id}))


def render_pdf_question_workspace(data: PdfQuestionWorkspaceData, on_action: ActionCallback | None = None) -> None:
    """Render a complete workspace from an object matching PdfQuestionWorkspaceData."""
    render_extraction_state(data.extraction)
    render_learning_progress(data.progress)
    render_question_display(data.question, on_action)
    render_question_navigation(data.navigation, data.question.id, on_action)
    render_hint_panel(data.hints, data.question.id, on_action)
    render_question_management(data.question, data.deleted_questions, on_action)

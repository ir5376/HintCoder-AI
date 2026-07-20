"""Presentation-only solution-link review controls."""

from __future__ import annotations

from collections.abc import Callable
from html import escape

import streamlit as st

from src.ui.components.solution_link_view_models import (
    SolutionLinkReviewViewModel,
    SolutionReviewAction,
    SolutionReviewActionType,
    SolutionSourceStatus,
)

SolutionActionCallback = Callable[[SolutionReviewAction], None]


_LINK_COPY = {
    "no_solution": ("No solution", "No solution is linked to this question."),
    "automatically_matched": ("Automatically matched", "A solution was matched automatically."),
    "manually_confirmed": ("Manually confirmed", "A learner or reviewer confirmed this solution link."),
    "low_confidence": ("Low-confidence candidate", "Review the suggested match before using it."),
}

_SOURCE_COPY = {
    SolutionSourceStatus.PENDING: ("info", "Solution PDF is waiting to be processed."),
    SolutionSourceStatus.PROCESSING: ("info", "Solution PDF is being processed."),
    SolutionSourceStatus.COMPLETED: ("success", "Solution PDF processing completed."),
    SolutionSourceStatus.PARTIAL: ("warning", "Solution PDF processing completed with unresolved items."),
    SolutionSourceStatus.FAILED: ("error", "Solution PDF processing failed."),
}


def solution_source_message(status: SolutionSourceStatus, detail: str | None = None) -> tuple[str, str]:
    tone, default = _SOURCE_COPY[status]
    return tone, detail.strip() if detail and detail.strip() else default


def explanation_preview(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(limit - 3, 0)].rstrip()}..."


def _emit(callback: SolutionActionCallback | None, action: SolutionReviewAction) -> None:
    if callback is not None:
        callback(action)


def render_solution_link_review(
    data: SolutionLinkReviewViewModel,
    on_action: SolutionActionCallback | None = None,
) -> None:
    """Render review controls; all mutations are delegated through ``on_action``."""
    title, description = _LINK_COPY[data.link_status.value]
    st.markdown("#### Solution link")
    st.markdown(
        f'<div class="hc-card"><div class="hc-label">Current status</div>'
        f'<div class="hc-item"><div><b>{escape(title)}</b><br>'
        f'<span class="hc-muted">{escape(description)}</span></div>'
        f'<span class="hc-chip">{escape(data.link_status.value.replace("_", " ").title())}</span></div></div>',
        unsafe_allow_html=True,
    )

    with st.expander("Solution source and matching", expanded=data.link_status.value == "low_confidence"):
        tone, message = solution_source_message(data.source_status, data.source_detail)
        getattr(st, tone)(message)
        if data.source_status == SolutionSourceStatus.PROCESSING:
            st.progress(0, text="Processing solution PDF")

        uploaded = st.file_uploader(
            "Attach a solution PDF",
            type=["pdf"],
            key=f"solution_pdf_{data.question_id}",
            help="The backend will store and process this file after you attach it.",
        )
        if st.button(
            "Attach solution PDF",
            key=f"attach_solution_pdf_{data.question_id}",
            disabled=uploaded is None or on_action is None,
        ):
            _emit(
                on_action,
                SolutionReviewAction(
                    SolutionReviewActionType.ATTACH_SOLUTION_PDF,
                    data.question_id,
                    {"file": uploaded, "filename": uploaded.name, "content_type": uploaded.type},
                ),
            )
        if on_action is None:
            st.caption("Solution management is read-only until the repository action adapter is connected.")

        if data.link_status.value == "low_confidence" and data.candidate:
            candidate = data.candidate
            st.markdown("##### Suggested match")
            st.markdown(
                f'<div class="hc-card"><b>Candidate question {escape(candidate.question_number)}</b>'
                f'<p class="hc-muted">{escape(explanation_preview(candidate.explanation_snippet))}</p></div>',
                unsafe_allow_html=True,
            )
            confirm, reject = st.columns(2)
            if confirm.button("Confirm match", key=f"confirm_solution_{data.question_id}", disabled=on_action is None, use_container_width=True):
                _emit(on_action, SolutionReviewAction(SolutionReviewActionType.CONFIRM_MATCH, data.question_id, {"solution_id": candidate.id}))
            if reject.button("Reject candidate", key=f"reject_solution_{data.question_id}", disabled=on_action is None, use_container_width=True):
                _emit(on_action, SolutionReviewAction(SolutionReviewActionType.REJECT_CANDIDATE, data.question_id, {"solution_id": candidate.id}))

        alternatives = [item for item in data.extracted_solutions if not data.candidate or item.id != data.candidate.id]
        if alternatives:
            st.markdown("##### Select another extracted solution")
            labels = {item.id: f"Question {item.question_number} — {explanation_preview(item.explanation_snippet, 90)}" for item in alternatives}
            selected_id = st.selectbox(
                "Extracted solution",
                [item.id for item in alternatives],
                format_func=labels.get,
                key=f"alternate_solution_{data.question_id}",
            )
            if st.button("Use selected solution", key=f"select_solution_{data.question_id}", disabled=on_action is None):
                _emit(on_action, SolutionReviewAction(SolutionReviewActionType.SELECT_SOLUTION, data.question_id, {"solution_id": selected_id}))

        review_solution = data.confirmed_solution or (data.candidate if data.link_status.value == "low_confidence" else None)
        if review_solution and review_solution.full_solution:
            with st.expander("Review full solution"):
                st.warning("Full solutions are shown only in this explicit review section.")
                st.write(review_solution.full_solution)


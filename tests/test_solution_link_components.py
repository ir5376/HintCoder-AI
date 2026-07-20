from src.ui.components.solution_link_review import explanation_preview, solution_source_message
from src.ui.components.solution_link_view_models import (
    SolutionReviewAction,
    SolutionReviewActionType,
    SolutionSourceStatus,
)


def test_solution_source_statuses_have_presentation_copy():
    for status in SolutionSourceStatus:
        tone, message = solution_source_message(status)
        assert tone in {"info", "success", "warning", "error"}
        assert message


def test_solution_source_detail_overrides_default_copy():
    assert solution_source_message(SolutionSourceStatus.PARTIAL, "Two answers need review.") == (
        "warning",
        "Two answers need review.",
    )


def test_explanation_preview_is_short_and_normalized():
    preview = explanation_preview("  This   is a long explanation.  ", limit=20)
    assert preview == "This is a long ex..."
    assert len(preview) <= 20


def test_confirmation_action_has_repository_adapter_payload():
    action = SolutionReviewAction(
        SolutionReviewActionType.CONFIRM_MATCH,
        "question-4",
        {"solution_id": "solution-9"},
    )
    assert action.kind.value == "confirm_solution_match"
    assert action.question_id == "question-4"
    assert action.payload == {"solution_id": "solution-9"}

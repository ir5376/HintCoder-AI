from src.ui.components.pdf_question_view_models import (
    ExtractionStateViewModel,
    ExtractionStatus,
    FrontendAction,
    FrontendActionType,
    QuestionNavigationViewModel,
)
from src.ui.components.pdf_question_workspace import extraction_message, question_position_label


def test_question_position_label_clamps_invalid_indexes():
    assert question_position_label(QuestionNavigationViewModel(1, 5, True, True)) == "Question 2 of 5"
    assert question_position_label(QuestionNavigationViewModel(99, 5, True, False)) == "Question 5 of 5"
    assert question_position_label(QuestionNavigationViewModel(0, 0, False, False)) == "Question 0 of 0"


def test_all_extraction_states_have_user_facing_copy():
    for status in ExtractionStatus:
        tone, message = extraction_message(ExtractionStateViewModel(status))
        assert tone in {"info", "success", "warning", "error"}
        assert message


def test_extraction_detail_overrides_default_copy():
    assert extraction_message(ExtractionStateViewModel(ExtractionStatus.PARTIAL, "3 pages need review.")) == ("warning", "3 pages need review.")


def test_extraction_message_hides_sqlalchemy_traceback():
    detail = "Traceback (most recent call last):\n  File 'worker.py'\nsqlalchemy.exc.OperationalError: database is locked"
    assert extraction_message(ExtractionStateViewModel(ExtractionStatus.FAILED, detail)) == (
        "error",
        "Couldn't import PDF.",
    )


def test_frontend_actions_have_stable_string_values():
    action = FrontendAction(FrontendActionType.REQUEST_HINT, "question-7", {"level": 2})
    assert action.kind.value == "request_hint"
    assert action.question_id == "question-7"
    assert action.payload == {"level": 2}

from src.ui.problem_detail_page import (
    answer_status_label,
    can_submit_answer,
    load_answer_state,
    presentation_choices,
    submit_selected_answer,
)


class FakeProblemService:
    def __init__(self, state=None, result=None):
        self.state = state or {"status": "not_submitted"}
        self.result = result or {"status": "correct", "selected_answer": "C. 8"}
        self.submissions = []
        self.loaded = []

    def get_answer_state(self, problem_id):
        self.loaded.append(problem_id)
        return self.state

    def submit_answer(self, problem_id, selected_answer):
        self.submissions.append((problem_id, selected_answer))
        return self.result


def test_duplicate_question_stem_excluded_from_choices():
    question = "Which number is even?"
    choices = ["Which number is even?", "A. 3", "B. 5", "C. 8", "D. 9"]

    assert presentation_choices(question, choices) == ["A. 3", "B. 5", "C. 8", "D. 9"]


def test_duplicate_question_stem_with_choice_label_excluded_from_choices():
    question = "Which number is even?"
    choices = ["A. Which number is even?", "B. 3", "C. 8"]

    assert presentation_choices(question, choices) == ["B. 3", "C. 8"]


def test_submit_button_unavailable_until_valid_choice_is_selected():
    choices = ["A. 3", "B. 5", "C. 8"]

    assert can_submit_answer(None, choices) is False
    assert can_submit_answer("", choices) is False
    assert can_submit_answer("D. 9", choices) is False
    assert can_submit_answer("C. 8", choices) is True


def test_submit_answer_called_once():
    service = FakeProblemService(result={"status": "correct", "selected_answer": "C. 8"})

    result = submit_selected_answer(service, "learning_item:3", "C. 8")

    assert result["status"] == "correct"
    assert service.submissions == [("learning_item:3", "C. 8")]


def test_correct_result_label_rendered():
    assert answer_status_label("correct") == "Correct"


def test_incorrect_result_label_rendered():
    assert answer_status_label("incorrect") == "Incorrect"


def test_unverified_result_label_rendered():
    assert answer_status_label("unverified") == "Unverified"


def test_latest_persisted_state_loaded_after_rerun():
    state = {"status": "incorrect", "selected_answer": "A. 3", "submission_id": 12}
    service = FakeProblemService(state=state)

    assert load_answer_state(service, "learning_item:3") == state
    assert service.loaded == ["learning_item:3"]

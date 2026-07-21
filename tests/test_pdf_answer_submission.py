import os
import tempfile

from src.database import get_session, init_db
from src.models.learning_item import LearningItemAnswerSubmission
from src.services.problem_service import ProblemService


QUESTION_TEXT = """Question 1
Which number is even?
A. 3
B. 5
C. 8
D. 9
"""


SOLUTION_TEXT = """Question 1
Correct answer: C. 8
Explanation:
An even number is divisible by 2 without a remainder.
8 divided by 2 equals 4, so 8 is even.
"""


def _database_url():
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir, f"sqlite:///{os.path.join(temp_dir.name, 'test.db')}"


def _import_demo_item(service: ProblemService, *, with_answer: bool = True) -> str:
    result = service.import_pdf_source(
        question_pdf_name="demo_questions.pdf",
        question_pdf=QUESTION_TEXT,  # type: ignore[arg-type]
        answer_pdf_name="demo_solutions.pdf" if with_answer else "",
        answer_pdf=SOLUTION_TEXT if with_answer else None,  # type: ignore[arg-type]
    )
    return f"learning_item:{result['items'][0]['learning_item']['id']}"


def test_submit_answer_grades_c_correct_for_imported_learning_item():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            public_id = _import_demo_item(service)

            result = service.submit_answer(public_id, "C")

        assert result["status"] == "correct"
        assert result["selected_answer"] == "C. 8"
        assert result["correct_answer"] == "C. 8"
        assert result["explanation_available"] is True
        assert result["submission_id"]
        assert result["is_correct"] is True


def test_submit_answer_grades_a_incorrect_and_persists_latest_state():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            public_id = _import_demo_item(service)

            result = service.submit_answer(public_id, "A")
            state = service.get_answer_state(public_id)

        assert result["status"] == "incorrect"
        assert result["selected_answer"] == "A. 3"
        assert state["status"] == "incorrect"
        assert state["selected_answer"] == "A. 3"
        assert state["is_correct"] is False


def test_answer_state_survives_new_service_session_instance():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            public_id = _import_demo_item(service)
            service.submit_answer(public_id, "8")

        with get_session(database_url) as session:
            state = ProblemService(session).get_answer_state(public_id)

        assert state["status"] == "correct"
        assert state["selected_answer"] == "C. 8"
        assert state["verified"] is True


def test_missing_official_answer_returns_unverified_and_persists_submission():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            public_id = _import_demo_item(service, with_answer=False)

            result = service.submit_answer(public_id, "C")
            state = service.get_answer_state(public_id)

        assert result["status"] == "unverified"
        assert result["correct_answer"] == ""
        assert result["is_correct"] is None
        assert state["status"] == "unverified"
        assert state["verified"] is False
        assert state["selected_answer"] == "C. 8"


def test_resubmission_creates_another_attempt_and_latest_state_wins():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            public_id = _import_demo_item(service)
            first = service.submit_answer(public_id, "A")
            second = service.submit_answer(public_id, "C.")
            state = service.get_answer_state(public_id)
            count = session.query(LearningItemAnswerSubmission).count()

        assert first["status"] == "incorrect"
        assert second["status"] == "correct"
        assert second["submission_id"] != first["submission_id"]
        assert state["submission_id"] == second["submission_id"]
        assert state["status"] == "correct"
        assert count == 2


def test_deterministic_grading_does_not_call_openai(monkeypatch):
    def fail_openai(*_args, **_kwargs):
        raise AssertionError("OpenAI should not be called during deterministic grading")

    monkeypatch.setattr("src.services.hint_service.HintService.generate_hint", fail_openai, raising=False)
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            public_id = _import_demo_item(service)
            result = service.submit_answer(public_id, "C. 8")

        assert result["status"] == "correct"

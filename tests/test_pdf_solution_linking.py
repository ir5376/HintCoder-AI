import os
import tempfile

from src.database import get_session, init_db
from src.models.learning_item import AnswerRecord, LearningItem
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


def test_pdf_answer_pdf_links_solution_to_imported_learning_item():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            result = service.import_pdf_source(
                question_pdf_name="demo_questions.pdf",
                question_pdf=QUESTION_TEXT,  # type: ignore[arg-type]
                answer_pdf_name="demo_solutions.pdf",
                answer_pdf=SOLUTION_TEXT,  # type: ignore[arg-type]
            )
            learning_item_id = result["items"][0]["learning_item"]["id"]
            public_id = f"learning_item:{learning_item_id}"
            item = session.query(LearningItem).filter(LearningItem.id == learning_item_id).one()
            answer_record = session.query(AnswerRecord).filter(AnswerRecord.matched_learning_item_id == learning_item_id).one()
            solution = service.get_linked_solution(public_id)

        assert item.question_number == "1"
        assert item.verified_answer == "C. 8"
        assert item.answer_status == "verified"
        assert "divisible by 2" in (item.explanation or "")
        assert answer_record.verified_answer == "C. 8"
        assert answer_record.question_number == "1"
        assert solution == {
            "has_reliable_solution": True,
            "canonical_answer": "C. 8",
            "explanation": "An even number is divisible by 2 without a remainder.\n8 divided by 2 equals 4, so 8 is even.",
            "answer_record_id": answer_record.id,
            "learning_item_id": learning_item_id,
        }


def test_linked_solution_survives_new_service_session_and_retry_does_not_duplicate_records():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            first = ProblemService(session).import_pdf_source(
                question_pdf_name="demo_questions.pdf",
                question_pdf=QUESTION_TEXT,  # type: ignore[arg-type]
                answer_pdf_name="demo_solutions.pdf",
                answer_pdf=SOLUTION_TEXT,  # type: ignore[arg-type]
            )
            learning_item_id = first["items"][0]["learning_item"]["id"]

        with get_session(database_url) as session:
            service = ProblemService(session)
            service.import_pdf_source(
                question_pdf_name="demo_questions.pdf",
                question_pdf=QUESTION_TEXT,  # type: ignore[arg-type]
                answer_pdf_name="demo_solutions.pdf",
                answer_pdf=SOLUTION_TEXT,  # type: ignore[arg-type]
            )
            solution = service.get_linked_solution(f"learning_item:{learning_item_id}")
            answer_count = session.query(AnswerRecord).filter(AnswerRecord.matched_learning_item_id == learning_item_id).count()

        assert solution["has_reliable_solution"] is True
        assert solution["canonical_answer"] == "C. 8"
        assert "8 is even" in solution["explanation"]
        assert answer_count == 1


def test_existing_example_problems_remain_unaffected_by_solution_linking():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            before = [problem for problem in ProblemService(session).get_problem_list() if not str(problem["id"]).startswith("learning_item:")]
            ProblemService(session).import_pdf_source(
                question_pdf_name="demo_questions.pdf",
                question_pdf=QUESTION_TEXT,  # type: ignore[arg-type]
                answer_pdf_name="demo_solutions.pdf",
                answer_pdf=SOLUTION_TEXT,  # type: ignore[arg-type]
            )
            after = [problem for problem in ProblemService(session).get_problem_list() if not str(problem["id"]).startswith("learning_item:")]

        assert len(before) == 10
        assert [problem["id"] for problem in after] == [problem["id"] for problem in before]

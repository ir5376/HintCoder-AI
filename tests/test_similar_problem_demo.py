import os
import tempfile

from src.database import get_session, init_db
from src.models.learning_item import LearningItem
from src.models.problem import Problem
from src.services.problem_service import ProblemService
from src.ui.problem_detail_page import (
    get_similar_problem_result,
    similar_problem_button_key,
    similar_problem_display_key,
    similar_problem_hint_button_key,
    similar_problem_hint_result_key,
    similar_problem_result_key,
    store_similar_problem_result,
)


def _database_url():
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir, f"sqlite:///{os.path.join(temp_dir.name, 'test.db')}"


def test_generate_similar_problem_for_builtin_problem_does_not_modify_original():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            original = service.get_problem(1)
            problem_count = session.query(Problem).count()

            generated = service.generate_similar_problem(1)

            reloaded = service.get_problem(1)
            assert session.query(Problem).count() == problem_count

        assert generated["question"]
        assert generated["question"] != original["description"]
        assert generated["difficulty"] == original["difficulty"]
        assert generated["choices"]
        assert generated["correct_answer"]
        assert generated["explanation"]
        assert reloaded == original


def test_generate_similar_problem_for_imported_learning_item_is_structured():
    question_text = """Demo Exam
Question 1 What is 2 + 2?
A. 3
B. 4
C. 5
D. 6
"""
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            imported = service.import_pdf_source(question_pdf_name="demo.txt", question_pdf=question_text)
            item_id = imported["items"][0]["learning_item"]["id"]
            original = session.query(LearningItem).filter(LearningItem.id == item_id).one().to_dict()

            generated = service.generate_similar_problem(f"learning_item:{item_id}")
            reloaded = session.query(LearningItem).filter(LearningItem.id == item_id).one().to_dict()

        assert generated["question"]
        assert generated["question"] != original["content"]
        assert generated["difficulty"] == original["difficulty"]
        assert generated["choices"]
        assert generated["correct_answer"] in generated["choices"]
        assert generated["explanation"]
        assert reloaded["content"] == original["content"]


def test_similar_problem_session_keys_separate_data_from_widgets():
    problem_id = "learning_item:71"
    keys = {
        similar_problem_result_key(problem_id),
        similar_problem_button_key(problem_id),
        similar_problem_display_key(problem_id),
        similar_problem_hint_button_key(problem_id),
        similar_problem_hint_result_key(problem_id),
    }

    assert len(keys) == 5
    assert similar_problem_result_key(problem_id) not in {
        similar_problem_button_key(problem_id),
        similar_problem_display_key(problem_id),
        similar_problem_hint_button_key(problem_id),
    }


def test_similar_problem_result_remains_visible_after_rerun_and_can_be_replaced():
    state = {}
    problem_id = "learning_item:71"
    first = {"question": "First generated question?", "choices": ["A", "B"]}
    second = {"question": "Second generated question?", "choices": ["C", "D"]}

    store_similar_problem_result(state, problem_id, first)
    assert get_similar_problem_result(state, problem_id) == first

    rerun_state = dict(state)
    assert get_similar_problem_result(rerun_state, problem_id) == first

    store_similar_problem_result(rerun_state, problem_id, second)
    assert get_similar_problem_result(rerun_state, problem_id) == second


def test_similar_problem_results_do_not_mix_between_learning_items():
    state = {}
    first_id = "learning_item:71"
    second_id = "learning_item:72"
    first = {"question": "Problem 71 variant"}
    second = {"question": "Problem 72 variant"}

    store_similar_problem_result(state, first_id, first)
    store_similar_problem_result(state, second_id, second)

    assert get_similar_problem_result(state, first_id) == first
    assert get_similar_problem_result(state, second_id) == second

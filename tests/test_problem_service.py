import os
import tempfile

from src.database import init_db, get_session
from src.models.problem import Problem
from src.services.problem_service import ProblemService


def test_get_filters_and_problem_list():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            filters = service.get_filters()
            problem_list = service.get_problem_list()

        assert "categories" in filters
        assert "difficulties" in filters
        assert len(problem_list) == 10


def test_get_problem_detail():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            result = service.get_problem(1)

        assert result is not None
        assert result["id"] == 1
        assert result["title"] != ""


def test_init_db_replaces_existing_seed_entries_without_duplicates():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            session.add(
                Problem(
                    title="Old Problem",
                    description="Old description",
                    category="Old Category",
                    difficulty="Easy",
                    problem_type="Function Implementation",
                    function_name="legacy_problem",
                    starter_code="pass",
                    constraints="",
                    test_cases="[]",
                    explanation="",
                    source_type="",
                    source_reference="",
                )
            )
            session.commit()

        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            problem_list = service.get_problem_list()
            legacy_problem = session.query(Problem).filter(Problem.function_name == "legacy_problem").one_or_none()

        assert len(problem_list) == 10
        assert [problem["id"] for problem in problem_list] == list(range(1, 11))
        assert legacy_problem is None

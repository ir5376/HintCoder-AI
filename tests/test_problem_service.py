import os
import tempfile

from src.database import init_db, get_session
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

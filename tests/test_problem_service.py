import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text

from src.database import init_db, get_session
from src.models.problem import Problem
from src.repositories.problem_repository import ProblemRepository
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


def test_get_random_problem_returns_problem_when_available():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            result = service.get_random_problem()

        assert result is not None
        assert result["title"] != ""


def test_problem_repository_loads_problem_json_files_from_directory(tmp_path):
    problems_dir = tmp_path / "problems"
    problems_dir.mkdir()
    (problems_dir / "sample.json").write_text(
        '{"problems": [{"title": "Sample", "description": "Sample description", "category": "Algorithms", "difficulty": "Easy", "problem_type": "Function Implementation", "function_name": "sample", "starter_code": "pass"}]}',
        encoding="utf-8",
    )

    session = object()
    repository = ProblemRepository(session)  # type: ignore[arg-type]
    repository._problem_dir = problems_dir

    loaded = repository._load_problem_sets_from_disk()

    assert len(loaded) == 1
    assert loaded[0]["title"] == "Sample"


def test_problem_repository_loads_problem_list_json_files_from_directory(tmp_path):
    problems_dir = tmp_path / "problems"
    problems_dir.mkdir()
    (problems_dir / "sample.json").write_text(
        '[{"title": "List Sample", "description": "From list", "category": "Basics", "difficulty": "Medium", "problem_type": "Function Implementation", "function_name": "list_sample", "starter_code": "pass"}]',
        encoding="utf-8",
    )

    session = object()
    repository = ProblemRepository(session)  # type: ignore[arg-type]
    repository._problem_dir = problems_dir

    loaded = repository._load_problem_sets_from_disk()

    assert len(loaded) == 1
    assert loaded[0]["title"] == "List Sample"


def test_init_db_adds_missing_tags_column_to_existing_problem_table():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        engine = create_engine(database_url, future=True)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE problems (
                        id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL,
                        category VARCHAR(100) NOT NULL,
                        difficulty VARCHAR(50) NOT NULL,
                        problem_type VARCHAR(100) NOT NULL,
                        function_name VARCHAR(100) NOT NULL,
                        starter_code TEXT NOT NULL,
                        constraints TEXT,
                        test_cases TEXT,
                        explanation TEXT,
                        source_type VARCHAR(100),
                        source_reference VARCHAR(255),
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
        engine.dispose()

        init_db(database_url)

        with get_session(database_url) as session:
            item = Problem.from_dict(
                {
                    "title": "Legacy Tag Test",
                    "description": "desc",
                    "category": "Algorithms",
                    "difficulty": "Easy",
                    "problem_type": "Function Implementation",
                    "function_name": "legacy_tag_test",
                    "starter_code": "pass",
                }
            )
            session.add(item)
            session.commit()
            stored = session.query(Problem).filter(Problem.function_name == "legacy_tag_test").one()

        assert stored.tags == "[]"


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

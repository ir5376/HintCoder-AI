import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import streamlit as st
from sqlalchemy import create_engine, text

from src.database import init_db, get_session
from src.models.learning_item import LearningItem
from src.models.problem import Problem
from src.repositories.problem_repository import ProblemRepository
from src.services.problem_service import ProblemService
from src.ui.problem_list_page import _add_source


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


PDF_QUESTION_TEXT = """Sample Exam 2025
Subject: Networks
1. What does DNS resolve?
A. Names to IP addresses
B. Ports to sockets
C. Files to blocks
D. Keys to locks
2. Which algorithm explores neighbors level by level?
A. DFS
B. BFS
C. Greedy
D. Hashing
"""
PDF_QUESTION_BYTES = b"%PDF-1.5 fake questions"


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakePdfReader:
    def __init__(self, _data):
        self.pages = [_FakePage(PDF_QUESTION_TEXT)]


def _install_fake_pdf_reader(monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=_FakePdfReader))


def test_import_pdf_source_persists_questions_and_problem_details(monkeypatch):
    _install_fake_pdf_reader(monkeypatch)
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            result = service.import_pdf_source(
                question_pdf_name="questions.pdf",
                question_pdf=PDF_QUESTION_BYTES,
                title="Sample Exam 2025",
            )
            problem_id = result["items"][0]["problem_id"]
            problem = service.get_problem(problem_id)

        assert result["import_report"]["questions_detected"] == 2
        assert problem["source_type"] == "PDF"
        assert problem["question_number"] == "1"
        assert "What does DNS resolve?" in problem["question_text"]
        assert "A. Names to IP addresses" in problem["choices"]


def test_opening_existing_pdf_problem_does_not_reprocess(monkeypatch):
    _install_fake_pdf_reader(monkeypatch)
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            result = service.import_pdf_source(question_pdf_name="questions.pdf", question_pdf=PDF_QUESTION_BYTES)
            problem_id = result["items"][0]["problem_id"]

            def fail_if_called(*_args, **_kwargs):
                raise AssertionError("PDF import should not run when opening an existing problem")

            monkeypatch.setattr(ProblemService, "import_pdf_source", fail_if_called)
            loaded = service.get_problem(problem_id)

        assert loaded["question_text"]


def test_reimporting_same_pdf_does_not_create_duplicate_learning_items(monkeypatch):
    _install_fake_pdf_reader(monkeypatch)
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProblemService(session)
            first = service.import_pdf_source(question_pdf_name="questions.pdf", question_pdf=PDF_QUESTION_BYTES)
            second = service.import_pdf_source(question_pdf_name="questions.pdf", question_pdf=PDF_QUESTION_BYTES)
            item_count = session.query(LearningItem).filter(LearningItem.source_id == "questions.pdf").count()

        assert first["import_report"]["questions_detected"] == 2
        assert second["import_report"]["questions_detected"] == 2
        assert item_count == 2


def test_persisted_pdf_questions_survive_new_service_session_instance(monkeypatch):
    _install_fake_pdf_reader(monkeypatch)
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            result = ProblemService(session).import_pdf_source(question_pdf_name="questions.pdf", question_pdf=PDF_QUESTION_BYTES)
            problem_id = result["items"][1]["problem_id"]

        with get_session(database_url) as session:
            loaded = ProblemService(session).get_problem(problem_id)

        assert loaded["question_number"] == "2"
        assert "Which algorithm explores neighbors level by level?" in loaded["question_text"]
        assert "B. BFS" in loaded["choices"]


def test_pdf_learning_item_appears_in_problem_list_after_problem_seed_refresh(monkeypatch):
    _install_fake_pdf_reader(monkeypatch)
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            result = ProblemService(session).import_pdf_source(question_pdf_name="demo_questions.pdf", question_pdf=PDF_QUESTION_BYTES)
            imported_item = session.query(LearningItem).filter(LearningItem.id == result["items"][0]["learning_item"]["id"]).one()

        init_db(database_url)

        with get_session(database_url) as session:
            problems = ProblemService(session).get_problem_list()

        imported_rows = [problem for problem in problems if problem["id"] == f"learning_item:{imported_item.id}"]
        assert imported_item.item_type == "multiple_choice"
        assert imported_item.provider == "pdf"
        assert imported_item.source_type == "exam_pdf"
        assert imported_item.owner_user_id == "local"
        assert imported_item.source_id == "demo_questions.pdf"
        assert imported_rows
        assert imported_rows[0]["source_type"] == "PDF"
        assert imported_rows[0]["question_text"]


def test_pdf_preview_returns_structured_questions_without_persisting(monkeypatch):
    _install_fake_pdf_reader(monkeypatch)
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            preview = ProblemService(session).preview_pdf_source(question_pdf_name="questions.pdf", question_pdf=PDF_QUESTION_BYTES)
            item_count = session.query(LearningItem).filter(LearningItem.source_id == "questions.pdf").count()

        assert preview["report"]["questions_detected"] == 2
        assert preview["questions"][0]["choices"][0] == "A. Names to IP addresses"
        assert item_count == 0


def test_pdf_import_failure_returns_error_state_without_crashing():
    class FakePdf:
        name = "broken.pdf"

        def getvalue(self):
            return b"%PDF-1.4 broken"

    class FailingService:
        def import_pdf_source(self, **_kwargs):
            raise RuntimeError("parser failed")

    st.session_state["new_source_type"] = "PDF"
    st.session_state["source_pdf"] = FakePdf()
    st.session_state["source_answer_pdf"] = None
    st.session_state["source_name"] = "Broken"
    st.session_state["source_subject"] = "Auto detect"

    error = _add_source(FailingService())

    assert error == "PDF processing failed: parser failed"

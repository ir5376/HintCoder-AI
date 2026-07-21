from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base
from src.models.learning_item import (
    AnswerRecord,
    ExamSource,
    KnowledgeEntry,
    LearningActivity,
    LearningArtifact,
    LearningAttempt,
    LearningHistory,
    LearningItem,
    LearningReviewQueue,
    PassageGroup,
    ProviderSubmissionResult,
    UserProfile,
    XpEvent,
)
from src.models.problem import Problem

ROOT_DIR = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT_DIR / "seed" / "problems.json"
JSON_DATA_PATH = ROOT_DIR / "data" / "problems.json"
PROBLEMS_DIR = ROOT_DIR / "problems"


def get_engine(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, future=True)


def init_db(database_url: str) -> None:
    engine = get_engine(database_url)
    try:
        Base.metadata.create_all(engine)
        _ensure_problem_table_columns(engine)
        _ensure_learning_os_table_columns(engine)
        _seed_database(engine)
    finally:
        engine.dispose()


def _ensure_problem_table_columns(engine: Engine) -> None:
    """Add missing columns to existing problem tables so older SQLite databases keep working."""
    inspector = inspect(engine)
    if not inspector.has_table("problems"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("problems")}
    required_columns = {
        "tags": "TEXT",
    }

    if not required_columns.keys() - existing_columns:
        return

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE problems ADD COLUMN {column_name} {column_type}"))


def _ensure_learning_os_table_columns(engine: Engine) -> None:
    """Add missing Learning OS columns to older SQLite databases without dropping rows."""
    inspector = inspect(engine)
    table_columns = {
        "learning_items": {
            "item_type": "VARCHAR(100) NOT NULL DEFAULT 'unknown'",
            "owner_user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "source_type": "VARCHAR(50) NOT NULL DEFAULT 'unknown'",
            "source_id": "VARCHAR(255)",
            "provider": "VARCHAR(100)",
            "provider_problem_id": "VARCHAR(255)",
            "subject": "VARCHAR(255)",
            "exam_name": "VARCHAR(255)",
            "year": "VARCHAR(50)",
            "question_number": "VARCHAR(50)",
            "title": "VARCHAR(255) NOT NULL DEFAULT 'Untitled'",
            "content": "TEXT",
            "choices_json": "TEXT NOT NULL DEFAULT '[]'",
            "verified_answer": "TEXT",
            "inferred_answer": "TEXT",
            "answer_status": "VARCHAR(50) NOT NULL DEFAULT 'unavailable'",
            "explanation": "TEXT",
            "concepts_json": "TEXT NOT NULL DEFAULT '[]'",
            "difficulty": "VARCHAR(50) NOT NULL DEFAULT 'Unknown'",
            "original_reference": "TEXT",
            "question_type": "VARCHAR(100) NOT NULL DEFAULT 'unknown'",
            "learning_objective": "TEXT",
            "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "exam_sources": {
            "owner_user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "exam_title": "VARCHAR(255) NOT NULL DEFAULT 'Untitled exam'",
            "subject": "VARCHAR(255)",
            "year": "VARCHAR(50)",
            "question_pdf_name": "VARCHAR(255) NOT NULL DEFAULT ''",
            "answer_pdf_name": "VARCHAR(255)",
            "answer_status": "VARCHAR(50) NOT NULL DEFAULT 'unavailable'",
            "import_report_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "DATETIME",
        },
        "answer_records": {
            "exam_source_id": "INTEGER",
            "subject": "VARCHAR(255)",
            "question_number": "VARCHAR(50) NOT NULL DEFAULT ''",
            "verified_answer": "TEXT NOT NULL DEFAULT ''",
            "explanation": "TEXT",
            "page_number": "INTEGER",
            "matched_learning_item_id": "INTEGER",
            "created_at": "DATETIME",
        },
        "passage_groups": {
            "exam_source_id": "INTEGER",
            "group_identifier": "VARCHAR(100) NOT NULL DEFAULT ''",
            "passage_text": "TEXT NOT NULL DEFAULT ''",
            "page_number": "INTEGER",
            "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "DATETIME",
        },
        "knowledge_entries": {
            "learning_item_id": "INTEGER",
            "concept": "VARCHAR(255) NOT NULL DEFAULT ''",
            "source": "VARCHAR(100) NOT NULL DEFAULT ''",
            "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "DATETIME",
        },
        "learning_artifacts": {
            "learning_item_id": "INTEGER",
            "artifact_type": "VARCHAR(100) NOT NULL DEFAULT ''",
            "content_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "DATETIME",
        },
        "learning_review_queue": {
            "user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "learning_item_id": "INTEGER",
            "interval_days": "INTEGER NOT NULL DEFAULT 1",
            "status": "VARCHAR(50) NOT NULL DEFAULT 'pending'",
            "created_at": "DATETIME",
            "completed_at": "DATETIME",
        },
        "learning_history": {
            "user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "learning_item_id": "INTEGER",
            "event_type": "VARCHAR(100) NOT NULL DEFAULT ''",
            "payload_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "DATETIME",
        },
        "learning_activities": {
            "user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "activity_date": "DATE",
            "event_type": "VARCHAR(100) NOT NULL DEFAULT ''",
            "learning_item_id": "INTEGER",
            "created_at": "DATETIME",
        },
        "xp_events": {
            "user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "event_type": "VARCHAR(100) NOT NULL DEFAULT ''",
            "points": "INTEGER NOT NULL DEFAULT 0",
            "learning_item_id": "INTEGER",
            "idempotency_key": "VARCHAR(255) NOT NULL DEFAULT ''",
            "created_at": "DATETIME",
        },
        "learning_attempts": {
            "user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "learning_item_id": "INTEGER",
            "provider": "VARCHAR(100) NOT NULL DEFAULT ''",
            "provider_problem_id": "VARCHAR(255) NOT NULL DEFAULT ''",
            "language": "VARCHAR(100)",
            "source_code_hash": "VARCHAR(255)",
            "status": "VARCHAR(50) NOT NULL DEFAULT 'pending'",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "provider_submission_results": {
            "user_id": "VARCHAR(100) NOT NULL DEFAULT 'local'",
            "attempt_id": "INTEGER",
            "provider": "VARCHAR(100) NOT NULL DEFAULT ''",
            "provider_problem_id": "VARCHAR(255) NOT NULL DEFAULT ''",
            "problem_url": "TEXT",
            "language": "VARCHAR(100)",
            "source_code_hash": "VARCHAR(255)",
            "raw_status": "VARCHAR(255)",
            "normalized_status": "VARCHAR(50) NOT NULL DEFAULT 'unknown'",
            "submitted_at": "DATETIME",
            "created_at": "DATETIME",
        },
    }

    with engine.begin() as connection:
        for table_name, required_columns in table_columns.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def _load_seed_data() -> list[dict]:
    if not SEED_PATH.exists():
        return []

    with SEED_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_problem_dir_data() -> list[dict]:
    if not PROBLEMS_DIR.exists():
        return []

    problems: list[dict] = []
    for path in sorted(PROBLEMS_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            continue

        if isinstance(payload, dict):
            items = payload.get("problems") or payload.get("items") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        if isinstance(items, list):
            problems.extend(item for item in items if isinstance(item, dict))

    return problems


def _seed_database(engine: Engine) -> None:
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    seed_items = _load_seed_data()
    problem_dir_items = _load_problem_dir_data()
    combined_items = seed_items + problem_dir_items
    if not combined_items:
        return

    seen_keys: set[tuple] = set()

    with SessionLocal.begin() as session:
        session.query(Problem).delete(synchronize_session=False)
        if engine.dialect.name == "sqlite":
            try:
                session.execute(text("DELETE FROM sqlite_sequence WHERE name='problems'"))
            except Exception:
                pass

        for item in combined_items:
            key = (item.get("id"), item.get("title"), item.get("function_name"))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            session.add(Problem.from_dict(item))


class ProblemDatabase:
    def __init__(self, data_path: str | Path | None = None) -> None:
        self.data_path = Path(data_path) if data_path else JSON_DATA_PATH

    def _load_problems(self) -> list[dict]:
        if not self.data_path.exists():
            return []

        with self.data_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def get_all_problems(self) -> list[dict]:
        return self._load_problems()

    def get_problem_by_id(self, problem_id: int) -> dict | None:
        problems = self._load_problems()
        for problem in problems:
            if problem.get("id") == problem_id:
                return problem
        return None


@contextmanager
def get_session(database_url: str) -> Iterator[Session]:
    engine = get_engine(database_url)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

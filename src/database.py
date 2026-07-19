from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base
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

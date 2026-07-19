from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base
from src.models.problem import Problem

ROOT_DIR = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT_DIR / "seed" / "problems.json"
JSON_DATA_PATH = ROOT_DIR / "data" / "problems.json"


def get_engine(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, future=True)


def init_db(database_url: str) -> None:
    engine = get_engine(database_url)
    try:
        Base.metadata.create_all(engine)
        _seed_database(engine)
    finally:
        engine.dispose()


def _load_seed_data() -> list[dict]:
    if not SEED_PATH.exists():
        return []

    with SEED_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _seed_database(engine: Engine) -> None:
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    seed_items = _load_seed_data()
    if not seed_items:
        return

    with SessionLocal.begin() as session:
        session.query(Problem).delete(synchronize_session=False)
        if engine.dialect.name == "sqlite":
            try:
                session.execute(text("DELETE FROM sqlite_sequence WHERE name='problems'"))
            except Exception:
                pass

        for item in seed_items:
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

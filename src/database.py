from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base
from src.models.problem import Problem

ROOT_DIR = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT_DIR / "seed" / "problems.json"


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
        existing_keys = {
            (problem.title, problem.function_name)
            for problem in session.query(Problem).all()
        }

        for item in seed_items:
            key = (item.get("title"), item.get("function_name"))
            if key in existing_keys:
                continue
            session.add(Problem.from_dict(item))
            existing_keys.add(key)


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

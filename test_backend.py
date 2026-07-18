import json
from pathlib import Path

from src.database import ProblemDatabase
from src.services.hint_service import HintService


def test_problem_database_loads_all_problems():
    db = ProblemDatabase()
    problems = db.get_all_problems()

    assert isinstance(problems, list)
    assert len(problems) == 3
    assert problems[0]["id"] == 1
    assert problems[1]["title"] == "리스트 합 구하기"


def test_problem_database_get_problem_by_id():
    db = ProblemDatabase()
    problem = db.get_problem_by_id(2)

    assert problem is not None
    assert problem["id"] == 2
    assert problem["title"] == "리스트 합 구하기"


def test_hint_service_returns_level_hints():
    service = HintService()
    sample_problem = {"id": 1, "title": "짝수 판별"}

    hint1 = service.get_hint(sample_problem, "def solution(n): return n % 2 == 0", 1)
    hint2 = service.get_hint(sample_problem, "def solution(n): return n % 2 == 0", 2)
    hint3 = service.get_hint(sample_problem, "def solution(n): return n % 2 == 0", 3)

    assert "입력과 출력" in hint1
    assert "작은 단계" in hint2
    assert "변수와 반복문" in hint3

import os
import tempfile

from src.database import ProblemDatabase, get_session, init_db
from src.models.problem import Problem
from src.services.hint_service import HintService


class DummySession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        return None

    def query(self, *args, **kwargs):
        raise AssertionError("This test should not need to query the session")


class FakeResponses:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def create(self, **kwargs):
        return type(
            "Response",
            (),
            {
                "output": [
                    type(
                        "Output",
                        (),
                        {"content": [type("Content", (), {"text": self.response_text})()]},
                    )()
                ]
            },
        )()


class FakeOpenAIClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.responses = FakeResponses(response_text)


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
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            session.add(
                Problem(
                    title="Two Sum",
                    description="Return the indices of two numbers that add up to the target.",
                    category="Array",
                    difficulty="Easy",
                    problem_type="Function Implementation",
                    function_name="two_sum",
                    starter_code="def two_sum(nums, target):\n    pass",
                    constraints="",
                    test_cases="[]",
                    explanation="",
                    source_type="internal",
                    source_reference="",
                )
            )
            session.commit()
            problem = session.query(Problem).filter(Problem.function_name == "two_sum").one()

            service = HintService(DummySession(), openai_client=FakeOpenAIClient("A helpful hint about the central idea."))
            service._store_hint_history = lambda context, hint_level, hint: None
            context = service.build_problem_context(
                problem,
                student_code="def two_sum(nums, target):\n    return []",
                programming_language="Python",
                hint_level=1,
            )

            result1 = service.generate_hint(context, hint_level=1)
            result2 = service.generate_hint(context, hint_level=2)
            result3 = service.generate_hint(context, hint_level=3)

        assert result1["hint"]
        assert result2["hint"]
        assert result3["hint"]
        assert result1["hint_level"] == 1
        assert result2["hint_level"] == 2
        assert result3["hint_level"] == 3
        assert context.source_platform == "HintCode"
        assert context.title == "Two Sum"

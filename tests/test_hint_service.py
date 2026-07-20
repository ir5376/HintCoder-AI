import os
import tempfile

import pytest

from src.database import get_session, init_db
from src.models.problem import Problem
from src.services.hint_service import HintService, ProblemContext


class FakeResponses:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def create(self, **kwargs):
        return type("Response", (), {"output": [type("Output", (), {"content": [type("Content", (), {"text": self.response_text})()]})()]})()


class FakeOpenAIClient:
    def __init__(self, response_text: str, error: Exception | None = None):
        self.response_text = response_text
        self.error = error
        self.responses = FakeResponses(response_text)

    def __call__(self, *args, **kwargs):
        return self


class FailingOpenAIClient:
    def __init__(self, exception: Exception):
        self.exception = exception
        self.responses = type("Responses", (), {"create": lambda self, **kwargs: (_ for _ in ()).throw(exception)})()


@pytest.fixture()
def temp_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)
        yield database_url


def test_generate_hint_from_internal_problem(temp_db):
    with get_session(temp_db) as session:
        session.add(
            Problem(
                title="Two Sum",
                description="Return indices of two numbers that add up to a target.",
                category="Array",
                difficulty="Easy",
                problem_type="Function Implementation",
                function_name="two_sum",
                starter_code="def two_sum(nums, target):\n    pass",
                constraints="1 <= len(nums) <= 10^5",
                test_cases="[]",
                explanation="",
                source_type="internal",
                source_reference="",
            )
        )
        session.commit()
        problem = session.query(Problem).filter(Problem.function_name == "two_sum").one()
        service = HintService(session, openai_client=FakeOpenAIClient("A useful hint about hash maps."))

        result = service.generate_hint(
            service.build_problem_context(
                problem,
                student_code="def two_sum(nums, target):\n    return []",
                programming_language="Python",
            ),
            hint_level=2,
        )

        assert result["hint"].startswith("A useful hint")
        assert result["hint_level"] == 2
        assert result["source_platform"] == "HintCode"
        assert len(service.list_hint_history()) == 1


def test_generate_hint_from_platform_inputs(temp_db):
    with get_session(temp_db) as session:
        service = HintService(session, openai_client=FakeOpenAIClient("A platform-agnostic hint."))
        contexts = [
            ProblemContext(
                source_platform="Programmers",
                source_url="https://programmers.co.kr/learn/courses/30/lessons/42576",
                external_problem_id="42576",
                title="Unknown",
                description="Find the missing person.",
                constraints="",
                examples="",
                difficulty="Medium",
                programming_language="Python",
                student_code="def solution(participant, completion):\n    return None",
                execution_result="",
                hint_level=1,
            ),
            ProblemContext(
                source_platform="LeetCode",
                source_url="https://leetcode.com/problems/two-sum/",
                external_problem_id="1",
                title="Two Sum",
                description="Return indices.",
                constraints="",
                examples="",
                difficulty="Easy",
                programming_language="Python",
                student_code="",
                execution_result="",
                hint_level=1,
            ),
            ProblemContext(
                source_platform="Baekjoon",
                source_url="https://www.acmicpc.net/problem/1000",
                external_problem_id="1000",
                title="A+B",
                description="Read two integers and print their sum.",
                constraints="",
                examples="",
                difficulty="Easy",
                programming_language="Python",
                student_code="",
                execution_result="",
                hint_level=1,
            ),
        ]

        for context in contexts:
            result = service.generate_hint(context, hint_level=1)
            assert result["hint"]
            assert result["source_platform"] == context.source_platform


def test_missing_optional_fields_are_handled(temp_db):
    with get_session(temp_db) as session:
        service = HintService(session, openai_client=FakeOpenAIClient("A useful hint."))
        context = ProblemContext(
            source_platform="Manual",
            source_url="",
            external_problem_id=None,
            title="Manual problem",
            description="Solve the task.",
            constraints="",
            examples="",
            difficulty="",
            programming_language="Python",
            student_code="",
            execution_result="",
            hint_level=1,
        )

        result = service.generate_hint(context, hint_level=1)
        assert "hint" in result
        assert result["hint"]


def test_api_failure_falls_back_to_local_hint(temp_db):
    with get_session(temp_db) as session:
        service = HintService(session, openai_client=FailingOpenAIClient(RuntimeError("boom")))
        context = ProblemContext(
            source_platform="Manual",
            source_url="",
            external_problem_id=None,
            title="Fallback",
            description="Explain the approach.",
            constraints="",
            examples="",
            difficulty="Easy",
            programming_language="Python",
            student_code="",
            execution_result="",
            hint_level=3,
        )

        result = service.generate_hint(context, hint_level=3)
        assert result["hint"]
        assert "fallback" in result["hint"].lower() or "hint" in result["hint"].lower()


def test_english_only_response_behavior(temp_db):
    with get_session(temp_db) as session:
        service = HintService(session, openai_client=FakeOpenAIClient("이 문제는 해시 맵을 사용합니다."))
        context = ProblemContext(
            source_platform="Manual",
            source_url="",
            external_problem_id=None,
            title="English only",
            description="Write a hint.",
            constraints="",
            examples="",
            difficulty="Easy",
            programming_language="Python",
            student_code="",
            execution_result="",
            hint_level=1,
        )

        result = service.generate_hint(context, hint_level=1)
        assert result["hint"]
        assert all(char not in result["hint"] for char in "가아나더러미바사수아에이오우으")


def test_full_solution_leakage_prevention(temp_db):
    with get_session(temp_db) as session:
        service = HintService(session, openai_client=FakeOpenAIClient("def solution(nums, target):\n    return []"))
        context = ProblemContext(
            source_platform="Manual",
            source_url="",
            external_problem_id=None,
            title="Leak prevention",
            description="Avoid giving a full solution.",
            constraints="",
            examples="",
            difficulty="Easy",
            programming_language="Python",
            student_code="",
            execution_result="",
            hint_level=4,
        )

        result = service.generate_hint(context, hint_level=4)
        assert result["hint"]
        assert "def solution" not in result["hint"]
        assert "copy-paste" not in result["hint"].lower()

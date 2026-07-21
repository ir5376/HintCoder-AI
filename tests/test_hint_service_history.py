import os
import tempfile

from src.database import get_session, init_db
from src.models.hint import HintHistory
from src.models.problem import Problem
from src.services.hint_service import HintService


class DummyGeminiClient:
    class _Models:
        def generate_content(self, **kwargs):
            return type("Response", (), {"text": "A helpful hint."})()

    def __init__(self):
        self.models = self._Models()


def test_store_hint_history_uses_existing_model_fields():
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

            service = HintService(session, openai_client=DummyGeminiClient())
            context = service.build_problem_context(
                problem,
                student_code="def two_sum(nums, target):\n    return []",
                programming_language="Python",
                hint_level=1,
            )

            result = service.generate_hint(context, hint_level=1)

            history = session.query(HintHistory).all()

        assert len(history) == 1
        assert history[0].hint_level == 1
        assert history[0].hint_text
        assert result["hint"] == "A helpful hint."


def test_hint_generation_returns_hint_when_history_persistence_fails(monkeypatch):
    class FailingSession:
        def add(self, _record):
            raise RuntimeError("history persistence failed")

    service = HintService(FailingSession(), openai_client=DummyGeminiClient())

    result = service.generate_hint(
        context=type(
            "Context",
            (),
            {
                "source_platform": "HintCode",
                "source_url": "",
                "external_problem_id": None,
                "title": "Imported PDF question",
                "description": "Which number is even?",
                "constraints": "",
                "examples": "",
                "difficulty": "Unknown",
                "programming_language": "Python",
                "student_code": "",
                "execution_result": "",
                "hint_level": 1,
                "problem_id": "learning_item:3",
                "learner_context": "",
                "subject_profile": "",
                "previous_hints": (),
            },
        )(),
        hint_level=1,
    )

    assert result["hint"] == "A helpful hint."
    assert result["problem_id"] == "learning_item:3"

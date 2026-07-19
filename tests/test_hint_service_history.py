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

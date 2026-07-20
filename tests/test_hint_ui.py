import src.ui.problem_detail_page as problem_detail_page
from src.learning_engine.domain import LearningContext
from src.services.hint_service import HintService
from src.ui.problem_detail_page import build_hint_context


def test_build_hint_context_uses_problem_details_and_user_inputs():
    problem = {
        "id": 7,
        "title": "Sum of two numbers",
        "description": "Return the sum of two numbers.",
        "constraints": "Use integers.",
        "test_cases": [{"input": [1, 2], "output": 3}],
        "difficulty": "Easy",
        "starter_code": "def solution(a, b):\n    pass",
        "source_reference": "https://example.com",
    }

    context = build_hint_context(
        problem,
        student_code="def solution(a, b):\n    return a + b",
        programming_language="Python",
        hint_level=3,
        learning_context=LearningContext(
            current_approach="Use direct addition.",
            current_obstacle="Not sure about input type.",
            intended_algorithm="Arithmetic",
            desired_hint_level=3,
            confidence_level=0.7,
        ),
    )

    assert context.title == "Sum of two numbers"
    assert context.programming_language == "Python"
    assert context.hint_level == 3
    assert context.student_code.startswith("def solution")
    assert context.source_url == "https://example.com"
    assert context.learning_context is not None
    assert context.learning_context.current_approach == "Use direct addition."


def test_problem_detail_page_uses_st_ace_when_available(monkeypatch):
    captured = {}

    def fake_st_ace(*args, **kwargs):
        captured.update(kwargs)
        return "print('hi')"

    monkeypatch.setattr(problem_detail_page, "st_ace", fake_st_ace, raising=False)
    monkeypatch.setattr(problem_detail_page, "st", type("FakeSt", (), {"text_area": lambda *args, **kwargs: ""})())

    result = problem_detail_page._render_code_editor("Your code", "", "editor_key", language="python")

    assert result == "print('hi')"
    assert captured["language"] == "python"


def test_hint_prompt_includes_provider_independent_learning_context():
    service = HintService(session=object())
    context = problem_detail_page.ProblemContext(
        source_platform="AnyProvider",
        title="Sample",
        description="Solve it.",
        student_code="print('work')",
        hint_level=2,
        learning_context=LearningContext(
            current_approach="I want to use BFS.",
            current_obstacle="I do not know when to mark visited.",
            intended_algorithm="BFS",
            desired_hint_level=2,
            confidence_level=0.4,
        ),
    )

    prompt = service._build_prompt(context, hint_level=2)

    assert "Learning context:" in prompt
    assert "- Current approach: I want to use BFS." in prompt
    assert "- Current obstacle: I do not know when to mark visited." in prompt
    assert "- Intended algorithm: BFS" in prompt
    assert "- Desired hint level: 2" in prompt
    assert "- Confidence level: 0.4" in prompt

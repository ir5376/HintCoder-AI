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
    )

    assert context.title == "Sum of two numbers"
    assert context.programming_language == "Python"
    assert context.hint_level == 3
    assert context.student_code.startswith("def solution")
    assert context.source_url == "https://example.com"

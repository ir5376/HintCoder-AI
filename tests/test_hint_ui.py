import src.ui.problem_detail_page as problem_detail_page
from src.ui.problem_detail_page import build_hint_context
from src.ui.problem_detail_page import _is_safe_external_url


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


def test_is_safe_external_url_accepts_only_http_urls():
    assert _is_safe_external_url("https://school.programmers.co.kr/learn/courses/30/lessons/43165")
    assert _is_safe_external_url("http://example.com/problem")
    assert not _is_safe_external_url("javascript:alert(1)")
    assert not _is_safe_external_url("file:///C:/secret.txt")
    assert not _is_safe_external_url("school.programmers.co.kr/learn/courses/30/lessons/43165")

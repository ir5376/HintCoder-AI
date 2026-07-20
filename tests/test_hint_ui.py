import src.ui.problem_detail_page as problem_detail_page
from src.ui.problem_detail_page import build_hint_context
from src.ui.problem_detail_page import _is_safe_external_url
from src.ui.problem_detail_page import _build_external_problem_context
from src.ui.problem_detail_page import _external_session_payload
from src.ui.problem_detail_page import _reset_external_problem_state


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


def test_external_session_payload_saves_required_fields():
    payload = _external_session_payload("Two Sum", "https://example.com/two-sum", 2)

    assert payload == {
        "problem_title": "Two Sum",
        "problem_url": "https://example.com/two-sum",
        "hint_level_used": 2,
    }


def test_build_external_problem_context_uses_external_problem_details():
    context = _build_external_problem_context(
        problem_title="Two Sum",
        problem_url="https://example.com/two-sum",
        student_code="def two_sum(nums, target):\n    pass",
        hint_level=3,
    )

    assert context.source_platform == "External"
    assert context.source_url == "https://example.com/two-sum"
    assert context.external_problem_id == "https://example.com/two-sum"
    assert context.title == "Two Sum"
    assert context.problem_id is None
    assert context.hint_level == 3
    assert context.student_code.startswith("def two_sum")


def test_reset_external_problem_state_initializes_session(monkeypatch):
    fake_session_state = {}
    fake_st = type("FakeSt", (), {"session_state": fake_session_state})()

    monkeypatch.setattr(problem_detail_page, "st", fake_st)

    _reset_external_problem_state("Two Sum", "https://example.com/two-sum")

    assert fake_session_state["external_hint_level_used"] == 0
    assert fake_session_state["external_hint_history"] == []
    assert fake_session_state["external_code_editor"] == ""
    assert fake_session_state["external_problem_session"] == {
        "problem_title": "Two Sum",
        "problem_url": "https://example.com/two-sum",
        "hint_level_used": 0,
    }


def test_reset_external_problem_state_preserves_existing_same_problem(monkeypatch):
    fake_session_state = {
        "external_problem_key": "Two Sum\nhttps://example.com/two-sum",
        "external_hint_level_used": 2,
        "external_hint_history": [{"hint_level": 1}],
        "external_code_editor": "print('keep')",
    }
    fake_st = type("FakeSt", (), {"session_state": fake_session_state})()

    monkeypatch.setattr(problem_detail_page, "st", fake_st)

    _reset_external_problem_state("Two Sum", "https://example.com/two-sum")

    assert fake_session_state["external_hint_level_used"] == 2
    assert fake_session_state["external_hint_history"] == [{"hint_level": 1}]
    assert fake_session_state["external_code_editor"] == "print('keep')"

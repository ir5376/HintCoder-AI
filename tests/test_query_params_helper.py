from src.ui import query_params_helper


def test_get_problem_context_from_query_params_reads_title_and_url(monkeypatch):
    fake_st = type(
        "FakeSt",
        (),
        {
            "query_params": {
                "problem_title": "  Programmers Target Number  ",
                "problem_url": " https://school.programmers.co.kr/learn/courses/30/lessons/43165 ",
            }
        },
    )()

    monkeypatch.setattr(query_params_helper, "st", fake_st)

    context = query_params_helper.get_problem_context_from_query_params()

    assert context["problem_title"] == "Programmers Target Number"
    assert context["problem_url"] == "https://school.programmers.co.kr/learn/courses/30/lessons/43165"
    assert context["language"] is None


def test_get_problem_context_from_query_params_handles_missing_values(monkeypatch):
    fake_st = type("FakeSt", (), {"query_params": {}})()

    monkeypatch.setattr(query_params_helper, "st", fake_st)

    context = query_params_helper.get_problem_context_from_query_params()

    assert context == {"problem_title": None, "problem_url": None, "language": None}


def test_get_problem_context_from_query_params_accepts_list_values(monkeypatch):
    fake_st = type(
        "FakeSt",
        (),
        {
            "query_params": {
                "problem_title": ["Two Sum"],
                "problem_url": ["https://example.com/two-sum"],
                "language": ["Java"],
            }
        },
    )()

    monkeypatch.setattr(query_params_helper, "st", fake_st)

    context = query_params_helper.get_problem_context_from_query_params()

    assert context["problem_title"] == "Two Sum"
    assert context["problem_url"] == "https://example.com/two-sum"
    assert context["language"] == "Java"


def test_get_problem_context_from_query_params_preserves_korean_title(monkeypatch):
    fake_st = type(
        "FakeSt",
        (),
        {
            "query_params": {
                "problem_title": "타겟 넘버",
                "problem_url": "https://school.programmers.co.kr/learn/courses/30/lessons/43165",
            }
        },
    )()

    monkeypatch.setattr(query_params_helper, "st", fake_st)

    context = query_params_helper.get_problem_context_from_query_params()

    assert context["problem_title"] == "타겟 넘버"
    assert context["language"] is None

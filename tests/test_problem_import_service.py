import pytest

from src.services.problem_import_service import ProblemImportService


def test_problem_import_accepts_only_provider_independent_fields():
    imported = ProblemImportService().import_problem(
        {
            "provider": "leetcode",
            "problem_id": "two-sum",
            "title": "Two Sum",
            "url": "https://leetcode.com/problems/two-sum/",
            "language": "python3",
        }
    )

    assert imported.provider == "leetcode"
    assert imported.problem_id == "two-sum"
    assert imported.title == "Two Sum"
    assert imported.url == "https://leetcode.com/problems/two-sum/"
    assert imported.language == "Python"


def test_problem_import_works_for_programmers_without_engine_provider_logic():
    imported = ProblemImportService().import_problem(
        {
            "provider": "programmers",
            "problem_id": "43165",
            "title": "Target Number",
            "url": "https://school.programmers.co.kr/learn/courses/30/lessons/43165",
            "language": "JavaScript",
        }
    )

    assert imported.provider == "programmers"
    assert imported.problem_id == "43165"
    assert imported.language == "JavaScript"


def test_problem_import_detects_leetcode_url():
    imported = ProblemImportService().import_problem_from_url(
        "https://leetcode.com/problems/two-sum/",
        {"language": "python3"},
    )

    assert imported.provider == "leetcode"
    assert imported.problem_id == "two-sum"
    assert imported.title == "Two Sum"
    assert imported.difficulty == "Unknown"
    assert imported.language == "Python"


def test_problem_import_detects_programmers_url():
    imported = ProblemImportService().import_problem_from_url(
        "https://school.programmers.co.kr/learn/courses/30/lessons/43165",
        {"title": "Target Number", "language": "JavaScript"},
    )

    assert imported.provider == "programmers"
    assert imported.problem_id == "43165"
    assert imported.title == "Target Number"


def test_problem_import_supports_custom_provider_url_with_hint():
    imported = ProblemImportService().import_problem_from_url(
        "https://example.edu/problems/custom-1",
        {"title": "Custom Practice", "language": "Python"},
        provider_hint="custom",
    )

    assert imported.provider == "custom"
    assert imported.problem_id == "custom-1"
    assert imported.title == "Custom Practice"


def test_problem_import_normalizes_internal_problem_shape():
    service = ProblemImportService()
    provider_payload = service.import_problem_from_url(
        "https://leetcode.com/problems/two-sum/",
        {"language": "Python"},
    )

    internal_problem = service.normalize_internal_problem(provider_payload)

    assert internal_problem.title == "Two Sum"
    assert internal_problem.provider == "leetcode"
    assert internal_problem.provider_problem_id == "two-sum"
    assert internal_problem.provider_url == "https://leetcode.com/problems/two-sum/"
    assert internal_problem.difficulty == "Unknown"
    assert "Python" in internal_problem.language_support


def test_problem_import_rejects_unnecessary_scraped_fields():
    with pytest.raises(ValueError, match="Unsupported import field"):
        ProblemImportService().import_problem(
            {
                "provider": "leetcode",
                "problem_id": "two-sum",
                "title": "Two Sum",
                "url": "https://leetcode.com/problems/two-sum/",
                "language": "Python",
                "problem_statement": "Do not duplicate external content.",
            }
        )

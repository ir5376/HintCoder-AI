import os
import tempfile

from src.database import get_session, init_db
from src.models.learning_os import (
    Assessment,
    LearningAttempt,
    LearningHistoryEvent,
    LearningItem,
    LearningReflection,
    ProviderRecord,
    ReviewQueueItem,
    WeaknessAnalysis,
)
from src.provider_adapters.registry import ProviderRegistry
from src.services.learning_os_service import LearningOSService


def test_provider_registry_exposes_supported_coding_providers():
    providers = ProviderRegistry().list_providers()
    provider_ids = {provider.id for provider in providers}

    assert provider_ids == {"leetcode", "programmers", "baekjoon", "codeforces", "atcoder", "custom"}
    assert all("problem_import" in provider.capabilities for provider in providers)
    assert all(provider.display_name for provider in providers)
    assert all(provider.icon for provider in providers)
    assert all(provider.supported_languages for provider in providers)


def test_provider_adapters_expose_future_sync_interfaces():
    adapter = ProviderRegistry().get("leetcode")

    assert adapter.sync_recent() == []
    assert adapter.sync_favorites() == []
    assert adapter.sync_history() == []


def test_learning_os_pipeline_is_provider_independent():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        adapter = ProviderRegistry().get("programmers")
        provider_payload = adapter.import_problem(
            {
                "problem_id": "43165",
                "title": "Target Number",
                "url": "https://school.programmers.co.kr/learn/courses/30/lessons/43165",
                "starter_code": "def solution(numbers, target):\n    pass",
                "metadata": {"description": "Count ways to make target."},
            }
        )
        assessment_payload = adapter.sync_submission(
            {
                "status": "accepted",
                "execution_trace": {"status": "completed", "steps": [{"line_no": 1}]},
                "tests": {"passed": 14, "total": 14},
            }
        )

        with get_session(database_url) as session:
            result = LearningOSService(session).complete_learning_loop(
                provider_payload,
                assessment_payload,
                answer="def solution(numbers, target):\n    return 0",
                language=adapter.map_language("python3"),
                confidence=0.7,
            )

            assert session.query(ProviderRecord).count() == 1
            assert session.query(LearningItem).count() == 1
            assert session.query(LearningAttempt).count() == 1
            assert session.query(Assessment).count() == 1
            assert session.query(LearningReflection).count() == 1
            assert session.query(ReviewQueueItem).count() == 4
            assert session.query(LearningHistoryEvent).count() == 4
            assert session.query(WeaknessAnalysis).count() == 1

        assert len(result.review_ids) == 4

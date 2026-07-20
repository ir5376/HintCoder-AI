import os
import tempfile
from datetime import date, timedelta

from src.database import get_session, init_db
from src.models.learning_item import LearningArtifact, LearningItem, LearningReviewQueue, XpEvent
from src.services.hint_service import HintService, ProblemContext
from src.services.learning_source_parser import ExamSourceParser
from src.services.learning_source_service import LearningSourceService
from src.services.user_progress_service import UserProgressService


QUESTION_TEXT = """Sample Exam 2025
Subject: Networks
1. What does DNS resolve?
A. Names to IP addresses
B. Ports to sockets
C. Files to blocks
D. Keys to locks
2. Which algorithm explores neighbors level by level?
A. DFS
B. BFS
C. Greedy
D. Hashing
"""

ANSWER_TEXT = """1. A - DNS maps domain names to IP addresses.
2. B - BFS explores level by level.
"""


def _database_url():
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir, f"sqlite:///{os.path.join(temp_dir.name, 'test.db')}"


def test_question_pdf_with_answer_pdf_imports_verified_answers():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            result = LearningSourceService(session).import_exam_source(
                question_pdf_name="questions.pdf",
                question_pdf=QUESTION_TEXT,
                answer_pdf_name="answers.pdf",
                answer_pdf=ANSWER_TEXT,
                owner_user_id="u1",
            )
            items = session.query(LearningItem).filter(LearningItem.owner_user_id == "u1").all()

        assert result["import_report"]["questions_detected"] == 2
        assert result["import_report"]["answers_matched"] == 2
        assert {item.answer_status for item in items} == {"verified"}
        assert {item.verified_answer for item in items} == {"A", "B"}


def test_question_pdf_without_answer_pdf_keeps_answers_unavailable():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            result = LearningSourceService(session).import_exam_source(
                question_pdf_name="questions.pdf",
                question_pdf=QUESTION_TEXT,
                owner_user_id="u1",
            )
            items = session.query(LearningItem).filter(LearningItem.owner_user_id == "u1").all()

        assert result["import_report"]["answers_detected"] == 0
        assert {item.answer_status for item in items} == {"unavailable"}
        assert all(not item.verified_answer for item in items)


def test_incorrect_answer_numbers_are_reported_as_unmatched():
    preview = ExamSourceParser().preview(
        question_pdf_name="questions.pdf",
        question_pdf=QUESTION_TEXT,
        answer_pdf_name="answers.pdf",
        answer_pdf="3. C - unmatched",
    )

    assert preview.report["answers_detected"] == 1
    assert preview.report["answers_matched"] == 0
    assert preview.report["unmatched_answers"] == ["3"]


def test_verified_answer_is_not_overwritten_by_inferred_answer():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = LearningSourceService(session)
            service.import_exam_source(
                question_pdf_name="questions.pdf",
                question_pdf=QUESTION_TEXT,
                answer_pdf_name="answers.pdf",
                answer_pdf="1. A - official",
                owner_user_id="u1",
            )
            item = session.query(LearningItem).filter(LearningItem.question_number == "1").one()
            item.inferred_answer = "B"
            item.answer_status = "verified"
            session.commit()

            stored = session.query(LearningItem).filter(LearningItem.question_number == "1").one()

        assert stored.verified_answer == "A"
        assert stored.inferred_answer == "B"
        assert stored.answer_status == "verified"


def test_learner_context_is_passed_to_hint_prompt():
    class CaptureClient:
        class Models:
            def __init__(self):
                self.prompt = ""

            def generate_content(self, **kwargs):
                self.prompt = kwargs["contents"]
                return type("Response", (), {"text": "A helpful hint."})()

        def __init__(self):
            self.models = self.Models()

    client = CaptureClient()
    service = HintService(session=None, openai_client=client)
    service.generate_hint(
        ProblemContext(
            source_platform="HintCode",
            title="Two Sum",
            description="Find target pair.",
            learner_context="I only want to know whether my approach is correct.",
        )
    )

    assert "I only want to know whether my approach is correct." in client.models.prompt


def test_daily_attendance_deduplicates_same_user_and_date():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            progress = UserProgressService(session)
            progress.get_or_create_user("u1", "Ada")
            progress.record_activity(user_id="u1", event_type="attempt_submitted", activity_date=date(2026, 7, 20))
            progress.record_activity(user_id="u1", event_type="quiz_completed", activity_date=date(2026, 7, 20))
            session.commit()

            summary = progress.streak_summary("u1")
            xp_count = session.query(XpEvent).filter(XpEvent.user_id == "u1", XpEvent.event_type == "daily_attendance_bonus").count()

        assert summary.active_days == 1
        assert xp_count == 1


def test_streak_continuation_and_break():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            progress = UserProgressService(session)
            progress.get_or_create_user("u1", "Ada")
            progress.record_activity(user_id="u1", event_type="attempt_submitted", activity_date=date(2026, 7, 18))
            progress.record_activity(user_id="u1", event_type="attempt_submitted", activity_date=date(2026, 7, 19))
            progress.record_activity(user_id="u1", event_type="attempt_submitted", activity_date=date(2026, 7, 21))
            session.commit()
            summary = progress.streak_summary("u1")

        assert summary.longest_streak == 2
        assert summary.active_days == 3


def test_xp_idempotency():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            progress = UserProgressService(session)
            progress.get_or_create_user("u1", "Ada")
            progress.award_xp(user_id="u1", event_type="first_attempt", idempotency_key="attempt:1")
            progress.award_xp(user_id="u1", event_type="first_attempt", idempotency_key="attempt:1")

        with get_session(database_url) as session:
            assert UserProgressService(session).current_xp("u1") == 10


def test_two_users_and_weekly_leaderboard_ordering():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            progress = UserProgressService(session)
            progress.get_or_create_user("u1", "Ada")
            progress.get_or_create_user("u2", "Grace")
            progress.award_xp(user_id="u1", event_type="first_attempt", idempotency_key="u1:a")
            progress.award_xp(user_id="u2", event_type="learning_item_completed", idempotency_key="u2:c")
            leaderboard = progress.leaderboard()

        assert [row["user_id"] for row in leaderboard[:2]] == ["u2", "u1"]


def test_coding_url_and_pdf_use_same_learning_engine():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = LearningSourceService(session)
            coding = service.import_provider_url("https://leetcode.com/problems/two-sum/", owner_user_id="u1")
            pdf = service.import_exam_source(question_pdf_name="q.pdf", question_pdf=QUESTION_TEXT, owner_user_id="u1")

            coding_artifacts = session.query(LearningArtifact).filter(
                LearningArtifact.learning_item_id == coding["learning_item"]["id"]
            ).count()
            review_count = session.query(LearningReviewQueue).count()

        assert coding_artifacts > 0
        assert pdf["items"]
        assert review_count >= 8

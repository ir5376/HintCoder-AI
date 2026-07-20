import os
import tempfile
from datetime import date

import pytest

from src.database import get_session, init_db
from src.models.learning_item import AnswerRecord, LearningItem, LearningReviewQueue, XpEvent
from src.services.learning_source_parser import ExamSourceParser
from src.services.learning_source_service import LearningSourceService
from src.services.provider_adapters import LeetCodeAdapter, ProgrammersAdapter, get_provider_adapter
from src.services.provider_submission_service import ProviderSubmissionService
from src.services.subject_profiles import get_subject_profile
from src.services.user_progress_service import UserProgressService


QUESTION_TEXT = """Shared Passage Exam 2025
Subject: English
Passage A:
Read the paragraph and choose the best answer.
1. What is the main idea?
A. Growth
B. Weather
C. Syntax
D. Cooking
2. Which word is closest to improve?
A. decline
B. enhance
C. stop
D. erase
3. Standalone grammar question.
A. are
B. is
C. were
D. be
"""


ANSWER_TEXT = """1. A - The passage describes growth.
2. B - Improve is closest to enhance.
4. C - This answer has no question.
"""


def _database_url():
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir, f"sqlite:///{os.path.join(temp_dir.name, 'test.db')}"


def test_programmers_result_normalization():
    adapter = ProgrammersAdapter()

    assert adapter.normalize_submission_status("정답") == "accepted"
    assert adapter.normalize_submission_status("시간 초과") == "time_limit_exceeded"
    assert adapter.normalize_submission_status("컴파일 에러") == "compile_error"
    assert adapter.normalize_submission_status("unexpected") == "unknown"


def test_leetcode_result_normalization():
    adapter = LeetCodeAdapter()

    assert adapter.normalize_submission_status("Accepted") == "accepted"
    assert adapter.normalize_submission_status("Wrong Answer") == "wrong_answer"
    assert adapter.normalize_submission_status("Runtime Error") == "runtime_error"
    assert adapter.normalize_submission_status("Memory Limit Exceeded") == "memory_limit_exceeded"


def test_unknown_provider_result_is_rejected():
    with pytest.raises(ValueError):
        get_provider_adapter("unknown-provider")


def test_duplicate_accepted_event_awards_xp_once():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProviderSubmissionService(session)
            service.create_pending_attempt(
                user_id="u1",
                provider="leetcode",
                provider_problem_id="two-sum",
                source_code_hash="abc123",
            )
            payload = {
                "provider": "leetcode",
                "provider_problem_id": "two-sum",
                "problem_url": "https://leetcode.com/problems/two-sum/",
                "language": "Python3",
                "source_code_hash": "abc123",
                "raw_status": "Accepted",
                "submitted_at": "2026-07-20T10:00:00Z",
            }
            first = service.handle_submission_result(payload, user_id="u1")
            second = service.handle_submission_result({**payload, "submitted_at": "2026-07-20T10:05:00Z"}, user_id="u1")
            xp_events = session.query(XpEvent).filter(XpEvent.user_id == "u1", XpEvent.event_type == "learning_item_completed").count()

        assert first["normalized_status"] == "accepted"
        assert second["normalized_status"] == "accepted"
        assert xp_events == 1


def test_question_pdf_with_multiple_questions_and_shared_passage_preview():
    preview = ExamSourceParser().preview(
        question_pdf_name="questions.pdf",
        question_pdf=QUESTION_TEXT,
        answer_pdf_name="answers.pdf",
        answer_pdf=ANSWER_TEXT,
    )

    assert preview.report["questions_detected"] == 3
    assert preview.report["passages_detected"] == 1
    assert preview.questions[0].metadata["passage_group"] == "A"
    assert preview.questions[1].metadata["passage_group"] == "A"


def test_separate_answer_pdf_matching_and_unmatched_numbers_are_reported():
    preview = ExamSourceParser().preview(
        question_pdf_name="questions.pdf",
        question_pdf=QUESTION_TEXT,
        answer_pdf_name="answers.pdf",
        answer_pdf=ANSWER_TEXT,
    )

    assert preview.report["answers_detected"] == 3
    assert preview.report["answers_matched"] == 2
    assert preview.report["questions_without_answers"] == ["3"]
    assert preview.report["unmatched_answers"] == ["4"]


def test_confirm_import_persists_learning_items_and_answer_records():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            result = LearningSourceService(session).confirm_import(
                question_pdf_name="questions.pdf",
                question_pdf=QUESTION_TEXT,
                answer_pdf_name="answers.pdf",
                answer_pdf=ANSWER_TEXT,
                owner_user_id="u1",
            )
            item_count = session.query(LearningItem).filter(LearningItem.owner_user_id == "u1").count()
            answer_records = session.query(AnswerRecord).all()

        assert result["import_report"]["questions_detected"] == 3
        assert item_count == 3
        assert len(answer_records) == 3
        assert sum(1 for record in answer_records if record.matched_learning_item_id) == 2


def test_subject_profiles_and_generic_fallback():
    coding = get_subject_profile("Coding", "coding")
    english = get_subject_profile("English", "multiple_choice")
    generic = get_subject_profile("History", "multiple_choice")

    assert coding.id == "coding"
    assert "algorithm" in coding.memory_extraction_rules
    assert english.id == "english_multiple_choice"
    assert english.answer_format.startswith("choice")
    assert generic.id == "generic_exam"


def test_attendance_deduplication_and_streak_update():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            progress = UserProgressService(session)
            progress.get_or_create_user("u1", "Ada")
            progress.record_activity(user_id="u1", event_type="app_opened", activity_date=date(2026, 7, 19))
            progress.record_activity(user_id="u1", event_type="attempt_submitted", activity_date=date(2026, 7, 20))
            progress.record_activity(user_id="u1", event_type="review_completed", activity_date=date(2026, 7, 20))
            progress.record_activity(user_id="u1", event_type="quiz_completed", activity_date=date(2026, 7, 21))
            session.commit()
            summary = progress.streak_summary("u1")
            attendance_xp = session.query(XpEvent).filter(XpEvent.event_type == "daily_attendance_bonus").count()

        assert summary.active_days == 2
        assert summary.longest_streak == 2
        assert attendance_xp == 2


def test_two_user_weekly_leaderboard_review_xp_and_hint_usage():
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            progress = UserProgressService(session)
            progress.get_or_create_user("u1", "Ada")
            progress.get_or_create_user("u2", "Grace")
            item = LearningItem(
                owner_user_id="u1",
                source_type="notes",
                title="Review target",
                difficulty="Easy",
                question_type="short_answer",
            )
            session.add(item)
            session.flush()
            review = LearningReviewQueue(user_id="u1", learning_item_id=item.id, interval_days=1)
            session.add(review)
            session.flush()

            before_hint_xp = progress.current_xp("u1")
            progress.record_hint_usage(user_id="u1", learning_item_id=item.id, hint_level=2)
            assert progress.current_xp("u1") >= before_hint_xp

            review_result = progress.complete_review(user_id="u1", review_id=review.id)
            progress.award_xp(user_id="u2", event_type="learning_item_completed", idempotency_key="u2:accepted")
            leaderboard = progress.leaderboard(mode="weekly_xp")

        assert review_result["points"] == 15
        assert [row["user_id"] for row in leaderboard[:2]] == ["u2", "u1"]

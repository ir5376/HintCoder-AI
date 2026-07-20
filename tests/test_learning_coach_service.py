import os
import tempfile

from src.database import get_session, init_db
from src.database import get_engine
from src.models.learning import LearningEvent, ReviewSchedule
from src.services.learning_coach_service import LearningCoachService


def test_record_solved_problem_builds_memory_and_review_schedule():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = LearningCoachService(session)

            result = service.record_solved_problem(
                {
                    "problem_title": "Target Number",
                    "problem_url": "https://example.com/target-number",
                    "content_module": "coding",
                    "content_id": "target-number",
                    "topic": "DFS",
                    "difficulty": "Medium",
                    "language": "Python",
                    "algorithm_choice": "DFS",
                    "solving_time_seconds": 1200,
                    "confidence": 0.8,
                    "thinking_progress": 0.7,
                    "hint_level_used": 1,
                    "implementation_mistakes": ["delays marking visited"],
                    "conceptual_mistakes": ["unclear recursion state"],
                    "insights": ["Mark visited before recursion"],
                }
            )

            events = session.query(LearningEvent).all()
            reviews = session.query(ReviewSchedule).order_by(ReviewSchedule.interval_days).all()
            profile = service.get_profile()
            thought_profile = service.get_thought_profile()
            hint_analytics = service.get_hint_analytics()
            reflection_history = service.get_reflection_history()
            learning_scores = service.get_learning_scores()

        assert result["learning_event_id"] == events[0].id
        assert result["mode"] == "learning"
        assert result["content_module"] == "coding"
        assert result["reflection"]["why_did_you_need_the_hint"] == "You used one strategic hint to confirm the key idea."
        assert len(events) == 1
        assert events[0].content_id == "target-number"
        assert [review.interval_days for review in reviews] == [1, 3, 7, 30]
        assert {review.content_module for review in reviews} == {"coding"}
        assert profile["language_preference"] == "Python"
        assert profile["preferred_algorithm_choices"] == {"DFS": 1}
        assert profile["repeated_implementation_mistakes"] == {"delays marking visited": 1}
        assert thought_profile["hint_dependency"] == "balanced"
        assert hint_analytics["average_hint_level"] == 1.0
        assert reflection_history[0]["reflection"]["what_concept_was_missing"] == "unclear recursion state"
        assert learning_scores["learning_score"] >= 0


def test_adaptive_difficulty_increases_when_mastery_improves():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = LearningCoachService(session)
            for _ in range(4):
                service.record_solved_problem(
                    {
                        "topic": "Arrays",
                        "difficulty": "Easy",
                        "language": "Python",
                        "algorithm_choice": "Hash Map",
                        "confidence": 0.9,
                        "hints_used": 0,
                        "solved": True,
                    }
                )

            difficulty = service.get_adaptive_difficulty()

        assert difficulty["recommended_difficulty"] == "Medium"
        assert "improving" in difficulty["reason"]


def test_weekly_report_and_roadmap_have_expected_sections():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = LearningCoachService(session)
            service.record_solved_problem(
                {
                    "topic": "Dynamic Programming",
                    "difficulty": "Hard",
                    "language": "Python",
                    "algorithm_choice": "DP",
                    "confidence": 0.4,
                    "hints_used": 3,
                    "conceptual_mistakes": ["struggles defining DP states"],
                }
            )

            weekly = service.generate_weekly_reflection()
            roadmap = service.generate_roadmap("7-day")

        assert "weekly_summary" in weekly
        assert "weakest_topic" in weekly
        assert "suggested_roadmap" in weekly
        assert roadmap["type"] == "7-day"
        assert roadmap["content_module"] == "coding"
        assert len(roadmap["days"]) == 7


def test_exam_mode_does_not_affect_learning_statistics_or_reviews():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = LearningCoachService(session)
            service.record_solved_problem(
                {
                    "mode": "learning",
                    "topic": "Arrays",
                    "difficulty": "Easy",
                    "language": "Python",
                    "algorithm_choice": "Hash Map",
                    "confidence": 0.9,
                    "hints_used": 0,
                    "hint_level_used": 0,
                }
            )
            exam_result = service.record_solved_problem(
                {
                    "mode": "exam",
                    "topic": "Graphs",
                    "difficulty": "Hard",
                    "language": "Java",
                    "algorithm_choice": "BFS",
                    "confidence": 0.4,
                    "hints_used": 2,
                    "hint_level_used": 2,
                    "exam_timer_seconds": 1800,
                    "exam_hints_available": True,
                    "exam_hint_penalty_enabled": True,
                    "exam_hint_penalty_points": 10,
                }
            )

            profile = service.get_profile()
            hint_analytics = service.get_hint_analytics()
            exam_summary = service.get_exam_summary()
            reviews = session.query(ReviewSchedule).all()

        assert exam_result["mode"] == "exam"
        assert exam_result["exam_final_score"] == 80.0
        assert profile["language_preference"] == "Python"
        assert "BFS" not in profile["preferred_algorithm_choices"]
        assert hint_analytics["average_hint_level"] == 0.0
        assert exam_summary["attempts"] == 1
        assert len(reviews) == 4


def test_init_db_adds_learning_mode_columns_to_existing_learning_events_table():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        engine = get_engine(database_url)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE learning_events (
                    id INTEGER NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    problem_id INTEGER,
                    external_problem_title VARCHAR(255),
                    external_problem_url TEXT,
                    topic VARCHAR(100),
                    difficulty VARCHAR(50),
                    language VARCHAR(50),
                    algorithm_choice VARCHAR(100),
                    solving_time_seconds INTEGER,
                    confidence FLOAT,
                    hints_used INTEGER NOT NULL,
                    solved BOOLEAN NOT NULL,
                    implementation_mistakes TEXT NOT NULL,
                    conceptual_mistakes TEXT NOT NULL,
                    insights TEXT NOT NULL,
                    reasoning_notes TEXT,
                    created_at DATETIME NOT NULL,
                    PRIMARY KEY (id)
                )
                """
            )
        engine.dispose()

        init_db(database_url)

        engine = get_engine(database_url)
        with engine.connect() as connection:
            columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(learning_events)").fetchall()}
        engine.dispose()

        assert "mode" in columns
        assert "content_module" in columns
        assert "content_id" in columns
        assert "hint_level_used" in columns
        assert "reflection_json" in columns
        assert "exam_final_score" in columns
        assert "execution_trace_json" in columns
        assert "provider" in columns
        assert "provider_submission_id" in columns

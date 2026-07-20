from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.services.learning_coach_service import LearningCoachService


class LearningEngine:
    """Universal learning layer shared by every present and future content module."""

    def __init__(self, session: Session) -> None:
        self.coach_service = LearningCoachService(session)

    def record_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.coach_service.record_solved_problem(payload)

    def dashboard(self) -> dict[str, Any]:
        dashboard = self.coach_service.get_dashboard()
        dashboard["xp"] = self.xp()
        dashboard["attendance"] = self.attendance()
        dashboard["missions"] = self.missions()
        dashboard["gamification"] = self.gamification()
        return dashboard

    def xp(self) -> dict[str, Any]:
        scores = self.coach_service.get_learning_scores()
        return {
            "current_xp": scores["learning_score"],
            "policy": "Learning Mode never subtracts XP for hint usage.",
        }

    def attendance(self) -> dict[str, Any]:
        weekly = self.coach_service.generate_weekly_reflection()
        return {"longest_streak": weekly["longest_streak"]}

    def missions(self) -> list[dict[str, str]]:
        focus_items = self.coach_service.generate_adaptive_coach_report()["tomorrow_focus"]
        return [{"title": item, "type": "learning_focus"} for item in focus_items]

    def gamification(self) -> dict[str, Any]:
        scores = self.coach_service.get_learning_scores()
        return {
            "learning_score": scores["learning_score"],
            "independence_score": scores["independence_score"],
            "review_readiness": scores["review_readiness"],
        }

    def review(self, status: str | None = "pending") -> list[dict[str, Any]]:
        return self.coach_service.get_review_queue(status=status)

    def reflection(self) -> dict[str, Any]:
        return self.coach_service.generate_adaptive_coach_report()

    def roadmap(self, roadmap_type: str = "7-day", content_module: str = "coding") -> dict[str, Any]:
        return self.coach_service.generate_roadmap(roadmap_type, content_module=content_module)

    def exam(self) -> dict[str, Any]:
        return self.coach_service.get_exam_summary()

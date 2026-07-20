from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.learning_item import LearningActivity, LearningReviewQueue, UserProfile, XpEvent
from src.repositories.learning_item_repository import LearningItemRepository


MEANINGFUL_ACTIVITY_EVENTS = {
    "attempt_submitted",
    "meaningful_hint_requested",
    "quiz_completed",
    "reflection_submitted",
    "review_completed",
}

XP_RULES = {
    "first_attempt": 10,
    "learning_item_completed": 30,
    "reflection_submitted": 10,
    "review_completed": 15,
    "quiz_completed": 10,
    "daily_attendance_bonus": 5,
}


@dataclass(frozen=True)
class StreakSummary:
    user_id: str
    activity_date: date | None
    current_streak: int
    longest_streak: int
    active_days: int
    last_active_date: date | None


class UserProgressService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = LearningItemRepository(session)

    def get_or_create_user(self, user_id: str = "local", display_name: str = "Local Learner") -> dict[str, Any]:
        return self.repository.get_or_create_user(user_id, display_name).to_dict()

    def record_activity(
        self,
        *,
        user_id: str,
        event_type: str,
        learning_item_id: int | None = None,
        activity_date: date | None = None,
    ) -> StreakSummary:
        if event_type not in MEANINGFUL_ACTIVITY_EVENTS:
            return self.streak_summary(user_id)
        day = activity_date or _today()
        existing = (
            self.session.query(LearningActivity)
            .filter(LearningActivity.user_id == user_id, LearningActivity.activity_date == day)
            .one_or_none()
        )
        if existing is None:
            self.session.add(
                LearningActivity(
                    user_id=user_id,
                    activity_date=day,
                    event_type=event_type,
                    learning_item_id=learning_item_id,
                )
            )
            self.repository.add_xp_event(
                user_id=user_id,
                event_type="daily_attendance_bonus",
                points=XP_RULES["daily_attendance_bonus"],
                learning_item_id=learning_item_id,
                idempotency_key=f"attendance:{day.isoformat()}",
            )
            self.session.flush()
        return self.streak_summary(user_id)

    def award_xp(
        self,
        *,
        user_id: str,
        event_type: str,
        learning_item_id: int | None = None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        points = XP_RULES.get(event_type, 0)
        event = self.repository.add_xp_event(
            user_id=user_id,
            event_type=event_type,
            points=points,
            learning_item_id=learning_item_id,
            idempotency_key=idempotency_key,
        )
        self.session.commit()
        return {"xp_event_id": event.id, "points": event.points, "current_xp": self.current_xp(user_id)}

    def record_accepted_completion(
        self,
        *,
        user_id: str,
        learning_item_id: int | None,
        provider: str,
        provider_problem_id: str,
        source_code_hash: str = "",
    ) -> dict[str, Any]:
        self.record_activity(user_id=user_id, event_type="attempt_submitted", learning_item_id=learning_item_id)
        event = self.repository.add_xp_event(
            user_id=user_id,
            event_type="learning_item_completed",
            points=XP_RULES["learning_item_completed"],
            learning_item_id=learning_item_id,
            idempotency_key=f"accepted:{provider}:{provider_problem_id}",
        )
        return {"xp_event_id": event.id, "points": event.points, "current_xp": self.current_xp(user_id)}

    def complete_review(self, *, user_id: str, review_id: int) -> dict[str, Any]:
        review = (
            self.session.query(LearningReviewQueue)
            .filter(LearningReviewQueue.id == review_id, LearningReviewQueue.user_id == user_id)
            .one_or_none()
        )
        if review is None:
            raise ValueError("Review not found")
        if review.status != "completed":
            review.status = "completed"
            review.completed_at = datetime.utcnow()
            self.record_activity(user_id=user_id, event_type="review_completed", learning_item_id=review.learning_item_id)
        event = self.repository.add_xp_event(
            user_id=user_id,
            event_type="review_completed",
            points=XP_RULES["review_completed"],
            learning_item_id=review.learning_item_id,
            idempotency_key=f"review_completed:{review.id}",
        )
        self.session.commit()
        return {"review_id": review.id, "xp_event_id": event.id, "points": event.points, "current_xp": self.current_xp(user_id)}

    def record_hint_usage(self, *, user_id: str, learning_item_id: int | None = None, hint_level: int = 1) -> dict[str, Any]:
        self.record_activity(user_id=user_id, event_type="meaningful_hint_requested", learning_item_id=learning_item_id)
        self.session.flush()
        return {"hint_level": hint_level, "xp_delta": 0, "current_xp": self.current_xp(user_id)}

    def current_xp(self, user_id: str) -> int:
        return int(self.session.query(func.coalesce(func.sum(XpEvent.points), 0)).filter(XpEvent.user_id == user_id).scalar() or 0)

    def streak_summary(self, user_id: str) -> StreakSummary:
        days = [
            row[0]
            for row in self.session.query(LearningActivity.activity_date)
            .filter(LearningActivity.user_id == user_id)
            .distinct()
            .order_by(LearningActivity.activity_date)
            .all()
        ]
        if not days:
            return StreakSummary(user_id, None, 0, 0, 0, None)
        longest = current_run = 1
        for previous, current in zip(days, days[1:]):
            if current == previous + timedelta(days=1):
                current_run += 1
            else:
                current_run = 1
            longest = max(longest, current_run)
        today = _today()
        current_streak = 0
        cursor = today if today in days else days[-1]
        day_set = set(days)
        while cursor in day_set:
            current_streak += 1
            cursor -= timedelta(days=1)
        return StreakSummary(user_id, days[-1], current_streak, longest, len(days), days[-1])

    def leaderboard(self, *, mode: str = "weekly_xp") -> list[dict[str, Any]]:
        if mode == "current_streak":
            users = self.session.query(UserProfile).all()
            rows = [(user, self.streak_summary(user.user_id).current_streak, datetime.utcnow()) for user in users]
        elif mode == "reviews_completed":
            rows = self._review_rows()
        else:
            rows = self._xp_rows(weekly=(mode != "all_time_xp"))

        ranked = []
        for rank, (user, score, achieved_at) in enumerate(rows, start=1):
            ranked.append(
                {
                    "rank": rank,
                    "user_id": user.user_id,
                    "display_name": user.display_name,
                    "score": int(score or 0),
                    "current_streak": self.streak_summary(user.user_id).current_streak,
                }
            )
        return ranked

    def _xp_rows(self, *, weekly: bool) -> list[tuple[UserProfile, int, datetime]]:
        query = self.session.query(UserProfile, func.coalesce(func.sum(XpEvent.points), 0), func.min(XpEvent.created_at)).outerjoin(
            XpEvent, XpEvent.user_id == UserProfile.user_id
        )
        if weekly:
            query = query.filter((XpEvent.created_at.is_(None)) | (XpEvent.created_at >= datetime.utcnow() - timedelta(days=7)))
        rows = query.group_by(UserProfile.user_id).all()
        return sorted(rows, key=lambda row: (-int(row[1] or 0), -self._completed_reviews(row[0].user_id), row[2] or datetime.max))

    def _review_rows(self) -> list[tuple[UserProfile, int, datetime]]:
        rows = (
            self.session.query(UserProfile, func.count(LearningReviewQueue.id), func.min(LearningReviewQueue.completed_at))
            .outerjoin(LearningReviewQueue, LearningReviewQueue.user_id == UserProfile.user_id)
            .filter((LearningReviewQueue.status == "completed") | (LearningReviewQueue.status.is_(None)))
            .group_by(UserProfile.user_id)
            .all()
        )
        return sorted(rows, key=lambda row: (-int(row[1] or 0), row[2] or datetime.max))

    def _completed_reviews(self, user_id: str) -> int:
        return int(
            self.session.query(func.count(LearningReviewQueue.id))
            .filter(LearningReviewQueue.user_id == user_id, LearningReviewQueue.status == "completed")
            .scalar()
            or 0
        )


def _today() -> date:
    configured = os.environ.get("HINTCODE_TIMEZONE", "UTC")
    if configured.upper() == "UTC":
        return datetime.now(timezone.utc).date()
    return datetime.utcnow().date()

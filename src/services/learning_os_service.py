from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.learning_engine.domain import AssessmentPayload, LearningLoopResult, ProviderProblemPayload
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


class LearningOSService:
    review_intervals_days = (1, 3, 7, 30)

    def __init__(self, session: Session) -> None:
        self.session = session

    def import_learning_item(self, provider_payload: ProviderProblemPayload, *, item_type: str = "coding_problem") -> LearningItem:
        provider_record = ProviderRecord(
            provider_id=provider_payload.provider_id,
            problem_id=provider_payload.problem_id,
            title=provider_payload.title,
            url=provider_payload.url,
            metadata_json=self._json(provider_payload.metadata),
            starter_code=provider_payload.starter_code,
        )
        self.session.add(provider_record)
        self.session.flush()

        learning_item = LearningItem(
            provider_record_id=provider_record.id,
            item_type=item_type,
            title=provider_payload.title,
            content=provider_payload.metadata.get("description", ""),
            source_url=provider_payload.url,
            metadata_json=self._json(provider_payload.metadata),
            starter_code=provider_payload.starter_code,
        )
        self.session.add(learning_item)
        self.session.flush()
        self._history(learning_item.id, "learning_item_imported", {"provider_id": provider_payload.provider_id})
        return learning_item

    def record_attempt(
        self,
        learning_item: LearningItem,
        *,
        answer: str = "",
        language: str = "Python",
        confidence: float | None = None,
        elapsed_seconds: int | None = None,
        mode: str = "learning",
        metadata: dict[str, Any] | None = None,
    ) -> LearningAttempt:
        attempt = LearningAttempt(
            learning_item_id=learning_item.id,
            mode=mode,
            language=language,
            answer=answer,
            confidence=confidence,
            elapsed_seconds=elapsed_seconds,
            metadata_json=self._json(metadata or {}),
        )
        self.session.add(attempt)
        self.session.flush()
        self._history(learning_item.id, "attempt_recorded", {"attempt_id": attempt.id, "mode": mode})
        return attempt

    def record_assessment(self, attempt: LearningAttempt, assessment_payload: AssessmentPayload) -> Assessment:
        assessment = Assessment(
            attempt_id=attempt.id,
            assessment_type=assessment_payload.assessment_type,
            status=assessment_payload.status,
            score=assessment_payload.score,
            execution_trace_json=self._json(assessment_payload.execution_trace),
            tests_json=self._json(assessment_payload.tests),
            metadata_json=self._json(assessment_payload.metadata),
        )
        self.session.add(assessment)
        self.session.flush()
        self._history(attempt.learning_item_id, "assessment_recorded", {"assessment_id": assessment.id, "status": assessment.status})
        return assessment

    def create_reflection(self, assessment: Assessment) -> LearningReflection:
        status = assessment.status.lower()
        why_it_worked = "The official assessment accepted the attempt." if status in {"accepted", "ac", "correct"} else ""
        struggled_with = self._infer_struggle(assessment)
        reflection = LearningReflection(
            assessment_id=assessment.id,
            why_it_worked=why_it_worked,
            struggled_with=struggled_with,
            remember_next_time="Review the assessment evidence and explain the first key decision before retrying.",
            metadata_json=self._json({"assessment_type": assessment.assessment_type}),
        )
        self.session.add(reflection)
        self.session.flush()
        return reflection

    def schedule_reviews(self, learning_item_id: int, assessment_id: int | None = None) -> list[ReviewQueueItem]:
        now = datetime.utcnow()
        reviews = []
        for interval in self.review_intervals_days:
            review = ReviewQueueItem(
                learning_item_id=learning_item_id,
                assessment_id=assessment_id,
                due_at=now + timedelta(days=interval),
                interval_days=interval,
                status="pending",
            )
            self.session.add(review)
            reviews.append(review)
        self.session.flush()
        self._history(learning_item_id, "review_queue_scheduled", {"intervals": list(self.review_intervals_days)})
        return reviews

    def analyze_weakness(self, learning_item_id: int, assessment: Assessment) -> WeaknessAnalysis:
        weakness_type = "execution_understanding" if assessment.execution_trace_json != "{}" else "assessment_gap"
        weakness = WeaknessAnalysis(
            learning_item_id=learning_item_id,
            topic=None,
            weakness_type=weakness_type,
            evidence_json=self._json(
                {
                    "assessment_status": assessment.status,
                    "assessment_type": assessment.assessment_type,
                    "has_execution_trace": assessment.execution_trace_json != "{}",
                }
            ),
        )
        self.session.add(weakness)
        self.session.flush()
        return weakness

    def complete_learning_loop(
        self,
        provider_payload: ProviderProblemPayload,
        assessment_payload: AssessmentPayload,
        *,
        answer: str = "",
        language: str = "Python",
        confidence: float | None = None,
        elapsed_seconds: int | None = None,
        mode: str = "learning",
    ) -> LearningLoopResult:
        learning_item = self.import_learning_item(provider_payload)
        attempt = self.record_attempt(
            learning_item,
            answer=answer,
            language=language,
            confidence=confidence,
            elapsed_seconds=elapsed_seconds,
            mode=mode,
        )
        assessment = self.record_assessment(attempt, assessment_payload)
        reflection = self.create_reflection(assessment)
        reviews = self.schedule_reviews(learning_item.id, assessment.id)
        self.analyze_weakness(learning_item.id, assessment)
        self.session.commit()
        return LearningLoopResult(
            learning_item_id=learning_item.id,
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            reflection_id=reflection.id,
            review_ids=[review.id for review in reviews],
            created_at=datetime.utcnow(),
        )

    def _history(self, learning_item_id: int, event_type: str, payload: dict[str, Any]) -> None:
        self.session.add(
            LearningHistoryEvent(
                learning_item_id=learning_item_id,
                event_type=event_type,
                payload_json=self._json(payload),
            )
        )

    def _infer_struggle(self, assessment: Assessment) -> str:
        if assessment.status.lower() in {"accepted", "ac", "correct"}:
            return "Confirm why the accepted approach worked, not only that it passed."
        if assessment.execution_trace_json != "{}":
            return "Use the execution trace to locate the first unexpected state."
        return "Compare the attempt against the assessment evidence before reviewing the solution."

    def _json(self, value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

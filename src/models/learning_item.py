from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "display_name": self.display_name, "created_at": self.created_at}


class LearningItem(Base):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    owner_user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="local")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=True)
    provider_problem_id: Mapped[str] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    exam_name: Mapped[str] = mapped_column(String(255), nullable=True)
    year: Mapped[str] = mapped_column(String(50), nullable=True)
    question_number: Mapped[str] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    choices_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verified_answer: Mapped[str] = mapped_column(Text, nullable=True)
    inferred_answer: Mapped[str] = mapped_column(Text, nullable=True)
    answer_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unavailable")
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    concepts_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, default="Unknown")
    original_reference: Mapped[str] = mapped_column(Text, nullable=True)
    question_type: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    learning_objective: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "item_type": self.item_type,
            "owner_user_id": self.owner_user_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "provider": self.provider,
            "provider_problem_id": self.provider_problem_id,
            "subject": self.subject,
            "exam_name": self.exam_name,
            "year": self.year,
            "question_number": self.question_number,
            "title": self.title,
            "content": self.content,
            "choices": loads(self.choices_json, []),
            "verified_answer": self.verified_answer,
            "inferred_answer": self.inferred_answer,
            "answer_status": self.answer_status,
            "answer": self.verified_answer or self.inferred_answer or "",
            "explanation": self.explanation,
            "concepts": loads(self.concepts_json, []),
            "difficulty": self.difficulty,
            "original_reference": self.original_reference,
            "original_url": self.original_reference,
            "question_type": self.question_type,
            "learning_objective": self.learning_objective,
            "metadata": loads(self.metadata_json, {}),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ExamSource(Base):
    __tablename__ = "exam_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="local")
    exam_title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    year: Mapped[str] = mapped_column(String(50), nullable=True)
    question_pdf_name: Mapped[str] = mapped_column(String(255), nullable=False)
    answer_pdf_name: Mapped[str] = mapped_column(String(255), nullable=True)
    answer_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unavailable")
    import_report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PassageGroup(Base):
    __tablename__ = "passage_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_source_id: Mapped[int] = mapped_column(ForeignKey("exam_sources.id"), nullable=False, index=True)
    group_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    passage_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class AnswerRecord(Base):
    __tablename__ = "answer_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_source_id: Mapped[int] = mapped_column(ForeignKey("exam_sources.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    question_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    verified_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_learning_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearningArtifact(Base):
    __tablename__ = "learning_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearningReviewQueue(Base):
    __tablename__ = "learning_review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="local")
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=False, index=True)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LearningItemAnswerSubmission(Base):
    __tablename__ = "learning_item_answer_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="local", index=True)
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=False, index=True)
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_selected_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    correct_answer: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unverified")
    is_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearningHistory(Base):
    __tablename__ = "learning_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="local")
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearningActivity(Base):
    __tablename__ = "learning_activities"
    __table_args__ = (UniqueConstraint("user_id", "activity_date", name="uq_learning_activity_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    learning_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class XpEvent(Base):
    __tablename__ = "xp_events"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_xp_user_idempotency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    learning_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearningAttempt(Base):
    __tablename__ = "learning_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    learning_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider_problem_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(100), nullable=True)
    source_code_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ProviderSubmissionResult(Base):
    __tablename__ = "provider_submission_results"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            "provider_problem_id",
            "source_code_hash",
            "normalized_status",
            "submitted_at",
            name="uq_provider_submission_result",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    attempt_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider_problem_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    problem_url: Mapped[str] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(100), nullable=True)
    source_code_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    raw_status: Mapped[str] = mapped_column(String(255), nullable=True)
    normalized_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback

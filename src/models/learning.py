from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="solved_problem")
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="learning")
    content_module: Mapped[str] = mapped_column(String(100), nullable=False, default="coding")
    content_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    problem_id: Mapped[Optional[int]] = mapped_column(ForeignKey("problems.id"), nullable=True)
    external_problem_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_problem_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    algorithm_choice: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    solving_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hint_level_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thinking_progress: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    implementation_mistakes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    conceptual_mistakes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    insights: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reflection_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reasoning_notes: Mapped[str] = mapped_column(Text, nullable=True)
    coach_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    coach_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_trace_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_submission_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exam_timer_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exam_hints_available: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    exam_hint_penalty_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    exam_hint_penalty_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exam_final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exam_report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    problem = relationship("Problem", backref="learning_events")


class LearningMemory(Base):
    __tablename__ = "learning_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class LearningTrendSnapshot(Base):
    __tablename__ = "learning_trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String(50), nullable=False, default="daily")
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ReviewSchedule(Base):
    __tablename__ = "review_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learning_events.id"), nullable=True)
    content_module: Mapped[str] = mapped_column(String(100), nullable=False, default="coding")
    content_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    problem_id: Mapped[Optional[int]] = mapped_column(ForeignKey("problems.id"), nullable=True)
    external_problem_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_problem_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    learning_event = relationship("LearningEvent", backref="review_schedules")
    problem = relationship("Problem", backref="review_schedules")


class ProviderProblem(Base):
    __tablename__ = "provider_problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_problem_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ProviderSubmission(Base):
    __tablename__ = "provider_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_submission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_problem_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=True)
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trace_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

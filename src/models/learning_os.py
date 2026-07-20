from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class ProviderRecord(Base):
    __tablename__ = "provider_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    problem_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    starter_code: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearningItem(Base):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_record_id: Mapped[Optional[int]] = mapped_column(ForeignKey("provider_records.id"), nullable=True)
    item_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    starter_code: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    provider_record = relationship("ProviderRecord", backref="learning_items")


class LearningAttempt(Base):
    __tablename__ = "learning_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="learning")
    language: Mapped[str] = mapped_column(String(50), nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elapsed_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    learning_item = relationship("LearningItem", backref="attempts")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("learning_attempts.id"), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    execution_trace_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    tests_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    attempt = relationship("LearningAttempt", backref="assessments")


class LearningReflection(Base):
    __tablename__ = "learning_reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), nullable=False)
    why_it_worked: Mapped[str] = mapped_column(Text, nullable=True)
    struggled_with: Mapped[str] = mapped_column(Text, nullable=True)
    remember_next_time: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    assessment = relationship("Assessment", backref="reflections")


class ReviewQueueItem(Base):
    __tablename__ = "review_queue_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), nullable=False)
    assessment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    learning_item = relationship("LearningItem", backref="review_queue_items")
    assessment = relationship("Assessment", backref="review_queue_items")


class LearningHistoryEvent(Base):
    __tablename__ = "learning_history_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learning_items.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    learning_item = relationship("LearningItem", backref="history_events")


class WeaknessAnalysis(Base):
    __tablename__ = "weakness_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learning_items.id"), nullable=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=True)
    weakness_type: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    learning_item = relationship("LearningItem", backref="weakness_analyses")

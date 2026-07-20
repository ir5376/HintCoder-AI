from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("learner_id", "problem_id", name="uq_progress_learner_problem"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learner_id: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)
    draft_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    programming_language: Mapped[str] = mapped_column(String(50), nullable=False, default="Python")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    problem_content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    last_opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.submission import Submission


class HintHistory(Base):
    __tablename__ = "hint_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("submissions.id"), nullable=True)
    source_platform: Mapped[str] = mapped_column(String(100), nullable=False, default="HintCode")
    external_problem_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    problem_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    programming_language: Mapped[str] = mapped_column(String(100), nullable=False, default="Python")
    student_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_hint: Mapped[str] = mapped_column(Text, nullable=False)
    hint_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    submission = relationship("Submission", backref="hint_histories")

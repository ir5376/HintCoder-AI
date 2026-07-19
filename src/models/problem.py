from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    problem_type: Mapped[str] = mapped_column(String(100), nullable=False)
    function_name: Mapped[str] = mapped_column(String(100), nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[str] = mapped_column(Text, nullable=True)
    test_cases: Mapped[str] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=True)

    @classmethod
    def from_dict(cls, item: Dict[str, Any]) -> "Problem":
        required_fields = [
            "title",
            "description",
            "category",
            "difficulty",
            "problem_type",
            "function_name",
            "starter_code",
        ]
        for field in required_fields:
            if field not in item or item[field] is None:
                raise ValueError(f"Missing required field: {field}")

        return cls(
            title=item["title"],
            description=item["description"],
            category=item["category"],
            difficulty=item["difficulty"],
            problem_type=item["problem_type"],
            function_name=item["function_name"],
            starter_code=item["starter_code"],
            constraints=item.get("constraints", ""),
            test_cases=json.dumps(item.get("test_cases", []), ensure_ascii=False),
            explanation=item.get("explanation", ""),
            source_type=item.get("source_type", ""),
            source_reference=item.get("source_reference", ""),
            tags=json.dumps(item.get("tags", []), ensure_ascii=False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "problem_type": self.problem_type,
            "function_name": self.function_name,
            "starter_code": self.starter_code,
            "constraints": self.constraints,
            "test_cases": json.loads(self.test_cases or "[]"),
            "explanation": self.explanation,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "tags": json.loads(self.tags or "[]"),
        }

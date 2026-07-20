from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LearningContent:
    id: str
    title: str
    content: str
    difficulty: str
    topic: str
    source: str
    content_type: str
    question_type: str
    answer: str
    metadata: dict[str, Any] = field(default_factory=dict)
    choices: list[str] | None = None
    coding_template: str | None = None
    language: str | None = None

    @property
    def starter_template(self) -> str | None:
        return self.coding_template


class ContentModule(Protocol):
    module_id: str
    display_name: str

    def to_learning_content(self, item: Any, *, language: str | None = None) -> LearningContent:
        """Convert module-specific content into the universal learning content shape."""

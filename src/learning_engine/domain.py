from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderMetadata:
    id: str
    display_name: str
    icon: str
    supported_languages: list[str]
    import_mode: list[str]
    supports_search: bool
    supports_url: bool
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderProblemPayload:
    provider_id: str
    problem_id: str
    title: str
    url: str = ""
    difficulty: str = ""
    language: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    starter_code: str = ""

    @property
    def provider(self) -> str:
        return self.provider_id


@dataclass(frozen=True)
class InternalProblemPayload:
    title: str
    provider: str
    provider_problem_id: str
    provider_url: str
    difficulty: str
    tags: list[str] = field(default_factory=list)
    starter_code: str = ""
    description: str = ""
    language_support: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryNote:
    problem_id: int | str
    concepts: list[str] = field(default_factory=list)
    flashcards: list[dict[str, Any]] = field(default_factory=list)
    quiz_items: list[dict[str, Any]] = field(default_factory=list)
    review_queue_items: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningItemPayload:
    item_id: str
    item_type: str
    title: str
    content: str = ""
    source_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    starter_code: str = ""


@dataclass(frozen=True)
class AssessmentPayload:
    assessment_type: str
    status: str
    score: float | None = None
    execution_trace: dict[str, Any] = field(default_factory=dict)
    tests: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningContext:
    current_approach: str = ""
    current_obstacle: str = ""
    intended_algorithm: str = ""
    desired_hint_level: int = 1
    confidence_level: float | None = None

    def to_prompt_lines(self) -> list[str]:
        confidence = "Not provided" if self.confidence_level is None else str(self.confidence_level)
        return [
            f"- Current approach: {self.current_approach or 'Not provided'}",
            f"- Current obstacle: {self.current_obstacle or 'Not provided'}",
            f"- Intended algorithm: {self.intended_algorithm or 'Not provided'}",
            f"- Desired hint level: {self.desired_hint_level}",
            f"- Confidence level: {confidence}",
        ]


class ProviderAdapter(Protocol):
    provider_id: str
    display_name: str
    icon: str
    supported_languages: list[str]
    import_mode: list[str]
    supports_search: bool
    supports_url: bool

    def import_problem(self, payload: dict[str, Any]) -> ProviderProblemPayload:
        """Normalize provider problem import data."""

    def import_problem_from_url(self, url: str, payload: dict[str, Any] | None = None) -> ProviderProblemPayload:
        """Build normalized provider problem data from a supported URL."""

    def map_language(self, language: str | None) -> str:
        """Map provider language names to HintCode language names."""

    def sync_submission(self, payload: dict[str, Any]) -> AssessmentPayload:
        """Normalize official submission results into an assessment payload."""

    def sync_recent(self) -> list[ProviderProblemPayload]:
        """Future authenticated sync for recently solved/imported problems."""

    def sync_favorites(self) -> list[ProviderProblemPayload]:
        """Future authenticated sync for favorite/bookmarked problems."""

    def sync_history(self) -> list[ProviderProblemPayload]:
        """Future authenticated sync for official submission history."""

    def metadata(self) -> ProviderMetadata:
        """Describe provider capabilities without leaking provider logic into the engine."""


@dataclass(frozen=True)
class LearningLoopResult:
    learning_item_id: int
    attempt_id: int
    assessment_id: int
    reflection_id: int
    review_ids: list[int]
    created_at: datetime

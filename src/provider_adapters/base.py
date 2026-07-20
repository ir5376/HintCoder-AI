from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from src.learning_engine.content import LearningContent


@dataclass(frozen=True)
class ImportedProblem:
    provider: str
    provider_problem_id: str
    content: LearningContent
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncedSubmission:
    provider: str
    provider_submission_id: str
    provider_problem_id: str
    status: str
    language: str
    submitted_at: datetime
    code: str = ""
    runtime_ms: int | None = None
    memory_kb: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderAdapter(Protocol):
    provider_id: str
    display_name: str

    def import_problem(self, payload: dict[str, Any]) -> ImportedProblem:
        """Convert provider-specific problem data into LearningContent."""

    def map_language(self, provider_language: str | None) -> str:
        """Convert provider language names into Nextep language names."""

    def sync_submission(self, payload: dict[str, Any]) -> SyncedSubmission:
        """Convert provider-specific submission data into Nextep submission sync data."""

    def metadata(self) -> dict[str, Any]:
        """Return provider capabilities and attribution metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.learning_engine.domain import InternalProblemPayload, ProviderProblemPayload
from src.provider_adapters.detector import detect_provider
from src.provider_adapters.registry import ProviderRegistry


@dataclass(frozen=True)
class ProblemImportRequest:
    provider: str
    problem_id: str
    title: str
    url: str
    difficulty: str = ""
    language: str = ""
    starter_code: str = ""
    metadata: dict[str, Any] | None = None


class ProblemImportService:
    """Normalizes provider problem imports before they enter the Learning Engine."""

    allowed_fields = {"provider", "problem_id", "title", "url", "difficulty", "language", "starter_code", "metadata"}

    def __init__(self, provider_registry: ProviderRegistry | None = None) -> None:
        self.provider_registry = provider_registry or ProviderRegistry()

    def import_problem(self, payload: dict[str, Any]) -> ProviderProblemPayload:
        unexpected_fields = set(payload) - self.allowed_fields
        if unexpected_fields:
            raise ValueError(f"Unsupported import field(s): {', '.join(sorted(unexpected_fields))}")

        request = ProblemImportRequest(
            provider=str(payload.get("provider") or "").strip(),
            problem_id=str(payload.get("problem_id") or "").strip(),
            title=str(payload.get("title") or "").strip(),
            url=str(payload.get("url") or "").strip(),
            difficulty=str(payload.get("difficulty") or "").strip(),
            language=str(payload.get("language") or "").strip(),
            starter_code=str(payload.get("starter_code") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )
        if not request.provider:
            raise ValueError("provider is required")
        if not request.title:
            raise ValueError("title is required")
        if not request.url:
            raise ValueError("url is required")

        adapter = self.provider_registry.get(request.provider)
        normalized_payload = {
            "problem_id": request.problem_id,
            "title": request.title,
            "url": request.url,
            "difficulty": request.difficulty,
            "language": request.language,
            "starter_code": request.starter_code,
            "metadata": request.metadata or {},
        }
        if not request.problem_id:
            return adapter.import_problem_from_url(request.url, normalized_payload)
        return adapter.import_problem(normalized_payload)

    def import_problem_from_url(
        self,
        url: str,
        payload: dict[str, Any] | None = None,
        provider_hint: str = "",
    ) -> ProviderProblemPayload:
        normalized_url = _normalize_url(url)
        provider_id = detect_provider(normalized_url) or provider_hint
        if not provider_id:
            raise ValueError("Unsupported provider URL")

        adapter = self.provider_registry.get(provider_id)
        return adapter.import_problem_from_url(normalized_url, payload or {})

    def normalize_internal_problem(self, payload: ProviderProblemPayload) -> InternalProblemPayload:
        metadata = dict(payload.metadata or {})
        tags = list(metadata.get("tags") or [])
        provider_url = metadata.get("provider_url") or payload.url
        language_support = list(metadata.get("supported_languages") or [])
        return InternalProblemPayload(
            title=payload.title,
            provider=payload.provider_id,
            provider_problem_id=payload.problem_id,
            provider_url=provider_url,
            difficulty=payload.difficulty or "Unknown",
            tags=tags,
            starter_code=payload.starter_code,
            description=metadata.get("description", ""),
            language_support=language_support,
            metadata=metadata,
        )


def _normalize_url(url: str) -> str:
    value = str(url or "").strip()
    if "://" not in value and "." in value:
        return f"https://{value}"
    return value

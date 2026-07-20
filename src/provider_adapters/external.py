from __future__ import annotations

from datetime import datetime
from hashlib import sha1
from typing import Any

from src.learning_engine.content import LearningContent
from src.learning_engine.templates import StarterTemplateRegistry
from src.provider_adapters.base import ImportedProblem, SyncedSubmission


class ExternalProviderAdapter:
    provider_id = "external"
    display_name = "External Provider"

    def __init__(self, template_registry: StarterTemplateRegistry | None = None) -> None:
        self.template_registry = template_registry or StarterTemplateRegistry()

    def import_problem(self, payload: dict[str, Any]) -> ImportedProblem:
        title = str(payload.get("problem_title") or payload.get("title") or "External Problem").strip()
        url = str(payload.get("problem_url") or payload.get("url") or "").strip()
        language = self.map_language(payload.get("language"))
        provider_problem_id = str(payload.get("provider_problem_id") or self._stable_problem_id(title, url))
        return ImportedProblem(
            provider=self.provider_id,
            provider_problem_id=provider_problem_id,
            content=LearningContent(
                id=f"{self.provider_id}:{provider_problem_id}",
                title=title,
                content=str(payload.get("description") or "Imported problem. Use the original provider for the full statement."),
                difficulty=str(payload.get("difficulty") or "Unknown"),
                topic=str(payload.get("topic") or "Coding"),
                source=url or self.display_name,
                content_type="coding",
                question_type="coding_practice",
                answer="",
                metadata={
                    "provider": self.provider_id,
                    "provider_problem_id": provider_problem_id,
                    "problem_url": url,
                },
                coding_template=self.template_registry.get_template(language),
                language=language,
            ),
            metadata={"problem_url": url},
        )

    def map_language(self, provider_language: str | None) -> str:
        normalized = (provider_language or "Python").strip().lower()
        language_map = {
            "python": "Python",
            "python3": "Python",
            "py": "Python",
            "java": "Java",
            "cpp": "C++",
            "c++": "C++",
            "javascript": "JavaScript",
            "js": "JavaScript",
            "c": "C",
        }
        return language_map.get(normalized, "Python")

    def sync_submission(self, payload: dict[str, Any]) -> SyncedSubmission:
        submitted_at = payload.get("submitted_at")
        if isinstance(submitted_at, str):
            try:
                submitted_at_value = datetime.fromisoformat(submitted_at)
            except ValueError:
                submitted_at_value = datetime.utcnow()
        else:
            submitted_at_value = submitted_at if isinstance(submitted_at, datetime) else datetime.utcnow()

        return SyncedSubmission(
            provider=self.provider_id,
            provider_submission_id=str(payload.get("provider_submission_id") or self._stable_problem_id(payload.get("code", ""), str(submitted_at_value))),
            provider_problem_id=str(payload.get("provider_problem_id") or payload.get("content_id") or ""),
            status=str(payload.get("status") or "unknown"),
            language=self.map_language(payload.get("language")),
            submitted_at=submitted_at_value,
            code=str(payload.get("code") or ""),
            runtime_ms=payload.get("runtime_ms"),
            memory_kb=payload.get("memory_kb"),
            metadata={key: value for key, value in payload.items() if key not in {"code"}},
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "capabilities": ["problem_import", "language_mapping", "submission_sync", "metadata"],
            "official_judging": False,
        }

    def _stable_problem_id(self, title: Any, url: str) -> str:
        digest = sha1(f"{title}|{url}".encode("utf-8")).hexdigest()[:12]
        return digest

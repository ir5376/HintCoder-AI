from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from src.learning_engine.domain import AssessmentPayload, ProviderMetadata, ProviderProblemPayload


class StaticCodingProviderAdapter:
    def __init__(
        self,
        provider_id: str,
        display_name: str,
        *,
        icon: str = "code",
        supported_languages: list[str] | None = None,
        import_mode: list[str] | None = None,
        supports_search: bool = False,
        supports_url: bool = True,
    ) -> None:
        self.provider_id = provider_id
        self.display_name = display_name
        self.icon = icon
        self.supported_languages = supported_languages or ["Python", "Java", "C++", "JavaScript", "C"]
        self.import_mode = import_mode or ["url"]
        self.supports_search = supports_search
        self.supports_url = supports_url

    def import_problem(self, payload: dict[str, Any]) -> ProviderProblemPayload:
        language = self.map_language(payload.get("language") or payload.get("metadata", {}).get("language"))
        return ProviderProblemPayload(
            provider_id=self.provider_id,
            problem_id=str(payload.get("problem_id") or payload.get("id") or ""),
            title=str(payload.get("title") or ""),
            url=str(payload.get("url") or payload.get("source_reference") or ""),
            difficulty=str(payload.get("difficulty") or payload.get("metadata", {}).get("difficulty") or "Unknown"),
            language=language,
            metadata=self._enrich_metadata(dict(payload.get("metadata") or {}), payload),
            starter_code=str(payload.get("starter_code") or ""),
        )

    def import_problem_from_url(self, url: str, payload: dict[str, Any] | None = None) -> ProviderProblemPayload:
        payload = dict(payload or {})
        payload["url"] = url
        payload["problem_id"] = payload.get("problem_id") or self._problem_id_from_url(url)
        payload["title"] = payload.get("title") or self._title_from_url(url, payload["problem_id"])
        payload["difficulty"] = payload.get("difficulty") or "Unknown"
        payload.setdefault("metadata", self._metadata_from_url(url))
        return self.import_problem(payload)

    def _problem_id_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            return parsed.netloc or "external_problem"
        return path_parts[-1]

    def _title_from_url(self, url: str, problem_id: str) -> str:
        return f"{self.display_name} {problem_id}" if problem_id else self.display_name

    def _metadata_from_url(self, url: str) -> dict[str, Any]:
        parsed = urlparse(url)
        return {"hostname": parsed.hostname or "", "pathname": parsed.path}

    def map_language(self, language: str | None) -> str:
        normalized = (language or "Python").strip().lower()
        language_map = {
            "python": "Python",
            "python3": "Python",
            "java": "Java",
            "cpp": "C++",
            "c++": "C++",
            "javascript": "JavaScript",
            "js": "JavaScript",
            "c": "C",
        }
        return language_map.get(normalized, "Python")

    def sync_submission(self, payload: dict[str, Any]) -> AssessmentPayload:
        status = str(payload.get("status") or "unknown")
        return AssessmentPayload(
            assessment_type="coding",
            status=status,
            score=1.0 if status.lower() in {"accepted", "ac", "correct"} else 0.0,
            execution_trace=dict(payload.get("execution_trace") or {}),
            tests=dict(payload.get("tests") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )

    def sync_recent(self) -> list[ProviderProblemPayload]:
        return []

    def sync_favorites(self) -> list[ProviderProblemPayload]:
        return []

    def sync_history(self) -> list[ProviderProblemPayload]:
        return []

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            id=self.provider_id,
            display_name=self.display_name,
            icon=self.icon,
            supported_languages=self.supported_languages,
            import_mode=self.import_mode,
            supports_search=self.supports_search,
            supports_url=self.supports_url,
            capabilities=["problem_import", "language_mapping", "submission_sync", "metadata"],
        )

    def _enrich_metadata(self, metadata: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        metadata.setdefault("provider", self.provider_id)
        metadata.setdefault("display_name", self.display_name)
        metadata.setdefault("provider_url", str(payload.get("url") or ""))
        metadata.setdefault("supported_languages", self.supported_languages)
        return metadata


class LeetCodeProvider(StaticCodingProviderAdapter):
    def __init__(self) -> None:
        super().__init__(
            "leetcode",
            "LeetCode",
            icon="LC",
            supported_languages=["Python", "Java", "C++", "JavaScript", "C"],
            import_mode=["url", "search"],
            supports_search=True,
            supports_url=True,
        )

    def _problem_id_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if "problems" in path_parts:
            index = path_parts.index("problems")
            if index + 1 < len(path_parts):
                return path_parts[index + 1]
        return super()._problem_id_from_url(url)

    def _title_from_url(self, url: str, problem_id: str) -> str:
        if problem_id:
            return problem_id.replace("-", " ").title()
        return super()._title_from_url(url, problem_id)


class ProgrammersProvider(StaticCodingProviderAdapter):
    def __init__(self) -> None:
        super().__init__(
            "programmers",
            "Programmers",
            icon="PG",
            supported_languages=["Python", "Java", "C++", "JavaScript", "C"],
            import_mode=["url", "search"],
            supports_search=True,
            supports_url=True,
        )

    def _problem_id_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if "lessons" in path_parts:
            index = path_parts.index("lessons")
            if index + 1 < len(path_parts):
                return path_parts[index + 1]
        return super()._problem_id_from_url(url)


class BaekjoonProvider(StaticCodingProviderAdapter):
    def __init__(self) -> None:
        super().__init__(
            "baekjoon",
            "Baekjoon",
            icon="BOJ",
            supported_languages=["Python", "Java", "C++", "C"],
            import_mode=["url"],
            supports_search=False,
            supports_url=True,
        )

    def _problem_id_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if "problem" in path_parts:
            index = path_parts.index("problem")
            if index + 1 < len(path_parts):
                return path_parts[index + 1]
        return super()._problem_id_from_url(url)


class CustomProvider(StaticCodingProviderAdapter):
    def __init__(self) -> None:
        super().__init__(
            "custom",
            "Custom",
            icon="CUSTOM",
            supported_languages=["Python", "Java", "C++", "JavaScript", "C"],
            import_mode=["url"],
            supports_search=False,
            supports_url=True,
        )


LeetCodeProviderAdapter = LeetCodeProvider
ProgrammersProviderAdapter = ProgrammersProvider

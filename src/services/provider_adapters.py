from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


NORMALIZED_STATUSES = {
    "pending",
    "accepted",
    "wrong_answer",
    "runtime_error",
    "time_limit_exceeded",
    "memory_limit_exceeded",
    "compile_error",
    "cancelled",
    "unknown",
}


@dataclass(frozen=True)
class ProblemIdentity:
    provider: str
    provider_problem_id: str
    title: str
    url: str
    metadata: dict[str, Any]


class CodingProviderAdapter(ABC):
    provider: str
    supported_hosts: tuple[str, ...]
    language_map: dict[str, str]
    status_map: dict[str, str]

    def supports_url(self, url: str) -> bool:
        host = urlparse(_normalize_url(url)).netloc.lower()
        return any(host == supported or host.endswith(f".{supported}") for supported in self.supported_hosts)

    @abstractmethod
    def extract_problem_identity(self, page_metadata: dict[str, Any]) -> ProblemIdentity:
        raise NotImplementedError

    def normalize_language(self, language: str) -> str:
        key = _compact(language)
        return self.language_map.get(key, str(language or "").strip() or "unknown")

    def prepare_code_transfer(self, code: str, language: str) -> dict[str, str]:
        clean_code = str(code or "")
        return {
            "language": self.normalize_language(language),
            "code": clean_code,
            "source_code_hash": hashlib.sha256(clean_code.encode("utf-8")).hexdigest(),
            "submit": "manual",
        }

    def detect_submission_status(self, page_state: dict[str, Any]) -> str:
        raw = str(
            page_state.get("raw_status")
            or page_state.get("status")
            or page_state.get("status_text")
            or page_state.get("result")
            or page_state.get("result_text")
            or ""
        )
        return self.normalize_submission_status(raw)

    def normalize_submission_status(self, raw_status: str) -> str:
        normalized = self.status_map.get(_compact(raw_status), "")
        return normalized if normalized in NORMALIZED_STATUSES else "unknown"


class LeetCodeAdapter(CodingProviderAdapter):
    provider = "leetcode"
    supported_hosts = ("leetcode.com",)
    language_map = {
        "python": "python",
        "python3": "python",
        "java": "java",
        "cpp": "cpp",
        "c++": "cpp",
        "javascript": "javascript",
        "js": "javascript",
        "c": "c",
    }
    status_map = {
        "accepted": "accepted",
        "wronganswer": "wrong_answer",
        "runtimeerror": "runtime_error",
        "timelimitexceeded": "time_limit_exceeded",
        "memorylimitexceeded": "memory_limit_exceeded",
        "compileerror": "compile_error",
        "compilationerror": "compile_error",
        "pending": "pending",
        "running": "pending",
        "cancelled": "cancelled",
        "canceled": "cancelled",
    }

    def extract_problem_identity(self, page_metadata: dict[str, Any]) -> ProblemIdentity:
        url = _normalize_url(str(page_metadata.get("url") or page_metadata.get("problem_url") or ""))
        problem_id = str(page_metadata.get("problem_id") or _leetcode_problem_id(url) or "").strip()
        return ProblemIdentity(
            provider=self.provider,
            provider_problem_id=problem_id,
            title=_clean_title(str(page_metadata.get("title") or _title_from_id(problem_id) or "LeetCode Problem")),
            url=url,
            metadata={"hostname": urlparse(url).netloc, "source": "content_script"},
        )


class ProgrammersAdapter(CodingProviderAdapter):
    provider = "programmers"
    supported_hosts = ("programmers.co.kr", "school.programmers.co.kr")
    language_map = {
        "python": "python",
        "python3": "python",
        "java": "java",
        "cpp": "cpp",
        "c++": "cpp",
        "javascript": "javascript",
        "js": "javascript",
        "c": "c",
    }
    status_map = {
        "정답": "accepted",
        "맞았습니다": "accepted",
        "accepted": "accepted",
        "실행중": "pending",
        "채점중": "pending",
        "pending": "pending",
        "오답": "wrong_answer",
        "wronganswer": "wrong_answer",
        "런타임에러": "runtime_error",
        "runtimeerror": "runtime_error",
        "시간초과": "time_limit_exceeded",
        "timelimitexceeded": "time_limit_exceeded",
        "메모리초과": "memory_limit_exceeded",
        "memorylimitexceeded": "memory_limit_exceeded",
        "컴파일에러": "compile_error",
        "compileerror": "compile_error",
        "취소": "cancelled",
        "cancelled": "cancelled",
    }

    def extract_problem_identity(self, page_metadata: dict[str, Any]) -> ProblemIdentity:
        url = _normalize_url(str(page_metadata.get("url") or page_metadata.get("problem_url") or ""))
        problem_id = str(page_metadata.get("problem_id") or _programmers_problem_id(url) or "").strip()
        return ProblemIdentity(
            provider=self.provider,
            provider_problem_id=problem_id,
            title=_clean_title(str(page_metadata.get("title") or _title_from_id(problem_id) or "Programmers Problem")),
            url=url,
            metadata={"hostname": urlparse(url).netloc, "source": "content_script"},
        )


class BaekjoonAdapter(CodingProviderAdapter):
    provider = "baekjoon"
    supported_hosts = ("acmicpc.net",)
    language_map = LeetCodeAdapter.language_map
    status_map = {}

    def extract_problem_identity(self, page_metadata: dict[str, Any]) -> ProblemIdentity:
        url = _normalize_url(str(page_metadata.get("url") or page_metadata.get("problem_url") or ""))
        problem_id = str(page_metadata.get("problem_id") or _path_problem_id(url, "problem") or "").strip()
        return ProblemIdentity(
            provider=self.provider,
            provider_problem_id=problem_id,
            title=_clean_title(str(page_metadata.get("title") or _title_from_id(problem_id) or "Baekjoon Problem")),
            url=url,
            metadata={"hostname": urlparse(url).netloc, "source": "content_script"},
        )


class CodeforcesAdapter(CodingProviderAdapter):
    provider = "codeforces"
    supported_hosts = ("codeforces.com",)
    language_map = LeetCodeAdapter.language_map
    status_map = {}

    def extract_problem_identity(self, page_metadata: dict[str, Any]) -> ProblemIdentity:
        url = _normalize_url(str(page_metadata.get("url") or page_metadata.get("problem_url") or ""))
        problem_id = str(page_metadata.get("problem_id") or _codeforces_problem_id(url) or "").strip()
        return ProblemIdentity(
            provider=self.provider,
            provider_problem_id=problem_id,
            title=_clean_title(str(page_metadata.get("title") or _title_from_id(problem_id) or "Codeforces Problem")),
            url=url,
            metadata={"hostname": urlparse(url).netloc, "source": "content_script"},
        )


ADAPTERS: dict[str, CodingProviderAdapter] = {
    "leetcode": LeetCodeAdapter(),
    "programmers": ProgrammersAdapter(),
    "baekjoon": BaekjoonAdapter(),
    "boj": BaekjoonAdapter(),
    "codeforces": CodeforcesAdapter(),
}


def get_provider_adapter(provider: str) -> CodingProviderAdapter:
    adapter = ADAPTERS.get(str(provider or "").strip().lower())
    if adapter is None:
        raise ValueError("Unsupported provider")
    return adapter


def adapter_for_url(url: str) -> CodingProviderAdapter:
    for adapter in {adapter.provider: adapter for adapter in ADAPTERS.values()}.values():
        if adapter.supports_url(url):
            return adapter
    raise ValueError("Unsupported provider URL")


def _compact(value: str) -> str:
    return re.sub(r"[\s_\-:]+", "", str(value or "").strip().lower())


def _normalize_url(url: str) -> str:
    value = str(url or "").strip()
    if "://" not in value and "." in value:
        return f"https://{value}"
    return value


def _leetcode_problem_id(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if "problems" in parts:
        index = parts.index("problems")
        return parts[index + 1] if index + 1 < len(parts) else ""
    return parts[-1] if parts else ""


def _programmers_problem_id(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if "lessons" in parts:
        index = parts.index("lessons")
        return parts[index + 1] if index + 1 < len(parts) else ""
    return parts[-1] if parts else ""


def _path_problem_id(url: str, marker: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if marker in parts:
        index = parts.index(marker)
        return parts[index + 1] if index + 1 < len(parts) else ""
    return parts[-1] if parts else ""


def _codeforces_problem_id(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return "/".join(parts[-2:]) if len(parts) >= 2 else (parts[-1] if parts else "")


def _title_from_id(problem_id: str) -> str:
    if not problem_id:
        return ""
    return problem_id.replace("-", " ").replace("_", " ").title()


def _clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", str(title or "").replace("- LeetCode", "").strip())

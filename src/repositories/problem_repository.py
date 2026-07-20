import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from src.models.problem import Problem


class ProblemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._problem_dir = Path(__file__).resolve().parents[1] / "problems"

    def _load_problem_sets_from_disk(self) -> List[dict[str, Any]]:
        """Load JSON problem sets from the /problems directory when present."""
        if not self._problem_dir.exists():
            return []

        problems: List[dict[str, Any]] = []
        for path in sorted(self._problem_dir.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (json.JSONDecodeError, OSError):
                continue

            if isinstance(payload, dict):
                items = payload.get("problems") or payload.get("items") or []
            elif isinstance(payload, list):
                items = payload
            else:
                items = []

            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        problems.append(item)

        return problems

    def seed_from_problem_files(self) -> None:
        """Populate the database from JSON files in /problems when available."""
        problem_items = self._load_problem_sets_from_disk()
        if not problem_items:
            return

        for item in problem_items:
            existing = self.session.query(Problem).filter(Problem.id == item.get("id")).one_or_none()
            if existing is None:
                self.session.add(Problem.from_dict(item))

    def list_problems(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[Problem]:
        query = self.session.query(Problem)
        if category:
            query = query.filter(Problem.category == category)
        if difficulty:
            query = query.filter(Problem.difficulty == difficulty)
        return query.order_by(Problem.id).all()

    def get_problem(self, problem_id: int) -> Optional[Problem]:
        return self.session.query(Problem).filter(Problem.id == problem_id).one_or_none()

    def upsert_provider_problem(
        self,
        *,
        provider: str,
        provider_problem_id: str,
        title: str,
        url: str,
        difficulty: str = "Unknown",
        language: str = "",
        starter_code: str = "",
        metadata: dict[str, Any] | None = None,
        description: str = "",
        tags: list[str] | None = None,
        language_support: list[str] | None = None,
    ) -> Problem:
        existing = (
            self.session.query(Problem)
            .filter(Problem.source_type == provider, Problem.source_reference == url)
            .one_or_none()
        )

        metadata = dict(metadata or {})
        language_support = language_support or list(metadata.get("supported_languages") or [])
        tags = tags or list(metadata.get("tags") or [])
        provider_tags = json.dumps(
            {
                "provider": provider,
                "provider_problem_id": provider_problem_id,
                "provider_url": url,
                "difficulty": difficulty or "Unknown",
                "tags": tags,
                "language": language,
                "language_support": language_support,
                "original_url": url,
                "import_time": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
            },
            ensure_ascii=False,
        )
        fallback_code = starter_code or _starter_code_for_language(language)
        function_name = _provider_function_name(provider, provider_problem_id)

        if existing is None:
            existing = Problem(
                title=title,
                description=description
                or "Imported provider problem. Use the original problem URL for the official statement.",
                category="External",
                difficulty=difficulty or "Unknown",
                problem_type="Provider Import",
                function_name=function_name,
                starter_code=fallback_code,
                constraints="",
                test_cases="[]",
                explanation="",
                source_type=provider,
                source_reference=url,
                tags=provider_tags,
            )
            self.session.add(existing)
        else:
            existing.title = title
            if description:
                existing.description = description
            existing.difficulty = difficulty or existing.difficulty or "Unknown"
            existing.source_type = provider
            existing.source_reference = url
            existing.starter_code = existing.starter_code or fallback_code
            existing.tags = provider_tags

        self.session.flush()
        return existing

    def get_random_problem(self) -> Optional[Problem]:
        """Return a random problem from the database, falling back to disk data if needed."""
        problems = self.list_problems()
        if not problems:
            problem_items = self._load_problem_sets_from_disk()
            if not problem_items:
                return None

            for item in problem_items:
                self.session.add(Problem.from_dict(item))
            self.session.flush()
            problems = self.list_problems()

        if not problems:
            return None

        return random.choice(problems)

    def get_next_problem(self, current_problem_id: Optional[int] = None) -> Optional[Problem]:
        """Return the next problem after the given id, or the first one if none is provided."""
        problems = self.list_problems()
        if not problems:
            problem_items = self._load_problem_sets_from_disk()
            if not problem_items:
                return None

            for item in problem_items:
                self.session.add(Problem.from_dict(item))
            self.session.flush()
            problems = self.list_problems()

        if not problems:
            return None

        if current_problem_id is None:
            return problems[0]

        for index, problem in enumerate(problems):
            if problem.id == current_problem_id:
                return problems[index + 1] if index + 1 < len(problems) else problems[0]

        return problems[0]

    def list_categories(self) -> List[str]:
        return [row[0] for row in self.session.query(Problem.category).distinct().order_by(Problem.category).all()]

    def list_difficulties(self) -> List[str]:
        return [row[0] for row in self.session.query(Problem.difficulty).distinct().order_by(Problem.difficulty).all()]


def _starter_code_for_language(language: str) -> str:
    normalized = (language or "Python").strip().lower()
    if normalized in {"javascript", "js"}:
        return "function solution() {\n    // Write your solution here\n}\n"
    if normalized == "java":
        return "class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}\n"
    if normalized in {"c++", "cpp"}:
        return "#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n"
    return "def solution():\n    pass\n"


def _provider_function_name(provider: str, provider_problem_id: str) -> str:
    raw_name = f"{provider}_{provider_problem_id or 'problem'}".lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", raw_name).strip("_")
    return (normalized or "provider_problem")[:100]

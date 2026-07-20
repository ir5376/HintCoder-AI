from typing import Any, Dict, List, Optional

from src.learning_engine.domain import InternalProblemPayload, ProviderProblemPayload
from src.models.problem import Problem
from src.repositories.problem_repository import ProblemRepository


class ProblemService:
    def __init__(self, session) -> None:
        self.repository = ProblemRepository(session)

    def get_problem_list(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        problems = self.repository.list_problems(category=category, difficulty=difficulty)
        return [problem.to_dict() for problem in problems]

    def get_problem(self, problem_id: int) -> Optional[Dict[str, str]]:
        problem = self.repository.get_problem(problem_id)
        return problem.to_dict() if problem else None

    def import_provider_problem(
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
    ) -> Dict[str, Any]:
        problem = self.repository.upsert_provider_problem(
            provider=provider,
            provider_problem_id=provider_problem_id,
            title=title,
            url=url,
            difficulty=difficulty,
            language=language,
            starter_code=starter_code,
            metadata=metadata,
            description=description,
            tags=tags,
            language_support=language_support,
        )
        self.repository.session.commit()
        return problem.to_dict()

    def import_provider_payload(self, payload: ProviderProblemPayload) -> Dict[str, Any]:
        return self.import_provider_problem(
            provider=payload.provider_id,
            provider_problem_id=payload.problem_id,
            title=payload.title,
            url=payload.url,
            difficulty=payload.difficulty or "Unknown",
            language=payload.language,
            starter_code=payload.starter_code,
            metadata=payload.metadata,
        )

    def import_internal_problem(self, payload: InternalProblemPayload) -> Dict[str, Any]:
        return self.import_provider_problem(
            provider=payload.provider,
            provider_problem_id=payload.provider_problem_id,
            title=payload.title,
            url=payload.provider_url,
            difficulty=payload.difficulty,
            language=payload.metadata.get("language", ""),
            starter_code=payload.starter_code,
            metadata=payload.metadata,
            description=payload.description,
            tags=payload.tags,
            language_support=payload.language_support,
        )

    def get_random_problem(self) -> Optional[Dict[str, Any]]:
        """Return a random problem for the current session."""
        problem = self.repository.get_random_problem()
        return problem.to_dict() if problem else None

    def get_next_problem(self, current_problem_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Return the next problem for a simple Next Problem flow."""
        problem = self.repository.get_next_problem(current_problem_id=current_problem_id)
        return problem.to_dict() if problem else None

    def get_filters(self) -> Dict[str, List[str]]:
        return {
            "categories": self.repository.list_categories(),
            "difficulties": self.repository.list_difficulties(),
        }

from typing import Dict, List, Optional

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

    def get_filters(self) -> Dict[str, List[str]]:
        return {
            "categories": self.repository.list_categories(),
            "difficulties": self.repository.list_difficulties(),
        }

from typing import Any, Dict, List, Optional

from src.models.learning_item import LearningItem
from src.models.problem import Problem
from src.repositories.problem_repository import ProblemRepository
from src.services.learning_source_service import LearningSourceService


class ProblemService:
    def __init__(self, session) -> None:
        self.repository = ProblemRepository(session)

    def get_problem_list(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        problems = self.repository.list_problems(category=category, difficulty=difficulty)
        return [self._problem_to_dict(problem) for problem in problems]

    def get_problem(self, problem_id: int) -> Optional[Dict[str, str]]:
        problem = self.repository.get_problem(problem_id)
        return self._problem_to_dict(problem) if problem else None

    def get_random_problem(self) -> Optional[Dict[str, Any]]:
        """Return a random problem for the current session."""
        problem = self.repository.get_random_problem()
        return problem.to_dict() if problem else None

    def get_next_problem(self, current_problem_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Return the next problem for a simple Next Problem flow."""
        problem = self.repository.get_next_problem(current_problem_id=current_problem_id)
        return self._problem_to_dict(problem) if problem else None

    def get_filters(self) -> Dict[str, List[str]]:
        return {
            "categories": self.repository.list_categories(),
            "difficulties": self.repository.list_difficulties(),
        }

    def preview_pdf_source(
        self,
        *,
        question_pdf_name: str,
        question_pdf: bytes,
        answer_pdf_name: str = "",
        answer_pdf: bytes | None = None,
        owner_user_id: str = "local",
        title: str = "",
    ) -> dict[str, Any]:
        return LearningSourceService(self.repository.session).preview_exam_source(
            question_pdf_name=question_pdf_name,
            question_pdf=question_pdf,
            answer_pdf_name=answer_pdf_name,
            answer_pdf=answer_pdf,
            owner_user_id=owner_user_id,
            title=title,
        )

    def import_pdf_source(
        self,
        *,
        question_pdf_name: str,
        question_pdf: bytes,
        answer_pdf_name: str = "",
        answer_pdf: bytes | None = None,
        owner_user_id: str = "local",
        title: str = "",
    ) -> dict[str, Any]:
        return LearningSourceService(self.repository.session).import_exam_source(
            question_pdf_name=question_pdf_name,
            question_pdf=question_pdf,
            answer_pdf_name=answer_pdf_name,
            answer_pdf=answer_pdf,
            owner_user_id=owner_user_id,
            title=title,
        )

    def _problem_to_dict(self, problem: Problem) -> Dict[str, Any]:
        payload = problem.to_dict()
        learning_item = self._learning_item_for_problem(problem)
        if learning_item is None:
            return payload
        item = learning_item.to_dict()
        metadata = item.get("metadata") or {}
        payload.update(
            {
                "learning_item": item,
                "problem_type": item.get("question_type") or payload.get("problem_type"),
                "source_type": "PDF" if item.get("source_type") == "exam_pdf" else payload.get("source_type"),
                "question_number": item.get("question_number"),
                "question_text": item.get("content") or payload.get("description"),
                "choices": item.get("choices") or [],
                "answer_state": "Verified" if item.get("answer_status") == "verified" else "No answer",
                "source_page": metadata.get("page_number"),
                "source_metadata": metadata,
            }
        )
        return payload

    def _learning_item_for_problem(self, problem: Problem) -> LearningItem | None:
        reference = problem.source_reference or ""
        prefix = "learning_item:"
        if problem.source_type != "learning_item" or not reference.startswith(prefix):
            return None
        raw_id = reference.removeprefix(prefix)
        try:
            learning_item_id = int(raw_id)
        except ValueError:
            return None
        return self.repository.session.query(LearningItem).filter(LearningItem.id == learning_item_id).one_or_none()

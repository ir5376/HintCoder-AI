import re
from typing import Any, Dict, List, Optional

from src.models.learning_item import LearningItem
from src.models.problem import Problem
from src.repositories.learning_item_repository import LearningItemRepository
from src.repositories.problem_repository import ProblemRepository
from src.services.learning_source_service import LearningSourceService


class ProblemService:
    def __init__(self, session) -> None:
        self.repository = ProblemRepository(session)
        self.learning_repository = LearningItemRepository(session)

    def get_problem_list(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        problems = self.repository.list_problems(category=category, difficulty=difficulty)
        problem_rows = [self._problem_to_dict(problem) for problem in problems]
        wrapped_learning_item_ids = {
            int(problem.source_reference.removeprefix("learning_item:"))
            for problem in problems
            if (problem.source_type or "") == "learning_item"
            and (problem.source_reference or "").startswith("learning_item:")
            and problem.source_reference.removeprefix("learning_item:").isdigit()
        }
        learning_item_rows = [
            self._learning_item_to_problem_dict(item)
            for item in self.repository.list_learning_items()
            if item.id not in wrapped_learning_item_ids
        ]
        rows = [*problem_rows, *learning_item_rows]
        if category:
            rows = [row for row in rows if row.get("category") == category]
        if difficulty:
            rows = [row for row in rows if row.get("difficulty") == difficulty]
        return rows

    def get_problem(self, problem_id: int) -> Optional[Dict[str, str]]:
        if isinstance(problem_id, str) and problem_id.startswith("learning_item:"):
            learning_item_id = problem_id.removeprefix("learning_item:")
            if learning_item_id.isdigit():
                item = self.repository.session.query(LearningItem).filter(LearningItem.id == int(learning_item_id)).one_or_none()
                return self._learning_item_to_problem_dict(item) if item else None
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

    def get_linked_solution(self, item_id: int | str) -> Dict[str, Any]:
        learning_item_id = self._learning_item_id_from_public_id(item_id)
        if learning_item_id is None:
            return {
                "has_reliable_solution": False,
                "canonical_answer": "",
                "explanation": "",
                "answer_record_id": None,
                "learning_item_id": None,
            }
        record = self.learning_repository.linked_answer_record(learning_item_id)
        if record is None or not record.verified_answer:
            return {
                "has_reliable_solution": False,
                "canonical_answer": "",
                "explanation": "",
                "answer_record_id": None,
                "learning_item_id": learning_item_id,
            }
        return {
            "has_reliable_solution": True,
            "canonical_answer": record.verified_answer,
            "explanation": record.explanation or "",
            "answer_record_id": record.id,
            "learning_item_id": learning_item_id,
        }

    def has_reliable_linked_solution(self, item_id: int | str) -> bool:
        return bool(self.get_linked_solution(item_id).get("has_reliable_solution"))

    def submit_answer(self, problem_id: int | str, selected_answer: str, *, user_id: str = "local") -> Dict[str, Any]:
        learning_item_id = self._learning_item_id_from_public_id(problem_id)
        if learning_item_id is None:
            raise ValueError(f"Unsupported learning item id: {problem_id}")
        item = self.learning_repository.get(learning_item_id)
        if item is None:
            raise ValueError(f"Learning item not found: {problem_id}")

        choices = item.to_dict().get("choices") or []
        solution = self.get_linked_solution(problem_id)
        normalized_selected = _normalize_answer(selected_answer, choices)
        correct_answer = solution.get("canonical_answer") or ""
        normalized_correct = _normalize_answer(correct_answer, choices) if correct_answer else ""

        if not solution.get("has_reliable_solution"):
            status = "unverified"
            is_correct = None
            persisted_correct_answer = None
        else:
            is_correct = normalized_selected == normalized_correct and normalized_selected != ""
            status = "correct" if is_correct else "incorrect"
            persisted_correct_answer = correct_answer

        submission = self.learning_repository.add_answer_submission(
            user_id=user_id,
            learning_item_id=learning_item_id,
            selected_answer=selected_answer,
            normalized_selected_answer=normalized_selected,
            correct_answer=persisted_correct_answer,
            status=status,
            is_correct=is_correct,
        )
        self.repository.session.flush()
        return _submission_result(
            submission_id=submission.id,
            learning_item_id=learning_item_id,
            status=status,
            selected_answer=normalized_selected or selected_answer,
            correct_answer=correct_answer if solution.get("has_reliable_solution") else "",
            explanation_available=bool(solution.get("explanation")),
            is_correct=is_correct,
        )

    def get_answer_state(self, problem_id: int | str, *, user_id: str = "local") -> Dict[str, Any]:
        learning_item_id = self._learning_item_id_from_public_id(problem_id)
        if learning_item_id is None:
            return _empty_answer_state(None)
        submission = self.learning_repository.latest_answer_submission(user_id=user_id, learning_item_id=learning_item_id)
        solution = self.get_linked_solution(problem_id)
        if submission is None:
            state = _empty_answer_state(learning_item_id)
            state["verified"] = bool(solution.get("has_reliable_solution"))
            state["explanation_available"] = bool(solution.get("explanation"))
            return state
        return {
            "learning_item_id": learning_item_id,
            "submission_id": submission.id,
            "status": submission.status,
            "selected_answer": submission.normalized_selected_answer or submission.selected_answer,
            "raw_selected_answer": submission.selected_answer,
            "verified": submission.status in {"correct", "incorrect"},
            "is_correct": None if submission.is_correct is None else bool(submission.is_correct),
            "correct_answer": submission.correct_answer or "",
            "explanation_available": bool(solution.get("explanation")),
            "submitted_at": submission.submitted_at,
        }

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

    def generate_similar_problem(self, problem_id: int | str) -> Dict[str, Any]:
        learning_item_id = self._learning_item_id_from_public_id(problem_id)
        if learning_item_id is not None:
            return LearningSourceService(self.repository.session).generate_similar_problem(learning_item_id)
        problem = self.repository.get_problem(problem_id)
        if problem is None:
            raise ValueError(f"Problem not found: {problem_id}")
        payload = self._problem_to_dict(problem)
        concept = (payload.get("tags") or [payload.get("category") or "core idea"])[0]
        question = _rewrite_demo_question(payload.get("description", ""), concept)
        choices = _demo_choices(payload)
        return {
            "title": f"Similar Practice: {payload.get('title', 'Problem')}",
            "label": "AI-generated",
            "difficulty": payload.get("difficulty") or "Unknown",
            "topic": concept,
            "concept": concept,
            "question": question,
            "choices": choices,
            "correct_answer": choices[0],
            "explanation": f"This keeps the same topic and difficulty while changing the details. The intended answer is {choices[0]}.",
            "source_problem_id": payload.get("id"),
        }

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

    def _learning_item_id_from_public_id(self, item_id: int | str) -> int | None:
        if isinstance(item_id, str) and item_id.startswith("learning_item:"):
            raw_id = item_id.removeprefix("learning_item:")
            return int(raw_id) if raw_id.isdigit() else None
        if isinstance(item_id, int):
            problem = self.repository.get_problem(item_id)
            if problem is None:
                return None
            learning_item = self._learning_item_for_problem(problem)
            return learning_item.id if learning_item else None
        return None

    def _learning_item_to_problem_dict(self, item: LearningItem) -> Dict[str, Any]:
        payload = item.to_dict()
        concepts = payload.get("concepts") or []
        metadata = payload.get("metadata") or {}
        category = (concepts[0] if concepts else payload.get("source_type") or "Learning item").title()
        return {
            "id": f"learning_item:{item.id}",
            "title": payload.get("title") or "Untitled learning item",
            "description": payload.get("content") or payload.get("title") or "",
            "category": category,
            "difficulty": payload.get("difficulty") or "Unknown",
            "problem_type": payload.get("question_type") or payload.get("item_type") or "Learning Item",
            "function_name": f"learning_item_{item.id}",
            "starter_code": "",
            "constraints": "",
            "test_cases": [],
            "explanation": payload.get("learning_objective") or "",
            "source_type": "PDF" if payload.get("source_type") == "exam_pdf" else payload.get("source_type"),
            "source_reference": payload.get("original_reference") or payload.get("source_id") or "",
            "tags": concepts,
            "provider": payload.get("provider") or ("PDF import" if payload.get("source_type") == "exam_pdf" else "HintCode"),
            "review_status": "Not reviewed",
            "learning_item": payload,
            "question_number": payload.get("question_number"),
            "question_text": payload.get("content") or "",
            "choices": payload.get("choices") or [],
            "answer_state": "Verified" if payload.get("answer_status") == "verified" else "No answer",
            "source_page": metadata.get("page_number"),
            "source_metadata": metadata,
        }


def _submission_result(
    *,
    submission_id: int,
    learning_item_id: int,
    status: str,
    selected_answer: str,
    correct_answer: str,
    explanation_available: bool,
    is_correct: bool | None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "selected_answer": selected_answer,
        "correct_answer": correct_answer,
        "explanation_available": explanation_available,
        "submission_id": submission_id,
        "learning_item_id": learning_item_id,
        "is_correct": is_correct,
    }


def _empty_answer_state(learning_item_id: int | None) -> Dict[str, Any]:
    return {
        "learning_item_id": learning_item_id,
        "submission_id": None,
        "status": "not_submitted",
        "selected_answer": "",
        "raw_selected_answer": "",
        "verified": False,
        "is_correct": None,
        "correct_answer": "",
        "explanation_available": False,
        "submitted_at": None,
    }


def _normalize_answer(answer: str, choices: list[str]) -> str:
    value = _compact_answer(answer)
    if not value:
        return ""
    parsed_choices = [_parse_choice(choice) for choice in choices]
    for label, text, original in parsed_choices:
        if value == _compact_answer(label):
            return original
        if value == _compact_answer(f"{label}."):
            return original
        if value == _compact_answer(original):
            return original
        if text and value == _compact_answer(text):
            return original
    match = re.match(r"^([A-E])\s*[.)]?\s*(.*)$", str(answer or "").strip(), flags=re.IGNORECASE)
    if match:
        label = match.group(1).upper()
        suffix = _compact_answer(match.group(2))
        for choice_label, text, original in parsed_choices:
            if choice_label == label and (not suffix or suffix == _compact_answer(text)):
                return original
    return str(answer or "").strip()


def _parse_choice(choice: str) -> tuple[str, str, str]:
    original = str(choice or "").strip()
    match = re.match(r"^\s*([A-E])\s*[.)]\s*(.+?)\s*$", original, flags=re.IGNORECASE)
    if not match:
        return "", original, original
    return match.group(1).upper(), match.group(2).strip(), original


def _compact_answer(answer: str) -> str:
    return re.sub(r"[\s.)：:：-]+", "", str(answer or "").strip().lower())

def _rewrite_demo_question(description: str, concept: str) -> str:
    source = str(description or "").strip()
    if not source:
        return f"Solve a new practice problem using {concept}."

    def shift(match: re.Match[str]) -> str:
        return str(int(match.group(0)) + 1)

    rewritten = re.sub(r"\b\d+\b", shift, source)
    if rewritten == source:
        rewritten = f"In a new scenario, {source}"
    return rewritten


def _demo_choices(problem: Dict[str, Any]) -> list[str]:
    if problem.get("test_cases"):
        return [
            "A. Adapt the same reasoning to the changed input",
            "B. Ignore the changed condition",
            "C. Use an unrelated shortcut",
            "D. Stop before checking edge cases",
        ]
    return [
        "A. Apply the same core idea",
        "B. Guess from the wording",
        "C. Ignore the constraints",
        "D. Use an unrelated concept",
    ]

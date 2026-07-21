import json
import random
from pathlib import Path
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from src.models.problem import Problem
from src.models.learning_item import LearningItem


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

    def list_learning_items(self, owner_user_id: str = "local") -> List[LearningItem]:
        return (
            self.session.query(LearningItem)
            .filter(LearningItem.owner_user_id == owner_user_id)
            .order_by(LearningItem.id)
            .all()
        )

    def get_problem(self, problem_id: int) -> Optional[Problem]:
        return self.session.query(Problem).filter(Problem.id == problem_id).one_or_none()

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

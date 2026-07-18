from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.problem import Problem


class ProblemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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

    def list_categories(self) -> List[str]:
        return [row[0] for row in self.session.query(Problem.category).distinct().order_by(Problem.category).all()]

    def list_difficulties(self) -> List[str]:
        return [row[0] for row in self.session.query(Problem.difficulty).distinct().order_by(Problem.difficulty).all()]

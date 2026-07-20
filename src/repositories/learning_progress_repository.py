from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.models.learning_progress import LearningProgress
from src.models.submission import Submission


class LearningProgressRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, problem_id: int, learner_id: str = "default") -> LearningProgress | None:
        return self.session.query(LearningProgress).filter_by(problem_id=problem_id, learner_id=learner_id).one_or_none()

    def save_draft(self, problem_id: int, answer: str, language: str, content_hash: str, learner_id: str = "default") -> LearningProgress:
        record = self.get(problem_id, learner_id) or LearningProgress(problem_id=problem_id, learner_id=learner_id)
        record.draft_answer = answer
        record.programming_language = language
        record.problem_content_hash = content_hash
        record.last_opened_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()
        self.session.add(record)
        self.session.commit()
        return record

    def submit(self, problem_id: int, answer: str, language: str, content_hash: str, status: str, learner_id: str = "default") -> LearningProgress:
        record = self.save_draft(problem_id, answer, language, content_hash, learner_id)
        record.status = status
        record.attempt_count += 1
        record.updated_at = datetime.utcnow()
        self.session.add(Submission(problem_id=problem_id, code=answer, status=status))
        self.session.commit()
        return record

    def touch(self, problem_id: int, content_hash: str, learner_id: str = "default") -> LearningProgress:
        record = self.get(problem_id, learner_id) or LearningProgress(problem_id=problem_id, learner_id=learner_id, problem_content_hash=content_hash)
        record.last_opened_at = datetime.utcnow()
        self.session.add(record)
        self.session.commit()
        return record

    def last_opened_problem_id(self, learner_id: str = "default") -> int | None:
        record = self.session.query(LearningProgress).filter_by(learner_id=learner_id).order_by(LearningProgress.last_opened_at.desc()).first()
        return record.problem_id if record else None

    def completed_count(self, learner_id: str = "default") -> int:
        return self.session.query(LearningProgress).filter_by(learner_id=learner_id, status="completed").count()

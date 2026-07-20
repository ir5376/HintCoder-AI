from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models.learning_item import (
    AnswerRecord,
    ExamSource,
    KnowledgeEntry,
    LearningArtifact,
    LearningAttempt,
    LearningHistory,
    LearningItem,
    LearningReviewQueue,
    PassageGroup,
    ProviderSubmissionResult,
    UserProfile,
    XpEvent,
    dumps,
)
from src.services.learning_source_parser import ExamImportPreview, ParsedLearningItem


class LearningItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_user(self, user_id: str = "local", display_name: str = "Local Learner") -> UserProfile:
        user = self.session.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
        if user is None:
            user = UserProfile(user_id=user_id, display_name=display_name)
            self.session.add(user)
            self.session.flush()
        return user

    def create_exam_source(
        self,
        preview: ExamImportPreview,
        *,
        owner_user_id: str,
        question_pdf_name: str,
        answer_pdf_name: str = "",
    ) -> ExamSource:
        source = ExamSource(
            owner_user_id=owner_user_id,
            exam_title=preview.exam_title,
            subject=preview.subject,
            year=preview.year,
            question_pdf_name=question_pdf_name,
            answer_pdf_name=answer_pdf_name,
            answer_status="verified" if preview.report.get("answers_matched", 0) else "unavailable",
            import_report_json=dumps(preview.report),
        )
        self.session.add(source)
        self.session.flush()
        return source

    def add_passage_groups(self, exam_source_id: int, passages: list[dict[str, Any]]) -> list[PassageGroup]:
        groups = []
        seen: set[str] = set()
        for passage in passages:
            identifier = str(passage.get("group_identifier") or passage.get("id") or "").strip()
            text = str(passage.get("passage_text") or passage.get("text") or "").strip()
            if not identifier or not text or identifier in seen:
                continue
            seen.add(identifier)
            group = PassageGroup(
                exam_source_id=exam_source_id,
                group_identifier=identifier,
                passage_text=text,
                page_number=passage.get("page_number"),
                metadata_json=dumps(passage.get("metadata", {})),
            )
            self.session.add(group)
            groups.append(group)
        self.session.flush()
        return groups

    def add_answer_records(
        self,
        exam_source_id: int,
        answers: list,
        *,
        subject: str = "",
        matched_items_by_question: dict[str, int] | None = None,
    ) -> list[AnswerRecord]:
        matched_items_by_question = matched_items_by_question or {}
        records = []
        for answer in answers:
            record = AnswerRecord(
                exam_source_id=exam_source_id,
                subject=subject,
                question_number=str(answer.question_number),
                verified_answer=str(answer.official_answer),
                explanation=str(answer.explanation or ""),
                page_number=answer.page_number,
                matched_learning_item_id=matched_items_by_question.get(str(answer.question_number)),
            )
            self.session.add(record)
            records.append(record)
        self.session.flush()
        return records

    def upsert_learning_item(self, parsed: ParsedLearningItem) -> LearningItem:
        existing = self._find_existing(parsed)
        values = {
            "owner_user_id": parsed.owner_user_id,
            "source_type": parsed.source_type,
            "source_id": parsed.source_id,
            "provider": parsed.provider,
            "provider_problem_id": parsed.provider_problem_id,
            "subject": parsed.subject,
            "exam_name": parsed.exam_name,
            "year": parsed.year,
            "question_number": parsed.question_number,
            "title": parsed.title,
            "content": parsed.content,
            "choices_json": dumps(parsed.choices),
            "verified_answer": parsed.verified_answer,
            "inferred_answer": parsed.inferred_answer,
            "answer_status": parsed.answer_status,
            "explanation": parsed.explanation,
            "concepts_json": dumps(parsed.concepts),
            "difficulty": parsed.difficulty or "Unknown",
            "original_reference": parsed.original_url,
            "question_type": parsed.question_type,
            "learning_objective": parsed.learning_objective,
            "metadata_json": dumps(parsed.metadata),
            "updated_at": datetime.utcnow(),
        }
        if existing is None:
            item = LearningItem(**values)
            self.session.add(item)
            self.session.flush()
            return item
        for key, value in values.items():
            if key == "verified_answer" and existing.verified_answer and parsed.answer_status != "verified":
                continue
            if key == "answer_status" and existing.answer_status == "verified" and parsed.answer_status != "verified":
                continue
            setattr(existing, key, value)
        self.session.flush()
        return existing

    def add_knowledge(self, learning_item_id: int, concepts: list[str], *, source: str) -> list[KnowledgeEntry]:
        entries = []
        for concept in concepts[:5]:
            entry = KnowledgeEntry(learning_item_id=learning_item_id, concept=concept, source=source, metadata_json=dumps({}))
            self.session.add(entry)
            entries.append(entry)
        self.session.flush()
        return entries

    def add_artifact(self, learning_item_id: int, artifact_type: str, content: dict[str, Any]) -> LearningArtifact:
        artifact = LearningArtifact(learning_item_id=learning_item_id, artifact_type=artifact_type, content_json=dumps(content))
        self.session.add(artifact)
        self.session.flush()
        return artifact

    def schedule_reviews(
        self,
        learning_item_id: int,
        *,
        user_id: str,
        intervals: tuple[int, ...] = (1, 3, 7, 30),
    ) -> list[LearningReviewQueue]:
        reviews = []
        for interval in intervals:
            review = LearningReviewQueue(user_id=user_id, learning_item_id=learning_item_id, interval_days=interval, status="pending")
            self.session.add(review)
            reviews.append(review)
        self.session.flush()
        return reviews

    def add_history(self, learning_item_id: int | None, event_type: str, payload: dict[str, Any], *, user_id: str = "local") -> LearningHistory:
        event = LearningHistory(user_id=user_id, learning_item_id=learning_item_id, event_type=event_type, payload_json=dumps(payload))
        self.session.add(event)
        self.session.flush()
        return event

    def add_xp_event(
        self,
        *,
        user_id: str,
        event_type: str,
        points: int,
        learning_item_id: int | None,
        idempotency_key: str,
    ) -> XpEvent:
        existing = (
            self.session.query(XpEvent)
            .filter(XpEvent.user_id == user_id, XpEvent.idempotency_key == idempotency_key)
            .one_or_none()
        )
        if existing is not None:
            return existing
        event = XpEvent(
            user_id=user_id,
            event_type=event_type,
            points=points,
            learning_item_id=learning_item_id,
            idempotency_key=idempotency_key,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def create_attempt(
        self,
        *,
        user_id: str,
        provider: str,
        provider_problem_id: str,
        learning_item_id: int | None = None,
        language: str = "",
        source_code_hash: str = "",
        status: str = "pending",
    ) -> LearningAttempt:
        attempt = LearningAttempt(
            user_id=user_id,
            provider=provider,
            provider_problem_id=provider_problem_id,
            learning_item_id=learning_item_id,
            language=language,
            source_code_hash=source_code_hash,
            status=status,
        )
        self.session.add(attempt)
        self.session.flush()
        return attempt

    def latest_pending_attempt(
        self,
        *,
        user_id: str,
        provider: str,
        provider_problem_id: str,
        source_code_hash: str = "",
    ) -> LearningAttempt | None:
        query = self.session.query(LearningAttempt).filter(
            LearningAttempt.user_id == user_id,
            LearningAttempt.provider == provider,
            LearningAttempt.provider_problem_id == provider_problem_id,
            LearningAttempt.status == "pending",
        )
        if source_code_hash:
            query = query.filter(LearningAttempt.source_code_hash == source_code_hash)
        return query.order_by(LearningAttempt.created_at.desc(), LearningAttempt.id.desc()).first()

    def add_submission_result(
        self,
        *,
        user_id: str,
        attempt_id: int | None,
        provider: str,
        provider_problem_id: str,
        problem_url: str,
        language: str,
        source_code_hash: str,
        raw_status: str,
        normalized_status: str,
        submitted_at: datetime,
    ) -> ProviderSubmissionResult:
        existing = (
            self.session.query(ProviderSubmissionResult)
            .filter(
                ProviderSubmissionResult.user_id == user_id,
                ProviderSubmissionResult.provider == provider,
                ProviderSubmissionResult.provider_problem_id == provider_problem_id,
                ProviderSubmissionResult.source_code_hash == source_code_hash,
                ProviderSubmissionResult.normalized_status == normalized_status,
                ProviderSubmissionResult.submitted_at == submitted_at,
            )
            .one_or_none()
        )
        if existing is not None:
            return existing
        result = ProviderSubmissionResult(
            user_id=user_id,
            attempt_id=attempt_id,
            provider=provider,
            provider_problem_id=provider_problem_id,
            problem_url=problem_url,
            language=language,
            source_code_hash=source_code_hash,
            raw_status=raw_status,
            normalized_status=normalized_status,
            submitted_at=submitted_at,
        )
        self.session.add(result)
        self.session.flush()
        return result

    def get(self, learning_item_id: int) -> LearningItem | None:
        return self.session.query(LearningItem).filter(LearningItem.id == learning_item_id).one_or_none()

    def _find_existing(self, parsed: ParsedLearningItem) -> LearningItem | None:
        if parsed.provider and parsed.provider_problem_id:
            return (
                self.session.query(LearningItem)
                .filter(
                    LearningItem.owner_user_id == parsed.owner_user_id,
                    LearningItem.provider == parsed.provider,
                    LearningItem.provider_problem_id == parsed.provider_problem_id,
                )
                .one_or_none()
            )
        if parsed.source_id and parsed.question_number:
            return (
                self.session.query(LearningItem)
                .filter(
                    LearningItem.owner_user_id == parsed.owner_user_id,
                    LearningItem.source_id == parsed.source_id,
                    LearningItem.question_number == parsed.question_number,
                )
                .one_or_none()
            )
        return None

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.models.problem import Problem
from src.repositories.learning_item_repository import LearningItemRepository
from src.services.learning_engine_service import LearningEngineService
from src.services.learning_source_parser import ExamSourceParser, NotesParser, PdfParser, ProviderUrlParser


class LearningSourceService:
    def __init__(self, session: Session) -> None:
        self.repository = LearningItemRepository(session)
        self.engine = LearningEngineService(self.repository)
        self.provider_url_parser = ProviderUrlParser()
        self.pdf_parser = PdfParser()
        self.exam_source_parser = ExamSourceParser()
        self.notes_parser = NotesParser()

    def import_provider_url(self, url: str, *, title: str = "", difficulty: str = "", owner_user_id: str = "local") -> dict[str, Any]:
        self.repository.get_or_create_user(owner_user_id)
        parsed = self.provider_url_parser.parse(url, title=title, difficulty=difficulty, owner_user_id=owner_user_id)
        return self._store_and_process(parsed)

    def import_pdf(self, filename: str, data: bytes | str, *, title: str = "", owner_user_id: str = "local") -> list[dict[str, Any]]:
        self.repository.get_or_create_user(owner_user_id)
        parsed_items = self.pdf_parser.parse(filename, data, title=title, owner_user_id=owner_user_id)
        return [self._store_and_process(parsed) for parsed in parsed_items]

    def preview_exam_source(
        self,
        *,
        question_pdf_name: str,
        question_pdf: bytes | str,
        answer_pdf_name: str = "",
        answer_pdf: bytes | str | None = None,
        owner_user_id: str = "local",
        title: str = "",
    ) -> dict[str, Any]:
        preview = self.exam_source_parser.preview(
            question_pdf_name=question_pdf_name,
            question_pdf=question_pdf,
            answer_pdf_name=answer_pdf_name,
            answer_pdf=answer_pdf,
            owner_user_id=owner_user_id,
            title=title,
        )
        return {
            "exam_title": preview.exam_title,
            "subject": preview.subject,
            "year": preview.year,
            "questions": [question.__dict__ for question in preview.questions],
            "answers": [answer.__dict__ for answer in preview.answers],
            "passages": [passage.__dict__ for passage in preview.passages],
            "report": preview.report,
        }

    def preview_import(self, **kwargs: Any) -> dict[str, Any]:
        return self.preview_exam_source(**kwargs)

    def confirm_import(self, **kwargs: Any) -> dict[str, Any]:
        return self.import_exam_source(**kwargs)

    def import_exam_source(
        self,
        *,
        question_pdf_name: str,
        question_pdf: bytes | str,
        answer_pdf_name: str = "",
        answer_pdf: bytes | str | None = None,
        owner_user_id: str = "local",
        title: str = "",
    ) -> dict[str, Any]:
        self.repository.get_or_create_user(owner_user_id)
        preview = self.exam_source_parser.preview(
            question_pdf_name=question_pdf_name,
            question_pdf=question_pdf,
            answer_pdf_name=answer_pdf_name,
            answer_pdf=answer_pdf,
            owner_user_id=owner_user_id,
            title=title,
        )
        exam_source = self.repository.create_exam_source(
            preview,
            owner_user_id=owner_user_id,
            question_pdf_name=question_pdf_name,
            answer_pdf_name=answer_pdf_name,
        )
        self.repository.add_passage_groups(
            exam_source.id,
            [
                {
                    "group_identifier": passage.group_identifier,
                    "passage_text": passage.passage_text,
                    "page_number": passage.page_number,
                    "metadata": {**passage.metadata, "question_numbers": passage.question_numbers},
                }
                for passage in preview.passages
            ],
        )
        imported = []
        matched_items_by_question: dict[str, int] = {}
        for parsed in preview.questions:
            stored = self._store_and_process(parsed, commit=False)
            imported.append(stored)
            matched_items_by_question[str(parsed.question_number)] = int(stored["learning_item"]["id"])
        self.repository.add_answer_records(
            exam_source.id,
            preview.answers,
            subject=preview.subject,
            matched_items_by_question=matched_items_by_question,
        )
        self.repository.add_history(None, "exam_source_imported", preview.report, user_id=owner_user_id)
        self.repository.session.commit()
        return {"exam_source_id": exam_source.id, "import_report": preview.report, "items": imported}

    def import_notes(self, notes: str, *, title: str = "", owner_user_id: str = "local") -> dict[str, Any]:
        self.repository.get_or_create_user(owner_user_id)
        parsed = self.notes_parser.parse(notes, title=title, owner_user_id=owner_user_id)
        return self._store_and_process(parsed)

    def generate_similar_problem(self, learning_item_id: int) -> dict[str, Any]:
        return self.engine.generate_similar_problem(learning_item_id)

    def _store_and_process(self, parsed, *, commit: bool = True) -> dict[str, Any]:
        item = self.repository.upsert_learning_item(parsed)
        self.repository.add_knowledge(item.id, parsed.concepts, source=parsed.source_type)
        self.repository.add_history(
            item.id,
            "learning_source_imported",
            {
                "source_type": parsed.source_type,
                "provider": parsed.provider,
                "provider_problem_id": parsed.provider_problem_id,
                "original_url": parsed.original_url,
            },
        )
        artifacts = self.engine.process_learning_item(item)
        problem = self._sync_problem_detail_record(item)
        if commit:
            self.repository.session.commit()
        return {"learning_item": item.to_dict(), "problem_id": problem.id, "artifacts": artifacts}

    def _sync_problem_detail_record(self, item) -> Problem:
        payload = item.to_dict()
        source_reference = f"learning_item:{item.id}"
        existing = (
            self.repository.session.query(Problem)
            .filter(Problem.source_type == "learning_item", Problem.source_reference == source_reference)
            .one_or_none()
        )
        if existing is None:
            problem = Problem(
                title=payload["title"],
                description=payload["content"] or payload["title"],
                category=(payload["concepts"][0] if payload["concepts"] else payload["source_type"]).title(),
                difficulty=payload["difficulty"] or "Unknown",
                problem_type=payload["question_type"] or "Learning Item",
                function_name=f"learning_item_{item.id}",
                starter_code="",
                constraints="",
                test_cases="[]",
                explanation=payload["learning_objective"] or "",
                source_type="learning_item",
                source_reference=source_reference,
                tags="[]",
            )
            self.repository.session.add(problem)
            self.repository.session.flush()
            return problem

        existing.title = payload["title"]
        existing.description = payload["content"] or payload["title"]
        existing.category = (payload["concepts"][0] if payload["concepts"] else payload["source_type"]).title()
        existing.difficulty = payload["difficulty"] or "Unknown"
        existing.problem_type = payload["question_type"] or "Learning Item"
        existing.explanation = payload["learning_objective"] or ""
        self.repository.session.flush()
        return existing

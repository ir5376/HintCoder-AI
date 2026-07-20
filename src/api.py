from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.database import get_session, init_db
from src.services.learning_source_service import LearningSourceService
from src.services.provider_submission_service import ProviderSubmissionService
from src.services.user_progress_service import UserProgressService

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except Exception:  # pragma: no cover - keeps backend modules importable without API deps
    FastAPI = None
    CORSMiddleware = None
    BaseModel = object


if FastAPI is not None:
    api = FastAPI(title="HintCode Learning OS API", version="1.0.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    api = None


class ProviderUrlImportPayload(BaseModel):
    url: str
    title: str = ""
    difficulty: str = ""
    owner_user_id: str = "local"


class PdfImportPayload(BaseModel):
    filename: str = ""
    text: str = ""
    title: str = ""
    owner_user_id: str = "local"


class ExamSourcePayload(BaseModel):
    question_pdf_name: str
    question_text: str
    answer_pdf_name: str = ""
    answer_text: str = ""
    title: str = ""
    owner_user_id: str = "local"


class NotesImportPayload(BaseModel):
    title: str = ""
    notes: str
    owner_user_id: str = "local"


class SimilarProblemPayload(BaseModel):
    learning_item_id: int


class UserPayload(BaseModel):
    user_id: str = "local"
    display_name: str = "Local Learner"


class ActivityPayload(BaseModel):
    user_id: str
    event_type: str
    learning_item_id: int | None = None


class XpPayload(BaseModel):
    user_id: str
    event_type: str
    learning_item_id: int | None = None
    idempotency_key: str


class ProviderSubmissionPayload(BaseModel):
    provider: str
    provider_problem_id: str
    problem_url: str = ""
    language: str = ""
    source_code_hash: str = ""
    raw_status: str = ""
    normalized_status: str = ""
    submitted_at: str = ""
    user_id: str = "local"


class ProviderAttemptPayload(BaseModel):
    user_id: str = "local"
    provider: str
    provider_problem_id: str
    learning_item_id: int | None = None
    language: str = ""
    source_code_hash: str = ""


def _payload_dict(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return dict(payload)


def _service() -> LearningSourceService:
    settings = get_settings()
    init_db(settings.database_url)
    session_context = get_session(settings.database_url)
    session = session_context.__enter__()
    service = LearningSourceService(session)
    service._session_context = session_context  # type: ignore[attr-defined]
    return service


def _close_service(service: LearningSourceService) -> None:
    context = getattr(service, "_session_context", None)
    if context is not None:
        context.__exit__(None, None, None)


if api is not None:

    @api.post("/learning-sources/url")
    def import_provider_url(payload: ProviderUrlImportPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return service.import_provider_url(
                data["url"],
                title=data.get("title", ""),
                difficulty=data.get("difficulty", ""),
                owner_user_id=data.get("owner_user_id", "local"),
            )
        finally:
            _close_service(service)

    @api.post("/learning-sources/pdf")
    def import_pdf(payload: PdfImportPayload) -> list[dict[str, Any]]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return service.import_pdf(
                data.get("filename", ""),
                data.get("text", ""),
                title=data.get("title", ""),
                owner_user_id=data.get("owner_user_id", "local"),
            )
        finally:
            _close_service(service)

    @api.post("/learning-sources/exam/preview")
    def preview_exam_source(payload: ExamSourcePayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return service.preview_exam_source(
                question_pdf_name=data["question_pdf_name"],
                question_pdf=data["question_text"],
                answer_pdf_name=data.get("answer_pdf_name", ""),
                answer_pdf=data.get("answer_text") or None,
                owner_user_id=data.get("owner_user_id", "local"),
                title=data.get("title", ""),
            )
        finally:
            _close_service(service)

    @api.post("/learning-sources/exam/import")
    def import_exam_source(payload: ExamSourcePayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return service.import_exam_source(
                question_pdf_name=data["question_pdf_name"],
                question_pdf=data["question_text"],
                answer_pdf_name=data.get("answer_pdf_name", ""),
                answer_pdf=data.get("answer_text") or None,
                owner_user_id=data.get("owner_user_id", "local"),
                title=data.get("title", ""),
            )
        finally:
            _close_service(service)

    @api.post("/learning-sources/notes")
    def import_notes(payload: NotesImportPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return service.import_notes(data["notes"], title=data.get("title", ""), owner_user_id=data.get("owner_user_id", "local"))
        finally:
            _close_service(service)

    @api.post("/learning-items/similar-problem")
    def generate_similar_problem(payload: SimilarProblemPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return service.generate_similar_problem(int(data["learning_item_id"]))
        finally:
            _close_service(service)

    @api.post("/users")
    def create_user(payload: UserPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return UserProgressService(service.repository.session).get_or_create_user(data["user_id"], data.get("display_name", "Local Learner"))
        finally:
            _close_service(service)

    @api.post("/activity")
    def record_activity(payload: ActivityPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            summary = UserProgressService(service.repository.session).record_activity(
                user_id=data["user_id"],
                event_type=data["event_type"],
                learning_item_id=data.get("learning_item_id"),
            )
            service.repository.session.commit()
            return summary.__dict__
        finally:
            _close_service(service)

    @api.post("/xp")
    def award_xp(payload: XpPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return UserProgressService(service.repository.session).award_xp(
                user_id=data["user_id"],
                event_type=data["event_type"],
                learning_item_id=data.get("learning_item_id"),
                idempotency_key=data["idempotency_key"],
            )
        finally:
            _close_service(service)

    @api.get("/leaderboard")
    def leaderboard(mode: str = "weekly_xp") -> list[dict[str, Any]]:
        service = _service()
        try:
            return UserProgressService(service.repository.session).leaderboard(mode=mode)
        finally:
            _close_service(service)

    @api.post("/provider-submissions")
    def provider_submission_result(payload: ProviderSubmissionPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return ProviderSubmissionService(service.repository.session).handle_submission_result(
                data,
                user_id=data.get("user_id", "local"),
            )
        finally:
            _close_service(service)

    @api.post("/provider-attempts")
    def create_provider_attempt(payload: ProviderAttemptPayload) -> dict[str, Any]:
        data = _payload_dict(payload)
        service = _service()
        try:
            return ProviderSubmissionService(service.repository.session).create_pending_attempt(
                user_id=data.get("user_id", "local"),
                provider=data["provider"],
                provider_problem_id=data["provider_problem_id"],
                learning_item_id=data.get("learning_item_id"),
                language=data.get("language", ""),
                source_code_hash=data.get("source_code_hash", ""),
            )
        finally:
            _close_service(service)

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.config import get_settings
from src.content_modules.registry import ContentModuleRegistry
from src.database import get_engine, init_db
from src.learning_engine.engine import LearningEngine
from src.execution_engine.trace import PythonExecutionTracer
from src.services.learning_coach_service import LearningCoachService
from src.services.provider_service import ProviderService

settings = get_settings()
init_db(settings.database_url)

api = FastAPI(title="Nextep AI Learning Engine", version="1.0.0")


def get_db() -> Session:
    engine = get_engine(settings.database_url)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class SolvedProblemPayload(BaseModel):
    mode: str = "learning"
    content_module: str = "coding"
    content_id: str | None = None
    problem_id: int | None = None
    problem_title: str | None = None
    problem_url: str | None = None
    external_problem_title: str | None = None
    external_problem_url: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    language: str | None = None
    programming_language: str | None = None
    algorithm_choice: str | None = None
    solving_time_seconds: int | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    thinking_progress: float | None = Field(default=None, ge=0, le=1)
    hints_used: int = Field(default=0, ge=0)
    hint_level_used: int | None = Field(default=None, ge=0, le=4)
    solved: bool = True
    implementation_mistakes: list[str] = Field(default_factory=list)
    conceptual_mistakes: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    reasoning_notes: str | None = None
    coach_action: str | None = None
    coach_question: str | None = None
    exam_timer_seconds: int | None = Field(default=None, ge=0)
    exam_hints_available: bool | None = None
    exam_hint_penalty_enabled: bool | None = None
    exam_hint_penalty_points: float | None = Field(default=None, ge=0)
    exam_base_score: float | None = Field(default=None, ge=0, le=100)


class CompleteReviewPayload(BaseModel):
    confidence: float | None = Field(default=None, ge=0, le=1)


class ProviderImportPayload(BaseModel):
    problem_title: str
    problem_url: str = ""
    language: str | None = None
    description: str | None = None
    difficulty: str | None = None
    topic: str | None = None
    provider_problem_id: str | None = None


class SubmissionSyncPayload(BaseModel):
    provider_problem_id: str
    provider_submission_id: str | None = None
    content_id: str | None = None
    status: str = "unknown"
    language: str = "Python"
    code: str = ""
    runtime_ms: int | None = None
    memory_kb: int | None = None
    submitted_at: str | None = None


class PythonTracePayload(BaseModel):
    code: str
    stdin: str = ""


@api.get("/dashboard")
def dashboard(session: Session = Depends(get_db)) -> dict[str, Any]:
    return LearningEngine(session).dashboard()


@api.get("/content-modules")
def content_modules() -> dict[str, Any]:
    return {"modules": ContentModuleRegistry().list_modules()}


@api.get("/providers")
def providers(session: Session = Depends(get_db)) -> dict[str, Any]:
    return {"providers": ProviderService(session).list_providers()}


@api.post("/providers/{provider_id}/import-problem")
def import_provider_problem(
    provider_id: str,
    payload: ProviderImportPayload,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    return ProviderService(session).import_problem(provider_id, payload_data)


@api.post("/providers/{provider_id}/sync-submission")
def sync_provider_submission(
    provider_id: str,
    payload: SubmissionSyncPayload,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    return ProviderService(session).sync_submission(provider_id, payload_data)


@api.post("/execution/python/trace")
def python_execution_trace(payload: PythonTracePayload) -> dict[str, Any]:
    return PythonExecutionTracer().run(payload.code, stdin=payload.stdin).to_dict()


@api.get("/content-modules/{module_id}/content")
def module_content(module_id: str) -> dict[str, Any]:
    registry = ContentModuleRegistry()
    try:
        module = registry.get(module_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Content module not found") from exc
    if not hasattr(module, "list_content"):
        return {"module_id": module_id, "content": []}
    return {"module_id": module_id, "content": [item.__dict__ for item in module.list_content()]}


@api.get("/profile")
def profile(session: Session = Depends(get_db)) -> dict[str, Any]:
    return LearningCoachService(session).get_profile()


@api.get("/thought-profile")
def thought_profile(session: Session = Depends(get_db)) -> dict[str, Any]:
    return LearningCoachService(session).get_thought_profile()


@api.get("/review")
def review(status: str | None = "pending", session: Session = Depends(get_db)) -> dict[str, Any]:
    return {"reviews": LearningCoachService(session).get_review_queue(status=status)}


@api.post("/review")
def record_solved_problem(payload: SolvedProblemPayload, session: Session = Depends(get_db)) -> dict[str, Any]:
    payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    return LearningCoachService(session).record_solved_problem(payload_data)


@api.post("/review/{review_id}/complete")
def complete_review(
    review_id: int,
    payload: CompleteReviewPayload,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    completed = LearningCoachService(session).complete_review(review_id, confidence=payload.confidence)
    if completed is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return completed


@api.get("/roadmap")
def roadmap(type: str = "7-day", content_module: str = "coding", session: Session = Depends(get_db)) -> dict[str, Any]:
    return LearningCoachService(session).generate_roadmap(type, content_module=content_module)


@api.get("/weekly-report")
def weekly_report(session: Session = Depends(get_db)) -> dict[str, Any]:
    return LearningCoachService(session).generate_weekly_reflection()

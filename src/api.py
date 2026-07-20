from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.services.problem_import_service import ProblemImportService

api = FastAPI(title="HintCode Provider Import API", version="1.0.0")


class ProblemImportPayload(BaseModel):
    provider: str
    problem_id: str = ""
    title: str
    url: str
    difficulty: str = ""
    language: str = ""
    starter_code: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@api.post("/import/problem")
def import_problem(payload: ProblemImportPayload) -> dict[str, Any]:
    payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    imported = ProblemImportService().import_problem(payload_data)
    return {
        "provider": imported.provider,
        "problem_id": imported.problem_id,
        "title": imported.title,
        "url": imported.url,
        "difficulty": imported.difficulty,
        "language": imported.language,
        "starter_code": imported.starter_code,
        "metadata": imported.metadata,
    }

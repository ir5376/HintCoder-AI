from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from src.execution_engine.trace import PythonExecutionTracer
from src.models.learning import ProviderProblem, ProviderSubmission
from src.provider_adapters.registry import ProviderRegistry


class ProviderService:
    def __init__(self, session: Session, registry: ProviderRegistry | None = None) -> None:
        self.session = session
        self.registry = registry or ProviderRegistry()

    def list_providers(self) -> list[dict[str, Any]]:
        return self.registry.list_providers()

    def import_problem(self, provider_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        adapter = self.registry.get(provider_id)
        imported = adapter.import_problem(payload)
        record = (
            self.session.query(ProviderProblem)
            .filter(
                ProviderProblem.provider == imported.provider,
                ProviderProblem.provider_problem_id == imported.provider_problem_id,
            )
            .one_or_none()
        )
        metadata_json = json.dumps(imported.metadata | imported.content.metadata, ensure_ascii=False, default=str)
        if record is None:
            record = ProviderProblem(
                provider=imported.provider,
                provider_problem_id=imported.provider_problem_id,
                content_id=imported.content.id,
                title=imported.content.title,
                source_url=imported.metadata.get("problem_url"),
                language=imported.content.language,
                metadata_json=metadata_json,
            )
            self.session.add(record)
        else:
            record.content_id = imported.content.id
            record.title = imported.content.title
            record.source_url = imported.metadata.get("problem_url")
            record.language = imported.content.language
            record.metadata_json = metadata_json
        self.session.commit()
        return {
            "provider_problem_id": imported.provider_problem_id,
            "content": imported.content.__dict__,
            "metadata": imported.metadata,
        }

    def sync_submission(self, provider_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        adapter = self.registry.get(provider_id)
        synced = adapter.sync_submission(payload)
        trace = None
        if synced.language == "Python" and synced.code:
            trace = PythonExecutionTracer().run(synced.code)

        record = ProviderSubmission(
            provider=synced.provider,
            provider_submission_id=synced.provider_submission_id,
            provider_problem_id=synced.provider_problem_id,
            content_id=payload.get("content_id"),
            status=synced.status,
            language=synced.language,
            code=synced.code,
            runtime_ms=synced.runtime_ms,
            memory_kb=synced.memory_kb,
            trace_json=json.dumps(trace.to_dict() if trace else {}, ensure_ascii=False, default=str),
            metadata_json=json.dumps(synced.metadata, ensure_ascii=False, default=str),
            submitted_at=synced.submitted_at,
        )
        self.session.add(record)
        self.session.commit()
        return {
            "submission_id": record.id,
            "provider_submission_id": synced.provider_submission_id,
            "status": synced.status,
            "language": synced.language,
            "trace": trace.to_dict() if trace else {},
        }

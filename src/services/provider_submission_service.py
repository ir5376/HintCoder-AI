from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.models.learning_item import LearningAttempt
from src.repositories.learning_item_repository import LearningItemRepository
from src.services.provider_adapters import NORMALIZED_STATUSES, get_provider_adapter
from src.services.user_progress_service import UserProgressService


@dataclass(frozen=True)
class SubmissionMessage:
    provider: str
    provider_problem_id: str
    problem_url: str
    language: str
    source_code_hash: str
    raw_status: str
    normalized_status: str
    submitted_at: datetime


class ProviderSubmissionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = LearningItemRepository(session)
        self.progress = UserProgressService(session)

    def create_pending_attempt(
        self,
        *,
        user_id: str = "local",
        provider: str,
        provider_problem_id: str,
        learning_item_id: int | None = None,
        language: str = "",
        source_code_hash: str = "",
    ) -> dict[str, Any]:
        adapter = get_provider_adapter(provider)
        self.repository.get_or_create_user(user_id)
        attempt = self.repository.create_attempt(
            user_id=user_id,
            provider=adapter.provider,
            provider_problem_id=_sanitize_token(provider_problem_id),
            learning_item_id=learning_item_id,
            language=adapter.normalize_language(language),
            source_code_hash=_sanitize_hash(source_code_hash),
        )
        self.progress.record_activity(user_id=user_id, event_type="attempt_submitted", learning_item_id=learning_item_id)
        self.session.commit()
        return _attempt_to_dict(attempt)

    def handle_submission_result(self, payload: dict[str, Any], *, user_id: str = "local") -> dict[str, Any]:
        message = self.validate_message(payload)
        self.repository.get_or_create_user(user_id)
        attempt = self.repository.latest_pending_attempt(
            user_id=user_id,
            provider=message.provider,
            provider_problem_id=message.provider_problem_id,
            source_code_hash=message.source_code_hash,
        )
        if attempt is None and message.source_code_hash:
            attempt = self.repository.latest_pending_attempt(
                user_id=user_id,
                provider=message.provider,
                provider_problem_id=message.provider_problem_id,
            )

        if attempt is not None:
            attempt.status = message.normalized_status
            attempt.language = message.language or attempt.language
            attempt.source_code_hash = message.source_code_hash or attempt.source_code_hash
            attempt.updated_at = datetime.utcnow()

        result = self.repository.add_submission_result(
            user_id=user_id,
            attempt_id=attempt.id if attempt else None,
            provider=message.provider,
            provider_problem_id=message.provider_problem_id,
            problem_url=message.problem_url,
            language=message.language,
            source_code_hash=message.source_code_hash,
            raw_status=message.raw_status,
            normalized_status=message.normalized_status,
            submitted_at=message.submitted_at,
        )

        xp = None
        if message.normalized_status == "accepted" and attempt is not None:
            learning_item_id = attempt.learning_item_id
            xp = self.progress.record_accepted_completion(
                user_id=user_id,
                learning_item_id=learning_item_id,
                provider=message.provider,
                provider_problem_id=message.provider_problem_id,
                source_code_hash=message.source_code_hash,
            )
        elif attempt is not None:
            self.progress.record_activity(
                user_id=user_id,
                event_type="attempt_submitted",
                learning_item_id=attempt.learning_item_id,
            )

        self.session.commit()
        return {
            "submission_result_id": result.id,
            "attempt_id": attempt.id if attempt else None,
            "matched_attempt": attempt is not None,
            "normalized_status": message.normalized_status,
            "xp": xp,
        }

    def validate_message(self, payload: dict[str, Any]) -> SubmissionMessage:
        provider = _sanitize_token(payload.get("provider", "")).lower()
        adapter = get_provider_adapter(provider)
        provider_problem_id = _sanitize_token(payload.get("provider_problem_id", ""))
        if not provider_problem_id:
            raise ValueError("provider_problem_id is required")

        raw_status = _sanitize_text(payload.get("raw_status", ""))
        supplied_normalized = _sanitize_token(payload.get("normalized_status", "")).lower()
        normalized = supplied_normalized if supplied_normalized in NORMALIZED_STATUSES else adapter.normalize_submission_status(raw_status)
        if normalized not in NORMALIZED_STATUSES:
            normalized = "unknown"

        submitted_at = _parse_submitted_at(payload.get("submitted_at"))
        return SubmissionMessage(
            provider=adapter.provider,
            provider_problem_id=provider_problem_id,
            problem_url=_sanitize_url(payload.get("problem_url", "")),
            language=adapter.normalize_language(_sanitize_text(payload.get("language", ""))),
            source_code_hash=_sanitize_hash(payload.get("source_code_hash", "")),
            raw_status=raw_status,
            normalized_status=normalized,
            submitted_at=submitted_at,
        )


def _attempt_to_dict(attempt: LearningAttempt) -> dict[str, Any]:
    return {
        "attempt_id": attempt.id,
        "user_id": attempt.user_id,
        "learning_item_id": attempt.learning_item_id,
        "provider": attempt.provider,
        "provider_problem_id": attempt.provider_problem_id,
        "language": attempt.language,
        "source_code_hash": attempt.source_code_hash,
        "status": attempt.status,
    }


def _sanitize_text(value: Any, *, max_length: int = 1000) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", str(value or "")).strip()[:max_length]


def _sanitize_token(value: Any, *, max_length: int = 255) -> str:
    return re.sub(r"[^A-Za-z0-9_.:/+-]", "", str(value or "").strip())[:max_length]


def _sanitize_hash(value: Any) -> str:
    return re.sub(r"[^A-Fa-f0-9]", "", str(value or "").strip())[:128]


def _sanitize_url(value: Any) -> str:
    text = _sanitize_text(value, max_length=2000)
    if text and not text.startswith(("http://", "https://")):
        return ""
    return text


def _parse_submitted_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value or "").strip()
    if not text:
        return datetime.utcnow()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return datetime.utcnow()

"""Frontend contracts for reviewing links between questions and solutions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class SolutionLinkStatus(str, Enum):
    NO_SOLUTION = "no_solution"
    AUTOMATICALLY_MATCHED = "automatically_matched"
    MANUALLY_CONFIRMED = "manually_confirmed"
    LOW_CONFIDENCE = "low_confidence"


class SolutionSourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class SolutionReviewActionType(str, Enum):
    ATTACH_SOLUTION_PDF = "attach_solution_pdf"
    CONFIRM_MATCH = "confirm_solution_match"
    REJECT_CANDIDATE = "reject_solution_candidate"
    SELECT_SOLUTION = "select_extracted_solution"


@dataclass(frozen=True)
class SolutionReviewAction:
    kind: SolutionReviewActionType
    question_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SolutionCandidateViewModel:
    id: str
    question_number: str
    explanation_snippet: str
    full_solution: str | None = None


@dataclass(frozen=True)
class SolutionLinkReviewViewModel:
    question_id: str
    link_status: SolutionLinkStatus
    source_status: SolutionSourceStatus
    candidate: SolutionCandidateViewModel | None = None
    extracted_solutions: Sequence[SolutionCandidateViewModel] = ()
    confirmed_solution: SolutionCandidateViewModel | None = None
    source_detail: str | None = None


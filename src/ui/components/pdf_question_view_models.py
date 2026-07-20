"""Frontend-only contracts for presenting questions extracted from PDFs.

These types deliberately do not import backend models. An integration layer can
map repository/domain objects into these immutable view models later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class ExtractionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    OCR_REQUIRED = "ocr_required"
    EMPTY = "empty"


class LearningStatus(str, Enum):
    DRAFT = "draft"
    COMPLETED = "completed"
    REVIEW_NEEDED = "review_needed"


class FrontendActionType(str, Enum):
    ANSWER_CHANGED = "answer_changed"
    PREVIOUS_QUESTION = "previous_question"
    NEXT_QUESTION = "next_question"
    EDIT_QUESTION = "edit_question"
    DELETE_QUESTION = "delete_question"
    RESTORE_QUESTION = "restore_question"
    REPROCESS_PDF = "reprocess_pdf"
    REQUEST_HINT = "request_hint"


@dataclass(frozen=True)
class FrontendAction:
    kind: FrontendActionType
    question_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChoiceViewModel:
    id: str
    label: str
    text: str


@dataclass(frozen=True)
class QuestionViewModel:
    id: str
    number: str
    text: str
    document_id: str | None = None
    choices: Sequence[ChoiceViewModel] = ()
    shared_passage: str | None = None
    source_page: int | None = None
    is_uncertain: bool = False
    uncertainty_message: str | None = None
    draft_answer: str = ""


@dataclass(frozen=True)
class QuestionNavigationViewModel:
    current_index: int
    total: int
    has_previous: bool
    has_next: bool


@dataclass(frozen=True)
class ExtractionStateViewModel:
    status: ExtractionStatus
    detail: str | None = None


@dataclass(frozen=True)
class LearningProgressViewModel:
    completed_count: int
    total_count: int
    status: LearningStatus
    is_last_opened: bool = False


@dataclass(frozen=True)
class HintLevelViewModel:
    level: int
    unlocked: bool
    viewed_text: str | None = None
    is_loading: bool = False


@dataclass(frozen=True)
class HintPanelViewModel:
    levels: Sequence[HintLevelViewModel]
    has_reliable_solution: bool = True


@dataclass(frozen=True)
class DeletedQuestionViewModel:
    id: str
    number: str
    text: str


class PdfQuestionWorkspaceData(Protocol):
    """Minimum data shape expected by the composed PDF question workspace."""

    question: QuestionViewModel
    navigation: QuestionNavigationViewModel
    extraction: ExtractionStateViewModel
    progress: LearningProgressViewModel
    hints: HintPanelViewModel
    deleted_questions: Sequence[DeletedQuestionViewModel]

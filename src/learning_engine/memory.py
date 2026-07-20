from __future__ import annotations

from typing import Protocol

from src.learning_engine.domain import MemoryNote


class MemoryNoteRepository(Protocol):
    def save(self, note: MemoryNote) -> MemoryNote:
        """Persist a memory note generated from a learning problem."""

    def list_by_problem(self, problem_id: int | str) -> list[MemoryNote]:
        """Return memory notes linked to a problem."""


class FlashcardGenerator(Protocol):
    def generate_from_concepts(self, concepts: list[str]) -> list[dict]:
        """Future interface for concept-to-flashcard generation."""


class QuizGenerator(Protocol):
    def generate_from_flashcards(self, flashcards: list[dict]) -> list[dict]:
        """Future interface for flashcard-to-quiz generation."""


class MemoryReviewScheduler(Protocol):
    def schedule_from_quiz(self, problem_id: int | str, quiz_items: list[dict]) -> list[dict]:
        """Future interface for connecting quiz outcomes to the review queue."""

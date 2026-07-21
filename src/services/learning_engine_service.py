from __future__ import annotations

import re
from typing import Any

from src.models.learning_item import LearningItem
from src.repositories.learning_item_repository import LearningItemRepository
from src.services.subject_profiles import get_subject_profile


class LearningEngineService:
    """Backend-only learning engine that creates study artifacts for a LearningItem."""

    def __init__(self, repository: LearningItemRepository) -> None:
        self.repository = repository

    def process_learning_item(self, item: LearningItem) -> dict[str, Any]:
        payload = item.to_dict()
        profile = get_subject_profile(payload.get("subject", ""), payload.get("question_type", ""))
        concepts = payload["concepts"]
        primary_concept = concepts[0] if concepts else "core idea"
        objective = payload["learning_objective"] or f"Understand and apply {primary_concept}."

        artifacts = {
            "ai_hint": {
                "hint": f"{profile.hint_generation_instructions} Focus first on {primary_concept}.",
                "level": 1,
                "subject_profile": profile.id,
            },
            "memory_cards": [
                {
                    "front": f"What should you remember about {primary_concept}?",
                    "back": objective,
                    "rule": profile.memory_extraction_rules[0],
                }
            ],
            "flashcards": [
                {
                    "question": f"Define or explain {primary_concept}.",
                    "answer": objective,
                    "answer_format": profile.answer_format,
                }
            ],
            "quiz": {
                "profile": profile.id,
                "ox": [
                    {
                        "question": f"This item mainly reviews {primary_concept}.",
                        "answer": True,
                    }
                ],
                "fill_blank": [
                    {
                        "question": f"The key concept is ____.",
                        "answer": primary_concept,
                    }
                ],
                "multiple_choice": [
                    {
                        "question": "Which concept should you review first?",
                        "choices": _multiple_choice(primary_concept),
                        "answer": primary_concept,
                    }
                ],
            },
        }

        for artifact_type, content in artifacts.items():
            self.repository.add_artifact(item.id, artifact_type, content)
        self.repository.schedule_reviews(item.id, user_id=payload["owner_user_id"])
        self.repository.add_history(
            item.id,
            "learning_item_processed",
            {"artifact_types": list(artifacts), "subject_profile": profile.id},
            user_id=payload["owner_user_id"],
        )
        return artifacts

    def generate_similar_problem(self, learning_item_id: int) -> dict[str, Any]:
        item = self.repository.get(learning_item_id)
        if item is None:
            raise ValueError("LearningItem not found")

        payload = item.to_dict()
        concepts = payload["concepts"]
        concept = concepts[0] if concepts else "core idea"
        profile = get_subject_profile(payload.get("subject", ""), payload.get("question_type", ""))
        original_question = payload.get("content") or payload.get("title") or ""
        original_choices = payload.get("choices") or []
        generated_question = _rewrite_question(original_question, concept=concept)
        generated_choices = _rewrite_choices(original_choices)
        correct_answer = generated_choices[0] if generated_choices else "Review the transformed condition."
        similar_problem = {
            "title": f"Similar Practice: {payload['title']}",
            "label": "AI-generated",
            "difficulty": payload["difficulty"],
            "topic": concept,
            "concept": concept,
            "learning_objective": payload["learning_objective"],
            "constraints": list(profile.similar_question_constraints),
            "question": generated_question,
            "choices": generated_choices,
            "correct_answer": correct_answer,
            "explanation": _short_similar_explanation(concept, correct_answer),
            "source_learning_item_id": learning_item_id,
        }
        _validate_similar_problem(similar_problem, original_question)
        self.repository.add_artifact(learning_item_id, "similar_problem", similar_problem)
        self.repository.add_history(
            learning_item_id,
            "similar_problem_generated",
            {"concept": concept, "label": "AI-generated"},
            user_id=payload["owner_user_id"],
        )
        return similar_problem


def _multiple_choice(answer: str) -> list[str]:
    choices = [answer, "unrelated syntax", "random memorization", "guessing"]
    deduped = []
    for choice in choices:
        if choice not in deduped:
            deduped.append(choice)
    return deduped


def _rewrite_question(question: str, *, concept: str) -> str:
    source = str(question or "").strip()
    if not source:
        return f"New practice problem: apply {concept} in a slightly different scenario."
    rewritten = _shift_numbers(source)
    rewritten = re.sub(r"\boriginal\b", "new", rewritten, flags=re.IGNORECASE)
    if rewritten == source:
        rewritten = f"In a new scenario, {source}"
    return rewritten


def _shift_numbers(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(0)
        try:
            number = int(value)
        except ValueError:
            return value
        return str(number + 1 if number >= 0 else number - 1)

    return re.sub(r"\b\d+\b", replace, text)


def _rewrite_choices(choices: list[str]) -> list[str]:
    if not choices:
        return ["A. New condition works", "B. The condition is unrelated", "C. The result is impossible", "D. More information is required"]
    rewritten = []
    for index, choice in enumerate(choices):
        shifted = _shift_numbers(str(choice))
        if shifted == str(choice):
            shifted = f"{choice} (modified)" if index == 0 else str(choice)
        rewritten.append(shifted)
    return _dedupe_choices(rewritten)


def _dedupe_choices(choices: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for choice in choices:
        normalized = re.sub(r"\s+", " ", str(choice or "")).strip()
        if normalized and normalized.casefold() not in seen:
            seen.add(normalized.casefold())
            deduped.append(normalized)
    return deduped


def _short_similar_explanation(concept: str, correct_answer: str) -> str:
    return f"The transformed problem keeps the same core concept: {concept}. The intended answer is {correct_answer} because the modified details preserve the same reasoning pattern."


def _validate_similar_problem(problem: dict[str, Any], original_question: str) -> None:
    if not problem.get("question") or not str(problem["question"]).strip():
        raise ValueError("Generated problem is empty.")
    if str(problem.get("question", "")).strip() == str(original_question or "").strip():
        raise ValueError("Generated problem copied the original question.")
    if not problem.get("choices"):
        raise ValueError("Generated problem has no choices.")
    if not problem.get("correct_answer"):
        raise ValueError("Generated problem has no correct answer.")
    if not problem.get("explanation"):
        raise ValueError("Generated problem has no explanation.")

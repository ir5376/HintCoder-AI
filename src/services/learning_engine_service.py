from __future__ import annotations

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
        similar_problem = {
            "title": f"Similar Practice: {payload['title']}",
            "label": "AI-generated",
            "difficulty": payload["difficulty"],
            "concept": concept,
            "learning_objective": payload["learning_objective"],
            "constraints": list(profile.similar_question_constraints),
            "question": (
                f"Create one solution plan for a new problem that uses {concept} at "
                f"{payload['difficulty']} difficulty. Explain the key decision before solving."
            ),
        }
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

from __future__ import annotations

from typing import Any

from src.learning_engine.content import LearningContent
from src.learning_engine.templates import StarterTemplateRegistry


class CodingModule:
    module_id = "coding"
    display_name = "Coding"

    def __init__(self, template_registry: StarterTemplateRegistry | None = None) -> None:
        self.template_registry = template_registry or StarterTemplateRegistry()

    def to_learning_content(self, item: dict[str, Any], *, language: str | None = None) -> LearningContent:
        selected_language = language or "Python"
        starter_template = item.get("starter_code") if selected_language == "Python" else None
        return LearningContent(
            id=str(item.get("id") or item.get("function_name") or item.get("title", "")),
            title=item.get("title", ""),
            content=item.get("description", ""),
            difficulty=item.get("difficulty", ""),
            topic=item.get("category") or item.get("topic") or "General",
            source=item.get("source_reference") or item.get("source_type") or "Nextep",
            content_type="coding",
            question_type=item.get("problem_type") or "coding_practice",
            answer=item.get("answer") or item.get("function_name") or "",
            metadata={
                "module": self.module_id,
                "problem_id": item.get("id"),
                "description": item.get("description", ""),
                "constraints": item.get("constraints", ""),
                "examples": item.get("test_cases", []),
                "function_name": item.get("function_name", ""),
                "tags": item.get("tags", []),
            },
            coding_template=starter_template or self.template_registry.get_template(selected_language),
            language=selected_language,
        )

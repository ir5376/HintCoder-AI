from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SubjectProfile:
    id: str
    display_name: str
    answer_format: str
    hint_generation_instructions: str
    memory_extraction_rules: tuple[str, ...]
    quiz_generation_rules: tuple[str, ...]
    similar_question_constraints: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "answer_format": self.answer_format,
            "hint_generation_instructions": self.hint_generation_instructions,
            "memory_extraction_rules": list(self.memory_extraction_rules),
            "quiz_generation_rules": list(self.quiz_generation_rules),
            "similar_question_constraints": list(self.similar_question_constraints),
        }


CODING_PROFILE = SubjectProfile(
    id="coding",
    display_name="Coding",
    answer_format="source code and reasoning",
    hint_generation_instructions="Guide algorithm choice, edge cases, complexity, and implementation bugs without revealing final code.",
    memory_extraction_rules=("algorithm", "data structure", "edge case", "common implementation mistake"),
    quiz_generation_rules=("complexity check", "trace small input", "choose algorithm"),
    similar_question_constraints=("same core algorithm", "same difficulty", "same learning objective"),
)

ENGLISH_MULTIPLE_CHOICE_PROFILE = SubjectProfile(
    id="english_multiple_choice",
    display_name="English Multiple Choice",
    answer_format="choice label with evidence from the passage or grammar rule",
    hint_generation_instructions="Guide vocabulary, grammar, elimination, and passage evidence without giving the answer first.",
    memory_extraction_rules=("vocabulary", "grammar pattern", "trap choice", "reading evidence"),
    quiz_generation_rules=("vocabulary hint", "grammar explanation", "wrong choice explanation"),
    similar_question_constraints=("same concept", "same difficulty", "same learning objective", "one question only"),
)

GENERIC_EXAM_PROFILE = SubjectProfile(
    id="generic_exam",
    display_name="Generic Exam",
    answer_format="verified answer or short explanation",
    hint_generation_instructions="Explain the concept, narrow the choices, and point to the missing knowledge without over-revealing.",
    memory_extraction_rules=("concept", "mistake", "keyword", "review fact"),
    quiz_generation_rules=("OX quiz", "fill-in-the-blank", "multiple choice"),
    similar_question_constraints=("same concept", "same difficulty", "same learning objective", "one question only"),
)


PROFILES = {
    "coding": CODING_PROFILE,
    "code": CODING_PROFILE,
    "algorithm": CODING_PROFILE,
    "english": ENGLISH_MULTIPLE_CHOICE_PROFILE,
    "english_multiple_choice": ENGLISH_MULTIPLE_CHOICE_PROFILE,
    "reading": ENGLISH_MULTIPLE_CHOICE_PROFILE,
    "grammar": ENGLISH_MULTIPLE_CHOICE_PROFILE,
    "generic_exam": GENERIC_EXAM_PROFILE,
}


def get_subject_profile(subject: str = "", question_type: str = "") -> SubjectProfile:
    key = str(subject or "").strip().lower().replace(" ", "_")
    type_key = str(question_type or "").strip().lower().replace(" ", "_")
    if key in PROFILES:
        return PROFILES[key]
    if type_key == "coding":
        return CODING_PROFILE
    if key.startswith("english") or "english" in key:
        return ENGLISH_MULTIPLE_CHOICE_PROFILE
    return GENERIC_EXAM_PROFILE

from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from src.config import get_settings
from src.models.hint import HintHistory
from src.models.problem import Problem
from src.services.subject_profiles import get_subject_profile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger(__name__)


@dataclass
class ProblemContext:
    source_platform: str
    source_url: str = ""
    external_problem_id: Optional[str] = None
    title: str = ""
    description: str = ""
    constraints: str = ""
    examples: str = ""
    difficulty: str = ""
    programming_language: str = "Python"
    student_code: str = ""
    execution_result: str = ""
    hint_level: int = 1
    problem_id: Optional[int] = None
    learner_context: str = ""
    subject_profile: str = ""
    previous_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoachingAction:
    key: str
    label: str
    response_style: str
    prompt_instruction: str


COACHING_ACTIONS = {
    "generate_hint": CoachingAction("generate_hint", "Generate Hint", "progressive_hint", "Give a progressive hint."),
    "validate_idea": CoachingAction("validate_idea", "Validate My Idea", "idea_validation", "Validate the learner's idea."),
    "ask_coach": CoachingAction("ask_coach", "Ask My Coach", "interactive_coaching", "Guide without revealing the answer."),
    "explain_concept": CoachingAction("explain_concept", "Explain Concept", "concept_explanation", "Explain the core concept."),
    "explain_algorithm": CoachingAction("explain_algorithm", "Explain Algorithm", "algorithm_explanation", "Explain the algorithmic idea."),
    "complexity_check": CoachingAction("complexity_check", "Complexity Check", "complexity_feedback", "Check time and space complexity."),
    "debug_code": CoachingAction("debug_code", "Debug My Code", "debugging_guidance", "Point to the suspicious area."),
    "review_thinking": CoachingAction("review_thinking", "Review My Thinking", "thinking_review", "Review reasoning and assumptions."),
}


class HintService:
    def __init__(self, session, openai_client: Any | None = None) -> None:
        self.session = session
        self.openai_client = openai_client

    def _get_client(self) -> Any | None:
        if self.openai_client is not None:
            return self.openai_client

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[HintService] GEMINI_API_KEY is missing; using fallback hint.")
            return None

        try:
            from google import genai
        except Exception as exc:
            print(f"[HintService] Google GenAI SDK import failed: {type(exc).__name__}: {exc}")
            return None

        return genai.Client(api_key=api_key)

    def build_problem_context(
        self,
        problem: Problem,
        *,
        student_code: str = "",
        programming_language: str = "Python",
        execution_result: str = "",
        hint_level: int = 1,
        learner_context: str = "",
    ) -> ProblemContext:
        return ProblemContext(
            source_platform="HintCode",
            source_url=problem.source_reference or "",
            external_problem_id=None,
            title=problem.title,
            description=problem.description,
            constraints=problem.constraints or "",
            examples=self._normalize_optional_text(problem.test_cases),
            difficulty=problem.difficulty or "",
            programming_language=programming_language or "Python",
            student_code=student_code or problem.starter_code or "",
            execution_result=execution_result,
            hint_level=hint_level,
            problem_id=problem.id,
            learner_context=learner_context,
            subject_profile=get_subject_profile("Coding", problem.problem_type or "").id,
        )

    def generate_hint(self, context: ProblemContext, hint_level: int | None = None) -> dict[str, Any]:
        level = max(1, min(hint_level if hint_level is not None else context.hint_level or 1, 4))
        raw_response = self._call_gemini(self._build_prompt(context, level))
        hint = self._normalize_hint(raw_response, context, level)
        try:
            self._store_hint_history(context, level, hint)
        except Exception as exc:
            logger.exception(
                "Hint history persistence failed for problem_id=%s source_platform=%s hint_level=%s error_type=%s",
                context.problem_id,
                context.source_platform,
                level,
                type(exc).__name__,
            )
        return {
            "hint": hint,
            "hint_level": level,
            "source_platform": context.source_platform,
            "problem_id": context.problem_id,
            "external_problem_id": context.external_problem_id,
        }

    def coach(
        self,
        context: ProblemContext,
        *,
        action: str = "generate_hint",
        user_question: str = "",
        hint_level: int | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        result = self.generate_hint(context, hint_level=hint_level)
        normalized_action = action if action in COACHING_ACTIONS else "ask_coach"
        response = result["hint"]
        if user_question and normalized_action != "generate_hint":
            response = f"{response} Consider your question: {user_question.strip()}"
        return {
            **result,
            "action": normalized_action,
            "label": COACHING_ACTIONS[normalized_action].label,
            "response": response,
            "hint": response,
        }

    def list_hint_history(self) -> list[dict[str, Any]]:
        records = self.session.query(HintHistory).order_by(HintHistory.created_at.desc()).all()
        return [
            {
                "id": record.id,
                "source_platform": getattr(record, "source_platform", "HintCode"),
                "external_problem_id": getattr(record, "external_problem_id", None),
                "problem_id": getattr(record, "problem_id", None),
                "programming_language": getattr(record, "programming_language", "Python"),
                "student_code": getattr(record, "student_code", ""),
                "hint_level": record.hint_level,
                "generated_hint": getattr(record, "generated_hint", None) or record.hint_text,
                "created_at": record.created_at,
            }
            for record in records
        ]

    def _build_prompt(self, context: ProblemContext, hint_level: int) -> str:
        level_instruction = {
            1: "Level 1: clarify the key concept and ask one guiding question.",
            2: "Level 2: suggest the algorithmic direction and useful data structures without pseudocode.",
            3: "Level 3: identify likely issues and provide a tiny partial pseudocode fragment.",
            4: "Level 4: outline a nearly complete strategy while avoiding final complete code.",
        }[hint_level]
        return "\n".join(
            [
                "You are an English-speaking coding tutor.",
                "Guide the student's reasoning through progressive hints.",
                "Never provide the complete solution or a copy-paste-ready final answer.",
                "Reply only in English.",
                level_instruction,
                "Problem context:",
                f"- Source platform: {self._normalize_optional_text(context.source_platform)}",
                f"- Source URL: {self._normalize_optional_text(context.source_url)}",
                f"- External problem ID: {self._normalize_optional_text(context.external_problem_id)}",
                f"- Title: {self._normalize_optional_text(context.title)}",
                f"- Description: {self._normalize_optional_text(context.description)}",
                f"- Constraints: {self._normalize_optional_text(context.constraints) or 'Not provided'}",
                f"- Examples: {self._normalize_optional_text(context.examples) or 'Not provided'}",
                f"- Difficulty: {self._normalize_optional_text(context.difficulty) or 'Not provided'}",
                f"- Programming language: {self._normalize_optional_text(context.programming_language) or 'Python'}",
                f"- Student code: {self._normalize_optional_text(context.student_code) or 'Not provided'}",
                f"- Execution result: {self._normalize_optional_text(context.execution_result) or 'Not provided'}",
                f"- Learner context: {self._normalize_optional_text(context.learner_context) or 'Not provided'}",
                f"- Subject profile: {self._normalize_optional_text(context.subject_profile) or 'coding'}",
                f"- Previous hints: {self._normalize_optional_text(context.previous_hints) or 'Not provided'}",
                "Return only one short English hint.",
            ]
        )

    def _call_gemini(self, prompt: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        try:
            model_name = self._get_gemini_model_name()
            if not model_name:
                raise RuntimeError("No Gemini model is configured for this environment.")
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                return self._extract_response_text(client.models.generate_content(model=model_name, contents=prompt))
            if hasattr(client, "generate_content"):
                return self._extract_response_text(client.generate_content(model=model_name, contents=prompt))
            raise RuntimeError("Unexpected Gemini client interface")
        except Exception as exc:
            raise RuntimeError(self._format_gemini_error_message(exc)) from exc

    def _get_gemini_model_name(self) -> str:
        settings = get_settings()
        return os.environ.get("GEMINI_MODEL") or settings.gemini_model or ""

    def get_available_gemini_model_name(self) -> str:
        return self._get_gemini_model_name()

    def _format_gemini_error_message(self, exc: Exception) -> str:
        message = str(exc).lower()
        if "429" in message or "resource_exhausted" in message or "quota" in message or "limit: 0" in message:
            return (
                "The current Gemini API project has no available quota for text generation right now. "
                "Please wait for quota to be replenished or use a different API project/account."
            )
        if "404" in message or "not_found" in message or "unavailable" in message:
            return (
                "The selected Gemini model is currently unavailable for this account. "
                "Please update GEMINI_MODEL to a supported Gemini model and try again later."
            )
        if "api key" in message or "authentication" in message or "permission" in message:
            return "The Gemini API key appears to be invalid or missing. Please verify GEMINI_API_KEY in your environment."
        return "The Gemini service could not generate a hint right now. Please try again in a moment."

    def _extract_response_text(self, response: Any) -> Optional[str]:
        if response is None:
            return None
        if hasattr(response, "text") and response.text:
            return response.text
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text
        if hasattr(response, "candidates") and response.candidates:
            parts = getattr(getattr(response.candidates[0], "content", None), "parts", None)
            if parts and hasattr(parts[0], "text"):
                return parts[0].text
        if hasattr(response, "output") and response.output:
            content_items = response.output[0].content
            if content_items and hasattr(content_items[0], "text"):
                return content_items[0].text
        return None

    def _normalize_hint(self, raw_response: Optional[str], context: ProblemContext, hint_level: int) -> str:
        if raw_response and self._is_safe_english_hint(raw_response):
            return raw_response.strip()
        return self._fallback_hint(context, hint_level)

    def _is_safe_english_hint(self, text: str) -> bool:
        if not text or not text.strip():
            return False
        if re.search(r"[\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]", text):
            return False
        if re.search(r"```|^\s*def\s+\w+\s*\(|^\s*class\s+\w+\s*\(", text, re.MULTILINE):
            return False
        if re.search(r"copy-paste|full solution|final answer|complete solution", text, re.IGNORECASE):
            return False
        return True

    def _fallback_hint(self, context: ProblemContext, hint_level: int) -> str:
        if hint_level == 1:
            return "Fallback hint: restate the problem and identify the first useful concept."
        if hint_level == 2:
            return "Fallback hint: choose an approach that matches the constraints and data shape."
        if hint_level == 3:
            return "Fallback hint: test your current logic on a small example and inspect the first wrong state."
        return "Fallback hint: outline the main steps and complexity before writing the final implementation."

    def _store_hint_history(self, context: ProblemContext, hint_level: int, hint: str) -> None:
        if self.session is None:
            return
        record = HintHistory(submission_id=0, hint_level=hint_level, hint_text=hint)
        self.session.add(record)
        self.session.commit()

    def _normalize_optional_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            return str(value)
        return str(value)

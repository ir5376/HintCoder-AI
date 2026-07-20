from __future__ import annotations

import os
import re
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from src.models.hint import HintHistory
from src.models.problem import Problem

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


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
    ) -> ProblemContext:
        examples = self._normalize_optional_text(problem.test_cases)
        return ProblemContext(
            source_platform="HintCode",
            source_url=problem.source_reference or "",
            external_problem_id=None,
            title=problem.title,
            description=problem.description,
            constraints=problem.constraints or "",
            examples=examples,
            difficulty=problem.difficulty or "",
            programming_language=programming_language or "Python",
            student_code=student_code or problem.starter_code or "",
            execution_result=execution_result,
            hint_level=hint_level,
            problem_id=problem.id,
        )

    def generate_hint(self, context: ProblemContext, hint_level: int | None = None) -> dict[str, Any]:
        level = hint_level if hint_level is not None else context.hint_level or 1
        level = max(1, min(level, 4))

        prompt = self._build_prompt(context, level)
        raw_response = self._call_gemini(prompt)
        hint = self._normalize_hint(raw_response, context, level)

        self._store_hint_history(context, level, hint)
        return {
            "hint": hint,
            "hint_level": level,
            "source_platform": context.source_platform,
            "problem_id": context.problem_id,
            "external_problem_id": context.external_problem_id,
        }

    def list_hint_history(self) -> list[dict[str, Any]]:
        records = self.session.query(HintHistory).order_by(HintHistory.created_at.desc()).all()
        return [
            {
                "id": record.id,
                "source_platform": record.source_platform,
                "external_problem_id": record.external_problem_id,
                "problem_id": record.problem_id,
                "programming_language": record.programming_language,
                "student_code": record.student_code,
                "hint_level": record.hint_level,
                "generated_hint": record.generated_hint,
                "created_at": record.created_at,
            }
            for record in records
        ]

    def _build_prompt(self, context: ProblemContext, hint_level: int) -> str:
        title = self._normalize_optional_text(context.title)
        description = self._normalize_optional_text(context.description)
        constraints = self._normalize_optional_text(context.constraints)
        examples = self._normalize_optional_text(context.examples)
        student_code = self._normalize_optional_text(context.student_code)
        execution_result = self._normalize_optional_text(context.execution_result)

        instructions = [
            "You are an English-speaking coding tutor.",
            "Guide the student's reasoning through progressive hints.",
            "Never provide the complete solution or a copy-paste-ready final answer.",
            "Reply only in English.",
            "If optional fields are missing, make the hint from the available information.",
            "Keep the answer concise and helpful.",
        ]

        if hint_level == 1:
            level_instruction = (
                "Level 1: reveal only the key concept needed to approach the problem and ask a guiding question. "
                "Do not directly name the complete algorithm unless necessary."
            )
        elif hint_level == 2:
            level_instruction = (
                "Level 2: reveal the algorithm direction, mention useful data structures, and explain why the direction may work. "
                "Do not provide full pseudocode."
            )
        elif hint_level == 3:
            level_instruction = (
                "Level 3: provide concise pseudocode for the main approach and point out likely edge cases in the student's submitted code. "
                "Do not provide a complete executable solution."
            )
        else:
            level_instruction = (
                "Level 4: provide a nearly complete implementation strategy, explain the key steps and complexity, and still avoid the final complete solution code."
            )

        prompt_parts = [
            *instructions,
            level_instruction,
            "Problem context:",
            f"- Source platform: {self._normalize_optional_text(context.source_platform)}",
            f"- Source URL: {self._normalize_optional_text(context.source_url)}",
            f"- External problem ID: {self._normalize_optional_text(context.external_problem_id)}",
            f"- Title: {title}",
            f"- Description: {description}",
            f"- Constraints: {constraints or 'Not provided'}",
            f"- Examples: {examples or 'Not provided'}",
            f"- Difficulty: {self._normalize_optional_text(context.difficulty) or 'Not provided'}",
            f"- Programming language: {self._normalize_optional_text(context.programming_language) or 'Python'}",
            f"- Student code: {student_code or 'Not provided'}",
            f"- Execution result: {execution_result or 'Not provided'}",
            "",
            "Return only one short English hint that is progressive, educational, and safe.",
            "Do not include a full solution, a copy-paste-ready code block, or a complete function implementation.",
        ]
        return "\n".join(prompt_parts)

    def _call_gemini(self, prompt: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        try:
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return self._extract_response_text(response)

            if hasattr(client, "generate_content"):
                response = client.generate_content(model=model_name, contents=prompt)
                return self._extract_response_text(response)

            raise RuntimeError("Unexpected Gemini client interface")
        except Exception as exc:
            print(f"[HintService] Gemini request failed: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            return None

        return None

    def _extract_response_text(self, response: Any) -> Optional[str]:
        if response is None:
            return None
        if hasattr(response, "text") and response.text:
            return response.text
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text
        if hasattr(response, "candidates") and response.candidates:
            first_candidate = response.candidates[0]
            if hasattr(first_candidate, "content") and hasattr(first_candidate.content, "parts"):
                parts = first_candidate.content.parts
                if parts:
                    first_part = parts[0]
                    if hasattr(first_part, "text"):
                        return first_part.text
        if hasattr(response, "output") and response.output:
            content_items = response.output[0].content
            if content_items:
                first_item = content_items[0]
                if hasattr(first_item, "text"):
                    return first_item.text
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
        if re.search(r"[가-힣]", text):
            return False

        if re.search(r"```|^\s*def\s+\w+\s*\(|^\s*class\s+\w+\s*\(|\breturn\b.*\bdef\b", text, re.MULTILINE):
            return False

        if re.search(r"copy-paste|full solution|final answer|complete solution", text, re.IGNORECASE):
            return False

        return True

    def _fallback_hint(self, context: ProblemContext, hint_level: int) -> str:
        if hint_level == 1:
            return (
                "Fallback hint: restate the problem in your own words and identify the most important idea needed to begin. "
                "What is the first useful observation you can make?"
            )
        if hint_level == 2:
            return (
                "Fallback hint: think about an algorithmic direction that matches the problem's constraints and data shape. "
                "A suitable data structure may make the approach much clearer."
            )
        if hint_level == 3:
            return (
                "Fallback hint: review your current logic for edge cases and boundary conditions. "
                "Compare the behavior of your code on small examples and inspect the branch that seems suspicious."
            )
        return (
            "Fallback hint: outline the main steps of a correct approach, including why each step matters. "
            "Focus on correctness first and refine the implementation only after the structure is clear."
        )

    def _store_hint_history(self, context: ProblemContext, hint_level: int, hint: str) -> None:
        record = HintHistory(
            submission_id=0,
            hint_level=hint_level,
            hint_text=hint,
        )
        self.session.add(record)
        self.session.commit()

    def _normalize_optional_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            return str(value)
        return str(value)

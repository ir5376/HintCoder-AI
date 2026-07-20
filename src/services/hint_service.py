from __future__ import annotations

import os
import re
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from src.config import get_settings
from src.models.hint import HintHistory
from src.models.problem import Problem

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class LearningContext:
    current_approach: str = ""
    current_obstacle: str = ""
    intended_algorithm: str = ""
    desired_hint_level: int = 1
    confidence_level: float | None = None

    def to_prompt_lines(self) -> list[str]:
        confidence = "Not provided" if self.confidence_level is None else str(self.confidence_level)
        return [
            f"- Current approach: {self.current_approach or 'Not provided'}",
            f"- Current obstacle: {self.current_obstacle or 'Not provided'}",
            f"- Intended algorithm: {self.intended_algorithm or 'Not provided'}",
            f"- Desired hint level: {self.desired_hint_level}",
            f"- Confidence level: {confidence}",
        ]


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
    learning_context: LearningContext | None = None


@dataclass(frozen=True)
class CoachingAction:
    key: str
    label: str
    response_style: str
    prompt_instruction: str


COACHING_ACTIONS = {
    "generate_hint": CoachingAction("generate_hint", "Generate Hint", "progressive_hint", "Give a progressive hint that helps the learner take the next step."),
    "validate_idea": CoachingAction("validate_idea", "Validate My Idea", "idea_validation", "Validate the learner's idea, name the risk if any, and ask one guiding follow-up question."),
    "ask_coach": CoachingAction("ask_coach", "Ask My Coach", "interactive_coaching", "Answer the learner's question Socratically without revealing the final answer."),
    "explain_concept": CoachingAction("explain_concept", "Explain Concept", "concept_explanation", "Explain the missing concept with a small analogy or minimal example, not the full solution."),
    "explain_wrong_choices": CoachingAction("explain_wrong_choices", "Explain Wrong Choices", "choice_analysis", "Explain why each wrong choice is tempting but incorrect, then reinforce the correct concept."),
    "give_progressive_hint": CoachingAction("give_progressive_hint", "Give Progressive Hint", "progressive_hint", "Give the next smallest hint for this content type without revealing the answer."),
    "explain_algorithm": CoachingAction("explain_algorithm", "Explain Algorithm", "algorithm_explanation", "Explain the algorithmic idea and complexity without writing a full implementation."),
    "complexity_check": CoachingAction("complexity_check", "Complexity Check", "complexity_feedback", "Evaluate the likely time and space complexity and suggest what to inspect next."),
    "debug_code": CoachingAction("debug_code", "Debug My Code", "debugging_guidance", "Point to the most suspicious area and suggest a tiny test case without rewriting the solution."),
    "review_thinking": CoachingAction("review_thinking", "Review My Thinking", "thinking_review", "Review the learner's reasoning process, decision points, and assumptions."),
    "vocabulary_hint": CoachingAction("vocabulary_hint", "Vocabulary Hint", "vocabulary_guidance", "Explain important vocabulary clues without translating the whole passage or giving the answer."),
    "grammar_explanation": CoachingAction("grammar_explanation", "Grammar Explanation", "grammar_guidance", "Explain the grammar pattern needed to reason about the question."),
    "reading_guidance": CoachingAction("reading_guidance", "Reading Guidance", "reading_strategy", "Guide how to read the passage, identify structure, and eliminate traps."),
}


class HintService:
    def __init__(self, session, openai_client: Any | None = None) -> None:
        self.session = session
        self.openai_client = openai_client

    def _get_client(self) -> Any | None:
        if self.openai_client is not None:
            return self.openai_client

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai

                return genai.Client(api_key=gemini_key)
            except Exception as exc:
                print(f"[HintService] Google GenAI SDK import failed: {type(exc).__name__}: {exc}")

        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI

                return OpenAI(api_key=openai_key)
            except Exception as exc:
                print(f"[HintService] OpenAI SDK import failed: {type(exc).__name__}: {exc}")

        print("[HintService] No AI API key is configured; using fallback hint.")
        return None

    def build_problem_context(
        self,
        problem: Problem,
        *,
        student_code: str = "",
        programming_language: str = "Python",
        execution_result: str = "",
        hint_level: int = 1,
        learning_context: LearningContext | None = None,
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
            learning_context=learning_context,
        )

    def generate_hint(self, context: ProblemContext, hint_level: int | None = None) -> dict[str, Any]:
        level = max(1, min(hint_level if hint_level is not None else context.hint_level or 1, 4))
        raw_response = self._call_ai(self._build_prompt(context, level))
        hint = self._normalize_hint(raw_response, context, level)
        self._store_hint_history(context, level, hint)
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
        execution_trace: dict[str, Any] | None = None,
        current_step: str = "",
        reflection: dict[str, Any] | None = None,
        hint_level: int | None = None,
    ) -> dict[str, Any]:
        normalized_action = action if action in COACHING_ACTIONS else "ask_coach"
        if normalized_action in {"generate_hint", "give_progressive_hint"}:
            result = self.generate_hint(context, hint_level=hint_level)
            result.update(
                {
                    "action": normalized_action,
                    "label": COACHING_ACTIONS[normalized_action].label,
                    "response": result["hint"],
                }
            )
            return result

        level = hint_level or context.hint_level or 1
        prompt = self._build_coaching_prompt(
            context,
            COACHING_ACTIONS[normalized_action],
            user_question=user_question,
            execution_trace=execution_trace,
            current_step=current_step,
            reflection=reflection,
        )
        response = self._normalize_hint(self._call_ai(prompt), context, level)
        return {
            "action": normalized_action,
            "label": COACHING_ACTIONS[normalized_action].label,
            "response": response,
            "hint": response,
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
                "generated_hint": record.generated_hint or record.hint_text,
                "created_at": record.created_at,
            }
            for record in records
        ]

    def _build_prompt(self, context: ProblemContext, hint_level: int) -> str:
        learning_context = context.learning_context or LearningContext(desired_hint_level=hint_level)
        if hint_level == 1:
            level_instruction = (
                "Level 1: reveal only the key concept needed to approach the problem, clarify what is being asked, "
                "and ask a guiding question. Do not directly name the complete algorithm unless necessary."
            )
        elif hint_level == 2:
            level_instruction = (
                "Level 2: suggest the algorithm direction, mention useful data structures, and explain why the direction may work. "
                "Do not provide full pseudocode."
            )
        elif hint_level == 3:
            level_instruction = (
                "Level 3: analyze the learner's submitted work, identify likely logical or boundary-case issues, "
                "and provide concise partial pseudocode. Do not provide a complete executable solution."
            )
        else:
            level_instruction = (
                "Level 4: provide a nearly complete implementation strategy, explain the key steps and complexity, "
                "and still avoid the final complete solution code."
            )

        return "\n".join(
            [
                "You are an English-speaking AI learning coach.",
                "Guide the learner's reasoning through progressive hints.",
                "Never provide the complete solution or a copy-paste-ready final answer.",
                "Reply only in English.",
                "If optional fields are missing, make the hint from the available information.",
                "Keep the answer concise and helpful.",
                level_instruction,
                "Learning item context:",
                f"- Source platform: {self._normalize_optional_text(context.source_platform)}",
                f"- Source URL: {self._normalize_optional_text(context.source_url)}",
                f"- External problem ID: {self._normalize_optional_text(context.external_problem_id)}",
                f"- Title: {self._normalize_optional_text(context.title)}",
                f"- Description: {self._normalize_optional_text(context.description)}",
                f"- Constraints: {self._normalize_optional_text(context.constraints) or 'Not provided'}",
                f"- Examples: {self._normalize_optional_text(context.examples) or 'Not provided'}",
                f"- Difficulty: {self._normalize_optional_text(context.difficulty) or 'Not provided'}",
                f"- Programming language: {self._normalize_optional_text(context.programming_language) or 'Python'}",
                f"- Student code or answer: {self._normalize_optional_text(context.student_code) or 'Not provided'}",
                f"- Execution result: {self._normalize_optional_text(context.execution_result) or 'Not provided'}",
                "Learning context:",
                *learning_context.to_prompt_lines(),
                "",
                "Return only one short English response that is progressive, educational, and safe.",
                "Do not include a full solution, a copy-paste-ready code block, or a complete function implementation.",
            ]
        )

    def _build_coaching_prompt(
        self,
        context: ProblemContext,
        action: CoachingAction,
        *,
        user_question: str = "",
        execution_trace: dict[str, Any] | None = None,
        current_step: str = "",
        reflection: dict[str, Any] | None = None,
    ) -> str:
        return "\n".join(
            [
                self._build_prompt(context, context.hint_level or 1),
                "",
                f"Coaching action: {action.label}",
                f"Response style: {action.response_style}",
                action.prompt_instruction,
                f"Learner question: {self._normalize_optional_text(user_question) or 'Not provided'}",
                f"Current learning step: {self._normalize_optional_text(current_step) or 'Not provided'}",
                f"Execution trace: {self._normalize_optional_text(execution_trace) or 'Not provided'}",
                f"Reflection: {self._normalize_optional_text(reflection) or 'Not provided'}",
                "Guide without revealing the final answer.",
            ]
        )

    def _call_ai(self, prompt: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None
        try:
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                return self._call_gemini_client(client, prompt)
            if hasattr(client, "generate_content"):
                return self._call_gemini_client(client, prompt)
            if hasattr(client, "responses") and hasattr(client.responses, "create"):
                return self._call_openai_client(client, prompt)
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                raise RuntimeError("Chat Completions API is not supported by this service")
            raise RuntimeError("Unexpected AI client interface")
        except Exception as exc:
            print(f"[HintService] AI request failed: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            return None

    def _call_gemini_client(self, client: Any, prompt: str) -> Optional[str]:
        model_name = self._get_gemini_model_name()
        if hasattr(client, "models") and hasattr(client.models, "generate_content"):
            response = client.models.generate_content(model=model_name, contents=prompt)
            return self._extract_response_text(response)
        response = client.generate_content(model=model_name, contents=prompt)
        return self._extract_response_text(response)

    def _call_openai_client(self, client: Any, prompt: str) -> Optional[str]:
        response = client.responses.create(model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"), input=prompt)
        return self._extract_response_text(response)

    def _call_gemini(self, prompt: str) -> Optional[str]:
        return self._call_ai(prompt)

    def _call_openai(self, prompt: str) -> Optional[str]:
        return self._call_ai(prompt)

    def _get_gemini_model_name(self) -> str:
        settings = get_settings()
        return os.environ.get("GEMINI_MODEL") or settings.gemini_model or "gemini-2.5-flash"

    def get_available_gemini_model_name(self) -> str:
        return self._get_gemini_model_name()

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
        if re.search(r"```|^\s*def\s+\w+\s*\(|^\s*class\s+\w+\s*\(|\breturn\b.*\bdef\b", text, re.MULTILINE):
            return False
        if re.search(r"copy-paste|full solution|final answer|complete solution", text, re.IGNORECASE):
            return False
        return True

    def _fallback_hint(self, context: ProblemContext, hint_level: int) -> str:
        if hint_level == 1:
            return (
                "Fallback hint: restate the learning item in your own words and identify the most important idea needed to begin. "
                "What is the first useful observation you can make?"
            )
        if hint_level == 2:
            return (
                "Fallback hint: think about a direction that matches the constraints and data shape. "
                "A suitable structure or concept may make the approach much clearer."
            )
        if hint_level == 3:
            return (
                "Fallback hint: review your current logic for edge cases and boundary conditions. "
                "Compare your reasoning on small examples and inspect the step that seems suspicious."
            )
        return (
            "Fallback hint: outline the main steps of a correct approach, including why each step matters. "
            "Focus on correctness first and refine the implementation only after the structure is clear."
        )

    def _store_hint_history(self, context: ProblemContext, hint_level: int, hint: str) -> None:
        record = HintHistory(
            submission_id=None,
            source_platform=context.source_platform,
            external_problem_id=context.external_problem_id,
            problem_id=context.problem_id,
            programming_language=context.programming_language,
            student_code=context.student_code,
            hint_level=hint_level,
            generated_hint=hint,
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

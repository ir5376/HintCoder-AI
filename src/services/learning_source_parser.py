from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from src.services.provider_adapters import adapter_for_url


@dataclass(frozen=True)
class ParsedLearningItem:
    source_type: str
    title: str
    owner_user_id: str = "local"
    source_id: str = ""
    difficulty: str = "Unknown"
    provider: str = ""
    provider_problem_id: str = ""
    original_url: str = ""
    subject: str = ""
    exam_name: str = ""
    year: str = ""
    question_number: str = ""
    content: str = ""
    question_type: str = "unknown"
    choices: list[str] = field(default_factory=list)
    verified_answer: str = ""
    inferred_answer: str = ""
    answer_status: str = "unavailable"
    explanation: str = ""
    concepts: list[str] = field(default_factory=list)
    learning_objective: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedAnswer:
    question_number: str
    official_answer: str
    explanation: str = ""
    page_number: int | None = None


@dataclass(frozen=True)
class ParsedPassageGroup:
    group_identifier: str
    passage_text: str
    question_numbers: list[str] = field(default_factory=list)
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExamImportPreview:
    exam_title: str
    subject: str
    year: str
    questions: list[ParsedLearningItem]
    answers: list[ParsedAnswer]
    passages: list[ParsedPassageGroup]
    report: dict[str, Any]


class ProviderUrlParser:
    def parse(self, url: str, *, title: str = "", difficulty: str = "", owner_user_id: str = "local") -> ParsedLearningItem:
        normalized_url = _normalize_url(url)
        adapter = adapter_for_url(normalized_url)
        identity = adapter.extract_problem_identity({"url": normalized_url, "title": title})
        problem_id = identity.provider_problem_id
        clean_title = title.strip() or identity.title or _title_from_problem_id(problem_id) or adapter.provider.title()
        return ParsedLearningItem(
            source_type="provider_url",
            owner_user_id=owner_user_id,
            source_id=normalized_url,
            provider=identity.provider,
            provider_problem_id=problem_id,
            original_url=normalized_url,
            subject="Coding",
            title=clean_title,
            difficulty=difficulty.strip() or "Unknown",
            content=f"Imported provider problem from {identity.provider}: {clean_title}",
            question_type="coding",
            concepts=_infer_concepts(clean_title),
            learning_objective=f"Solve {clean_title} using the key concept.",
            metadata=identity.metadata,
        )


class PdfParser:
    def parse(self, filename: str, data: bytes | str, *, title: str = "", owner_user_id: str = "local") -> list[ParsedLearningItem]:
        text = data if isinstance(data, str) else extract_pdf_text(data)
        return parse_question_text(text, filename=filename, title=title, owner_user_id=owner_user_id)


class ExamSourceParser:
    def preview(
        self,
        *,
        question_pdf_name: str,
        question_pdf: bytes | str,
        answer_pdf_name: str = "",
        answer_pdf: bytes | str | None = None,
        owner_user_id: str = "local",
        title: str = "",
    ) -> ExamImportPreview:
        question_text = question_pdf if isinstance(question_pdf, str) else extract_pdf_text(question_pdf)
        answer_text = ""
        if answer_pdf is not None:
            answer_text = answer_pdf if isinstance(answer_pdf, str) else extract_pdf_text(answer_pdf)

        exam_title = title.strip() or _extract_exam_title(question_text) or question_pdf_name
        subject = _extract_subject(question_text)
        year = _extract_year(question_text)
        passages = extract_passage_groups(question_text)
        questions = parse_question_text(
            question_text,
            filename=question_pdf_name,
            title=exam_title,
            owner_user_id=owner_user_id,
            subject=subject,
            year=year,
            passages=passages,
        )
        answers = parse_answer_text(answer_text) if answer_text else _answers_from_final_pages(question_text)
        matched, unmatched_answers = _match_answers(questions, answers)

        report = {
            "questions_detected": len(questions),
            "passages_detected": len(passages),
            "answers_detected": len(answers),
            "answers_matched": len(matched),
            "questions_without_answers": [
                question.question_number for question in questions if question.question_number not in matched
            ],
            "unmatched_answers": [answer.question_number for answer in unmatched_answers],
            "low_confidence_question_boundaries": [],
            "low_confidence_items": [],
            "warnings": [],
        }
        if not answers:
            report["warnings"].append("No answer PDF or final-page answers detected; answers are unavailable.")

        questions_with_answers = []
        for question in questions:
            answer = matched.get(question.question_number)
            if answer:
                questions_with_answers.append(
                    ParsedLearningItem(
                        **{
                            **question.__dict__,
                            "verified_answer": answer.official_answer,
                            "answer_status": "verified",
                            "explanation": answer.explanation,
                        }
                    )
                )
            else:
                questions_with_answers.append(question)

        return ExamImportPreview(exam_title, subject, year, questions_with_answers, answers, passages, report)


class NotesParser:
    def parse(self, notes: str, *, title: str = "", owner_user_id: str = "local") -> ParsedLearningItem:
        clean_title = title.strip() or _first_line(notes) or "Notes"
        concepts = _infer_concepts(notes)
        return ParsedLearningItem(
            source_type="notes",
            owner_user_id=owner_user_id,
            source_id=clean_title,
            provider="notes",
            title=clean_title,
            content=notes.strip(),
            question_type="notes",
            concepts=concepts,
            learning_objective=_objective(concepts),
            metadata={},
        )


def parse_question_text(
    text: str,
    *,
    filename: str,
    title: str = "",
    owner_user_id: str = "local",
    subject: str = "",
    year: str = "",
    passages: list[ParsedPassageGroup] | None = None,
) -> list[ParsedLearningItem]:
    chunks = _split_questions(text)
    if not chunks and text.strip():
        chunks = [text.strip()]
    exam_name = title.strip() or _extract_exam_title(text) or filename
    subject = subject or _extract_subject(text)
    year = year or _extract_year(text)
    items = []
    for index, chunk in enumerate(chunks, start=1):
        concepts = _infer_concepts(chunk)
        question_number = _extract_question_number(chunk) or str(index)
        choices = _extract_choices(chunk)
        passage = _passage_for_question(passages or [], question_number)
        metadata = {"filename": filename, "question_index": index, "page_number": index}
        if passage:
            metadata["passage_group"] = passage.group_identifier
            metadata["passage_text"] = passage.passage_text
        items.append(
            ParsedLearningItem(
                source_type="exam_pdf",
                owner_user_id=owner_user_id,
                source_id=filename,
                provider="pdf",
                subject=subject,
                exam_name=exam_name,
                year=year,
                question_number=question_number,
                title=f"{exam_name} Q{question_number}",
                content=chunk.strip(),
                question_type="multiple_choice" if choices else "short_answer",
                choices=choices,
                concepts=concepts,
                difficulty="Unknown",
                original_url=filename,
                learning_objective=_objective(concepts),
                metadata=metadata,
            )
        )
    return items


def extract_passage_groups(text: str) -> list[ParsedPassageGroup]:
    normalized = str(text or "").strip()
    markers = list(re.finditer(r"(?im)^\s*(?:passage|지문|reading)\s*([A-Za-z0-9]+)?\s*[:.)-]\s*", normalized))
    groups: list[ParsedPassageGroup] = []
    if not markers:
        return groups
    for index, marker in enumerate(markers, start=1):
        end = markers[index].start() if index < len(markers) else len(normalized)
        block = normalized[marker.end() : end].strip()
        question_numbers = re.findall(r"(?m)^\s*(?:Q(?:uestion)?\s*)?(\d+)[.)]\s+", block)
        first_question = re.search(r"(?m)^\s*(?:Q(?:uestion)?\s*)?\d+[.)]\s+", block)
        passage_text = block[: first_question.start()].strip() if first_question else block
        identifier = marker.group(1) or str(index)
        if passage_text:
            groups.append(
                ParsedPassageGroup(
                    group_identifier=str(identifier),
                    passage_text=passage_text,
                    question_numbers=question_numbers,
                    page_number=index,
                    metadata={"marker_index": index},
                )
            )
    return groups


def parse_answer_text(text: str) -> list[ParsedAnswer]:
    answers = []
    pattern = re.compile(
        r"(?im)^\s*(?:Q(?:uestion)?\s*)?(\d+)[.)]?\s*(?:answer|ans)?\s*[:：\-]?\s*([A-E]|\d+)(?:\s*[-:]\s*(.*))?$"
    )
    for index, match in enumerate(pattern.finditer(text), start=1):
        answers.append(ParsedAnswer(match.group(1), match.group(2), (match.group(3) or "").strip(), index))
    return answers


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return data.decode("utf-8", errors="ignore")


def _answers_from_final_pages(text: str) -> list[ParsedAnswer]:
    marker = re.search(r"(?im)^\s*(answers?|answer key|solutions?)\s*$", text)
    if not marker:
        return []
    return parse_answer_text(text[marker.start() :])


def _match_answers(questions: list[ParsedLearningItem], answers: list[ParsedAnswer]) -> tuple[dict[str, ParsedAnswer], list[ParsedAnswer]]:
    question_numbers = {question.question_number for question in questions if question.question_number}
    matched = {answer.question_number: answer for answer in answers if answer.question_number in question_numbers}
    unmatched = [answer for answer in answers if answer.question_number not in question_numbers]
    return matched, unmatched


def _passage_for_question(passages: list[ParsedPassageGroup], question_number: str) -> ParsedPassageGroup | None:
    for passage in passages:
        if question_number in passage.question_numbers:
            return passage
    return None


def _normalize_url(url: str) -> str:
    value = str(url or "").strip()
    if "://" not in value and "." in value:
        return f"https://{value}"
    return value


def _split_questions(text: str) -> list[str]:
    normalized = str(text or "").strip()
    matches = list(re.finditer(r"(?m)^\s*(?:Q(?:uestion)?\s*)?(\d+)[.)]\s+", normalized))
    if len(matches) <= 1:
        return [normalized] if normalized else []
    chunks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        chunks.append(normalized[match.start() : end].strip())
    return chunks


def _extract_choices(text: str) -> list[str]:
    return [match.group(0).strip() for match in re.finditer(r"(?m)^\s*(?:[A-E]|\d+)[.)]\s+.+$", text)]


def _extract_question_number(text: str) -> str:
    match = re.search(r"(?m)^\s*(?:Q(?:uestion)?\s*)?(\d+)[.)]\s+", text)
    return match.group(1) if match else ""


def _extract_exam_title(text: str) -> str:
    for line in str(text or "").splitlines()[:5]:
        if line.strip() and not line.lower().startswith(("subject:", "year:")):
            return line.strip()
    return ""


def _extract_subject(text: str) -> str:
    match = re.search(r"(?im)^\s*subject\s*[:：]\s*(.+)$", text)
    return match.group(1).strip() if match else ""


def _extract_year(text: str) -> str:
    match = re.search(r"\b(?:19|20)\d{2}\b", text)
    return match.group(0) if match else ""


def _title_from_problem_id(problem_id: str) -> str:
    return problem_id.replace("-", " ").replace("_", " ").title()


def _infer_concepts(text: str) -> list[str]:
    lower = str(text or "").lower()
    concepts = [
        concept
        for concept in [
            "array",
            "graph",
            "bfs",
            "dfs",
            "dynamic programming",
            "dp",
            "greedy",
            "network",
            "database",
            "sql",
            "operating system",
            "security",
            "algorithm",
        ]
        if concept in lower
    ]
    if concepts:
        return concepts[:5]
    words = re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,}", lower)
    seen = []
    for word in words:
        if word not in {"the", "and", "for", "with", "from", "this", "that"} and word not in seen:
            seen.append(word)
        if len(seen) == 3:
            break
    return seen


def _objective(concepts: list[str]) -> str:
    return f"Understand and apply {concepts[0]}." if concepts else "Understand the core idea and recall it during review."


def _first_line(text: str) -> str:
    for line in str(text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""

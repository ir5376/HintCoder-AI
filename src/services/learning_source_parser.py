from __future__ import annotations

import re
import zlib
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


@dataclass(frozen=True)
class ExtractedPdfPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedPdfDocument:
    pages: list[ExtractedPdfPage] = field(default_factory=list)
    page_count: int = 0
    byte_length: int = 0
    starts_with_pdf: bool = False
    extraction_method: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def extracted_char_count(self) -> int:
        return sum(len(page.text) for page in self.pages)

    @property
    def has_text(self) -> bool:
        return self.extracted_char_count > 0


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
        document = ExtractedPdfDocument() if isinstance(data, str) else extract_pdf_document(data)
        pages = document.pages
        text = data if isinstance(data, str) else _join_pdf_pages(pages)
        return parse_question_text(text, filename=filename, title=title, owner_user_id=owner_user_id, page_texts=pages)


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
        question_document = ExtractedPdfDocument() if isinstance(question_pdf, str) else extract_pdf_document(question_pdf)
        question_pages = question_document.pages
        question_text = question_pdf if isinstance(question_pdf, str) else _join_pdf_pages(question_pages)
        answer_text = ""
        if answer_pdf is not None:
            answer_document = ExtractedPdfDocument() if isinstance(answer_pdf, str) else extract_pdf_document(answer_pdf)
            answer_pages = answer_document.pages
            answer_text = answer_pdf if isinstance(answer_pdf, str) else _join_pdf_pages(answer_pages)

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
            page_texts=question_pages,
        )
        answers = parse_answer_text(answer_text) if answer_text else _answers_from_final_pages(question_text)
        matched, unmatched_answers = _match_answers(questions, answers)

        extracted_char_count = question_document.extracted_char_count if not isinstance(question_pdf, str) else len(question_text)
        page_count = question_document.page_count if not isinstance(question_pdf, str) else 0
        report = {
            "questions_detected": len(questions),
            "passages_detected": len(passages),
            "answers_detected": len(answers),
            "answers_matched": len(matched),
            "page_count": page_count,
            "extracted_char_count": extracted_char_count,
            "uploaded_byte_length": question_document.byte_length if not isinstance(question_pdf, str) else len(question_text.encode("utf-8")),
            "starts_with_pdf_signature": question_document.starts_with_pdf if not isinstance(question_pdf, str) else False,
            "extraction_method": question_document.extraction_method,
            "extraction_errors": question_document.errors,
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
        if not isinstance(question_pdf, str) and question_document.byte_length == 0:
            report["warnings"].append("The uploaded PDF is empty.")
            report["invalid_pdf"] = True
            report["ocr_required"] = False
        elif not isinstance(question_pdf, str) and not question_document.starts_with_pdf:
            report["warnings"].append("The uploaded file is not a valid PDF.")
            report["invalid_pdf"] = True
            report["ocr_required"] = False
        elif page_count > 0 and not question_text.strip():
            report["warnings"].append("The PDF has pages but no readable text layer. OCR is required for scanned/image-only PDFs.")
            report["invalid_pdf"] = False
            report["ocr_required"] = True
        elif page_count == 0 and not question_text.strip():
            report["warnings"].append("The PDF could not be opened or no pages were detected.")
            if question_document.errors:
                report["warnings"].append(f"PDF extractor errors: {'; '.join(question_document.errors[:3])}")
            report["invalid_pdf"] = True
            report["ocr_required"] = False
        else:
            report["invalid_pdf"] = False
            report["ocr_required"] = False

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
    page_texts: list[ExtractedPdfPage] | None = None,
) -> list[ParsedLearningItem]:
    if _looks_like_pdf_syntax(text):
        return []
    chunks, used_fallback = _split_questions(text)
    exam_name = title.strip() or _extract_exam_title(text) or filename
    subject = subject or _extract_subject(text)
    year = year or _extract_year(text)
    items = []
    for index, chunk in enumerate(chunks, start=1):
        concepts = _infer_concepts(chunk)
        question_number = _extract_question_number(chunk) or str(index)
        choices = _extract_choices(chunk)
        passage = _passage_for_question(passages or [], question_number)
        metadata = {
            "filename": filename,
            "question_index": index,
            "page_number": _page_number_for_chunk(chunk, page_texts or []) or index,
            "parsing_mode": "single_question_fallback" if used_fallback else "deterministic_question_split",
        }
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
    answers = _parse_answer_blocks(text)
    seen = {answer.question_number for answer in answers}
    pattern = re.compile(
        r"(?im)^\s*(?:Q(?:uestion)?\s*)?(\d+)[.)]?\s*(?:answer|ans)?\s*[:：\-]?\s*([A-E]|\d+)(?:\s*[-:]\s*(.*))?$"
    )
    for index, match in enumerate(pattern.finditer(text), start=1):
        question_number = match.group(1)
        if question_number in seen:
            continue
        answers.append(ParsedAnswer(question_number, _canonical_answer(match.group(2)), (match.group(3) or "").strip(), index))
        seen.add(question_number)
    return answers


def _parse_answer_blocks(text: str) -> list[ParsedAnswer]:
    normalized = str(text or "").strip()
    markers = list(re.finditer(r"(?im)^\s*(?:Q(?:uestion)?|문항)\s*(\d+)\s*[:.)-]?\s*$", normalized))
    answers: list[ParsedAnswer] = []
    for index, marker in enumerate(markers, start=1):
        end = markers[index].start() if index < len(markers) else len(normalized)
        block = normalized[marker.end() : end].strip()
        answer_match = re.search(
            r"(?im)^\s*(?:correct\s+answer|answer|ans|정답)\s*[:：]\s*(.+?)\s*$",
            block,
        )
        if not answer_match:
            continue
        explanation_match = re.search(r"(?ims)^\s*(?:explanation|solution|해설|풀이)\s*[:：]\s*(.+)$", block)
        explanation = explanation_match.group(1).strip() if explanation_match else block[answer_match.end() :].strip()
        answers.append(
            ParsedAnswer(
                question_number=marker.group(1),
                official_answer=_canonical_answer(answer_match.group(1)),
                explanation=explanation,
                page_number=index,
            )
        )
    return answers


def _canonical_answer(value: str) -> str:
    answer = re.sub(r"\s+", " ", str(value or "")).strip()
    answer = re.sub(r"^([A-E])\s*\)\s*", r"\1. ", answer, flags=re.IGNORECASE)
    answer = re.sub(r"^([A-E])\s*[-:]\s*", r"\1. ", answer, flags=re.IGNORECASE)
    answer = re.sub(r"^([A-E])\.\s*", lambda match: f"{match.group(1).upper()}. ", answer, count=1)
    return answer.strip()


def extract_pdf_document(data: bytes) -> ExtractedPdfDocument:
    raw = bytes(data or b"")
    if not raw:
        return ExtractedPdfDocument(byte_length=0, starts_with_pdf=False, errors=["empty_pdf"])
    starts_with_pdf = raw.startswith(b"%PDF")
    if not starts_with_pdf:
        return ExtractedPdfDocument(byte_length=len(raw), starts_with_pdf=False, errors=["invalid_pdf_signature"])
    errors: list[str] = []
    for method, extractor in (
        ("pymupdf", _extract_pages_with_pymupdf),
        ("pdfplumber", _extract_pages_with_pdfplumber),
        ("pypdf", _extract_pages_with_pypdf),
        ("builtin", _extract_pages_with_builtin_pdf),
    ):
        try:
            page_count, pages, error = extractor(raw)
        except Exception as exc:
            errors.append(f"{method}: extract_failed:{type(exc).__name__}:{exc}")
            continue
        if error:
            errors.append(f"{method}: {error}")
        if page_count > 0:
            return ExtractedPdfDocument(
                pages=pages,
                page_count=page_count,
                byte_length=len(raw),
                starts_with_pdf=True,
                extraction_method=method,
                errors=errors,
            )
    return ExtractedPdfDocument(byte_length=len(raw), starts_with_pdf=True, errors=errors or ["pdf_open_failed"])


def extract_pdf_pages(data: bytes) -> list[ExtractedPdfPage]:
    return extract_pdf_document(data).pages


def _extract_pages_with_pymupdf(data: bytes) -> tuple[int, list[ExtractedPdfPage], str]:
    try:
        import fitz
    except Exception as exc:
        return 0, [], f"import_failed:{type(exc).__name__}"
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return 0, [], f"open_failed:{type(exc).__name__}:{exc}"
    pages = []
    try:
        page_count = len(document)
        for index, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            cleaned = _clean_extracted_page_text(text)
            if cleaned:
                pages.append(ExtractedPdfPage(page_number=index, text=cleaned))
    finally:
        document.close()
    return page_count, pages, ""


def _extract_pages_with_pdfplumber(data: bytes) -> tuple[int, list[ExtractedPdfPage], str]:
    try:
        import pdfplumber
    except Exception as exc:
        return 0, [], f"import_failed:{type(exc).__name__}"
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = []
            page_count = len(pdf.pages)
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                cleaned = _clean_extracted_page_text(text)
                if cleaned:
                    pages.append(ExtractedPdfPage(page_number=index, text=cleaned))
            return page_count, pages, ""
    except Exception as exc:
        return 0, [], f"open_failed:{type(exc).__name__}:{exc}"


def _extract_pages_with_pypdf(data: bytes) -> tuple[int, list[ExtractedPdfPage], str]:
    backend = "pypdf"
    try:
        from pypdf import PdfReader
    except Exception as exc:
        try:
            from PyPDF2 import PdfReader  # type: ignore[no-redef]
            backend = "PyPDF2"
        except Exception as fallback_exc:
            return 0, [], f"import_failed:pypdf:{type(exc).__name__};PyPDF2:{type(fallback_exc).__name__}"
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        return 0, [], f"open_failed:{backend}:{type(exc).__name__}:{exc}"
    pages = []
    try:
        page_count = len(reader.pages)
    except Exception as exc:
        return 0, [], f"page_count_failed:{backend}:{type(exc).__name__}:{exc}"
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        cleaned = _clean_extracted_page_text(text)
        if cleaned:
            pages.append(ExtractedPdfPage(page_number=index, text=cleaned))
    return page_count, pages, ""


def _extract_pages_with_builtin_pdf(data: bytes) -> tuple[int, list[ExtractedPdfPage], str]:
    page_count = len(re.findall(rb"/Type\s*/Page\b", data))
    if page_count <= 0:
        return 0, [], "no_page_markers"

    texts: list[str] = []
    for match in re.finditer(rb"stream\r?\n?(.*?)\r?\n?endstream", data, flags=re.DOTALL):
        stream_data = match.group(1).strip(b"\r\n")
        header = data[max(0, match.start() - 500) : match.start()]
        if b"/FlateDecode" in header:
            try:
                stream_data = zlib.decompress(stream_data)
            except Exception:
                continue
        extracted = _extract_text_from_pdf_stream(stream_data)
        if extracted:
            texts.append(extracted)

    joined = _clean_extracted_page_text("\n".join(texts))
    pages = [ExtractedPdfPage(page_number=1, text=joined)] if joined else []
    return page_count, pages, ""


def _extract_text_from_pdf_stream(stream_data: bytes) -> str:
    parts: list[str] = []
    for literal in re.findall(rb"\((?:\\.|[^\\)])*\)", stream_data, flags=re.DOTALL):
        decoded = _decode_pdf_literal(literal[1:-1])
        if decoded:
            parts.append(decoded)
    for hex_string in re.findall(rb"(?<!<)<([0-9A-Fa-f\s]+)>(?!>)", stream_data):
        decoded = _decode_pdf_hex(hex_string)
        if decoded:
            parts.append(decoded)
    return " ".join(part.strip() for part in parts if part.strip())


def _decode_pdf_literal(value: bytes) -> str:
    replacements = {
        b"\\n": b"\n",
        b"\\r": b"\r",
        b"\\t": b"\t",
        b"\\b": b"\b",
        b"\\f": b"\f",
        b"\\(": b"(",
        b"\\)": b")",
        b"\\\\": b"\\",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value.decode("utf-8", errors="ignore") or value.decode("latin-1", errors="ignore")


def _decode_pdf_hex(value: bytes) -> str:
    compact = re.sub(rb"\s+", b"", value)
    if len(compact) % 2:
        compact += b"0"
    try:
        raw = bytes.fromhex(compact.decode("ascii"))
    except ValueError:
        return ""
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", errors="ignore")
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le", errors="ignore")
    if raw.count(b"\x00") >= max(1, len(raw) // 4):
        return raw.decode("utf-16-be", errors="ignore")
    return raw.decode("utf-8", errors="ignore") or raw.decode("latin-1", errors="ignore")


def extract_pdf_text(data: bytes) -> str:
    return _join_pdf_pages(extract_pdf_document(data).pages)


def _join_pdf_pages(pages: list[ExtractedPdfPage]) -> str:
    return "\n".join(page.text for page in pages if page.text.strip() and not _looks_like_pdf_syntax(page.text))


def _clean_extracted_page_text(text: str) -> str:
    cleaned = re.sub(r"\s+\n", "\n", str(text or "")).strip()
    if not cleaned or _looks_like_pdf_syntax(cleaned):
        return ""
    return cleaned


def _looks_like_pdf_syntax(text: str) -> bool:
    value = str(text or "").lstrip()
    if value.startswith("%PDF-"):
        return True
    markers = (" obj", "endobj", " stream", "endstream", "/FlateDecode", "xref", "trailer")
    return sum(1 for marker in markers if marker in value[:2000]) >= 2


def _page_number_for_chunk(chunk: str, pages: list[ExtractedPdfPage]) -> int | None:
    normalized_chunk = re.sub(r"\s+", " ", str(chunk or "")).strip()
    if not normalized_chunk:
        return None
    needle = normalized_chunk[:80]
    for page in pages:
        normalized_page = re.sub(r"\s+", " ", page.text)
        if needle and needle in normalized_page:
            return page.page_number
    return None


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


def _split_questions(text: str) -> tuple[list[str], bool]:
    normalized = str(text or "").strip()
    matches = list(re.finditer(r"(?m)^\s*(?:Q(?:uestion)?\s*)?(\d+)[.)]\s+", normalized))
    if len(matches) <= 1:
        return ([normalized], True) if normalized else ([], False)
    chunks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        chunks.append(normalized[match.start() : end].strip())
    return chunks, False


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

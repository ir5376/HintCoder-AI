import os
import sys
import tempfile
from io import BytesIO
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text

from src.database import get_session, init_db
from src.models.learning_item import LearningItem
from src.services.learning_source_parser import ExamSourceParser, parse_question_text, extract_pdf_document, extract_pdf_pages, extract_pdf_text
from src.services.problem_service import ProblemService
from src.ui.problem_list_page import _uploaded_file_bytes


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakePdfReader:
    def __init__(self, _data):
        self.pages = [
            _FakePage(
                "Sample Exam 2025\n"
                "Subject: Networks\n"
                "1. What does DNS resolve?\n"
                "A. Names to IP addresses\n"
                "B. Ports to sockets\n"
            )
        ]


def _install_fake_pypdf(monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=_FakePdfReader))


def _database_url():
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir, f"sqlite:///{os.path.join(temp_dir.name, 'test.db')}"


def test_raw_pdf_bytes_are_not_decoded_as_question_text(monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=lambda _data: (_ for _ in ()).throw(RuntimeError("bad pdf"))))
    raw = b"%PDF-1.5\n1 0 obj\nstream\nbinary-ish question text should not leak\nendstream"

    assert extract_pdf_text(raw) == ""


def test_text_based_pdf_extracts_readable_page_text(monkeypatch):
    _install_fake_pypdf(monkeypatch)

    document = extract_pdf_document(b"%PDF-1.5 fake")
    pages = document.pages

    assert document.page_count == 1
    assert document.byte_length > 0
    assert document.starts_with_pdf is True
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "What does DNS resolve?" in pages[0].text
    assert "%PDF-" not in pages[0].text
    assert sum(len(page.text) for page in pages) == 105


def test_zero_question_parser_output_falls_back_to_one_question():
    items = parse_question_text(
        "Read the passage and explain the main network service being described.",
        filename="fallback.pdf",
        title="Fallback Source",
    )

    assert len(items) == 1
    assert items[0].question_number == "1"
    assert items[0].content == "Read the passage and explain the main network service being described."
    assert items[0].metadata["parsing_mode"] == "single_question_fallback"


def test_pdf_syntax_is_rejected_from_preview(monkeypatch):
    class SyntaxPdfReader:
        def __init__(self, _data):
            self.pages = [_FakePage("%PDF-1.5\n1 0 obj\nstream\n/FlateDecode\nendstream")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=SyntaxPdfReader))
    preview = ExamSourceParser().preview(question_pdf_name="raw.pdf", question_pdf=b"%PDF-1.5 raw")

    assert preview.report["questions_detected"] == 0
    assert preview.report["ocr_required"] is True
    assert preview.questions == []


def test_empty_scanned_pdf_returns_ocr_required_state(monkeypatch):
    class EmptyPdfReader:
        def __init__(self, _data):
            self.pages = [_FakePage("")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=EmptyPdfReader))
    preview = ExamSourceParser().preview(question_pdf_name="scan.pdf", question_pdf=b"%PDF-1.5 scan")

    assert preview.report["questions_detected"] == 0
    assert preview.report["page_count"] == 1
    assert preview.report["ocr_required"] is True
    assert preview.report["invalid_pdf"] is False
    assert any("OCR is required" in warning for warning in preview.report["warnings"])


def test_empty_bytes_return_invalid_pdf_error():
    preview = ExamSourceParser().preview(question_pdf_name="empty.pdf", question_pdf=b"")

    assert preview.report["page_count"] == 0
    assert preview.report["uploaded_byte_length"] == 0
    assert preview.report["invalid_pdf"] is True
    assert preview.report["ocr_required"] is False


def test_uploaded_file_cursor_position_does_not_cause_zero_byte_extraction():
    class CursorPdf(BytesIO):
        name = "cursor.pdf"
        type = "application/pdf"

    uploaded = CursorPdf(b"%PDF-1.5 cursor-safe")
    uploaded.read()

    data = _uploaded_file_bytes(uploaded)

    assert len(data) > 0
    assert data.startswith(b"%PDF-")


def test_builtin_pdf_fallback_counts_pages_without_pdf_libraries(monkeypatch):
    monkeypatch.setitem(sys.modules, "fitz", None)
    monkeypatch.setitem(sys.modules, "pdfplumber", None)
    monkeypatch.setitem(sys.modules, "pypdf", None)
    monkeypatch.setitem(sys.modules, "PyPDF2", None)
    raw = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Page >> endobj\n"
        b"2 0 obj << /Length 44 >> stream\n"
        b"BT /F1 12 Tf 72 720 Td (What is 2 plus 2?) Tj ET\n"
        b"endstream endobj\n"
    )

    document = extract_pdf_document(raw)

    assert document.extraction_method == "builtin"
    assert document.page_count == 1
    assert "What is 2 plus 2?" in document.pages[0].text


def test_builtin_pdf_fallback_reports_ocr_required_when_pages_have_no_text(monkeypatch):
    monkeypatch.setitem(sys.modules, "fitz", None)
    monkeypatch.setitem(sys.modules, "pdfplumber", None)
    monkeypatch.setitem(sys.modules, "pypdf", None)
    monkeypatch.setitem(sys.modules, "PyPDF2", None)
    raw = b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n"

    preview = ExamSourceParser().preview(question_pdf_name="image.pdf", question_pdf=raw)

    assert preview.report["page_count"] == 1
    assert preview.report["ocr_required"] is True
    assert preview.report["invalid_pdf"] is False


def test_empty_scanned_pdf_import_returns_explicit_error(monkeypatch):
    class EmptyPdfReader:
        def __init__(self, _data):
            self.pages = [_FakePage("")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=EmptyPdfReader))
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            try:
                ProblemService(session).import_pdf_source(question_pdf_name="scan.pdf", question_pdf=b"%PDF-1.5 scan")
            except ValueError as exc:
                assert "OCR is required" in str(exc)
            else:
                raise AssertionError("Expected OCR-required extraction error")


def test_old_learning_items_schema_is_upgraded_idempotently():
    temp_dir, database_url = _database_url()
    with temp_dir:
        engine = create_engine(database_url, future=True)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE learning_items (
                        id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        content TEXT,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            connection.execute(text("INSERT INTO learning_items (title, content) VALUES ('Legacy', 'Keep me')"))
        engine.dispose()

        init_db(database_url)
        init_db(database_url)

        engine = create_engine(database_url, future=True)
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("learning_items")}
        with engine.connect() as connection:
            row_count = connection.execute(text("SELECT COUNT(*) FROM learning_items WHERE title = 'Legacy'")).scalar_one()
        engine.dispose()

        assert "owner_user_id" in columns
        assert "choices_json" in columns
        assert row_count == 1


def test_pdf_import_persists_questions_after_schema_migration(monkeypatch):
    _install_fake_pypdf(monkeypatch)
    temp_dir, database_url = _database_url()
    with temp_dir:
        engine = create_engine(database_url, future=True)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE learning_items (
                        id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        content TEXT,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
        engine.dispose()

        init_db(database_url)
        with get_session(database_url) as session:
            result = ProblemService(session).import_pdf_source(question_pdf_name="questions.pdf", question_pdf=b"%PDF-1.5 fake")
            count = session.query(LearningItem).filter(LearningItem.source_id == "questions.pdf").count()

        assert result["import_report"]["questions_detected"] == 1
        assert count == 1


def test_pdf_import_persists_question_item_type(monkeypatch):
    _install_fake_pypdf(monkeypatch)
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            result = ProblemService(session).import_pdf_source(question_pdf_name="questions.pdf", question_pdf=b"%PDF-1.5 fake")
            item_id = result["items"][0]["learning_item"]["id"]
            item = session.query(LearningItem).filter(LearningItem.id == item_id).one()

        assert item.item_type == "multiple_choice"
        assert item.question_type == "multiple_choice"


def test_retry_does_not_duplicate_fallback_question(monkeypatch):
    class SingleBlockPdfReader:
        def __init__(self, _data):
            self.pages = [_FakePage("Explain why DNS is needed before a browser opens a web page.")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=SingleBlockPdfReader))
    temp_dir, database_url = _database_url()
    with temp_dir:
        init_db(database_url)
        with get_session(database_url) as session:
            service = ProblemService(session)
            first = service.import_pdf_source(question_pdf_name="fallback.pdf", question_pdf=b"%PDF-1.5 fallback")
            second = service.import_pdf_source(question_pdf_name="fallback.pdf", question_pdf=b"%PDF-1.5 fallback")
            count = session.query(LearningItem).filter(LearningItem.source_id == "fallback.pdf").count()

        assert first["import_report"]["questions_detected"] == 1
        assert second["import_report"]["questions_detected"] == 1
        assert count == 1

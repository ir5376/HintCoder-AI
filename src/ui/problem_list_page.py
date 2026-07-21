from collections.abc import Callable
from html import escape
from urllib.parse import urlparse

import streamlit as st

from src.services.problem_service import ProblemService


def _provider_for(problem: dict) -> str:
    host = urlparse(problem.get("source_reference", "") or "").netloc.lower()
    if "leetcode" in host:
        return "LeetCode"
    if "programmers" in host:
        return "Programmers"
    return {"Notes": "Personal notes", "PDF": "PDF import"}.get(problem.get("source_type"), problem.get("source_type") or "HintCode")


def _add_source() -> str | None:
    source_type = st.session_state.get("new_source_type", "URL")
    question_pdf = st.session_state.get("source_pdf")
    answer_pdf = st.session_state.get("source_answer_pdf")
    value = st.session_state.get("source_url", "").strip() if source_type == "URL" else st.session_state.get("source_note", "").strip()
    if source_type == "URL" and not urlparse(value).scheme:
        return "Enter a complete URL, including http:// or https://."
    if source_type == "PDF" and question_pdf is None:
        return "Choose a question paper PDF before importing it."
    if source_type == "Notes" and not value:
        return "Add a note before importing it."

    reference = value if source_type != "PDF" else question_pdf.name
    name = st.session_state.get("source_name", "").strip() or (urlparse(value).netloc if source_type == "URL" else getattr(question_pdf, "name", "Untitled note"))
    subject = st.session_state.get("source_subject", "Auto detect")
    preview = st.session_state.get("pdf_import_preview", {}) if source_type == "PDF" else {}
    item = {
        "id": f"source-{len(st.session_state.get('added_sources', [])) + 1}",
        "title": name,
        "description": value or f"Imported PDF: {question_pdf.name}",
        "category": subject if subject != "Auto detect" else "Personal learning",
        "difficulty": "To assess",
        "problem_type": "Exam PDF" if source_type == "PDF" else "Learning source",
        "source_type": source_type,
        "source_reference": reference,
        "tags": [subject] if subject != "Auto detect" else ["Personal learning"],
        "provider": _provider_for({"source_reference": reference, "source_type": source_type}),
        "review_status": "Not reviewed",
        "exam_name": st.session_state.get("source_exam_name", "").strip(),
        "year": st.session_state.get("source_year", "").strip(),
        "answer_state": "Verified" if answer_pdf else "No answer",
        "import_preview": preview,
    }
    st.session_state["added_sources"] = [item, *st.session_state.get("added_sources", [])]
    st.session_state["source_added"] = "PDF imported." if source_type == "PDF" else f"{name} was added."
    return None


def _render_pdf_preview() -> None:
    preview = st.session_state.get("pdf_import_preview", {})
    st.markdown("#### Import preview")
    if st.session_state.get("source_answer_pdf") is None:
        st.info("Unverified learning mode: continue with hints, but verified grading and answer analysis are unavailable until an official answer file is added.")
    else:
        st.caption("Official answer file selected. Verification will be available after PDF processing completes.")
    fields = [("Detected subject", preview.get("detected_subject")), ("Questions", preview.get("question_count")), ("Answers", preview.get("answer_count")), ("Matched answers", preview.get("matched_answers")), ("Unmatched questions", preview.get("unmatched_questions"))]
    columns = st.columns(2)
    for index, (label, value) in enumerate(fields):
        columns[index % 2].caption(f"{label}: {value if value is not None else 'Not available'}")
    questions = preview.get("questions", [])
    if questions:
        for question in questions[:4]:
            number = escape(str(question.get("number", "-")))
            state = escape(str(question.get("answer_state", "No answer")))
            excerpt = escape(str(question.get("text", ""))[:120])
            st.markdown(f'<div class="hc-card"><b>Question {number}</b> <span class="hc-chip">{state}</span><p class="hc-muted">{excerpt}</p></div>', unsafe_allow_html=True)
    else:
        st.caption("Question preview will appear after PDF processing.")
    if st.button("Review warnings", key="review_pdf_warnings"):
        st.session_state["show_pdf_warnings"] = True
    if st.session_state.get("show_pdf_warnings"):
        for warning in preview.get("warnings", []):
            st.warning(warning)
    cancel, confirm = st.columns(2)
    with cancel:
        if st.button("Cancel", key="cancel_pdf_import", use_container_width=True):
            st.session_state.pop("show_pdf_preview", None)
            st.session_state.pop("show_pdf_warnings", None)
            st.rerun()
    with confirm:
        if st.button("Confirm import", type="primary", key="confirm_pdf_import", use_container_width=True):
            error = _add_source()
            if error:
                st.error(error)
            else:
                st.session_state.pop("show_pdf_preview", None)
                st.rerun()


@st.dialog("Add Learning Source")
def _render_source_dialog() -> None:
    st.radio("Source type", ["URL", "PDF", "Notes"], horizontal=True, key="new_source_type")
    source_type = st.session_state.get("new_source_type", "URL")
    st.text_input("Name (optional)", key="source_name", placeholder="e.g. Two Sum practice")
    if source_type == "URL":
        st.text_input("URL", key="source_url", placeholder="https://...")
    elif source_type == "PDF":
        st.file_uploader("Question paper PDF", type=["pdf"], key="source_pdf")
        st.file_uploader("Answer / explanation PDF", type=["pdf"], key="source_answer_pdf")
        st.caption("Without an official answer file, hints are available, but automatic grading and answer analysis may be unavailable or AI-inferred.")
        st.selectbox("Subject", ["Auto detect", "Coding", "English", "Mathematics", "Generic multiple choice"], key="source_subject")
        st.text_input("Exam name", key="source_exam_name", placeholder="e.g. 2025 mock exam")
        st.text_input("Year", key="source_year", placeholder="e.g. 2025")
        if st.button("Preview import", key="preview_pdf_import"):
            if st.session_state.get("source_pdf") is None:
                st.warning("Choose a question paper PDF before previewing it.")
            else:
                st.session_state["pdf_import_preview"] = st.session_state.get("pdf_import_preview") or {"detected_subject": st.session_state.get("source_subject", "Auto detect"), "question_count": None, "answer_count": None, "matched_answers": None, "unmatched_questions": None, "warnings": ["PDF processing is not connected yet. Counts and question text will appear after the parser returns a preview."], "questions": []}
                st.session_state["show_pdf_preview"] = True
        if st.session_state.get("show_pdf_preview"):
            _render_pdf_preview()
    else:
        st.text_area("Notes", key="source_note", placeholder="Paste or write the learning material here.", height=120)

    if source_type != "PDF" and st.button("Add Learning Source", type="primary", key="add_source"):
        error = _add_source()
        if error:
            st.error(error)
        else:
            st.rerun()


def render_problem_list(service: ProblemService, on_open_problem: Callable[[int | str], None]) -> None:
    st.markdown('<div class="hc-eyebrow">Learning Sources</div><div class="hc-title">Build your learning library.</div><p class="hc-lede">Add a source once, then learn from it in the same focused workspace.</p>', unsafe_allow_html=True)
    if st.button("Add Learning Source", type="primary"):
        _render_source_dialog()
    if name := st.session_state.pop("source_added", None):
        st.success(name)
    left, right = st.columns(2)
    filters = service.get_filters()
    with left:
        category = st.selectbox("Topic", ["All"] + filters["categories"])
    with right:
        difficulty = st.selectbox("Challenge level", ["All"] + filters["difficulties"])
    problems = service.get_problem_list(category=None if category == "All" else category, difficulty=None if difficulty == "All" else difficulty)
    problems = [*st.session_state.get("added_sources", []), *problems]
    st.caption(f"{len(problems)} learning source(s) available")
    for problem in problems:
        concepts = ", ".join(problem.get("tags", []) or [problem["category"]])
        provider = problem.get("provider") or _provider_for(problem)
        status = st.session_state.get("review_statuses", {}).get(problem["id"], problem.get("review_status", "Not reviewed"))
        st.markdown(f'<div class="hc-card"><div class="hc-item"><div><b>{escape(str(problem["title"]))}</b><br><span class="hc-muted">Source: {escape(str(problem.get("source_type") or "Learning item"))} &nbsp; · &nbsp; Provider: {escape(str(provider))}</span></div><span class="hc-chip">{escape(str(problem.get("difficulty", "To assess")))}</span></div><p class="hc-muted">Concepts: {escape(concepts)} &nbsp; · &nbsp; Status: {escape(str(status))}</p></div>', unsafe_allow_html=True)
        if st.button("Open learning item", key=f"open_problem_{problem['id']}"):
            on_open_problem(problem["id"])

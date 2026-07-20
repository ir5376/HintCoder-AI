from collections.abc import Callable
from html import escape
from urllib.parse import urlparse

import streamlit as st

from src.services.problem_service import ProblemService


def _provider_for(problem: dict) -> str:
    reference = problem.get("source_reference", "") or ""
    host = urlparse(reference).netloc.lower()
    if "leetcode" in host:
        return "LeetCode"
    if "programmers" in host:
        return "Programmers"
    if problem.get("source_type") == "Notes":
        return "Personal notes"
    if problem.get("source_type") == "PDF":
        return "PDF import"
    return problem.get("source_type") or "HintCode"


def _add_source() -> str | None:
    """Add the dialog's current source to this browser session.

    Imported material deliberately stays in session state: importing a source
    should not overwrite the seeded learning library when the app is restarted.
    """
    source_type = st.session_state.get("new_source_type", "URL")
    uploaded_pdf = st.session_state.get("source_pdf")
    value = st.session_state.get("source_url", "").strip() if source_type == "URL" else st.session_state.get("source_note", "").strip()
    if source_type == "URL" and not urlparse(value).scheme:
        return "Enter a complete URL, including http:// or https://."
    if source_type == "PDF" and uploaded_pdf is None:
        return "Choose a PDF before importing it."
    if source_type == "Notes" and not value:
        return "Add a note before importing it."

    reference = value if source_type != "PDF" else uploaded_pdf.name
    description = value or f"Imported PDF: {uploaded_pdf.name}"
    default_name = urlparse(value).netloc if source_type == "URL" else getattr(uploaded_pdf, "name", "Untitled note")
    name = st.session_state.get("source_name", "").strip() or default_name
    source_id = f"source-{len(st.session_state.get('added_sources', [])) + 1}"
    provider = _provider_for({"source_reference": reference, "source_type": source_type})
    added = list(st.session_state.get("added_sources", []))
    added.insert(0, {"id": source_id, "title": name, "description": description, "category": "Personal learning", "difficulty": "To assess", "problem_type": "Learning source", "source_type": source_type, "source_reference": reference, "tags": ["Personal learning"], "provider": provider, "review_status": "Not reviewed"})
    st.session_state["added_sources"] = added
    st.session_state["source_added"] = name
    return None


@st.dialog("Add Learning Source")
def _render_source_dialog() -> None:
    st.radio("Source type", ["URL", "PDF", "Notes"], horizontal=True, key="new_source_type")
    source_type = st.session_state.get("new_source_type", "URL")
    st.text_input("Name (optional)", key="source_name", placeholder="e.g. Two Sum practice")
    if source_type == "URL":
        st.text_input("URL", key="source_url", placeholder="https://...")
    elif source_type == "PDF":
        st.file_uploader("PDF", type=["pdf"], key="source_pdf")
    else:
        st.text_area("Notes", key="source_note", placeholder="Paste or write the learning material here.", height=120)

    if st.button("Add Learning Source", type="primary", key="add_source"):
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
        st.success(f"{name} was added to your learning sources.")

    filter_a, filter_b = st.columns(2)
    filters = service.get_filters()
    with filter_a:
        category = st.selectbox("Topic", ["All"] + filters["categories"])
    with filter_b:
        difficulty = st.selectbox("Challenge level", ["All"] + filters["difficulties"])
    problems = service.get_problem_list(category=None if category == "All" else category, difficulty=None if difficulty == "All" else difficulty)
    problems = list(st.session_state.get("added_sources", [])) + problems
    st.caption(f"{len(problems)} learning source(s) available")
    if not problems:
        st.info("Add your first learning source to begin.")
        return
    for problem in problems:
        concepts = ", ".join(problem.get("tags", []) or [problem["category"]])
        provider = problem.get("provider") or _provider_for(problem)
        status = st.session_state.get("review_statuses", {}).get(problem["id"], problem.get("review_status", "Not reviewed"))
        st.markdown(f'<div class="hc-card"><div class="hc-item"><div><b>{escape(str(problem["title"]))}</b><br><span class="hc-muted">Source: {escape(str(problem.get("source_type") or "Learning item"))} &nbsp; · &nbsp; Provider: {escape(str(provider))}</span></div><span class="hc-chip">{escape(str(problem.get("difficulty", "To assess")))}</span></div><p class="hc-muted">Concepts: {escape(concepts)} &nbsp; · &nbsp; Status: {escape(str(status))}</p></div>', unsafe_allow_html=True)
        if st.button("Open learning item", key=f"open_problem_{problem['id']}"):
            on_open_problem(problem["id"])

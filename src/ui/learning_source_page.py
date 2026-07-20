from __future__ import annotations

import streamlit as st


def render_learning_source_page() -> None:
    st.subheader("Learning Source")
    st.caption("Import a learning source without changing the existing learning flow.")

    source_type = st.radio(
        "Source type",
        ["URL", "PDF", "Notes"],
        horizontal=True,
        key="learning_source_type",
    )

    if source_type == "URL":
        _render_url_source_form()
    elif source_type == "PDF":
        _render_pdf_source_form()
    else:
        _render_notes_source_form()


def _render_url_source_form() -> None:
    with st.form("learning_source_url_form"):
        source_url = st.text_input("URL", key="learning_source_url")
        title_hint = st.text_input("Title", key="learning_source_url_title")
        submitted = st.form_submit_button("Import URL")

    if submitted:
        st.session_state["pending_learning_source"] = {
            "source_type": "url",
            "url": source_url.strip(),
            "title": title_hint.strip(),
        }


def _render_pdf_source_form() -> None:
    with st.form("learning_source_pdf_form"):
        uploaded_file = st.file_uploader("PDF", type=["pdf"], key="learning_source_pdf")
        title_hint = st.text_input("Title", key="learning_source_pdf_title")
        submitted = st.form_submit_button("Import PDF")

    if submitted:
        st.session_state["pending_learning_source"] = {
            "source_type": "pdf",
            "filename": uploaded_file.name if uploaded_file is not None else "",
            "title": title_hint.strip(),
            "uploaded_file": uploaded_file,
        }


def _render_notes_source_form() -> None:
    with st.form("learning_source_notes_form"):
        title = st.text_input("Title", key="learning_source_notes_title")
        notes = st.text_area("Notes", height=220, key="learning_source_notes")
        submitted = st.form_submit_button("Import Notes")

    if submitted:
        st.session_state["pending_learning_source"] = {
            "source_type": "notes",
            "title": title.strip(),
            "notes": notes.strip(),
        }

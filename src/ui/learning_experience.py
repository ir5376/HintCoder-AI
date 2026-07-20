"""Learning-first presentation helpers for the HintCode Streamlit app."""

from __future__ import annotations

import streamlit as st


def inject_learning_styles() -> None:
    """Apply the shared, responsive visual language used across the app."""
    st.markdown("""<style>
      .block-container { max-width: 1220px; padding-top: 2.25rem; padding-bottom: 3rem; }
      [data-testid="stSidebar"] { background: #10233b; }
      [data-testid="stSidebar"] * { color: #f6f8fc !important; }
      [data-testid="stSidebar"] .stButton button { border-color: rgba(255,255,255,.32); }
      .hc-eyebrow { color:#5069a8; font-size:.74rem; font-weight:750; letter-spacing:.11em; text-transform:uppercase; }
      .hc-title { color:#14233b; font-size:clamp(2rem,4vw,3rem); font-weight:780; line-height:1.08; margin:.22rem 0 .45rem; }
      .hc-lede { color:#617086; font-size:1.03rem; margin:0 0 1.5rem; }
      .hc-card { background:#fff; border:1px solid #e1e8f1; border-radius:16px; padding:1.1rem 1.2rem; margin-bottom:.9rem; box-shadow:0 6px 18px rgba(20,35,59,.045); }
      .hc-mission { background:linear-gradient(120deg,#18385a,#326287); border-radius:20px; color:#fff; padding:1.5rem; margin-bottom:1rem; }
      .hc-mission h3, .hc-mission p { color:#fff !important; margin:.3rem 0; }
      .hc-label { color:#67758b; font-size:.76rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
      .hc-value { color:#172a45; font-size:1.65rem; font-weight:780; margin:.15rem 0; }
      .hc-muted { color:#68768a; font-size:.9rem; }
      .hc-progress { height:8px; border-radius:999px; overflow:hidden; background:#e8eef4; margin:.7rem 0 .35rem; }
      .hc-progress > div { height:100%; border-radius:999px; background:#4e7da6; }
      .hc-item { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.8rem 0; border-bottom:1px solid #edf1f5; }
      .hc-item:last-child { border-bottom:0; }
      .hc-chip { color:#315c82; background:#eaf2f8; border-radius:999px; font-size:.78rem; font-weight:700; padding:.25rem .55rem; white-space:nowrap; }
      @media(max-width: 640px) { .block-container { padding:1.25rem 1rem 2rem; } .hc-mission { padding:1.15rem; } }
    </style>""", unsafe_allow_html=True)


def _heading(eyebrow: str, title: str, lede: str) -> None:
    st.markdown(f'<div class="hc-eyebrow">{eyebrow}</div><div class="hc-title">{title}</div><p class="hc-lede">{lede}</p>', unsafe_allow_html=True)


def _card(label: str, value: str, note: str) -> None:
    st.markdown(f'<div class="hc-card"><div class="hc-label">{label}</div><div class="hc-value">{value}</div><div class="hc-muted">{note}</div></div>', unsafe_allow_html=True)


def _set_problem_route(problem_id: int = 1) -> None:
    st.query_params["page"] = "detail"
    st.query_params["problem_id"] = str(problem_id)


def _history() -> list[dict]:
    return list(st.session_state.get("hint_history", []))


def _render_empty(title: str, message: str, action_label: str | None = None) -> None:
    st.markdown(f'<div class="hc-card"><b>{title}</b><p class="hc-muted">{message}</p></div>', unsafe_allow_html=True)
    if action_label and st.button(action_label, type="primary", use_container_width=True):
        _set_problem_route()
        st.rerun()


def render_home() -> None:
    history = _history()
    _heading("Learning home", "Make one useful move today.", "HintCode keeps the focus on your thinking: understand, attempt, reflect, then return when it matters.")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown('<div class="hc-mission"><div class="hc-label" style="color:#c9deed">Today\'s mission</div><h3>Work through one problem with intention.</h3><p>Read the problem, make an attempt, and ask for a progressive hint only when you need a nudge.</p></div>', unsafe_allow_html=True)
        if st.button("Open a learning item", type="primary", use_container_width=True, key="home_open_problem"):
            _set_problem_route(); st.rerun()
        st.markdown("#### Review queue")
        _render_empty("Nothing scheduled for review", "Reflections and completed learning items will appear here when review scheduling is available.")
    with right:
        _card("XP", "Not available yet", "XP is shown once it is connected to your learning record.")
        _card("Weakness", "Still learning", "Complete a few attempts and reflections to reveal a reliable focus area.")
        progress = min(len(history) * 20, 100)
        plural = "s" if len(history) != 1 else ""
        st.markdown(f'<div class="hc-card"><div class="hc-label">Learning progress</div><div class="hc-value">{len(history)} hint{plural} explored</div><div class="hc-progress"><div style="width:{progress}%"></div></div><div class="hc-muted">Your current session activity</div></div>', unsafe_allow_html=True)


def render_review_queue() -> None:
    _heading("Learning rhythm", "Review queue", "Return to ideas at the right time. Your scheduled reviews will appear here.")
    _render_empty("Your queue is clear", "There are no review items to work through right now. Start a problem to build your learning history.", "Open a learning item")


def render_learning_history() -> None:
    history = _history()
    _heading("Your record", "Learning history", "A lightweight record of the hints you have explored in this session.")
    if not history:
        _render_empty("No learning activity yet", "When you request a hint while working on a problem, it will be listed here.", "Open a learning item")
        return
    for entry in history:
        title = entry.get("problem_title") or "Learning item"
        level = entry.get("hint_level", 1)
        language = entry.get("programming_language", "Python")
        text = entry.get("generated_hint", "")
        st.markdown(f'<div class="hc-card"><div class="hc-item"><b>{title}</b><span class="hc-chip">Hint {level} · {language}</span></div><div class="hc-muted">{text}</div></div>', unsafe_allow_html=True)


PAGES = {"Home": render_home, "Review Queue": render_review_queue, "Learning History": render_learning_history}


def render_learning_page(page: str) -> None:
    PAGES.get(page, render_home)()

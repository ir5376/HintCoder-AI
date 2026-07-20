"""Learning-first presentation helpers for the HintCode Streamlit app."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def inject_learning_styles() -> None:
    st.markdown("""<style>
      .block-container { max-width: 1220px; padding-top: 2.25rem; padding-bottom: 3rem; }
      [data-testid="stSidebar"] { background: #10233b; }
      [data-testid="stSidebar"] * { color: #f6f8fc !important; }
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
      @media(max-width: 900px) { .block-container { padding-left:1.25rem; padding-right:1.25rem; } }
      @media(max-width: 640px) { .block-container { padding:1.25rem 1rem 2rem; } .hc-mission { padding:1.15rem; } .hc-card { padding:1rem; } .hc-item { align-items:flex-start; flex-direction:column; gap:.55rem; } .hc-chip { align-self:flex-start; } }
    </style>""", unsafe_allow_html=True)


def render_home(on_open_library: Callable[[], None]) -> None:
    history = list(st.session_state.get("hint_history", []))
    st.markdown('<div class="hc-eyebrow">Learning home</div><div class="hc-title">Learn from what you collect.</div><p class="hc-lede">Add a source, make an attempt, and return when it matters.</p>', unsafe_allow_html=True)
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown('<div class="hc-mission"><div class="hc-label" style="color:#c9deed">Today\'s mission</div><h3>Work through one problem with intention.</h3><p>Read the problem, make an attempt, and ask for a progressive hint only when you need a nudge.</p></div>', unsafe_allow_html=True)
        if st.button("Browse learning sources", type="primary", use_container_width=True):
            on_open_library()
        st.markdown("#### Review queue")
        st.markdown('<div class="hc-card"><b>Nothing scheduled for review</b><p class="hc-muted">Reflections and completed learning items will appear here when review scheduling is available.</p></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="hc-card"><div class="hc-label">XP</div><div class="hc-value">Not available yet</div><div class="hc-muted">XP is shown once it is connected to your learning record.</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="hc-card"><div class="hc-label">Weakness</div><div class="hc-value">Still learning</div><div class="hc-muted">Complete attempts and reflections to reveal a focus area.</div></div>', unsafe_allow_html=True)
        progress = min(len(history) * 20, 100)
        plural = "s" if len(history) != 1 else ""
        st.markdown(f'<div class="hc-card"><div class="hc-label">Learning progress</div><div class="hc-value">{len(history)} hint{plural} explored</div><div class="hc-progress"><div style="width:{progress}%"></div></div><div class="hc-muted">Your current session activity</div></div>', unsafe_allow_html=True)

from collections.abc import Callable

import streamlit as st

from src.services.problem_service import ProblemService


def render_problem_list(service: ProblemService, on_open_problem: Callable[[int], None]) -> None:
    st.markdown('<div class="hc-eyebrow">Problem library</div><div class="hc-title">Choose a learning item</div><p class="hc-lede">Pick a problem that matches the concept you want to practise.</p>', unsafe_allow_html=True)
    filter_a, filter_b = st.columns(2)
    filters = service.get_filters()
    with filter_a:
        category = st.selectbox("Topic", ["All"] + filters["categories"])
    with filter_b:
        difficulty = st.selectbox("Challenge level", ["All"] + filters["difficulties"])
    problems = service.get_problem_list(category=None if category == "All" else category, difficulty=None if difficulty == "All" else difficulty)
    st.caption(f"{len(problems)} learning item(s) available")
    if not problems:
        st.info("No learning items match these filters. Try widening your selection.")
        return
    for problem in problems:
        st.markdown(f'<div class="hc-card"><div class="hc-item"><div><b>{problem["title"]}</b><br><span class="hc-muted">{problem["category"]} | {problem["difficulty"]} | {problem["problem_type"]}</span></div><span class="hc-chip">Learning item</span></div><p class="hc-muted">{problem["description"]}</p></div>', unsafe_allow_html=True)
        if st.button("Open problem", key=f"open_problem_{problem['id']}"):
            on_open_problem(problem["id"])

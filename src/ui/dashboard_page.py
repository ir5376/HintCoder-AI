from __future__ import annotations

import streamlit as st

from src.learning_engine.engine import LearningEngine
from src.services.learning_coach_service import LearningCoachService


def render_dashboard(
    service: LearningCoachService,
    *,
    learning_engine: LearningEngine | None = None,
    current_module: str = "coding",
) -> None:
    dashboard = learning_engine.dashboard() if learning_engine is not None else service.get_dashboard()

    st.subheader("Home")
    st.write(f"Current module: **{current_module.replace('_', ' ').title()}**")

    mission_col, xp_col, review_col = st.columns(3)
    with mission_col:
        missions = dashboard.get("missions", [])
        st.markdown("### Today's Mission")
        st.write(missions[0]["title"] if missions else "Complete one focused practice session.")
    with xp_col:
        xp = dashboard.get("xp", {"current_xp": dashboard["learning_scores"]["learning_score"]})
        st.markdown("### XP")
        st.metric("Current XP", xp["current_xp"])
    with review_col:
        st.markdown("### Review Queue")
        st.metric("Pending", len(dashboard.get("next_reviews", [])))

    learning_col, exam_col = st.columns(2)
    with learning_col:
        learning_card = dashboard["learning_mode_card"]
        st.markdown("### Learning Mode")
        st.write(learning_card["message"])
        st.metric("Solved", learning_card["solved_count"])
        st.write(f"Hint dependency: **{learning_card['hint_dependency']}**")

    with exam_col:
        exam_card = dashboard["exam_mode_card"]
        st.markdown("### Exam Mode")
        st.write(exam_card["message"])
        st.metric("Attempts", exam_card["attempts"])
        st.write(f"Average score: **{exam_card['average_score']}**")

    scores = dashboard["learning_scores"]
    score_cols = st.columns(4)
    score_cols[0].metric("Learning Score", scores["learning_score"])
    score_cols[1].metric("Thinking Score", scores["thinking_score"])
    score_cols[2].metric("Independence Score", scores["independence_score"])
    score_cols[3].metric("Review Readiness", scores["review_readiness"])

    st.markdown("### Hint Analytics")
    hint_analytics = dashboard["hint_analytics"]
    st.write(hint_analytics["coach_language"])
    st.metric("Average hint level", hint_analytics["average_hint_level"])
    topic_col, difficulty_col = st.columns(2)
    with topic_col:
        st.write("Average hints per topic")
        st.json(hint_analytics["average_hints_per_topic"])
    with difficulty_col:
        st.write("Hints by difficulty")
        st.json(hint_analytics["hints_by_difficulty"])

    st.markdown("### Reflection History")
    reflections = dashboard["reflection_history"]
    if not reflections:
        st.write("No reflections yet.")
    else:
        for item in reflections:
            reflection = item["reflection"]
            title = item["problem_title"] or item["topic"] or "Solved problem"
            with st.expander(title, expanded=False):
                st.write(f"Why did you need the hint? {reflection.get('why_did_you_need_the_hint', '')}")
                st.write(f"What concept was missing? {reflection.get('what_concept_was_missing', '')}")
                st.write(f"What should you remember? {reflection.get('what_should_you_remember', '')}")
                st.write(
                    "What similar problem should you solve next? "
                    f"{reflection.get('what_similar_problem_should_you_solve_next', '')}"
                )

    st.markdown("### Learning DNA")
    st.json(
        {
            "summary": dashboard.get("profile_summary", []),
            "adaptive_difficulty": dashboard.get("adaptive_difficulty", {}),
        }
    )

    st.markdown("### Thought Profile")
    st.json({"summary": dashboard.get("thought_summary", [])})

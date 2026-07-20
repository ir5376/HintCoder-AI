import streamlit as st

from src.config import get_settings
from src.database import get_session, init_db
from src.services.hint_service import HintService
from src.services.problem_service import ProblemService
from src.ui.learning_experience import inject_learning_styles, render_home
from src.ui.learner_dashboard import render_attendance, render_home_dashboard, render_leaderboard, render_profile_selector, render_review_queue
from src.ui.navigation import ATTENDANCE, DETAIL, HOME, LEADERBOARD, LEARNING, LIBRARY, REVIEW_QUEUE, current_page, go_back, initialize, navigate
from src.ui.problem_detail_page import render_learning_workspace, render_problem_detail
from src.ui.problem_list_page import render_problem_list


def _rerun_after(action) -> None:
    action()
    st.rerun()


def _render_navigation() -> None:
    page = current_page()
    label = {HOME: "Home", LIBRARY: "Learning Sources", DETAIL: "Learning Item", LEARNING: "Learning Item", ATTENDANCE: "Attendance", LEADERBOARD: "Leaderboard", REVIEW_QUEUE: "Review Queue"}[page]
    left, right = st.columns([1, 5])
    with left:
        if page == HOME:
            st.button("Back", disabled=True, use_container_width=True, help="You are at the start of your learning path.")
        elif st.button("Back", use_container_width=True):
            _rerun_after(go_back)
    with right:
        st.caption(f"Home / {label}" if page != HOME else "Home")


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)
    st.set_page_config(page_title="HintCode | Learn by thinking", page_icon="H", layout="wide")
    inject_learning_styles()
    initialize()

    with get_session(settings.database_url) as session:
        service = ProblemService(session)
        hint_service = HintService(session)
        st.sidebar.markdown("## HintCode")
        st.sidebar.caption("An AI learning OS for deliberate practice")
        render_profile_selector()
        if st.sidebar.button("Home", use_container_width=True):
            _rerun_after(lambda: navigate(HOME))
        if st.sidebar.button("Learning Sources", use_container_width=True):
            _rerun_after(lambda: navigate(LIBRARY))
        if st.sidebar.button("Attendance", use_container_width=True):
            _rerun_after(lambda: navigate(ATTENDANCE))
        if st.sidebar.button("Leaderboard", use_container_width=True):
            _rerun_after(lambda: navigate(LEADERBOARD))
        if st.sidebar.button("Review Queue", use_container_width=True):
            _rerun_after(lambda: navigate(REVIEW_QUEUE))
        st.sidebar.divider()
        st.sidebar.caption(f"Provider: {st.session_state['selected_provider']}")
        st.sidebar.caption("Your learning data stays private by default.")

        _render_navigation()
        page = current_page()
        problem_id = st.session_state.get("selected_problem_id")
        if page == HOME:
            render_home(on_open_library=lambda: _rerun_after(lambda: navigate(LIBRARY)))
            render_home_dashboard()
        elif page == LIBRARY:
            render_problem_list(service, on_open_problem=lambda item_id: _rerun_after(lambda: navigate(DETAIL, problem_id=item_id)))
        elif page == DETAIL:
            render_problem_detail(
                service,
                problem_id=problem_id,
                on_start_learning=lambda: _rerun_after(lambda: navigate(LEARNING)),
            )
        elif page == LEARNING:
            render_learning_workspace(service, problem_id=problem_id, hint_service=hint_service)
        elif page == ATTENDANCE:
            render_attendance()
        elif page == LEADERBOARD:
            render_leaderboard()
        else:
            render_review_queue()


if __name__ == "__main__":
    main()

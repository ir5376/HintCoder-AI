import streamlit as st

from src.config import get_settings
from src.database import init_db, get_session
from src.services.hint_service import HintService
from src.services.problem_service import ProblemService
from src.ui.problem_detail_page import render_problem_detail
from src.ui.problem_list_page import render_problem_list
from src.ui.learning_experience import PAGES, inject_learning_styles, render_learning_page


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)

    st.set_page_config(page_title="HintCode · Learn by solving", page_icon="✦", layout="wide")
    inject_learning_styles()

    with get_session(settings.database_url) as session:
        service = ProblemService(session)
        hint_service = HintService(session)

        query_params = st.query_params
        if query_params.get("page") == "detail" and query_params.get("problem_id") is not None:
            render_problem_detail(service, int(query_params["problem_id"]), hint_service=hint_service)
            return

        st.sidebar.markdown("## ✦ HintCode")
        st.sidebar.caption("Practice that remembers you")
        learning_pages = list(PAGES.keys())
        if "learning_page" not in st.session_state:
            st.session_state["learning_page"] = "Home"
        if "show_problem_library" not in st.session_state:
            st.session_state["show_problem_library"] = False
        page = st.sidebar.radio(
            "LEARN",
            learning_pages,
            key="learning_page",
            on_change=lambda: st.session_state.update(show_problem_library=False),
        )
        st.sidebar.divider()
        workspace = st.sidebar.radio("SOLVE", ["Problem Library", "Open a problem"], key="workspace_page")
        st.sidebar.caption("Your learning data stays private by default.")
        if workspace == "Problem Library" and st.sidebar.button("Browse problem library", use_container_width=True):
            st.session_state["show_problem_library"] = True
            st.rerun()
        if workspace == "Open a problem" and st.sidebar.button("Open problem workspace", use_container_width=True):
            st.query_params["page"] = "detail"
            st.query_params["problem_id"] = "1"
            st.rerun()

        if st.session_state["show_problem_library"]:
            render_problem_list(service)
        else:
            render_learning_page(page)


if __name__ == "__main__":
    main()

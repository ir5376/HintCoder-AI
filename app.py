import streamlit as st

from src.config import get_settings
from src.database import init_db, get_session
from src.services.problem_service import ProblemService
from src.ui.problem_detail_page import render_problem_detail
from src.ui.problem_list_page import render_problem_list


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)

    st.set_page_config(page_title="HintCode", layout="wide")
    st.title("HintCode: Python 코딩 학습")

    with get_session(settings.database_url) as session:
        service = ProblemService(session)

        page = st.sidebar.selectbox("페이지", ["문제 목록", "문제 상세"])
        if page == "문제 목록":
            render_problem_list(service)
        else:
            render_problem_detail(service)


if __name__ == "__main__":
    main()

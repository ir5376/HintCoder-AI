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
    st.title("HintCode: Learn Python Coding")

    with get_session(settings.database_url) as session:
        service = ProblemService(session)

        query_params = st.query_params
        if query_params.get("page") == "detail" and query_params.get("problem_id") is not None:
            render_problem_detail(service, int(query_params["problem_id"]))
            return


        page = st.sidebar.selectbox("Page", ["Problem List", "Problem Detail"])
        if page == "Problem List":
            render_problem_list(service)
        else:
            render_problem_detail(service)


if __name__ == "__main__":
    main()

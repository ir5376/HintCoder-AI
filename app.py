import streamlit as st

from src.config import get_settings
from src.database import init_db, get_session
from src.services.hint_service import HintService
from src.services.problem_service import ProblemService
from src.ui.problem_detail_page import render_external_problem_mode
from src.ui.problem_detail_page import render_problem_detail
from src.ui.problem_list_page import render_problem_list
from src.ui.query_params_helper import get_problem_context_from_query_params


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)

    st.set_page_config(page_title="HintCode", layout="wide")
    st.title("HintCode: Learn Python Coding")

    with get_session(settings.database_url) as session:
        service = ProblemService(session)
        hint_service = HintService(session)

        query_params = st.query_params
        problem_context = get_problem_context_from_query_params()

        if problem_context["problem_title"] and problem_context["problem_url"]:
            render_external_problem_mode(
                hint_service=hint_service,
                problem_title=problem_context["problem_title"],
                problem_url=problem_context["problem_url"],
            )
            return

        if query_params.get("page") == "detail" and query_params.get("problem_id") is not None:
            render_problem_detail(
                service,
                int(query_params["problem_id"]),
                hint_service=hint_service,
                external_title=problem_context["problem_title"],
                external_url=problem_context["problem_url"],
            )
            return

        page = st.sidebar.selectbox("Page", ["Problem List", "Problem Detail"])
        if page == "Problem List":
            render_problem_list(service)
        else:
            render_problem_detail(
                service,
                hint_service=hint_service,
                external_title=problem_context["problem_title"],
                external_url=problem_context["problem_url"],
            )


if __name__ == "__main__":
    main()

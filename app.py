import streamlit as st

from src.config import get_settings
from src.content_modules.registry import ContentModuleRegistry
from src.database import init_db, get_session
from src.learning_engine.engine import LearningEngine
from src.services.hint_service import HintService
from src.services.learning_coach_service import LearningCoachService
from src.services.problem_service import ProblemService
from src.ui.dashboard_page import render_dashboard
from src.ui.module_practice_page import render_module_practice
from src.ui.problem_detail_page import render_external_problem_mode
from src.ui.problem_detail_page import render_problem_detail
from src.ui.problem_list_page import render_problem_list
from src.ui.query_params_helper import get_problem_context_from_query_params


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)

    st.set_page_config(page_title="Nextep", layout="wide")
    st.title("Nextep")
    st.caption(
        "AI Learning Engine. Today we support Coding and Information Processing Engineer. "
        "The same engine can support interviews, certifications, college entrance exams, and language learning."
    )

    with get_session(settings.database_url) as session:
        service = ProblemService(session)
        hint_service = HintService(session)
        learning_coach_service = LearningCoachService(session)
        learning_engine = LearningEngine(session)
        content_registry = ContentModuleRegistry()
        module_options = content_registry.list_modules()
        module_labels = {item["display_name"]: item["module_id"] for item in module_options}
        selected_module_label = st.sidebar.selectbox("Current Module", list(module_labels.keys()), index=0)
        selected_module_id = module_labels[selected_module_label]

        app_mode = st.sidebar.radio("Mode", ["Learning Mode", "Exam Mode"], index=0)
        st.session_state["hintcode_mode"] = app_mode
        st.session_state["nextep_module"] = selected_module_id
        if app_mode == "Learning Mode":
            st.sidebar.caption("Hints are learning tools. XP is never reduced for using them.")
        else:
            st.sidebar.caption("Exam attempts are tracked separately from Learning Mode statistics.")
            st.sidebar.number_input("Timer (minutes)", min_value=1, max_value=240, value=30, key="exam_timer_minutes")
            st.sidebar.checkbox("Hints available", value=True, key="exam_hints_available")
            st.sidebar.checkbox("Adjust score when hints are used", value=False, key="exam_hint_penalty_enabled")
            st.sidebar.number_input("Score adjustment per hint", min_value=0, max_value=50, value=5, key="exam_hint_penalty_points")

        query_params = st.query_params
        problem_context = get_problem_context_from_query_params()

        if problem_context["problem_title"] and problem_context["problem_url"]:
            render_external_problem_mode(
                hint_service=hint_service,
                problem_title=problem_context["problem_title"],
                problem_url=problem_context["problem_url"],
                language=problem_context["language"],
                app_mode=app_mode,
            )
            return

        if query_params.get("page") == "detail" and query_params.get("problem_id") is not None:
            render_problem_detail(
                service,
                int(query_params["problem_id"]),
                hint_service=hint_service,
                app_mode=app_mode,
                preferred_language=problem_context["language"],
                external_title=problem_context["problem_title"],
                external_url=problem_context["problem_url"],
            )
            return

        page = st.sidebar.selectbox("Page", ["Home", "Practice", "Problem List", "Problem Detail"])
        if page == "Home":
            render_dashboard(
                learning_coach_service,
                learning_engine=learning_engine,
                current_module=selected_module_id,
            )
        elif page == "Practice" and selected_module_id != "coding":
            render_module_practice(
                registry=content_registry,
                learning_engine=learning_engine,
                hint_service=hint_service,
                selected_module_id=selected_module_id,
                app_mode=app_mode,
            )
        elif page == "Practice":
            render_problem_detail(
                service,
                hint_service=hint_service,
                app_mode=app_mode,
                preferred_language=problem_context["language"],
                external_title=problem_context["problem_title"],
                external_url=problem_context["problem_url"],
            )
        elif page == "Problem List":
            render_problem_list(service)
        else:
            render_problem_detail(
                service,
                hint_service=hint_service,
                app_mode=app_mode,
                preferred_language=problem_context["language"],
                external_title=problem_context["problem_title"],
                external_url=problem_context["problem_url"],
            )


if __name__ == "__main__":
    main()

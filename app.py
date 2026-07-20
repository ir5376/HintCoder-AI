import streamlit as st

from src.config import get_settings
from src.database import get_session, init_db
from src.services.hint_service import HintService
from src.services.problem_import_service import ProblemImportService
from src.services.problem_service import ProblemService
from src.ui.learning_experience import PAGES, inject_learning_styles, render_learning_page
from src.ui.problem_detail_page import render_problem_detail
from src.ui.problem_list_page import render_problem_list


PROVIDER_IMPORT_KEYS = ("provider", "problem_title", "problem_url")
def _get_query_value(query_params, key: str) -> str:
    value = query_params.get(key, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def _get_provider_import_params(query_params, import_service: ProblemImportService) -> dict | None:
    if not all(_get_query_value(query_params, key) for key in PROVIDER_IMPORT_KEYS):
        return None

    payload = import_service.import_problem(
        {
            "provider": _get_query_value(query_params, "provider"),
            "problem_id": _get_query_value(query_params, "problem_id"),
            "title": _get_query_value(query_params, "problem_title"),
            "url": _get_query_value(query_params, "problem_url"),
            "difficulty": _get_query_value(query_params, "difficulty"),
            "language": _get_query_value(query_params, "language"),
            "starter_code": _get_query_value(query_params, "starter_code"),
            "metadata": {},
        }
    )
    return _provider_payload_to_import_params(import_service, payload)


def _set_provider_import_query_params(import_params: dict[str, str]) -> None:
    st.query_params.clear()
    st.query_params["provider"] = import_params["provider"]
    st.query_params["problem_id"] = import_params["provider_problem_id"]
    st.query_params["problem_title"] = import_params["title"]
    st.query_params["problem_url"] = import_params["url"]
    st.query_params["difficulty"] = import_params.get("difficulty") or "Unknown"
    if import_params.get("language"):
        st.query_params["language"] = import_params["language"]


def _build_url_import_params(
    import_service: ProblemImportService,
    problem_url: str,
    title: str,
    language: str,
    provider_hint: str = "",
) -> dict[str, str]:
    payload = import_service.import_problem_from_url(
        problem_url,
        {
            "title": title.strip(),
            "language": language,
        },
        provider_hint=provider_hint,
    )
    return _provider_payload_to_import_params(import_service, payload)


def _provider_payload_to_import_params(import_service: ProblemImportService, payload) -> dict:
    internal_problem = import_service.normalize_internal_problem(payload)
    return {
        "provider": internal_problem.provider,
        "provider_problem_id": internal_problem.provider_problem_id,
        "title": internal_problem.title,
        "url": internal_problem.provider_url,
        "difficulty": internal_problem.difficulty,
        "language": payload.language,
        "starter_code": internal_problem.starter_code,
        "metadata": internal_problem.metadata,
        "description": internal_problem.description,
        "tags": internal_problem.tags,
        "language_support": internal_problem.language_support,
    }


def _provider_import_signature(import_params: dict | None) -> tuple[str, str, str] | None:
    if import_params is None:
        return None
    return (
        str(import_params.get("provider") or ""),
        str(import_params.get("provider_problem_id") or ""),
        str(import_params.get("url") or ""),
    )


def _init_navigation() -> None:
    st.session_state.setdefault("current_view", "home")
    st.session_state.setdefault("navigation_stack", ["home"])
    st.session_state.setdefault("show_problem_library", False)


def _navigate_to(view: str, **state) -> None:
    current_view = st.session_state.get("current_view", "home")
    stack = list(st.session_state.get("navigation_stack", ["home"]))
    if not stack or stack[-1] != current_view:
        stack.append(current_view)
    if stack[-1] != view:
        stack.append(view)
    st.session_state["navigation_stack"] = stack
    st.session_state["current_view"] = view
    for key, value in state.items():
        st.session_state[key] = value


_dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


if _dialog is not None:

    @_dialog("Import Problem")
    def render_import_problem_dialog(service: ProblemService, import_service: ProblemImportService) -> None:
        _render_import_problem_dialog_body(service, import_service)

else:

    def render_import_problem_dialog(service: ProblemService, import_service: ProblemImportService) -> None:
        st.warning("Import Problem dialog is not available in this Streamlit version.")
        _render_import_problem_dialog_body(service, import_service)


def _render_import_problem_dialog_body(service: ProblemService, import_service: ProblemImportService) -> None:
    providers = import_service.provider_registry.list_importable_providers()
    provider_options = {provider.display_name: provider for provider in providers}
    provider_label = st.selectbox("Provider", list(provider_options.keys()))
    selected_provider = provider_options[provider_label]
    import_methods = []
    if selected_provider.supports_url:
        import_methods.append("URL")
    if selected_provider.supports_search:
        import_methods.append("Problem search")
    import_method = st.radio("Import by", import_methods, horizontal=True)
    language = st.selectbox("Language", selected_provider.supported_languages)

    if import_method == "Problem search":
        st.text_input(f"Search {provider_label} problem")
        st.info("Provider search will be connected when the public provider APIs are available. Import by URL for now.")
        return

    with st.form("provider_url_import_form"):
        problem_url = st.text_input("Problem URL")
        title = st.text_input("Problem title")
        submitted = st.form_submit_button("Import")

    if not submitted:
        return

    if not problem_url.strip():
        st.error("Problem URL is required.")
        return

    try:
        import_params = _build_url_import_params(
            import_service,
            problem_url,
            title,
            language,
            provider_hint=selected_provider.provider_id if selected_provider.provider_id == "custom" else "",
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    imported_problem = service.import_provider_problem(**import_params)
    st.session_state["show_import_problem_dialog"] = False
    st.session_state["show_problem_detail_back_button"] = True
    _navigate_to("detail", current_problem_id=int(imported_problem["id"]))
    st.session_state["last_provider_import_signature"] = _provider_import_signature(import_params)
    _set_provider_import_query_params(import_params)
    st.rerun()


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)

    st.set_page_config(page_title="HintCode \u00b7 Learn by solving", page_icon="\u2726", layout="wide")
    inject_learning_styles()

    with get_session(settings.database_url) as session:
        service = ProblemService(session)
        hint_service = HintService(session)
        import_service = ProblemImportService()
        _init_navigation()

        query_params = st.query_params
        try:
            provider_import_params = _get_provider_import_params(query_params, import_service)
        except ValueError as exc:
            st.error(str(exc))
            provider_import_params = None

        provider_signature = _provider_import_signature(provider_import_params)
        should_open_provider_import = (
            provider_import_params is not None
            and (
                provider_signature != st.session_state.get("last_provider_import_signature")
                or st.session_state.get("current_problem_id") is None
            )
        )
        if should_open_provider_import:
            imported_problem = service.import_provider_problem(**provider_import_params)
            _navigate_to("detail", current_problem_id=int(imported_problem["id"]))
            st.session_state["last_provider_import_signature"] = provider_signature
            render_problem_detail(
                service,
                int(imported_problem["id"]),
                hint_service=hint_service,
                show_back_button=True,
            )
            return

        if st.session_state.get("current_view") == "detail" and st.session_state.get("current_problem_id") is not None:
            render_problem_detail(
                service,
                int(st.session_state["current_problem_id"]),
                hint_service=hint_service,
                show_back_button=True,
            )
            return

        if st.session_state.get("current_view") not in {"home", "library"}:
            st.session_state["current_view"] = "home"

        if query_params.get("page") == "detail" and query_params.get("problem_id") is not None:
            try:
                query_problem_id = int(query_params["problem_id"])
            except (TypeError, ValueError):
                query_problem_id = None
            if query_problem_id is None:
                st.session_state["current_view"] = "home"
                st.session_state["show_problem_library"] = False
            else:
                suppress_detail_query = (
                    st.session_state.get("suppress_detail_query")
                    and st.session_state.get("current_problem_id") == query_problem_id
                    and st.session_state.get("current_view") in {"home", "library"}
                )
                if not suppress_detail_query:
                    st.session_state["suppress_detail_query"] = False
                    _navigate_to("detail", current_problem_id=query_problem_id)
                    render_problem_detail(
                        service,
                        query_problem_id,
                        hint_service=hint_service,
                        show_back_button=True,
                    )
                    return

        if st.session_state.get("current_view") == "library":
            st.session_state["show_problem_library"] = True

        if st.session_state.get("current_view") == "home":
            st.session_state["show_problem_library"] = False

        if st.session_state.get("current_view") == "detail" and st.session_state.get("current_problem_id") is not None:
            render_problem_detail(
                service,
                int(st.session_state["current_problem_id"]),
                hint_service=hint_service,
                show_back_button=True,
            )
            return

        st.sidebar.markdown("## \u2726 HintCode")
        st.sidebar.caption("Practice that remembers you")
        learning_pages = list(PAGES.keys())
        if "learning_page" not in st.session_state:
            st.session_state["learning_page"] = "Home"
        pending_learning_page = st.session_state.pop("pending_learning_page", None)
        if pending_learning_page in learning_pages:
            st.session_state["learning_page"] = pending_learning_page
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
        if st.sidebar.button("Import Problem", use_container_width=True):
            st.session_state["show_import_problem_dialog"] = True
        if st.session_state.get("show_import_problem_dialog"):
            render_import_problem_dialog(service, import_service)
        if workspace == "Problem Library" and st.sidebar.button("Browse problem library", use_container_width=True):
            _navigate_to("library")
            st.session_state["show_problem_library"] = True
            st.rerun()
        if workspace == "Open a problem" and st.sidebar.button("Open problem workspace", use_container_width=True):
            _navigate_to("detail", current_problem_id=1)
            st.query_params["page"] = "detail"
            st.query_params["problem_id"] = "1"
            st.rerun()

        if st.session_state["show_problem_library"] or st.session_state.get("current_view") == "library":
            render_problem_list(service)
        else:
            st.session_state["current_view"] = "home"
            render_learning_page(page)


if __name__ == "__main__":
    main()

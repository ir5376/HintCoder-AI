"""Internal, session-backed navigation for HintCode's learning flow."""

from __future__ import annotations

import streamlit as st

HOME = "home"
LIBRARY = "library"
DETAIL = "detail"
LEARNING = "learning"
ATTENDANCE = "attendance"
LEADERBOARD = "leaderboard"
REVIEW_QUEUE = "review_queue"

_VALID_PAGES = {HOME, LIBRARY, DETAIL, LEARNING, ATTENDANCE, LEADERBOARD, REVIEW_QUEUE}
_PATHS = {
    HOME: [HOME],
    LIBRARY: [HOME, LIBRARY],
    DETAIL: [HOME, LIBRARY, DETAIL],
    LEARNING: [HOME, LIBRARY, DETAIL, LEARNING],
    ATTENDANCE: [HOME, ATTENDANCE],
    LEADERBOARD: [HOME, LEADERBOARD],
    REVIEW_QUEUE: [HOME, REVIEW_QUEUE],
}


def initialize() -> None:
    """Create one navigation source of truth, seeded from a shared URL if present."""
    if "nav_stack" in st.session_state:
        return
    requested_page = str(st.query_params.get("page", HOME)).lower()
    page = requested_page if requested_page in _VALID_PAGES else HOME
    st.session_state["nav_stack"] = list(_PATHS[page])
    st.session_state["selected_problem_id"] = _coerce_problem_id(st.query_params.get("problem_id"))
    st.session_state["selected_provider"] = str(st.query_params.get("provider", "HintCode"))
    sync_url()


def _coerce_problem_id(value: object) -> int | str | None:
    try:
        raw_value = str(value) if value is not None else ""
        if not raw_value:
            return None
        return int(raw_value) if raw_value.isdigit() else raw_value
    except (TypeError, ValueError):
        return None


def current_page() -> str:
    return st.session_state["nav_stack"][-1]


def navigate(page: str, *, problem_id: int | str | None = None, provider: str | None = None) -> None:
    if page not in _VALID_PAGES:
        raise ValueError(f"Unknown HintCode page: {page}")
    if problem_id is not None:
        st.session_state["selected_problem_id"] = problem_id
    if provider is not None:
        st.session_state["selected_provider"] = provider
    # Each forward destination has a canonical in-app ancestry. This keeps the
    # Back destination predictable even when the user enters through sidebar
    # navigation rather than the primary call-to-action.
    st.session_state["nav_stack"] = list(_PATHS[page])
    sync_url()


def go_back() -> None:
    stack = list(st.session_state["nav_stack"])
    if len(stack) > 1:
        stack.pop()
    st.session_state["nav_stack"] = stack
    sync_url()


def sync_url() -> None:
    """Reflect the internal state in the URL without using browser history."""
    values = {
        "page": current_page(),
        "provider": st.session_state.get("selected_provider", "HintCode"),
    }
    problem_id = st.session_state.get("selected_problem_id")
    if problem_id is not None:
        values["problem_id"] = str(problem_id)
    st.query_params.clear()
    st.query_params.update(values)

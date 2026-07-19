"""URL query parameter utilities for HintCode."""

import streamlit as st


def _first_query_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def get_problem_context_from_query_params() -> dict:
    """
    Extract problem_title and problem_url from URL query parameters.
    
    Returns:
        dict with 'problem_title' and 'problem_url' keys (None if not present)
    """
    query_params = st.query_params
    problem_title = _first_query_value(query_params.get("problem_title"))
    problem_url = _first_query_value(query_params.get("problem_url"))

    return {
        "problem_title": problem_title.strip() if isinstance(problem_title, str) and problem_title.strip() else None,
        "problem_url": problem_url.strip() if isinstance(problem_url, str) and problem_url.strip() else None,
    }

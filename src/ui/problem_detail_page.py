import traceback
from urllib.parse import urlparse

import streamlit as st

from src.services.hint_service import HintService, ProblemContext
from src.services.problem_service import ProblemService

try:
    from streamlit_ace import st_ace
except ImportError:  # pragma: no cover - optional dependency in test environments
    st_ace = None


def build_hint_context(
    problem: dict,
    *,
    student_code: str = "",
    programming_language: str = "Python",
    hint_level: int = 1,
) -> ProblemContext:
    return ProblemContext(
        source_platform="HintCode",
        source_url=problem.get("source_reference", "") or "",
        title=problem.get("title", "") or "",
        description=problem.get("description", "") or "",
        constraints=problem.get("constraints", "") or "",
        examples=str(problem.get("test_cases", []) or ""),
        difficulty=problem.get("difficulty", "") or "",
        programming_language=programming_language or "Python",
        student_code=student_code or problem.get("starter_code", "") or "",
        hint_level=hint_level,
        problem_id=problem.get("id"),
    )


def _normalize_history_entry(entry: dict) -> dict:
    hint_text = entry.get("generated_hint") or entry.get("hint") or entry.get("hint_text") or ""
    return {
        "generated_hint": hint_text,
        "hint_level": entry.get("hint_level", 1),
        "programming_language": entry.get("programming_language", "Python"),
        "problem_title": entry.get("problem_title") or entry.get("title") or "Problem",
    }


def _render_code_editor(label: str, value: str, key: str, *, language: str = "python") -> str:
    if st_ace is not None:
        return st_ace(
            value=value,
            language=language,
            theme="monokai",
            key=key,
            height=250,
            auto_update=False,
            show_gutter=True,
        )

    return st.text_area(label, value=value, height=250, key=key)


def _is_safe_external_url(url: str | None) -> bool:
    if not url:
        return False

    parsed_url = urlparse(url)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


EXTERNAL_HINT_LEVEL_LABELS = {
    1: "Key concept",
    2: "Algorithm direction",
    3: "Pseudocode",
    4: "Nearly complete implementation strategy",
}


def _external_session_payload(problem_title: str, problem_url: str, hint_level_used: int) -> dict:
    return {
        "problem_title": problem_title,
        "problem_url": problem_url,
        "hint_level_used": hint_level_used,
    }


def _reset_external_problem_state(problem_title: str, problem_url: str) -> None:
    problem_key = f"{problem_title}\n{problem_url}"
    if st.session_state.get("external_problem_key") == problem_key:
        return

    st.session_state["external_problem_key"] = problem_key
    st.session_state["external_hint_level_used"] = 0
    st.session_state["external_hint_history"] = []
    st.session_state["external_code_editor"] = ""
    st.session_state["external_problem_session"] = _external_session_payload(problem_title, problem_url, 0)


def _build_external_problem_context(
    *,
    problem_title: str,
    problem_url: str,
    student_code: str,
    programming_language: str = "Python",
    hint_level: int = 1,
) -> ProblemContext:
    return ProblemContext(
        source_platform="External",
        source_url=problem_url,
        external_problem_id=problem_url,
        title=problem_title,
        description="",
        constraints="",
        examples="",
        difficulty="",
        programming_language=programming_language,
        student_code=student_code,
        hint_level=hint_level,
        problem_id=None,
    )


def render_external_problem_mode(
    *,
    hint_service: HintService | None,
    problem_title: str,
    problem_url: str,
) -> None:
    _reset_external_problem_state(problem_title, problem_url)

    st.subheader("External Problem Mode")
    st.markdown(f"## {problem_title}")
    if _is_safe_external_url(problem_url):
        st.link_button("Open original problem", problem_url)
        st.caption(problem_url)
    else:
        st.caption("Original problem URL is invalid.")
        st.code(problem_url)

    st.markdown("### Code Editor")
    student_code = _render_code_editor(
        "Your code",
        st.session_state.get("external_code_editor", ""),
        "external_code_editor",
        language="python",
    )

    hint_level_used = int(st.session_state.get("external_hint_level_used", 0))
    next_hint_level = min(hint_level_used + 1, 4)
    button_disabled = hint_level_used >= 4

    if not button_disabled:
        st.caption(f"Next: Hint Level {next_hint_level} - {EXTERNAL_HINT_LEVEL_LABELS[next_hint_level]}")

    if st.button("Generate Hint", type="primary", disabled=button_disabled):
        if hint_service is None:
            st.error("Hint service is not available.")
            return

        with st.spinner("Generating a hint..."):
            try:
                context = _build_external_problem_context(
                    problem_title=problem_title,
                    problem_url=problem_url,
                    student_code=student_code,
                    hint_level=next_hint_level,
                )
                result = hint_service.generate_hint(context, hint_level=next_hint_level)
            except Exception as exc:
                traceback.print_exc()
                st.error("Sorry, I could not generate a hint right now. Please try again.")
                st.caption(f"Exception type: {type(exc).__name__}")
                return

        if result.get("hint"):
            history = list(st.session_state.get("external_hint_history", []))
            history.append(
                {
                    "hint_level": result.get("hint_level", next_hint_level),
                    "label": EXTERNAL_HINT_LEVEL_LABELS.get(result.get("hint_level", next_hint_level), "Hint"),
                    "generated_hint": result["hint"],
                }
            )
            hint_level_used = max(hint_level_used, int(result.get("hint_level", next_hint_level)))
            st.session_state["external_hint_history"] = history
            st.session_state["external_hint_level_used"] = hint_level_used
            st.session_state["external_problem_session"] = _external_session_payload(
                problem_title,
                problem_url,
                hint_level_used,
            )

    st.markdown("### Progressive Hints")
    history_entries = list(st.session_state.get("external_hint_history", []))
    if history_entries:
        for entry in history_entries:
            st.markdown(f"#### Hint Level {entry['hint_level']} - {entry['label']}")
            st.info(entry["generated_hint"])
    else:
        st.write("No hints generated yet.")

    if int(st.session_state.get("external_hint_level_used", 0)) >= 4:
        st.caption("All hint levels have been generated for this session.")


def render_problem_detail(
    service: ProblemService,
    problem_id: int | None = None,
    hint_service: HintService | None = None,
    external_title: str | None = None,
    external_url: str | None = None,
) -> None:
    st.subheader("Problem Details")

    if external_title is not None:
        st.session_state["external_problem_title"] = external_title
    else:
        st.session_state.pop("external_problem_title", None)
    if external_url is not None:
        st.session_state["external_problem_url"] = external_url
    else:
        st.session_state.pop("external_problem_url", None)

    current_external_title = st.session_state.get("external_problem_title")
    current_external_url = st.session_state.get("external_problem_url")
    safe_external_url = current_external_url if _is_safe_external_url(current_external_url) else None

    if current_external_title:
        st.info(f"Problem from extension: **{current_external_title}**")
    if safe_external_url:
        st.link_button("View original problem", safe_external_url)
    elif current_external_url:
        st.caption("Original problem link is not shown because the URL is invalid.")

    if problem_id is None:
        problem_id = st.sidebar.number_input("problem ID", min_value=1, step=1, value=1)

    problem = service.get_problem(int(problem_id))

    if problem is None:
        st.error("Cannot find the problem.")
        return

    hint_problem = dict(problem)
    if current_external_title:
        hint_problem["title"] = current_external_title
    if safe_external_url:
        hint_problem["source_reference"] = safe_external_url

    st.markdown(f"## {problem['id']}. {problem['title']}")
    st.write(f"**Category:** {problem['category']}  |  **Difficulty:** {problem['difficulty']}")
    st.write(f"**Problem Type:** {problem['problem_type']}")
    st.write(f"**Function name:** `{problem['function_name']}`")
    st.markdown("### Problem Description")
    st.write(problem['description'])
    if problem['constraints']:
        st.markdown("### Constraints")
        st.write(problem['constraints'])
    if problem['test_cases']:
        st.markdown("### Sample Test Cases")
        st.write(problem['test_cases'])
    if problem['explanation']:
        st.markdown("### Explanation")
        st.write(problem['explanation'])

    st.markdown("### Starter Code")
    st.code(problem['starter_code'], language='python')

    st.markdown("### Hint Assistant")
    st.caption("Get a progressive hint based on your current code.")

    col1, col2 = st.columns([1, 1])
    with col1:
        programming_language = st.selectbox("Programming language", ["Python", "JavaScript", "Java", "C++"], index=0)
    with col2:
        hint_level = st.selectbox("Hint level", [1, 2, 3, 4], index=0)

    templates = {
        "Python": problem.get("starter_code", "") or "",
        "JavaScript": "function solution() {\n    // Write your solution here\n}",
        "Java": "class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}",
        "C++": "#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}",
    }

    editor_key = f"code_editor_{problem['id']}_{programming_language}"
    if editor_key not in st.session_state:
        st.session_state[editor_key] = templates.get(programming_language, "")

    ace_language_map = {
        "Python": "python",
        "JavaScript": "javascript",
        "Java": "java",
        "C++": "c_cpp",
    }
    student_code = _render_code_editor(
        "Your code",
        st.session_state[editor_key],
        editor_key,
        language=ace_language_map.get(programming_language, "python"),
    )

    if st.button("Get Hint", type="primary"):
        if hint_service is None:
            st.error("Hint service is not available.")
            return

        with st.spinner("Generating a hint..."):
            try:
                context = build_hint_context(
                    hint_problem,
                    student_code=student_code,
                    programming_language=programming_language,
                    hint_level=hint_level,
                )
                result = hint_service.generate_hint(context, hint_level=hint_level)
            except Exception as exc:
                traceback.print_exc()
                st.error("Sorry, I could not generate a hint right now. Please try again.")
                st.caption(f"Exception type: {type(exc).__name__}")
                return

        if result.get("hint"):
            st.markdown("#### Hint Output")
            st.info(result["hint"])

            history = list(st.session_state.get("hint_history", []))
            history.insert(
                0,
                {
                    "generated_hint": result["hint"],
                    "hint_level": result.get("hint_level", hint_level),
                    "programming_language": programming_language,
                    "problem_title": hint_problem["title"],
                },
            )
            st.session_state["hint_history"] = history[:8]

    history_entries = list(st.session_state.get("hint_history", []))
    if not history_entries and hint_service is not None:
        try:
            backend_history = hint_service.list_hint_history()
            history_entries = [_normalize_history_entry(item) for item in backend_history]
            st.session_state["hint_history"] = history_entries[:8]
        except Exception:
            history_entries = []

    with st.expander("Hint history", expanded=False):
        if history_entries:
            for entry in history_entries:
                st.markdown(f"- Level {entry['hint_level']} ({entry['programming_language']}): {entry['generated_hint']}")
        else:
            st.write("No hints generated yet.")

import traceback

import streamlit as st

from src.services.hint_service import HintService, ProblemContext
from src.services.problem_service import ProblemService


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


def render_problem_detail(
    service: ProblemService,
    problem_id: int | None = None,
    hint_service: HintService | None = None,
) -> None:
    st.subheader("Problem Details")

    if problem_id is None:
        problem_id = st.sidebar.number_input("problem ID", min_value=1, step=1, value=1)

    problem = service.get_problem(int(problem_id))

    if problem is None:
        st.error("Cannot find the problem.")
        return

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

    student_code = st.text_area("Your code", value=st.session_state[editor_key], height=250, key=editor_key)

    if st.button("Get Hint", type="primary"):
        if hint_service is None:
            st.error("Hint service is not available.")
            return

        with st.spinner("Generating a hint..."):
            try:
                context = build_hint_context(
                    problem,
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
                    "problem_title": problem["title"],
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

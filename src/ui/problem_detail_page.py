import streamlit as st

from src.services.hint_service import HintService, ProblemContext
from src.services.problem_service import ProblemService

try:
    from streamlit_ace import st_ace
except ImportError:  # pragma: no cover - optional dependency in test environments
    st_ace = None


def build_hint_context(problem: dict, *, student_code: str = "", programming_language: str = "Python", hint_level: int = 1) -> ProblemContext:
    return ProblemContext(
        source_platform="HintCode", source_url=problem.get("source_reference", "") or "",
        title=problem.get("title", "") or "", description=problem.get("description", "") or "",
        constraints=problem.get("constraints", "") or "", examples=str(problem.get("test_cases", []) or ""),
        difficulty=problem.get("difficulty", "") or "", programming_language=programming_language or "Python",
        student_code=student_code or problem.get("starter_code", "") or "", hint_level=hint_level,
        problem_id=problem.get("id"),
    )


def _normalize_history_entry(entry: dict) -> dict:
    return {
        "generated_hint": entry.get("generated_hint") or entry.get("hint") or entry.get("hint_text") or "",
        "hint_level": entry.get("hint_level", 1), "programming_language": entry.get("programming_language", "Python"),
        "problem_title": entry.get("problem_title") or entry.get("title") or "Problem",
    }


def _render_code_editor(label: str, value: str, key: str, *, language: str = "python") -> str:
    if st_ace is not None:
        return st_ace(value=value, language=language, theme="monokai", key=key, height=330, auto_update=False, show_gutter=True)
    return st.text_area(label, value=value, height=330, key=key)


def _back_to_library() -> None:
    st.query_params.clear()
    st.session_state["show_problem_library"] = True
    st.rerun()


def render_problem_detail(service: ProblemService, problem_id: int | None = None, hint_service: HintService | None = None) -> None:
    if problem_id is None:
        problem_id = st.sidebar.number_input("Problem ID", min_value=1, step=1, value=1)
    problem = service.get_problem(int(problem_id))
    if problem is None:
        st.error("We couldn't find that learning item.")
        st.caption("It may have been removed or the link may be incomplete.")
        if st.button("Back to problem library"):
            _back_to_library()
        return

    st.markdown('<div class="hc-eyebrow">Learning item</div>', unsafe_allow_html=True)
    top, back = st.columns([5, 1])
    with top:
        st.markdown(f'<div class="hc-title">{problem["title"]}</div><p class="hc-lede">{problem["category"]} · {problem["difficulty"]} · {problem["problem_type"]}</p>', unsafe_allow_html=True)
    with back:
        st.button("← Library", on_click=_back_to_library, use_container_width=True)

    tabs = st.tabs(["Problem", "Hint", "Attempt", "Reflection", "Execution trace", "Review"])
    with tabs[0]:
        st.markdown("#### Understand the problem")
        st.write(problem["description"])
        if problem.get("constraints"):
            st.markdown("#### Constraints")
            st.write(problem["constraints"])
        if problem.get("test_cases"):
            st.markdown("#### Examples")
            st.write(problem["test_cases"])
        if problem.get("explanation"):
            with st.expander("Concept explanation"):
                st.write(problem["explanation"])
        st.info("Before you code, name the input, the desired output, and one example you can trace by hand.")

    templates = {
        "Python": problem.get("starter_code", "") or "", "JavaScript": "function solution() {\n    // Write your solution here\n}",
        "Java": "class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}",
        "C++": "#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}",
    }
    with tabs[2]:
        st.markdown("#### Make an attempt")
        st.caption("Your draft is used only to give the hint assistant useful context.")
        language = st.selectbox("Language", ["Python", "JavaScript", "Java", "C++"], key=f"language_{problem['id']}")
        editor_key = f"code_editor_{problem['id']}_{language}"
        if editor_key not in st.session_state:
            st.session_state[editor_key] = templates[language]
        language_map = {"Python": "python", "JavaScript": "javascript", "Java": "java", "C++": "c_cpp"}
        student_code = _render_code_editor("Your attempt", st.session_state[editor_key], editor_key, language=language_map[language])
        st.session_state[f"student_code_{problem['id']}"] = student_code
        st.session_state[f"student_language_{problem['id']}"] = language

    with tabs[1]:
        st.markdown("#### Ask for the smallest useful nudge")
        st.caption("Hints are progressive. Start small so your reasoning stays in the lead.")
        hint_level = st.select_slider("How direct should the hint be?", options=[1, 2, 3, 4], value=1, key=f"hint_level_{problem['id']}", format_func=lambda value: f"Level {value}")
        if st.button("Get a hint", type="primary", key=f"get_hint_{problem['id']}"):
            if hint_service is None:
                st.error("The hint assistant is unavailable. Please try again shortly.")
            else:
                code = st.session_state.get(f"student_code_{problem['id']}", problem.get("starter_code", ""))
                language = st.session_state.get(f"student_language_{problem['id']}", "Python")
                with st.spinner("Reading your attempt and preparing a hint…"):
                    try:
                        result = hint_service.generate_hint(build_hint_context(problem, student_code=code, programming_language=language, hint_level=hint_level), hint_level=hint_level)
                    except Exception:
                        st.error("We couldn't generate a hint right now. Your attempt is still here—please try again in a moment.")
                    else:
                        if result.get("hint"):
                            entry = {"generated_hint": result["hint"], "hint_level": result.get("hint_level", hint_level), "programming_language": language, "problem_title": problem["title"]}
                            st.session_state[f"latest_hint_{problem['id']}"] = entry
                            history = list(st.session_state.get("hint_history", [])); history.insert(0, entry)
                            st.session_state["hint_history"] = history[:8]
                        else:
                            st.warning("The assistant returned no hint. Please try again.")
        latest = st.session_state.get(f"latest_hint_{problem['id']}")
        if latest:
            st.success(latest["generated_hint"])
        else:
            st.markdown('<div class="hc-card"><b>No hint yet</b><p class="hc-muted">Write an attempt first, then choose the level of guidance you need.</p></div>', unsafe_allow_html=True)

    with tabs[3]:
        st.markdown("#### Reflection")
        st.caption("Capture the part that changed your understanding. This remains in the current session until persistence is connected.")
        st.text_area("What did you notice? What would you try first next time?", key=f"reflection_{problem['id']}", placeholder="For example: I should draw the visited set before choosing the traversal.", height=150)
    with tabs[4]:
        st.markdown("#### Execution trace")
        st.markdown('<div class="hc-card"><b>Trace is not available yet</b><p class="hc-muted">Execution tracing needs a safe code-runner connection. You can still walk through an example in your reflection.</p></div>', unsafe_allow_html=True)
    with tabs[5]:
        st.markdown("#### Review")
        st.markdown('<div class="hc-card"><b>Not scheduled for review</b><p class="hc-muted">Review scheduling will appear here when it is connected to your learning record.</p></div>', unsafe_allow_html=True)

    history = list(st.session_state.get("hint_history", []))
    if not history and hint_service is not None:
        try:
            st.session_state["hint_history"] = [_normalize_history_entry(item) for item in hint_service.list_hint_history()][:8]
        except Exception:
            pass

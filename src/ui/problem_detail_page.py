import streamlit as st

from src.services.problem_service import ProblemService


def render_problem_detail(service: ProblemService) -> None:
    st.subheader("Problem Details")
    problem_id = st.sidebar.number_input("problem ID", min_value=1, step=1, value=1)
    problem = service.get_problem(int(problem_id))

    if problem is None:
        st.error("Cannot find the problem.")
        return

    st.markdown(f"## {problem['id']}. {problem['title']}")
    st.write(f"**Category:** {problem['category']}  |  **Difficulty:** {problem['difficulty']}")
    st.write(f"*Problem Type:** {problem['problem_type']}")
    st.write(f"**Function name:** `{problem['function_name']}`")
    st.markdown("### Problem Description")
    st.write(problem['description'])
    if problem['constraints']:
        st.markdown("### Constraints")
        st.write(problem['constraints'])
    if problem['test_cases']:
        st.markdown("### Sample Test Cases ")
        st.write(problem['test_cases'])
    if problem['explanation']:
        st.markdown("### Explanation")
        st.write(problem['explanation'])

    st.markdown("### Starter Code")
    st.code(problem['starter_code'], language='python')

import streamlit as st

from src.services.problem_service import ProblemService


def render_problem_list(service: ProblemService) -> None:
    filters = service.get_filters()
    category = st.sidebar.selectbox("카테고리", ["전체"] + filters["categories"])
    difficulty = st.sidebar.selectbox("난이도", ["전체"] + filters["difficulties"])

    category_filter = None if category == "전체" else category
    difficulty_filter = None if difficulty == "전체" else difficulty

    problems = service.get_problem_list(category=category_filter, difficulty=difficulty_filter)

    st.subheader("문제 목록")
    st.write(f"총 {len(problems)}개 문제")

    for problem in problems:
        st.markdown(f"### {problem['id']}. {problem['title']}")
        st.write(problem['description'])
        st.write(f"**카테고리:** {problem['category']}  |  **난이도:** {problem['difficulty']}")
        st.write(f"**문제 유형:** {problem['problem_type']}")
        st.markdown(f"[문제 보기](?problem_id={problem['id']})")
        st.divider()

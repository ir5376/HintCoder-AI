import streamlit as st

from src.services.problem_service import ProblemService


def render_problem_detail(service: ProblemService) -> None:
    st.subheader("문제 상세")
    problem_id = st.sidebar.number_input("문제 ID", min_value=1, step=1, value=1)
    problem = service.get_problem(int(problem_id))

    if problem is None:
        st.error("해당 문제를 찾을 수 없습니다.")
        return

    st.markdown(f"## {problem['id']}. {problem['title']}")
    st.write(f"**카테고리:** {problem['category']}  |  **난이도:** {problem['difficulty']}")
    st.write(f"**문제 유형:** {problem['problem_type']}")
    st.write(f"**함수 이름:** `{problem['function_name']}`")
    st.markdown("### 문제 설명")
    st.write(problem['description'])
    if problem['constraints']:
        st.markdown("### 제약 사항")
        st.write(problem['constraints'])
    if problem['test_cases']:
        st.markdown("### 테스트 케이스 (샘플)")
        st.write(problem['test_cases'])
    if problem['explanation']:
        st.markdown("### 설명")
        st.write(problem['explanation'])

    st.markdown("### Starter 코드")
    st.code(problem['starter_code'], language='python')

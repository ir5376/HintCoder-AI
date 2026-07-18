
import streamlit as st 
from src.services.problem_service import ProblemService 
def render_problem_list(service: ProblemService) -> None:
     filters = service.get_filters() 
     category = st.sidebar.selectbox( "Category", ["All"] + filters["categories"] ) 
     difficulty = st.sidebar.selectbox( "Difficulty", ["All"] + filters["difficulties"] ) 
     
     category_filter = None if category == "All" else category 
     difficulty_filter = None if difficulty == "All" else difficulty 
     
     problems = service.get_problem_list( category=category_filter, difficulty=difficulty_filter ) 
     st.subheader("Problem List") 
     st.write(f"{len(problems)} problem(s) found") 
     
     for problem in problems: 
        st.markdown(f"### {problem['id']}. {problem['title']}") 
        st.write(problem['description']) 
        st.write( f"**Category:** {problem['category']} | " f"**Difficulty:** {problem['difficulty']}" ) 
        st.write(f"**Problem Type:** {problem['problem_type']}") 
        st.markdown(f"[View Problem](?problem_id={problem['id']})") 
        st.divider()
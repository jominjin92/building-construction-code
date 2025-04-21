import streamlit as st

def init_session_state():
    if 'problem_list' not in st.session_state:
        st.session_state.problem_list = []
    if 'show_problems' not in st.session_state:
        st.session_state.show_problems = False
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'show_results' not in st.session_state:
        st.session_state.show_results = {}
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = None

def login_ui():
    if not st.session_state["logged_in"]:
        st.title("로그인")
        username = st.text_input("사용자 이름")
        password = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if _check_credentials(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("로그인 성공!")
            else:
                st.session_state["logged_in"] = False
                st.session_state["username"] = None
                st.session_state["user_role"] = None
                st.error("사용자 이름이나 비밀번호가 올바르지 않습니다.")
                st.experimental_rerun()
        st.stop()

from db.user_db import verify_user

def _check_credentials(username, password):
    role = verify_user(username, password)
    if role:
        st.session_state.user_role = role
        return True
    return False
import streamlit as st

# 초기화 및 기능 모듈 import
from db.init import init_db, create_feedback_table, create_attempts_table, update_db_types
from ui.auth import init_session_state, login_ui
from ui.problem_ui import render_problem_tab
from ui.admin_ui import render_admin_tab
from ui.dashboard_ui import render_dashboard_tab

# -------------------- 시스템 초기화 --------------------
init_session_state()
init_db()
create_feedback_table()
create_attempts_table()
update_db_types()

# -------------------- 로그인 UI --------------------
login_ui()

# -------------------- 메인 화면 --------------------
st.title("🏗 건축시공학 하이브리드 문제풀이 시스템")

tab_problem, tab_admin, tab_dashboard = st.tabs(["📝 문제풀이", "🛠 문제관리 (관리자)", "📊 대시보드"])

with tab_problem:
    render_problem_tab()

with tab_admin:
    render_admin_tab()

with tab_dashboard:
    render_dashboard_tab()
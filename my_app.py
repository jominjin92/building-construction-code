import streamlit as st

# -------------------- 초기화 및 import --------------------
from db.init import init_db, create_feedback_table, create_attempts_table, update_db_types
from ui.auth import init_session_state, login_ui
from ui.problem_ui import render_problem_tab
from ui.admin_ui import render_admin_tab
from ui.dashboard_ui import render_dashboard_tab
from db.user_db import init_user_db, add_user
from ui.lecture_material_ui import render_lecture_material_tab
import sqlite3

# ✅ admin 계정 존재 시 중복 방지 함수
def ensure_admin_exists():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    exists = c.fetchone()[0]
    conn.close()
    if not exists:
        add_user("admin", "1234", "admin")

# -------------------- 시스템 초기화 --------------------
init_session_state()
init_db()
init_user_db()
create_feedback_table()
create_attempts_table()
update_db_types()

ensure_admin_exists()  # ✅ 안전하게 admin 계정 추가

# -------------------- 로그인 --------------------
if not st.session_state.logged_in:
    login_ui()
    st.stop()  # 로그인 성공 전에는 아래 내용 실행 안 됨

# -------------------- 메인 화면 --------------------
st.title("🏗 건축시공학 하이브리드 문제풀이 시스템")

tab_problem, tab_admin, tab_dashboard = st.tabs(["📝 문제풀이", "🛠 문제관리 (관리자)", "📊 대시보드"])

with tab_problem:
    render_problem_tab()

with tab_admin:
    if st.session_state.user_role == "admin":
        render_admin_tab()
    else:
        st.warning("관리자만 접근할 수 있습니다.")

with tab_dashboard:
    render_dashboard_tab()
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import altair as alt

def render_dashboard_tab():
    st.header("📊 통계 및 대시보드")

    user_id = st.session_state.get("username", "guest")
    user_role = st.session_state.get("user_role", "user")

    # ------------------ 나의 히스토리 ------------------
    st.subheader("🧠 나의 학습 히스토리")
    try:
        df = pd.read_csv("data/results.csv")
        df["풀이날짜"] = pd.to_datetime(df["풀이날짜"])
        user_df = df[df["사용자ID"] == user_id]

        if user_df.empty:
            st.info("아직 풀이 기록이 없습니다.")
        else:
            daily_count = user_df.groupby(user_df["풀이날짜"].dt.date).size().reset_index(name="풀이횟수")
            chart = alt.Chart(daily_count).mark_bar().encode(
                x="풀이날짜:T",
                y="풀이횟수:Q"
            ).properties(title="날짜별 문제풀이 수", width=700, height=300)
            st.altair_chart(chart)

            st.markdown("### 🧾 최근 10개 문제풀이 기록")
            st.dataframe(user_df.sort_values("풀이날짜", ascending=False).head(10)[
                ["문제", "선택한답", "정답", "정오답", "풀이날짜", "개념"]
            ])

    except Exception as e:
        st.error(f"학습 히스토리 시각화 중 오류: {e}")

    # ------------------ 성과 리포트 ------------------
    st.subheader("📋 나의 학습 성과 리포트")
    try:
        df = pd.read_csv("data/results.csv")
        df["풀이날짜"] = pd.to_datetime(df["풀이날짜"])
        user_df = df[df["사용자ID"] == user_id]

        if not user_df.empty:
            correct_rate = (user_df["정오답"] == "정답").mean() * 100
            avg_time = user_df["풀이시간"].mean()

            st.metric("📈 전체 정답률", f"{correct_rate:.1f}%")
            st.metric("⏱ 평균 풀이 시간", f"{avg_time:.1f}초")

            concept_df = user_df.groupby("개념")["정오답"].value_counts().unstack().fillna(0)
            concept_df["정답률"] = (concept_df.get("정답", 0) / concept_df.sum(axis=1)) * 100
            st.markdown("### 🧠 개념별 정답률")
            st.dataframe(concept_df[["정답률"]].sort_values("정답률", ascending=False))

            wrongs = user_df[user_df["정오답"] == "오답"]["개념"].value_counts().head(5)
            st.markdown("### ❗ 가장 많이 틀린 개념 TOP 5")
            st.bar_chart(wrongs)
    except Exception as e:
        st.error(f"성과 리포트 생성 중 오류: {e}")

    # ------------------ 통계 범위 선택 ------------------
    st.subheader("📑 세부 통계")
    scope = st.selectbox("통계 범위 선택", ["문제 풀이 통계", "피드백 통계"])

    conn = sqlite3.connect("problems.db")

    if scope == "문제 풀이 통계":
        detail = st.selectbox("세부 통계", ["전체 통계", "사용자별 통계"])
        if detail == "사용자별 통계" and user_role == "admin":
            users = pd.read_sql_query("SELECT DISTINCT user_id FROM attempts", conn)
            selected_user = st.selectbox("사용자 선택", users['user_id'])
            user_filter = "WHERE a.user_id = ?"
            user_param = (selected_user,)
        elif detail == "사용자별 통계":
            user_filter = "WHERE a.user_id = ?"
            user_param = (user_id,)
        else:
            user_filter = ""
            user_param = ()

        df_attempts = pd.read_sql_query(f"""
            SELECT is_correct FROM attempts a {user_filter}
        """, conn, params=user_param)

        if not df_attempts.empty:
            total = df_attempts.shape[0]
            correct = df_attempts['is_correct'].sum()
            chart_df = pd.DataFrame({
                '결과': ['정답', '오답'],
                '비율': [correct / total, (total - correct) / total]
            })
            fig = px.bar(chart_df, x='결과', y='비율', color='결과', text='비율')
            fig.update_traces(texttemplate='%{text:.2%}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("문제풀이 기록이 없습니다.")

    elif scope == "피드백 통계":
        st.subheader("📝 피드백 통계")
        detail = st.selectbox("세부 통계", ["전체 피드백 통계", "사용자별 피드백 통계"])

        if detail == "사용자별 피드백 통계":
            users = pd.read_sql_query("SELECT DISTINCT user_id FROM feedback", conn)
            if not users.empty:
                selected_user = st.selectbox("사용자 선택", users['user_id'])
                query = """
                SELECT f.user_id, f.problem_id, p.question, f.feedback_text, f.feedback_time
                FROM feedback f
                LEFT JOIN problems p ON f.problem_id = p.id
                WHERE f.user_id = ?
                ORDER BY f.feedback_time DESC
                """
                df_feedback = pd.read_sql_query(query, conn, params=(selected_user,))
            else:
                df_feedback = pd.DataFrame()
        else:
            query = """
            SELECT f.user_id, f.problem_id, p.question, f.feedback_text, f.feedback_time
            FROM feedback f
            LEFT JOIN problems p ON f.problem_id = p.id
            ORDER BY f.feedback_time DESC
            """
            df_feedback = pd.read_sql_query(query, conn)

        if not df_feedback.empty:
            st.markdown(f"총 피드백 수: **{df_feedback.shape[0]}**")
            st.dataframe(df_feedback)
        else:
            st.info("피드백 기록이 없습니다.")

    conn.close()
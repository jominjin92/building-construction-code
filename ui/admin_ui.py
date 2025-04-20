import streamlit as st
import pandas as pd
import sqlite3
from services.problem_generator import generate_openai_problem, generate_question_from_lecture
from services.pdf_parser import extract_text_from_pdf
from db.query import save_problem_to_db, update_problem_in_db as update_problem, delete_problem, export_problems_to_csv
from db.query import get_all_problems_dict
from utils.download import get_table_download_link

def render_admin_tab():
    if st.session_state.user_role != "admin":
        st.warning("관리자만 접근할 수 있습니다.")
        return

    st.header("문제 관리 (관리자 전용)")

    # ------------------ GPT 문제 생성 ------------------
    st.subheader("OpenAI 문제 생성")
    problem_source = st.selectbox("문제 출처 선택", ["건축시공 기출문제"])

    if st.button("GPT 문제 생성 (객관식)"):
        prob = generate_openai_problem("객관식", problem_source)
        if prob:
            save_problem_to_db(prob)
            st.success("객관식 문제 생성 완료!")

    if st.button("GPT 문제 생성 (주관식)"):
        prob = generate_openai_problem("주관식", problem_source)
        if prob:
            save_problem_to_db(prob)
            st.success("주관식 문제 생성 완료!")

    # ------------------ PDF 기반 문제 생성 ------------------
    st.subheader("📘 강의자료 기반 GPT 문제 생성")
    pdf_file = st.file_uploader("강의자료 PDF를 업로드하세요", type=["pdf"])

    if pdf_file:
        lecture_text = extract_text_from_pdf(pdf_file)
        with st.expander("📄 추출된 텍스트 미리보기"):
            st.text(lecture_text[:1000])

        if st.button("🔄 문제 생성"):
            with st.spinner("GPT가 문제를 생성 중입니다..."):
                question_data = generate_question_from_lecture(lecture_text)
                st.json(question_data)
                save_problem_to_db(question_data)
                st.success("강의자료 기반 문제 생성 완료!")

    # ------------------ CSV 업로드 ------------------
    st.subheader("📁 CSV 문제 업로드")
    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        for _, row in df.iterrows():
            problem_data = {
                "question": row["문제"],
                "선택지": [row.get(f"선택지{i+1}", "") for i in range(4)],
                "정답": str(row.get("정답", "")),
                "해설": row.get("해설", ""),
                "문제출처": "건축기사 기출문제",
                "문제형식": "객관식",
                "id": None
            }
            save_problem_to_db(problem_data)
        st.success("CSV 업로드 완료!")

    # ------------------ 문제 목록 편집 ------------------
    st.subheader("📋 문제 목록 관리")
    conn = sqlite3.connect("problems.db")
    df_sources = pd.read_sql_query("SELECT DISTINCT type AS 문제출처 FROM problems", conn)
    conn.close()

    sources = df_sources['문제출처'].tolist() if not df_sources.empty else []
    selected_source = st.selectbox("출처 선택", sources)

    all_problems = get_all_problems_dict()
    filtered = [p for p in all_problems if p["문제출처"] == selected_source]

    st.markdown(f"총 문제 수: **{len(filtered)}개**")

    for prob in filtered:
        with st.expander(f"[{prob['문제형식']}] {prob['문제'][:30]}..."):
            new_text = st.text_area("문제", prob['문제'], key=f"text_{prob['id']}")
            if prob["문제형식"] == "객관식":
                new_choices = [
                    st.text_input(f"선택지 {i+1}", prob['선택지'][i], key=f"ch_{i}_{prob['id']}")
                    for i in range(4)
                ]
                choices = ["1", "2", "3", "4"]
                default_index = 0
                if str(prob["정답"]).isdigit() and 1 <= int(prob["정답"]) <= 4:
                    default_index = int(prob["정답"]) - 1

                new_answer = st.selectbox(
                    "정답",
                    ["1", "2", "3", "4"],
                    index=int(prob["정답"]) - 1 if prob["정답"].isdigit() else 0,
                    key=f"ans_{prob['id']}"
                )
            else:
                new_choices = ["", "", "", ""]
                new_answer = st.text_input("정답", prob['정답'], key=f"ans_{prob['id']}")

            new_expl = st.text_area("해설", prob['해설'], key=f"exp_{prob['id']}")

            if st.button("수정 저장", key=f"save_{prob['id']}"):
                update_problem(prob['id'], {
                    "문제": new_text,
                    "선택지": new_choices,
                    "정답": new_answer,
                    "해설": new_expl,
                    "문제형식": prob["문제형식"],
                    "문제출처": prob["문제출처"]
                })
                st.success("문제가 수정되었습니다.")

            if st.button("문제 삭제", key=f"del_{prob['id']}"):
                delete_problem(prob['id'])
                st.warning("문제가 삭제되었습니다.")

    # ------------------ 문제 다운로드 ------------------
    st.subheader("📥 문제 CSV 다운로드")
    if st.button("CSV로 저장"):
        export_problems_to_csv()
        st.markdown(get_table_download_link("problems_export.csv"), unsafe_allow_html=True)
import streamlit as st
import sqlite3
import openai
import json
import pandas as pd
import random
import os
import logging
import uuid
from datetime import datetime

# ---------------------
# 기본 설정
# ---------------------
st.set_page_config(layout="wide")
st.title("건축시공학 문제 생성 및 풀이 시스템")
st.sidebar.title(f"안녕하세요, {st.session_state['username']}님!")

# 로그 설정
logging.basicConfig(level=logging.INFO)

# OpenAI API 키 설정
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("API key 설정 오류: secrets.toml에 OPENAI_API_KEY가 없습니다.")
    st.stop()

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "user"
if "username" not in st.session_state:
    st.session_state["username"] = "guest"
if "show_results" not in st.session_state:
    st.session_state["show_results"] = {}
if "user_answers" not in st.session_state:
    st.session_state["user_answers"] = {}

# DB 연결 및 테이블 초기화
def init_db():
    conn = sqlite3.connect("problems.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id TEXT PRIMARY KEY,
            문제 TEXT,
            선택지1 TEXT,
            선택지2 TEXT,
            선택지3 TEXT,
            선택지4 TEXT,
            정답 TEXT,
            해설 TEXT,
            문제형식 TEXT,
            문제출처 TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            problem_id TEXT,
            feedback_text TEXT,
            feedback_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            problem_id TEXT,
            user_answer TEXT,
            is_correct INTEGER,
            attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------------
# 로그인 기능
# ---------------------
def login(username, password):
    credentials = {
        "admin": "1234",
        "user1": "pass1",
        "user2": "pass2",
        "user3": "pass3",
        "user4": "pass4"
    }
    return credentials.get(username) == password

if not st.session_state["logged_in"]:
    st.subheader("로그인")
    username = st.text_input("사용자 이름")
    password = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if login(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["user_role"] = "admin" if username == "admin" else "user"
            st.success("로그인 성공!")
            st.experimental_rerun()
        else:
            st.error("사용자 이름이나 비밀번호가 올바르지 않습니다.")
    st.stop()

# ---------------------
# OpenAI 문제 생성 + CSV 저장
# ---------------------
def save_problem_to_csv(problem_data, filename="openai_generated_questions.csv"):
    df = pd.DataFrame([{
        "문제": problem_data["문제"],
        "선택지1": problem_data["선택지"][0],
        "선택지2": problem_data["선택지"][1],
        "선택지3": problem_data["선택지"][2],
        "선택지4": problem_data["선택지"][3],
        "정답": problem_data["정답"],
        "해설": problem_data["해설"],
        "문제형식": problem_data["문제형식"],
        "문제출처": problem_data["문제출처"]
    }])
    if os.path.exists(filename):
        df.to_csv(filename, mode='a', header=False, index=False)
    else:
        df.to_csv(filename, index=False)

def generate_openai_problem(question_type):
    prompt = f"""
    당신은 건축시공학 교수입니다. 건축시공학과 관련된 {question_type} 문제를 하나 출제하고, 선택지와 정답, 해설을 제공하세요.

    - 문제:
    - 선택지1:
    - 선택지2:
    - 선택지3:
    - 선택지4:
    - 정답 번호 (1~4 중 하나):
    - 해설:
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        result = response['choices'][0]['message']['content']
        lines = result.strip().split("\n")

        problem_data = {
            "문제": lines[0].replace("문제:", "").strip(),
            "선택지": [
                lines[1].split(":")[1].strip(),
                lines[2].split(":")[1].strip(),
                lines[3].split(":")[1].strip(),
                lines[4].split(":")[1].strip()
            ],
            "정답": lines[5].split(":")[1].strip(),
            "해설": lines[6].replace("해설:", "").strip(),
            "문제출처": "OpenAI 생성",
            "문제형식": question_type,
            "id": str(uuid.uuid4())
        }

        # DB 저장
        conn = sqlite3.connect("problems.db")
        c = conn.cursor()
        c.execute('''
            INSERT INTO problems (id, 문제, 선택지1, 선택지2, 선택지3, 선택지4, 정답, 해설, 문제형식, 문제출처)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            problem_data["id"],
            problem_data["문제"],
            problem_data["선택지"][0],
            problem_data["선택지"][1],
            problem_data["선택지"][2],
            problem_data["선택지"][3],
            problem_data["정답"],
            problem_data["해설"],
            problem_data["문제형식"],
            problem_data["문제출처"]
        ))
        conn.commit()
        conn.close()

        # CSV 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"openai_generated_questions_{timestamp}.csv"
        save_problem_to_csv(problem_data, csv_filename)

        return problem_data, csv_filename

    except Exception as e:
        st.error(f"문제 생성 중 오류가 발생했습니다: {e}")
        return None, None

# ---------------------
# 문제 불러오기 함수
# ---------------------
def load_problems():
    conn = sqlite3.connect("problems.db")
    df = pd.read_sql_query("SELECT * FROM problems", conn)
    conn.close()
    return df

# ---------------------
# 문제 풀이 기능
# ---------------------
def solve_problems():
    st.subheader("문제 풀이")
    problems_df = load_problems()

    if problems_df.empty:
        st.warning("등록된 문제가 없습니다. 관리자에게 문의하세요.")
        return

    num_questions = st.number_input("풀 문제 수 선택", min_value=1, max_value=len(problems_df), value=5, step=1)
    selected_problems = problems_df.sample(num_questions).reset_index(drop=True)

    for idx, row in selected_problems.iterrows():
        st.write(f"**문제 {idx + 1}.** {row['문제']}")
        options = [row['선택지1'], row['선택지2'], row['선택지3'], row['선택지4']]
        user_answer = st.radio(
            f"답안 선택 - 문제 {idx + 1}",
            options,
            key=f"answer_{idx}"
        )
        st.session_state["user_answers"][row["id"]] = user_answer

    if st.button("채점하기"):
        st.subheader("채점 결과")
        correct_count = 0
        conn = sqlite3.connect("problems.db")
        c = conn.cursor()

        for idx, row in selected_problems.iterrows():
            correct_answer = row[f"선택지{row['정답']}"]
            user_answer = st.session_state["user_answers"].get(row["id"], "")

            is_correct = int(user_answer == correct_answer)
            if is_correct:
                correct_count += 1

            st.write(f"**문제 {idx + 1}: {'정답' if is_correct else '오답'}**")
            st.write(f"- 선택한 답: {user_answer}")
            st.write(f"- 정답: {correct_answer}")
            st.write(f"- 해설: {row['해설']}")
            st.markdown("---")

            # 시도 기록 저장
            c.execute('''
                INSERT INTO attempts (user_id, problem_id, user_answer, is_correct)
                VALUES (?, ?, ?, ?)
            ''', (
                st.session_state["username"],
                row["id"],
                user_answer,
                is_correct
            ))

        conn.commit()
        conn.close()

        st.success(f"총 {correct_count} / {num_questions} 문제를 맞추셨습니다!")

        # 피드백 요청
        st.subheader("피드백 작성")
        for idx, row in selected_problems.iterrows():
            feedback = st.text_area(f"문제 {idx + 1}에 대한 피드백을 남겨주세요.", key=f"feedback_{idx}")
            if st.button(f"피드백 제출 - 문제 {idx + 1}", key=f"submit_feedback_{idx}"):
                save_feedback(st.session_state["username"], row["id"], feedback)
                st.success(f"문제 {idx + 1} 피드백이 저장되었습니다.")

# ---------------------
# 피드백 저장 함수
# ---------------------
def save_feedback(user_id, problem_id, feedback_text):
    conn = sqlite3.connect("problems.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO feedback (user_id, problem_id, feedback_text)
        VALUES (?, ?, ?)
    ''', (user_id, problem_id, feedback_text))
    conn.commit()
    conn.close()

# ---------------------
# CSV 업로드 시 미리보기 및 유효성 검사
# ---------------------
def upload_csv():
    st.subheader("CSV 파일 업로드 (문제 추가)")
    uploaded_file = st.file_uploader("CSV 파일 선택", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            required_columns = {"문제", "선택지1", "선택지2", "선택지3", "선택지4", "정답", "해설", "문제형식", "문제출처"}
            if not required_columns.issubset(df.columns):
                st.error(f"CSV 파일에 다음 필수 컬럼이 필요합니다: {required_columns}")
                return

            st.write("CSV 미리보기:")
            st.dataframe(df)

            if st.button("CSV 데이터 저장"):
                conn = sqlite3.connect("problems.db")
                c = conn.cursor()

                for _, row in df.iterrows():
                    c.execute('''
                        INSERT INTO problems (id, 문제, 선택지1, 선택지2, 선택지3, 선택지4, 정답, 해설, 문제형식, 문제출처)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),
                        row["문제"],
                        row["선택지1"],
                        row["선택지2"],
                        row["선택지3"],
                        row["선택지4"],
                        row["정답"],
                        row["해설"],
                        row["문제형식"],
                        row["문제출처"]
                    ))
                conn.commit()
                conn.close()
                st.success("CSV 데이터가 성공적으로 저장되었습니다!")

        except Exception as e:
            st.error(f"CSV 파일 처리 중 오류가 발생했습니다: {e}")

# ---------------------
# 관리자 문제 관리 (수정 / 삭제 기능)
# ---------------------
def manage_problems():
    st.subheader("문제 관리 (수정 / 삭제)")
    df = load_problems()

    if df.empty:
        st.warning("문제가 없습니다.")
        return

    selected_problem = st.selectbox("문제 선택", df["문제"])
    problem_data = df[df["문제"] == selected_problem].iloc[0]

    st.write("문제 정보:")
    st.json(problem_data.to_dict(), expanded=False)

    # 수정 기능
    new_question = st.text_input("문제", problem_data["문제"])
    new_choices = [
        st.text_input("선택지1", problem_data["선택지1"]),
        st.text_input("선택지2", problem_data["선택지2"]),
        st.text_input("선택지3", problem_data["선택지3"]),
        st.text_input("선택지4", problem_data["선택지4"]),
    ]
    new_answer = st.text_input("정답 (1~4)", problem_data["정답"])
    new_explanation = st.text_area("해설", problem_data["해설"])

    if st.button("문제 수정"):
        conn = sqlite3.connect("problems.db")
        c = conn.cursor()
        c.execute('''
            UPDATE problems
            SET 문제 = ?, 선택지1 = ?, 선택지2 = ?, 선택지3 = ?, 선택지4 = ?, 정답 = ?, 해설 = ?
            WHERE id = ?
        ''', (
            new_question,
            new_choices[0],
            new_choices[1],
            new_choices[2],
            new_choices[3],
            new_answer,
            new_explanation,
            problem_data["id"]
        ))
        conn.commit()
        conn.close()
        st.success("문제가 성공적으로 수정되었습니다!")
        st.experimental_rerun()

    # 삭제 기능 - 삭제 확인 팝업 추가
    if st.button("문제 삭제"):
        confirm = st.radio("정말로 삭제하시겠습니까?", ("아니요", "네"), key="confirm_delete")
        if confirm == "네":
            conn = sqlite3.connect("problems.db")
            c = conn.cursor()
            c.execute("DELETE FROM problems WHERE id = ?", (problem_data["id"],))
            conn.commit()
            conn.close()
            st.success("문제가 삭제되었습니다.")
            st.experimental_rerun()
        else:
            st.info("문제 삭제가 취소되었습니다.")

# ---------------------
# 대시보드 기능
# ---------------------
def dashboard():
    st.subheader("대시보드")
    conn = sqlite3.connect("problems.db")

    # 시도 기록 불러오기
    attempts_df = pd.read_sql_query("SELECT * FROM attempts", conn)
    if not attempts_df.empty:
        st.markdown("### 시도 기록")
        st.dataframe(attempts_df)

        # 전체 정답률
        correct_rate = attempts_df["is_correct"].mean() * 100
        st.metric("전체 정답률", f"{correct_rate:.2f}%")

        # 사용자별 정답률
        st.markdown("### 사용자별 정답률")
        user_correct = attempts_df.groupby("user_id")["is_correct"].mean() * 100
        st.dataframe(user_correct.reset_index().rename(columns={"is_correct": "정답률 (%)"}))

        # 문제별 정답률
        st.markdown("### 문제별 정답률")
        problem_correct = attempts_df.groupby("problem_id")["is_correct"].mean() * 100
        st.dataframe(problem_correct.reset_index().rename(columns={"is_correct": "정답률 (%)"}))

    else:
        st.info("아직 시도 기록이 없습니다.")

    # 피드백 통계
    feedback_df = pd.read_sql_query("SELECT * FROM feedback", conn)
    if not feedback_df.empty:
        st.markdown("### 수집된 피드백")
        st.dataframe(feedback_df)

        # 피드백 키워드 분석 (간단 빈도 분석)
        st.markdown("### 피드백 키워드 빈도")
        feedback_text = " ".join(feedback_df["feedback_text"].dropna().tolist())
        words = feedback_text.split()
        word_freq = pd.Series(words).value_counts().head(10)
        st.bar_chart(word_freq)

    else:
        st.info("수집된 피드백이 없습니다.")

    conn.close()

# ---------------------
# 메인 화면 구성
# ---------------------
def main():
    login()

    # 공통 다운로드 버튼 (OpenAI 문제 생성 CSV 파일)
    csv_files = [f for f in os.listdir() if f.startswith("openai_generated_questions") and f.endswith(".csv")]
    if csv_files:
        latest_csv = max(csv_files, key=os.path.getctime)
        with open(latest_csv, "rb") as file:
            btn_label = f"OpenAI 생성 문제 다운로드 ({latest_csv})"
            st.sidebar.download_button(
                label=btn_label,
                data=file,
                file_name=latest_csv,
                mime="text/csv"
            )

    # 탭 메뉴
    tabs = ["문제 풀이", "대시보드"]
    if st.session_state["user_role"] == "admin":
        tabs = ["문제 풀이", "문제 관리", "CSV 업로드", "OpenAI 문제 생성", "대시보드"]

    selected_tab = st.sidebar.radio("메뉴 선택", tabs)

    if selected_tab == "문제 풀이":
        solve_problems()
    elif selected_tab == "문제 관리" and st.session_state["user_role"] == "admin":
        manage_problems()
    elif selected_tab == "CSV 업로드" and st.session_state["user_role"] == "admin":
        upload_csv()
    elif selected_tab == "OpenAI 문제 생성" and st.session_state["user_role"] == "admin":
        st.subheader("OpenAI 문제 자동 생성")
        question_type = st.selectbox("문제 유형 선택", ["객관식"])
        if st.button("문제 생성"):
            with st.spinner("문제를 생성 중입니다..."):
                problem_data, csv_filename = generate_openai_problem(question_type)
                if problem_data:
                    st.success("문제가 성공적으로 생성되었습니다!")
                    st.write(problem_data)

                    # 생성된 문제 CSV 다운로드
                    with open(csv_filename, "rb") as file:
                        st.download_button(
                            label="생성된 문제 CSV 다운로드",
                            data=file,
                            file_name=csv_filename,
                            mime="text/csv"
                        )
    elif selected_tab == "대시보드":
        dashboard()

# 메인 실행
if __name__ == "__main__":
    main()
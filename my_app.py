import streamlit as st
import sqlite3
import openai
import json
import pandas as pd
import random
import os
import logging
import schedule
import time
import threading

logging.basicConfig(level=logging.INFO, force=True)

# ---------------------
# 1) API 키 설정
# ---------------------
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("API key 설정 오류: secrets.toml에 OPENAI_API_KEY가 없습니다.")
    st.stop()

# ---------------------
# 로그인 기능 추가
# ---------------------
# 만약 "logged_in"이나 "username" 키가 없다면 기본값을 설정합니다.
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "user"
if "username" not in st.session_state:
    st.session_state["username"] = "guest"  # 기본값

def login(username, password):
    # 데모용 사용자 정보: 관리자 1개, 사용자 4개
    # 관리자 계정은 "admin", 그 외는 일반 사용자
    credentials = {
        "admin": "1234",   # 관리자 계정
        "user1": "pass1",  # 사용자 계정 1
        "user2": "pass2",  # 사용자 계정 2
        "user3": "pass3",  # 사용자 계정 3
        "user4": "pass4"   # 사용자 계정 4
    }
    return credentials.get(username) == password

# ---------------------
# 로그인 UI
# ---------------------
if not st.session_state["logged_in"]:
    st.title("로그인")
    username = st.text_input("사용자 이름")
    password = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        # 로그인 함수 (예제에서는 데모용 사용자 정보 사용)
        def login(username, password):
            credentials = {
                "admin": "1234",
                "user1": "pass1",
                "user2": "pass2",
                "user3": "pass3",
                "user4": "pass4"
            }
            return credentials.get(username) == password

        if login(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["user_role"] = "admin" if username == "admin" else "user"
            st.success("로그인 성공!")
            # 최신 버전에서 st.experimental_rerun()을 사용할 수 있다면 활성화
            # st.experimental_rerun()
        else:
            st.error("사용자 이름이나 비밀번호가 올바르지 않습니다.")
    st.stop()  # 로그인되지 않은 경우 아래의 코드는 실행되지 않음

# ---------------------
# 3) DB 초기화
# ---------------------
def init_db(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            choice1 TEXT,
            choice2 TEXT,
            choice3 TEXT,
            choice4 TEXT,
            answer TEXT,
            explanation TEXT,
            difficulty INTEGER,
            chapter TEXT,
            type TEXT  -- 건축기사 기출문제 or 건축시공 기출문제
        )
    """)
    conn.commit()
    conn.close()

init_db("problems.db")

def update_db_types(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # 공백 및 개행 제거
    c.execute("UPDATE problems SET type = TRIM(type)")
    # 이전 값 변경: 예를 들어 '객관식'을 '건축기사 기출문제'로, '주관식'을 '건축시공 기출문제'로
    c.execute("UPDATE problems SET type = '건축기사 기출문제' WHERE type = '객관식'")
    c.execute("UPDATE problems SET type = '건축시공 기출문제' WHERE type = '주관식'")
    conn.commit()
    conn.close()

# 1. DB에 피드백 테이블 추가
def create_feedback_table(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            problem_id INTEGER,
            feedback_text TEXT,
            feedback_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_feedback_table("problems.db")

def record_feedback(user_id, problem_id, feedback_text, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, problem_id, feedback_text) VALUES (?, ?, ?)",
              (user_id, problem_id, feedback_text))
    conn.commit()
    conn.close()

def get_all_feedback(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM feedback ORDER BY feedback_time DESC", conn)
    conn.close()
    return df

def get_feedback_with_problem(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        f.id,
        f.user_id,
        f.problem_id,
        p.question AS 문제내용,
        f.feedback_text,
        f.feedback_time
    FROM feedback f
    LEFT JOIN problems p ON f.problem_id = p.id
    ORDER BY f.feedback_time DESC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# DB 초기화 후, DB의 type 필드를 업데이트합니다.
init_db("problems.db")
update_db_types()

def create_attempts_table(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            problem_id INTEGER,
            user_answer TEXT,   -- 추가된 컬럼: 사용자가 선택한 답안
            is_correct INTEGER,
            attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_attempts_table("problems.db")

def record_attempt(user_id, problem_id, user_answer, is_correct, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO attempts (user_id, problem_id, user_answer, is_correct) VALUES (?, ?, ?, ?)",
              (user_id, problem_id, user_answer, is_correct))
    conn.commit()
    conn.close()

# ---------------------
# 통계 및 대시보드 새로운 집계 추가
# ---------------------
def get_chapter_accuracy():
    conn = sqlite3.connect("problems.db")
    query = """
    SELECT 
        p.chapter,
        COUNT(a.id) AS total_attempts,
        SUM(a.is_correct) AS correct_attempts,
        ROUND(AVG(a.is_correct)*100, 2) AS accuracy_percentage
    FROM attempts a
    JOIN problems p ON a.problem_id = p.id
    GROUP BY p.chapter;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_user_stats():
    conn = sqlite3.connect("problems.db")
    query = """
    SELECT 
        user_id,
        COUNT(*) AS total_attempts,
        SUM(is_correct) AS correct_attempts,
        ROUND(AVG(is_correct)*100, 2) AS accuracy_percentage
    FROM attempts
    GROUP BY user_id;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_difficulty_stats():
    conn = sqlite3.connect("problems.db")
    query = """
    SELECT 
        p.difficulty,
        COUNT(a.id) AS total_attempts,
        SUM(a.is_correct) AS correct_attempts,
        ROUND(AVG(a.is_correct)*100, 2) AS accuracy_percentage
    FROM attempts a
    JOIN problems p ON a.problem_id = p.id
    GROUP BY p.difficulty;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_all_attempts():
    conn = sqlite3.connect("problems.db")
    df = pd.read_sql_query("SELECT * FROM attempts ORDER BY attempt_time DESC", conn)
    conn.close()
    return df

def get_detailed_attempts():
    conn = sqlite3.connect("problems.db")
    query = """
    SELECT 
        a.id,
        a.user_id,
        a.problem_id,
        p.question,
        p.answer AS correct_answer,
        a.user_answer,
        a.is_correct,
        a.attempt_time
    FROM attempts a
    JOIN problems p ON a.problem_id = p.id
    ORDER BY a.attempt_time DESC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_detailed_attempts_for_user(user_id):
    conn = sqlite3.connect("problems.db")
    query = """
    SELECT 
        a.id,
        a.user_id,
        a.problem_id,
        p.question AS problem_text,
        p.answer AS correct_answer,
        a.user_answer,
        a.is_correct,
        a.attempt_time
    FROM attempts a
    JOIN problems p ON a.problem_id = p.id
    WHERE a.user_id = ?
    ORDER BY a.attempt_time DESC;
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df

# ---------------------
# 4) 문제 생성/저장 함수들
# ---------------------
def generate_variation_question(df):
    """
    CSV에서 기존 문제 하나를 무작위로 뽑아,
    선택지만 섞은 객관식 문제를 반환.
    (건축기사 기출문제)
    """
    try:
        original_question = df.sample(n=1).to_dict(orient='records')[0]
        logging.info("샘플 데이터: %s", original_question)
    except Exception as e:
        logging.error("질문 샘플 추출 오류: %s", e)
        return None
    
    choices = [
        original_question.get('선택지1', ''),
        original_question.get('선택지2', ''),
        original_question.get('선택지3', ''),
        original_question.get('선택지4', '')
    ]
    random.shuffle(choices)
    
    try:
        correct_index = choices.index(original_question.get(f'선택지{original_question["정답"]}', '')) + 1
    except Exception as e:
        logging.error("정답 인덱스 결정 오류: %s", e)
        correct_index = 1

    new_question = {
        "문제": original_question.get('문제', ''),
        "선택지": choices,
        "정답": str(correct_index),  # 객관식 정답 (문자열)
        "유형": "건축기사 기출문제"  # CSV 문제
    }
    return new_question

def expand_question_with_gpt(base_question, base_choices, correct_answer, question_type="객관식"):
    if question_type == "객관식":
        prompt = f"""
기존 문제: {base_question}
기존 선택지: {base_choices}
정답: {correct_answer}

위 정보를 바탕으로, 완전히 새로운 객관식 4지선다형 문제를 만들어 주세요.
출력은 아래 JSON 형식만 사용:
{{
  "문제": "...",
  "선택지": ["...", "...", "...", "..."],
  "정답": "1"
}}

Please output valid JSON without any markdown formatting.
"""
    else:
        prompt = f"""
기존 문제: {base_question}

위 정보를 바탕으로, 완전히 새로운 주관식 문제를 만들어 주세요.
출력은 아래 JSON 형식만 사용:
{{
  "문제": "...",
  "모범답안": "..."
}}

Please output valid JSON without any markdown formatting.
"""
    messages = [
        {"role": "system", "content": "당신은 건축시공학 문제를 만드는 어시스턴트입니다."},
        {"role": "user", "content": prompt}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=700,
            temperature=1.0
        )
        result_text = response.choices[0].message.content.strip()
        logging.info("GPT raw output: %s", result_text)
    except Exception as e:
        logging.error("OpenAI API 호출 오류: %s", e)
        return None

    try:
        result_json = json.loads(result_text)
        return result_json
    except Exception as e:
        logging.error("JSON 파싱 오류: %s", e)
        logging.info("원시 응답: %s", result_text)
        return None

def classify_chapter(question_text):
    # 테스트용
    return "1"

def classify_difficulty(question_text):
    # 테스트용
    return 3

def generate_explanation(question_text, answer_text):
    prompt = f"""
문제: {question_text}
답안: {answer_text}

위 문제에 대해, 다음 두 가지 해설을 작성해 주세요.
1. 자세한 해설
2. 핵심 요약(3개 포인트)

출력은 아래 JSON 형식만 사용:
{{
  "자세한해설": "...",
  "핵심요약": ["...", "...", "..."]
}}

출력에 마크다운 포맷(예: ```json) 없이 순수 JSON만 출력해 주세요.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 건축시공학 문제 해설을 작성하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        finish_reason = response.choices[0].finish_reason
        logging.info(f"[finish_reason] {finish_reason}")

        raw_output = response.choices[0].message.content.strip()
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`").strip()
            if raw_output.lower().startswith("json"):
                raw_output = raw_output[4:].strip()
        logging.info(f"[해설 clean output] {raw_output}")
        
        explanation_dict = json.loads(raw_output)
        return explanation_dict

    except Exception as e:
        logging.error("해설 생성 오류: %s", e)
        return {"자세한해설": "해설 생성 중 오류가 발생했습니다.", "핵심요약": []}

def save_problem_to_db(problem, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    explanation_data = problem.get("해설", "")
    if isinstance(explanation_data, dict):
        explanation_data = json.dumps(explanation_data, ensure_ascii=False)
    c.execute("""
        INSERT INTO problems (question, choice1, choice2, choice3, choice4, answer, explanation, difficulty, chapter, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        problem.get("문제", ""),
        problem.get("선택지", ["", "", "", ""])[0],
        problem.get("선택지", ["", "", "", ""])[1],
        problem.get("선택지", ["", "", "", ""])[2],
        problem.get("선택지", ["", "", "", ""])[3],
        problem.get("정답", ""),
        explanation_data,
        problem.get("난이도", 3),
        problem.get("주제", "1"),
        problem.get("유형", "건축기사 기출문제")  # 기본값
    ))
    conn.commit()
    conn.close()

def generate_new_problem(question_type="객관식", source="건축시공 기출문제"):
    """
    GPT를 통해 완전히 새로운 문제(객관식/주관식)를 생성하여 DB에 저장.
    source 인자로 "건축시공 기출문제"로 구분.
    """
    # CSV 문제를 하나 뽑아 base_question, base_choices, correct_answer를 만듦
    base = generate_variation_question(df)
    if base is None:
        st.error("기존 문제 추출 실패")
        return None

    base_question = base["문제"]
    base_choices = base["선택지"]
    correct_answer = base["정답"]  # e.g. "2"

    # GPT로 새 문제 생성
    new_problem = expand_question_with_gpt(base_question, base_choices, correct_answer, question_type)
    if new_problem is None:
        st.error("GPT 문제 생성 실패")
        return None

    # 난이도/챕터
    chapter = classify_chapter(base_question)
    difficulty = classify_difficulty(base_question)

    # 해설 생성
    if question_type == "객관식":
        correct_idx = int(new_problem["정답"]) - 1
        ans_text = new_problem["선택지"][correct_idx]
    else:
        ans_text = new_problem["모범답안"]

    explanation_dict = generate_explanation(new_problem["문제"], ans_text)

    new_problem["해설"] = explanation_dict
    new_problem["난이도"] = difficulty
    new_problem["주제"] = chapter
    new_problem["유형"] = source  # "건축시공 기출문제"

    # DB에 저장
    save_problem_to_db(new_problem)
    return new_problem

def get_all_problems(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM problems")
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_problems_dict(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT id, question, choice1, choice2, choice3, choice4, 
               answer, explanation, difficulty, chapter, type
        FROM problems
    """)
    rows = c.fetchall()
    conn.close()

    problems = []
    for row in rows:
        problems.append({
            "id": row[0],
            "question": row[1],
            "choice1": row[2],
            "choice2": row[3],
            "choice3": row[4],
            "choice4": row[5],
            "answer": row[6],
            "explanation": row[7],
            "difficulty": row[8],
            "chapter": row[9],
            "유형": row[10]
        })
    return problems

def update_problem_in_db(problem_id, updated_problem, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        UPDATE problems
        SET question=?, choice1=?, choice2=?, choice3=?, choice4=?,
            answer=?, explanation=?, difficulty=?, chapter=?, type=?
        WHERE id=?
    """, (
        updated_problem["question"],
        updated_problem["choice1"],
        updated_problem["choice2"],
        updated_problem["choice3"],
        updated_problem["choice4"],
        updated_problem["answer"],
        updated_problem["explanation"],
        updated_problem["difficulty"],
        updated_problem["chapter"],
        updated_problem["유형"],
        problem_id
    ))
    conn.commit()
    conn.close()

# ---------------------
# 6) UI (탭)
# ---------------------
st.title("건축시공학 문제 생성 및 풀이")

if "user_role" in st.session_state:
    
    # 1. 탭 정의
    if st.session_state.user_role == "admin":
        tab_problem, tab_admin, tab_dashboard = st.tabs(["📘 문제풀이", "🛠 문제 관리", "📊 학습 통계"])
    else:
        tab_problem, tab_dashboard = st.tabs(["📘 문제풀이", "📊 학습 통계"])

# 관리자는 관리자 모드와 전체 통계 탭을 모두 볼 수 있게 함
st.markdown("""
    <style>
        .main {
            max-width: 1100px;
            margin: 0 auto;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- 사용자 모드 ---
with tab_problem:
    st.subheader("📘 문제풀이")

    col1, col2 = st.columns([2, 1])  # 문제/선택지 | 풀이/결과

    with col1:
        st.markdown("#### 문제 출처 및 생성")
        question_source = st.selectbox("문제 출처 선택", ["건축기사 기출문제", "건축시공 기출문제"])
        if question_source == "건축기사 기출문제":
            if st.button("CSV 문제 불러오기"):
                csv_problem = generate_variation_question(df)
                if csv_problem:
                    csv_problem["유형"] = "건축기사 기출문제"
                    save_problem_to_db(csv_problem)
                    st.session_state.current_problem = csv_problem
                    st.session_state.submitted_answer = False
                    st.success("건축기사 기출문제가 준비되었습니다!")
        else:
            gpt_question_type = st.selectbox("GPT 문제 유형 선택", ["객관식", "주관식"])
            if st.button("GPT 문제 생성"):
                new_prob = generate_new_problem(question_type=gpt_question_type, source="건축시공 기출문제")
                if new_prob:
                    st.session_state.current_problem = new_prob
                    st.session_state.submitted_answer = False
                    st.success("건축시공 기출문제가 생성되었습니다!")

    if "current_problem" in st.session_state and st.session_state.current_problem is not None:
        prob = st.session_state.current_problem

        with col1:
            st.markdown("#### 문제")
            st.write(prob["문제"])

            if prob["유형"] == "건축기사 기출문제" or ("모범답안" not in prob):
                user_choice = st.radio("정답을 고르세요:", prob["선택지"])
            else:
                user_choice = st.text_area("답안을 입력하세요:")

        with col2:
            st.markdown("#### 풀이 및 해설")
            if st.button("답안 제출"):
                st.session_state.submitted_answer = True

            if st.session_state.submitted_answer:
                correct = False
                if prob["유형"] == "건축기사 기출문제" or ("모범답안" not in prob):
                    correct_index = int(prob["정답"])
                    correct_choice = prob["선택지"][correct_index - 1]
                    if user_choice.strip() == correct_choice.strip():
                        st.success("정답입니다!")
                        correct = True
                    else:
                        st.error(f"오답입니다. 정답은 '{correct_choice}'")
                else:
                    correct_text = prob["모범답안"]
                    if user_choice.strip() == correct_text.strip():
                        st.success("정답입니다!")
                        correct = True
                    else:
                        st.error(f"오답입니다. 모범답안: {correct_text}")

                record_attempt(
                    user_id=st.session_state.get("username", "guest"),
                    problem_id=prob.get("id", 0),
                    user_answer=user_choice,
                    is_correct=int(correct)
                )

                # 해설 표시
                explanation = prob.get("해설", {})
                if isinstance(explanation, str):
                    try:
                        explanation = json.loads(explanation)
                    except:
                        explanation = {"자세한해설": "해설 없음", "핵심요약": []}
                st.write("**📘 자세한 해설**")
                st.write(explanation.get("자세한해설", "해설 없음"))
                st.write("**📌 핵심 요약**")
                for point in explanation.get("핵심요약", []):
                    st.markdown(f"- {point}")

                # 피드백 입력
                st.markdown("---")
                user_feedback = st.text_area("💬 피드백을 남겨주세요 (선택사항)")
                if st.button("피드백 제출"):
                    record_feedback(
                        st.session_state.get("username", "guest"),
                        prob.get("id", 0),
                        user_feedback
                    )
                    st.success("피드백이 제출되었습니다!")

# --- 관리자 모드 ---
if st.session_state.user_role == "admin":
    with tab_admin:
        st.subheader("🛠 문제 관리")

        st.markdown("#### 📂 CSV 문제 파일 업로드 (관리자 전용)")
        uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type="csv")

        df = None
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.success("CSV 파일이 성공적으로 업로드되었습니다.")
            except:
                st.error("CSV 파일을 읽는 중 오류가 발생했습니다.")

        if df is None:
            default_file_path = "456.csv"
            if os.path.exists(default_file_path):
                try:
                    df = pd.read_csv(default_file_path)
                    logging.info("기본 CSV 파일 로드 성공")
                except Exception as e:
                    logging.error("기본 CSV 파일 읽기 오류: %s", e)
                    st.error("기본 CSV 파일을 읽는 도중 오류 발생했습니다.")
                    st.stop()
            else:
                st.error("CSV 파일이 업로드되지 않았으며, 기본 파일도 존재하지 않습니다.")
                st.stop()

        col1, col2 = st.columns([2, 1])

    # 왼쪽: 문제 선택 및 편집
        with col1:
            st.markdown("#### 🔧 문제 선택 및 편집")

            problems = get_all_problems_dict()
            source_filter_dashboard = st.selectbox(
                "문제 출처(유형) 필터",
                ["전체", "건축기사 기출문제", "건축시공 기출문제"],
                key="filter_tab_admin"
            )
            if source_filter_dashboard != "전체":
                problems = [p for p in problems if p["유형"] == source_filter_dashboard]

            if problems:
                problem_options = {f"{p['id']} - {p['question'][:30]}": p for p in problems}
                selected_key = st.selectbox("편집할 문제 선택:", list(problem_options.keys()))
                selected_problem = problem_options[selected_key]

                # 편집 UI 코드 기존 그대로 유지

            else:
                st.info("해당 유형의 문제가 없습니다.")

            st.markdown("#### ✏️ 문제 수정")

            # 문제 필드 편집
            edited_question = st.text_area("문제 내용", value=selected_problem["question"])
            edited_choice1 = st.text_input("선택지 1", value=selected_problem["choice1"])
            edited_choice2 = st.text_input("선택지 2", value=selected_problem["choice2"])
            edited_choice3 = st.text_input("선택지 3", value=selected_problem["choice3"])
            edited_choice4 = st.text_input("선택지 4", value=selected_problem["choice4"])
            edited_answer = st.selectbox("정답 선택 (숫자)", ["1", "2", "3", "4"], index=int(selected_problem["answer"]) - 1)
            edited_difficulty = st.slider("난이도", 1, 5, value=selected_problem["difficulty"])
            edited_chapter = st.text_input("챕터 (예: 1)", value=selected_problem["chapter"])
            edited_type = st.selectbox("문제 유형", ["건축기사 기출문제", "건축시공 기출문제"], index=0 if selected_problem["유형"] == "건축기사 기출문제" else 1)
            edited_explanation = st.text_area("해설 (JSON 형식)", value=selected_problem["explanation"])

            # 저장 버튼
            if st.button("💾 수정 내용 저장"):
                updated_problem = {
                    "question": edited_question,
                    "choice1": edited_choice1,
                    "choice2": edited_choice2,
                    "choice3": edited_choice3,
                    "choice4": edited_choice4,
                    "answer": edited_answer,
                    "difficulty": edited_difficulty,
                    "chapter": edited_chapter,
                    "유형": edited_type,
                    "explanation": edited_explanation
                }
                update_problem_in_db(selected_problem["id"], updated_problem)
                st.success("문제가 성공적으로 수정되었습니다.")

        # 오른쪽: 활동내역, 피드백, 알림
        with col2:
            st.markdown("#### 📋 활동 및 피드백")

            filter_user = st.text_input("사용자명 필터")
            date_range = st.date_input("날짜 범위 선택", [])
            query = "SELECT * FROM attempts"
            params, conditions = [], []
            if filter_user:
                conditions.append("user_id = ?")
                params.append(filter_user)
            if len(date_range) == 2:
                conditions.append("DATE(attempt_time) BETWEEN ? AND ?")
                params.extend([date_range[0].strftime("%Y-%m-%d"), date_range[1].strftime("%Y-%m-%d")])
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY attempt_time DESC"
            conn = sqlite3.connect("problems.db")
            filtered_attempts = pd.read_sql_query(query, conn, params=params)
            conn.close()
            if not filtered_attempts.empty:
                st.dataframe(filtered_attempts)
            else:
                st.info("해당 활동 내역 없음.")

            st.markdown("#### 💬 피드백 보기")
            feedback_df = get_feedback_with_problem()
            if not feedback_df.empty:
                st.dataframe(feedback_df)
            else:
                st.info("피드백 없음.")

            st.markdown("#### ⚠️ 낮은 정답률 챕터")
            chapter_accuracy = get_chapter_accuracy()
            low_accuracy = chapter_accuracy[chapter_accuracy["accuracy_percentage"] <= 50]
            if not low_accuracy.empty:
                st.warning("정답률이 낮은 챕터가 있습니다.")
                st.dataframe(low_accuracy)
            else:
                st.info("정답률이 낮은 챕터가 없습니다.")

# --- 통계 및 대시보드 ---
with tab_dashboard:
    st.subheader("📊 학습 통계")

    col1, col2 = st.columns([2, 1])

    # 왼쪽: 문제 및 주제 분포 시각화
    with col1:
        st.markdown("#### 📘 문제 통계 시각화")

        problems_all = get_all_problems_dict()
        if st.session_state.user_role == "admin":
            source_filter_dashboard = st.selectbox(
                "문제 출처(유형) 필터",
                ["전체", "건축기사 기출문제", "건축시공 기출문제"],
                key="filter_tab3_admin"
            )
            if source_filter_dashboard != "전체":
                problems_all = [p for p in problems_all if p["유형"] == source_filter_dashboard]

        if problems_all:
            df_stats = pd.DataFrame(problems_all)
            st.write("전체 문제 개수:", len(df_stats))
            st.bar_chart(df_stats["유형"].value_counts())
            st.bar_chart(df_stats["difficulty"].value_counts().sort_index())
            st.bar_chart(df_stats["chapter"].value_counts())
        else:
            st.info("저장된 문제가 없습니다.")

    # 오른쪽: 정답률 통계
    with col2:
        st.markdown("#### 📌 정답률 및 사용자 통계")

        if st.session_state.user_role == "admin":
            st.markdown("**사용자별 정확도**")
            user_stats = get_user_stats()
            if not user_stats.empty:
                st.bar_chart(user_stats.set_index("user_id")["accuracy_percentage"])
            else:
                st.info("사용자 통계 없음.")

        if st.session_state.user_role != "admin":
            user_id = st.session_state.username
            def get_personal_stats(user_id):
                conn = sqlite3.connect("problems.db")
                query = """
                SELECT user_id, COUNT(*) AS total_attempts, 
                       SUM(is_correct) AS correct_attempts, 
                       ROUND(AVG(is_correct)*100, 2) AS accuracy_percentage
                FROM attempts
                WHERE user_id = ?
                GROUP BY user_id;
                """
                return pd.read_sql_query(query, conn, params=(user_id,))
            personal_stats = get_personal_stats(user_id)
            if not personal_stats.empty:
                st.bar_chart(personal_stats.set_index("user_id")["accuracy_percentage"])
            else:
                st.info("개인 통계 없음.")



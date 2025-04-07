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
import uuid
import base64

logging.basicConfig(level=logging.INFO, force=True)

st.set_page_config(layout="wide")

def init_state():
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
        st.session_state.user_role = "user"
    if 'username' not in st.session_state:
        st.session_state.username = "guest"

init_state()

# ---------------------
# 1) API 키 설정
# ---------------------
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("API key 설정 오류: secrets.toml에 OPENAI_API_KEY가 없습니다.")
    st.stop()

# Streamlit 기본 설정
st.title("건축시공학 문제 생성 및 풀이")

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
            # st.rerun()
        else:
            st.error("사용자 이름이나 비밀번호가 올바르지 않습니다.")
    st.stop()  # 로그인되지 않은 경우 아래의 코드는 실행되지 않음

# ---------------------
# 3) DB 초기화
# ---------------------
def init_db(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    cursor = conn.cursor()
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
    cursor = conn.cursor()
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
    cursor = conn.cursor()
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, problem_id, feedback_text) VALUES (?, ?, ?)",
              (user_id, problem_id, feedback_text))
    conn.commit()
    conn.close()

def get_all_feedback(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    df = pd.read_sql_query("SELECT * FROM feedback ORDER BY feedback_time DESC", conn)
    conn.close()
    return df

def get_feedback_with_problem(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    cursor = conn.cursor()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            problem_id INTEGER,
            user_answer TEXT,
            is_correct INTEGER,
            attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_attempts_table("problems.db")

def record_attempt(user_id, problem_id, user_answer, is_correct, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    c = conn.cursor()
    c.execute("INSERT INTO attempts (user_id, problem_id, user_answer, is_correct) VALUES (?, ?, ?, ?)",
              (user_id, problem_id, user_answer, is_correct))
    conn.commit()
    conn.close()

# ---------------------
# 통계 및 대시보드 새로운 집계 추가
# ---------------------
def get_chapter_accuracy():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor("problems.db")
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor("problems.db")
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor("problems.db")
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor("problems.db")
    df = pd.read_sql_query("SELECT * FROM attempts ORDER BY attempt_time DESC", conn)
    conn.close()
    return df

def get_detailed_attempts():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor("problems.db")
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor("problems.db")
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
def generate_variation_question(df, question_type=None):
    """
    CSV에서 기존 문제 하나를 무작위로 뽑아,
    선택지만 섞은 객관식 문제를 반환.
    (건축기사 기출문제)
    """
    try:
        # 객관식: 선택지가 모두 있는 경우
        if question_type == "객관식":
            filtered_df = df.dropna(subset=["선택지1", "선택지2", "선택지3", "선택지4"], how="any")
        # 주관식: 선택지들이 모두 비어있는 경우
        elif question_type == "주관식":
            filtered_df = df[
                df[["선택지1", "선택지2", "선택지3", "선택지4"]].isnull().all(axis=1)
            ]
        else:
            filtered_df = df

        if filtered_df.empty:
            logging.warning(f"문제 유형 '{question_type}' 에 해당하는 문제가 없습니다.")
            return None

        original_question = filtered_df.sample(n=1).to_dict(orient='records')[0]

    except Exception as e:
        logging.error("질문 샘플 추출 오류: %s", e)
        return None

    # 객관식인지 주관식인지 판별
    is_objective = all(original_question.get(opt, '') != '' for opt in ['선택지1', '선택지2', '선택지3', '선택지4'])

    choices = []
    correct_index = None
    if is_objective:
        choices = [
            original_question.get('선택지1', ''),
            original_question.get('선택지2', ''),
            original_question.get('선택지3', ''),
            original_question.get('선택지4', '')
        ]
        random.shuffle(choices)
        try:
            correct_choice = original_question.get(f'선택지{original_question["정답"]}', '')
            correct_index = choices.index(correct_choice) + 1
        except Exception as e:
            logging.error("정답 인덱스 결정 오류: %s", e)
            correct_index = 1

    new_question = {
        "문제": original_question.get('문제', ''),
        "선택지": choices if choices else None,
        "정답": str(correct_index) if correct_index else str(original_question.get("정답", "")),
        "유형": original_question.get('구분', "건축기사 기출문제"),
        "문제형식": "객관식" if is_objective else "주관식",
        "explanation": original_question.get('해설', '해설 없음'),
        "id": original_question.get('id', None)
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

출력에 마크다운 포맷(예: 
json) 없이 순수 JSON만 출력해 주세요.
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

# 문제 DB 저장 함수
def save_problem_to_db(problem_data, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    choices = problem_data.get("선택지", ["", "", "", ""])
    while len(choices) < 4:
        choices.append("")

    problem_data['id'] = str(uuid.uuid4())

    cursor.execute('''
        INSERT INTO problems (question, choice1, choice2, choice3, choice4, answer, explanation, difficulty, chapter, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        problem_data.get("문제", ""),
        choices[0],
        choices[1],
        choices[2],
        choices[3],
        problem_data.get("정답", ""),
        problem_data.get("해설", ""),
        3,  # difficulty 기본값
        "1",  # chapter 기본값
        problem_data.get("type", "건축기사 기출문제")
    ))
    problem_id = cursor.lastrowid  # ✅ 추가: 저장된 id 가져오기

    conn.commit()
    conn.close()

    return problem_id  # ✅ 추가: 반환

# ✅ 문제 불러오기 (DB 기반)
def load_csv_problems():
    try:
        df = pd.read_csv("456.csv")
        problems = df.to_dict(orient='records')
        for problem in problems:
            problem['id'] = str(uuid.uuid4())
            problem['문제출처'] = '건축기사 기출문제'
        return problems
    except FileNotFoundError:
        st.warning("CSV 파일이 존재하지 않습니다. 관리자 모드에서 업로드해주세요!")
        return []

def load_problems_from_db(problem_source, question_format, limit=1, db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    if question_format == "객관식":
        # 선택지가 있는 경우
        query = """
        SELECT id, question, choice1, choice2, choice3, choice4, answer, explanation, difficulty, chapter, type 
        FROM problems 
        WHERE type = ? AND choice1 != '' AND choice2 != '' AND choice3 != '' AND choice4 != ''
        ORDER BY RANDOM() 
        LIMIT ?
        """
    else:
        # 선택지가 모두 없는 경우
        query = """
        SELECT id, question, choice1, choice2, choice3, choice4, answer, explanation, difficulty, chapter, type 
        FROM problems 
        WHERE type = ? AND choice1 = '' AND choice2 = '' AND choice3 = '' AND choice4 = ''
        ORDER BY RANDOM() 
        LIMIT ?
        """

    c.execute(query, (problem_source, limit))
    rows = c.fetchall()
    conn.close()

    problems = []
    for row in rows:
        problems.append({
            "id": row[0],
            "문제": row[1],
            "선택지": [row[2], row[3], row[4], row[5]],
            "정답": row[6],
            "해설": row[7],
            "난이도": row[8],
            "챕터": row[9],
            "문제형식": question_format,
            "문제출처": row[10]
        })
    return problems

# ✅ 문제 수정 함수 (관리자용)
def update_problem_in_db(problem_id, updated_data):
    cursor.execute('''
        UPDATE problems SET 문제=?, 선택지1=?, 선택지2=?, 선택지3=?, 선택지4=?, 정답=?, 해설=?, 문제형식=?, 문제출처=? WHERE id=?
    ''', (
        updated_data["문제"],
        updated_data["선택지"][0],
        updated_data["선택지"][1],
        updated_data["선택지"][2],
        updated_data["선택지"][3],
        updated_data["정답"],
        updated_data["해설"],
        updated_data["문제형식"],
        updated_data["문제출처"],
        problem_id
    ))
    conn.commit()

# ✅ 문제 삭제 함수 (관리자용)
def delete_problem_from_db(problem_id):
    cursor.execute('DELETE FROM problems WHERE id=?', (problem_id,))
    conn.commit()

# OpenAI 문제 생성 함수
def generate_openai_problem(question_type, problem_source):
    if question_type == "객관식":
        prompt = f"""
        당신은 건축시공학 교수입니다. 건축시공학과 관련된 객관식 4지선다형 문제를 하나 출제하세요.
        아래 형식의 JSON 으로 출력하세요. JSON 외의 텍스트는 출력하지 마세요.

        {{
          "문제": "...",
          "선택지1": "...",
          "선택지2": "...",
          "선택지3": "...",
          "선택지4": "...",
          "정답": "1",
          "해설": "..."
        }}
        """
    else:  # 주관식
        prompt = f"""
        당신은 건축시공학 교수입니다. 건축시공학과 관련된 주관식 문제를 하나 출제하세요.
        아래 형식의 JSON 으로 출력하세요. JSON 외의 텍스트는 출력하지 마세요.

        {{
          "문제": "...",
          "모범답안": "...",
          "해설": "..."
        }}
        """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    result = response['choices'][0]['message']['content']

    try:
        result_json = json.loads(result)

        # 🧩 주관식인 경우 선택지 빈 값으로, 모범답안 → 정답으로 매핑
        if question_type == "주관식":
            problem_data = {
                "문제": result_json.get("문제", ""),
                "선택지": ["", "", "", ""],  # 주관식이므로 빈값
                "정답": result_json.get("모범답안", ""),
                "문제출처": problem_source,
                "문제형식": question_type,
                "해설": result_json.get("해설", ""),
                "id": None
            }
        else:
            problem_data = {
                "문제": result_json.get("문제", ""),
                "선택지": [
                    result_json.get("선택지1", ""),
                    result_json.get("선택지2", ""),
                    result_json.get("선택지3", ""),
                    result_json.get("선택지4", "")
                ],
                "정답": result_json.get("정답", ""),
                "문제출처": problem_source,
                "문제형식": question_type,
                "해설": result_json.get("해설", ""),
                "id": None
            }

        save_problem_to_db(problem_data)
        return problem_data

    except json.JSONDecodeError as e:
        logging.error(f"GPT 응답 JSON 파싱 오류: {e}")
        st.error("GPT 응답을 JSON으로 파싱하는 중 오류가 발생했습니다. 프롬프트를 다시 확인하세요.")
        return None

def get_table_download_link(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="problems_export.csv">📥 문제 CSV 다운로드</a>'
    return href

def export_problems_to_csv(db_path="problems.db", export_path="problems_export.csv"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM problems", conn)
    df.to_csv(export_path, index=False, encoding='utf-8-sig')
    conn.close()

# 문제 풀이 UI 출력 함수
def display_problems():
    correct_count = 0
    total = len(st.session_state.problem_list)

    for idx, prob in enumerate(st.session_state.problem_list):
        st.markdown(f"### 문제 {idx + 1}: {prob['문제']}")
        unique_key = f"answer_{idx}_{prob['id']}"

        user_answer = st.radio(
            f"답안 선택 (문제 {idx + 1})",
            prob.get('선택지', ['']) if prob.get('문제형식') == '객관식' else [],
            key=unique_key
        )

        st.session_state.user_answers[prob['id']] = user_answer

        # 채점 버튼 (문제별)
        if st.button(f"문제 {idx + 1} 채점하기", key=f"grade_{prob['id']}"):
            is_correct = user_answer == prob['정답']
            st.session_state.show_results[prob['id']] = is_correct
            st.experimental_rerun()

        # 결과 출력
        if st.session_state.show_results.get(prob['id'], False):
            if user_answer == prob['정답']:
                st.success("정답입니다!")
            else:
                st.error(f"오답입니다. 정답: {prob['정답']}")
                with st.expander("해설 보기"):
                    st.info(prob['해설'])

    # 전체 결과 출력
    if total > 0:
        st.markdown(f"최종 정답률: **{correct_count} / {total}** ({(correct_count/total)*100:.2f}%)")
    else:
        st.markdown("문제가 없습니다. 먼저 문제를 생성하거나 선택해주세요.")
        correct_count = sum(
            1 for prob in st.session_state.problem_list
            if st.session_state.user_answers.get(prob['id']) == prob['정답']
        )
        st.markdown(f"### 총 정답 수: {correct_count} / {total}")

# ✅ 전체 문제 조회 (관리자용)
def get_all_problems_dict(db_path="problems.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM problems")
    rows = cursor.fetchall()
    conn.close()

    problem_list = []
    for row in rows:
        # 선택지가 모두 비어 있으면 주관식
        if not any([row[2], row[3], row[4], row[5]]):
            question_format = "주관식"
        else:
            question_format = "객관식"

        problem_list.append({
            "id": row[0],
            "문제": row[1],
            "선택지": [row[2], row[3], row[4], row[5]] if row[2] else [],
            "정답": row[6],
            "해설": row[7],
            "난이도": row[8],
            "챕터": row[9],
            "문제형식": question_format,
            "문제출처": row[10]
        })
    return problem_list

# ✅ 로그인 함수
def login():
    user_id = st.sidebar.text_input("아이디")
    password = st.sidebar.text_input("비밀번호", type="password")
    if st.sidebar.button("로그인"):
        if user_id == "admin" and password == "1234":
            st.session_state.user_role = "admin"
            st.sidebar.success("관리자 로그인 성공!")
        else:
            st.session_state.user_role = "user"
            st.sidebar.success("사용자 로그인 성공!")

# ✅ 초기 세션 상태
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# ---------------------
# 6) UI (탭)
# ---------------------
login()

# 탭 구성
st.title("건축시공학 하이브리드 문제풀이 시스템 🎉")

tab_problem, tab_admin, tab_dashboard = st.tabs(["문제풀이", "문제 관리", "통계 및 대시보드"])

with tab_problem:
    st.subheader("문제풀이")
    col1, col2 = st.columns([2, 4])  # 문제 출제 / 문제 풀이

    with col1:
        st.markdown("### 문제 출처 및 수 선택")
        selected_source = st.radio("문제 출처 선택", ("건축기사 기출문제", "건축시공 기출문제"))
        num_objective = st.number_input("객관식 문제 수", min_value=1, value=3, step=1)
        num_subjective = 0
        if selected_source == "건축시공 기출문제":
            num_subjective = st.number_input("주관식 문제 수", min_value=0, value=2, step=1)

        if st.button("문제 시작하기"):
            st.session_state.problem_list = []
            st.session_state.show_problems = True
            st.session_state.user_answers = {}
            st.session_state.show_results = {}

            if selected_source == "건축기사 기출문제":
                try:
                    df = pd.read_csv("456.csv")
                    if not df.empty:
                        sampled_df = df.sample(n=num_objective, random_state=42)
                        problems = sampled_df.to_dict(orient='records')
                        for prob in problems:
                            prob['id'] = str(uuid.uuid4())
                            prob['문제출처'] = '건축기사 기출문제'
                            prob['문제형식'] = '객관식'
                            prob['선택지'] = [prob.get('선택지1', ''), prob.get('선택지2', ''), prob.get('선택지3', ''), prob.get('선택지4', '')]
                            prob['정답'] = str(prob.get('정답', ''))
                            prob['해설'] = prob.get('해설', '')
                            problem_id = save_problem_to_db(prob, db_path="problems.db")

                            prob['id'] = problem_id
                            st.session_state.problem_list.append(prob)

                        st.success(f"CSV에서 문제 {len(st.session_state.problem_list)}개 불러오기 완료!")
                    else:
                        st.warning("CSV 파일에 문제가 없습니다. 파일을 확인해주세요!")
                except FileNotFoundError:
                    st.error("CSV 파일이 존재하지 않습니다. 관리자 모드에서 업로드해주세요!")
                except Exception as e:
                    st.error(f"문제 불러오기 중 오류 발생: {e}")

            elif selected_source == "건축시공 기출문제":
                for _ in range(num_objective):
                    prob = load_problems_from_db("건축시공 기출문제", "객관식", 1)
                    if prob:
                        st.session_state.problem_list.extend(prob)

                for _ in range(num_subjective):
                    prob = load_problems_from_db("건축시공 기출문제", "주관식", 1)
                    if prob:
                        st.session_state.problem_list.extend(prob)

    # ✅ 총 문제 수 검증 추가
                total = len(st.session_state.problem_list)
                if total == 0:
                    st.warning("문제가 없습니다. 문제를 먼저 생성하거나 선택해주세요.")
                else:
                    correct_count = sum(1 for prob in st.session_state.problem_list if prob.get("is_correct", False))
                    st.markdown(f"최종 정답률: **{correct_count} / {total}** ({(correct_count/total)*100:.2f}%)")

    with col2:
        if st.session_state.get("show_problems", False):
            st.markdown("### 📝 문제 풀이")
            for idx, prob in enumerate(st.session_state.problem_list):
                st.markdown(f"### 문제 {idx + 1}: {prob['문제']}")
                unique_key = f"answer_{idx}_{prob['문제형식']}_{prob['문제출처']}"
                if prob["문제형식"] == "객관식":
                    answer = st.radio("선택지", prob["선택지"], key=f"answer_{idx}")
                else:
                    answer = st.text_area("답안을 입력하세요", key=f"answer_{idx}")
                st.session_state.user_answers[idx] = answer

            if st.button("채점하기"):
                problem_key = prob.get("id", idx)
                st.session_state.show_results[problem_key] = True
                st.rerun()

        if st.session_state.get("show_results", False):
            st.markdown("### ✅ 채점 결과")
            correct_count = 0
            total = len(st.session_state.problem_list)

            for idx, prob in enumerate(st.session_state.problem_list):
                user_answer = st.session_state.user_answers.get(idx, "").strip()
                correct_answer = str(prob["정답"]).strip()

                # 시도 기록 저장
                conn = sqlite3.connect("problems.db")
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO attempts (user_id, problem_id, user_answer, is_correct)
                    VALUES (?, ?, ?, ?)
                ''', (
                    st.session_state.username,  # user_id
                    prob['id'],                 # problem_id
                    user_answer,                # user_answer
                    1 if user_answer == correct_answer else 0  # is_correct (정답 여부)
                ))
                conn.commit()
                conn.close()

                if user_answer == correct_answer:
                    st.success(f"문제 {idx + 1}: 정답 🎉")
                    correct_count += 1
                else:
                    st.error(f"문제 {idx + 1}: 오답 ❌ (정답: {correct_answer})")
                    with st.expander(f"문제 {idx + 1} 해설 보기"):
                        st.info(prob.get("해설", "해설이 등록되지 않았습니다."))
                    feedback = st.text_area(f"문제 {idx + 1} 피드백 작성", key=f"feedback_{idx}")
                    if st.button(f"문제 {idx + 1} 피드백 저장", key=f"save_feedback_{idx}"):
                        if feedback.strip():
                            cursor.execute('''
                                INSERT INTO feedback (문제ID, 피드백) VALUES (?, ?)
                            ''', (prob['id'], feedback))
                            conn.commit()
                            st.success("피드백이 저장되었습니다.")

                st.markdown(f"### 🎯 최종 정답률: **{correct_count} / {total}** ({(correct_count/total)*100:.2f}%)")

                if st.button("다시 풀기", key=f"retry_button_{idx}"):
                    for key in list(st.session_state.keys()):
                        if key.startswith("answer_") or key in ["problem_list", "user_answers", "show_problems", "show_results"]:
                            del st.session_state[key]
                    st.rerun()

# ============================== 관리자 모드 ==============================

with tab_admin:
    if st.session_state.user_role != "admin":
        st.warning("관리자만 접근할 수 있습니다.")
    else:
        st.header("문제 관리 (관리자 전용)")

        # 문제 생성 (GPT)
        st.subheader("OpenAI 문제 생성")
        problem_source = st.selectbox("문제 출처 선택", ["건축시공 기출문제"], key="select_problem_source")
        if st.button("GPT 문제 생성 (객관식)"):
            generate_openai_problem("객관식", problem_source)
            st.success(f"{problem_source} 객관식 문제 생성 완료!")

        if st.button("GPT 문제 생성 (주관식)"):
            generate_openai_problem("주관식", problem_source)
            st.success(f"{problem_source} 주관식 문제 생성 완료!")

        # CSV 문제 업로드
        st.subheader("CSV 문제 업로드")
        uploaded_file = st.file_uploader("CSV 파일 업로드 (관리자 전용)", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                problem_data = {
                    "문제": row['문제'],
                    "선택지": [
                        row.get('선택지1', ''),
                        row.get('선택지2', ''),
                        row.get('선택지3', ''),
                        row.get('선택지4', '')
                    ],
                    "정답": str(row.get('정답', '')),
                    "문제출처": "건축기사 기출문제",
                    "문제형식": "객관식",
                    "해설": row.get('해설', ''),
                    "id": None
                }
                save_problem_to_db(problem_data)
            st.success("CSV 업로드가 완료되었습니다!")

        # 문제 목록 조회 및 편집
        st.subheader("문제 목록")

        # ✅ 문제 출처 선택
        problem_sources = ["건축시공 기출문제"]
        selected_source = st.selectbox("문제 출처 선택", problem_sources, key="select_problem_list_source")

        # 전체 문제 불러오기
        problems = get_all_problems_dict()

        # ✅ 선택한 출처에 맞는 문제만 필터링
        filtered_problems = [prob for prob in problems if prob['문제출처'] == selected_source]

        # ✅ 총 문제 수 표시
        st.markdown(f"**총 {len(filtered_problems)}개 문제가 있습니다.**")

        objective_count = 1
        subjective_count = 1

        if not filtered_problems:
            st.write("선택한 출처에 해당하는 문제가 없습니다.")
        else:
            for prob in filtered_problems:
                # 문제 형식에 따라 제목 다르게 지정
                if prob['문제형식'] == '객관식':
                    title = f"객관식 문제 {objective_count}번: {prob['문제'][:30]}..."
                    objective_count += 1
                else:
                    title = f"주관식 문제 {subjective_count}번: {prob['문제'][:30]}..."
                    subjective_count += 1

                with st.expander(title):
                    # 기존 코드 그대로 유지!
                    problem_text = st.text_area("문제 내용", prob['문제'], key=f"edit_problem_{prob['id']}")

                    if prob['문제형식'] == "객관식":
                        edited_choices = [
                            st.text_input(f"선택지 {i+1}", prob['선택지'][i] if i < len(prob['선택지']) else "", key=f"edit_choice_{i}_{prob['id']}")
                            for i in range(4)
                        ]
                        edited_answer = st.selectbox(
                            "정답 선택 (숫자)",
                            ["1", "2", "3", "4"],
                            index=int(prob['정답']) - 1 if prob['정답'].isdigit() and int(prob['정답']) in range(1, 5) else 0,
                            key=f"edit_answer_{prob['id']}"
                        )
                    else:
                        edited_choices = ["", "", "", ""]
                        edited_answer = st.text_input("정답 입력", prob['정답'], key=f"edit_answer_{prob['id']}")

                    edited_explanation = st.text_area("해설", prob['해설'], key=f"edit_explanation_{prob['id']}")

                    # ✅ 수정 저장 버튼
                    if st.button("문제 수정 저장", key=f"save_edit_{prob['id']}"):
                        updated_data = {
                            "문제": problem_text,
                            "선택지": edited_choices,
                            "정답": edited_answer,
                            "해설": edited_explanation,
                            "문제형식": prob['문제형식'],
                            "문제출처": prob['문제출처']
                        }
                        update_problem_in_db(prob['id'], updated_data)
                        st.success("문제가 수정되었습니다!")

                    # ✅ 삭제 버튼
                    if st.button("문제 삭제", key=f"delete_{prob['id']}"):
                        delete_problem_from_db(prob['id'])
                        st.warning("문제가 삭제되었습니다!")

        # ✅ 문제 CSV 내보내기 다운로드 (여기!)
        st.subheader("문제 CSV 다운로드")
        if st.button("문제 CSV로 내보내기"):
            export_problems_to_csv()
            st.success("문제를 CSV 파일로 저장했습니다.")
            st.markdown(get_table_download_link("problems_export.csv"), unsafe_allow_html=True)

# ============================== 통계 및 대시보드 ==============================
with tab_dashboard:
    st.header("📊 통계 및 대시보드")

    conn = sqlite3.connect("problems.db")
    cursor = conn.cursor()

    # ✅ 전체 정답률
    cursor.execute("SELECT is_correct FROM attempts")
    results = cursor.fetchall()
    if results:
        df = pd.DataFrame(results, columns=['정답여부'])
        summary = df['정답여부'].value_counts()
        st.subheader("전체 정답률")
        st.bar_chart(summary)
    else:
        st.write("풀이 기록이 없습니다.")

    # ✅ 문제 유형별 시도 기록
    cursor.execute("""
        SELECT type, COUNT(*) FROM problems 
        JOIN attempts ON problems.id = attempts.problem_id
        GROUP BY type
    """)
    data = cursor.fetchall()
    if data:
        df = pd.DataFrame(data, columns=['문제형식', '시도 수'])
        st.subheader("문제 출처별 시도 기록")
        st.bar_chart(df.set_index('문제형식'))
    else:
        st.write("문제풀이 기록이 없습니다.")

    # ✅ 챕터별 정답률
    df_chapter = get_chapter_accuracy()
    if not df_chapter.empty:
        st.subheader("챕터별 정답률")
        st.bar_chart(df_chapter.set_index('chapter')['accuracy_percentage'])
    else:
        st.write("챕터별 풀이 기록이 없습니다.")

    # ✅ 사용자별 통계
    df_user = get_user_stats()
    if not df_user.empty:
        st.subheader("사용자별 풀이 통계")
        st.bar_chart(df_user.set_index('user_id')['accuracy_percentage'])
    else:
        st.write("사용자 풀이 기록이 없습니다.")

    # ✅ 난이도별 통계
    df_difficulty = get_difficulty_stats()
    if not df_difficulty.empty:
        st.subheader("난이도별 풀이 통계")
        st.bar_chart(df_difficulty.set_index('difficulty')['accuracy_percentage'])
    else:
        st.write("난이도별 풀이 기록이 없습니다.")

    conn.close()
from db.connection import get_connection
import pandas as pd
import os
import csv
from datetime import datetime

def record_feedback(user_id, problem_id, feedback_text):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (user_id, problem_id, feedback_text)
            VALUES (?, ?, ?)
        """, (user_id, problem_id, feedback_text))
        conn.commit()

def get_all_feedback():
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM feedback ORDER BY feedback_time DESC", conn)

def record_attempt(user_id, problem_id, user_answer, is_correct):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attempts (user_id, problem_id, user_answer, is_correct)
            VALUES (?, ?, ?, ?)
        """, (user_id, problem_id, user_answer, is_correct))
        conn.commit()

def save_result_to_csv(user_id, question, selected, correct, concept, is_correct, solve_time):
    file_path = "data/results.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)  # ✅ 폴더 없으면 자동 생성

    file_exists = os.path.exists(file_path)
    with open(file_path, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["사용자ID", "문제", "선택한답", "정답", "정오답", "풀이날짜", "개념", "풀이시간"])
        writer.writerow([
            user_id,
            question,
            selected,
            correct,
            "정답" if is_correct else "오답",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            concept,
            solve_time
        ])

def save_problem_to_db(problem_data, db_path="problems.db"):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        choices = problem_data.get("선택지", ["", "", "", ""])
        while len(choices) < 4:
            choices.append("")

        cursor.execute('''
            INSERT INTO problems (question, choice1, choice2, choice3, choice4, answer, explanation, difficulty, chapter, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            problem_data.get("question", problem_data.get("문제", "")),
            choices[0],
            choices[1],
            choices[2],
            choices[3],
            problem_data.get("정답", ""),
            problem_data.get("해설", ""),
            3,                          # 기본 난이도
            "1",                        # 기본 챕터
            problem_data.get("문제출처", "건축기사 기출문제")
        ))
        problem_id = cursor.lastrowid
        conn.commit()

    problem_data['id'] = problem_id
    return {
        **problem_data,
        'id': problem_id
    }

def load_problems_from_db(problem_type, problem_format, limit=1):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, question, choice1, choice2, choice3, choice4, answer, explanation, difficulty, chapter, type
            FROM problems
            WHERE type = ? AND
                  (CASE WHEN ? = '객관식' THEN choice1 IS NOT NULL ELSE choice1 IS NULL OR choice1 = '' END)
            ORDER BY RANDOM()
            LIMIT ?
        """, (problem_type, problem_format, limit))

        rows = cursor.fetchall()
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
                "문제출처": row[10],
                "문제형식": problem_format
            })
        return problems

def update_problem_in_db(problem_id, updated_data):
    with get_connection() as conn:
        cursor = conn.cursor()
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

def export_problems_to_csv(db_path="problems.db", export_path="problems_export.csv"):
    with get_connection(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM problems", conn)
        df.to_csv(export_path, index=False, encoding='utf-8-sig')

def delete_problem(problem_id, db_path="problems.db"):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
        conn.commit()

def get_all_problems_dict(db_path="problems.db"):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM problems")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    problem_list = []
    for row in rows:
        data = dict(zip(columns, row))
        choices = [data.get('choice1', ''), data.get('choice2', ''), data.get('choice3', ''), data.get('choice4', '')]
        question_format = "객관식" if any(choices) else "주관식"

        problem_list.append({
            "id": data.get('id'),
            "문제": data.get('question', ''),
            "선택지": choices if question_format == "객관식" else [],
            "정답": data.get('answer', ''),
            "해설": data.get('explanation', ''),
            "난이도": data.get('difficulty', 3),
            "챕터": data.get('chapter', "1"),
            "문제형식": question_format,
            "문제출처": data.get('type', '건축기사 기출문제')
        })

    return problem_list

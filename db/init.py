from db.connection import get_connection

def init_db(db_path="problems.db"):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
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
                type TEXT
            )
        """)
        conn.commit()

def create_feedback_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                problem_id INTEGER,
                feedback_text TEXT,
                feedback_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def create_attempts_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
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

def update_db_types(db_path="problems.db"):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE problems SET type = TRIM(type)")
        cursor.execute("UPDATE problems SET type = '건축기사 기출문제' WHERE type = '객관식'")
        cursor.execute("UPDATE problems SET type = '건축시공 기출문제' WHERE type = '주관식'")
        conn.commit()
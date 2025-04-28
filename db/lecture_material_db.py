import sqlite3
import os
from datetime import datetime

def get_db_path():
    return os.path.join(os.getcwd(), "lecture_materials.db")

def init_lecture_materials_db():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS lecture_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL,
            filename TEXT NOT NULL,
            upload_time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_lecture_material(week, filename):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    upload_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute('''
        INSERT INTO lecture_materials (week, filename, upload_time)
        VALUES (?, ?, ?)
    ''', (week, filename, upload_time))
    conn.commit()
    conn.close()

def get_lecture_materials_by_week(week):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('SELECT id, filename, upload_time FROM lecture_materials WHERE week = ?', (week,))
    results = c.fetchall()
    conn.close()
    return results

def delete_lecture_material(id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('DELETE FROM lecture_materials WHERE id = ?', (id,))
    conn.commit()
    conn.close()
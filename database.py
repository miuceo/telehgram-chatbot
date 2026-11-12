import sqlite3
import datetime
from typing import List, Dict
from config import DB_PATH, MAX_HISTORY_MESSAGES

def init_db():
    """Ma'lumotlar bazasini yaratadi va jadvallarni sozlaydi."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON chat_history (user_id)
        """)
        
        # Foydalanuvchining oxirgi audio/fayl transkripsiyasi yoki maxsus holati
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                user_id INTEGER PRIMARY KEY,
                last_transcription TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_message(user_id: int, role: str, content: str):
    """Suhbatdagi yangi xabarni xotiraga yozadi."""
    if not content or not content.strip():
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content.strip())
        )
        conn.commit()

def get_chat_history(user_id: int, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, str]]:
    """Foydalanuvchining oxirgi suhbat tarixini oladi."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content FROM (
                SELECT role, content, id FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
        """, (user_id, limit))
        rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]

def clear_chat_history(user_id: int):
    """Foydalanuvchining suhbat tarixini va kontekstini tozalaydi."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_context WHERE user_id = ?", (user_id,))
        conn.commit()

def save_last_transcription(user_id: int, transcription: str):
    """Foydalanuvchining oxirgi audio transkripsiyasini saqlaydi."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_context (user_id, last_transcription, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                last_transcription = excluded.last_transcription,
                last_updated = CURRENT_TIMESTAMP
        """, (user_id, transcription))
        conn.commit()

def get_last_transcription(user_id: int) -> str:
    """Foydalanuvchining oxirgi audio transkripsiyasini qaytaradi."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_transcription FROM user_context WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else ""

# Baza jadvalini ishga tushirish
init_db()

"""
review_history.py
------------------
سجل المراجعة البشرية (Human Review History). يخزن كل تعديل يديره
المستخدم على ترجمة الـ AI فقاعدة بيانات SQLite بسيطة (ملف واحد،
بلا سيرفر، بلا إعداد إضافي).

الجدول corrections يخزن:
    - chunk_num: رقم القطعة
    - source_text: النص الفرنسي الأصلي
    - ai_translation: الترجمة اللي قدمها الـ AI
    - human_translation: الترجمة بعد تصحيح الإنسان
    - was_edited: 1 إذا الإنسان بدل شي حاجة فعلاً، 0 إذا أكد الترجمة كيفما هي
    - new_glossary_term_fr / new_glossary_term_en: إذا التصحيح جاب مصطلح
      جديد تزاد للمعجم (اختياري)
    - created_at: تاريخ ووقت الحفظ
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "./data/corrections_history.db"


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """ينشئ الجدول إذا ما كانش موجود. آمن نعاودو نشغلها بزاف."""
    conn = _get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_num INTEGER,
            source_text TEXT NOT NULL,
            ai_translation TEXT NOT NULL,
            human_translation TEXT NOT NULL,
            was_edited INTEGER NOT NULL,
            new_glossary_term_fr TEXT,
            new_glossary_term_en TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_correction(
    chunk_num: int,
    source_text: str,
    ai_translation: str,
    human_translation: str,
    new_glossary_term_fr: str = "",
    new_glossary_term_en: str = "",
) -> int:
    """
    يحفظ تصحيح واحد فالسجل. يرجع الـ id ديال السطر المحفوظ.
    was_edited يتحسب تلقائياً بمقارنة الترجمتين.
    """
    init_db()
    was_edited = 1 if human_translation.strip() != ai_translation.strip() else 0

    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO corrections (
            chunk_num, source_text, ai_translation, human_translation,
            was_edited, new_glossary_term_fr, new_glossary_term_en, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chunk_num,
            source_text,
            ai_translation,
            human_translation,
            was_edited,
            new_glossary_term_fr.strip() or None,
            new_glossary_term_en.strip() or None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_all_corrections(edited_only: bool = False):
    """يرجع كل التصحيحات كقائمة dicts، الأحدث أولاً."""
    init_db()
    conn = _get_connection()
    query = "SELECT * FROM corrections"
    if edited_only:
        query += " WHERE was_edited = 1"
    query += " ORDER BY id DESC"

    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats() -> dict:
    """إحصائيات سريعة للسجل: العدد الكلي، وعدد التصحيحات الفعلية."""
    init_db()
    conn = _get_connection()
    total = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
    edited = conn.execute(
        "SELECT COUNT(*) FROM corrections WHERE was_edited = 1"
    ).fetchone()[0]
    new_terms = conn.execute(
        "SELECT COUNT(*) FROM corrections WHERE new_glossary_term_fr IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "edited": edited, "new_terms": new_terms}

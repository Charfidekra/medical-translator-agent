"""
config.py
---------
إعدادات المشروع: مفاتيح الـ API، اختيار النموذج، وثوابت عامة.
حطي مفاتيحك في ملف .env (سطر ANTHROPIC_API_KEY=xxxx) وما تشاركيهش أبداً.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# مفتاح الـ API (Claude). يمكن تبدليه بـ OpenAI أو Gemini إذا حبيتي.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# النموذج المستعمل. Sonnet كافي جداً لهذا العمل ومتوازن بين الجودة والتكلفة.
MODEL_NAME = "claude-sonnet-4-6"

# طول القطعة (Chunk) عند تقسيم الكتاب - بالكلمات تقريباً
CHUNK_SIZE_WORDS = 350

# مسار قاعدة بيانات المصطلحات (RAG) - Chroma persistent store
TERMINOLOGY_DB_PATH = "./data/terminology_db"

# مسار ملف المعجم الطبي الأولي (فرنسي-إنجليزي) بصيغة CSV: french_term,english_term,domain
TERMINOLOGY_SEED_FILE = "./data/medical_terms_seed.csv"

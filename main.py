"""
main.py
-------
نقطة الدخول للمشروع. تاخذ نص فرنسي (أو ملف)، تقسمه لقطع، وتشغل عليه
الـ Crew (الوكلاء الثلاثة) قطعة بقطعة، ثم تجمع النتيجة في ملف نهائي.
"""

import os
import sys
import argparse

# 1️⃣ ضبط متغیرات البيئة لإيقاف التتبع والذاكرة المؤقتة لمنع التعارض
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st
from crewai import Crew, Process, LLM
from config import CHUNK_SIZE_WORDS
from tasks import build_pipeline_tasks
from terminology_db import query_relevant_terms


def chunk_text(text: str, chunk_size_words: int = CHUNK_SIZE_WORDS):
    """
    تقسيم بسيط للنص حسب عدد الكلمات.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size_words):
        chunks.append(" ".join(words[i : i + chunk_size_words]))
    return chunks


def translate_chunk(chunk: str, retrieved_terms: str = "") -> str:
    """
    ترجمة قطعة واحدة باستخدام نموذج Groq عبر واجهة OpenAI المستقرة.
    """
    # جلب المفتاح بأمان من Streamlit Secrets أو البيئة
    groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

    # استخدام واجهة OpenAI القياسية للتوجيه إلى سيرفرات Groq
    # هذه الطريقة تتفادي خطأ ImportError الخاص بحزمة groq في CrewAI
    groq_llm = LLM(
        model="openai/llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_key,
        temperature=0.2,
    )

    tasks = build_pipeline_tasks(chunk, retrieved_terms)

    # ربط النموذج بكافة الوكلاء داخل المهام
    for task in tasks:
        task.agent.llm = groq_llm

    crew = Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,  # كل مهمة تلو الأخرى: ترجمة -> تدقيق -> تنقيح
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)


def translate_document(source_text: str) -> str:
    """
    تقسيم النص الكامل إلى قطع وترجمته قطعة بقطعة.
    """
    chunks = chunk_text(source_text)
    print(f"[INFO] تم تقسيم النص إلى {len(chunks)} قطعة/قطع.")

    translated_parts = []
    for idx, chunk in enumerate(chunks, start=1):
        print(f"\n[INFO] جاري ترجمة القطعة {idx}/{len(chunks)}...")

        # جلب المصطلحات من المعجم مع وجود معالجة للاستثناءات
        try:
            retrieved_terms = query_relevant_terms(chunk)
            if not retrieved_terms:
                retrieved_terms = "No specific local database terms found. Use standard medical terminology."
        except Exception as e:
            print(f"[WARN] خطأ أثناء جلب المصطلحات: {e}")
            retrieved_terms = "No specific local database terms found. Use standard medical terminology."

        print(f"[INFO] مصطلحات مسترجعة من المعجم:\n{retrieved_terms}\n")

        translated = translate_chunk(chunk, retrieved_terms)
        translated_parts.append(translated)

    return "\n\n".join(translated_parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medical French->English Translator Agent")
    parser.add_argument("--text", type=str, help="نص فرنسي مباشر للترجمة")
    parser.add_argument("--file", type=str, help="مسار ملف .txt يحتوي النص الفرنسي")
    parser.add_argument("--output", type=str, default="translated_output.txt")
    args = parser.parse_args()

    if args.text:
        source = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            source = f.read()
    else:
        # نص تجريبي بسيط
        source = (
            "L'insuffisance rénale aiguë (IRA) est définie par une diminution "
            "brutale et rapide du débit de filtration glomérulaire, entraînant "
            "une accumulation des déchets azotés dans le sang."
        )
        print("[INFO] تجربة السكريبت على نص افتراضي...")

    final_text = translate_document(source)
    print("\n--- النتيجة النهائية ---")
    print(final_text)

"""
main.py
-------
نقطة الدخول للمشروع.
"""

import os
import sys
import argparse

# 1️⃣ ضبط متغیرات البيئة لمنع التضارب
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st
from crewai import Crew, Process, LLM
from config import CHUNK_SIZE_WORDS
from tasks import build_pipeline_tasks
from terminology_db import query_relevant_terms


def chunk_text(text: str, chunk_size_words: int = CHUNK_SIZE_WORDS):
    """تقسيم بسيط للنص حسب عدد الكلمات."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size_words):
        chunks.append(" ".join(words[i : i + chunk_size_words]))
    return chunks



 def translate_chunk(chunk: str, retrieved_terms: str = "") -> str:
    groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if not groq_key:
        raise ValueError("GROQ_API_KEY is missing from Streamlit Secrets!")

    os.environ["OPENAI_API_KEY"] = str(groq_key).strip()

    # استخدام واجهة OpenAI لتوجيه الطلبات لـ Groq بأمان
    groq_llm = LLM(
        model="openai/llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=str(groq_key).strip(),
        temperature=0.2
    )

    tasks = build_pipeline_tasks(chunk, retrieved_terms)

    # تعيين النموذج لكل وكيل
    for task in tasks:
        task.agent.llm = groq_llm

    crew = Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)



def translate_document(source_text: str) -> str:
    """تقسيم النص الكامل إلى قطع وترجمته."""
    chunks = chunk_text(source_text)
    print(f"[INFO] تم تقسيم النص إلى {len(chunks)} قطعة/قطع.")

    translated_parts = []
    for idx, chunk in enumerate(chunks, start=1):
        print(f"\n[INFO] جاري ترجمة القطعة {idx}/{len(chunks)}...")

        try:
            retrieved_terms = query_relevant_terms(chunk)
            if not retrieved_terms:
                retrieved_terms = "No specific local database terms found. Use standard medical terminology."
        except Exception as e:
            print(f"[WARN] خطأ أثناء جلب المصطلحات: {e}")
            retrieved_terms = "No specific local database terms found. Use standard medical terminology."

        translated = translate_chunk(chunk, retrieved_terms)
        translated_parts.append(translated)

    return "\n\n".join(translated_parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medical French->English Translator Agent")
    parser.add_argument("--text", type=str, help="نص فرنسي مباشر للترجمة")
    parser.add_argument("--file", type=str, help="مسار ملف .txt يحتوي النص الفرنسي")
    args = parser.parse_args()

    if args.text:
        source = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            source = f.read()
    else:
        source = "L'insuffisance rénale aiguë (IRA) est définie par une diminution brutale du débit de filtration glomérulaire."

    final_text = translate_document(source)
    print(final_text)

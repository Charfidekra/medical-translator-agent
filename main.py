"""
main.py
-------
نقطة الدخول للمشروع.
"""
import os
import sys
import argparse

# 1️⃣ ضبط بيئة العمل لتفادي التضارب
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st
from crewai import Crew, Process, LLM
from config import CHUNK_SIZE_WORDS
from tasks import build_pipeline_tasks
from terminology_db import query_relevant_terms


def chunk_text(text: str, chunk_size_words: int = CHUNK_SIZE_WORDS):
    """تقسيم النص إلى قطع"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size_words):
        chunks.append(" ".join(words[i : i + chunk_size_words]))
    return chunks


def translate_chunk(chunk: str, retrieved_terms: str = "") -> str:
    """ترجمة قطعة واحدة باستعمال CrewAI و Groq"""
    
    # 1️⃣ جلب المفتاح بأمان
    groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    # 2️⃣ إنشاء كائن LLM حقيقي خاص بـ Groq
    groq_llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=groq_key,
        temperature=0.2
    )

    tasks = build_pipeline_tasks(chunk, retrieved_terms)
    
    # 3️⃣ ربط كائن الـ LLM المعرّف بكافة الوكلاء
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
    """ترجمة المستند كاملاً"""
    chunks = chunk_text(source_text)
    translated_parts = []
    
    for idx, chunk in enumerate(chunks, start=1):
        try:
            retrieved_terms = query_relevant_terms(chunk)
        except Exception:
            retrieved_terms = "No specific terminology available."

        translated = translate_chunk(chunk, retrieved_terms)
        translated_parts.append(translated)

    return "\n\n".join(translated_parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medical French->English Translator Agent")
    parser.add_argument("--text", type=str, help="نص فرنسي مباشر للترجمة")
    parser.add_argument("--file", type=str, help="مسار ملف .txt")
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

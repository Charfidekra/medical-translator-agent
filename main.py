import os
import sys
import argparse

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st
from crewai import Crew, Process
from config import CHUNK_SIZE_WORDS
from tasks import build_pipeline_tasks
from terminology_db import query_relevant_terms

# 1️⃣ جلب المفتاح وضبطه في البيئة
GROQ_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
if GROQ_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_KEY


def chunk_text(text: str, chunk_size_words: int = CHUNK_SIZE_WORDS):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size_words):
        chunks.append(" ".join(words[i : i + chunk_size_words]))
    return chunks


def translate_chunk(chunk: str, retrieved_terms: str = "") -> str:
    tasks = build_pipeline_tasks(chunk, retrieved_terms)
    
    # 💡 بدلاً من كائن LLM، نمرر اسم النموذج مباشرة كـ string للـ Agents
    MODEL_NAME = "groq/llama-3.3-70b-versatile"
    for task in tasks:
        task.agent.llm = MODEL_NAME

    crew = Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)


def translate_document(source_text: str) -> str:
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

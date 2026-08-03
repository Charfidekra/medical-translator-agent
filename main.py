"""
main.py
-------
نقطة الدخول للمشروع. تاخذ نص فرنسي (أو ملف)، تقسمه لقطع، وتشغل عليه
الـ Crew (الوكلاء الثلاثة) قطعة بقطعة، ثم تجمع النتيجة في ملف نهائي.

طريقة الاستعمال:
    python main.py --text "النص الفرنسي هنا"
    python main.py --file chapter1.txt
"""
import os

# إيقاف تتبع الخدمة والذاكرة لتفادي التعارض مع ChromaDB و Python 3.14
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st
from crewai import Crew, Process, LLM
# باقي الأسطر تاع الكود تاعك عادي جداً...

import argparse
from crewai import Crew, Process, LLM
from config import CHUNK_SIZE_WORDS
from tasks import build_pipeline_tasks
from terminology_db import query_relevant_terms

# -------------------------------------------------------------
# 1️⃣ إعداد مفتاح API والنموذج (Groq - Llama 3.3)
# -------------------------------------------------------------
# يمكنك وضع مفتاح Groq الخاص بكِ هنا مباشرة أو في ملف .env
os.environ["GROQ_API_KEY"] = "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"
# تعريف نموذج الذكاء الاصطناعي المجاني والسريع جداً
groq_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    temperature=0.2
)


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
    tasks = build_pipeline_tasks(chunk, retrieved_terms)
    
    # ربط النموذج (groq_llm) بكافة الوكلاء (Agents) داخل المهام لمنع خطأ Anthropic
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
    chunks = chunk_text(source_text)
    print(f"[INFO] تم تقسيم النص إلى {len(chunks)} قطعة/قطع.")

    translated_parts = []
    for idx, chunk in enumerate(chunks, start=1):
        print(f"\n[INFO] جاري ترجمة القطعة {idx}/{len(chunks)}...")

        # البحث في معجم المصطلحات عن الكلمات المهمة قبل التمرير للـ Crew
        retrieved_terms = query_relevant_terms(chunk)
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
        # نص تجريبي بسيط للاختبار السريع
        source = (
            "L'insuffisance rénale aiguë (IRA) est définie par une diminution "
            "brutale et rapide du débit de filtration glomérulaire, entraînant "
            "une accumulation des déchets azotés dans le sang."
        )
        print("[INFO] ما كاين لا --text ولا --file، نستعملو نص تجريبي.")

    final_text = translate_document(source)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"\n[DONE] النص المترجم النهائي محفوظ في: {args.output}")

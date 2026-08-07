"""
main.py
-------
نقطة الترجمة: تدير استرجاع المصطلحات (RAG) من terminology_db.py
وتحطها فـ prompt قبل ما تبعث النص للنموذج.
"""

import os
from litellm import completion
from terminology_db import query_relevant_terms


def translate_document(text: str) -> str:
    # التاكد من وجود نص حقيقي
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    # 1. استرجاع المصطلحات ذات الصلة من قاعدة بيانات ChromaDB
    try:
        relevant_terms = query_relevant_terms(text)
    except Exception as e:
        relevant_terms = f"(تعذر استرجاع المصطلحات: {e})"

    # 2. بناء الـ system prompt مع حقن المصطلحات كسياق موثوق
    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "\n\nUse the following glossary terms if they appear in the text (these are authoritative, trusted translations — "
        "prefer them over your own judgment when there's a conflict):\n"
        f"{relevant_terms}\n\n"
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases. "
        "Do NOT mention the glossary or explain your choices — just produce the final translated text."
    )

    try:
        response = completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[خطأ في الترجمة: {str(e)}]"

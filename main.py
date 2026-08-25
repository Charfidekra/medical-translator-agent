import os
import streamlit as st
from litellm import completion

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    # التأكد من التعرّف على المفتاح
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    # قائمة النماذج المتاحة للربط التلقائي في حال تعثر أحدها
    models_to_try = [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "groq/mixtral-8x7b-32768"
    ]

    for model_name in models_to_try:
        try:
            response = completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception:
            continue

    return "[خطأ: تعذر الاتصال بنماذج Groq. يرجى التأكد من إضافة GROQ_API_KEY في st.secrets أو ملف .env]"

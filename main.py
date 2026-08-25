import os
import streamlit as st
from litellm import completion

def get_groq_api_key():
    if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
        return st.secrets["GROQ_API_KEY"]
    if os.environ.get("GROQ_API_KEY"):
        return os.environ.get("GROQ_API_KEY")
    if "groq_key_input" in st.session_state and st.session_state["groq_key_input"]:
        return st.session_state["groq_key_input"]
    return None

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    api_key = get_groq_api_key()
    if not api_key:
        return "[⚠️ يرجى إدخال مفتاح Groq API Key في الشريط الجانبي أولاً]"

    # تنظيف المفتاح من أي مسافات زائدة
    api_key = api_key.strip()
    os.environ["GROQ_API_KEY"] = api_key

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    models_to_try = [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-8b-instant"
    ]

    last_error = ""
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
        except Exception as e:
            last_error = str(e)
            continue

    return f"[خطأ من Groq: {last_error}]"

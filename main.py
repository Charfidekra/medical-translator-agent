import os
import streamlit as st
from google import genai

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    # المفتاح ياخذوه فقط من Streamlit Secrets — ماكيبقاش مكتوب فالكود
    api_key = ""
    try:
        api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return "[⚠️ يرجى إضافة GEMINI_API_KEY في Streamlit Secrets]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    models_to_try = ['gemini-3.5-flash', 'gemini-3.5-flash-lite']
    client = genai.Client(api_key=api_key)
    last_error = ""

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"{system_prompt}\n\nText to translate:\n{text}",
            )
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            last_error = err_str
            # إذا كان quota/rate-limit، مافيش فايدة نجربو موديل آخر بنفس المفتاح
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                return f"[⚠️ تجاوزتِ الحد المسموح من الطلبات (rate limit) — انتظري شوية وعاودي المحاولة: {err_str}]"
            continue

    return f"[خطأ في الترجمة: {last_error}]"

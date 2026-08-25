import os
import streamlit as st
from google import genai

# 🔑 ضعي مفتاح Gemini الجديد هنا (يبدأ بـ AIzaSy...)
GEMINI_API_KEY = "AQ.Ab8RN6L8uTxtW5zhV2DVlvXEgtgjIi5w-x01_Mgsqtml1gQptQ"

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    api_key = GEMINI_API_KEY.strip()

    # محاولة جلب المفتاح من Secrets إذا لم يكن مكتوباً أعلاه
    if api_key.startswith("AIzaSy_ضع"):
        if "GEMINI_API_KEY" in st.secrets:
            api_key = str(st.secrets["GEMINI_API_KEY"]).strip()

    if not api_key or api_key.startswith("AIzaSy_ضع"):
        return "[⚠️ يرجى وضع مفتاح Google Gemini في متغير GEMINI_API_KEY داخل main.py]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nText to translate:\n{text}",
        )
        return response.text.strip()
    except Exception as e:
        return f"[خطأ في الترجمة: {str(e)}]"

import os
import streamlit as st
from groq import Groq

def get_groq_api_key():
    # 1. جلب المفتاح من secrets
    if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
        return st.secrets["GROQ_API_KEY"].strip()
    # 2. جلب المفتاح من بيئة النظام
    if os.environ.get("GROQ_API_KEY"):
        return os.environ.get("GROQ_API_KEY").strip()
    # 3. جلب المفتاح من الشريط الجانبي في Streamlit
    if "groq_key_input" in st.session_state and st.session_state["groq_key_input"]:
        return st.session_state["groq_key_input"].strip()
    return None

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    api_key = get_groq_api_key()
    if not api_key:
        return "[⚠️ يرجى إدخال مفتاح Groq API Key الصحيح في الشريط الجانبي أولاً]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    try:
        # الاتصال المباشر بمكتبة Groq الرسمية بدون وسائط litellm
        client = Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        # المحاولة باستخدام النموذج الخفيف السريع في حال التحتّم
        try:
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception as err:
            return f"[خطأ من Groq: {str(err)}]"

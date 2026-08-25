import os
from litellm import completion
import streamlit as st
from litellm import completion

# جلب المفتاح من secrets الخاصة بـ Streamlit أو من بيئة النظام
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

def translate_document(text: str) -> str:
    # التأكد من وجود نص حقيقي
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    try:
        # استخدام نموذج Llama 3.3 الأساسي والمعتمد حالياً على Groq
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
        # في حال حدوث أي ضغط أو خطأ يتم التراجع تلقائياً إلى Llama 3.1 8B السريع
        try:
            response = completion(
                model="groq/llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as fallback_error:
            return f"[خطأ في الترجمة: {str(e)}]"

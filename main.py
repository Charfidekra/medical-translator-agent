import os
from groq import Groq

# 🔑 ضعي مفتاح Groq الجديد هنا مباشرة بين القوسين
GROQ_API_KEY = "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"

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    clean_key = GROQ_API_KEY.strip()

    if not clean_key or clean_key.startswith("gsk_ضع"):
        return "[⚠️ يرجى لصق مفتاح Groq الجديد داخل متغير GROQ_API_KEY في main.py]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it"
    ]

    last_error = ""
    client = Groq(api_key=clean_key)

    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                model=model_name,
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = str(e)
            continue

    return f"[خطأ في المفتاح أو الحساب: {last_error}]"

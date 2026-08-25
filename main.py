import os
from groq import Groq

# 🔑 حطي مفتاحك هنا مباشرة بين القوسين
GROQ_API_KEY = "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"

def translate_document(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    # التأكد من كتابة المفتاح
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("gsk_ضع"):
        return "[⚠️ يرجى وضع مفتاح Groq الخاص بك في متغير GROQ_API_KEY داخل main.py]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases."
    )

    try:
        # الاتصال المباشر فوراً باستخدام المفتاح المكتوب أعلاه
        client = Groq(api_key=GROQ_API_KEY.strip())
        
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
        # البديل السريع المباشر
        try:
            client = Groq(api_key=GROQ_API_KEY.strip())
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
            return f"[خطأ في الاتصال: {str(err)}]"

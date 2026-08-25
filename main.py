import os
from litellm import completion

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
        # استخدام اسم النموذج المعتمد رسمياً لدى Groq عبر LiteLLM
        response = completion(
            model="groq/llama3-70b-8192",  # تم تحديث الاسم هنا
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # في حال حدوث خطأ يتم تجربة نموذج llama3-8b السريع كبديل احتياطي
        try:
            response = completion(
                model="groq/llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as fallback_error:
            return f"[خطأ في الترجمة: {str(e)}]"

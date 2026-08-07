import os
from litellm import completion

def translate_document(text_content: str) -> str:
    """ترجمة طبية وجينية متخصصة ودقيقة باستخدام Groq"""
    
    system_prompt = (
        "You are an expert Professor of Medical Genetics and Senior Population Geneticist. "
        "Translate the provided French medical/genetics text into highly accurate academic English. "
        "STRICT RULES:\n"
        "1. Terminology Standard: Use standard English population genetics terms (e.g., use 'non-random mating' NOT 'coupling', 'no overlapping generations' NOT 'no reproduction', 'small population size', 'allele frequencies').\n"
        "2. Formulas & Equations: Preserve mathematical formulas (e.g., Hardy-Weinberg equilibrium p^2 + 2pq + q^2 = 1, P + H + Q = 1) and fix obvious OCR typos in genetics symbols if present.\n"
        "3. Language Consistency: The entire output MUST be in fluent English. Absolutely NO remaining French sentences allowed.\n"
        "4. Output: Return ONLY the translated English text without any commentary or intro."
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GROQ_API_KEY في Secrets."

    try:
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            temperature=0.1,  # درجة حرارة منخفضة للحفاظ على الدقة الأكاديمية والحد من الارتجال
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"حدث خطأ أثناء الترجمة: {str(e)}"

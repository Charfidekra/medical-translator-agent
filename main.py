import os
from litellm import completion

def translate_document(text_content: str) -> str:
    """ترجمة مباشرة وسريعة باستخدام Groq عبر LiteLLM"""
    
    system_prompt = (
        "You are an expert physician and Senior Medical Translator. Translate the provided French/Arabic medical text "
        "into clear, academic, and accurate English. Preserve all original formatting, structures, and precise medical terminology. "
        "Output ONLY the translated text without any preamble, labels, or repeated headers."
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GROQ_API_KEY في إعدادات البيئة (Secrets)."

    try:
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"حدث خطأ أثناء الترجمة: {str(e)}"

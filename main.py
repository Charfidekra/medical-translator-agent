import os
from litellm import completion

def translate_document(text_content: str) -> str:
    """دالة الترجمة المباشرة باستدعاء Groq عبر litellm بدون مشاكل Caching"""
    
    system_prompt = (
        "You are a Senior Medical Translator. Translate the provided medical text into clear, academic, "
        "and accurate English. Preserve all original formatting, structures, and terminology where applicable. "
        "Output ONLY the translated text without any preamble, labels, or repeated headers."
    )

    try:
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            api_key=os.environ.get("GROQ_API_KEY")
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"حدث خطأ أثناء الترجمة: {str(e)}"

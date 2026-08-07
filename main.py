import os
from litellm import completion

def translate_document(text_content: str) -> str:
    """ترجمة طبية مباشرة بدقة عالية باستخدام Groq عبر LiteLLM"""
    
    system_prompt = (
        "You are an expert physician and Senior Medical Translator. Translate the provided French or Arabic medical text "
        "accurately into clear, academic, and professional English. Preserve all original medical terminology, structures, and layout logic. "
        "IMPORTANT: Output ONLY the translated English text without any intro remarks, labels, or preamble."
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GROQ_API_KEY في Streamlit Secrets."

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

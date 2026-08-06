import os
import time
from google import genai
from google.genai.errors import APIError

def translate_document(text_content: str) -> str:
    """
    ترجمة مستند طبي باستخدام Gemini مع تبديل تلقائي للنماذج
    وإعادة المحاولة لتفادي خطأ 429 (Resource Exhausted)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GEMINI_API_KEY في إعدادات البيئة (Secrets)."

    client = genai.Client(api_key=api_key)
    
    prompt = (
        "You are an expert physician and Senior Medical Translator. Translate the following medical text "
        "accurately into clear, professional, and academic English. Preserve precise medical jargon and structures. "
        "IMPORTANT: Output ONLY the translated text without any intro remarks, labels, or repeated headers.\n\n"
        f"Text to translate:\n{text_content}"
    )

    # قائمة النماذج المرتبة حسب السرعة وخفة الاستهلاك
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-2.0-flash"
    ]

    for model_name in models_to_try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response.text:
                    return response.text.strip()
            except APIError as e:
                # إذا تجاوزنا الكوتا (429)، ننتظر قليلاً أو ننتقل للنموذج التالي
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # انتظار تصاعدي 5s, 10s...
                        continue
                    else:
                        break  # انتقل للنموذج التالي في القائمة
                return f"حدث خطأ أثناء الترجمة: {str(e)}"
            except Exception as e:
                return f"حدث خطأ غير متوقع: {str(e)}"

    return "تنبيه: تم تجاوز الكوتا لجميع النماذج المجانية حالياً. يرجى الانتظار دقيقة واحدة ثم إعادة المحاولة."

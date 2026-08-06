import os
import time
from google import genai
from google.genai.errors import APIError

def translate_document(text_content: str) -> str:
    """ترجمة مباشرة باستخدام Gemini مع حماية من خطأ 429 (Rate Limit)"""
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

    # محاولة الترجمة مع إعادة التكرار في حال حدوث Rate Limit (429)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash-8b", # استخدام النموذج الخفيف لتفادي 429
                contents=prompt,
            )
            return response.text.strip()
            
        except APIError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(10)  # انتظار 10 ثوانٍ قبل المحاولة مجدداً
                    continue
            return f"حدث خطأ أثناء الترجمة (الحد الأقصى للطلبات): {str(e)}"
        except Exception as e:
            return f"حدث خطأ غير متوقع: {str(e)}"
            
    return "تعذر الترجمة بسبب الضغط على الـ API، يرجى المحاولة بعد دقيقة."

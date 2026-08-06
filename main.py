import os
import time
from google import genai
from google.genai.errors import APIError

def translate_document(text_content: str) -> str:
    """
    ترجمة النص الطبي باستخدام مكتبة google-genai الرسمية
    مع تجربة النماذج المستقرة ومعالجة الأخطاء بدقة
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "❌ خطأ: لم يتم العثور على مفتاح GEMINI_API_KEY في Streamlit Secrets."

    # إنشاء العميل
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"❌ خطأ في تهيئة مفتاح API: {str(e)}"
    
    prompt = (
        "You are an expert physician and Senior Medical Translator. Translate the following medical text "
        "accurately into clear, professional, and academic English. Preserve precise medical jargon and structures. "
        "IMPORTANT: Output ONLY the translated text without any intro remarks, labels, or repeated headers.\n\n"
        f"Text to translate:\n{text_content}"
    )

    # النماذج الأكثر استقراراً وقبولاً في الحسابات المجانية
    models_to_try = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    last_error = ""

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()

        except APIError as e:
            err_msg = str(e)
            last_error = f"Model {model_name}: {err_msg}"
            
            # إذا كان النموذج 404 أو غير مدعوم، جرب النموذج التالي فوراً
            if "404" in err_msg or "NOT_FOUND" in err_msg:
                continue 
            
            # إذا كان 429 (Resource Exhausted)، انتظر 4 ثوانٍ وجرب نموذجاً آخر
            elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                time.sleep(4)
                continue
            else:
                continue

        except Exception as e:
            last_error = str(e)
            continue

    return f"❌ تعذر الاتصال بالخدمة. التفاصيل: {last_error}\n\nيرجى التأكد من صحة GEMINI_API_KEY في Streamlit Secrets."

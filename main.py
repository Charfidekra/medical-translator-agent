import os
import time
from google import genai
from google.genai.errors import APIError

def translate_document(text_content: str) -> str:
    """
    ترجمة النص الطبي باستخدام مكتبة google-genai الرسمية
    مع معالجة ذكية لأخطاء 404 و 429 والتنقل بين النماذج
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GEMINI_API_KEY في Streamlit Secrets."

    # إنشاء العميل باستعمال المفتاح
    client = genai.Client(api_key=api_key)
    
    prompt = (
        "You are an expert physician and Senior Medical Translator. Translate the following medical text "
        "accurately into clear, professional, and academic English. Preserve precise medical jargon and structures. "
        "IMPORTANT: Output ONLY the translated text without any intro remarks, labels, or repeated headers.\n\n"
        f"Text to translate:\n{text_content}"
    )

    # أسماء النماذج الرسمية المتاحة مباشرة بدون البادئات المسببة للخطأ
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash-8b"
    ]

    for model_name in models_to_try:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # استدعاء مباشر ومستقر بدون إضافة models/
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip()

            except APIError as e:
                err_msg = str(e)
                # إذا كان النموذج غير مدعوم بالاسم (404)، ننتقل للنموذج التالي فوراً
                if "404" in err_msg or "NOT_FOUND" in err_msg:
                    break 
                
                # إذا تجاوزنا الكوتا (429)، ننتظر قليلاً ثم نعيد المحاولة أو ننتقل للنموذج التالي
                elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    else:
                        break
                else:
                    # أي خطأ آخر لا يتعلق بالـ API Limit أو Model Not Found
                    return f"حدث خطأ أثناء الترجمة: {err_msg}"
            except Exception as e:
                return f"حدث خطأ غير متوقع: {str(e)}"

    return "تنبيه: تعذر الاتصال بالنظام حالياً. يرجى التأكد من صحة GEMINI_API_KEY أو إعادة المحاولة بعد دقيقة."

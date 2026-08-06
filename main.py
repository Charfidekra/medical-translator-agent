import os
from google import genai

def translate_document(text_content: str) -> str:
    """ترجمة مباشرة ودقيقة باستخدام مكتبة Gemini الرسمية"""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GEMINI_API_KEY في إعدادات البيئة (Secrets)."

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            "You are an expert physician and Senior Medical Translator. Translate the following medical text "
            "accurately into clear, professional, and academic English. Preserve precise medical jargon and structures. "
            "IMPORTANT: Output ONLY the translated text without any intro remarks, labels, or repeated headers.\n\n"
            f"Text to translate:\n{text_content}"
        )

        # استخدام نموذج gemini-2.0-flash الحديث والمستقر
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        
        return response.text.strip()
        
    except Exception as e:
        return f"حدث خطأ أثناء الترجمة: {str(e)}"

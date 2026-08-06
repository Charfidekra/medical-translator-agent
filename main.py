import os
from google import genai

def translate_document(text_content: str) -> str:
    """ترجمة مباشرة باستخدام Google GenAI SDK"""
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    prompt = (
        "You are a Senior Medical Translator. Translate the following French/Arabic medical text "
        "directly into clear, professional, and academic English. Preserve precise terminology. "
        "Output ONLY the translated text without intro or explanations.\n\n"
        f"Text to translate:\n{text_content}"
    )

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
    )
    
    return response.text

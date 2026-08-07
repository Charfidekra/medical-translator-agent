import os
from litellm import completion

def translate_document(text_content: str) -> str:
    if not text_content or not text_content.strip():
        return "No text provided for translation."

    system_prompt = (
        "You are an elite Clinical Genetics Professor and Expert Medical Translator.\n"
        "Translate the provided text from French/Arabic into highly accurate, fluent academic English.\n\n"
        "STRICT MEDICAL & GENETICS RULES:\n"
        "1. Medical Terminology: Preserve precise clinical, anatomical, and population genetics terms.\n"
        "2. Hardy-Weinberg Equilibrium: Preserve genotype notation (AA, Aa, aa) and phenotypic notation ([A], [a]). Ensure variables p, q, N, D, H, R are formatted cleanly.\n"
        "3. Zero French/Arabic Leakage: Output 100% academic English only.\n"
        "4. Direct Output: Return only the translated text without introductory commentary."
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not configured in Streamlit Secrets."

    try:
        response = completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            temperature=0.1,
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Translation Service Error: {str(e)}"

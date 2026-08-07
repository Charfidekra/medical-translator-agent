import os
from litellm import completion

def translate_document(text_content: str) -> str:
    """
    ترجمة طبية وجينية متقدمة مع ترميم المعادلات وإصلاح أخطاء الـ OCR
    """
    
    system_prompt = (
        "You are an expert Professor of Medical Genetics and Population Genetics Translator.\n"
        "Your task is to translate French medical/genetics lecture text into impecable academic English.\n\n"
        "CRITICAL RULES FOR ACCURACY:\n"
        "1. POPULATION GENETICS TERMINOLOGY:\n"
        "   - 'Accouplements non aléatoires' -> 'Non-random mating'\n"
        "   - 'Absence de chevauchement des générations' -> 'No overlapping generations'\n"
        "   - 'Taille limitée de la population' -> 'Small population size' or 'Finite population size'\n"
        "   - 'Fréquences alléliques / génotypiques' -> 'Allele / Genotype frequencies'\n"
        "   - 'Ecart à l'équilibre' -> 'Deviation from Hardy-Weinberg equilibrium'\n\n"
        "2. FORMULA & SYMBOL RESTORATION (Fix OCR Errors):\n"
        "   - Correct distorted Hardy-Weinberg formulas. Example: If you see 'I + V + Z' or 'X + V + Z', fix them to standard genotype frequency symbols like 'P + H + Q = 1' or 'f(AA) + f(Aa) + f(aa) = 1'.\n"
        "   - Standardize equilibrium equation to: p^2 + 2pq + q^2 = 1.\n"
        "   - Standardize allele frequency equation to: p + q = 1.\n"
        "   - Correct statistical p-value expressions (e.g., 'p < 0.05 indicates statistically significant deviation from Hardy-Weinberg equilibrium').\n\n"
        "3. ZERO FRENCH LEAKAGE:\n"
        "   - Translate EVERY SINGLE sentence. Do NOT leave any French meta-text or disclaimers.\n\n"
        "4. OUTPUT FORMAT:\n"
        "   - Return ONLY the clean, translated academic English text. Do NOT add intro, greetings, or notes."
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "خطأ: لم يتم العثور على مفتاح GROQ_API_KEY في Secrets."

    try:
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            temperature=0.0,  # الصفر يمنع الارتجال ويضمن الالتزام الصارم بالقواعد
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"حدث خطأ أثناء الترجمة: {str(e)}"

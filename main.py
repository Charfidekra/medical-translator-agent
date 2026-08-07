import os
from litellm import completion

def translate_document(text_content: str) -> str:
    system_prompt = (
        "You are an expert Professor of Medical Genetics and Population Genetics Editor.\n"
        "Your task is to translate French medical/genetics text into flawless, highly accurate academic English.\n\n"
        "CRITICAL CORRECTION & TRANSLATION RULES:\n"
        "1. HARDY-WEINBERG CONDITIONS (FIX CONTRADICTIONS):\n"
        "   - The primary condition for equilibrium is ALWAYS 'Random Mating' (Panmictic population). "
        "     If the raw text mistakenly says 'non-random mating' as a required condition for equilibrium, correct it to 'Random Mating'.\n"
        "   - List deviation factors correctly (e.g., Non-random mating, Selection, Mutation, Small population size / Genetic Drift, Migration / Gene Flow).\n\n"
        "2. FORMULA & SYMBOL SANITIZATION (Fix Corrupted OCR Symbols):\n"
        "   - Genotype counts: Standardize observed counts to D (Dominant/AA), H (Heterozygote/Aa), R (Recessive/aa), and N (Total = D + H + R). Fix distorted expressions like 'D + V + Z' to 'N = D + H + R'.\n"
        "   - Allele frequencies: p = f(A) = (2D + H) / 2N, q = f(a) = (2R + H) / 2N. Fix missing/corrupted variables like '2F/2N'.\n"
        "   - Genotype frequencies under HWE: f(AA) = p^2, f(Aa) = 2pq, f(aa) = q^2, where p^2 + 2pq + q^2 = 1.\n"
        "   - Phenotypes vs Genotypes: Preserve clear distinction between phenotype notation [A], [a], [Aa] and genotype notation AA, Aa, aa.\n"
        "   - Statistical significance: Clarify that 'p-value < 0.05 in Chi-square test indicates a statistically significant deviation from Hardy-Weinberg equilibrium'.\n\n"
        "3. ZERO FRENCH LEAKAGE:\n"
        "   - Translate every single phrase. Absolutely NO remaining French sentences.\n\n"
        "4. OUTPUT FORMAT:\n"
        "   - Return ONLY the corrected, clean academic English translation without any conversational intro."
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not found in Secrets."

    try:
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            temperature=0.0,
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error during translation: {str(e)}"

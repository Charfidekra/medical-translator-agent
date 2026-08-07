import time
from litellm import completion
from terminology_db import query_relevant_terms

def translate_document(text: str, max_retries: int = 4) -> str:
    if not text or len(text.strip()) < 3:
        return "[لا يوجد نص قابل للترجمة في هذه الصفحة]"

    try:
        query_snippet = text[:400]
        relevant_terms = query_relevant_terms(query_snippet)
    except Exception as e:
        relevant_terms = f"(تعذر استرجاع المصطلحات: {e})"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology, mathematical formulas, and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "\n\nUse the following glossary terms if they appear in the text (these are authoritative, trusted translations — "
        "prefer them over your own judgment when there's a conflict):\n"
        f"{relevant_terms}\n\n"
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings or intro phrases. "
        "Do NOT mention the glossary or explain your choices — just produce the final translated text."
    )

    delay = 3
    for attempt in range(max_retries):
        try:
            response = completion(
                model="groq/llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "rate limit" in err_str or "429" in err_str or "too many requests" in err_str
            if is_rate_limit and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  # exponential backoff: 3s, 6s, 12s, 24s
                continue
            return f"[خطأ في الترجمة: {str(e)}]"

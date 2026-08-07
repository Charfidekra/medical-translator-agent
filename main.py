import os
from litellm import completion

def translate_document(text: str) -> str:
    # التاكد من وجود نص حقيقي قبل إرساله للنموذج
    if not text or len(text.strip()) < 3:
        return "[This page contains diagrams, images, or unreadable graphical content]"

    system_prompt = (
        "You are an expert medical translator and population geneticist. "
        "Translate the following medical and genetics text directly into formal academic English. "
        "Preserve precise clinical terminology and Hardy-Weinberg equilibrium notation (p, q, p^2, 2pq, q^2). "
        "IMPORTANT: Output ONLY the direct English translation. Do NOT output system warnings, disclaimers, or intro phrases."
    )

    try:
        response = completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Translation Error: {str(e)}]"

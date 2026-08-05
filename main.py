import os
import time
from crewai import Agent, Crew, Process, Task, LLM

# ============================================================
# إعداد نماذج Groq للترجمة الطبية
# - النموذج الأساسي llama-3.3-70b-versatile: أدق، لكن حده اليومي
#   المجاني منخفض (100K توكن/يوم) وسهل يتفنى مع ملفات كبيرة.
# - النموذج الاحتياطي llama-3.1-8b-instant: حده اليومي أعلى بكثير،
#   نستعملوه تلقائيًا فقط إذا ضرب النموذج الأساسي حد الـ rate limit،
#   باش التطبيق ما يوقفش كليًا في نص الترجمة.
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY غير موجود في متغيرات البيئة. "
        "أضفه في إعدادات Streamlit Cloud تحت Settings > Secrets."
    )

BASE_URL = "https://api.groq.com/openai/v1"

primary_llm = LLM(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    base_url=BASE_URL,
    temperature=0.1,
    max_retries=1,  # ما نكرروش نفس الطلب بزاف باش ما نضيعوش توكنز على الفارغ
)

fallback_llm = LLM(
    model="llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    base_url=BASE_URL,
    temperature=0.1,
    max_retries=1,
)


def _make_agent(llm) -> Agent:
    return Agent(
        role="Senior Medical Translator",
        goal=(
            "Translate medical documents with perfect fidelity from French/Arabic to English, "
            "preserving exact meaning, numbers, and medical terminology without adding, omitting, "
            "or inventing any information."
        ),
        backstory=(
            "You are an expert medical translator and physician. You specialize in translating "
            "complex medical concepts, anatomical terms, and clinical notes into precise English. "
            "You never paraphrase away meaning, never guess at illegible or ambiguous parts, and "
            "never add information that is not present in the source text. If a fragment is unclear "
            "or seems corrupted (e.g. from OCR/PDF extraction), you translate it as literally as "
            "possible rather than inventing a plausible-sounding replacement."
        ),
        verbose=False,
        memory=False,
        llm=llm,
    )


primary_agent = _make_agent(primary_llm)
fallback_agent = _make_agent(fallback_llm)

# ============================================================
# تقسيم النص الطويل إلى مقاطع صغيرة
# ============================================================
MAX_CHARS_PER_CHUNK = 3000


def _split_into_chunks(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i + max_chars])
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [text]


def _build_task(chunk: str, agent: Agent) -> Task:
    return Task(
        description=(
            "Translate the following medical text fragment into clear, academic, accurate "
            "English.\n\n"
            "STRICT RULES:\n"
            "- Translate ONLY what is written. Do not add explanations, interpretations, or "
            "information not present in the source.\n"
            "- Preserve all numbers, units, dosages, dates, and measurements EXACTLY as given.\n"
            "- Preserve original formatting (line breaks, tables, lists) as closely as possible.\n"
            "- If a word or fragment is ambiguous, garbled, or looks like an OCR artifact, "
            "translate it as literally as possible. Do NOT guess or invent a 'plausible' medical "
            "term to replace it.\n"
            "- Output ONLY the translation, with no preamble, notes, or commentary.\n\n"
            f"Text fragment:\n{chunk}"
        ),
        expected_output="Only the English translation of the fragment, nothing else.",
        agent=agent,
    )


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate_limit" in msg or "429" in msg or "rate limit" in msg


def _translate_chunk(chunk: str) -> tuple[str, bool]:
    """يرجع (النص المترجم, هل استعملنا النموذج الاحتياطي)"""

    # محاولة بالنموذج الأساسي (70B، أدق)
    try:
        crew = Crew(
            agents=[primary_agent],
            tasks=[_build_task(chunk, primary_agent)],
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()
        return str(result).strip(), False
    except Exception as e:
        if not _is_rate_limit_error(e):
            raise
        # النموذج الأساسي ضرب حد الـ rate limit -> نبدلو للاحتياطي
        time.sleep(2)

    # النموذج الاحتياطي (8B، حد يومي أعلى)
    crew = Crew(
        agents=[fallback_agent],
        tasks=[_build_task(chunk, fallback_agent)],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result).strip(), True


def translate_document(text_content: str) -> str:
    """دالة الترجمة التي يستدعيها app.py"""

    if not text_content or not text_content.strip():
        return ""

    chunks = _split_into_chunks(text_content)
    translated_parts = []
    used_fallback_count = 0

    for i, chunk in enumerate(chunks):
        try:
            translated, used_fallback = _translate_chunk(chunk)
            translated_parts.append(translated)
            if used_fallback:
                used_fallback_count += 1
        except Exception as e:
            # نرجعو الأجزاء اللي نجحت + رسالة واضحة، بدل ما نخسرو كلش
            partial = "\n\n".join(translated_parts)
            raise RuntimeError(
                f"توقفت الترجمة عند المقطع {i + 1} من {len(chunks)} "
                f"(تُرجم {i} مقطع بنجاح قبل التوقف).\n"
                f"السبب: {e}\n\n"
                f"--- الترجمة الجزئية المتوفرة ---\n{partial}"
            ) from e

    result = "\n\n".join(translated_parts)

    if used_fallback_count:
        result += (
            f"\n\n[ملاحظة: {used_fallback_count} مقطع/مقاطع من {len(chunks)} "
            "تُرجمت بنموذج احتياطي أخف (llama-3.1-8b-instant) بسبب "
            "بلوغ الحد اليومي للنموذج الأساسي — تحقق من دقتها بعناية إضافية.]"
        )

    return result

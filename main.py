import os
from crewai import Agent, Crew, Process, Task, LLM

# ============================================================
# إعداد نموذج Groq الخفيف والسريع لتفادي حدود التوكنز (Rate Limit)
# ملاحظة مهمة: خطأ ImportError الذي ظهر لك سببه غالبًا تعارض
# في نسخ المكتبات (crewai / litellm / openai) وليس في الكود نفسه.
# لذلك تأكد من تحديث requirements.txt كما هو موضح أسفل هذا الملف.
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY غير موجود في متغيرات البيئة. "
        "أضفه في إعدادات Streamlit Cloud تحت Settings > Secrets."
    )

llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    temperature=0.3,
    max_retries=3,
)

# 1. تعريف العميل الطبي المترجم
medical_translator = Agent(
    role="Senior Medical Translator",
    goal=(
        "Translate medical documents accurately from French/Arabic to English "
        "while maintaining precise medical terminology."
    ),
    backstory=(
        "You are an expert medical translator and physician. You specialize in translating "
        "complex medical concepts, anatomical terms, and clinical notes into precise English, "
        "ensuring all medical jargon and tables are reflected accurately."
    ),
    verbose=False,
    memory=False,
    llm=llm,
)


def translate_document(text_content: str) -> str:
    """دالة الترجمة التي يستدعيها app.py"""

    if not text_content or not text_content.strip():
        return ""

    translation_task = Task(
        description=(
            "Translate the following medical text into clear, academic, and accurate English. "
            "Preserve all original formatting, structures, and terminology where applicable.\n\n"
            f"Text to translate:\n{text_content}"
        ),
        expected_output="A complete and accurate English translation of the provided medical text.",
        agent=medical_translator,
    )

    crew = Crew(
        agents=[medical_translator],
        tasks=[translation_task],
        process=Process.sequential,
        manager_llm=llm,  # يضمن استخدام Groq حتى في أي عمليات داخلية
        verbose=False,
    )

    try:
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        # رسالة واضحة بدل انهيار التطبيق بالكامل
        raise RuntimeError(f"فشلت عملية الترجمة: {e}") from e

import os
from crewai import Agent, Crew, Process, Task, LLM

# 1. إعداد الـ LLM الخاص بـ Groq بدون إضافة cache=False كقيمة بولينية
llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY")
)

# 2. تعريف العميل الطبي المترجم مع إلغاء الكاش الخاص بالعميل
medical_translator = Agent(
    role="Senior Medical Translator",
    goal="Translate French medical content into clean, standard English without repeating headers.",
    backstory=(
        "You are an expert physician and medical translator. You provide direct, accurate English translations "
        "of medical lecture notes, formulas, and terminology. Do not output conversational preamble or repeated headers."
    ),
    verbose=False,
    memory=False,
    cache=False,  # تعطيل كاش الـ Agent
    llm=llm
)

def translate_document(text_content: str) -> str:
    """دالة الترجمة المباشرة التي يستدعيها app.py"""
    
    translation_task = Task(
        description=(
            f"Translate the following medical text directly into accurate, professional English.\n"
            f"IMPORTANT: Output ONLY the translated text.\n\n"
            f"Text to translate:\n{text_content}"
        ),
        expected_output="Direct English translation of the medical text only.",
        agent=medical_translator
    )

    crew = Crew(
        agents=[medical_translator],
        tasks=[translation_task],
        process=Process.sequential,
        memory=False,
        cache=False  # تعطيل كاش الـ Crew
    )

    result = crew.kickoff()
    return str(result)

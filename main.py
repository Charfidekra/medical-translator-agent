import os
from crewai import Agent, Crew, Process, Task, LLM

# 1. إعداد نموذج Gemini المعتمد والمستقر
llm = LLM(
    model="gemini/gemini-1.5-flash",
    api_key=os.environ.get("GEMINI_API_KEY")
)

# 2. تعريف العميل الطبي المترجم
medical_translator = Agent(
    role="Senior Medical Translator",
    goal="Translate French and Arabic medical documents accurately into clean, academic English while preserving precise medical terminology.",
    backstory=(
        "You are an expert physician and senior medical translator. You specialize in translating "
        "complex medical concepts, anatomical terms, and clinical notes into precise, academic English, "
        "ensuring all medical jargon and structures are reflected accurately without preamble or filler words."
    ),
    verbose=False,
    memory=False,
    llm=llm
)

def translate_document(text_content: str) -> str:
    """دالة الترجمة المباشرة التي يستدعيها app.py"""
    
    translation_task = Task(
        description=(
            f"Translate the following medical text directly into clear, academic, and accurate English.\n"
            f"IMPORTANT: Provide ONLY the accurate translated English text. Do not add intro remarks, greetings, or repeated labels.\n\n"
            f"Text to translate:\n{text_content}"
        ),
        expected_output="A direct, accurate English translation of the provided medical text.",
        agent=medical_translator
    )

    crew = Crew(
        agents=[medical_translator],
        tasks=[translation_task],
        process=Process.sequential,
        memory=False
    )

    result = crew.kickoff()
    return str(result)

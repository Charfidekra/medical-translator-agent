import os
from crewai import Agent, Crew, Process, Task, LLM

# إعداد نموذج Groq الخفيف المتاح لتفادي تجاوز حدود التوكنز
llm_instance = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY")
)

medical_translator = Agent(
    role="Senior Medical Translator",
    goal="Translate medical documents accurately from French/Arabic to English while maintaining precise medical terminology.",
    backstory=(
        "You are an expert medical translator and physician. You specialize in translating "
        "complex medical concepts, anatomical terms, and clinical notes into precise English, "
        "ensuring all medical jargon and tables are reflected accurately."
    ),
    verbose=False,
    memory=False,
    llm=llm_instance
)

def translate_document(text_content: str) -> str:
    """دالة الترجمة التي يستدعيها app.py"""
    
    translation_task = Task(
        description=(
            f"Translate the following medical text into clear, academic, and accurate English. "
            f"Preserve all original formatting, structures, and terminology where applicable.\n\n"
            f"Text to translate:\n{text_content}"
        ),
        expected_output="A complete and accurate English translation of the provided medical text.",
        agent=medical_translator
    )

    crew = Crew(
        agents=[medical_translator],
        tasks=[translation_task],
        process=Process.sequential
    )

    result = crew.kickoff()
    return str(result)

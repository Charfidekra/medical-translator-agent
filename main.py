import os
from crewai import Agent, Crew, Process, Task, LLM

llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY")
)

medical_translator = Agent(
    role="Senior Medical Translator",
    goal="Translate French medical content into clean, standard English without repeating headers or intro text.",
    backstory=(
        "You are an expert physician and medical translator. You provide direct, accurate English translations "
        "of medical lecture notes, formulas, and terminology. Do not output conversational preamble, greetings, "
        "or repeated 'Translation:' prefixes."
    ),
    verbose=False,
    memory=False,
    llm=llm
)

def translate_document(text_content: str) -> str:
    """دالة الترجمة المباشرة"""
    
    translation_task = Task(
        description=(
            f"Translate the following medical text directly into accurate, professional English.\n"
            f"IMPORTANT: Output ONLY the translated text. Do not add labels like 'Translation:' or repeated headings.\n\n"
            f"Text to translate:\n{text_content}"
        ),
        expected_output="Direct English translation of the medical text only.",
        agent=medical_translator
    )

    crew = Crew(
        agents=[medical_translator],
        tasks=[translation_task],
        process=Process.sequential
    )

    result = crew.kickoff()
    return str(result)

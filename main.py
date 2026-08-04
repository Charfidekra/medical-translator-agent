import os
import streamlit as st
from crewai import Crew, Process

def translate_chunk(chunk: str, retrieved_terms: str = "") -> str:
    tasks = build_pipeline_tasks(chunk, retrieved_terms)
    
    # 1️⃣ التأكد من ضبط مفاتيح Groq في البيئة العامة لـ LiteLLM
    groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    # 2️⃣ تعيين اسم النموذج كـ string مباشر للوكلاء دون استخدام كائن LLM() المنفصل
    for task in tasks:
        task.agent.llm = "groq/llama-3.3-70b-versatile"

    crew = Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)

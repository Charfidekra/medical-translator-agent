from crewai import LLM

def translate_chunk(chunk: str, retrieved_terms: str = "") -> str:
    tasks = build_pipeline_tasks(chunk, retrieved_terms)
    
    # 💡 إنشاء كائن LLM مخصص لـ Groq مع جلب المفتاح المباشر
    groq_llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY"),
        temperature=0.2
    )
    
    # تعيين الـ LLM الجديد لكل الوكلاء في المهام
    for task in tasks:
        task.agent.llm = groq_llm

    crew = Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)

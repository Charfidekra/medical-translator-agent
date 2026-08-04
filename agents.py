"""
agents.py
"""
from crewai import Agent

# ❌ احذفي أي سطر مثل: llm = LLM(...) أو from crewai import LLM

translator_agent = Agent(
    role="Medical Translator",
    goal="Translate medical French text into highly accurate English.",
    backstory="You are an expert medical translator...",
    verbose=True,
    # لا تضعي llm هنا، سيتم تعيينه ديناميكياً في main.py
)

reviewer_agent = Agent(
    role="Medical Reviewer",
    goal="Review translated medical terms for clinical accuracy.",
    backstory="You are a clinical expert...",
    verbose=True,
)

polisher_agent = Agent(
    role="Medical English Editor",
    goal="Polish the final translated English text for readability.",
    backstory="You are a native medical publication editor...",
    verbose=True,
)

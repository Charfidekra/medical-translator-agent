"""
agents.py
---------
تعريف الوكلاء الثلاثة (Translator, Terminology Checker, Clinical Proofreader)
باستعمال CrewAI. كل وكيل عنده دور، هدف، وخلفية (backstory) تساعد النموذج
يبقى "متقمص" الشخصية الصحيحة طول المهمة.
"""

from crewai import Agent, LLM
from config import ANTHROPIC_API_KEY, MODEL_NAME
from prompts import (
    TRANSLATOR_SYSTEM_PROMPT,
    TERMINOLOGY_CHECKER_SYSTEM_PROMPT,
    CLINICAL_PROOFREADER_SYSTEM_PROMPT,
)

# إعداد الـ LLM المشترك بين كل الوكلاء (يمكن نبدلو نموذج مختلف لكل وكيل لاحقاً)
llm = LLM(
    model=f"anthropic/{MODEL_NAME}",
    api_key=ANTHROPIC_API_KEY,
    temperature=0.2,  # قليلة باش تكون الترجمة ثابتة ومو مبدعة بزاف
)


def build_translator_agent() -> Agent:
    return Agent(
        role="Medical Translator (French to English)",
        goal=(
            "Produce an accurate, terminology-correct English translation of "
            "French medical text without losing any clinical meaning."
        ),
        backstory=TRANSLATOR_SYSTEM_PROMPT,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def build_terminology_checker_agent() -> Agent:
    return Agent(
        role="Medical Terminology QC Specialist",
        goal=(
            "Verify and correct every medical term in the translation against "
            "standard English medical terminology (MeSH/UMLS)."
        ),
        backstory=TERMINOLOGY_CHECKER_SYSTEM_PROMPT,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def build_proofreader_agent() -> Agent:
    return Agent(
        role="Clinical Proofreader",
        goal=(
            "Polish the final English text so it reads like a professional "
            "medical textbook, without changing any clinical fact."
        ),
        backstory=CLINICAL_PROOFREADER_SYSTEM_PROMPT,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

"""
tasks.py
--------
تعريف المهام الخاصة بكل وكيل.
"""
from crewai import Task
from agents import translator_agent, reviewer_agent, polisher_agent


def build_pipeline_tasks(chunk: str, retrieved_terms: str = "") -> list[Task]:
    """
    بناء قائمة المهام مع تزويد السياق والمصطلحات الطبية.
    """
    task_translate = Task(
        description=(
            f"Translate the following French medical text to English:\n\n{chunk}\n\n"
            f"Use these retrieved terms if relevant:\n{retrieved_terms}"
        ),
        expected_output="An accurate English translation of the medical text.",
        agent=translator_agent,
    )

    task_review = Task(
        description=(
            "Review the translated text for clinical accuracy and terminology alignment. "
            "Correct any medical inconsistencies."
        ),
        expected_output="A clinically verified English medical text.",
        agent=reviewer_agent,
    )

    task_polish = Task(
        description=(
            "Polishing and editing the verified medical translation to improve natural "
            "flow and professional publication quality."
        ),
        expected_output="A polished, publication-ready English medical translation.",
        agent=polisher_agent,
    )

    return [task_translate, task_review, task_polish]

"""
tasks.py
--------
تعريف المهام (Tasks) التي تربط الوكلاء ببعضهم: كل مهمة تاخذ مخرجات
المهمة اللي قبلها (context) وتنتج مخرجات جديدة، لحد ما نوصلو للنص النهائي.
"""

from crewai import Task
from agents import (
    build_translator_agent,
    build_terminology_checker_agent,
    build_proofreader_agent,
)


def build_pipeline_tasks(source_text: str, retrieved_terms: str = ""):
    translator = build_translator_agent()
    checker = build_terminology_checker_agent()
    proofreader = build_proofreader_agent()

    translate_task = Task(
        description=(
            "Translate the following French medical text into English.\n\n"
            f"SOURCE TEXT:\n{source_text}\n\n"
            f"RELEVANT GLOSSARY ENTRIES (may be empty):\n{retrieved_terms}"
        ),
        expected_output=(
            "A complete English translation of the source text, preserving "
            "formatting, with [UNCERTAIN: ...] flags where relevant."
        ),
        agent=translator,
    )

    check_terminology_task = Task(
        description=(
            "Review the translation produced by the previous task against the "
            "original French source text (repeated below for reference), and "
            "correct any terminology issues.\n\n"
            f"ORIGINAL FRENCH SOURCE:\n{source_text}"
        ),
        expected_output=(
            "The corrected English text, followed by a '### Corrections' "
            "section listing every change made."
        ),
        agent=checker,
        context=[translate_task],
    )

    proofread_task = Task(
        description=(
            "Take the terminology-corrected English text from the previous task "
            "and polish it into clean, professional, publication-ready medical "
            "English. Do not change any clinical fact."
        ),
        expected_output="The final, polished English text ready for use.",
        agent=proofreader,
        context=[check_terminology_task],
    )

    return [translate_task, check_terminology_task, proofread_task]

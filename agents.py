"""
agents.py
--------
تعريف الوكلاء الأربعة لعملية الترجمة والتدقيق الطبي.
"""

from crewai import Agent

# 1️⃣ وكيل الترجمة الطبية
translator_agent = Agent(
    role="Medical Translator",
    goal="Translate medical French text into highly accurate English.",
    backstory=(
        "You are an expert medical translator proficient in French and English. "
        "You ensure accurate terminology mapping while preserving clinical intent."
    ),
    verbose=True,
)

# 2️⃣ وكيل التقييم والتدقيق اللغوي
reviewer_agent = Agent(
    role="Medical Reviewer",
    goal="Review translated medical terms for clinical accuracy.",
    backstory=(
        "You are a clinical expert who meticulously reviews medical translations "
        "to ensure anatomical and pharmacological terms are 100% precise."
    ),
    verbose=True,
)

# 3️⃣ وكيل التنقيح والصياغة النهائية
polisher_agent = Agent(
    role="Medical English Editor",
    goal="Polish the final translated English text for native readability.",
    backstory=(
        "You are a native English medical journal editor. You refine sentence structure "
        "and flow while maintaining strict clinical precision."
    ),
    verbose=True,
)

import re
from config import llm


def suggest_followups_agent(task, research, planning, decision_result):
    """
    Generates 3 to 5 short, specific follow-up questions tailored to the business report.
    Returns a list of clean question strings.
    """
    prompt = f"""
You are the Follow-up Recommendation Agent in an AI Business Decision Engine.

Based on the provided business problem and decision report, generate 3 to 5 short, highly specific follow-up questions that a decision-maker would plausibly ask about this exact report (e.g. about pricing, CAC, competitors, risk mitigation, execution timeline).

Business Problem:
{task}

Research Context:
{research}

Planning Context:
{planning}

Decision & Recommendation:
{decision_result}

RULES:
1. Return 3 to 5 short, actionable, and report-specific questions.
2. Output each question on a new line.
3. Do NOT include introductory text, explanations, or metadata.
"""

    response = llm.invoke(prompt)
    content = response.content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        content = "\n".join(text_parts)

    lines = str(content).strip().split("\n")
    questions = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Clean leading numbers, bullets, spaces
        cleaned = re.sub(r"^[\d\.\-\*\s\)]+", "", line).strip()
        if cleaned and len(cleaned) > 5:
            questions.append(cleaned)

    # Fallback if parsing returned less than 3
    if not questions:
        questions = [
            "What should I do first?",
            "What are the biggest risks?",
            "How can I mitigate potential financial risks?",
            "What is the recommended 30-day action plan?"
        ]

    return questions[:5]

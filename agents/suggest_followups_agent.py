import re
from utils.gemini_client import gemini_client


def suggest_followups_agent(task, research, planning, decision_result):
    """
    Generates 3 to 5 short, specific follow-up questions tailored to the business report.
    Returns a list of clean question strings.
    """
    system_instruction = "You are the Follow-up Recommendation Agent in an AI Business Decision Engine. Return 3 to 5 clean question strings on separate lines."

    prompt = f"""
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

    res = gemini_client.generate(prompt, system_instruction=system_instruction)
    content = res.get("content", "")

    lines = str(content).strip().split("\n")
    questions = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^[\d\.\-\*\s\)]+", "", line).strip()
        if cleaned and len(cleaned) > 5:
            questions.append(cleaned)

    if not questions:
        questions = [
            "Why is the market risk level medium?",
            "How can we lower customer acquisition cost?",
            "What happens if sales volume drops by 20%?",
            "What are our top 3 execution priorities?"
        ]

    return questions[:5]


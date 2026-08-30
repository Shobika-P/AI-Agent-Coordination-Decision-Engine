import re
from utils.gemini_client import gemini_client


def suggest_followups_agent(task: str, research: dict, planning: list, decision_result: dict) -> list:
    """
    Generates 3 to 5 short, specific follow-up questions tailored to the business report.
    Returns a list of clean question strings.
    """
    system_instruction = "You are the Follow-up Recommendation Agent in an AI Business Decision Engine. Return 3 to 5 clean question strings on separate lines."

    prompt = f"""
Based on the provided business problem and decision report, generate 3 to 5 short, highly specific follow-up questions that an executive decision-maker would plausibly ask about this exact report (e.g. regarding pricing strategy, unit margin sensitivity, competitor reaction, CAC thresholds, execution milestones).

Business Problem:
{task}

Decision & Strategic Recommendation:
{str(decision_result)[:400]}

RULES:
1. Return 3 to 5 short, actionable, and report-specific questions.
2. Output each question on a new line.
3. Do NOT include introductory text, numbers, bullets, or metadata.
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
        if cleaned and len(cleaned) > 5 and "?" in cleaned:
            questions.append(cleaned)
        elif cleaned and len(cleaned) > 5:
            questions.append(cleaned + "?")

    if not questions:
        clean_t = task.strip("?.!") if task else "this initiative"
        questions = [
            f"What happens to profitability if customer acquisition costs double for {clean_t}?",
            f"What is the break-even sales volume required in Phase 1?",
            f"How can we mitigate the primary market competition risk?",
            f"What pricing model delivers the highest contribution margin?"
        ]

    return questions[:5]

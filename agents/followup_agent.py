import json
from config import llm
from utils.gemini_client import gemini_client

def followup_agent(
    original_task,
    report,
    question,
    conversation_history=None
):
    print("[LLM] Follow-up Agent call")

    report_text = report
    if isinstance(report, (dict, list)):
        report_text = json.dumps(report, indent=2)

    history_text = ""
    if conversation_history and isinstance(conversation_history, list):
        formatted_turns = []
        for idx, turn in enumerate(conversation_history, 1):
            if isinstance(turn, dict):
                q = turn.get("question", "")
                a = turn.get("answer", "")
                if q and a:
                    formatted_turns.append(f"User Question {idx}: {q}\nAI Answer {idx}: {a}")
        if formatted_turns:
            history_text = "\n\nPrevious Q&A History:\n" + "\n\n".join(formatted_turns)

    system_instruction = """
You are the Follow-up Reasoning Agent in an AI Business Decision Engine.
Answer ONLY the user's question directly, concisely, and practically based on the decision report and context.
Do NOT repeat the entire report. Do NOT invent unverified data.
"""

    prompt = f"""
Original Business Problem:
{original_task}

Decision Report:
{report_text}
{history_text}

User's Follow-up Question:
{question}
"""

    res = gemini_client.generate(prompt, system_instruction=system_instruction)
    return res.get("content", "").strip()
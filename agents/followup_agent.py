import json
from config import llm
from utils.llm_helper import invoke_with_retry


def followup_agent(
    original_task,
    report,
    question,
    conversation_history=None
):
    print("[LLM] Follow-up Agent call")

    # Format report safely if it is a dict
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
                    formatted_turns.append(f"User Question {idx}: {q}\nAI Decision Engine Answer {idx}: {a}")
        if formatted_turns:
            history_text = "\n\nPrevious Discussion Thread:\n" + "\n\n".join(formatted_turns)

    prompt = f"""
You are the Follow-up Reasoning Agent in an AI Business Decision Engine.

Your job is to answer the user's follow-up question about an
existing business decision report and ongoing strategic analysis.

IMPORTANT RULES:

1. Answer ONLY the user's question directly and concisely.
2. Use the original business problem, generated decision report, and previous discussion context.
3. Do NOT generate a new business report.
4. Do NOT generate follow-up questions.
5. Do NOT repeat the entire report.
6. Give a clear, practical and business-focused answer.
7. If the question asks for an evaluation, explain the reasoning.
8. If information is not available in the report, clearly state that.
9. You may make reasonable analytical inferences from the report,
   but do not invent factual data.
10. Keep the answer structured and easy to understand.

Original Business Problem:
{original_task}

Existing Business Decision Report:
{report_text}
{history_text}

User's Follow-up Question:
{question}

Now answer the user's question directly.
"""

    response = invoke_with_retry(llm, prompt)
    content = response.content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts).strip()

    if isinstance(content, str):
        return content.strip()

    return str(content)
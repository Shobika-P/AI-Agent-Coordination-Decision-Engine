import json
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
            history_text = "\n\nPrevious Conversation History:\n" + "\n\n".join(formatted_turns)

    system_instruction = """
You are the Follow-up Reasoning Agent in an Enterprise AI Business Decision Support Engine.
Your task is to provide precise, analytical, context-aware answers to ANY follow-up question asked by the user.

CRITICAL GUIDELINES:
1. DIRECT ANSWER FIRST: Directly and explicitly answer the user's specific question in the very first sentence before providing detailed breakdown or supporting context.
2. DEEP CONTEXT AWARENESS: Fully utilize all provided context:
   - Original business question
   - Complete decision report (Executive Summary, Strategic Drivers, Key Risks, Opportunities, Recommended Decision, Implementation Roadmap, Success Metrics, Conditions/Assumptions, Conclusion, and Quantitative Tool Results)
   - Previous follow-up conversation turns
3. QUANTITATIVE & SENSITIVITY COMPUTATIONS:
   - If the user asks a quantitative or scenario question (e.g. "What happens if we reduce the price to ₹399?", "What if marketing budget increases to ₹25,000?"):
     - Calculate/estimate the exact changed price or parameters.
     - Detail the changed unit margin (Selling Price - Variable Cost).
     - Detail the break-even volume impact (Fixed Costs / Unit Margin).
     - Detail the monthly profitability impact.
     - Detail the risk rating impact (Low, Medium, High).
     - Explicitly state whether the original recommendation changes or remains valid.
4. INR CURRENCY FORMATTING: Use Indian Rupee symbol (₹) and Indian number formatting (e.g., ₹1,50,000, ₹399, ₹25,000) for all monetary figures.
5. NO FULL REPORT RE-DUMP: Answer ONLY the user's question thoroughly and concisely. Do NOT regenerate the entire original report.
6. PRESERVE CONVERSATION HISTORY: Keep answer consistent with past turns in the thread.
"""

    prompt = f"""
Original Business Problem:
{original_task}

Full Decision Report Context:
{report_text}
{history_text}

User's Follow-up Question:
{question}
"""

    res = gemini_client.generate(prompt, system_instruction=system_instruction)
    return res.get("content", "").strip()
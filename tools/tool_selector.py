from utils.gemini_client import gemini_client

def select_tool(task):
    system_instruction = "You are an AI Tool Selection Agent. Reply ONLY with one word: profit, roi, break_even, market_risk, or none."

    prompt = f"""
Available Business Tools:
1. Profit Tool (profit) - Calculates profit
2. ROI Tool (roi) - Calculates return on investment
3. Break Even Tool (break_even) - Calculates break-even units
4. Market Risk Tool (market_risk) - Evaluates market risk for business or product launches

Business Problem:
{task}

Reply ONLY with one of: profit, roi, break_even, market_risk, none
"""

    res = gemini_client.generate(prompt, system_instruction=system_instruction)
    content = (res.get("content") or "").strip().lower()

    for tool in ["market_risk", "break_even", "profit", "roi"]:
        if tool in content:
            return tool

    # Rule-based fallback if LLM response is ambiguous
    task_lower = task.lower()
    if any(k in task_lower for k in ["break even", "break-even", "units to sell", "fixed cost"]):
        return "break_even"
    elif any(k in task_lower for k in ["roi", "return on investment", "return"]):
        return "roi"
    elif any(k in task_lower for k in ["profit", "margin", "revenue"]):
        return "profit"
    else:
        return "market_risk"
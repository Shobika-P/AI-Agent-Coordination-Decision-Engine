from utils.gemini_client import gemini_client

def select_tool(task):
    """
    Selects the appropriate business tool.
    Checks deterministic rule-based intent FIRST to avoid unnecessary Gemini calls.
    Invokes Gemini LLM tool selection ONLY when intent is ambiguous.
    """
    task_lower = (task or "").lower()

    # 1. Deterministic Rule-Based Intent Detection (Fast path, 0 Gemini calls)
    if any(k in task_lower for k in ["break even", "break-even", "break_even", "units to sell", "fixed cost", "unit margin"]):
        print("[ToolSelector] Rule-based match: break_even")
        return "break_even"
    elif any(k in task_lower for k in ["roi", "return on investment", "return on capital", "investment", "return"]):
        print("[ToolSelector] Rule-based match: roi")
        return "roi"
    elif any(k in task_lower for k in ["profit", "revenue", "margin", "net profit"]):
        print("[ToolSelector] Rule-based match: profit")
        return "profit"
    elif any(k in task_lower for k in ["market risk", "launch risk", "competition risk", "product launch", "market launch", "market entry", "risk"]):
        print("[ToolSelector] Rule-based match: market_risk")
        return "market_risk"

    # 2. Fallback to Gemini Tool Selection when ambiguous
    print("[ToolSelector] Ambiguous query intent. Invoking Gemini tool selector...")
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

    for tool in ["break_even", "roi", "profit", "market_risk"]:
        if tool in content:
            return tool

    return "market_risk"

def select_tool(task: str) -> str:
    """
    Selects the appropriate quantitative business tool deterministically.
    Operates with 0 LLM calls to maximize performance and preserve API quota for deep research analysis.
    """
    task_lower = (task or "").lower()

    # 1. Break-Even Analysis
    if any(k in task_lower for k in ["break even", "break-even", "break_even", "units to sell", "fixed cost", "volume threshold", "unit margin"]):
        print("[ToolSelector] Deterministic match: break_even")
        return "break_even"

    # 2. Return on Investment (ROI)
    elif any(k in task_lower for k in ["roi", "return on investment", "return on capital", "capital outlay", "payback"]):
        print("[ToolSelector] Deterministic match: roi")
        return "roi"

    # 3. Profit & Margin Analysis
    elif any(k in task_lower for k in ["profit", "revenue", "margin", "pricing", "price", "tier", "subscription", "cost", "monetiz"]):
        print("[ToolSelector] Deterministic match: profit")
        return "profit"

    # 4. Market Risk & Expansion Assessment
    elif any(k in task_lower for k in ["risk", "market", "launch", "competition", "expand", "expansion", "entry", "startup", "scale", "threat"]):
        print("[ToolSelector] Deterministic match: market_risk")
        return "market_risk"

    # Default to Market Risk Tool for general strategic business initiatives
    print("[ToolSelector] Default strategic match: market_risk")
    return "market_risk"
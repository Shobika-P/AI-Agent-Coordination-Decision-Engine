from config import llm

def select_tool(task):

    prompt = f"""
You are an AI Tool Selection Agent.

Available Business Tools

1. Profit Tool
- Calculates profit.

2. ROI Tool
- Calculates return on investment.

3. Break Even Tool
- Calculates break-even units.

4. Market Risk Tool
- Evaluates market risk for product launches.

Rules

Reply ONLY one of the following.

profit
roi
break_even
market_risk
none

Business Problem

{task}
"""

    response = llm.invoke(prompt)
    

    if isinstance(response.content, str):
        return response.content.strip().lower()

    elif isinstance(response.content, list):
        return response.content[0].get("text", "").strip().lower()

    return "none"
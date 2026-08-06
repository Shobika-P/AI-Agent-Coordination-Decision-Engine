from config import llm
from prompts.decision_prompt import DECISION_PROMPT

def decision_agent(
    task,
    research,
    planning,
    tool_output,
    history
):

    full_prompt = f"""
{DECISION_PROMPT}

Current Business Problem:
{task}

Research Findings:
{research}

Business Plan:
{planning}

Business Tool Analysis

{tool_output}

Use this tool result while making the final business decision.

Do not ignore it.

Explain how the tool influenced your recommendation.

Previous Business Decisions:
{history}
"""

    response = llm.invoke(full_prompt)

    if isinstance(response.content, str):
        return response.content

    elif isinstance(response.content, list):
        return response.content[0].get("text", "")

    return str(response.content)
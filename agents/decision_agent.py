from config import llm
from prompts.decision_prompt import DECISION_PROMPT

def decision_agent(task, research, planning, tool_output):

    full_prompt = f"""
{DECISION_PROMPT}

Business Problem:
{task}

Research Findings:
{research}

Business Plan:
{planning}

Tool Output:
{tool_output}
"""

    response = llm.invoke(full_prompt)

    return response.content
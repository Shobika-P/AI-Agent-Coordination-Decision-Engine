from config import llm
from prompts.planning_prompt import PLANNING_PROMPT



def planning_agent(task, research_result):
    full_prompt = f"""
{PLANNING_PROMPT}

Business Problem:
{task}

Research Findings:
{research_result}
""" 

    response = llm.invoke(full_prompt)

    return response.content
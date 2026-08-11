from prompts.planning_prompt import PLANNING_PROMPT
from utils.gemini_client import gemini_client


def planning_agent(task, research):
    system_instruction = """
You are a Business Planning Agent. Create a clear, multi-phase execution roadmap.
"""

    prompt = f"""
{PLANNING_PROMPT}

Business Problem:
{task}

Research Findings:
{research}

Create a structured 3-phase execution roadmap.
"""

    print("[LLM] Planning Agent call")
    res = gemini_client.generate(prompt, system_instruction=system_instruction)
    return res.get("content", "").strip()
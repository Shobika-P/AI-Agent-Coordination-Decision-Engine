from config import llm
from prompts.planning_prompt import PLANNING_PROMPT
from utils.llm_helper import invoke_with_retry


def planning_agent(task, research):

    full_prompt = f"""
{PLANNING_PROMPT}

Current Business Problem:
{task}

Research Findings:
{research}

Based on the business problem and research findings, create a practical
business execution plan.

Return only the planning content.
Do not include metadata, signatures, or explanations outside the plan.
"""

    print("[LLM] Planning Agent call")
    response = invoke_with_retry(llm, full_prompt)

    content = response.content

    # Gemini/LangChain may return structured content
    if isinstance(content, list):

        text_parts = []

        for item in content:

            if isinstance(item, dict):

                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))

            elif isinstance(item, str):
                text_parts.append(item)

        return "\n".join(text_parts).strip()

    # Normal string response
    if isinstance(content, str):
        return content.strip()

    return str(content)
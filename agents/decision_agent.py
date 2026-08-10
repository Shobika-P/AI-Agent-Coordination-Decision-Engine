from config import llm
from prompts.decision_prompt import DECISION_PROMPT
from utils.llm_helper import invoke_with_retry


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

Business Tool Analysis:
{tool_output}

Previous Business Decisions:
{history}

Use the business tool result while making the final decision.

Do not ignore the tool result.

Explain clearly how the tool influenced the recommendation.

Return only the final business decision.
Do not include metadata, signatures, or API response objects.
"""

    print("[LLM] Decision Agent call")
    response = invoke_with_retry(llm, full_prompt)

    content = response.content

    # Gemini/LangChain structured response
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
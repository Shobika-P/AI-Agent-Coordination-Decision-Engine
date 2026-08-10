from config import llm
from prompts.research_prompt import RESEARCH_PROMPT
from utils.llm_helper import invoke_with_retry


def research_agent(question):

    full_prompt = f"""
{RESEARCH_PROMPT}

User Question:
{question}
"""

    print("[LLM] Research Agent call")
    response = invoke_with_retry(llm, full_prompt)

    content = response.content

    # New Gemini/LangChain response format
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
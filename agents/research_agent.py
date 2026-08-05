from config import llm
from prompts.research_prompt import RESEARCH_PROMPT

def research_agent(question):
    full_prompt = f"""
{RESEARCH_PROMPT}

User Question:
{question}
"""

    response = llm.invoke(full_prompt)

    return response.content
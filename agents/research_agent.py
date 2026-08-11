import json
from prompts.research_prompt import RESEARCH_PROMPT
from utils.gemini_client import gemini_client


def research_agent(question):
    system_instruction = """
You are a Market Research Agent. Provide concise, structured market insights.
Return structured bullet points or JSON summary covering demand, competition, target audience, and risk.
"""

    print("[LLM] Research Agent call")
    res = gemini_client.generate(f"{RESEARCH_PROMPT}\n\nQuestion: {question}", system_instruction=system_instruction)
    return res.get("content", "").strip()
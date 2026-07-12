import os

from dotenv import load_dotenv
from google import genai

from prompts.research_prompt import RESEARCH_PROMPT

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def research_agent(question):
    full_prompt = f"""
{RESEARCH_PROMPT}

User Question:
{question}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )

    return response.text
import os

from dotenv import load_dotenv
from google import genai

from prompts.planning_prompt import PLANNING_PROMPT

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def planning_agent(task):
    full_prompt = f"""
{PLANNING_PROMPT}

User Request:
{task}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )

    return response.text
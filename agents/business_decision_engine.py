import os

from dotenv import load_dotenv
from google import genai

from prompts.business_decision_prompt import BUSINESS_DECISION_PROMPT

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)


def business_decision_engine(task):

    full_prompt = f"""
{BUSINESS_DECISION_PROMPT}

Business Problem:
{task}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )

    return response.text
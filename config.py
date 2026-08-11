import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

llm = None
if GOOGLE_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3,
            max_output_tokens=4096
        )
    except Exception as e:
        print(f"[config.py Warning] Failed to initialize ChatGoogleGenerativeAI: {e}")
else:
    print("[config.py Warning] GOOGLE_API_KEY is not set. Engine will operate under Gemini Client Demo/Cache Mode.")
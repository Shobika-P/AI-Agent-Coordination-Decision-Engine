import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


def main():
    
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")

    

    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found.")
        return

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=api_key,
        temperature=0.3,
    )

    print("=" * 60)
    print("AI Agent Coordination & Decision Engine")
    print("=" * 60)

    question = input("\nAsk Gemini anything: ")

    response = llm.invoke(question)

    print("\nGemini:\n")
    print(response.content)


if __name__ == "__main__":
    main()
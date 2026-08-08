import os

from dotenv import load_dotenv
from google import genai

from memory.shared_memory import SharedMemory

from agents.research_agent import research_agent
from agents.planning_agent import planning_agent
from agents.decision_agent import decision_agent

from tools.tool_manager import execute_tool

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

memory = SharedMemory()


def business_decision_engine(task):

    print("=" * 60)
    print("        AI BUSINESS DECISION ENGINE")
    print("=" * 60)

    print("\nBusiness Problem:")
    print(task)

    print("\nStep 1 : Checking Business Tools")
    print("-" * 60)

    try:

        tool_result = execute_tool(task)

        if tool_result:
            print("Business tool executed successfully.")
            print("\nTool Output")
            print(tool_result)

        else:
            print("No business tool required.")
            tool_result = "No business tool required."

    except Exception as e:

        print("Tool execution failed.")
        print("Actual Error:", e)

        tool_result = f"Tool Error : {e}"

    memory.save("tool", tool_result)

    print("\nStep 2 : Research Agent")
    print("-" * 60)

    research_result = research_agent(task)

    memory.save("research", research_result)

    print("Research completed.")

    print("\nStep 3 : Planning Agent")
    print("-" * 60)

    planning_result = planning_agent(
        task,
        memory.load("research")
    )

    memory.save("planning", planning_result)

    print("Planning completed.")

    print("\nStep 4 : Decision Agent")
    print("-" * 60)

    previous_history = memory.get_history()

    decision_result = decision_agent(
        task,
        memory.load("research"),
        memory.load("planning"),
        memory.load("tool"),
        previous_history
    )

    memory.save("decision", decision_result)

    memory.add_history(task, decision_result)

    print("Final business decision generated.")

    print("\nBusiness Decision Engine completed successfully.\n")

    return decision_result



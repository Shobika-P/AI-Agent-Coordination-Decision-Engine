import time
import os

from dotenv import load_dotenv
from google import genai
from agents.suggest_followups_agent import suggest_followups_agent
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

    start_total_time = time.time()
    metrics = {}

    print("=" * 60)
    print("        AI BUSINESS DECISION ENGINE")
    print("=" * 60)

    print("\nBusiness Problem:")
    print(task)

    print("\nStep 1 : Checking Business Tools")
    print("-" * 60)

    t0 = time.time()
    tool_executed = False
    raw_tool_result = None
    risk_level = "Medium"

    try:
        tool_result = execute_tool(task)

        if tool_result and tool_result != "No business tool required.":
            tool_executed = True
            raw_tool_result = tool_result
            print("Business tool executed successfully.")
            print("\nTool Output")
            print(tool_result)

            if isinstance(tool_result, dict):
                risk_level = tool_result.get("risk_level", "Medium")
        else:
            print("No business tool required.")
            tool_result = None

    except Exception as e:
        print("Tool execution failed.")
        print("Actual Error:", e)
        tool_result = f"Tool Error : {e}"

    metrics["step_1_tool_seconds"] = round(time.time() - t0, 2)
    memory.save("tool", tool_result)

    print("\nStep 2 : Research Agent")
    print("-" * 60)

    t0 = time.time()
    research_result = research_agent(task)
    metrics["step_2_research_seconds"] = round(time.time() - t0, 2)

    memory.save("research", research_result)
    print("Research completed.")

    print("\nStep 3 : Planning Agent")
    print("-" * 60)

    t0 = time.time()
    planning_result = planning_agent(
        task,
        memory.load("research")
    )
    metrics["step_3_planning_seconds"] = round(time.time() - t0, 2)

    memory.save("planning", planning_result)
    print("Planning completed.")

    print("\nStep 4 : Decision Agent")
    print("-" * 60)

    t0 = time.time()
    previous_history = ""

    decision_result = decision_agent(
        task,
        memory.load("research"),
        memory.load("planning"),
        memory.load("tool") or "No quantitative tool required for this analysis.",
        previous_history
    )
    metrics["step_4_decision_seconds"] = round(time.time() - t0, 2)

    memory.save("decision", decision_result)

    metrics["total_seconds"] = round(time.time() - start_total_time, 2)
    memory.add_history(task, decision_result, risk_level=risk_level)

    print("\nFinal business decision generated.")
    print("Business Decision Engine completed successfully.\n")

    report_data = {
        "decision": decision_result,
        "risk_level": risk_level,
        "execution_metrics": metrics
    }

    if tool_executed and isinstance(raw_tool_result, dict):
        report_data["tool_analysis"] = raw_tool_result

    return report_data
 


import time
import os
from dotenv import load_dotenv
from graph.decision_graph import report_workflow

load_dotenv()

def business_decision_engine(task):
    """
    Business Decision Engine wrapper.
    Delegates directly to LangGraph report_workflow as the single source of truth,
    preventing workflow duplication and unnecessary LLM calls.
    """
    print("=" * 60)
    print("        AI BUSINESS DECISION ENGINE")
    print("=" * 60)
    print("\nBusiness Problem:", task)

    initial_state = {
        "task": task,
        "conversation_id": None,
        "conversation_history": [],
        "research_result": None,
        "planning_result": None,
        "business_tool_result": None,
        "decision_result": None,
        "final_report": None,
        "followup_question": None,
        "followup_answer": None,
        "errors": [],
        "workflow_status": "started",
        "agent_statuses": {
            "tool": "QUEUED",
            "research": "QUEUED",
            "planning": "QUEUED",
            "decision": "QUEUED",
            "report": "QUEUED"
        },
        "execution_metrics": {}
    }

    final_state = report_workflow.invoke(initial_state)
    report = final_state.get("final_report") or {}
    print("\nBusiness Decision Engine completed via LangGraph StateGraph.\n")
    return report

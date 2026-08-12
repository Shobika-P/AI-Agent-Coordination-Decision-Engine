import time
import json
import uuid
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, START, END

from agents.research_agent import research_agent
from agents.planning_agent import planning_agent
from agents.decision_agent import decision_agent
from agents.followup_agent import followup_agent
from tools.tool_manager import execute_tool
from memory.shared_memory import SharedMemory
from memory.report_db import report_db

memory = SharedMemory()

class GraphState(TypedDict):
    task: str
    conversation_id: str
    selected_tool: Optional[str]
    conversation_history: List[Dict[str, str]]
    research_result: Optional[str]
    planning_result: Optional[str]
    business_tool_result: Optional[Any]
    decision_result: Optional[Any]
    final_report: Optional[Dict[str, Any]]
    followup_question: Optional[str]
    followup_answer: Optional[str]
    errors: List[str]
    workflow_status: str
    agent_statuses: Dict[str, str]
    execution_metrics: Dict[str, Any]


def business_tool_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    t0 = time.time()

    agent_statuses = dict(state.get("agent_statuses") or {})
    execution_metrics = dict(state.get("execution_metrics") or {})
    errors = list(state.get("errors") or [])

    agent_statuses["tool"] = "RUNNING"
    print("\n[LangGraph] Node: business_tool_node")

    tool_result = None
    selected_tool_name = "Market Risk Tool"

    try:
        raw_result = execute_tool(task)
        if raw_result and raw_result != "No business tool required.":
            tool_result = raw_result
            if isinstance(raw_result, dict):
                selected_tool_name = raw_result.get("tool", "Market Risk Tool")
            agent_statuses["tool"] = "COMPLETED"
        else:
            tool_result = "No quantitative tool required for this analysis."
            agent_statuses["tool"] = "SKIPPED"
    except Exception as e:
        print("[LangGraph] Tool Execution Error:", e)
        errors.append(f"Tool Error: {str(e)}")
        tool_result = f"Tool Error: {str(e)}"
        agent_statuses["tool"] = "FAILED"

    execution_metrics["tool_seconds"] = round(time.time() - t0, 2)
    memory.save("tool", tool_result)

    return {
        "selected_tool": selected_tool_name,
        "business_tool_result": tool_result,
        "agent_statuses": agent_statuses,
        "execution_metrics": execution_metrics,
        "errors": errors
    }


def research_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    t0 = time.time()

    agent_statuses = dict(state.get("agent_statuses") or {})
    execution_metrics = dict(state.get("execution_metrics") or {})
    errors = list(state.get("errors") or [])

    agent_statuses["research"] = "RUNNING"
    print("\n[LangGraph] Node: research_node")

    try:
        res = research_agent(task)
        agent_statuses["research"] = "COMPLETED"
    except Exception as e:
        print("[LangGraph] Research Agent Error:", e)
        errors.append(f"Research Error: {str(e)}")
        res = f"Research Error: {str(e)}"
        agent_statuses["research"] = "FAILED"

    execution_metrics["research_seconds"] = round(time.time() - t0, 2)
    memory.save("research", res)

    return {
        "research_result": res,
        "agent_statuses": agent_statuses,
        "execution_metrics": execution_metrics,
        "errors": errors
    }


def planning_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    research = state.get("research_result") or ""
    t0 = time.time()

    agent_statuses = dict(state.get("agent_statuses") or {})
    execution_metrics = dict(state.get("execution_metrics") or {})
    errors = list(state.get("errors") or [])

    agent_statuses["planning"] = "RUNNING"
    print("\n[LangGraph] Node: planning_node")

    try:
        plan = planning_agent(task, research)
        agent_statuses["planning"] = "COMPLETED"
    except Exception as e:
        print("[LangGraph] Planning Agent Error:", e)
        errors.append(f"Planning Error: {str(e)}")
        plan = f"Planning Error: {str(e)}"
        agent_statuses["planning"] = "FAILED"

    execution_metrics["planning_seconds"] = round(time.time() - t0, 2)
    memory.save("planning", plan)

    return {
        "planning_result": plan,
        "agent_statuses": agent_statuses,
        "execution_metrics": execution_metrics,
        "errors": errors
    }


def decision_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    research = state.get("research_result") or ""
    planning = state.get("planning_result") or ""
    tool_res = state.get("business_tool_result") or "No tool required."
    t0 = time.time()

    agent_statuses = dict(state.get("agent_statuses") or {})
    execution_metrics = dict(state.get("execution_metrics") or {})
    errors = list(state.get("errors") or [])

    agent_statuses["decision"] = "RUNNING"
    print("\n[LangGraph] Node: decision_node")

    try:
        decision = decision_agent(
            task,
            research,
            planning,
            tool_res,
            history=""
        )
        agent_statuses["decision"] = "COMPLETED"
    except Exception as e:
        print("[LangGraph] Decision Agent Error:", e)
        errors.append(f"Decision Error: {str(e)}")
        decision = {"decision": f"Decision Error: {str(e)}", "viability_score": 50, "confidence": 50}
        agent_statuses["decision"] = "FAILED"

    execution_metrics["decision_seconds"] = round(time.time() - t0, 2)
    memory.save("decision", decision)

    return {
        "decision_result": decision,
        "agent_statuses": agent_statuses,
        "execution_metrics": execution_metrics,
        "errors": errors
    }


def report_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    decision = state.get("decision_result")
    tool_res = state.get("business_tool_result")
    metrics = state.get("execution_metrics") or {}
    agent_statuses = dict(state.get("agent_statuses") or {})

    agent_statuses["report"] = "COMPLETED"
    print("\n[LangGraph] Node: report_node")

    risk_level = "Medium"
    if isinstance(tool_res, dict):
        risk_level = tool_res.get("risk_level", "Medium")

    decision_text = ""
    viability_score = 78
    confidence = 82
    why_this_decision = []
    key_risks = []
    key_opportunities = []
    recommended_decision = ""
    implementation_roadmap = []
    success_metrics = []
    conditions_and_assumptions = []
    conclusion = ""

    if isinstance(decision, dict):
        decision_text = decision.get("executive_summary") or decision.get("recommendation_title") or str(decision)
        viability_score = decision.get("viability_score", 78)
        confidence = decision.get("confidence", 82)
        why_this_decision = decision.get("why_this_decision", [])
        key_risks = decision.get("key_risks", [])
        key_opportunities = decision.get("key_opportunities", [])
        recommended_decision = decision.get("recommended_decision") or decision.get("recommendation_title") or ""
        implementation_roadmap = decision.get("implementation_roadmap", [])
        success_metrics = decision.get("success_metrics", [])
        conditions_and_assumptions = decision.get("conditions_and_assumptions", [])
        conclusion = decision.get("conclusion", "")
    else:
        decision_text = str(decision)

    report_data = {
        "decision": decision_text,
        "risk_level": risk_level,
        "viability_score": viability_score,
        "confidence": confidence,
        "why_this_decision": why_this_decision,
        "key_risks": key_risks,
        "key_opportunities": key_opportunities,
        "recommended_decision": recommended_decision,
        "implementation_roadmap": implementation_roadmap,
        "success_metrics": success_metrics,
        "conditions_and_assumptions": conditions_and_assumptions,
        "conclusion": conclusion,
        "execution_metrics": metrics
    }

    if isinstance(tool_res, dict):
        report_data["tool_analysis"] = tool_res

    # Save to SQLite Database
    conv_id = state.get("conversation_id") or str(uuid.uuid4())
    report_db.save_report(
        report_id=conv_id,
        original_question=task,
        report_data=report_data,
        conversation_history=state.get("conversation_history") or []
    )

    session_data = {
        "task": task,
        "report": report_data,
        "conversation_history": state.get("conversation_history") or [],
        "agent_statuses": agent_statuses,
        "metrics": metrics
    }
    memory.save_session(conv_id, session_data)

    return {
        "final_report": report_data,
        "agent_statuses": agent_statuses,
        "workflow_status": "completed"
    }


# Build Report Workflow Graph
report_builder = StateGraph(GraphState)

report_builder.add_node("business_tool_node", business_tool_node)
report_builder.add_node("research_node", research_node)
report_builder.add_node("planning_node", planning_node)
report_builder.add_node("decision_node", decision_node)
report_builder.add_node("report_node", report_node)

report_builder.add_edge(START, "business_tool_node")
report_builder.add_edge("business_tool_node", "research_node")
report_builder.add_edge("research_node", "planning_node")
report_builder.add_edge("planning_node", "decision_node")
report_builder.add_edge("decision_node", "report_node")
report_builder.add_edge("report_node", END)

report_workflow = report_builder.compile()


# Follow-up Workflow Nodes
def load_previous_context(state: GraphState) -> Dict[str, Any]:
    conv_id = state.get("conversation_id")
    print(f"\n[LangGraph Follow-up] Node: load_previous_context for session: {conv_id}")

    session = memory.load_session(conv_id) if conv_id else None

    if session:
        return {
            "task": session.get("task") or state.get("task", ""),
            "final_report": session.get("report") or state.get("final_report"),
            "conversation_history": session.get("conversation_history") or state.get("conversation_history", [])
        }

    return {}


def followup_analysis_node(state: GraphState) -> Dict[str, Any]:
    print("[LangGraph Follow-up] Node: followup_analysis_node")
    question = state.get("followup_question", "")
    task = state.get("task", "")
    report = state.get("final_report")

    if not question:
        return {"errors": ["Missing follow-up question"]}

    return {
        "followup_question": question,
        "task": task,
        "final_report": report
    }


def followup_response_node(state: GraphState) -> Dict[str, Any]:
    print("[LangGraph Follow-up] Node: followup_response_node")
    question = state.get("followup_question", "")
    task = state.get("task", "")
    report = state.get("final_report")
    history = state.get("conversation_history") or []
    errors = list(state.get("errors") or [])

    answer = ""
    try:
        answer = followup_agent(task, report, question, conversation_history=history)
    except Exception as e:
        print("[LangGraph Follow-up] Agent Error:", e)
        errors.append(str(e))
        answer = f"Error generating follow-up answer: {str(e)}"

    return {
        "followup_answer": answer,
        "errors": errors
    }


def update_memory_node(state: GraphState) -> Dict[str, Any]:
    print("[LangGraph Follow-up] Node: update_memory_node")
    conv_id = state.get("conversation_id")
    question = state.get("followup_question", "")
    answer = state.get("followup_answer", "")

    history = list(state.get("conversation_history") or [])
    if question and answer:
        history.append({"question": question, "answer": answer})

    if conv_id:
        session = memory.load_session(conv_id) or {}
        session["conversation_history"] = history
        memory.save_session(conv_id, session)
        report_db.update_conversation(conv_id, history)

    return {
        "conversation_history": history,
        "workflow_status": "completed"
    }


followup_builder = StateGraph(GraphState)

followup_builder.add_node("load_previous_context", load_previous_context)
followup_builder.add_node("followup_analysis_node", followup_analysis_node)
followup_builder.add_node("followup_response_node", followup_response_node)
followup_builder.add_node("update_memory_node", update_memory_node)

followup_builder.add_edge(START, "load_previous_context")
followup_builder.add_edge("load_previous_context", "followup_analysis_node")
followup_builder.add_edge("followup_analysis_node", "followup_response_node")
followup_builder.add_edge("followup_response_node", "update_memory_node")
followup_builder.add_edge("update_memory_node", END)

followup_workflow = followup_builder.compile()


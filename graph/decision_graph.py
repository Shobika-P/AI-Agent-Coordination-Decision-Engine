import time
import json
import uuid
from typing import TypedDict, List, Dict, Any, Optional, Annotated

from langgraph.graph import StateGraph, START, END

from agents.research_agent import research_agent
from agents.planning_agent import planning_agent
from agents.decision_agent import decision_agent
from agents.followup_agent import followup_agent
from tools.tool_manager import execute_tool
from memory.shared_memory import SharedMemory
from memory.report_db import report_db

memory = SharedMemory()


def merge_dict(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    res = dict(a or {})
    res.update(b or {})
    return res


def merge_list(a: Optional[List[Any]], b: Optional[List[Any]]) -> List[Any]:
    res = list(a or [])
    for item in (b or []):
        if item not in res:
            res.append(item)
    return res


class GraphState(TypedDict):
    task: str
    conversation_id: str
    user_id: Optional[str]
    force_refresh: Optional[bool]
    selected_tool: Optional[str]
    conversation_history: List[Dict[str, str]]
    research_result: Optional[Any]
    planning_result: Optional[Any]
    business_tool_result: Optional[Any]
    decision_result: Optional[Any]
    final_report: Optional[Dict[str, Any]]
    followup_question: Optional[str]
    followup_answer: Optional[str]
    errors: Annotated[List[str], merge_list]
    workflow_status: str
    agent_statuses: Annotated[Dict[str, str], merge_dict]
    execution_metrics: Annotated[Dict[str, Any], merge_dict]


def business_tool_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    t0 = time.time()

    print("\n[LangGraph] Node: business_tool_node")

    tool_result = None
    selected_tool_name = "Market Risk Tool"
    status = "RUNNING"
    node_errors = []

    try:
        raw_result = execute_tool(task)
        if raw_result and raw_result != "No business tool required.":
            tool_result = raw_result
            if isinstance(raw_result, dict):
                selected_tool_name = raw_result.get("tool", "Market Risk Tool")
            status = "COMPLETED"
        else:
            tool_result = "No quantitative tool required for this analysis."
            status = "SKIPPED"
    except Exception as e:
        print("[LangGraph] Tool Execution Error:", e)
        node_errors.append(f"Tool Error: {str(e)}")
        tool_result = f"Tool Error: {str(e)}"
        status = "FAILED"

    elapsed = round(time.time() - t0, 2)
    memory.save("tool", tool_result)

    return {
        "selected_tool": selected_tool_name,
        "business_tool_result": tool_result,
        "agent_statuses": {"tool": status},
        "execution_metrics": {"tool_seconds": elapsed},
        "errors": node_errors
    }


def research_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    force_refresh = state.get("force_refresh", False)
    t0 = time.time()

    print("\n[LangGraph] Node: research_node")

    status = "RUNNING"
    node_errors = []
    res = None

    try:
        res = research_agent(task, force_refresh=force_refresh)
        if isinstance(res, dict) and res.get("success") is False:
            status = "FAILED"
            node_errors.append(f"Research Error: {res.get('error')}")
        else:
            status = "COMPLETED"
    except Exception as e:
        print("[LangGraph] Research Agent Error:", e)
        node_errors.append(f"Research Error: {str(e)}")
        res = {
            "success": False,
            "status": "temporary_ai_unavailable",
            "message": "The AI analysis service is temporarily busy. Please try again in a moment.",
            "retry_after_seconds": 15,
            "error": str(e),
            "analysis_source": "UNAVAILABLE"
        }
        status = "FAILED"

    elapsed = round(time.time() - t0, 2)
    memory.save("research", res)

    return {
        "research_result": res,
        "agent_statuses": {"research": status},
        "execution_metrics": {"research_seconds": elapsed},
        "errors": node_errors
    }


def planning_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    research = state.get("research_result") or {}
    t0 = time.time()

    print("\n[LangGraph] Node: planning_node")

    status = "RUNNING"
    node_errors = []
    plan = None

    if isinstance(research, dict) and research.get("success") is False:
        status = "SKIPPED"
        plan = []
    else:
        try:
            plan = planning_agent(task, research)
            status = "COMPLETED"
        except Exception as e:
            print("[LangGraph] Planning Agent Error:", e)
            node_errors.append(f"Planning Error: {str(e)}")
            plan = []
            status = "FAILED"

    elapsed = round(time.time() - t0, 2)
    memory.save("planning", plan)

    return {
        "planning_result": plan,
        "agent_statuses": {"planning": status},
        "execution_metrics": {"planning_seconds": elapsed},
        "errors": node_errors
    }


def decision_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    research = state.get("research_result") or {}
    planning = state.get("planning_result") or []
    tool_res = state.get("business_tool_result") or "No tool required."
    t0 = time.time()

    print("\n[LangGraph] Node: decision_node")

    status = "RUNNING"
    node_errors = []
    decision = None

    if isinstance(research, dict) and research.get("success") is False:
        status = "FAILED"
        decision = research
    else:
        try:
            decision = decision_agent(
                task,
                research,
                planning,
                tool_res,
                history=""
            )
            status = "COMPLETED"
        except Exception as e:
            print("[LangGraph] Decision Agent Error:", e)
            node_errors.append(f"Decision Error: {str(e)}")
            decision = {
                "success": False,
                "status": "temporary_ai_unavailable",
                "message": "Failed to synthesize decision report.",
                "error": str(e),
                "analysis_source": "UNAVAILABLE"
            }
            status = "FAILED"

    elapsed = round(time.time() - t0, 2)
    memory.save("decision", decision)

    return {
        "decision_result": decision,
        "agent_statuses": {"decision": status},
        "execution_metrics": {"decision_seconds": elapsed},
        "errors": node_errors
    }


def report_node(state: GraphState) -> Dict[str, Any]:
    task = state["task"]
    decision = state.get("decision_result")
    tool_res = state.get("business_tool_result")
    metrics = dict(state.get("execution_metrics") or {})
    agent_statuses = dict(state.get("agent_statuses") or {})

    print("\n[LangGraph] Node: report_node")

    # If decision/research failed, return failure without fabricating a generic report
    if isinstance(decision, dict) and decision.get("success") is False:
        agent_statuses["report"] = "FAILED"
        failure_status = decision.get("status", "temporary_ai_unavailable")
        return {
            "final_report": decision,
            "agent_statuses": agent_statuses,
            "workflow_status": failure_status
        }

    agent_statuses["report"] = "COMPLETED"

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
    suggested_followups = []
    conclusion = ""
    analysis_source = "LIVE_AI"
    is_demo = False
    quota_exhausted = False

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
        suggested_followups = decision.get("suggested_followups", [])
        conclusion = decision.get("conclusion", "")
        analysis_source = decision.get("analysis_source", "LIVE_AI")
        is_demo = decision.get("is_demo", False)
        quota_exhausted = decision.get("quota_exhausted", False)
        if decision.get("risk_level"):
            risk_level = decision.get("risk_level")
    else:
        decision_text = str(decision)

    if not suggested_followups:
        clean_t = task.strip("?.!") if task else "this initiative"
        suggested_followups = [
            f"What are the primary operational bottlenecks for {clean_t}?",
            f"What happens to profitability if customer acquisition costs increase by 30%?",
            f"What is the break-even volume required during Phase 1?",
            f"How can we mitigate the main competitive risks?"
        ]

    report_data = {
        "success": True,
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
        "suggested_followups": suggested_followups,
        "conclusion": conclusion,
        "execution_metrics": metrics,
        "analysis_source": analysis_source,
        "is_demo": is_demo,
        "quota_exhausted": quota_exhausted
    }

    if isinstance(tool_res, dict):
        report_data["tool_analysis"] = tool_res

    # Save to SQLite Database (Only if valid report)
    conv_id = state.get("conversation_id") or str(uuid.uuid4())
    user_id = state.get("user_id")
    report_db.save_report(
        report_id=conv_id,
        original_question=task,
        report_data=report_data,
        conversation_history=state.get("conversation_history") or [],
        user_id=user_id
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
report_builder.add_edge(START, "research_node")
report_builder.add_edge("business_tool_node", "planning_node")
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
        report_db.update_conversation(conv_id, history, user_id=state.get("user_id"))

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

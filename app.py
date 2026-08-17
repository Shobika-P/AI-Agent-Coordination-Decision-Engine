import os
import uuid
import json
import threading
import re
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from graph.decision_graph import report_workflow, followup_workflow
from utils.pdf_generator import generate_decision_pdf
from memory.shared_memory import SharedMemory
from memory.report_db import report_db
from utils.gemini_client import gemini_client
from tools.market_risk_tool import market_risk
from tools.break_even_tool import calculate_break_even
from tools.profit_tool import calculate_profit

app = Flask(__name__)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, origins=allowed_origins)

memory = SharedMemory()

# Query Cache & Concurrent Request Deduplication Locks
report_cache = {}  # norm_query -> dict response payload
active_report_requests = {}  # norm_query -> (threading.Event, holder_dict)
report_lock = threading.Lock()

def _normalize_query(task: str) -> str:
    return re.sub(r'\s+', ' ', (task or "").strip().lower())


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "Enterprise AI Business Decision Engine",
        "model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        "orchestration": "LangGraph StateGraph",
        "storage": "SQLite Persistent Database",
        "quota_status": "demo_fallback" if gemini_client.quota_exhausted else "active"
    }), 200


@app.route("/monitoring", methods=["GET"])
def get_monitoring():
    try:
        telemetry = memory.get_monitoring_metrics()
        return jsonify({
            "success": True,
            "metrics": telemetry
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# LANGGRAPH REPORT GENERATION
# ============================================================

@app.route("/generate-report", methods=["POST"])
def generate_report():
    data = request.get_json(silent=True) or {}
    task = data.get("task", "").strip()
    conversation_id = data.get("conversation_id") or str(uuid.uuid4())

    if not task:
        return jsonify({
            "success": False,
            "error": "Business problem is required."
        }), 400

    norm_query = _normalize_query(task)

    # 1. Check In-Memory Query Cache
    with report_lock:
        if norm_query in report_cache:
            print(f"[Report Cache HIT] Returning cached report for query: '{task}'")
            cached_payload = dict(report_cache[norm_query])
            cached_payload["conversation_id"] = conversation_id
            return jsonify(cached_payload), 200

    # 2. Check Database for Existing Match
    existing_reports = report_db.list_reports(search=task)
    if existing_reports:
        for rep in existing_reports:
            if _normalize_query(rep.get("original_question", "")) == norm_query:
                full_rep = report_db.get_report(rep["report_id"])
                if full_rep and full_rep.get("report_data"):
                    print(f"[Report DB Cache HIT] Found existing report in DB for query: '{task}'")
                    db_payload = {
                        "success": True,
                        "task": task,
                        "conversation_id": conversation_id,
                        "report": full_rep["report_data"],
                        "workflow": {
                            "status": "completed",
                            "agent_statuses": {
                                "tool": "COMPLETED",
                                "research": "COMPLETED",
                                "planning": "COMPLETED",
                                "decision": "COMPLETED",
                                "report": "COMPLETED"
                            },
                            "metrics": full_rep["report_data"].get("execution_metrics", {})
                        },
                        "quota_notice": "AI quota temporarily unavailable. Cached analysis or demo mode is being used." if gemini_client.quota_exhausted else None
                    }
                    with report_lock:
                        report_cache[norm_query] = db_payload
                    return jsonify(db_payload), 200

    # 3. Concurrent Request Deduplication
    need_wait = False
    with report_lock:
        if norm_query in active_report_requests:
            event, holder = active_report_requests[norm_query]
            print(f"[Concurrent Request DEDUPLICATED] Waiting for active workflow: '{task}'")
            need_wait = True
        else:
            event = threading.Event()
            holder = {"response_data": None}
            active_report_requests[norm_query] = (event, holder)
            need_wait = False

    if need_wait:
        event.wait(timeout=60.0)
        res_data = holder.get("response_data")
        if res_data:
            res_payload = dict(res_data[0])
            res_payload["conversation_id"] = conversation_id
            return jsonify(res_payload), res_data[1]

    # 4. Execute LangGraph Workflow
    try:
        print("\n" + "=" * 60)
        print(f"LANGGRAPH MULTI-AGENT ENGINE [ID: {conversation_id}]")
        print("=" * 60)
        print("Query:", task)

        initial_state = {
            "task": task,
            "conversation_id": conversation_id,
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

        report = final_state.get("final_report")
        agent_statuses = final_state.get("agent_statuses")

        print("\n[LangGraph] Workflow Completed Successfully.")

        response_payload = {
            "success": True,
            "task": task,
            "conversation_id": conversation_id,
            "report": report,
            "workflow": {
                "status": final_state.get("workflow_status", "completed"),
                "agent_statuses": agent_statuses,
                "metrics": final_state.get("execution_metrics")
            },
            "quota_notice": "AI quota temporarily unavailable. Cached analysis or demo mode is being used." if gemini_client.quota_exhausted else None
        }

        if report:
            with report_lock:
                report_cache[norm_query] = response_payload

        with report_lock:
            holder["response_data"] = (response_payload, 200)
            event.set()
            active_report_requests.pop(norm_query, None)

        return jsonify(response_payload), 200

    except Exception as e:
        err_str = str(e)
        print("\n[LangGraph ERROR] Generating Report:", repr(e))

        err_payload = {
            "success": False,
            "error": f"Analysis system warning: {err_str}",
            "quota_notice": "AI quota temporarily unavailable. Cached analysis or demo mode is being used."
        }

        with report_lock:
            holder["response_data"] = (err_payload, 200)
            event.set()
            active_report_requests.pop(norm_query, None)

        return jsonify(err_payload), 200



# ============================================================
# LANGGRAPH DYNAMIC FOLLOW-UP QUESTION
# ============================================================

@app.route("/follow-up", methods=["POST"])
def follow_up():
    try:
        data = request.get_json(silent=True) or {}

        question = data.get("question", "").strip()
        conversation_id = data.get("conversation_id")
        original_task = data.get("original_task", "")
        report = data.get("report")

        if not question:
            return jsonify({
                "success": False,
                "error": "Follow-up question is required."
            }), 400

        print("\n" + "=" * 60)
        print("LANGGRAPH USER DYNAMIC FOLLOW-UP")
        print("=" * 60)
        print("Question:", question)

        existing_session = memory.load_session(conversation_id) if conversation_id else None
        if not conversation_id or not existing_session:
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            memory.save_session(conversation_id, {
                "task": original_task,
                "report": report,
                "conversation_history": existing_session.get("conversation_history", []) if existing_session else []
            })

        followup_initial_state = {
            "task": original_task,
            "conversation_id": conversation_id,
            "conversation_history": existing_session.get("conversation_history", []) if existing_session else [],
            "research_result": None,
            "planning_result": None,
            "business_tool_result": None,
            "decision_result": None,
            "final_report": report,
            "followup_question": question,
            "followup_answer": None,
            "errors": [],
            "workflow_status": "started",
            "agent_statuses": {},
            "execution_metrics": {}
        }

        # Run Follow-up LangGraph Workflow
        final_followup_state = followup_workflow.invoke(followup_initial_state)

        answer = final_followup_state.get("followup_answer")

        print("[LangGraph Follow-up] Response generated successfully.")

        return jsonify({
            "success": True,
            "answer": answer,
            "conversation_id": conversation_id,
            "conversation_history": final_followup_state.get("conversation_history", []),
            "workflow_status": "completed"
        }), 200

    except Exception as e:
        err_str = str(e)
        print("\n[LangGraph ERROR] Processing Follow-up:", repr(e))

        # Always return structured answer fallback so page never blanks out
        return jsonify({
            "success": True,
            "answer": f"Analysis note: {err_str}. Based on current financial tool estimates, maintaining lean operational expenses optimizes break-even timelines.",
            "conversation_id": conversation_id,
            "workflow_status": "completed_fallback"
        }), 200


def format_inr(val, include_symbol=True):
    try:
        val = float(val)
        is_neg = val < 0
        val = abs(val)
        if val.is_integer():
            s = f"{int(val)}"
        else:
            s = f"{val:,.2f}"
            
        if '.' in s:
            int_part, dec_part = s.split('.')
        else:
            int_part, dec_part = s, None
            
        int_part = int_part.replace(',', '')
        if len(int_part) > 3:
            last3 = int_part[-3:]
            other = int_part[:-3]
            res = ""
            while len(other) > 2:
                res = "," + other[-2:] + res
                other = other[:-2]
            formatted_int = other + res + "," + last3
        else:
            formatted_int = int_part
            
        final_num = f"{formatted_int}.{dec_part}" if dec_part else formatted_int
        prefix = "-₹" if is_neg else ("₹" if include_symbol else "")
        return f"{prefix}{final_num}"
    except:
        return f"₹{val}" if include_symbol else str(val)


# ============================================================
# WHAT-IF SENSITIVITY ANALYSIS
# ============================================================

@app.route("/what-if", methods=["POST"])
def what_if_analysis():
    try:
        data = request.get_json(silent=True) or {}
        task = data.get("task", "")
        price = float(data.get("price", 500))
        monthly_orders = float(data.get("monthly_orders", 100))
        marketing_cost = float(data.get("marketing_cost", 10000))
        cac = float(data.get("cac", 50))
        variable_cost = float(data.get("variable_cost", 300))
        fixed_cost = float(data.get("fixed_cost", 50000))

        # Calculate updated figures
        revenue = price * monthly_orders
        monthly_variable = variable_cost * monthly_orders
        total_monthly_cost = fixed_cost + monthly_variable + marketing_cost
        monthly_profit = revenue - total_monthly_cost
        
        # Break-even units
        unit_margin = price - variable_cost
        be_units = round(fixed_cost / unit_margin) if unit_margin > 0 else 999999

        # Updated risk and viability calculation
        updated_viability = 75
        updated_risk = "Medium"
        if monthly_profit > 20000:
            updated_viability = 90
            updated_risk = "Low"
        elif monthly_profit < 0:
            updated_viability = 45
            updated_risk = "High"

        explanation = (
            f"At {format_inr(price)} unit price and {format_inr(monthly_orders, include_symbol=False)} monthly orders, projected monthly revenue is {format_inr(revenue)}. "
            f"After accounting for monthly fixed cost ({format_inr(fixed_cost)}), variable costs ({format_inr(monthly_variable)}), and marketing ({format_inr(marketing_cost)}), "
            f"the projected monthly net profit is {format_inr(monthly_profit)} with a break-even point of {format_inr(be_units, include_symbol=False)} units."
        )

        return jsonify({
            "success": True,
            "task": task,
            "updated_viability_score": updated_viability,
            "updated_risk_level": updated_risk,
            "monthly_profit": monthly_profit,
            "break_even_units": be_units,
            "explanation": explanation,
            "parameters": {
                "price": price,
                "monthly_orders": monthly_orders,
                "marketing_cost": marketing_cost,
                "cac": cac,
                "variable_cost": variable_cost,
                "fixed_cost": fixed_cost
            }
        }), 200

    except Exception as e:
        print("\nERROR IN WHAT-IF ANALYSIS:", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PERSISTENT REPORT LIBRARY API ROUTES
# ============================================================

@app.route("/reports", methods=["GET"])
def get_reports_library():
    try:
        search = request.args.get("search", "").strip()
        risk_filter = request.args.get("risk", "ALL").strip()
        reports = report_db.list_reports(search=search, risk_filter=risk_filter)
        return jsonify({"success": True, "reports": reports}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/<report_id>", methods=["GET"])
def get_single_report(report_id):
    try:
        r = report_db.get_report(report_id)
        if not r:
            return jsonify({"success": False, "error": "Report not found"}), 404
        return jsonify({"success": True, "report": r}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/<report_id>", methods=["DELETE"])
def delete_single_report(report_id):
    try:
        ok = report_db.delete_report(report_id)
        return jsonify({"success": ok}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/compare", methods=["GET"])
def compare_reports():
    try:
        id1 = request.args.get("id1", "").strip()
        id2 = request.args.get("id2", "").strip()
        if not id1 or not id2:
            return jsonify({"success": False, "error": "Two report IDs are required for comparison."}), 400

        r1 = report_db.get_report(id1)
        r2 = report_db.get_report(id2)

        if not r1 or not r2:
            return jsonify({"success": False, "error": "One or both reports could not be found."}), 444

        return jsonify({
            "success": True,
            "report1": r1,
            "report2": r2
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/re-run-decision", methods=["POST"])
def rerun_decision_stage():
    try:
        data = request.get_json(silent=True) or {}
        task = data.get("task", "")
        report_id = data.get("report_id") or str(uuid.uuid4())
        
        price = float(data.get("price", 500))
        monthly_orders = float(data.get("monthly_orders", 150))
        marketing_cost = float(data.get("marketing_cost", 10000))
        cac = float(data.get("cac", 45))
        fixed_cost = float(data.get("fixed_cost", 50000))
        variable_cost = float(data.get("variable_cost", 300))

        # 1. Recalculate tool metrics
        revenue = price * monthly_orders
        monthly_var = variable_cost * monthly_orders
        total_cost = fixed_cost + monthly_var + marketing_cost
        profit = revenue - total_cost

        unit_margin = price - variable_cost
        be_units = round(fixed_cost / unit_margin) if unit_margin > 0 else 999999

        tool_risk = "Medium"
        if profit > 20000:
            tool_risk = "Low"
        elif profit < 0:
            tool_risk = "High"

        updated_tool_result = {
            "tool": "Sensitivity Analysis Engine",
            "tool_name": "Adjusted Assumptions Tool",
            "risk_level": tool_risk,
            "observations": [
                f"Adjusted Selling Price: {format_inr(price)} / unit",
                f"Monthly Volume Target: {format_inr(monthly_orders, include_symbol=False)} units",
                f"Projected Monthly Profit: {format_inr(profit)}",
                f"Break-even Volume: {format_inr(be_units, include_symbol=False)} units"
            ],
            "recommendation": f"At {format_inr(price)} price and {format_inr(monthly_orders, include_symbol=False)} units volume, the business generates {format_inr(profit)} monthly net profit."
        }

        # 2. Fetch or load research and planning context
        existing_report = report_db.get_report(report_id)
        research_context = data.get("research_result") or "Market demand is strong with price sensitive segment."
        planning_context = data.get("planning_result") or "Phase 1: MVP Setup. Phase 2: Customer Acquisition. Phase 3: Scale."
        
        if existing_report and existing_report.get("report_data"):
            r_data = existing_report["report_data"]
            if r_data.get("research_summary"):
                research_context = json.dumps(r_data["research_summary"])
            if r_data.get("business_plan"):
                planning_context = json.dumps(r_data["business_plan"])

        # 3. Re-run Decision Agent with modified assumptions
        from agents.decision_agent import decision_agent
        new_decision = decision_agent(
            task,
            research_context,
            planning_context,
            updated_tool_result
        )

        viability = 75
        if profit > 25000:
            viability = 92
        elif profit > 10000:
            viability = 82
        elif profit < 0:
            viability = 40

        updated_report_data = {
            "decision": new_decision.get("executive_summary") if isinstance(new_decision, dict) else str(new_decision),
            "risk_level": tool_risk,
            "viability_score": new_decision.get("viability_score", viability) if isinstance(new_decision, dict) else viability,
            "confidence": new_decision.get("confidence", 85) if isinstance(new_decision, dict) else 85,
            "why_this_decision": new_decision.get("why_this_decision", []) if isinstance(new_decision, dict) else [],
            "key_risks": new_decision.get("key_risks", []) if isinstance(new_decision, dict) else [],
            "key_opportunities": new_decision.get("key_opportunities", []) if isinstance(new_decision, dict) else [],
            "tool_analysis": updated_tool_result
        }

        report_db.save_report(
            report_id=report_id,
            original_question=task,
            report_data=updated_report_data,
            conversation_history=existing_report.get("conversation_history", []) if existing_report else []
        )

        return jsonify({
            "success": True,
            "report_id": report_id,
            "updated_report": updated_report_data
        }), 200

    except Exception as e:
        print("Error re-running decision agent:", e)
        return jsonify({"success": False, "error": str(e)}), 500



# ============================================================
# REPORT EXPORT (PDF, JSON, MARKDOWN)
# ============================================================

@app.route("/export-report", methods=["POST"])
def export_report():
    try:
        data = request.get_json(silent=True) or {}
        export_format = data.get("format", "pdf").lower()
        report = data.get("report") or {}
        task = data.get("task", "Business Decision Query")
        history = data.get("conversation_history", [])

        if export_format == "pdf":
            pdf_bytes = generate_decision_pdf(report, task, history)
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=Decision_Report_{uuid.uuid4().hex[:6]}.pdf"
                }
            )

        elif export_format == "json":
            export_payload = {
                "task": task,
                "report": report,
                "conversation_history": history
            }
            return Response(
                json.dumps(export_payload, indent=2),
                mimetype="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=Decision_Report_{uuid.uuid4().hex[:6]}.json"
                }
            )

        elif export_format == "markdown":
            decision_text = str(report.get("decision", ""))
            risk = str(report.get("risk_level", "Medium"))
            viability = report.get("viability_score", 78)
            confidence = report.get("confidence", 82)
            
            md_content = f"# Executive Strategic Decision Report\n\n**Query:** {task}\n**Risk Level:** {risk}\n**Viability Score:** {viability}/100\n**AI Confidence:** {confidence}%\n\n---\n\n## Executive Summary\n\n{decision_text}\n"

            if history:
                md_content += "\n---\n\n## Follow-up Conversation\n\n"
                for idx, turn in enumerate(history, 1):
                    md_content += f"### Question {idx}\n**User:** {turn.get('question')}\n\n**AI Decision Engine:** {turn.get('answer')}\n\n"

            return Response(
                md_content,
                mimetype="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=Decision_Report_{uuid.uuid4().hex[:6]}.md"
                }
            )

        return jsonify({"success": False, "error": "Unsupported export format"}), 400

    except Exception as e:
        print("\nERROR EXPORTING REPORT:", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# GET DECISION HISTORY (SQLITE SOURCE OF TRUTH)
# ============================================================

@app.route("/history", methods=["GET"])
def get_history():
    try:
        reports = report_db.list_reports()
        return jsonify({
            "success": True,
            "history": reports
        }), 200

    except Exception as e:
        print("\nERROR RETRIEVING HISTORY:", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(
        debug=True,
        host="0.0.0.0" if os.getenv("PORT") else "127.0.0.1",
        port=port
    )
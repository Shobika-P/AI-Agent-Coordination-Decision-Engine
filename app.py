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
from utils.auth_helper import generate_auth_token, verify_auth_token, require_auth, optional_auth, get_authenticated_user
from tools.market_risk_tool import market_risk
from tools.break_even_tool import calculate_break_even
from tools.profit_tool import calculate_profit

app = Flask(__name__)

# Production-safe CORS configuration
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [orig.strip() for orig in allowed_origins_raw.split(",") if orig.strip()]
if "*" in allowed_origins or not allowed_origins:
    CORS(app, resources={r"/*": {"origins": "*"}})
else:
    CORS(app, resources={r"/*": {"origins": allowed_origins}})

memory = SharedMemory()

# In-Memory Exact Query Cache & Concurrent Request Deduplication Locks
report_cache = {}  # norm_query -> dict response payload
active_report_requests = {}  # norm_query -> (threading.Event, holder_dict)
report_lock = threading.Lock()


def _normalize_query(task: str) -> str:
    return re.sub(r'\s+', ' ', (task or "").strip().lower())


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health_check():
    telemetry = gemini_client.get_telemetry_metrics()
    status = telemetry.get("status", "LIVE")

    return jsonify({
        "status": status,
        "mode": status,
        "service": "Enterprise AI Business Decision Engine",
        "primary_model": telemetry.get("primary_model", os.getenv("GEMINI_MODEL", "gemini-3.7-flash")),
        "fallback_model": telemetry.get("fallback_model", os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")),
        "lightweight_model": telemetry.get("lightweight_model", os.getenv("GEMINI_LIGHTWEIGHT_MODEL", "gemini-3.5-flash-lite")),
        "model_chain": telemetry.get("model_chain", []),
        "orchestration": "LangGraph StateGraph",
        "storage": "SQLite Persistent Database",
        "gemini_available": telemetry.get("gemini_available", False),
        "circuit_state": telemetry.get("circuit_state", "CLOSED"),
        "quota_exhausted": telemetry.get("quota_exhausted", False)
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
# USER AUTHENTICATION API ROUTES
# ============================================================

@app.route("/register", methods=["POST"])
@app.route("/auth/register", methods=["POST"])
def register():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required."
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "error": "Password must be at least 6 characters long."
            }), 400

        user = report_db.create_user(email=email, password=password)
        token = generate_auth_token(user["id"], user["email"])

        return jsonify({
            "success": True,
            "message": "User registered successfully.",
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"]
            }
        }), 201

    except ValueError as ve:
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
    except Exception as e:
        print("[Register ERROR]:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to complete registration."
        }), 500


@app.route("/login", methods=["POST"])
@app.route("/auth/login", methods=["POST"])
def login():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required."
            }), 400

        user = report_db.authenticate_user(email=email, password=password)
        if not user:
            return jsonify({
                "success": False,
                "error": "Invalid email or password."
            }), 401

        token = generate_auth_token(user["id"], user["email"])

        return jsonify({
            "success": True,
            "message": "Logged in successfully.",
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"]
            }
        }), 200

    except Exception as e:
        print("[Login ERROR]:", repr(e))
        return jsonify({
            "success": False,
            "error": "Authentication failed. Please try again."
        }), 500


@app.route("/logout", methods=["POST"])
@app.route("/auth/logout", methods=["POST"])
def logout():
    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200


@app.route("/auth/me", methods=["GET"])
@require_auth
def get_current_authenticated_user():
    user = request.user
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "created_at": user.get("created_at")
        }
    }), 200


# ============================================================
# LANGGRAPH REPORT GENERATION
# ============================================================

@app.route("/generate-report", methods=["POST"])
@optional_auth
def generate_report():
    data = request.get_json(silent=True) or {}
    task = data.get("task", "").strip()
    conversation_id = data.get("conversation_id") or str(uuid.uuid4())
    force_refresh = bool(data.get("force_refresh", False))
    user_id = getattr(request, "user_id", None)

    if not task:
        return jsonify({
            "success": False,
            "error": "Business problem is required."
        }), 400

    norm_query = _normalize_query(task)

    # 1. Check In-Memory Exact Query Cache (Only genuine live responses are cached)
    if not force_refresh:
        with report_lock:
            if norm_query in report_cache:
                print(f"[Report Cache HIT] Returning cached report for query: '{task}'")
                cached_payload = json.loads(json.dumps(report_cache[norm_query]))
                cached_payload["conversation_id"] = conversation_id
                if isinstance(cached_payload.get("report"), dict):
                    cached_payload["report"]["analysis_source"] = "LIVE_CACHE"
                    if user_id:
                        report_db.save_report(
                            report_id=conversation_id,
                            original_question=task,
                            report_data=cached_payload["report"],
                            conversation_history=[],
                            user_id=user_id
                        )
                return jsonify(cached_payload), 200

    # 2. Concurrent Request Deduplication (Join in-flight execution if identical)
    need_wait = False
    with report_lock:
        if not force_refresh and norm_query in active_report_requests:
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
            res_payload = json.loads(json.dumps(res_data[0]))
            res_payload["conversation_id"] = conversation_id
            if user_id and isinstance(res_payload.get("report"), dict):
                report_db.save_report(
                    report_id=conversation_id,
                    original_question=task,
                    report_data=res_payload["report"],
                    conversation_history=[],
                    user_id=user_id
                )
            return jsonify(res_payload), res_data[1]

    # 3. Execute LangGraph Workflow
    try:
        print("\n" + "=" * 60)
        print(f"LANGGRAPH MULTI-AGENT ENGINE [ID: {conversation_id}] (force_refresh={force_refresh}, user_id={user_id})")
        print("=" * 60)
        print("Query:", task)

        initial_state = {
            "task": task,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "force_refresh": force_refresh,
            "selected_tool": None,
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
        agent_statuses = final_state.get("agent_statuses") or {}
        workflow_status = final_state.get("workflow_status", "completed")

        # Check if AI analysis failed or was unavailable
        if not report or (isinstance(report, dict) and report.get("success") is False):
            err_status = report.get("status", "temporary_ai_unavailable") if isinstance(report, dict) else "temporary_ai_unavailable"
            err_msg = report.get("message") if isinstance(report, dict) and report.get("message") else "The AI analysis service is temporarily busy. Please try again in a moment."
            retry_sec = report.get("retry_after_seconds", 15) if isinstance(report, dict) else 15
            raw_err = report.get("error") if isinstance(report, dict) else "AI service unavailable"

            if err_status == "rate_limited" or gemini_client.quota_exhausted:
                http_code = 429
                err_payload = {
                    "success": False,
                    "status": "rate_limited",
                    "message": "AI request rate limit reached. Please wait a moment before retrying.",
                    "retry_after_seconds": 30,
                    "error": raw_err
                }
            elif err_status == "configuration_error" or not gemini_client.gemini_available:
                http_code = 500
                err_payload = {
                    "success": False,
                    "status": "configuration_error",
                    "message": "Gemini API configuration or authentication error. Please check your API key.",
                    "retry_after_seconds": None,
                    "error": raw_err
                }
            else:
                http_code = 503
                err_payload = {
                    "success": False,
                    "status": "temporary_ai_unavailable",
                    "message": err_msg,
                    "retry_after_seconds": retry_sec,
                    "error": raw_err
                }

            with report_lock:
                holder["response_data"] = (err_payload, http_code)
                event.set()
                active_report_requests.pop(norm_query, None)

            return jsonify(err_payload), http_code

        print("\n[LangGraph] Workflow Completed Successfully.")

        response_payload = {
            "success": True,
            "task": task,
            "conversation_id": conversation_id,
            "report": report,
            "workflow": {
                "status": "completed",
                "agent_statuses": agent_statuses,
                "metrics": final_state.get("execution_metrics")
            }
        }

        # Cache ONLY genuine successful live reports
        with report_lock:
            report_cache[norm_query] = response_payload
            holder["response_data"] = (response_payload, 200)
            event.set()
            active_report_requests.pop(norm_query, None)

        return jsonify(response_payload), 200

    except Exception as e:
        err_str = str(e)
        print("\n[LangGraph ERROR] Generating Report:", repr(e))

        err_payload = {
            "success": False,
            "status": "temporary_ai_unavailable",
            "message": "The AI analysis service is temporarily busy. Please try again in a moment.",
            "retry_after_seconds": 15,
            "error": err_str
        }

        with report_lock:
            holder["response_data"] = (err_payload, 503)
            event.set()
            active_report_requests.pop(norm_query, None)

        return jsonify(err_payload), 503



# ============================================================
# LANGGRAPH DYNAMIC FOLLOW-UP QUESTION
# ============================================================

@app.route("/follow-up", methods=["POST"])
@optional_auth
def follow_up():
    try:
        data = request.get_json(silent=True) or {}

        question = data.get("question", "").strip()
        conversation_id = data.get("conversation_id")
        original_task = data.get("original_task", "")
        report = data.get("report")
        user_id = getattr(request, "user_id", None)

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
            "user_id": user_id,
            "force_refresh": False,
            "selected_tool": None,
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

        return jsonify({
            "success": False,
            "error": f"Failed to process follow-up: {err_str}",
            "conversation_id": conversation_id
        }), 500


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
    except Exception:
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
            f"After accounting for monthly fixed overhead ({format_inr(fixed_cost)}), variable expenses ({format_inr(monthly_variable)}), and marketing ({format_inr(marketing_cost)}), "
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
@require_auth
def get_reports_library():
    try:
        search = request.args.get("search", "").strip()
        risk_filter = request.args.get("risk", "ALL").strip()
        user_id = request.user_id
        reports = report_db.list_reports(search=search, risk_filter=risk_filter, user_id=user_id)
        return jsonify({"success": True, "reports": reports}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/<report_id>", methods=["GET"])
@require_auth
def get_single_report(report_id):
    try:
        user_id = request.user_id
        r = report_db.get_report(report_id, user_id=user_id)
        if not r:
            return jsonify({"success": False, "error": "Report not found"}), 404
        return jsonify({"success": True, "report": r}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/<report_id>", methods=["DELETE"])
@require_auth
def delete_single_report(report_id):
    try:
        user_id = request.user_id
        ok = report_db.delete_report(report_id, user_id=user_id)
        if not ok:
            return jsonify({"success": False, "error": "Report not found or could not be deleted"}), 404
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reports/compare", methods=["GET"])
@require_auth
def compare_reports():
    try:
        id1 = request.args.get("id1", "").strip()
        id2 = request.args.get("id2", "").strip()
        if not id1 or not id2:
            return jsonify({"success": False, "error": "Two report IDs are required for comparison."}), 400

        user_id = request.user_id
        r1 = report_db.get_report(id1, user_id=user_id)
        r2 = report_db.get_report(id2, user_id=user_id)

        if not r1 or not r2:
            return jsonify({"success": False, "error": "One or both reports could not be found."}), 404

        return jsonify({
            "success": True,
            "report1": r1,
            "report2": r2
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/re-run-decision", methods=["POST"])
@require_auth
def rerun_decision_stage():
    try:
        data = request.get_json(silent=True) or {}
        task = data.get("task", "")
        report_id = data.get("report_id") or str(uuid.uuid4())
        user_id = request.user_id

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
        existing_report = report_db.get_report(report_id, user_id=user_id)
        research_context = {"executive_summary": "Market demand validated for segment."}
        planning_context = []

        if existing_report and existing_report.get("report_data"):
            r_data = existing_report["report_data"]
            if isinstance(r_data, dict):
                research_context = r_data
                planning_context = r_data.get("implementation_roadmap", [])

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
            "recommended_decision": new_decision.get("recommended_decision", ""),
            "implementation_roadmap": new_decision.get("implementation_roadmap", planning_context),
            "success_metrics": new_decision.get("success_metrics", []),
            "conditions_and_assumptions": new_decision.get("conditions_and_assumptions", []),
            "conclusion": new_decision.get("conclusion", ""),
            "tool_analysis": updated_tool_result,
            "analysis_source": "LIVE_AI"
        }

        report_db.save_report(
            report_id=report_id,
            original_question=task,
            report_data=updated_report_data,
            conversation_history=existing_report.get("conversation_history", []) if existing_report else [],
            user_id=user_id
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
@optional_auth
def export_report():
    try:
        data = request.get_json(silent=True) or {}
        export_format = data.get("format", "pdf").lower()
        report = data.get("report") or {}
        task = data.get("task", "Business Decision Query")
        history = data.get("conversation_history", [])
        report_id = data.get("report_id")
        user_id = getattr(request, "user_id", None)

        if report_id and user_id:
            db_rep = report_db.get_report(report_id, user_id=user_id)
            if not db_rep:
                return jsonify({"success": False, "error": "Report not found"}), 404

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
# GET DECISION HISTORY
# ============================================================

@app.route("/history", methods=["GET"])
@optional_auth
def get_history():
    try:
        user_id = getattr(request, "user_id", None)
        if user_id:
            reports = report_db.list_reports(user_id=user_id)
        else:
            reports = report_db.list_reports(include_all=True)
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
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    host = os.getenv("HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
    app.run(
        debug=debug_mode,
        host=host,
        port=port
    )
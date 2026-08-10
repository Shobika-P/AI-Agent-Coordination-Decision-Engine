import os
import uuid
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from graph.decision_graph import report_workflow, followup_workflow
from utils.pdf_generator import generate_decision_pdf
from memory.shared_memory import SharedMemory

app = Flask(__name__)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, origins=allowed_origins)

memory = SharedMemory()


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "AI Business Decision Engine",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "orchestration": "LangGraph StateGraph"
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
    try:
        data = request.get_json(silent=True) or {}
        task = data.get("task", "").strip()
        conversation_id = data.get("conversation_id") or str(uuid.uuid4())

        if not task:
            return jsonify({
                "success": False,
                "error": "Business problem is required."
            }), 400

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

        # Run LangGraph StateGraph Execution
        final_state = report_workflow.invoke(initial_state)

        report = final_state.get("final_report")
        agent_statuses = final_state.get("agent_statuses")

        print("\n[LangGraph] Workflow Completed Successfully.")

        return jsonify({
            "success": True,
            "task": task,
            "conversation_id": conversation_id,
            "report": report,
            "workflow": {
                "status": final_state.get("workflow_status", "completed"),
                "agent_statuses": agent_statuses,
                "metrics": final_state.get("execution_metrics")
            }
        }), 200

    except Exception as e:
        err_str = str(e)
        print("\n[LangGraph ERROR] Generating Report:", repr(e))

        status_code = 500
        if "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str or "rate limit" in err_str.lower():
            err_str = "AI service quota/rate limit reached. Please try again later."
            status_code = 429

        return jsonify({
            "success": False,
            "error": err_str
        }), status_code


# ============================================================
# LANGGRAPH FOLLOW-UP QUESTION
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

        print("\n============================================================")
        print("LANGGRAPH USER FOLLOW-UP")
        print("============================================================")
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
            "conversation_history": [],
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

        status_code = 500
        if "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str or "rate limit" in err_str.lower():
            err_str = "AI service quota/rate limit reached. Please try again later."
            status_code = 429

        return jsonify({
            "success": False,
            "error": err_str
        }), status_code


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
            md_content = f"# Executive Decision Report\n\n**Query:** {task}\n**Risk Level:** {risk}\n\n---\n\n## Recommendation & Analysis\n\n{decision_text}\n"

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
def get_history():
    try:
        history = memory.get_history()
        return jsonify({
            "success": True,
            "history": history
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
        host="0.0.0.1" if os.getenv("PORT") else "127.0.0.1",
        port=port
    )
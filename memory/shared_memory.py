import os
from memory.report_db import report_db
from utils.gemini_client import gemini_client


class SharedMemory:
    """
    Manages short-term exchange memory, active session conversation states,
    and system telemetry monitoring.
    """

    def __init__(self):
        self.memory = {}
        self.sessions = {}
        self.report_db = report_db

    # ------------------------
    # Short-Term Node Exchange Memory
    # ------------------------

    def save(self, key, value):
        self.memory[key] = value

    def load(self, key):
        return self.memory.get(key)

    # ------------------------
    # Session / Conversation Memory (Per conversation_id)
    # ------------------------

    def save_session(self, conversation_id, session_data):
        if conversation_id:
            self.sessions[conversation_id] = session_data

    def load_session(self, conversation_id):
        if not conversation_id:
            return None

        # Check active in-memory session first
        if conversation_id in self.sessions:
            return self.sessions[conversation_id]

        # Load from SQLite database if not in active memory
        db_report = self.report_db.get_report(conversation_id)
        if db_report:
            session_data = {
                "task": db_report.get("original_question"),
                "report": db_report.get("report_data"),
                "conversation_history": db_report.get("conversation_history", [])
            }
            self.sessions[conversation_id] = session_data
            return session_data

        return None

    # ------------------------
    # Persistent History Bridge
    # ------------------------

    def add_history(self, task, decision, risk_level="Medium", report_data=None, conversation_id=None, user_id=None):
        report_data = report_data or {"decision": decision, "risk_level": risk_level}
        return self.report_db.save_report(
            report_id=conversation_id,
            original_question=task,
            report_data=report_data,
            user_id=user_id
        )

    def get_history(self, user_id=None, include_all=False):
        return self.report_db.list_reports(user_id=user_id, include_all=include_all)

    # ------------------------
    # Monitoring Telemetry Metrics
    # ------------------------

    def get_monitoring_metrics(self):
        history = self.get_history()
        total_decisions = len(history)
        active_sessions = len(self.sessions)
        ai_telemetry = gemini_client.get_telemetry_metrics()
        status = ai_telemetry.get("status", "LIVE")

        return {
            "total_decisions": total_decisions,
            "active_workflows": 0,
            "completed_workflows": total_decisions,
            "failed_workflows": ai_telemetry.get("failed_requests", 0),
            "active_sessions": active_sessions,
            "gemini_telemetry": ai_telemetry,
            "agent_statuses": {
                "business_tool": "OPERATIONAL",
                "research_agent": "OPERATIONAL" if status == "LIVE" else status,
                "planning_agent": "OPERATIONAL",
                "decision_agent": "OPERATIONAL",
                "followup_agent": "OPERATIONAL"
            },
            "api_status": status,
            "model_status": status
        }
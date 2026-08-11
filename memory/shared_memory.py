import datetime
import json
import os
from memory.report_db import report_db
from utils.gemini_client import gemini_client

class SharedMemory:

    def __init__(self):
        self.memory = {}
        self.sessions = {}
        self.report_db = report_db

    # ------------------------
    # Short-Term & Key Memory
    # ------------------------

    def save(self, key, value):
        self.memory[key] = value

    def load(self, key):
        return self.memory.get(key)

    # ------------------------
    # Session / Conversation Memory
    # ------------------------

    def save_session(self, conversation_id, session_data):
        self.sessions[conversation_id] = session_data

    def load_session(self, conversation_id):
        # Try in-memory active session first, then SQLite DB
        if conversation_id in self.sessions:
            return self.sessions[conversation_id]
        
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
    # Long-Term Decision Log Memory
    # ------------------------

    def add_history(self, task, decision, risk_level="Unknown", report_data=None, conversation_id=None):
        report_data = report_data or {"decision": decision, "risk_level": risk_level}
        return self.report_db.save_report(
            report_id=conversation_id,
            original_question=task,
            report_data=report_data
        )

    def get_history(self):
        return self.report_db.list_reports()

    # ------------------------
    # Monitoring Telemetry Metrics
    # ------------------------

    def get_monitoring_metrics(self):
        history = self.get_history()
        total_decisions = len(history)
        active_sessions = len(self.sessions)
        ai_telemetry = gemini_client.get_telemetry_metrics()

        return {
            "total_decisions": total_decisions,
            "active_workflows": 0,
            "completed_workflows": total_decisions,
            "failed_workflows": 0,
            "active_sessions": active_sessions,
            "gemini_telemetry": ai_telemetry,
            "agent_statuses": {
                "business_tool": "OPERATIONAL",
                "research_agent": "OPERATIONAL",
                "planning_agent": "OPERATIONAL",
                "decision_agent": "OPERATIONAL",
                "followup_agent": "OPERATIONAL"
            },
            "api_status": "online",
            "model_status": "operational" if not ai_telemetry.get("quota_exhausted") else "demo_fallback"
        }
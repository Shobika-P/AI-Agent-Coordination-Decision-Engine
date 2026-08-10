import datetime
import json
import os


class SharedMemory:

    def __init__(self):
        self.memory = {}
        self.sessions = {}
        self.history_file = "memory/history.json"

        # Create history file directory and file if missing
        os.makedirs("memory", exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w") as file:
                json.dump([], file)

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
        return self.sessions.get(conversation_id)

    # ------------------------
    # Long-Term Decision Log Memory
    # ------------------------

    def add_history(self, task, decision, risk_level="Unknown"):
        history = self.get_history()

        history.append({
            "task": task,
            "decision": decision,
            "risk_level": risk_level,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

        try:
            with open(self.history_file, "w") as file:
                json.dump(history, file, indent=4)
        except Exception as e:
            print("Error writing history file:", e)

    def get_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as file:
                    return json.load(file)
        except Exception as e:
            print("Error reading history file:", e)
        return []

    # ------------------------
    # Monitoring Telemetry Metrics
    # ------------------------

    def get_monitoring_metrics(self):
        history = self.get_history()
        total_decisions = len(history)
        active_sessions = len(self.sessions)

        return {
            "total_decisions": total_decisions,
            "active_workflows": 0,
            "completed_workflows": total_decisions,
            "failed_workflows": 0,
            "active_sessions": active_sessions,
            "agent_statuses": {
                "business_tool": "OPERATIONAL",
                "research_agent": "OPERATIONAL",
                "planning_agent": "OPERATIONAL",
                "decision_agent": "OPERATIONAL",
                "followup_agent": "OPERATIONAL"
            },
            "api_status": "online",
            "model_status": "operational"
        }
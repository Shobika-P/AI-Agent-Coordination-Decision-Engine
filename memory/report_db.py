import sqlite3
import json
import os
import datetime
import uuid

DB_PATH = os.path.join("memory", "decision_engine.db")

class ReportDatabase:
    """
    SQLite Database Manager for persistent Report Library, Decision History,
    and Follow-up Conversation Threads.
    """
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    original_question TEXT NOT NULL,
                    decision TEXT,
                    risk_level TEXT DEFAULT 'Medium',
                    viability_score INTEGER DEFAULT 75,
                    confidence INTEGER DEFAULT 80,
                    report_data TEXT,
                    conversation_history TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def generate_title(self, question: str) -> str:
        """Automatically generates a concise title from the business question."""
        clean_q = question.strip()
        # Remove common prefixes
        for prefix in ["should we", "how can we", "what is the", "is it profitable to", "can we", "would it be good to"]:
            if clean_q.lower().startswith(prefix):
                clean_q = clean_q[len(prefix):].strip()
                break
        
        # Capitalize and truncate
        words = clean_q.split()
        if len(words) > 7:
            short_title = " ".join(words[:7]).strip("?,.!") + "..."
        else:
            short_title = clean_q.strip("?,.!")

        if not short_title:
            return "Business Decision Analysis"

        return f"{short_title.capitalize()} — Launch Assessment"

    def save_report(self, report_id: str, original_question: str, report_data: dict, conversation_history: list = None) -> dict:
        if not report_id:
            report_id = str(uuid.uuid4())

        title = self.generate_title(original_question)
        decision_text = str(report_data.get("decision", ""))
        risk_level = report_data.get("risk_level") or report_data.get("tool_analysis", {}).get("risk_level", "Medium")
        viability_score = report_data.get("viability_score", 78)
        confidence = report_data.get("confidence", 82)

        report_json = json.dumps(report_data)
        conv_json = json.dumps(conversation_history or [])
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reports (
                    report_id, title, original_question, decision, risk_level,
                    viability_score, confidence, report_data, conversation_history, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                    decision = excluded.decision,
                    risk_level = excluded.risk_level,
                    viability_score = excluded.viability_score,
                    confidence = excluded.confidence,
                    report_data = excluded.report_data,
                    conversation_history = excluded.conversation_history,
                    updated_at = excluded.updated_at
            """, (
                report_id, title, original_question, decision_text, risk_level,
                viability_score, confidence, report_json, conv_json, now_str, now_str
            ))
            conn.commit()

        return {
            "report_id": report_id,
            "title": title,
            "original_question": original_question,
            "risk_level": risk_level,
            "viability_score": viability_score,
            "confidence": confidence,
            "created_at": now_str
        }

    def get_report(self, report_id: str) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            d = dict(row)
            d["report_data"] = json.loads(d["report_data"]) if d["report_data"] else {}
            d["conversation_history"] = json.loads(d["conversation_history"]) if d["conversation_history"] else []
            return d

    def list_reports(self, search: str = "", risk_filter: str = "ALL") -> list:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT report_id, title, original_question, decision, risk_level, viability_score, confidence, created_at FROM reports WHERE 1=1"
            params = []

            if search:
                query += " AND (title LIKE ? OR original_question LIKE ? OR decision LIKE ?)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])

            if risk_filter and risk_filter.upper() != "ALL":
                query += " AND UPPER(risk_level) = ?"
                params.append(risk_filter.upper())

            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def update_conversation(self, report_id: str, conversation_history: list) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            conv_json = json.dumps(conversation_history)
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute("""
                UPDATE reports SET conversation_history = ?, updated_at = ? WHERE report_id = ?
            """, (conv_json, now_str, report_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_report(self, report_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
            conn.commit()
            return cursor.rowcount > 0

# Singleton DB Instance
report_db = ReportDatabase()

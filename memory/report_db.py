import sqlite3
import json
import os
import datetime
import uuid
import re
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join("memory", "decision_engine.db")


class ReportDatabase:
    """
    SQLite Database Manager for persistent User Authentication, Report Library,
    Decision History, and Follow-up Conversation Threads.
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
            # 1. Create Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

            # 2. Create Reports Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    user_id TEXT DEFAULT NULL,
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

            # 3. Safe Column Migration: ensure user_id exists in existing reports table
            cursor.execute("PRAGMA table_info(reports)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE reports ADD COLUMN user_id TEXT DEFAULT NULL")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id)")
            conn.commit()

    # ============================================================
    # USER AUTHENTICATION & MANAGEMENT
    # ============================================================

    def create_user(self, email: str, password: str) -> dict:
        """Creates a new user account with validated email and secure password hash."""
        email_clean = (email or "").strip().lower()
        if not email_clean or not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email_clean):
            raise ValueError("Invalid email format.")

        if not password or len(str(password)) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
            if cursor.fetchone():
                raise ValueError("An account with this email already exists.")

            user_id = str(uuid.uuid4())
            pw_hash = generate_password_hash(password)
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

            cursor.execute(
                "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email_clean, pw_hash, now_str)
            )
            conn.commit()

            return {
                "id": user_id,
                "email": email_clean,
                "created_at": now_str
            }

    def authenticate_user(self, email: str, password: str) -> dict | None:
        """Verifies email and password securely against password hash."""
        email_clean = (email or "").strip().lower()
        if not email_clean or not password:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, password_hash, created_at FROM users WHERE email = ?", (email_clean,))
            row = cursor.fetchone()
            if not row:
                return None

            if check_password_hash(row["password_hash"], password):
                return {
                    "id": row["id"],
                    "email": row["email"],
                    "created_at": row["created_at"]
                }
            return None

    def get_user_by_id(self, user_id: str) -> dict | None:
        """Retrieves user details by user ID without exposing password hash."""
        if not user_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict | None:
        """Retrieves user details by email without exposing password hash."""
        email_clean = (email or "").strip().lower()
        if not email_clean:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, created_at FROM users WHERE email = ?", (email_clean,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ============================================================
    # REPORT STORAGE & USER ISOLATION
    # ============================================================

    def generate_title(self, question: str) -> str:
        """Generates a concise title from the business question."""
        clean_q = question.strip()
        for prefix in ["should we", "how can we", "what is the", "is it profitable to", "can we", "would it be good to"]:
            if clean_q.lower().startswith(prefix):
                clean_q = clean_q[len(prefix):].strip()
                break

        words = clean_q.split()
        if len(words) > 7:
            short_title = " ".join(words[:7]).strip("?,.!") + "..."
        else:
            short_title = clean_q.strip("?,.!")

        if not short_title:
            return "Business Decision Analysis"

        return f"{short_title.capitalize()} — Launch Assessment"

    def save_report(self, report_id: str, original_question: str, report_data: dict, conversation_history: list = None, user_id: str = None) -> dict:
        """Saves or updates a decision report, attaching user_id ownership."""
        if not report_id:
            report_id = str(uuid.uuid4())

        title = self.generate_title(original_question)
        decision_text = str(report_data.get("decision", ""))
        risk_level = report_data.get("risk_level") or report_data.get("tool_analysis", {}).get("risk_level", "Medium")
        viability_score = int(report_data.get("viability_score", 78))
        confidence = int(report_data.get("confidence", 82))

        report_json = json.dumps(report_data)
        conv_json = json.dumps(conversation_history or [])
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reports (
                    report_id, user_id, title, original_question, decision, risk_level,
                    viability_score, confidence, report_data, conversation_history, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                    user_id = COALESCE(excluded.user_id, reports.user_id),
                    decision = excluded.decision,
                    risk_level = excluded.risk_level,
                    viability_score = excluded.viability_score,
                    confidence = excluded.confidence,
                    report_data = excluded.report_data,
                    conversation_history = excluded.conversation_history,
                    updated_at = excluded.updated_at
            """, (
                report_id, user_id, title, original_question, decision_text, risk_level,
                viability_score, confidence, report_json, conv_json, now_str, now_str
            ))
            conn.commit()

        return {
            "report_id": report_id,
            "user_id": user_id,
            "title": title,
            "original_question": original_question,
            "risk_level": risk_level,
            "viability_score": viability_score,
            "confidence": confidence,
            "created_at": now_str
        }

    def get_report(self, report_id: str, user_id: str = None) -> dict | None:
        """Retrieves a single report. If user_id is provided, enforces user ownership."""
        if not report_id:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("SELECT * FROM reports WHERE report_id = ? AND user_id = ?", (report_id, user_id))
            else:
                cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))

            row = cursor.fetchone()
            if not row:
                return None

            d = dict(row)
            try:
                d["report_data"] = json.loads(d["report_data"]) if d["report_data"] else {}
            except Exception:
                d["report_data"] = {}
            try:
                d["conversation_history"] = json.loads(d["conversation_history"]) if d["conversation_history"] else []
            except Exception:
                d["conversation_history"] = []
            return d

    def list_reports(self, search: str = "", risk_filter: str = "ALL", user_id: str = None, include_all: bool = False) -> list:
        """Lists reports filtered strictly by user_id ownership and search/risk criteria."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT report_id, user_id, title, original_question, decision, risk_level, viability_score, confidence, created_at FROM reports WHERE 1=1"
            params = []

            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)
            elif not include_all:
                # If no user_id is specified and include_all is False, only show unassigned/legacy
                query += " AND user_id IS NULL"

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

    def update_conversation(self, report_id: str, conversation_history: list, user_id: str = None) -> bool:
        """Updates follow-up conversation history with optional ownership check."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            conv_json = json.dumps(conversation_history)
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if user_id is not None:
                cursor.execute("""
                    UPDATE reports SET conversation_history = ?, updated_at = ? WHERE report_id = ? AND user_id = ?
                """, (conv_json, now_str, report_id, user_id))
            else:
                cursor.execute("""
                    UPDATE reports SET conversation_history = ?, updated_at = ? WHERE report_id = ?
                """, (conv_json, now_str, report_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_report(self, report_id: str, user_id: str = None) -> bool:
        """Deletes a report with optional user_id ownership check."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("DELETE FROM reports WHERE report_id = ? AND user_id = ?", (report_id, user_id))
            else:
                cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
            conn.commit()
            return cursor.rowcount > 0


# Singleton DB Instance
report_db = ReportDatabase()


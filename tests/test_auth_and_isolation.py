import sys
import os
import time
import json
import sqlite3

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app as flask_app
from memory.report_db import report_db
from werkzeug.security import check_password_hash


def run_auth_and_isolation_test_suite():
    print("=" * 80)
    print("   AUTHENTICATION & USER REPORT ISOLATION TEST SUITE")
    print("=" * 80)

    client = flask_app.test_client()

    # Generate unique test email addresses
    ts = int(time.time() * 1000)
    email_a = f"usera_{ts}@example.com"
    email_b = f"userb_{ts}@example.com"
    password_a = "PasswordA123!"
    password_b = "PasswordB456!"

    # ------------------------------------------------------------
    # 1. REGISTER NEW USER (USER A)
    # ------------------------------------------------------------
    print("\n--- TEST 1: Register New User (User A) ---")
    res_reg_a = client.post("/register", json={"email": email_a, "password": password_a})
    assert res_reg_a.status_code == 201, f"Expected 201, got {res_reg_a.status_code}: {res_reg_a.get_json()}"
    d_reg_a = res_reg_a.get_json()
    assert d_reg_a.get("success") is True
    assert "token" in d_reg_a
    assert d_reg_a.get("user", {}).get("email") == email_a
    token_a = d_reg_a["token"]
    user_a_id = d_reg_a["user"]["id"]
    print(f"[TEST 1 PASSED] Registered User A successfully. ID: {user_a_id}, Email: {email_a}")

    # ------------------------------------------------------------
    # 2. PREVENT DUPLICATE EMAIL REGISTRATION
    # ------------------------------------------------------------
    print("\n--- TEST 2: Prevent Duplicate Email Registration ---")
    res_dup = client.post("/register", json={"email": email_a, "password": "differentPassword999"})
    assert res_dup.status_code == 400, f"Expected 400 for duplicate email, got {res_dup.status_code}"
    d_dup = res_dup.get_json()
    assert d_dup.get("success") is False
    assert "already exists" in d_dup.get("error", "").lower()
    print("[TEST 2 PASSED] Duplicate email registration was properly blocked.")

    # ------------------------------------------------------------
    # 3. VERIFY PASSWORD IS NEVER STORED AS PLAIN TEXT
    # ------------------------------------------------------------
    print("\n--- TEST 3: Verify Password is Stored as Secure Hash ---")
    with sqlite3.connect(report_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE id = ?", (user_a_id,))
        row = c.fetchone()
        assert row is not None
        stored_hash = row["password_hash"]
        assert stored_hash != password_a, "Password must not be stored in plain text!"
        assert check_password_hash(stored_hash, password_a) is True, "Hash must match original password"
        assert check_password_hash(stored_hash, "wrongpassword") is False
        print(f"[TEST 3 PASSED] Stored password is a valid secure hash: {stored_hash[:30]}...")

    # ------------------------------------------------------------
    # 4. LOGIN WITH VALID CREDENTIALS
    # ------------------------------------------------------------
    print("\n--- TEST 4: Login with Valid Credentials ---")
    res_login_a = client.post("/login", json={"email": email_a, "password": password_a})
    assert res_login_a.status_code == 200
    d_login_a = res_login_a.get_json()
    assert d_login_a.get("success") is True
    assert "token" in d_login_a
    assert d_login_a.get("user", {}).get("email") == email_a
    print("[TEST 4 PASSED] Login with valid credentials returned auth token and user object.")

    # ------------------------------------------------------------
    # 5. REJECT INVALID CREDENTIALS
    # ------------------------------------------------------------
    print("\n--- TEST 5: Reject Invalid Credentials ---")
    res_bad_pw = client.post("/login", json={"email": email_a, "password": "WrongPassword123"})
    assert res_bad_pw.status_code == 401
    assert res_bad_pw.get_json().get("success") is False
    assert "invalid email or password" in res_bad_pw.get_json().get("error", "").lower()

    res_bad_email = client.post("/login", json={"email": "nonexistent@example.com", "password": password_a})
    assert res_bad_email.status_code == 401
    assert res_bad_email.get_json().get("success") is False
    print("[TEST 5 PASSED] Invalid login attempts safely rejected with 401 and generic error.")

    # ------------------------------------------------------------
    # 6. AUTHENTICATED USER PROFILE CHECK (GET /auth/me)
    # ------------------------------------------------------------
    print("\n--- TEST 6: Authenticated User Profile Check (GET /auth/me) ---")
    res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res_me.status_code == 200
    d_me = res_me.get_json()
    assert d_me.get("success") is True
    assert d_me.get("user", {}).get("id") == user_a_id
    assert d_me.get("user", {}).get("email") == email_a

    # Unauthenticated request to /auth/me
    res_me_unauth = client.get("/auth/me")
    assert res_me_unauth.status_code == 401
    print("[TEST 6 PASSED] GET /auth/me verifies valid token and rejects unauthenticated requests.")

    # ------------------------------------------------------------
    # 7. LOGOUT ENDPOINT
    # ------------------------------------------------------------
    print("\n--- TEST 7: Logout Endpoint ---")
    res_logout = client.post("/logout", headers={"Authorization": f"Bearer {token_a}"})
    assert res_logout.status_code == 200
    assert res_logout.get_json().get("success") is True
    print("[TEST 7 PASSED] POST /logout returned HTTP 200.")

    # ------------------------------------------------------------
    # 8. REGISTER USER B
    # ------------------------------------------------------------
    print("\n--- TEST 8: Register User B ---")
    res_reg_b = client.post("/register", json={"email": email_b, "password": password_b})
    assert res_reg_b.status_code == 201
    d_reg_b = res_reg_b.get_json()
    token_b = d_reg_b["token"]
    user_b_id = d_reg_b["user"]["id"]
    print(f"[TEST 8 PASSED] Registered User B. ID: {user_b_id}, Email: {email_b}")

    # ------------------------------------------------------------
    # 9. USER A CREATES REPORT A & USER B CREATES REPORT B
    # ------------------------------------------------------------
    print("\n--- TEST 9: User Report Creation with Ownership Scoping ---")
    rep_a_id = f"rep_a_{ts}"
    rep_b_id = f"rep_b_{ts}"

    report_db.save_report(
        report_id=rep_a_id,
        original_question="User A Query: Autonomous Logistics AI Strategy",
        report_data={"decision": "Deploy AI in hubs", "risk_level": "Low", "viability_score": 88},
        conversation_history=[],
        user_id=user_a_id
    )

    report_db.save_report(
        report_id=rep_b_id,
        original_question="User B Query: Dark Kitchen Expansion in Tier 2 Cities",
        report_data={"decision": "Expand to Jaipur", "risk_level": "Medium", "viability_score": 76},
        conversation_history=[],
        user_id=user_b_id
    )
    print("[TEST 9 PASSED] Created Report A (owned by User A) and Report B (owned by User B).")

    # ------------------------------------------------------------
    # 10. USER A SEES ONLY REPORT A & USER B SEES ONLY REPORT B
    # ------------------------------------------------------------
    print("\n--- TEST 10: Server-Side Report Isolation in List Reports ---")
    res_list_a = client.get("/reports", headers={"Authorization": f"Bearer {token_a}"})
    assert res_list_a.status_code == 200
    reports_a = res_list_a.get_json().get("reports", [])
    report_ids_a = [r["report_id"] for r in reports_a]

    assert rep_a_id in report_ids_a, "User A must see Report A"
    assert rep_b_id not in report_ids_a, "User A must NEVER see Report B"

    res_list_b = client.get("/reports", headers={"Authorization": f"Bearer {token_b}"})
    assert res_list_b.status_code == 200
    reports_b = res_list_b.get_json().get("reports", [])
    report_ids_b = [r["report_id"] for r in reports_b]

    assert rep_b_id in report_ids_b, "User B must see Report B"
    assert rep_a_id not in report_ids_b, "User B must NEVER see Report A"
    print(f"[TEST 10 PASSED] User A sees {len(reports_a)} reports (only owned), User B sees {len(reports_b)} reports (only owned).")

    # ------------------------------------------------------------
    # 11. USER A CANNOT ACCESS USER B'S REPORT BY CHANGING REPORT ID
    # ------------------------------------------------------------
    print("\n--- TEST 11: Cross-User ID Access Prevention (GET & DELETE) ---")
    # User A tries to get User B's report
    res_cross_get = client.get(f"/reports/{rep_b_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_cross_get.status_code == 404, f"Expected 404 for cross-user report get, got {res_cross_get.status_code}"
    assert res_cross_get.get_json().get("success") is False

    # User A tries to delete User B's report
    res_cross_del = client.delete(f"/reports/{rep_b_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_cross_del.status_code == 404, f"Expected 404 for cross-user report delete, got {res_cross_del.status_code}"
    assert res_cross_del.get_json().get("success") is False

    # Verify Report B still exists in database
    rep_b_check = report_db.get_report(rep_b_id, user_id=user_b_id)
    assert rep_b_check is not None, "Report B should not have been deleted"

    # User B can access their own report
    res_b_own_get = client.get(f"/reports/{rep_b_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_own_get.status_code == 200
    assert res_b_own_get.get_json().get("report", {}).get("report_id") == rep_b_id
    print("[TEST 11 PASSED] User A cannot access or delete User B's report by changing IDs.")

    # ------------------------------------------------------------
    # 12. FOLLOW-UP CONVERSATION HISTORY ISOLATION
    # ------------------------------------------------------------
    print("\n--- TEST 12: Follow-up Conversation History Isolation ---")
    conv_history_a = [
        {"question": "What is the capital requirement?", "answer": "Estimated ₹50,000 upfront fixed overhead."},
        {"question": "How soon to break even?", "answer": "Break-even projected at 250 units."}
    ]
    report_db.update_conversation(rep_a_id, conv_history_a, user_id=user_a_id)

    # User A retrieves own report with conversation history
    res_a_conv = client.get(f"/reports/{rep_a_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a_conv.status_code == 200
    fetched_history_a = res_a_conv.get_json().get("report", {}).get("conversation_history", [])
    assert len(fetched_history_a) == 2
    assert fetched_history_a[0]["question"] == "What is the capital requirement?"

    # User B retrieves own report -> has empty history, not User A's history
    res_b_conv = client.get(f"/reports/{rep_b_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_conv.status_code == 200
    fetched_history_b = res_b_conv.get_json().get("report", {}).get("conversation_history", [])
    assert len(fetched_history_b) == 0
    print("[TEST 12 PASSED] Follow-up conversation history is completely isolated per user.")

    # ------------------------------------------------------------
    # 13. RETURNING USER PERSISTENCE
    # ------------------------------------------------------------
    print("\n--- TEST 13: Returning User Token Verification & Persistence ---")
    # Simulate returning user visiting again with stored token
    res_returning = client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res_returning.status_code == 200
    assert res_returning.get_json().get("user", {}).get("id") == user_a_id
    assert res_returning.get_json().get("user", {}).get("email") == email_a

    # User A accesses library on return
    res_ret_lib = client.get("/reports", headers={"Authorization": f"Bearer {token_a}"})
    assert res_ret_lib.status_code == 200
    ret_reports = res_ret_lib.get_json().get("reports", [])
    assert any(r["report_id"] == rep_a_id for r in ret_reports)
    print("[TEST 13 PASSED] Returning user is instantly authenticated and loads only their persistent reports.")

    # ------------------------------------------------------------
    # CLEANUP TEST DATA
    # ------------------------------------------------------------
    report_db.delete_report(rep_a_id, user_id=user_a_id)
    report_db.delete_report(rep_b_id, user_id=user_b_id)
    with sqlite3.connect(report_db.db_path) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id IN (?, ?)", (user_a_id, user_b_id))
        conn.commit()

    print("\n" + "=" * 80)
    print("   ALL 13 AUTHENTICATION & USER ISOLATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_auth_and_isolation_test_suite()

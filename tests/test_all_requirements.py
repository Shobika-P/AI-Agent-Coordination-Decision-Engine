import sys
import os
import time
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app as flask_app
from utils.gemini_client import gemini_client
from tools.break_even_tool import calculate_break_even
from memory.report_db import report_db


def run_comprehensive_validation_suite():
    print("=" * 80)
    print("   COMPREHENSIVE VALIDATION SUITE: ENTERPRISE DECISION AUTOMATION SYSTEM")
    print("=" * 80)

    client = flask_app.test_client()

    # TEST 1: New arbitrary startup/business query
    print("\n--- TEST 1: New Arbitrary Business Query ---")
    q1 = "Should an enterprise launch an autonomous AI agent workflow for supply chain logistics?"
    t0 = time.time()
    res1 = client.post("/generate-report", json={"task": q1, "force_refresh": True})
    elapsed1 = time.time() - t0
    d1 = res1.get_json()

    assert res1.status_code == 200, f"Failed: {d1}"
    assert d1.get("success") is True, "Expected success=True"
    report1 = d1.get("report") or {}
    source1 = report1.get("analysis_source")
    print(f"[TEST 1 PASSED] Generated in {elapsed1:.2f}s | Source: {source1}")
    print(f"  Decision summary: {str(report1.get('decision'))[:120]}...")
    print(f"  Viability Score: {report1.get('viability_score')}/100 | Risk: {report1.get('risk_level')}")
    assert source1 in ("LIVE_AI", "FALLBACK"), f"Invalid source: {source1}"

    # TEST 2: Pricing strategy query
    print("\n--- TEST 2: Pricing Strategy Query ---")
    q2 = "What pricing tier structure should we adopt for enterprise API usage (tiered vs usage-based)?"
    t0 = time.time()
    res2 = client.post("/generate-report", json={"task": q2, "force_refresh": True})
    elapsed2 = time.time() - t0
    d2 = res2.get_json()

    assert res2.status_code == 200
    assert d2.get("success") is True
    report2 = d2.get("report") or {}
    print(f"[TEST 2 PASSED] Pricing query in {elapsed2:.2f}s | Source: {report2.get('analysis_source')}")
    print(f"  Recommendation: {report2.get('recommended_decision')}")
    assert report1.get("decision") != report2.get("decision"), "Different queries must yield different reports"

    # TEST 3: Market expansion query
    print("\n--- TEST 3: Market Expansion Query ---")
    q3 = "Should our cybersecurity platform expand into Southeast Asian emerging fintech markets?"
    res3 = client.post("/generate-report", json={"task": q3, "force_refresh": True})
    d3 = res3.get_json()
    assert res3.status_code == 200
    report3 = d3.get("report") or {}
    print(f"[TEST 3 PASSED] Market expansion query completed | Source: {report3.get('analysis_source')}")
    print(f"  Roadmap phases: {len(report3.get('implementation_roadmap', []))} phases identified.")

    # TEST 4: Cost optimization query
    print("\n--- TEST 4: Cost Optimization Query ---")
    q4 = "How can a cloud software startup reduce fixed server costs and improve unit contribution margins?"
    res4 = client.post("/generate-report", json={"task": q4, "force_refresh": True})
    d4 = res4.get_json()
    assert res4.status_code == 200
    report4 = d4.get("report") or {}
    print(f"[TEST 4 PASSED] Cost optimization query completed | Source: {report4.get('analysis_source')}")

    # TEST 5: Follow-up question with context preservation
    print("\n--- TEST 5: Follow-up Question & Context Preservation ---")
    fu1_q = "What happens if we reduce the subscription price by 25%?"
    conv_id = d1.get("conversation_id")
    res_fu1 = client.post("/follow-up", json={
        "question": fu1_q,
        "conversation_id": conv_id,
        "original_task": q1,
        "report": report1
    })
    assert res_fu1.status_code == 200
    dfu1 = res_fu1.get_json()
    assert dfu1.get("success") is True
    ans1 = dfu1.get("answer", "")
    print(f"[TEST 5.1 PASSED] Follow-up 1 answered: {ans1[:120]}...")
    assert len(ans1) > 20

    # Second follow-up turn in same session
    fu2_q = "What is the single biggest operational bottleneck?"
    res_fu2 = client.post("/follow-up", json={
        "question": fu2_q,
        "conversation_id": conv_id,
        "original_task": q1,
        "report": report1
    })
    assert res_fu2.status_code == 200
    dfu2 = res_fu2.get_json()
    history = dfu2.get("conversation_history", [])
    print(f"[TEST 5.2 PASSED] Follow-up 2 answered. History length: {len(history)} turns.")
    assert len(history) >= 2, "Conversation history must track multiple turns"

    # TEST 6: What-If Sensitivity Analysis
    print("\n--- TEST 6: What-If Sensitivity Analysis ---")
    res_wi = client.post("/what-if", json={
        "task": q1,
        "price": 800,
        "monthly_orders": 200,
        "variable_cost": 300,
        "fixed_cost": 40000,
        "marketing_cost": 15000
    })
    assert res_wi.status_code == 200
    dwi = res_wi.get_json()
    assert dwi.get("success") is True
    # Profit = (800*200) - (40000 + 300*200 + 15000) = 160000 - 115000 = 45000
    assert dwi.get("monthly_profit") == 45000, f"Expected 45000, got {dwi.get('monthly_profit')}"
    # Break-even = 40000 / (800 - 300) = 40000 / 500 = 80 units
    assert dwi.get("break_even_units") == 80, f"Expected 80, got {dwi.get('break_even_units')}"
    print(f"[TEST 6 PASSED] What-If calculation: Profit = ₹{dwi.get('monthly_profit')}, Break-even = {dwi.get('break_even_units')} units.")

    # TEST 7: Report History & SQLite Persistence
    print("\n--- TEST 7: Report History & SQLite Persistence ---")
    res_hist = client.get("/history")
    assert res_hist.status_code == 200
    d_hist = res_hist.get_json()
    assert d_hist.get("success") is True
    history_list = d_hist.get("history", [])
    print(f"[TEST 7 PASSED] SQLite Report History contains {len(history_list)} persistent records.")
    assert len(history_list) >= 1

    # TEST 8: Exact Repeated Query Caching
    print("\n--- TEST 8: Exact Repeated Query Caching ---")
    t0 = time.time()
    res_cache = client.post("/generate-report", json={"task": q1, "force_refresh": False})
    elapsed_cache = time.time() - t0
    d_cache = res_cache.get_json()
    assert res_cache.status_code == 200
    report_cache = d_cache.get("report") or {}
    print(f"[TEST 8 PASSED] Cache hit returned in {elapsed_cache*1000:.1f}ms (<500ms) | Source: {report_cache.get('analysis_source')}")
    assert elapsed_cache < 0.5, "Cached query must return in under 500ms"
    assert report_cache.get("analysis_source") == "LIVE_CACHE", "Expected LIVE_CACHE for cached query"

    # TEST 9: Force Refresh Query
    print("\n--- TEST 9: Force Refresh Query ---")
    t0 = time.time()
    res_fr = client.post("/generate-report", json={"task": q1, "force_refresh": True})
    elapsed_fr = time.time() - t0
    d_fr = res_fr.get_json()
    assert res_fr.status_code == 200
    report_fr = d_fr.get("report") or {}
    print(f"[TEST 9 PASSED] Force refresh bypassed cache in {elapsed_fr:.2f}s | Source: {report_fr.get('analysis_source')}")
    assert report_fr.get("analysis_source") in ("LIVE_AI", "FALLBACK")

    # TEST 10: Invalid / Empty Query Handling
    print("\n--- TEST 10: Invalid / Empty Query Handling ---")
    res_inv = client.post("/generate-report", json={"task": ""})
    assert res_inv.status_code == 400, f"Expected 400, got {res_inv.status_code}"
    d_inv = res_inv.get_json()
    assert d_inv.get("success") is False
    assert "required" in d_inv.get("error", "").lower()
    print("[TEST 10 PASSED] Empty query properly rejected with HTTP 400 and structured error JSON.")

    # TEST 11: LLM Failure & Structured Unavailable Response
    print("\n--- TEST 11: LLM Unavailable Scenario & Structured Unavailable Status ---")
    with gemini_client.lock:
        gemini_client.circuit_state = "OPEN"
        gemini_client.last_error_type = "TRANSIENT"
        gemini_client.last_failure_time = time.time()

    fb_query = f"Should a boutique coffee roaster expand into ready-to-drink cans {time.time()}?"
    res_fb = client.post("/generate-report", json={"task": fb_query, "force_refresh": True})
    assert res_fb.status_code == 503, f"Expected 503, got {res_fb.status_code}"
    dfb = res_fb.get_json()

    print(f"  Response status: {dfb.get('status')}")
    print(f"  Response message: {dfb.get('message')}")
    print(f"  Retry after: {dfb.get('retry_after_seconds')}s")
    assert dfb.get("success") is False
    assert dfb.get("status") == "temporary_ai_unavailable"
    assert "temporarily busy" in dfb.get("message", "").lower()

    with gemini_client.lock:
        gemini_client.circuit_state = "CLOSED"
        gemini_client.consecutive_failures = 0
        gemini_client.quota_exhausted = False
    print("[TEST 11 PASSED] Unavailable mode is 100% structured (503) and never fabricates generic fake reports.")


    print("\n" + "=" * 80)
    print("   ALL 11 VALIDATION SUITE TESTS COMPLETED AND PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_comprehensive_validation_suite()

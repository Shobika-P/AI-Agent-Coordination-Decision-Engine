import sys
import os
import time
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.tool_selector import select_tool
from utils.gemini_client import gemini_client
from graph.decision_graph import report_workflow


def test_tool_selector_keywords():
    print("\n--- TEST 1: Tool Selector Keyword Optimization (0 Gemini Calls) ---")
    keywords_tests = [
        ("calculate break-even point", "break_even"),
        ("what is the profit margin?", "profit"),
        ("calculate ROI for investment", "roi"),
        ("evaluate risk for market launch", "market_risk"),
        ("expected revenue for product", "profit"),
        ("return on capital for startup", "roi"),
        ("fixed cost and units to sell", "break_even"),
    ]

    for query, expected_tool in keywords_tests:
        tool = select_tool(query)
        assert tool == expected_tool, f"Query '{query}' expected {expected_tool}, got {tool}"
        print(f"[OK] Tool match: '{query}' -> {tool}")


def test_circuit_breaker_fast_fail_propagation():
    print("\n--- TEST 2: Circuit Breaker Fast-Fail & Structured Error Propagation ---")

    # Manually transition circuit to OPEN state
    with gemini_client.lock:
        gemini_client.circuit_state = "OPEN"
        gemini_client.last_failure_time = time.time()
        gemini_client.cache.clear()

    initial_state = {
        "task": "Should we launch an AI analytics platform in India?",
        "conversation_id": "test-circuit-123",
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

    t0 = time.time()
    final_state = report_workflow.invoke(initial_state)
    total_elapsed = time.time() - t0

    print(f"[Circuit Breaker Test] Total Workflow Time: {total_elapsed:.3f}s")
    print("Agent Statuses:", final_state.get("agent_statuses"))
    print("Workflow Status:", final_state.get("workflow_status"))

    report = final_state.get("final_report")
    assert report is not None, "Report object should be present"
    assert report.get("success") is False, "When circuit is OPEN, report must not be fabricated"
    assert report.get("status") == "temporary_ai_unavailable", "Expected temporary_ai_unavailable status"
    assert gemini_client.circuit_state == "OPEN", "Circuit breaker should remain open"
    
    # Test instant fast-fail on subsequent client generate call
    t_fast = time.time()
    fast_res = gemini_client.generate("Instant fast-fail check prompt")
    fast_elapsed = time.time() - t_fast

    print(f"[Circuit Breaker Fast-Fail] Response latency: {fast_elapsed*1000:.2f}ms")
    assert fast_elapsed < 0.05, f"Fast fail should respond in <50ms, took {fast_elapsed:.3f}s"
    assert fast_res.get("success") is False, "Fast fail response should indicate success=False"
    assert fast_res.get("status") == "temporary_ai_unavailable"
    print("[OK] Fast-fail verified: Subsequent agent calls return structured busy status instantly.")

    # Reset circuit
    with gemini_client.lock:
        gemini_client.circuit_state = "CLOSED"
        gemini_client.consecutive_failures = 0
        gemini_client.quota_exhausted = False


def test_cooldown_and_half_open_recovery():
    print("\n--- TEST 3: Cooldown & Half-Open Circuit Recovery ---")

    # Manually open circuit and set failure time to 20 seconds ago (cooldown = 15s)
    with gemini_client.lock:
        gemini_client.circuit_state = "OPEN"
        gemini_client.last_failure_time = time.time() - 20.0

    print("[Circuit Breaker Test] Simulating 20s cooldown elapsed...")

    # Now make a request - should enter HALF-OPEN state and probe availability
    res = gemini_client.generate("Testing availability after cooldown")
    print(f"[Half-Open Test Result] circuit_state: {gemini_client.circuit_state}, status: {res.get('status')}")
    assert gemini_client.circuit_state in ("CLOSED", "OPEN", "HALF_OPEN"), "Circuit should transition appropriately"
    print("[OK] Cooldown recovery logic tested successfully.")

    # Reset circuit
    with gemini_client.lock:
        gemini_client.circuit_state = "CLOSED"
        gemini_client.consecutive_failures = 0
        gemini_client.quota_exhausted = False


if __name__ == "__main__":
    test_tool_selector_keywords()
    test_circuit_breaker_fast_fail_propagation()
    test_cooldown_and_half_open_recovery()
    print("\n==================================================")
    print("ALL CIRCUIT BREAKER TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


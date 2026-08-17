import sys
import os
import time
import threading
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.tool_selector import select_tool
from utils.gemini_client import gemini_client
from graph.decision_graph import report_workflow
from memory.report_db import report_db

def test_rule_based_tool_selection():
    print("\n--- TEST 1: Rule-Based Tool Selection (0 Gemini Calls) ---")

    # 1. Break even query
    be_tool = select_tool("Calculate break even point for selling 500 units at 500 price and 300 cost")
    assert be_tool == "break_even", f"Expected break_even, got {be_tool}"
    print("[OK] Break-even query matched rule: break_even")

    # 2. ROI query
    roi_tool = select_tool("What is the ROI if investment is 50000 and return is 70000?")
    assert roi_tool == "roi", f"Expected roi, got {roi_tool}"
    print("[OK] ROI query matched rule: roi")

    # 3. Profit query
    profit_tool = select_tool("Calculate profit margin for revenue 500 and cost 300")
    assert profit_tool == "profit", f"Expected profit, got {profit_tool}"
    print("[OK] Profit query matched rule: profit")

    # 4. Market Risk query
    risk_tool = select_tool("Evaluate market risk for launching a new cloud SaaS product in India")
    assert risk_tool == "market_risk", f"Expected market_risk, got {risk_tool}"
    print("[OK] Market Risk query matched rule: market_risk")


def test_parallel_langgraph_execution():
    print("\n--- TEST 2: Parallel LangGraph Execution ---")
    initial_state = {
        "task": "Should we launch a specialty coffee brand in Bangalore with fixed cost 50000?",
        "conversation_id": "test-parallel-123",
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
    elapsed = time.time() - t0

    assert final_state.get("final_report") is not None, "Final report should not be None"
    statuses = final_state.get("agent_statuses", {})
    metrics = final_state.get("execution_metrics", {})

    print("Agent Statuses:", statuses)
    print("Execution Metrics:", metrics)
    print(f"Total Workflow Elapsed: {elapsed:.2f}s")

    assert statuses.get("tool") in ["COMPLETED", "SKIPPED"], f"Tool status unexpected: {statuses.get('tool')}"
    assert statuses.get("research") == "COMPLETED", f"Research status unexpected: {statuses.get('research')}"
    assert statuses.get("planning") == "COMPLETED", f"Planning status unexpected: {statuses.get('planning')}"
    assert statuses.get("decision") == "COMPLETED", f"Decision status unexpected: {statuses.get('decision')}"
    assert statuses.get("report") == "COMPLETED", f"Report status unexpected: {statuses.get('report')}"
    print("[OK] LangGraph workflow executed successfully with all agent statuses intact.")


def test_gemini_client_deduplication():
    print("\n--- TEST 3: Concurrent Gemini Request Deduplication ---")

    prompt = "Give a 1-sentence strategic advice for e-commerce launch."
    sys_instruction = "You are a concise advisor."

    results = [None, None]
    latencies = [0.0, 0.0]

    def worker(idx):
        t0 = time.time()
        res = gemini_client.generate(prompt, system_instruction=sys_instruction)
        latencies[idx] = time.time() - t0
        results[idx] = res

    t1 = threading.Thread(target=worker, args=(0,))
    t2 = threading.Thread(target=worker, args=(1,))

    # Reset cache to test in-flight deduplication
    norm_key = gemini_client._normalize_prompt(f"{sys_instruction}\n\n{prompt}".strip())
    gemini_client.cache.pop(norm_key, None)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"Worker 0 content len: {len(results[0]['content'])}, latency: {latencies[0]:.2f}s")
    print(f"Worker 1 content len: {len(results[1]['content'])}, latency: {latencies[1]:.2f}s")

    assert results[0]['content'] == results[1]['content'], "Both concurrent requests must receive identical content"
    print("[OK] Concurrent duplicate Gemini requests successfully deduplicated.")


def test_app_endpoints():
    print("\n--- TEST 4: App Route API Integration & Caching ---")
    from app import app as flask_app

    client = flask_app.test_client()

    # Health Check
    res = client.get("/health")
    assert res.status_code == 200
    print("[OK] GET /health returned 200 OK")

    # Generate Report Request 1
    task_q = "Calculate break even for launching an AI analytics widget"
    res1 = client.post("/generate-report", json={"task": task_q})
    assert res1.status_code == 200
    d1 = res1.get_json()
    assert d1.get("success") is True, f"Response failed: {d1}"
    print("[OK] Initial POST /generate-report completed successfully.")

    # Generate Report Request 2 (Identical query - Cache Test)
    t0 = time.time()
    res2 = client.post("/generate-report", json={"task": task_q})
    elapsed = time.time() - t0
    assert res2.status_code == 200
    d2 = res2.get_json()
    assert d2.get("success") is True
    assert elapsed < 0.5, f"Cached query should return instantly (<0.5s), took {elapsed:.2f}s"
    print(f"[OK] Repeat POST /generate-report served from cache in {elapsed*1000:.1f}ms.")

    # Follow-up test
    res_fu = client.post("/follow-up", json={
        "question": "What is the break even unit volume if fixed costs increase by 10000?",
        "conversation_id": d1.get("conversation_id"),
        "original_task": task_q,
        "report": d1.get("report")
    })
    assert res_fu.status_code == 200
    dfu = res_fu.get_json()
    assert dfu.get("success") is True
    print("[OK] POST /follow-up responded successfully with context.")

    # What-If sensitivity test
    res_wi = client.post("/what-if", json={
        "task": task_q,
        "price": 600,
        "monthly_orders": 200,
        "fixed_cost": 50000,
        "variable_cost": 250
    })
    assert res_wi.status_code == 200
    dwi = res_wi.get_json()
    assert dwi.get("success") is True
    assert dwi.get("break_even_units") is not None
    print("[OK] POST /what-if executed deterministic calculation successfully.")


if __name__ == "__main__":
    test_rule_based_tool_selection()
    test_parallel_langgraph_execution()
    test_gemini_client_deduplication()
    test_app_endpoints()
    print("\n==================================================")
    print("ALL OPTIMIZATION INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

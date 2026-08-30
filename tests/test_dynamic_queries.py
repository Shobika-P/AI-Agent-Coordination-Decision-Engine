import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app as flask_app
from memory.report_db import report_db


def test_dynamic_domain_queries():
    print("=" * 80)
    print("   DYNAMIC 5-DOMAIN VERIFICATION SUITE")
    print("=" * 80)

    client = flask_app.test_client()

    queries = [
        ("1. Healthy Meal Subscription", "Should I launch a healthy meal subscription for office workers?"),
        ("2. Bookstore Online Delivery", "Should a small bookstore introduce online delivery?"),
        ("3. Manufacturing Inventory Automation", "Should a manufacturing company automate inventory management?"),
        ("4. College Academic Workflow Platform", "Should a college implement an AI-based academic workflow platform?"),
        ("5. Sustainable Fashion Marketplace", "Should a startup launch a sustainable fashion marketplace?")
    ]


    generated_reports = []

    for label, q in queries:
        print(f"\n--- Running: {label} ---")
        print(f"Query: {q}")
        t0 = time.time()
        res = client.post("/generate-report", json={"task": q, "force_refresh": True})
        elapsed = time.time() - t0
        
        assert res.status_code == 200, f"Error generating report: {res.get_json()}"
        data = res.get_json()
        assert data.get("success") is True
        
        report = data.get("report") or {}
        source = report.get("analysis_source")
        viability = report.get("viability_score")
        risk = report.get("risk_level")
        roadmap = report.get("implementation_roadmap", [])
        followups = report.get("suggested_followups", [])
        
        print(f"[SUCCESS] {label} completed in {elapsed:.2f}s | Source: {source}")
        print(f"  Viability Score: {viability}/100 | Risk Level: {risk}")
        print(f"  Decision Summary: {str(report.get('decision'))[:140]}...")
        print(f"  Roadmap Phases: {len(roadmap)} phases")
        print(f"  Dynamic Suggested Follow-ups: {len(followups)} questions")
        if followups:
            for f_idx, f_q in enumerate(followups[:3], 1):
                print(f"    Q{f_idx}: {f_q}")
                
        generated_reports.append((label, q, report))

    # Verify all 5 reports are unique and non-identical
    print("\n--- Verifying Distinct Strategic Outputs Across All 5 Domains ---")
    for i in range(len(generated_reports)):
        for j in range(i + 1, len(generated_reports)):
            label_i, q_i, rep_i = generated_reports[i]
            label_j, q_j, rep_j = generated_reports[j]
            
            assert rep_i.get("decision") != rep_j.get("decision"), f"Decision reports for '{label_i}' and '{label_j}' must be distinct!"
            print(f"[VERIFIED DISTINCT] {label_i} != {label_j}")

    print("\n" + "=" * 80)
    print("   ALL 5 DYNAMIC DOMAIN QUERIES VALIDATED AND VERIFIED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    test_dynamic_domain_queries()

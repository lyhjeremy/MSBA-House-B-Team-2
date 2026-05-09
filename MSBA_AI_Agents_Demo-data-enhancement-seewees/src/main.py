from __future__ import annotations
import sys
from dotenv import load_dotenv
load_dotenv()  # must be before importing graph/agents
from tracing import init_langsmith_tracing
init_langsmith_tracing()  # must be before importing graph/agents
from graph import build_graph


if __name__ == "__main__":
    # Detect optional demo-loop flag: `python src/main.py --demo-loop`
    demo_mode = "--demo-loop" in sys.argv

    if demo_mode:
        print("=" * 60)
        print("DEMO MODE: enabling stricter audit check to demonstrate")
        print("the self-correction loop. The first plan will likely fail")
        print("CHECK_6_ARITHMETIC_BREAKDOWN_DEMO; the planner will revise.")
        print("=" * 60)

    app = build_graph()

    state = {
        "pdf_path": "data/SeeWeeS Specialty distribution.pdf",
        "csv_path": "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv",
        "resources_path": "data-for-enhancement/Resource_availability_48h.csv",
        "demo_mode": demo_mode,
    }

    final = app.invoke(state)

    import json

    print("\n=== RECONCILIATION SUMMARY ===")
    print(final.get("csv_summary", {}))

    print("\n=== PER-CORRIDOR WEATHER ===")
    print(final.get("weather_summary", "(none)"))

    print("\n=== ALLOCATION SUMMARY ===")
    print(final.get("allocation_summary", "(none)"))

    print(f"\n=== TOTAL PENALTY: {final.get('total_penalty', 0)} points ===")

    print("\n=== AUDIT HISTORY (all attempts) ===")
    audit_history = final.get("audit_history", [])
    for i, attempt in enumerate(audit_history):
        print(f"\nAttempt {i + 1}: passed={attempt['passed']}, "
              f"violations={len(attempt['violations'])}")
        for v in attempt["violations"]:
            print(f"  - [{v['severity']}] ({v['check_id']}) {v['message']}")

    final_audit = final.get("audit_report", {})
    print(f"\n=== FINAL AUDIT: passed={final_audit.get('passed')} "
          f"after {final.get('retry_count', 0)} retries ===")

    report_html = final.get("report_html", "")
    print("\n=== REPORT (first 1500 chars) ===\n")
    print(report_html[:1500])

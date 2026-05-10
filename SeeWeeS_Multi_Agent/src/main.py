from __future__ import annotations
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # must be before importing graph/agents
from tracing import init_langsmith_tracing
init_langsmith_tracing()  # must be before importing graph/agents
from graph import build_graph
from tools.pdf_exporter import html_to_pdf


if __name__ == "__main__":
    demo_mode = "--demo-loop" in sys.argv

    if demo_mode:
        print("=" * 60)
        print("DEMO MODE: enabling stricter audit check to demonstrate")
        print("the self-correction loop. The first plan will likely fail")
        print("CHECK_6_GRAND_TOTAL_SUMMATION_DEMO; the planner will revise.")
        print("=" * 60)

    app = build_graph()

    state = {
        "pdf_path": "data/SeeWeeS Specialty distribution.pdf",
        "csv_path": "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv",
        "resources_path": "data-for-enhancement/Resource_availability_48h.csv",
        "demo_mode": demo_mode,
    }

    final = app.invoke(state)

    print("\n=== RECONCILIATION SUMMARY ===")
    print(final.get("csv_summary", {}))

    print(f"\n=== ALLOCATION TOTAL PENALTY: {final.get('total_penalty', 0)} points ===")

    print("\n=== AUDIT HISTORY ===")
    for i, attempt in enumerate(final.get("audit_history", [])):
        print(f"Attempt {i + 1}: passed={attempt['passed']}, "
              f"violations={len(attempt['violations'])}")

    final_audit = final.get("audit_report", {})
    print(f"FINAL AUDIT: passed={final_audit.get('passed')} "
          f"after {final.get('retry_count', 0)} retries")

    # Save HTML
    report_html = final.get("report_html", "")
    if report_html:
        os.makedirs("outputs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "_demo" if demo_mode else ""
        html_path = f"outputs/dispatch_report_{timestamp}{suffix}.html"
        pdf_path  = f"outputs/dispatch_report_{timestamp}{suffix}.pdf"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(report_html)
        abs_html = os.path.abspath(html_path)

        print(f"\n=== HTML SAVED ===")
        print(f"  {abs_html}")

        # Auto-export PDF (silently no-op if Playwright/Chromium missing)
        print("\n=== PDF EXPORT ===")
        result = html_to_pdf(html_path, pdf_path, paper_format="Letter", margin="0.5in")
        if result:
            print(f"  {result}")
        else:
            print(f"  (skipped — see message above; HTML still available for manual print)")

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()  # must be before importing graph/agents
from tracing import init_langsmith_tracing
init_langsmith_tracing()  # must be before importing graph/agents
from graph import build_graph


if __name__ == "__main__":
    app = build_graph()

    state = {
        "pdf_path": "data/SeeWeeS Specialty distribution.pdf",
        "csv_path": "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv",
        "resources_path": "data-for-enhancement/Resource_availability_48h.csv",
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

    report_html = final.get("report_html", "")
    print("\n=== REPORT (first 1500 chars) ===\n")
    print(report_html[:1500])

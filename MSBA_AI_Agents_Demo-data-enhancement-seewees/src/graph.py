from __future__ import annotations
import os
from typing import TypedDict, Dict, Any, List, Literal

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from tools.pdf_tools import PdfRag
from tools.csv_tools import analyze_csv
from tools.weather_tools import (
    get_weather_risk_by_corridor,
    format_corridor_weather_for_prompt,
)
from tools.resources import load_resource_pools
from tools.allocator import allocate, format_allocation_for_prompt
from tools.email_tools import send_email_smtp
from auditor import run_audit, format_audit_for_report
from agents import run_context_agent, run_ops_agent, run_planner_agent, run_report_agent

load_dotenv()


MAX_RETRIES = 2


class AppState(TypedDict, total=False):
    pdf_path: str
    csv_path: str
    resources_path: str
    demo_mode: bool                # Day 5: trigger the audit loop reliably for demo

    business_context: str

    csv_summary: Dict[str, Any]
    csv_kpis: Dict[str, Any]
    excluded_md: str
    reconciliation_log: List[Dict[str, Any]]
    ops_insights: str

    weather_by_corridor: Dict[str, Any]
    weather_summary: str

    allocation_result: Dict[str, Any]
    allocation_summary: str
    total_penalty: int

    dispatch_plan: str

    audit_report: Dict[str, Any]
    audit_history: List[Dict[str, Any]]
    audit_feedback: str
    retry_count: int

    report_html: str


def node_pdf_context(state: AppState) -> AppState:
    rag = PdfRag(persist_dir="chroma_db")
    vectordb = rag.build(state["pdf_path"])
    retriever = rag.retriever(vectordb, k=6)
    query = "Extract KPI definitions, thresholds, SLAs, constraints, dispatch rules, exceptions."
    docs = retriever.invoke(query)
    snippets = "\n\n---\n\n".join(d.page_content for d in docs)
    business_context = run_context_agent(snippets)
    return {"business_context": business_context}


def node_csv_analysis(state: AppState) -> AppState:
    res = analyze_csv(state["csv_path"])
    excluded_md = "(no exclusions)"
    if not res.anomalies.empty:
        excluded_md = res.anomalies.head(15).to_markdown(index=False)
    ops_insights = run_ops_agent(
        summary=res.summary,
        kpis=res.kpis,
        anomalies_md=excluded_md,
        formatted=res.formatted_for_prompt,
    )
    return {
        "csv_summary": res.summary,
        "csv_kpis": res.kpis,
        "excluded_md": excluded_md,
        "reconciliation_log": res.reconciliation_log,
        "ops_insights": ops_insights,
    }


def node_weather(state: AppState) -> AppState:
    tz = os.getenv("WEATHER_TZ", "America/New_York")
    weather_by_corridor = get_weather_risk_by_corridor(tz=tz)
    weather_summary = format_corridor_weather_for_prompt(weather_by_corridor)
    return {
        "weather_by_corridor": weather_by_corridor,
        "weather_summary": weather_summary,
    }


def node_allocation(state: AppState) -> AppState:
    resources_path = state.get("resources_path", "data-for-enhancement/Resource_availability_48h.csv")
    pools = load_resource_pools(resources_path)
    result = allocate(
        kpis_by_corridor=state.get("csv_kpis", {}),
        weather_by_corridor=state.get("weather_by_corridor", {}),
        pools=pools,
    )
    return {
        "allocation_result": result.to_dict(),
        "allocation_summary": format_allocation_for_prompt(result),
        "total_penalty": result.total_penalty,
        "retry_count": 0,
        "audit_history": [],
        "audit_feedback": "",
    }


def node_planner(state: AppState) -> AppState:
    plan = run_planner_agent(
        business_context=state.get("business_context", ""),
        ops_insights=state.get("ops_insights", ""),
        weather_summary=state.get("weather_summary", ""),
        allocation_summary=state.get("allocation_summary", ""),
        audit_feedback=state.get("audit_feedback", ""),
    )
    return {"dispatch_plan": plan}


def node_auditor(state: AppState) -> AppState:
    retry_count = state.get("retry_count", 0)
    demo_mode = bool(state.get("demo_mode", False))

    report = run_audit(
        dispatch_plan=state.get("dispatch_plan", ""),
        allocation_result=state.get("allocation_result", {}),
        weather_by_corridor=state.get("weather_by_corridor", {}),
        total_penalty=state.get("total_penalty", 0),
        retry_count=retry_count,
        demo_mode=demo_mode,
    )

    history = list(state.get("audit_history", []))
    history.append(report.to_dict())
    feedback = report.feedback_for_planner() if not report.passed else ""

    print(f"\n[AUDITOR pass #{retry_count + 1}] passed={report.passed}, "
          f"violations={len(report.violations)} (demo_mode={demo_mode})")
    for v in report.violations:
        print(f"  - [{v.severity}] ({v.check_id}) {v.message}")

    return {
        "audit_report": report.to_dict(),
        "audit_history": history,
        "audit_feedback": feedback,
    }


def route_after_audit(state: AppState) -> Literal["planner", "report"]:
    audit = state.get("audit_report", {})
    retry_count = state.get("retry_count", 0)

    if audit.get("passed"):
        print(f"[ROUTER] Audit passed -> proceeding to report.")
        return "report"

    if retry_count >= MAX_RETRIES:
        print(f"[ROUTER] Audit failed but retry cap ({MAX_RETRIES}) reached -> "
              f"proceeding to report with audit failures flagged.")
        return "report"

    print(f"[ROUTER] Audit failed (attempt {retry_count + 1}) -> looping back to planner.")
    return "planner"


def node_increment_retry(state: AppState) -> AppState:
    return {"retry_count": state.get("retry_count", 0) + 1}


def node_report(state: AppState) -> AppState:
    audit_report = state.get("audit_report", {})
    audit_history = state.get("audit_history", [])
    trail_lines = []
    for i, attempt in enumerate(audit_history):
        trail_lines.append(f"Attempt {i + 1}: passed={attempt['passed']}, "
                           f"violations={len(attempt['violations'])}")
        for v in attempt["violations"]:
            trail_lines.append(f"  - [{v['severity']}] ({v['check_id']}) {v['message']}")
    audit_trail = "\n".join(trail_lines) if trail_lines else "(no audit attempts recorded)"

    html = run_report_agent(
        business_context=state.get("business_context", ""),
        kpis=state.get("csv_kpis", {}),
        anomaly_highlights=state.get("excluded_md", "(none)"),
        weather_summary=state.get("weather_summary", ""),
        allocation_summary=state.get("allocation_summary", ""),
        total_penalty=state.get("total_penalty", 0),
        dispatch_plan=state.get("dispatch_plan", ""),
        audit_trail=audit_trail,
        final_audit_passed=audit_report.get("passed", False),
    )
    return {"report_html": html}


def node_email(state: AppState) -> AppState:
    to_email = os.getenv("REPORT_EMAIL_TO", "").strip()
    if not to_email:
        print("REPORT_EMAIL_TO not set -> skipping email send.")
        return {}
    subject = "MSBA Ops Multi-Agent Dispatch Report"
    send_email_smtp(subject=subject, html_body=state["report_html"], to_email=to_email)
    return {}


def build_graph():
    g = StateGraph(AppState)

    g.add_node("pdf_context", node_pdf_context)
    g.add_node("csv_analysis", node_csv_analysis)
    g.add_node("weather", node_weather)
    g.add_node("allocation", node_allocation)
    g.add_node("planner", node_planner)
    g.add_node("auditor", node_auditor)
    g.add_node("increment_retry", node_increment_retry)
    g.add_node("report", node_report)
    g.add_node("email", node_email)

    g.set_entry_point("pdf_context")
    g.add_edge("pdf_context", "csv_analysis")
    g.add_edge("csv_analysis", "weather")
    g.add_edge("weather", "allocation")
    g.add_edge("allocation", "planner")
    g.add_edge("planner", "auditor")

    g.add_conditional_edges(
        "auditor",
        route_after_audit,
        {
            "planner": "increment_retry",
            "report": "report",
        },
    )
    g.add_edge("increment_retry", "planner")

    g.add_edge("report", "email")
    g.add_edge("email", END)

    return g.compile()

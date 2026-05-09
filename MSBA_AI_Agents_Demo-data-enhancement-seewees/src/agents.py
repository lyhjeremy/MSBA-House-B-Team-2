from __future__ import annotations
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from prompts import (
    PDF_CONTEXT_PROMPT,
    OPS_ANALYSIS_PROMPT,
    PLANNER_PROMPT,
    PLANNER_REVISION_PROMPT,
    REPORT_PROMPT,
)

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.2,
    tags=["msba-demo", "multi-agent"],
    metadata={"repo": "MSBA_AI_Agents_Demo"}
)


def run_context_agent(snippets: str) -> str:
    return llm.invoke(PDF_CONTEXT_PROMPT.format_messages(snippets=snippets)).content


def run_ops_agent(
    summary: Dict[str, Any],
    kpis: Dict[str, Any],
    anomalies_md: str,
    formatted: str = "",
) -> str:
    return llm.invoke(OPS_ANALYSIS_PROMPT.format_messages(
        summary=summary,
        kpis=kpis,
        anomalies_md=anomalies_md,
        formatted=formatted,
    )).content


def run_planner_agent(
    business_context: str,
    ops_insights: str,
    weather_summary: str,
    allocation_summary: str,
    audit_feedback: str = "",
) -> str:
    """
    First call: empty audit_feedback -> use PLANNER_PROMPT.
    Revision call: non-empty audit_feedback -> use PLANNER_REVISION_PROMPT.
    """
    if audit_feedback:
        return llm.invoke(PLANNER_REVISION_PROMPT.format_messages(
            business_context=business_context,
            ops_insights=ops_insights,
            weather_summary=weather_summary,
            allocation_summary=allocation_summary,
            audit_feedback=audit_feedback,
        )).content
    else:
        return llm.invoke(PLANNER_PROMPT.format_messages(
            business_context=business_context,
            ops_insights=ops_insights,
            weather_summary=weather_summary,
            allocation_summary=allocation_summary,
        )).content


def run_report_agent(
    business_context: str,
    kpis: Dict[str, Any],
    anomaly_highlights: str,
    weather_summary: str,
    allocation_summary: str,
    total_penalty: int,
    dispatch_plan: str,
    audit_trail: str,
    final_audit_passed: bool,
) -> str:
    return llm.invoke(REPORT_PROMPT.format_messages(
        business_context=business_context,
        kpis=kpis,
        anomaly_highlights=anomaly_highlights,
        weather_summary=weather_summary,
        allocation_summary=allocation_summary,
        total_penalty=total_penalty,
        dispatch_plan=dispatch_plan,
        audit_trail=audit_trail,
        final_audit_passed=final_audit_passed,
    )).content

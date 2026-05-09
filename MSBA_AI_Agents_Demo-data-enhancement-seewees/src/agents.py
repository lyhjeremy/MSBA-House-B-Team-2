from __future__ import annotations
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from prompts import (
    PDF_CONTEXT_PROMPT,
    OPS_ANALYSIS_PROMPT,
    PLANNER_PROMPT,
    PLANNER_REVISION_PROMPT,
    REPORT_NARRATIVE_PROMPT,
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


def run_report_narrative_agent(
    *,
    weather_summary: str,
    allocation_summary: str,
    total_penalty: int,
    dispatch_plan: str,
    final_audit_passed: bool,
) -> Dict[str, str]:
    """
    Day 6: ReportAgent now produces SHORT narrative blocks only — the layout
    is rendered deterministically in Python. Returns a dict with keys:
      - executive_recommendation (2-3 sentences)
      - top_risks (3 bullets)
      - top_actions (3 bullets)
    """
    raw = llm.invoke(REPORT_NARRATIVE_PROMPT.format_messages(
        weather_summary=weather_summary,
        allocation_summary=allocation_summary,
        total_penalty=total_penalty,
        dispatch_plan=dispatch_plan,
        final_audit_passed=final_audit_passed,
    )).content

    # The LLM returns JSON. Be defensive about code-fence wrapping.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Strip the first line and trailing fence
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback if model didn't produce valid JSON
        parsed = {
            "executive_recommendation": "(narrative generation failed — see raw output)",
            "top_risks": "- (fallback)",
            "top_actions": "- (fallback)",
        }

    return {
        "executive_recommendation": str(parsed.get("executive_recommendation", "")),
        "top_risks": str(parsed.get("top_risks", "")),
        "top_actions": str(parsed.get("top_actions", "")),
    }

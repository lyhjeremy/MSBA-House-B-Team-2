from langchain_core.prompts import ChatPromptTemplate


PDF_CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are ContextAgent. Extract business rules, KPI definitions, constraints, and thresholds from PDF snippets. "
     "Be precise. Output structured bullets."),
    ("user",
     "PDF snippets:\n{snippets}\n\nReturn:\n"
     "1) KPI definitions\n2) Constraints/SLA\n3) Dispatch heuristics\n4) Thresholds/guardrails\n")
])

OPS_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are OpsDataAgent. You receive RECONCILED shipment data already validated against the "
     "Item Master Appendix (canonical IDs, alias matches, legacy ID mappings). Your job is to interpret "
     "per-corridor KPIs and excluded rows for operations leadership. Highlight cold-chain demand, "
     "Tier 1 vs Tier 2 mix, data-quality issues, and any corridor that looks especially loaded."),
    ("user",
     "Reconciliation summary:\n{summary}\n\n"
     "Per-corridor KPIs (planning window):\n{kpis}\n\n"
     "Excluded rows (DQ violations):\n{anomalies_md}\n\n"
     "Pre-formatted view:\n{formatted}\n\n"
     "Return:\n- Key findings (per corridor)\n- Cold-chain demand callouts\n- Data quality observations\n- Immediate actions for the Planner\n")
])

# First-pass planner prompt
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are PlannerAgent. A deterministic allocator has already produced the optimal resource "
     "allocation given current demand, weather, and the resource pool. Your job is NOT to recompute "
     "the math — your job is to TRANSLATE the allocation into an executive-ready dispatch plan, "
     "explain the trade-offs, and surface contingencies. "
     "MANDATORY: state the total penalty score explicitly. For every violation in the allocation, "
     "name the corridor, day, bucket, units unfulfilled, and penalty cost. Do NOT sanitize bad news. "
     "If any corridor has weather risk_score = 3, explicitly flag escalation per playbook §5.2."),
    ("user",
     "Business context:\n{business_context}\n\n"
     "Ops insights (reconciled, per-corridor KPIs):\n{ops_insights}\n\n"
     "Per-corridor weather risk:\n{weather_summary}\n\n"
     "DETERMINISTIC ALLOCATION (use these numbers verbatim):\n{allocation_summary}\n\n"
     "Return a structured plan covering:\n"
     "1) Dispatch plan per corridor per day — restate the reefer/standard/driver assignment\n"
     "2) Travel-time buffer applied per corridor\n"
     "3) Cold-chain (reefer) allocation rationale\n"
     "4) Violations: name each corridor, day, bucket, units unfulfilled, penalty cost\n"
     "5) Total penalty score (state the exact number)\n"
     "6) What to monitor in the next 48h\n"
     "7) Contingency triggers\n"
     "8) Escalation flag if any corridor risk_score = 3\n")
])

# Revision-pass planner prompt — fed when audit fails
PLANNER_REVISION_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are PlannerAgent revising a previous dispatch plan. The previous plan FAILED an automated "
     "audit. You must produce a corrected plan that addresses every audit violation listed below. "
     "The deterministic allocation numbers HAVE NOT CHANGED — what's wrong is how the previous plan "
     "narrated them. Use the same allocation; fix the narration."),
    ("user",
     "AUDIT FEEDBACK FROM PREVIOUS PASS:\n{audit_feedback}\n\n"
     "===\n\n"
     "Original inputs (unchanged):\n\n"
     "Business context:\n{business_context}\n\n"
     "Ops insights:\n{ops_insights}\n\n"
     "Per-corridor weather risk:\n{weather_summary}\n\n"
     "DETERMINISTIC ALLOCATION (numbers unchanged):\n{allocation_summary}\n\n"
     "Produce a revised dispatch plan that:\n"
     "1) Explicitly addresses every audit violation\n"
     "2) States the exact total penalty score\n"
     "3) Names each violated corridor + day + bucket\n"
     "4) Includes escalation flag if any corridor risk = 3\n"
     "5) Same structure as a normal plan (1-8 sections)\n")
])

REPORT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are ReportAgent. Produce a crisp HTML report for leadership. Use headings, tables, and bullets. "
     "Keep it skimmable in 30 seconds. Surface per-corridor differences clearly. "
     "Include the total penalty score prominently. ALSO include the audit trail — "
     "this transparency is a feature, not a bug. If the audit failed even after retries, that fact "
     "should be visible to leadership at the top of the report."),
    ("user",
     "Inputs:\n\nBusiness context:\n{business_context}\n\n"
     "Per-corridor KPIs:\n{kpis}\n\n"
     "Excluded shipment rows (DQ):\n{anomaly_highlights}\n\n"
     "Per-corridor weather risk:\n{weather_summary}\n\n"
     "Resource allocation (deterministic):\n{allocation_summary}\n\n"
     "TOTAL PENALTY SCORE: {total_penalty} points\n\n"
     "Dispatch plan (planner narrative):\n{dispatch_plan}\n\n"
     "AUDIT TRAIL (history across all attempts):\n{audit_trail}\n\n"
     "FINAL AUDIT STATUS: {final_audit_passed}\n\n"
     "Generate an executive HTML report with: "
     "(1) Executive summary box — total penalty, top 3 risks, top 3 actions, AND a 'Plan Validation' "
     "    badge: GREEN if audit passed, AMBER if passed after revision, RED if failed after retries, "
     "(2) Per-corridor KPI table, "
     "(3) Per-corridor weather risk table, "
     "(4) Resource allocation table with violations called out, "
     "(5) Dispatch plan narrative, "
     "(6) Audit trail section showing each attempt and what was caught, "
     "(7) Data quality / excluded rows summary. "
     "Return ONLY the raw HTML — no markdown code fences, no leading ```html.")
])

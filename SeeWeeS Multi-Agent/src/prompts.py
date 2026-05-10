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
     "1) Dispatch plan per corridor per day\n"
     "2) Travel-time buffer applied per corridor\n"
     "3) Cold-chain (reefer) allocation rationale\n"
     "4) Violations: name each corridor, day, bucket, units unfulfilled, penalty cost\n"
     "5) Total penalty score (state the exact number)\n"
     "6) What to monitor in the next 48h\n"
     "7) Contingency triggers\n"
     "8) Escalation flag if any corridor risk_score = 3\n")
])

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


# Day 6: Report agent produces SHORT structured prose only.
# Layout, tables, badges, and styling are rendered in Python.
REPORT_NARRATIVE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are ReportAgent. You write THREE short prose blocks for an executive dispatch report. "
     "Layout, tables, and styling are handled separately — your job is the words.\n\n"
     "RULES:\n"
     "- Plain text only. No HTML, no markdown formatting beyond bullet hyphens.\n"
     "- BE BRIEF. Executives scan for 30 seconds.\n"
     "- Be concrete. Reference specific corridors, days, and numbers.\n"
     "- Do NOT sanitize bad news.\n\n"
     "Return ONLY a JSON object with these three keys (no preamble, no code fences):\n"
     "  executive_recommendation: 2-3 sentences. The single most important thing leadership should know.\n"
     "  top_risks: 3 short bullet lines, each starting with '-'. One risk per line, max 18 words each.\n"
     "  top_actions: 3 short bullet lines, each starting with '-'. One concrete action per line, max 18 words each."),
    ("user",
     "Per-corridor weather:\n{weather_summary}\n\n"
     "Allocation result:\n{allocation_summary}\n\n"
     "Total penalty score: {total_penalty} points\n\n"
     "Final audit passed: {final_audit_passed}\n\n"
     "Planner's full dispatch plan (use as context — DO NOT echo it back):\n{dispatch_plan}\n\n"
     "Return the JSON object now.")
])

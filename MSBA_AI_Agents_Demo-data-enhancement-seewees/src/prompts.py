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

# Day 4: Planner now NARRATES a deterministic allocation rather than computing one.
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are PlannerAgent. A deterministic allocator has already produced the optimal resource "
     "allocation given current demand, weather, and the resource pool. Your job is NOT to recompute "
     "the math — your job is to TRANSLATE the allocation into an executive-ready dispatch plan, "
     "explain the trade-offs, and surface contingencies. "
     "If the allocation has violations (units that could not be served), call them out clearly with "
     "their penalty cost and the operational reason. If any corridor has weather risk_score = 3, "
     "explicitly flag escalation. Trust the numbers; do not invent allocations the math doesn't support."),
    ("user",
     "Business context:\n{business_context}\n\n"
     "Ops insights (reconciled, per-corridor KPIs):\n{ops_insights}\n\n"
     "Per-corridor weather risk:\n{weather_summary}\n\n"
     "DETERMINISTIC ALLOCATION (use these numbers verbatim):\n{allocation_summary}\n\n"
     "Return a structured plan covering:\n"
     "1) Dispatch plan per corridor per day — restate the reefer/standard/driver assignment from the allocation\n"
     "2) Travel-time buffer applied per corridor (driven by weather risk score)\n"
     "3) Cold-chain (reefer) allocation rationale — explain the priority order used\n"
     "4) Violations, if any — restate with penalty cost and root cause\n"
     "5) What to monitor in the next 48h\n"
     "6) Contingency triggers\n"
     "7) Escalation flag if any corridor risk_score = 3\n")
])

REPORT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are ReportAgent. Produce a crisp HTML report for leadership. Use headings, tables, and bullets. "
     "Keep it skimmable in 30 seconds. Surface per-corridor differences clearly. "
     "Include the total penalty score prominently — it's the single number leadership cares about."),
    ("user",
     "Inputs:\n\nBusiness context:\n{business_context}\n\n"
     "Per-corridor KPIs:\n{kpis}\n\n"
     "Excluded shipment rows (DQ):\n{anomaly_highlights}\n\n"
     "Per-corridor weather risk:\n{weather_summary}\n\n"
     "Resource allocation (deterministic):\n{allocation_summary}\n\n"
     "TOTAL PENALTY SCORE: {total_penalty} points\n\n"
     "Dispatch plan (planner narrative):\n{dispatch_plan}\n\n"
     "Generate an executive HTML report with: "
     "(1) Executive summary box with total penalty score, top 3 risks, top 3 actions, "
     "(2) Per-corridor KPI table, "
     "(3) Per-corridor weather risk table (Day0 / Day1 / 48h max + applied buffer), "
     "(4) Resource allocation table (corridor, day, reefers, std trucks, drivers, units served, penalty), "
     "(5) Violations section if any, "
     "(6) Dispatch plan narrative, "
     "(7) Data quality / excluded rows summary. "
     "Return ONLY the raw HTML — no markdown code fences, no leading ```html.")
])

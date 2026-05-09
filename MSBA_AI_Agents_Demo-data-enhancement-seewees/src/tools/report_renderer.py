"""
HTML report renderer for SeeWeeS dispatch reports.

Separation of concerns:
  - LAYOUT & STYLING: fixed in this module (deterministic, professional, consistent)
  - DATA: bound from Python state (deterministic numbers, no LLM math)
  - NARRATIVE PROSE: a small set of short blocks written by the LLM
    (executive recommendation, top 3 risks, top 3 actions)

This pattern keeps the report quality high run-to-run and prevents the LLM
from inventing layouts, hallucinating numbers, or producing inconsistent styling.
"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
import html as html_lib


# =====================================================================
# Top-level renderer
# =====================================================================

def render_report(
    *,
    narrative: Dict[str, str],
    csv_summary: Dict[str, Any],
    csv_kpis: Dict[str, Any],
    weather_by_corridor: Dict[str, Any],
    allocation_result: Dict[str, Any],
    total_penalty: int,
    audit_history: List[Dict[str, Any]],
    final_audit_passed: bool,
    excluded_md: str,
) -> str:
    """
    Build the final HTML report. `narrative` is a small dict of short LLM-written
    prose blocks (see `narrative_keys()` for required keys).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()

    # Decide validation badge based on audit history
    badge_class, badge_label = _validation_badge(audit_history, final_audit_passed)

    # Decide penalty severity color
    penalty_class = "penalty-zero" if total_penalty == 0 else (
        "penalty-low" if total_penalty < 200 else
        "penalty-mid" if total_penalty < 600 else
        "penalty-high"
    )

    sections = [
        _render_header(timestamp, badge_class, badge_label),
        _render_executive_summary(
            narrative=narrative,
            total_penalty=total_penalty,
            penalty_class=penalty_class,
            badge_class=badge_class,
            badge_label=badge_label,
        ),
        _render_kpi_section(csv_kpis),
        _render_weather_section(weather_by_corridor),
        _render_allocation_section(allocation_result, total_penalty),
        _render_audit_trail_section(audit_history, final_audit_passed),
        _render_data_quality_section(csv_summary, excluded_md),
        _render_footer(timestamp),
    ]

    body = "\n".join(sections)
    return _wrap_html(body)


def narrative_keys() -> List[str]:
    """The exact prose blocks the LLM is asked to produce. Keep these short."""
    return [
        "executive_recommendation",  # 2-3 sentences
        "top_risks",                 # bullet list, 3 items, one line each
        "top_actions",               # bullet list, 3 items, one line each
    ]


# =====================================================================
# Section renderers
# =====================================================================

def _render_header(timestamp: str, badge_class: str, badge_label: str) -> str:
    return f"""
<header class="report-header">
  <div class="title-block">
    <h1>SeeWeeS Specialty Dispatch Report</h1>
    <div class="subtitle">48-Hour Multi-Corridor Operations Plan · {html_lib.escape(timestamp)}</div>
  </div>
  <div class="header-badge {badge_class}">{html_lib.escape(badge_label)}</div>
</header>
"""


def _render_executive_summary(
    *,
    narrative: Dict[str, str],
    total_penalty: int,
    penalty_class: str,
    badge_class: str,
    badge_label: str,
) -> str:
    rec = narrative.get("executive_recommendation", "").strip() or "(no recommendation provided)"
    risks = narrative.get("top_risks", "").strip() or "(no risks provided)"
    actions = narrative.get("top_actions", "").strip() or "(no actions provided)"

    return f"""
<section class="exec-summary">
  <div class="exec-grid">
    <div class="exec-prose">
      <h2>Executive Summary</h2>
      <p class="recommendation">{_escape_paragraph(rec)}</p>

      <div class="exec-columns">
        <div class="exec-col">
          <h3>Top Risks</h3>
          {_render_bullet_list_from_text(risks)}
        </div>
        <div class="exec-col">
          <h3>Recommended Actions</h3>
          {_render_bullet_list_from_text(actions)}
        </div>
      </div>
    </div>

    <div class="exec-stats">
      <div class="penalty-card {penalty_class}">
        <div class="penalty-label">Total Penalty Score</div>
        <div class="penalty-value">{total_penalty}</div>
        <div class="penalty-units">points</div>
      </div>
      <div class="badge-card {badge_class}">
        <div class="badge-label">Plan Validation</div>
        <div class="badge-value">{html_lib.escape(badge_label)}</div>
      </div>
    </div>
  </div>
</section>
"""


def _render_kpi_section(csv_kpis: Dict[str, Any]) -> str:
    if not csv_kpis:
        return ""

    rows = []
    for corridor_id, days in csv_kpis.items():
        for day, m in days.items():
            if str(day).startswith("_") or not isinstance(m, dict):
                continue
            rows.append(f"""
<tr>
  <td class="mono">{html_lib.escape(corridor_id)}</td>
  <td>{html_lib.escape(str(day))}</td>
  <td class="num">{m.get('total_units', 0)}</td>
  <td class="num">{m.get('tier1_count', 0)}</td>
  <td class="num">{m.get('tier2_count', 0)}</td>
  <td class="num">{m.get('cold_chain_count', 0)}</td>
  <td class="num">{m.get('standard_temp_count', 0)}</td>
</tr>""")

    return f"""
<section class="card">
  <h2>Per-Corridor Demand (Planning Window)</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>Corridor</th><th>Day</th>
        <th>Total Units</th><th>Tier 1</th><th>Tier 2</th>
        <th>Cold-Chain</th><th>Standard Temp</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _render_weather_section(weather_by_corridor: Dict[str, Any]) -> str:
    if not weather_by_corridor:
        return ""

    rows = []
    for corridor_id, data in weather_by_corridor.items():
        d0 = data.get("Day0", {})
        d1 = data.get("Day1", {})
        max_buffer = data.get("max_48h_buffer", {})
        max_score = data.get("max_48h_score", 0)
        score_class = _risk_score_class(max_score)
        escalation = "Yes" if data.get("escalation_required") else "No"
        rows.append(f"""
<tr>
  <td class="mono">{html_lib.escape(corridor_id)}</td>
  <td>{html_lib.escape(data.get('name', ''))}</td>
  <td class="num">{d0.get('score', 0)}/3</td>
  <td class="num">{d1.get('score', 0)}/3</td>
  <td class="num"><span class="score-pill {score_class}">{max_score}/3</span></td>
  <td>{html_lib.escape(max_buffer.get('label', '—'))}</td>
  <td class="{'flag-yes' if escalation == 'Yes' else 'flag-no'}">{escalation}</td>
</tr>""")

    return f"""
<section class="card">
  <h2>Per-Corridor Weather Risk (48h Horizon)</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>Corridor</th><th>Route</th>
        <th>Day 0</th><th>Day 1</th><th>48h Max</th>
        <th>Travel Buffer</th><th>Escalation Req.</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _render_allocation_section(allocation_result: Dict[str, Any], total_penalty: int) -> str:
    allocations = allocation_result.get("allocations", [])
    if not allocations:
        return ""

    rows = []
    has_violation_anywhere = False
    for a in allocations:
        violation_count = len(a.get("violations", []))
        row_class = "violation-row" if violation_count > 0 else ""
        if violation_count > 0:
            has_violation_anywhere = True
        rows.append(f"""
<tr class="{row_class}">
  <td class="mono">{html_lib.escape(a.get('corridor_id', ''))}</td>
  <td>{html_lib.escape(a.get('day', ''))}</td>
  <td class="num">{a.get('weather_risk', 0)}/3</td>
  <td class="num">{a.get('units_demanded', 0)}</td>
  <td class="num">{a.get('units_fulfilled', 0)}</td>
  <td class="num">{a.get('trucks_temp_controlled_used', 0)}</td>
  <td class="num">{a.get('trucks_standard_used', 0)}</td>
  <td class="num">{a.get('drivers_used', 0)}</td>
  <td class="num penalty-cell">{a.get('penalty_points', 0)}</td>
</tr>""")

    # Violations sub-table
    violations_block = ""
    if has_violation_anywhere:
        v_rows = []
        for a in allocations:
            for v in a.get("violations", []):
                v_rows.append(f"""
<tr>
  <td class="mono">{html_lib.escape(a.get('corridor_id', ''))}</td>
  <td>{html_lib.escape(a.get('day', ''))}</td>
  <td>{html_lib.escape(v.get('bucket', ''))}</td>
  <td class="num">{v.get('units_unfulfilled', 0)}</td>
  <td class="num">{v.get('penalty_per_unit', 0)}</td>
  <td class="num penalty-cell">{v.get('penalty_total', 0)}</td>
  <td>{html_lib.escape(v.get('reason', ''))}</td>
</tr>""")

        violations_block = f"""
<h3 class="subheading">Violations</h3>
<table class="data-table data-table-tight">
  <thead>
    <tr>
      <th>Corridor</th><th>Day</th><th>Bucket</th>
      <th>Units Unfulfilled</th><th>Penalty/Unit</th><th>Total Penalty</th>
      <th>Reason</th>
    </tr>
  </thead>
  <tbody>{''.join(v_rows)}</tbody>
</table>
"""

    return f"""
<section class="card">
  <h2>Resource Allocation Plan</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>Corridor</th><th>Day</th><th>Risk</th>
        <th>Demand</th><th>Served</th>
        <th>Reefers</th><th>Std Trucks</th><th>Drivers</th>
        <th>Penalty</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  {violations_block}
  <p class="footnote">Total Penalty Score: <strong>{total_penalty} points</strong></p>
</section>
"""


def _render_audit_trail_section(audit_history: List[Dict[str, Any]], final_passed: bool) -> str:
    if not audit_history:
        return ""

    items = []
    for i, attempt in enumerate(audit_history):
        status = "PASSED" if attempt.get("passed") else "FAILED"
        status_class = "passed" if attempt.get("passed") else "failed"
        violations = attempt.get("violations", [])
        v_html = ""
        if violations:
            v_lines = "\n".join(
                f'<li><span class="severity {html_lib.escape(v.get("severity", ""))}">'
                f'{html_lib.escape(v.get("severity", "").upper())}</span> '
                f'<span class="check-id">{html_lib.escape(v.get("check_id", ""))}</span>: '
                f'{html_lib.escape(v.get("message", ""))}</li>'
                for v in violations
            )
            v_html = f"<ul class='violation-list'>{v_lines}</ul>"
        items.append(f"""
<div class="attempt">
  <div class="attempt-header">
    <span class="attempt-num">Attempt {i + 1}</span>
    <span class="attempt-status {status_class}">{status}</span>
    <span class="attempt-meta">{len(violations)} violation(s)</span>
  </div>
  {v_html}
</div>
""")

    final_msg = "audit passed" if final_passed else "audit failed (retry cap reached)"
    return f"""
<section class="card">
  <h2>Audit Trail</h2>
  <p class="footnote">Final outcome: <strong>{html_lib.escape(final_msg)}</strong></p>
  {''.join(items)}
</section>
"""


def _render_data_quality_section(csv_summary: Dict[str, Any], excluded_md: str) -> str:
    if not csv_summary:
        return ""
    return f"""
<section class="card">
  <h2>Data Quality &amp; Reconciliation</h2>
  <div class="dq-stats">
    <div class="stat"><div class="stat-num">{csv_summary.get('rows_original', 0)}</div><div class="stat-label">Rows in</div></div>
    <div class="stat"><div class="stat-num">{csv_summary.get('rows_kept', 0)}</div><div class="stat-label">Kept</div></div>
    <div class="stat"><div class="stat-num">{csv_summary.get('fixes_applied', 0)}</div><div class="stat-label">Fixes applied</div></div>
    <div class="stat warn"><div class="stat-num">{csv_summary.get('rows_excluded', 0)}</div><div class="stat-label">Excluded</div></div>
  </div>
  <p class="footnote">Reconciliation against Item Master Appendix (canonical IDs, alias matches, legacy ID mappings).</p>
</section>
"""


def _render_footer(timestamp: str) -> str:
    return f"""
<footer class="report-footer">
  Generated by SeeWeeS Multi-Agent Dispatch System · {html_lib.escape(timestamp)}
</footer>
"""


# =====================================================================
# Helpers
# =====================================================================

def _validation_badge(audit_history, final_audit_passed):
    if not audit_history:
        return "badge-amber", "NOT VALIDATED"
    if final_audit_passed:
        if len(audit_history) == 1:
            return "badge-green", "VALIDATED"
        return "badge-amber", "VALIDATED (after revision)"
    return "badge-red", "NOT VALIDATED"


def _risk_score_class(score: int) -> str:
    if score >= 3: return "score-red"
    if score >= 2: return "score-orange"
    if score >= 1: return "score-yellow"
    return "score-green"


def _escape_paragraph(text: str) -> str:
    """Escape HTML and convert newlines to <br>."""
    safe = html_lib.escape(text.strip())
    return safe.replace("\n", "<br>")


def _render_bullet_list_from_text(text: str) -> str:
    """
    Convert a multi-line string of bullet-style text into <ul><li>...</li></ul>.
    Accepts lines starting with '-', '*', or numbers; falls back to raw lines.
    """
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip common bullet prefixes
        for prefix in ("- ", "* ", "• "):
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        # Strip leading numbering like "1.", "1)"
        if line[:2].rstrip(".)").isdigit():
            parts = line.split(".", 1) if "." in line[:3] else line.split(")", 1)
            if len(parts) == 2:
                line = parts[1].strip()
        items.append(f"<li>{html_lib.escape(line)}</li>")
    if not items:
        return f"<p>{html_lib.escape(text)}</p>"
    return "<ul>" + "".join(items) + "</ul>"


# =====================================================================
# Top-level HTML wrapper (CSS + structure)
# =====================================================================

_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  background: #f4f6fa;
  color: #1e2230;
  line-height: 1.45;
}
.container { max-width: 1100px; margin: 0 auto; padding: 24px; }

/* Header */
.report-header {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #003580 0%, #0057b8 100%);
  color: white; padding: 22px 28px; border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0,53,128,0.15);
  margin-bottom: 22px;
}
.report-header h1 { margin: 0 0 4px 0; font-size: 1.55rem; font-weight: 600; }
.subtitle { opacity: 0.85; font-size: 0.92rem; }

/* Header validation badge */
.header-badge {
  padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 0.85rem;
  letter-spacing: 0.05em; text-transform: uppercase;
}
.header-badge.badge-green { background: #1d9c4f; color: white; }
.header-badge.badge-amber { background: #f0a020; color: #1e2230; }
.header-badge.badge-red   { background: #d23030; color: white; }

/* Cards */
.card, .exec-summary {
  background: white; border-radius: 10px; padding: 22px 26px;
  box-shadow: 0 2px 6px rgba(20,30,60,0.06);
  margin-bottom: 18px;
}
h2 { color: #003580; margin: 0 0 14px 0; font-size: 1.15rem; font-weight: 600; }
h3 { color: #003580; margin: 14px 0 6px 0; font-size: 1.0rem; font-weight: 600; }
.subheading { margin-top: 22px !important; }

/* Executive summary layout */
.exec-grid { display: grid; grid-template-columns: 1fr 240px; gap: 28px; align-items: start; }
.recommendation {
  font-size: 1.02rem; line-height: 1.55; margin: 0 0 16px 0; color: #2a2f42;
  padding: 12px 14px; background: #f6f8fc; border-left: 3px solid #0057b8; border-radius: 4px;
}
.exec-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.exec-col h3 { margin-top: 0; }
.exec-col ul { margin: 0; padding-left: 18px; }
.exec-col li { margin-bottom: 6px; font-size: 0.93rem; }

/* Penalty + badge cards */
.exec-stats { display: flex; flex-direction: column; gap: 10px; }
.penalty-card, .badge-card {
  border-radius: 8px; padding: 16px 18px; text-align: center;
  border: 1px solid rgba(0,0,0,0.08);
}
.penalty-card .penalty-label,
.badge-card .badge-label {
  font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em;
  color: #6b7385; margin-bottom: 6px;
}
.penalty-card .penalty-value { font-size: 2.1rem; font-weight: 700; line-height: 1; }
.penalty-card .penalty-units { font-size: 0.85rem; color: #6b7385; margin-top: 2px; }
.penalty-card.penalty-zero { background: #e8f7ed; }
.penalty-card.penalty-zero .penalty-value { color: #1d9c4f; }
.penalty-card.penalty-low  { background: #f6f8fc; }
.penalty-card.penalty-low  .penalty-value { color: #0057b8; }
.penalty-card.penalty-mid  { background: #fff5e6; }
.penalty-card.penalty-mid  .penalty-value { color: #d97706; }
.penalty-card.penalty-high { background: #fcecec; }
.penalty-card.penalty-high .penalty-value { color: #d23030; }

.badge-card .badge-value { font-size: 0.95rem; font-weight: 600; }
.badge-card.badge-green { background: #e8f7ed; color: #1d9c4f; }
.badge-card.badge-amber { background: #fff5e6; color: #d97706; }
.badge-card.badge-red   { background: #fcecec; color: #d23030; }

/* Tables */
.data-table {
  width: 100%; border-collapse: collapse; font-size: 0.93rem; margin-top: 4px;
}
.data-table th {
  text-align: left; background: #eef2f8; color: #1e2230;
  font-weight: 600; padding: 9px 10px; border-bottom: 2px solid #d3dae6;
}
.data-table td {
  padding: 9px 10px; border-bottom: 1px solid #ecf0f6;
}
.data-table tbody tr:hover { background: #f9fbfe; }
.data-table .mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.88rem; }
.data-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.data-table .penalty-cell { font-weight: 600; color: #b22222; }
.data-table .violation-row { background: #fff8f3; }
.data-table .flag-yes { color: #d23030; font-weight: 600; }
.data-table .flag-no  { color: #6b7385; }

.data-table-tight th, .data-table-tight td { padding: 6px 8px; font-size: 0.88rem; }

.score-pill {
  display: inline-block; padding: 2px 9px; border-radius: 999px;
  font-weight: 600; font-size: 0.85rem;
}
.score-pill.score-green  { background: #e8f7ed; color: #1d9c4f; }
.score-pill.score-yellow { background: #fdf6db; color: #b07e00; }
.score-pill.score-orange { background: #fff0e0; color: #d97706; }
.score-pill.score-red    { background: #fcecec; color: #d23030; }

/* Audit trail */
.attempt {
  margin-top: 12px; padding: 12px 14px;
  border: 1px solid #e2e7f0; border-radius: 6px; background: #f9fbfe;
}
.attempt-header { display: flex; align-items: center; gap: 14px; }
.attempt-num { font-weight: 600; }
.attempt-status { font-weight: 600; padding: 3px 10px; border-radius: 4px; font-size: 0.82rem; }
.attempt-status.passed { background: #e8f7ed; color: #1d9c4f; }
.attempt-status.failed { background: #fcecec; color: #d23030; }
.attempt-meta { color: #6b7385; font-size: 0.85rem; }
.violation-list { margin: 10px 0 0 0; padding-left: 18px; font-size: 0.9rem; }
.violation-list li { margin-bottom: 5px; }
.severity {
  display: inline-block; padding: 1px 7px; border-radius: 3px;
  font-size: 0.72rem; font-weight: 700; margin-right: 5px;
}
.severity.critical { background: #d23030; color: white; }
.severity.high     { background: #f0a020; color: white; }
.severity.medium   { background: #b3b8c4; color: white; }
.severity.low      { background: #d3dae6; color: #1e2230; }
.check-id { font-family: ui-monospace, SFMono-Regular, monospace; color: #6b7385; font-size: 0.82rem; }

/* DQ stats */
.dq-stats { display: flex; gap: 16px; flex-wrap: wrap; }
.stat {
  flex: 1; min-width: 130px; padding: 14px 16px; border-radius: 6px;
  background: #eef2f8; text-align: center;
}
.stat .stat-num { font-size: 1.8rem; font-weight: 700; color: #003580; }
.stat .stat-label { font-size: 0.8rem; color: #6b7385; text-transform: uppercase; letter-spacing: 0.05em; }
.stat.warn { background: #fcecec; }
.stat.warn .stat-num { color: #d23030; }

.footnote { color: #6b7385; font-size: 0.88rem; margin-top: 12px; }

.report-footer {
  text-align: center; color: #6b7385; font-size: 0.82rem;
  margin: 28px 0 12px; padding-top: 18px; border-top: 1px solid #d3dae6;
}

/* Responsive */
@media (max-width: 800px) {
  .exec-grid { grid-template-columns: 1fr; }
  .exec-columns { grid-template-columns: 1fr; }
}
"""


def _wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SeeWeeS Specialty Dispatch Report</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="container">
    {body}
  </div>
</body>
</html>
"""

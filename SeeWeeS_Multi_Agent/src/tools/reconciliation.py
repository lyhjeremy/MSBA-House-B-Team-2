"""
Reconciliation engine for SeeWeeS shipment CSVs.

Applies Item Master Appendix decision rules (D1..D8) to clean messy item
identifiers, drops invalid rows, and produces per-corridor KPIs ready for
the Planner and Auditor.

Pure Python — no LLM calls — for reproducibility and auditability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import pandas as pd

from tools.item_master import (
    CANONICAL_MASTER,
    NAME_ALIASES,
    LEGACY_ID_MAP,
    ITEM_ID_TO_CANONICALS,
    get_tier,
    is_cold_chain,
)


@dataclass
class ReconciliationResult:
    clean_df: pd.DataFrame
    excluded_df: pd.DataFrame
    reconciliation_log: List[Dict[str, Any]]
    kpis_by_corridor: Dict[str, Any]
    summary: Dict[str, Any]


def _normalize_name(name: Any) -> str:
    if not isinstance(name, str):
        return ""
    return name.strip().lower()


def _resolve_canonical(item_id: Any, item_name: Any) -> Dict[str, Any]:
    """
    Apply Appendix A decision rules in order:
      D3 EXACT_MATCH:  (item_id, item_name) -> single canonical row in A.1
      D4 ALIAS_MATCH:  item_name in A.2
      D5 LEGACY_ID_MAP: item_id in A.3
      D6 Conflict resolution via item_name when item_id maps to multiple

    Returns dict with: canonical_id, confidence, reason
    canonical_id is None if unresolved.
    """
    item_id_str = "" if pd.isna(item_id) else str(item_id).strip()
    name_norm = _normalize_name(item_name)

    # D3 + D6: try exact match by item_id, disambiguate by name if multiple
    if item_id_str in ITEM_ID_TO_CANONICALS:
        candidates = ITEM_ID_TO_CANONICALS[item_id_str]
        if len(candidates) == 1:
            cid = candidates[0]
            canonical_name_norm = _normalize_name(CANONICAL_MASTER[cid]["canonical_item_name"])
            if name_norm == canonical_name_norm:
                return {"canonical_id": cid, "confidence": "EXACT_MATCH", "reason": "item_id+name match A.1"}
            # name doesn't match exactly — check aliases first
            if name_norm in NAME_ALIASES and NAME_ALIASES[name_norm] == cid:
                return {"canonical_id": cid, "confidence": "ALIAS_MATCH", "reason": "item_id+alias match A.1/A.2"}
            # name is wrong but item_id is unique → trust item_id, log mismatch
            return {"canonical_id": cid, "confidence": "ITEM_ID_TRUST", "reason": f"item_name mismatch (got '{item_name}'); used item_id"}
        # Multiple canonicals for this item_id (e.g. 10021 -> RMD-100 or RMD-200)
        # Disambiguate by name
        for cid in candidates:
            canonical_name_norm = _normalize_name(CANONICAL_MASTER[cid]["canonical_item_name"])
            if name_norm == canonical_name_norm:
                return {"canonical_id": cid, "confidence": "EXACT_MATCH", "reason": "disambiguated by item_name"}
        # Try aliases for disambiguation
        if name_norm in NAME_ALIASES:
            cid = NAME_ALIASES[name_norm]
            if cid in candidates:
                return {"canonical_id": cid, "confidence": "ALIAS_MATCH", "reason": "disambiguated by alias"}
        return {"canonical_id": None, "confidence": "UNRESOLVED_CONFLICT", "reason": f"item_id {item_id_str} maps to multiple; name '{item_name}' did not disambiguate"}

    # D5: legacy ID map
    if item_id_str in LEGACY_ID_MAP:
        cid, rule, rationale = LEGACY_ID_MAP[item_id_str]
        return {"canonical_id": cid, "confidence": rule, "reason": rationale}

    # D4: pure alias lookup (item_id unknown but name matches alias)
    if name_norm in NAME_ALIASES:
        cid = NAME_ALIASES[name_norm]
        return {"canonical_id": cid, "confidence": "ALIAS_MATCH", "reason": f"unknown item_id; matched alias '{item_name}'"}

    # Last resort: name matches a canonical name directly
    for cid, meta in CANONICAL_MASTER.items():
        if name_norm == _normalize_name(meta["canonical_item_name"]):
            return {"canonical_id": cid, "confidence": "NAME_ONLY_MATCH", "reason": f"unknown item_id; matched canonical name"}

    return {"canonical_id": None, "confidence": "UNRESOLVED", "reason": "no match in A.1/A.2/A.3"}


def reconcile_shipments(csv_path: str) -> ReconciliationResult:
    """
    Load a shipment CSV, apply DQ-01..04 + Appendix A reconciliation, and
    return a structured result with clean rows, excluded rows, log, and KPIs.
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    original_count = len(df)

    log: List[Dict[str, Any]] = []
    excluded_rows: List[Dict[str, Any]] = []
    kept_rows: List[Dict[str, Any]] = []

    # Track duplicates for DQ-04
    seen_unique_ids: Dict[str, int] = {}

    for idx, row in df.iterrows():
        unique_id = row.get("unique_item_id")
        item_id = row.get("item_id")
        item_name = row.get("item_name")

        # DQ-01: missing unique_item_id -> exclude
        if pd.isna(unique_id) or str(unique_id).strip() == "":
            reason = "DQ-01: missing unique_item_id"
            excluded_rows.append({**row.to_dict(), "exclusion_reason": reason})
            log.append({"row": int(idx), "action": "excluded", "reason": reason})
            continue

        unique_id_str = str(unique_id).strip()

        # DQ-04: duplicate unique_item_id -> flag (we keep the first, exclude later)
        if unique_id_str in seen_unique_ids:
            reason = f"DQ-04: duplicate unique_item_id (first seen at row {seen_unique_ids[unique_id_str]})"
            excluded_rows.append({**row.to_dict(), "exclusion_reason": reason})
            log.append({"row": int(idx), "action": "excluded", "reason": reason})
            continue
        seen_unique_ids[unique_id_str] = int(idx)

        # Apply A.1..A.3 reconciliation
        res = _resolve_canonical(item_id, item_name)

        if res["canonical_id"] is None:
            # DQ-02 / DQ-03: cannot reconcile -> exclude
            reason = f"DQ-02/03: {res['reason']}"
            excluded_rows.append({**row.to_dict(), "exclusion_reason": reason})
            log.append({"row": int(idx), "action": "excluded", "reason": reason})
            continue

        cid = res["canonical_id"]
        meta = CANONICAL_MASTER[cid]

        # Build the clean row with enrichments
        clean_row = row.to_dict()
        clean_row["canonical_item_id"] = cid
        clean_row["canonical_item_name"] = meta["canonical_item_name"]
        clean_row["medicine_type"] = meta["medicine_type"]
        clean_row["temp_control"] = meta["temp_control"]
        clean_row["product_class"] = meta["product_class"]
        clean_row["sla_tier"] = get_tier(cid)
        clean_row["is_cold_chain"] = is_cold_chain(cid)
        clean_row["match_confidence"] = res["confidence"]
        clean_row["match_reason"] = res["reason"]
        kept_rows.append(clean_row)

        if res["confidence"] != "EXACT_MATCH":
            log.append({"row": int(idx), "action": "fixed", "confidence": res["confidence"], "reason": res["reason"], "canonical_id": cid})

    clean_df = pd.DataFrame(kept_rows)
    excluded_df = pd.DataFrame(excluded_rows)

    # KPIs by corridor and planning_day (only planning window rows count)
    kpis_by_corridor = _compute_corridor_kpis(clean_df, excluded_df)

    summary = {
        "rows_original": original_count,
        "rows_kept": len(clean_df),
        "rows_excluded": len(excluded_df),
        "fixes_applied": sum(1 for entry in log if entry["action"] == "fixed"),
        "exclusions_applied": sum(1 for entry in log if entry["action"] == "excluded"),
    }

    return ReconciliationResult(
        clean_df=clean_df,
        excluded_df=excluded_df,
        reconciliation_log=log,
        kpis_by_corridor=kpis_by_corridor,
        summary=summary,
    )


def _compute_corridor_kpis(clean_df: pd.DataFrame, excluded_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute per-corridor KPIs for the planning window (Day0 + Day1).
    Returns nested dict: { corridor_id: { day: { metrics } } }
    """
    if clean_df.empty:
        return {}

    # Filter to planning window only
    if "is_planning_window" in clean_df.columns:
        planning_df = clean_df[clean_df["is_planning_window"] == 1].copy()
    else:
        planning_df = clean_df.copy()

    out: Dict[str, Any] = {}

    for corridor_id, corridor_df in planning_df.groupby("corridor_id"):
        out[corridor_id] = {}
        for day_label, day_df in corridor_df.groupby("planning_day"):
            tier1_count = int((day_df["sla_tier"] == 1).sum())
            tier2_count = int((day_df["sla_tier"] == 2).sum())
            cold_count = int(day_df["is_cold_chain"].sum())
            standard_count = int((~day_df["is_cold_chain"]).sum())

            # Per-tier cold-chain split (used for prioritized allocation)
            t1_cold = int(((day_df["sla_tier"] == 1) & (day_df["is_cold_chain"])).sum())
            t1_standard = int(((day_df["sla_tier"] == 1) & (~day_df["is_cold_chain"])).sum())
            t2_cold = int(((day_df["sla_tier"] == 2) & (day_df["is_cold_chain"])).sum())
            t2_standard = int(((day_df["sla_tier"] == 2) & (~day_df["is_cold_chain"])).sum())

            out[corridor_id][str(day_label)] = {
                "total_units": int(len(day_df)),
                "tier1_count": tier1_count,
                "tier2_count": tier2_count,
                "cold_chain_count": cold_count,
                "standard_temp_count": standard_count,
                "tier1_cold": t1_cold,
                "tier1_standard": t1_standard,
                "tier2_cold": t2_cold,
                "tier2_standard": t2_standard,
            }

    # Add excluded counts per corridor (best-effort; if no corridor in excluded, skip)
    if not excluded_df.empty and "corridor_id" in excluded_df.columns:
        for corridor_id, ex_df in excluded_df.groupby("corridor_id"):
            if corridor_id not in out:
                out[corridor_id] = {}
            out[corridor_id]["_excluded_total"] = int(len(ex_df))

    return out


# Convenience: format the reconciliation result for inclusion in agent prompts
def format_reconciliation_for_prompt(result: ReconciliationResult) -> str:
    s = result.summary
    lines = [
        "=== Reconciliation Summary ===",
        f"Original rows: {s['rows_original']}",
        f"Kept (clean): {s['rows_kept']}",
        f"Excluded: {s['rows_excluded']}",
        f"Fixes applied: {s['fixes_applied']}",
        "",
        "=== Per-Corridor KPIs (Planning Window: Day0 + Day1) ===",
    ]
    for corridor_id, days in result.kpis_by_corridor.items():
        lines.append(f"\n{corridor_id}:")
        for day, metrics in days.items():
            if day.startswith("_"):
                lines.append(f"  {day}: {metrics}")
                continue
            lines.append(
                f"  {day}: total={metrics['total_units']}, "
                f"T1={metrics['tier1_count']} (cold={metrics['tier1_cold']}/std={metrics['tier1_standard']}), "
                f"T2={metrics['tier2_count']} (cold={metrics['tier2_cold']}/std={metrics['tier2_standard']})"
            )
    return "\n".join(lines)

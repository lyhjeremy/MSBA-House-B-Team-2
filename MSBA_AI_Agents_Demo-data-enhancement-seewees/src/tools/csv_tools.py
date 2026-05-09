"""
CSV analysis tool — now backed by the reconciliation engine.

Replaces the old generic Isolation Forest approach with playbook-grounded
reconciliation against the Item Master (Appendix A).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd

from tools.reconciliation import (
    reconcile_shipments,
    ReconciliationResult,
    format_reconciliation_for_prompt,
)


@dataclass
class CsvAnalysisResult:
    summary: Dict[str, Any]
    kpis: Dict[str, Any]                # nested: kpis_by_corridor
    anomalies: pd.DataFrame             # excluded rows (DQ violations)
    reconciliation_log: List[Dict[str, Any]]
    clean_df: pd.DataFrame
    formatted_for_prompt: str


def analyze_csv(csv_path: str) -> CsvAnalysisResult:
    """
    Run reconciliation against the Item Master, then return a structured
    result that downstream agents can consume.
    """
    rec: ReconciliationResult = reconcile_shipments(csv_path)

    return CsvAnalysisResult(
        summary=rec.summary,
        kpis=rec.kpis_by_corridor,
        anomalies=rec.excluded_df,
        reconciliation_log=rec.reconciliation_log,
        clean_df=rec.clean_df,
        formatted_for_prompt=format_reconciliation_for_prompt(rec),
    )

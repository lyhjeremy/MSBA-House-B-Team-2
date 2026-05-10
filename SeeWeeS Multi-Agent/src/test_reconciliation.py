"""
Standalone test for the reconciliation engine.
Run this BEFORE running main.py — it doesn't call OpenAI so it's free and fast.

Usage (from project root, with venv active):
    python src/test_reconciliation.py
"""
from __future__ import annotations
import sys, os

# Allow running from project root or src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from tools.reconciliation import reconcile_shipments, format_reconciliation_for_prompt


def main():
    csv_path = "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv"
    print(f"Loading: {csv_path}\n")

    result = reconcile_shipments(csv_path)

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in result.summary.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("RECONCILIATION LOG (first 20 entries)")
    print("=" * 60)
    for entry in result.reconciliation_log[:20]:
        print(f"  row {entry['row']:>3} | {entry['action']:>8} | {entry['reason']}")

    print(f"\n  ... ({len(result.reconciliation_log)} total log entries)")

    print("\n" + "=" * 60)
    print("EXCLUDED ROWS (sample)")
    print("=" * 60)
    if result.excluded_df.empty:
        print("  (none)")
    else:
        print(result.excluded_df[["item_id", "item_name", "unique_item_id", "exclusion_reason"]].head(10).to_string(index=False))

    print("\n" + "=" * 60)
    print("CLEAN ROWS (sample of 8)")
    print("=" * 60)
    cols = ["item_id", "item_name", "canonical_item_id", "sla_tier", "is_cold_chain", "match_confidence"]
    print(result.clean_df[cols].head(8).to_string(index=False))

    print("\n" + "=" * 60)
    print("FORMATTED FOR AGENT PROMPT")
    print("=" * 60)
    print(format_reconciliation_for_prompt(result))


if __name__ == "__main__":
    main()

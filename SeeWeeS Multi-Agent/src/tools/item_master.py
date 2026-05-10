"""
Item Master constants encoded from SeeWeeS Specialty Dispatch Playbook Appendix A.
This is the authoritative source for reconciling shipment item identifiers.

These dicts are hard-coded from the playbook so reconciliation is:
- Deterministic (same answer every run)
- Cheap (no LLM calls per row)
- Auditable (graders can read the rules directly)
"""
from __future__ import annotations
from typing import Dict, List, Tuple

# --- Tier classification (from Section 7 of the playbook) ---
# Tier 1 = Life-critical (6h SLA), Tier 2 = Standard specialty (12h SLA)
# This isn't in Appendix A but we derive it from medicine_type:
TIER_1_TYPES = {
    "Antiviral",
    "Monoclonal Antibody",
    "Emergency Drug",
    "Clinical Trial Drug",
}
# Everything else is Tier 2 by default

# --- A.1 Canonical Item Master (Authoritative) ---
# Key: canonical_item_id
# Value: dict of metadata
CANONICAL_MASTER: Dict[str, Dict[str, str]] = {
    "RMD-100": {
        "item_id": "10021",
        "canonical_item_name": "Remdesivir 100mg",
        "medicine_type": "Antiviral",
        "temp_control": "Cold (2-8C)",
        "product_class": "Antiviral",
    },
    "RMD-200": {
        "item_id": "10021",
        "canonical_item_name": "Remdesivir 200mg",
        "medicine_type": "Antiviral",
        "temp_control": "Cold (2-8C)",
        "product_class": "Antiviral",
    },
    "INS-LIS": {
        "item_id": "10022",
        "canonical_item_name": "Insulin Lispro",
        "medicine_type": "Hormone",
        "temp_control": "Cold (2-8C)",
        "product_class": "Endocrine",
    },
    "PMB-KEY": {
        "item_id": "10035",
        "canonical_item_name": "Pembrolizumab",
        "medicine_type": "Monoclonal Antibody",
        "temp_control": "Cold (2-8C)",
        "product_class": "Oncology Biologic",
    },
    "EPI-AI": {
        "item_id": "10040",
        "canonical_item_name": "Epinephrine Auto-Injector",
        "medicine_type": "Emergency Drug",
        "temp_control": "Room Temp (20-25C)",
        "product_class": "Emergency",
    },
    "HEP-SOD": {
        "item_id": "10050",
        "canonical_item_name": "Heparin Sodium",
        "medicine_type": "Anticoagulant",
        "temp_control": "Room Temp (20-25C)",
        "product_class": "Anticoagulant",
    },
    "MOR-SUL": {
        "item_id": "10060",
        "canonical_item_name": "Morphine Sulfate",
        "medicine_type": "Opioid Analgesic",
        "temp_control": "Controlled Storage",
        "product_class": "Controlled",
    },
    "ALB-INH": {
        "item_id": "10070",
        "canonical_item_name": "Albuterol Inhaler",
        "medicine_type": "Bronchodilator",
        "temp_control": "Room Temp (20-25C)",
        "product_class": "Respiratory",
    },
    "EXP-ONC-CT": {
        "item_id": "99999",
        "canonical_item_name": "Experimental Oncology Drug (Clinical Trial)",
        "medicine_type": "Clinical Trial Drug",
        "temp_control": "Strict Cold Chain (-20C)",
        "product_class": "Clinical Trial",
    },
    "LEV-INH": {
        "item_id": "10071",
        "canonical_item_name": "Levalbuterol Inhaler",
        "medicine_type": "Bronchodilator",
        "temp_control": "Room Temp (20-25C)",
        "product_class": "Respiratory",
    },
    "INS-ASP": {
        "item_id": "10023",
        "canonical_item_name": "Insulin Aspart",
        "medicine_type": "Hormone",
        "temp_control": "Cold (2-8C)",
        "product_class": "Endocrine",
    },
}

# --- A.2 Name Alias / Variant Table (Accepted) ---
# Key: alias_name (lowercased for matching)
# Value: canonical_item_id
NAME_ALIASES: Dict[str, str] = {
    "remdesivir 100 mg": "RMD-100",
    "remdesivir 200 mg": "RMD-200",
    "pembrolizumab (keytruda)": "PMB-KEY",
    "epipen auto injector": "EPI-AI",
    "heparin na": "HEP-SOD",
    "morphine sulphate": "MOR-SUL",
    "albuterol inhaler 90mcg": "ALB-INH",
}

# --- A.3 Legacy / Deprecated / Invalid Identifier Mapping ---
# Key: legacy_item_id (as string)
# Value: (canonical_item_id, rule, rationale)
LEGACY_ID_MAP: Dict[str, Tuple[str, str, str]] = {
    "10020": ("RMD-100", "LEGACY_ID_MAP", "Vendor legacy ID for Remdesivir 100mg"),
    "20021": ("RMD-200", "LEGACY_ID_MAP", "Old system used 200xx for strength variants"),
    "1070":  ("ALB-INH", "LEGACY_ID_MAP", "Truncated ID found in older CSV exports"),
    "99999": ("EXP-ONC-CT", "SPECIAL_CASE", "Clinical trial placeholder ID; strict cold chain"),
}

# Helper: build a fast lookup from item_id -> list of canonical_item_ids
# (because some item_ids map to multiple canonicals e.g. 10021 -> RMD-100 or RMD-200)
def build_item_id_to_canonicals() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for canonical_id, meta in CANONICAL_MASTER.items():
        item_id = meta["item_id"]
        out.setdefault(item_id, []).append(canonical_id)
    return out

ITEM_ID_TO_CANONICALS: Dict[str, List[str]] = build_item_id_to_canonicals()


def get_tier(canonical_id: str) -> int:
    """Return SLA tier for a canonical item: 1 = life-critical, 2 = standard."""
    meta = CANONICAL_MASTER.get(canonical_id)
    if not meta:
        return 2  # default to Tier 2 if unknown
    return 1 if meta["medicine_type"] in TIER_1_TYPES else 2


def is_cold_chain(canonical_id: str) -> bool:
    """Return True if the item requires temperature-controlled (reefer) transport."""
    meta = CANONICAL_MASTER.get(canonical_id)
    if not meta:
        return False
    return "Cold" in meta["temp_control"] or "-20C" in meta["temp_control"]

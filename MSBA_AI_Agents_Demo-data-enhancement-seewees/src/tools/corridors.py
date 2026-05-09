"""
Corridor Catalog — encoded from SeeWeeS Specialty Dispatch Playbook Section 3.

This is the authoritative reference for waypoint geography used in
per-corridor weather risk evaluation.
"""
from __future__ import annotations
from typing import Dict, List


# Section 3.1 — Corridor metadata
# default_sla_tier: 1 = life-critical (6h), 2 = standard specialty (12h)
CORRIDOR_CATALOG: Dict[str, Dict] = {
    "C1_I95_NJ_BOS": {
        "name": "NJ → Boston (I-95)",
        "origin_dc": "Newark_NJ_DC",
        "destination_region": "Boston_MA",
        "default_sla_tier": 1,
        "notes": "Existing corridor; life-critical lane",
    },
    "C2_NJ_PHL": {
        "name": "NJ → Philadelphia",
        "origin_dc": "Newark_NJ_DC",
        "destination_region": "Philadelphia_PA",
        "default_sla_tier": 2,
        "notes": "Added corridor for multi-region planning",
    },
}

# Section 3.2 — Waypoints (per corridor)
# Each waypoint will get an independent weather lookup; corridor risk = max waypoint risk.
CORRIDOR_WAYPOINTS: Dict[str, List[Dict]] = {
    "C1_I95_NJ_BOS": [
        {"waypoint_id": "C1_W1", "city": "Newark NJ",     "lat": 40.7357, "lon": -74.1724},
        {"waypoint_id": "C1_W2", "city": "Bronx NY",      "lat": 40.8448, "lon": -73.8648},
        {"waypoint_id": "C1_W3", "city": "New Haven CT",  "lat": 41.3083, "lon": -72.9279},
        {"waypoint_id": "C1_W4", "city": "Providence RI", "lat": 41.8240, "lon": -71.4128},
        {"waypoint_id": "C1_W5", "city": "Boston MA",     "lat": 42.3601, "lon": -71.0589},
    ],
    "C2_NJ_PHL": [
        {"waypoint_id": "C2_W1", "city": "Newark NJ",         "lat": 40.7357, "lon": -74.1724},
        {"waypoint_id": "C2_W2", "city": "New Brunswick NJ",  "lat": 40.4862, "lon": -74.4518},
        {"waypoint_id": "C2_W3", "city": "Trenton NJ",        "lat": 40.2204, "lon": -74.7643},
        {"waypoint_id": "C2_W4", "city": "Philadelphia PA",   "lat": 39.9526, "lon": -75.1652},
    ],
}


def get_all_corridor_ids() -> List[str]:
    return list(CORRIDOR_CATALOG.keys())


def get_waypoints(corridor_id: str) -> List[Dict]:
    return CORRIDOR_WAYPOINTS.get(corridor_id, [])

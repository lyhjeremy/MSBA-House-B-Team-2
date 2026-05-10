"""
Weather tooling for SeeWeeS dispatch planning.

Two layers:
1. Single-point legacy interface (kept for back-compat).
2. Per-corridor / per-waypoint risk evaluation per playbook Section 5.

Risk thresholds (Section 6.1):
  - Heavy precipitation: precipitation_sum >= 15.0 mm/day
  - High wind:           wind_gusts_10m_max >= 45.0 km/h
  - Freezing:            temperature_2m_min <= 0.0 C

Aggregation (Section 5.1):
  - Day risk per corridor = max waypoint score that day
  - 48h corridor risk     = max(Day0, Day1)
"""
from __future__ import annotations
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from tools.corridors import CORRIDOR_CATALOG, CORRIDOR_WAYPOINTS


# --- Risk thresholds (from playbook Section 6.1) ---
PRECIP_THRESHOLD_MM   = 15.0
WIND_GUST_THRESHOLD_KMH = 45.0
FREEZE_THRESHOLD_C    = 0.0


# --- Travel time buffer policy (Section 5.2) ---
RISK_TO_BUFFER = {
    0: {"buffer_pct": 0,  "label": "No buffer"},
    1: {"buffer_pct": 10, "label": "+10% buffer"},
    2: {"buffer_pct": 25, "label": "+25% buffer"},
    3: {"buffer_pct": 40, "label": "+40% buffer + escalation"},
}


# =====================================================================
# Legacy single-point interface (kept so old code keeps working)
# =====================================================================

def get_weather_forecast(lat: str, lon: str, tz: str) -> Dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,wind_gusts_10m_max",
        "timezone": tz,
        "forecast_days": 2,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def derive_dispatch_weather_risk(forecast: Dict[str, Any]) -> Dict[str, Any]:
    """Single-point risk; aggregates across the 2-day forecast horizon."""
    daily = forecast.get("daily", {})
    precip = daily.get("precipitation_sum", []) or []
    gusts = daily.get("wind_gusts_10m_max", []) or []
    tmin = daily.get("temperature_2m_min", []) or []

    max_precip = max(precip) if precip else 0.0
    max_gusts = max(gusts) if gusts else 0.0
    min_temp = min(tmin) if tmin else None

    flags = {
        "heavy_rain_risk": max_precip >= PRECIP_THRESHOLD_MM,
        "high_wind_risk":  max_gusts >= WIND_GUST_THRESHOLD_KMH,
        "freezing_risk":   (min_temp is not None and min_temp <= FREEZE_THRESHOLD_C),
    }
    score = int(flags["heavy_rain_risk"]) + int(flags["high_wind_risk"]) + int(flags["freezing_risk"])

    return {
        "max_precip_mm_day": float(max_precip),
        "max_wind_gust_kmh": float(max_gusts),
        "min_temp_c": float(min_temp) if min_temp is not None else None,
        "risk_flags": flags,
        "risk_score_0_3": score,
    }


# =====================================================================
# Per-waypoint / per-corridor (the real Day 3 work)
# =====================================================================

def _score_day(precip_mm: float, wind_gust_kmh: float, temp_min_c: float) -> Dict[str, Any]:
    """Score a single (waypoint, day) using playbook Section 6.1 triggers."""
    flags = {
        "heavy_rain_risk": precip_mm >= PRECIP_THRESHOLD_MM,
        "high_wind_risk":  wind_gust_kmh >= WIND_GUST_THRESHOLD_KMH,
        "freezing_risk":   temp_min_c <= FREEZE_THRESHOLD_C,
    }
    score = int(flags["heavy_rain_risk"]) + int(flags["high_wind_risk"]) + int(flags["freezing_risk"])
    return {
        "score": score,
        "flags": flags,
        "metrics": {
            "precipitation_mm": float(precip_mm),
            "wind_gust_kmh":    float(wind_gust_kmh),
            "temp_min_c":       float(temp_min_c),
        },
    }


def _fetch_waypoint_forecast(waypoint: Dict, tz: str) -> Dict[str, Any]:
    """Hit Open-Meteo for one waypoint and return per-day risk for Day0/Day1."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": waypoint["lat"],
        "longitude": waypoint["lon"],
        "daily": "precipitation_sum,temperature_2m_min,wind_gusts_10m_max",
        "timezone": tz,
        "forecast_days": 2,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    j = r.json()
    daily = j.get("daily", {})

    precip = daily.get("precipitation_sum", [0.0, 0.0])
    gusts  = daily.get("wind_gusts_10m_max", [0.0, 0.0])
    tmin   = daily.get("temperature_2m_min", [99.0, 99.0])

    # Pad if API returned fewer than 2 days (rare but defensive)
    while len(precip) < 2: precip.append(0.0)
    while len(gusts)  < 2: gusts.append(0.0)
    while len(tmin)   < 2: tmin.append(99.0)

    return {
        "waypoint_id": waypoint["waypoint_id"],
        "city": waypoint["city"],
        "Day0": _score_day(precip[0], gusts[0], tmin[0]),
        "Day1": _score_day(precip[1], gusts[1], tmin[1]),
    }


def get_weather_risk_by_corridor(tz: str = "America/New_York") -> Dict[str, Any]:
    """
    Fetch weather for every waypoint in every corridor (in parallel),
    aggregate to corridor-level risk per Section 5.1, and return a
    structured dict the Planner and Auditor can consume.

    Output structure:
      {
        "C1_I95_NJ_BOS": {
            "name": "...",
            "default_sla_tier": 1,
            "Day0": {"score": 2, "buffer": {...}, "drivers": ["high_wind_risk"]},
            "Day1": {"score": 1, ...},
            "max_48h_score": 2,
            "max_48h_buffer": {"buffer_pct": 25, "label": "+25% buffer"},
            "escalation_required": False,
            "waypoints": [ ... per-waypoint detail ... ],
        },
        "C2_NJ_PHL": { ... },
      }
    """
    out: Dict[str, Any] = {}

    # Parallel fetch across all waypoints in all corridors
    futures = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for corridor_id, waypoints in CORRIDOR_WAYPOINTS.items():
            for wp in waypoints:
                fut = ex.submit(_fetch_waypoint_forecast, wp, tz)
                futures[fut] = (corridor_id, wp)

        # Collect results as they complete
        wp_results: Dict[str, List[Dict]] = {cid: [] for cid in CORRIDOR_WAYPOINTS.keys()}
        for fut in as_completed(futures):
            corridor_id, _wp = futures[fut]
            try:
                wp_results[corridor_id].append(fut.result())
            except Exception as e:
                # Defensive: if one waypoint fails, log but don't kill the whole pipeline
                wp_results[corridor_id].append({
                    "waypoint_id": _wp["waypoint_id"],
                    "city": _wp["city"],
                    "error": str(e),
                    "Day0": {"score": 0, "flags": {}, "metrics": {}},
                    "Day1": {"score": 0, "flags": {}, "metrics": {}},
                })

    # Aggregate per corridor
    for corridor_id, meta in CORRIDOR_CATALOG.items():
        wps = wp_results.get(corridor_id, [])

        day0_max = max((w["Day0"]["score"] for w in wps), default=0)
        day1_max = max((w["Day1"]["score"] for w in wps), default=0)
        max_48h  = max(day0_max, day1_max)

        # Collect which flags were triggered on each day (across all waypoints)
        def collect_drivers(day_key: str) -> List[str]:
            drivers = set()
            for w in wps:
                for flag, fired in w[day_key].get("flags", {}).items():
                    if fired:
                        drivers.add(flag)
            return sorted(drivers)

        out[corridor_id] = {
            "name": meta["name"],
            "default_sla_tier": meta["default_sla_tier"],
            "Day0": {
                "score": day0_max,
                "buffer": RISK_TO_BUFFER[day0_max],
                "drivers": collect_drivers("Day0"),
            },
            "Day1": {
                "score": day1_max,
                "buffer": RISK_TO_BUFFER[day1_max],
                "drivers": collect_drivers("Day1"),
            },
            "max_48h_score": max_48h,
            "max_48h_buffer": RISK_TO_BUFFER[max_48h],
            "escalation_required": max_48h >= 3,
            "waypoints": wps,
        }

    return out


def format_corridor_weather_for_prompt(weather_by_corridor: Dict[str, Any]) -> str:
    """Pretty-print per-corridor weather for inclusion in agent prompts."""
    lines = ["=== Per-Corridor Weather Risk (48h horizon) ==="]
    for corridor_id, data in weather_by_corridor.items():
        lines.append(f"\n{corridor_id} ({data['name']}):")
        lines.append(f"  Day0 risk: {data['Day0']['score']}/3 -> {data['Day0']['buffer']['label']}; drivers: {data['Day0']['drivers'] or 'none'}")
        lines.append(f"  Day1 risk: {data['Day1']['score']}/3 -> {data['Day1']['buffer']['label']}; drivers: {data['Day1']['drivers'] or 'none'}")
        lines.append(f"  48h max:   {data['max_48h_score']}/3 -> {data['max_48h_buffer']['label']}")
        if data["escalation_required"]:
            lines.append(f"  *** ESCALATION REQUIRED (risk_score = 3) ***")
    return "\n".join(lines)

"""
Standalone test for per-corridor weather (Day 3).
No OpenAI calls — just hits the free Open-Meteo API.

Usage (from project root, with venv active):
    python src/test_weather.py
"""
from __future__ import annotations
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from tools.weather_tools import get_weather_risk_by_corridor, format_corridor_weather_for_prompt


def main():
    print("Fetching weather across all 9 waypoints (parallel)...\n")
    weather = get_weather_risk_by_corridor(tz="America/New_York")

    print("=" * 60)
    print("PRETTY SUMMARY")
    print("=" * 60)
    print(format_corridor_weather_for_prompt(weather))

    print("\n" + "=" * 60)
    print("FULL STRUCTURED OUTPUT")
    print("=" * 60)

    # Print each corridor with its waypoint detail
    for corridor_id, data in weather.items():
        print(f"\n[{corridor_id}] {data['name']}")
        print(f"  Default SLA tier: {data['default_sla_tier']}")
        print(f"  Day0: score={data['Day0']['score']}/3, drivers={data['Day0']['drivers']}")
        print(f"  Day1: score={data['Day1']['score']}/3, drivers={data['Day1']['drivers']}")
        print(f"  48h max: {data['max_48h_score']}/3 ({data['max_48h_buffer']['label']})")
        print(f"  Escalation required: {data['escalation_required']}")
        print(f"  Waypoint detail:")
        for wp in data["waypoints"]:
            d0 = wp["Day0"]
            d1 = wp["Day1"]
            print(f"    {wp['waypoint_id']:>6} {wp['city']:<22} | "
                  f"D0 score={d0['score']} (precip={d0['metrics'].get('precipitation_mm', 0):.1f}mm, "
                  f"gust={d0['metrics'].get('wind_gust_kmh', 0):.1f}kmh, "
                  f"min={d0['metrics'].get('temp_min_c', 0):.1f}C) | "
                  f"D1 score={d1['score']}")


if __name__ == "__main__":
    main()

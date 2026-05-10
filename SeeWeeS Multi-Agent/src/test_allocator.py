"""
Standalone test for the resource allocator (Day 4).
No OpenAI calls, no network — pure logic test.

Usage (from project root, with venv active):
    python src/test_allocator.py
"""
from __future__ import annotations
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from tools.reconciliation import reconcile_shipments
from tools.resources import load_resource_pools
from tools.allocator import allocate, format_allocation_for_prompt


def main():
    csv_path = "data-for-enhancement/Incoming_shipments_14d_multi_corridor.csv"
    resources_path = "data-for-enhancement/Resource_availability_48h.csv"

    print("Step 1: Reconciliation")
    rec = reconcile_shipments(csv_path)
    print(f"  Kept: {rec.summary['rows_kept']}, Excluded: {rec.summary['rows_excluded']}")

    print("\nStep 2: Resource pools")
    pools = load_resource_pools(resources_path)
    for day, pool in pools.items():
        print(f"  {day}: {pool.to_dict()}")

    print("\nStep 3: Allocation (mocked clear weather, risk=0)")
    weather_mock = {
        "C1_I95_NJ_BOS": {"Day0": {"score": 0}, "Day1": {"score": 0}},
        "C2_NJ_PHL":     {"Day0": {"score": 0}, "Day1": {"score": 0}},
    }
    result = allocate(rec.kpis_by_corridor, weather_mock, pools)

    print("\n" + "=" * 60)
    print("ALLOCATION RESULT")
    print("=" * 60)
    print(format_allocation_for_prompt(result))

    # Stress test
    print("\n\n" + "=" * 60)
    print("STRESS TEST: high weather on C1 (risk=2), reload pools")
    print("=" * 60)
    pools2 = load_resource_pools(resources_path)
    weather_stress = {
        "C1_I95_NJ_BOS": {"Day0": {"score": 2}, "Day1": {"score": 1}},
        "C2_NJ_PHL":     {"Day0": {"score": 0}, "Day1": {"score": 0}},
    }
    result2 = allocate(rec.kpis_by_corridor, weather_stress, pools2)
    print(format_allocation_for_prompt(result2))


if __name__ == "__main__":
    main()

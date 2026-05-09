"""
Standalone test for the AuditorAgent (Day 5).
No OpenAI calls — uses mock plan strings to verify each check fires correctly.

Usage (from project root, with venv active):
    python src/test_auditor.py
"""
from __future__ import annotations
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from auditor import run_audit


# Mock allocation result mirroring real Day 4 output
MOCK_ALLOC = {
    "pools_initial":  {"Day0": {"driver": 6, "truck_standard": 4, "truck_temp_controlled": 2}},
    "pools_remaining":{"Day0": {"driver": 0, "truck_standard": 0, "truck_temp_controlled": 0}},
    "allocations": [
        {
            "corridor_id": "C1_I95_NJ_BOS",
            "day": "Day0",
            "violations": [
                {"bucket": "tier2_cold", "tier": 2, "units_unfulfilled": 1,
                 "penalty_per_unit": 120, "penalty_total": 120,
                 "reason": "insufficient reefer capacity"}
            ],
        }
    ],
}

MOCK_WEATHER_NORMAL = {
    "C1_I95_NJ_BOS": {"max_48h_score": 1, "Day0": {"score": 1}, "Day1": {"score": 0}},
    "C2_NJ_PHL":     {"max_48h_score": 0, "Day0": {"score": 0}, "Day1": {"score": 0}},
}

MOCK_WEATHER_HIGH = {
    "C1_I95_NJ_BOS": {"max_48h_score": 3, "Day0": {"score": 3}, "Day1": {"score": 2}},
    "C2_NJ_PHL":     {"max_48h_score": 0, "Day0": {"score": 0}, "Day1": {"score": 0}},
}


def header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    # Scenario 1: GOOD plan — mentions corridor + penalty + violations
    good_plan = (
        "Dispatch plan for C1_I95_NJ_BOS Day0: 1 reefer, 2 standard trucks, 3 drivers. "
        "Violation noted: 1 tier2_cold unit unfulfilled, contributing 120 points to the "
        "total penalty score of 120. We will monitor reefer availability for next-day procurement."
    )

    header("SCENARIO 1: Good plan, normal weather — should PASS")
    rep = run_audit(good_plan, MOCK_ALLOC, MOCK_WEATHER_NORMAL, total_penalty=120)
    print(json.dumps(rep.to_dict(), indent=2))

    # Scenario 2: BAD plan — missing corridor name AND penalty number
    bad_plan = (
        "Cold-chain demand looks healthy; we'll prioritize critical shipments. "
        "Some constraints may apply across corridors but operations should continue smoothly."
    )

    header("SCENARIO 2: Sanitized plan, normal weather — should FAIL multiple checks")
    rep = run_audit(bad_plan, MOCK_ALLOC, MOCK_WEATHER_NORMAL, total_penalty=120)
    print(json.dumps(rep.to_dict(), indent=2))
    print("\nFeedback that would be sent back to planner:")
    print(rep.feedback_for_planner())

    # Scenario 3: Plan acknowledges everything but high weather demands escalation
    plan_no_escalation = (
        "Total penalty: 120 points. C1_I95_NJ_BOS Day0 has 1 tier2_cold unit unfulfilled. "
        "We'll apply travel buffers per playbook §5.2."
    )

    header("SCENARIO 3: Penalty acknowledged but missing 'escalation' wording, risk=3 — should FAIL")
    rep = run_audit(plan_no_escalation, MOCK_ALLOC, MOCK_WEATHER_HIGH, total_penalty=120)
    print(json.dumps(rep.to_dict(), indent=2))


if __name__ == "__main__":
    main()

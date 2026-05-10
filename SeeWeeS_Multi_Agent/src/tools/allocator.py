"""
Priority-weighted greedy allocator for SeeWeeS multi-corridor dispatch.

Inputs:
  - Per-corridor KPIs (from reconciliation): Day0/Day1 unit counts split by tier and cold-chain
  - Per-corridor weather (from weather_tools): risk score per corridor per day
  - Resource pools per day: drivers, standard trucks, reefer trucks

Output:
  - Allocation per (corridor, day): trucks_std, trucks_reefer, drivers
  - Per-bucket fulfillment stats (units_demanded, units_fulfilled, units_unfulfilled)
  - List of violations with penalty points
  - Total penalty score

Truck capacity model (playbook Section 8):
  - Each truck: 10 volume units
  - Each unique_item_id: 1 volume unit
  - Packing buffer: +10%
  - required_trucks = ceil((units * 1.10) / 10)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
import math

from tools.resources import ResourcePool


# --- Penalty constants (playbook Section 13.2) ---
PENALTY_TIER1_SLA      = 100
PENALTY_TIER2_SLA      = 40
PENALTY_COLD_CHAIN_ADD = 80   # additive on top of any SLA penalty
PENALTY_NON_SLA_DELAY  = 10

# Truck packing model (Section 8.2)
TRUCK_CAPACITY = 10
PACKING_BUFFER = 1.10


def required_trucks_for_units(units: int) -> int:
    """ceil((units * 1.10) / 10)"""
    if units <= 0:
        return 0
    return math.ceil((units * PACKING_BUFFER) / TRUCK_CAPACITY)


# --- Bucket priority order ---
# Higher priority = allocated first because penalty for missing it is higher
# (cold-chain mismatch = SLA penalty + 80; cold items can ONLY go on reefers)
BUCKETS_IN_PRIORITY = [
    ("tier1_cold",     1, True,  PENALTY_TIER1_SLA + PENALTY_COLD_CHAIN_ADD),  # 180
    ("tier2_cold",     2, True,  PENALTY_TIER2_SLA + PENALTY_COLD_CHAIN_ADD),  # 120
    ("tier1_standard", 1, False, PENALTY_TIER1_SLA),                            # 100
    ("tier2_standard", 2, False, PENALTY_TIER2_SLA),                            # 40
]


@dataclass
class CorridorDayAllocation:
    corridor_id: str
    day: str
    weather_risk: int = 0

    units_demanded_total: int = 0
    units_demanded_by_bucket: Dict[str, int] = field(default_factory=dict)

    units_fulfilled_total: int = 0
    units_fulfilled_by_bucket: Dict[str, int] = field(default_factory=dict)

    trucks_temp_controlled_used: int = 0
    trucks_standard_used: int = 0
    drivers_used: int = 0

    violations: List[Dict[str, Any]] = field(default_factory=list)
    penalty_points: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corridor_id": self.corridor_id,
            "day": self.day,
            "weather_risk": self.weather_risk,
            "units_demanded": self.units_demanded_total,
            "units_demanded_by_bucket": self.units_demanded_by_bucket,
            "units_fulfilled": self.units_fulfilled_total,
            "units_fulfilled_by_bucket": self.units_fulfilled_by_bucket,
            "trucks_temp_controlled_used": self.trucks_temp_controlled_used,
            "trucks_standard_used": self.trucks_standard_used,
            "drivers_used": self.drivers_used,
            "violations": self.violations,
            "penalty_points": self.penalty_points,
        }


@dataclass
class AllocationResult:
    allocations: List[CorridorDayAllocation] = field(default_factory=list)
    total_penalty: int = 0
    pools_initial: Dict[str, Dict[str, int]] = field(default_factory=dict)
    pools_remaining: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocations": [a.to_dict() for a in self.allocations],
            "total_penalty": self.total_penalty,
            "pools_initial": self.pools_initial,
            "pools_remaining": self.pools_remaining,
        }


def _allocate_bucket(
    alloc: CorridorDayAllocation,
    bucket_name: str,
    units_needed: int,
    cold_chain: bool,
    tier: int,
    base_penalty: int,
    pool: ResourcePool,
) -> None:
    """Try to allocate trucks + drivers from `pool` for this bucket. Mutates `pool` and `alloc`."""
    alloc.units_demanded_by_bucket[bucket_name] = units_needed
    alloc.units_demanded_total += units_needed

    if units_needed <= 0:
        alloc.units_fulfilled_by_bucket[bucket_name] = 0
        return

    trucks_needed = required_trucks_for_units(units_needed)
    units_fulfilled = 0

    if cold_chain:
        # Cold-chain MUST go on reefers — no substitution allowed
        trucks_avail = pool.truck_temp_controlled
        drivers_avail = pool.driver
        trucks_to_use = min(trucks_needed, trucks_avail, drivers_avail)

        if trucks_to_use > 0:
            units_capacity = trucks_to_use * TRUCK_CAPACITY
            units_fulfilled = min(units_needed, math.floor(units_capacity / PACKING_BUFFER))
            pool.truck_temp_controlled -= trucks_to_use
            pool.driver -= trucks_to_use
            alloc.trucks_temp_controlled_used += trucks_to_use
            alloc.drivers_used += trucks_to_use

        units_unfulfilled = units_needed - units_fulfilled
        if units_unfulfilled > 0:
            penalty = units_unfulfilled * base_penalty
            alloc.penalty_points += penalty
            alloc.violations.append({
                "bucket": bucket_name,
                "tier": tier,
                "cold_chain": True,
                "units_unfulfilled": units_unfulfilled,
                "penalty_per_unit": base_penalty,
                "penalty_total": penalty,
                "reason": f"insufficient reefer capacity (needed {trucks_needed} reefers, drivers_avail={drivers_avail})",
            })
    else:
        # Standard items — only use standard trucks (preserve reefers for cold-chain)
        trucks_avail = pool.truck_standard
        drivers_avail = pool.driver
        trucks_to_use = min(trucks_needed, trucks_avail, drivers_avail)

        if trucks_to_use > 0:
            units_capacity = trucks_to_use * TRUCK_CAPACITY
            units_fulfilled = min(units_needed, math.floor(units_capacity / PACKING_BUFFER))
            pool.truck_standard -= trucks_to_use
            pool.driver -= trucks_to_use
            alloc.trucks_standard_used += trucks_to_use
            alloc.drivers_used += trucks_to_use

        units_unfulfilled = units_needed - units_fulfilled
        if units_unfulfilled > 0:
            penalty = units_unfulfilled * base_penalty
            alloc.penalty_points += penalty
            alloc.violations.append({
                "bucket": bucket_name,
                "tier": tier,
                "cold_chain": False,
                "units_unfulfilled": units_unfulfilled,
                "penalty_per_unit": base_penalty,
                "penalty_total": penalty,
                "reason": f"insufficient standard truck/driver capacity (needed {trucks_needed} trucks, drivers_avail={drivers_avail})",
            })

    alloc.units_fulfilled_by_bucket[bucket_name] = units_fulfilled
    alloc.units_fulfilled_total += units_fulfilled


def allocate(
    kpis_by_corridor: Dict[str, Any],
    weather_by_corridor: Dict[str, Any],
    pools: Dict[str, ResourcePool],
) -> AllocationResult:
    """Greedy priority-weighted allocator across (corridor, day) pairs."""
    result = AllocationResult()
    result.pools_initial = {d: p.to_dict() for d, p in pools.items()}

    alloc_index: Dict[Tuple[str, str], CorridorDayAllocation] = {}

    for day in ["Day0", "Day1"]:
        if day not in pools:
            continue
        pool = pools[day]  # mutated as we allocate

        # Seed (corridor, day) allocations
        for corridor_id, corridor_kpis in kpis_by_corridor.items():
            if day not in corridor_kpis:
                continue
            risk = (
                weather_by_corridor.get(corridor_id, {})
                .get(day, {})
                .get("score", 0)
            )
            alloc_index[(corridor_id, day)] = CorridorDayAllocation(
                corridor_id=corridor_id,
                day=day,
                weather_risk=risk,
            )

        # Allocate buckets in priority order; within bucket, higher weather risk corridor first
        for bucket_name, tier, cold_chain, base_penalty in BUCKETS_IN_PRIORITY:
            corridor_order = sorted(
                kpis_by_corridor.keys(),
                key=lambda cid: -(weather_by_corridor.get(cid, {}).get(day, {}).get("score", 0)),
            )
            for corridor_id in corridor_order:
                day_kpis = kpis_by_corridor.get(corridor_id, {}).get(day, {})
                if not isinstance(day_kpis, dict):
                    continue
                units_needed = int(day_kpis.get(bucket_name, 0))
                alloc = alloc_index.get((corridor_id, day))
                if alloc is None:
                    continue
                _allocate_bucket(alloc, bucket_name, units_needed, cold_chain, tier, base_penalty, pool)

    result.allocations = sorted(alloc_index.values(), key=lambda a: (a.day, a.corridor_id))
    result.total_penalty = sum(a.penalty_points for a in result.allocations)
    result.pools_remaining = {d: p.to_dict() for d, p in pools.items()}
    return result


def format_allocation_for_prompt(result: AllocationResult) -> str:
    """Pretty-print the allocation for inclusion in the Planner prompt."""
    lines = ["=== Resource Allocation Plan (computed deterministically) ==="]
    lines.append(f"\nInitial pools: {result.pools_initial}")
    lines.append(f"Remaining pools after allocation: {result.pools_remaining}")
    lines.append(f"\nTOTAL PENALTY SCORE: {result.total_penalty} points")

    lines.append("\nPer-corridor / per-day allocation:")
    header = f"{'corridor':<18} {'day':<6} {'risk':<5} {'demand':<8} {'served':<8} {'reefers':<9} {'std':<5} {'drivers':<9} {'penalty':<8}"
    lines.append(header)
    lines.append("-" * len(header))
    for a in result.allocations:
        lines.append(
            f"{a.corridor_id:<18} {a.day:<6} {a.weather_risk:<5} "
            f"{a.units_demanded_total:<8} {a.units_fulfilled_total:<8} "
            f"{a.trucks_temp_controlled_used:<9} {a.trucks_standard_used:<5} "
            f"{a.drivers_used:<9} {a.penalty_points:<8}"
        )

    any_violations = any(a.violations for a in result.allocations)
    if any_violations:
        lines.append("\nViolations:")
        for a in result.allocations:
            for v in a.violations:
                lines.append(
                    f"  {a.corridor_id} {a.day} [{v['bucket']}]: "
                    f"{v['units_unfulfilled']} units unfulfilled @ {v['penalty_per_unit']}pts each "
                    f"= {v['penalty_total']}pts ({v['reason']})"
                )
    else:
        lines.append("\nNo violations — all demand fulfilled within resource constraints.")

    return "\n".join(lines)

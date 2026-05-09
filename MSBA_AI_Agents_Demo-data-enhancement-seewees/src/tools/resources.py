"""
Resource pool loader for SeeWeeS dispatch planning.

Loads `Resource_availability_48h.csv` and returns a structured per-day pool.

Resource types (from playbook Section 13.1):
  - driver
  - truck_standard
  - truck_temp_controlled  (the binding constraint — "reefer")
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import pandas as pd


@dataclass
class ResourcePool:
    """Per-day available pool. Mutated during allocation as resources are consumed."""
    driver: int = 0
    truck_standard: int = 0
    truck_temp_controlled: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "driver": self.driver,
            "truck_standard": self.truck_standard,
            "truck_temp_controlled": self.truck_temp_controlled,
        }

    def copy(self) -> "ResourcePool":
        return ResourcePool(self.driver, self.truck_standard, self.truck_temp_controlled)


def load_resource_pools(csv_path: str) -> Dict[str, ResourcePool]:
    """
    Returns: {"Day0": ResourcePool(...), "Day1": ResourcePool(...)}
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    pools: Dict[str, ResourcePool] = {}
    for day, day_df in df.groupby("day"):
        pool = ResourcePool()
        for _, row in day_df.iterrows():
            rtype = str(row["resource_type"]).strip()
            count = int(row["available_count"])
            if rtype == "driver":
                pool.driver = count
            elif rtype == "truck_standard":
                pool.truck_standard = count
            elif rtype == "truck_temp_controlled":
                pool.truck_temp_controlled = count
        pools[str(day)] = pool

    return pools

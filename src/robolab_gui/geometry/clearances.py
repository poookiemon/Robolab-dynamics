"""Clearance boundaries, safe traverse heights, and collision protection limits."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TravelBoundaries:
    min_x: float = 0.0
    max_x: float = 300.0
    min_y: float = 0.0
    max_y: float = 300.0
    min_z: float = 0.0
    max_z: float = 120.0


class ClearanceManager:
    SAFE_TRAVERSE_Z: float = 0.0
    DEFAULT_BOTTOM_CLEARANCE_MM: float = 1.0
    DEFAULT_BRIM_CLEARANCE_MM: float = 2.0
    DEFAULT_TOUCH_OFF_RETRACT_MM: float = 1.5

    def __init__(self, boundaries: Optional[TravelBoundaries] = None):
        self.boundaries = boundaries or TravelBoundaries()

    def is_within_bounds(self, x: float, y: float, z: Optional[float] = None) -> bool:
        if not (self.boundaries.min_x <= x <= self.boundaries.max_x):
            return False
        if not (self.boundaries.min_y <= y <= self.boundaries.max_y):
            return False
        if z is not None and not (self.boundaries.min_z <= z <= self.boundaries.max_z):
            return False
        return True

    def clamp_z(self, z: float) -> float:
        return max(self.boundaries.min_z, min(z, self.boundaries.max_z))

    def get_safe_traverse_z(self) -> float:
        return self.SAFE_TRAVERSE_Z

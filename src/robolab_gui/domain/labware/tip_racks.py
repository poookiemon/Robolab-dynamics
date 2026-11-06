"""Tip rack representations and pickup Z limits."""

from typing import Tuple, Any
from robolab_gui.domain.labware.base import LabwareBase


class TipRack96(LabwareBase):
    """96-Tip Rack (1000 µL, 300 µL, or 10 µL tips)."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "1000 µL Tip Rack (96 Tips)",
            "category": "tip_rack",
            "rows": 8,
            "columns": 12,
            "z_height_mm": 78.18,
            "well_depth_mm": 9.65,
            "well_radius_mm": 4.5,
            "max_safe_bottom_z": 98.0,
            "pitch_x_mm": 9.0,
            "pitch_y_mm": 9.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.pickup_limit_z = float(kwargs.get("pickup_limit_z", 95.0))
        self.pickup_force = int(kwargs.get("pickup_force", 26))

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        ox, oy = slot.origin_a1_xy
        return (ox - (c_idx * 9.0)), (oy + (r_idx * 9.0))

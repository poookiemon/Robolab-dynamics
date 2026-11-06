"""Tube rack representations (2mL Falcon microcentrifuge tubes and 50mL conical tubes)."""

from typing import Tuple, Any, Optional
from robolab_gui.domain.labware.base import LabwareBase


class TubeRack2x6_2mL(LabwareBase):
    """12-Tube Rack (2 rows A-B x 6 cols 1-6) for 2mL Falcon microcentrifuge tubes."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "12-Tube Rack 2x6 - 2 mL Falcon",
            "category": "tube_rack_2x6",
            "rows": 2,
            "columns": 6,
            "z_height_mm": 104.6,
            "well_depth_mm": 40.0,
            "well_radius_mm": 4.35,
            "max_safe_bottom_z": 103.0,
            "dead_volume_ul": 100.0,
            "max_volume_ul": 2000.0,
            "pitch_x_mm": 18.0,
            "pitch_y_mm": 18.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        orig_x = 245.0 if slot.x_abs >= 70.0 else (245.0 - 135.2)
        orig_y = 0.0 if slot.is_front_slot else slot.origin_a1_xy[1]
        return orig_x - (c_idx * 18.0), orig_y + (r_idx * 18.0)


class FalconRack50mL(LabwareBase):
    """3-Position 50 mL Falcon Conical Tube Rack for Slot 1 and Slot 2."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "3-Position 50mL Falcon Tube Rack",
            "category": "tube_rack_50ml",
            "rows": 1,
            "columns": 3,
            "z_height_mm": 115.0,
            "well_depth_mm": 110.0,
            "well_radius_mm": 14.5,
            "max_safe_bottom_z": 103.0,
            "dead_volume_ul": 1000.0,
            "max_volume_ul": 50000.0,
            "pitch_x_mm": 38.0,
            "pitch_y_mm": 0.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        if getattr(slot, "name", "") == "Slot_2":
            w_str = str(well_id or "").upper().strip()
            if w_str in ("A1", "1"):
                return 95.5, 13.0
            elif w_str in ("A2", "2"):
                return 57.0, 13.0
            return 12.0, 13.0
        r_idx, c_idx = self.parse_well(well_id)
        ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
        ox, oy = slot.origin_a1_xy
        return ox - (ci * 38.0), oy

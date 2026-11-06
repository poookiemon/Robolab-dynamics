"""Waste container representations for liquid discard and tip ejection."""

from typing import Tuple, Any
from robolab_gui.domain.labware.base import LabwareBase


class WasteTrough(LabwareBase):
    """Waste container for liquid discard and ejected tips (e.g. Slot 2 or Slot 6)."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "Liquid & Tip Waste Trough",
            "category": "waste",
            "rows": 1,
            "columns": 1,
            "z_height_mm": 43.35,
            "well_depth_mm": 43.35,
            "well_radius_mm": 30.0,
            "max_safe_bottom_z": 80.0,
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
        return slot.center_x, slot.center_y

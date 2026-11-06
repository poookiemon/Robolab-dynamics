"""Reagent reservoir definitions (3-well, 6-column, 7-column)."""

from typing import Tuple, Any, Optional
from robolab_gui.domain.labware.base import LabwareBase


class Reservoir3Well(LabwareBase):
    """3-Well Reagent Reservoir for Slot 1 and Slot 2 front risers."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "3-Well Reagent Reservoir",
            "category": "reservoir_3",
            "rows": 1,
            "columns": 3,
            "z_height_mm": 44.0,
            "well_depth_mm": 40.0,
            "well_radius_mm": 15.0,
            "max_safe_bottom_z": 102.0,
            "max_volume_ul": 60000.0,
            "pitch_x_mm": 42.6,
            "pitch_y_mm": 0.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        if getattr(slot, "name", "") == "Slot_2":
            col_x = [95.5, 57.0, 12.0]
            _, c_idx = self.parse_well(well_id)
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
            if c_idx is None and str(well_id) in ("1", "2", "3"):
                ci = int(well_id) - 1
            return col_x[ci], 13.0
        _, c_idx = self.parse_well(well_id)
        ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
        if c_idx is None and str(well_id) in ("1", "2", "3"):
            ci = int(well_id) - 1
        ox, oy = slot.origin_a1_xy
        return ox - (ci * 42.6), oy


class Reservoir6Column(LabwareBase):
    """6-Column Reagent Reservoir."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "6-Column Reagent Reservoir",
            "category": "reservoir_6",
            "rows": 1,
            "columns": 6,
            "z_height_mm": 44.0,
            "well_depth_mm": 40.0,
            "well_radius_mm": 8.0,
            "max_safe_bottom_z": 102.0,
            "max_volume_ul": 40000.0,
            "pitch_x_mm": 16.5,
            "pitch_y_mm": 0.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        col_dx = [3.0, -12.0, -30.0, -46.5, -63.0, -79.5]
        clean_w = str(well_id or "").upper().strip().lstrip("R")
        ci = (int(clean_w) - 1) if clean_w.isdigit() and 1 <= int(clean_w) <= 6 else 0
        ox, oy = slot.origin_a1_xy
        return ox + col_dx[ci], oy + (0.0 if slot.is_front_slot else 31.5)


class Reservoir7Column(LabwareBase):
    """7-Column Reagent Reservoir for Slot 6 media storage and waste."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "7-Column Reagent Reservoir",
            "category": "reservoir_7",
            "rows": 1,
            "columns": 7,
            "z_height_mm": 44.0,
            "well_depth_mm": 40.0,
            "well_radius_mm": 7.0,
            "max_safe_bottom_z": 102.0,
            "max_volume_ul": 35000.0,
            "pitch_x_mm": 15.0,
            "pitch_y_mm": 0.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        col_x = [108.81, 93.81, 75.06, 56.31, 37.56, 18.81, 5.91]
        clean_w = str(well_id or "").upper().strip().lstrip("R")
        ci = (int(clean_w) - 1) if clean_w.isdigit() and 1 <= int(clean_w) <= 7 else 0
        if getattr(slot, "name", "") == "Slot_6":
            return col_x[ci], 183.64
        ox, oy = slot.origin_a1_xy
        return ox + 3.81 - (ci * 15.0), oy + (0.0 if slot.is_front_slot else 30.67)

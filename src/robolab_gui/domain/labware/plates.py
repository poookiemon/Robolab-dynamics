"""Microplate definitions (96-well standard plates and Myriamed 48-well EHM plates)."""

from typing import Tuple, Optional, Any
from robolab_gui.domain.labware.base import LabwareBase


class Plate96(LabwareBase):
    """Standard ANSI/SLAS 96-well microplate (8 rows A-H, 12 cols 1-12, 9.0mm pitch)."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "Generic 96-Well Microplate",
            "category": "plate96",
            "rows": 8,
            "columns": 12,
            "z_height_mm": 14.3,
            "well_depth_mm": 10.8,
            "well_radius_mm": 3.4,
            "max_safe_bottom_z": 100.0,
            "dead_volume_ul": 10.0,
            "max_volume_ul": 300.0,
            "pitch_x_mm": 9.0,
            "pitch_y_mm": 9.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)


class Plate48Myriamed(LabwareBase):
    """Myriamed 48-Well Engineered Heart Muscle (EHM) Culture Plate."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "Myriamed 48-Well EHM Plate",
            "category": "ehm48",
            "rows": 8,
            "columns": 6,
            "z_height_mm": 78.42,
            "well_depth_mm": 16.90,
            "well_radius_mm": 4.5,
            "max_safe_bottom_z": 95.0,
            "dead_volume_ul": 50.0,
            "max_volume_ul": 1000.0,
            "pitch_x_mm": 18.0,
            "pitch_y_mm": 9.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        col_dx = [0.0, -18.0, -36.0, -54.0, -72.0, -90.0]
        row_dy = [1.0, 9.0, 18.0, 26.0, 35.0, 44.0, 54.0, 63.0]
        ox, oy = slot.origin_a1_xy
        return ox + col_dx[c_idx] + 1.0, oy + row_dy[r_idx] - 2.0

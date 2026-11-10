"""Coordinate system, bed transforms, and well location resolution for RoboLab.

Defines nominal and physically calibrated slot origins, column tables, and well
transformation math across standard multiwell plates, tube racks, reservoirs, and waste troughs.
"""

from typing import Dict, Tuple, Optional, List
import re

# Physically jog-calibrated machine XY coordinates of "well A1" for each slot
DEFAULT_SLOT_A1_ORIGINS: Dict[str, Tuple[float, float]] = {
    "Slot_1": (238.2, 13.0),   # Front right (height-block slot, 2mL Falcon rack A1)
    "Slot_2": (95.5, 13.0),    # Front left (3-well reservoir / waste trough A1)
    "Slot_3": (243.81, 52.64), # Mid right (Machine 2 1-10µL: A1 X=243.81, A1 Y=52.64, Center Y=84.14)
    "Slot_4": (105.63, 57.12), # Mid left (Machine 2 1-10µL calibrated: A1 X=105.63, A1 Y=57.12, Center Y=84.14)
    "Slot_5": (243.24, 146.81), # Rear right (Machine 2 1-10µL: Center Y=178.31 -> A1 Y=146.81)
    "Slot_6": (105.60, 146.81), # Rear left (Machine 2 1-10µL: Center Y=178.31 -> A1 Y=146.81)
}

# Calibrated per-slot column X tables for 96-format labware (overrides pitch math)
DEFAULT_SLOT_96_COL_OVERRIDES: Dict[str, List[float]] = {
    "Slot_4": [round(105.63 - (c * 9.0), 2) for c in range(12)],
    "Slot_5": [round(243.24 - (c * 9.0), 2) for c in range(12)],
}

# Calibrated nominal Z for 96-well microplates: (deep / aspirate / mix, brim / dispense)
DEFAULT_SLOT_96_PLATE_Z: Dict[str, Tuple[float, float]] = {
    "Slot_3": (78.40, 68.43),
    "Slot_4": (78.40, 68.43),
    "Slot_5": (78.40, 68.43),
    "Slot_6": (78.40, 68.43),
}


def parse_well(well_id: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Parse a well identifier into 0-indexed row and column indices."""
    if not well_id:
        return None, None
    s = str(well_id).strip().upper()
    if not s:
        return None, None

    if s.isdigit():
        return None, int(s) - 1
    if s.startswith("R") and s[1:].isdigit():
        return None, int(s[1:]) - 1

    match = re.match(r"^([A-Z]+)(\d+)$", s)
    if not match:
        return None, None

    row_letters, col_str = match.groups()
    col_idx = int(col_str) - 1

    row_idx = 0
    for char in row_letters:
        row_idx = row_idx * 26 + (ord(char) - ord("A") + 1)
    row_idx -= 1

    if row_idx < 0 or col_idx < 0:
        return None, None
    return row_idx, col_idx


def format_well(row_idx: int, col_idx: int) -> str:
    """Format row and column indices into standard alphanumeric notation."""
    row_char = chr(ord("A") + row_idx)
    return f"{row_char}{col_idx + 1}"


class CoordinateService:
    """Handles machine coordinate transforms for slots, labware, and wells."""

    def __init__(
        self,
        slot_a1_origins: Optional[Dict[str, Tuple[float, float]]] = None,
        col_overrides: Optional[Dict[str, List[float]]] = None,
        max_x: float = 300.0,
        max_y: float = 300.0,
        max_z: float = 120.0,
    ):
        self.slot_a1_origins = slot_a1_origins or dict(DEFAULT_SLOT_A1_ORIGINS)
        self.col_overrides = col_overrides or dict(DEFAULT_SLOT_96_COL_OVERRIDES)
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

    def get_slot_a1_origin(self, slot_name: str) -> Tuple[float, float]:
        norm_slot = self.normalize_slot_name(slot_name)
        return self.slot_a1_origins.get(norm_slot, (105.0, 53.0))

    @staticmethod
    def normalize_slot_name(slot: str) -> str:
        s = str(slot).strip()
        s_lower = s.lower().replace("-", "_").replace(" ", "_")
        for i in range(1, 7):
            if s_lower in (f"slot_{i}", f"slot{i}", str(i)):
                return f"Slot_{i}"
        return s

    def clamp(self, x: float, y: float, z: Optional[float] = None) -> Tuple[float, float, Optional[float]]:
        cx = max(0.0, min(float(x), self.max_x))
        cy = max(0.0, min(float(y), self.max_y))
        cz = None if z is None else max(0.0, min(float(z), self.max_z))
        return cx, cy, cz

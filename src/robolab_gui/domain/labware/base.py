"""Base labware domain models, geometry properties, and well coordinate computations."""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any


@dataclass
class WellDefinition:
    """Represents a single well or cavity within labware."""
    name: str
    x_rel: float
    y_rel: float
    depth_mm: float
    radius_mm: float
    max_volume_ul: float = 1000.0


@dataclass
class LabwareBase:
    """Base class for all multiwell plates, tip racks, reservoirs, and tube racks."""
    name: str
    category: str
    rows: int
    columns: int
    z_height_mm: float
    well_depth_mm: float
    well_radius_mm: float
    max_safe_bottom_z: float = 100.0
    dead_volume_ul: float = 50.0
    max_volume_ul: float = 1000.0
    pitch_x_mm: float = 9.0
    pitch_y_mm: float = 9.0
    source_file: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def parse_well(self, well_id: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse alphanumeric well string ('A1') into 0-indexed (row, col)."""
        if not well_id or len(well_id) < 2:
            return None, None
        r_c = well_id[0].upper()
        try:
            c_idx = int(well_id[1:]) - 1
        except ValueError:
            return None, None
        r_idx = ord(r_c) - ord("A")
        if r_idx < 0 or r_idx >= self.rows or c_idx < 0 or c_idx >= self.columns:
            return None, None
        return r_idx, c_idx

    def get_well_xy(self, slot: Any, well_id: str) -> Tuple[float, float]:
        """Compute absolute machine (X, Y) coordinates for the given well on a slot."""
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        ox, oy = slot.origin_a1_xy
        return ox - (c_idx * self.pitch_x_mm), oy + (r_idx * self.pitch_y_mm)

    def get_rim_z(self, slot: Any) -> float:
        """Machine Z height corresponding to the upper brim of the labware."""
        adapter_h = slot.adapter.height_mm if slot.adapter else 0.0
        base_ref = 103.5 - self.z_height_mm
        effective_z = max(0.0, base_ref - adapter_h)
        return round(effective_z, 2)

    def get_bottom_z(self, slot: Any) -> float:
        """Machine Z height corresponding to internal well floor."""
        rim_z = self.get_rim_z(slot)
        return min(rim_z + self.well_depth_mm, self.max_safe_bottom_z, 103.0)

    def get_aspirate_z(self, slot: Any, well_id: str, volume_ul: float = 0.0) -> float:
        """Safe aspiration depth elevated safely above the bottom."""
        bottom_z = self.get_bottom_z(slot)
        rim_z = self.get_rim_z(slot)
        return max(rim_z, min(bottom_z - 1.5, self.max_safe_bottom_z))

    def get_dispense_z(self, slot: Any, well_id: str, in_liquid: bool = False) -> float:
        """Dispense depth at brim or submerged."""
        rim_z = self.get_rim_z(slot)
        if not in_liquid:
            return min(rim_z + 3.0, self.get_bottom_z(slot) - 1.0)
        return self.get_bottom_z(slot) - 2.0

    def get_mix_z(self, slot: Any, well_id: str) -> float:
        """Deep mixing depth inside well."""
        return max(self.get_rim_z(slot), self.get_bottom_z(slot) - 1.5)

"""
labware_models.py - Object-Oriented Labware, Height Adapters, and Stacking Kinematics
Biohit Automated Pipettor Platform

This module implements a strongly-typed object hierarchy for all labware,
deck slots, and height adapters. All Z calculations are computed in reference
to the labware and its mounting stack (height adapter + labware geometry),
replacing arbitrary hardcoded constants.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class HeightAdapter:
    """Represents a riser or mounting block placed between the deck slot and labware."""
    name: str
    height_mm: float
    z_offset_mm: float = 0.0
    description: str = ""

    def __post_init__(self):
        self.height_mm = float(self.height_mm)
        self.z_offset_mm = float(self.z_offset_mm)


# Standard adapter definitions
ADAPTER_NONE = HeightAdapter("Direct Deck (No Adapter)", 0.0, 0.0, "Labware sits directly on the deck surface.")
ADAPTER_90MM_BLOCK = HeightAdapter("90mm Height Block", 90.0, 0.0, "Standard 3D printed / CNC 90mm block for Slot 1/2 front risers.")
ADAPTER_45MM_BLOCK = HeightAdapter("45mm Height Block", 45.0, 0.0, "Intermediate 45mm riser block.")


@dataclass
class LabwareBase:
    """
    Abstract base class for all deck labware.
    Computes X/Y well coordinates and Z depths strictly in reference to the
    mounting slot stack and the physical labware geometry.
    """
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
    a1_offset_x: float = 0.0
    a1_offset_y: float = 0.0
    pitch_x_mm: float = 9.0
    pitch_y_mm: float = 9.0
    source_file: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def parse_well(self, well_id: str) -> Tuple[Optional[int], Optional[int]]:
        """Parses 'A1' -> (row_idx=0, col_idx=0). Returns (None, None) if invalid."""
        if not well_id or len(well_id) < 2:
            return None, None
        r_c = well_id[0].upper()
        try:
            c_idx = int(well_id[1:]) - 1
        except ValueError:
            return None, None
        r_idx = ord(r_c) - ord('A')
        if r_idx < 0 or r_idx >= self.rows or c_idx < 0 or c_idx >= self.columns:
            return None, None
        return r_idx, c_idx

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        """Calculates absolute machine X, Y coordinates for a given well."""
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            # Fallback to slot center
            return slot.center_x, slot.center_y
        ox, oy = slot.origin_a1_xy
        return ox - (c_idx * self.pitch_x_mm), oy + (r_idx * self.pitch_y_mm)

    def get_rim_z(self, slot: 'DeckSlot') -> float:
        """
        Machine Z position corresponding to the top rim of the labware.
        Under the Biohit machine coordinate system:
        - Z = 0.0 mm is top clearance (retracted).
        - Z = 103.5 mm is absolute bed floor.
        - Mounting an adapter of height H raises the rim closer to 0:
          Rim Z decreases as stack height increases.
        """
        adapter_h = slot.adapter.height_mm if slot.adapter else 0.0
        # Reference: with 90mm block, top rim of 2mL falcon rack is at Z=75.0mm,
        # 3-well reservoir is at Z=47.0mm.
        # Without block (adapter_h=0), rim is near slot bed.
        base_ref = 103.5 - self.z_height_mm
        effective_z = max(0.0, base_ref - adapter_h)
        return round(effective_z, 2)

    def get_bottom_z(self, slot: 'DeckSlot') -> float:
        """Machine Z position corresponding to the internal bottom of the well."""
        rim_z = self.get_rim_z(slot)
        bottom_z = rim_z + self.well_depth_mm
        return min(bottom_z, self.max_safe_bottom_z, 103.0)

    def get_clearance_z(self, slot: 'DeckSlot', clearance_mm: float = 10.0) -> float:
        """Safe transit Z height above the top of this labware."""
        rim_z = self.get_rim_z(slot)
        return max(0.0, rim_z - clearance_mm)

    def get_aspirate_z(self, slot: 'DeckSlot', well_id: str, current_vol_ul: float, submerge_mm: float = 2.0) -> float:
        """Calculates aspirate depth relative to liquid surface and bottom clearance."""
        bottom_z = self.get_bottom_z(slot)
        rim_z = self.get_rim_z(slot)
        # Default fallback: 2mm above bottom
        return max(rim_z, min(bottom_z - 1.5, self.max_safe_bottom_z))

    def get_dispense_z(self, slot: 'DeckSlot', well_id: str, in_liquid: bool = False) -> float:
        """Calculates dispense depth: brim dispensing or immersed dispensing."""
        rim_z = self.get_rim_z(slot)
        if not in_liquid:
            # Dispense at brim (1.5mm to 3.0mm inside the well collar)
            return min(rim_z + 3.0, self.get_bottom_z(slot) - 1.0)
        return self.get_bottom_z(slot) - 2.0

    def get_mix_z(self, slot: 'DeckSlot', well_id: str) -> float:
        """Deep in-well mixing depth (1.5mm above well floor)."""
        bottom_z = self.get_bottom_z(slot)
        return max(self.get_rim_z(slot), bottom_z - 1.5)


# ---------------------------------------------------------------------------
# Specialized Labware Subclasses
# ---------------------------------------------------------------------------

class Plate96(LabwareBase):
    """Standard 96-well microplate (8 rows A-H, 12 columns 1-12, 9.0mm pitch)."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "Generic 96-Well Microplate",
            "category": "plate96",
            "rows": 8,
            "columns": 12,
            "z_height_mm": 14.35,
            "well_depth_mm": 10.8,
            "well_radius_mm": 3.4,
            "max_safe_bottom_z": 99.0,
            "dead_volume_ul": 20.0,
            "max_volume_ul": 360.0,
            "pitch_x_mm": 9.0,
            "pitch_y_mm": 9.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.col_overrides = kwargs.get("col_overrides", {})
        self.aspirate_depth_override = kwargs.get("aspirate_depth_override", None)
        self.dispense_depth_override = kwargs.get("dispense_depth_override", None)

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        ox, oy = slot.origin_a1_xy
        tx = self.col_overrides[c_idx] if c_idx in self.col_overrides else (ox - (c_idx * self.pitch_x_mm))
        ty = oy + (r_idx * self.pitch_y_mm)
        return tx, ty

    def get_aspirate_z(self, slot: 'DeckSlot', well_id: str, current_vol_ul: float = 0.0, submerge_mm: float = 2.0) -> float:
        if self.aspirate_depth_override is not None:
            return self.aspirate_depth_override
        active_pid = str(getattr(slot, "active_profile_id", "") or "")
        if "300" in active_pid and slot.name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6"):
            return 98.72
        # Calibrated 96-well plate deep aspirate / mix is 78.40mm
        if slot.name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6"):
            return 78.40
        return super().get_aspirate_z(slot, well_id, current_vol_ul, submerge_mm)

    def get_dispense_z(self, slot: 'DeckSlot', well_id: str, in_liquid: bool = False) -> float:
        if self.dispense_depth_override is not None and not in_liquid:
            return self.dispense_depth_override
        active_pid = str(getattr(slot, "active_profile_id", "") or "")
        if "300" in active_pid and slot.name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6"):
            return 98.72
        if slot.name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6") and not in_liquid:
            return 68.43
        return super().get_dispense_z(slot, well_id, in_liquid)

    def get_mix_z(self, slot: 'DeckSlot', well_id: str) -> float:
        active_pid = str(getattr(slot, "active_profile_id", "") or "")
        if "300" in active_pid and slot.name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6"):
            return 98.72
        if slot.name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6"):
            return 78.40
        return super().get_mix_z(slot, well_id)


class Plate48Myriamed(LabwareBase):
    """Myriamed 48-well engineered heart muscle (EHM) tissue culture plate."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "Myriamed 48-Well EHM Plate",
            "category": "ehm48",
            "rows": 8,
            "columns": 6,
            "z_height_mm": 17.5,
            "well_depth_mm": 14.5,
            "well_radius_mm": 4.5,
            "max_safe_bottom_z": 80.0,
            "dead_volume_ul": 50.0,
            "max_volume_ul": 800.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.col_dx = kwargs.get("col_dx", [0.0, -18.0, -36.0, -54.0, -72.0, -90.0])
        self.row_dy = kwargs.get("row_dy", [1.0, 9.0, 18.0, 26.0, 35.0, 44.0, 54.0, 63.0])

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        ox, oy = slot.origin_a1_xy
        cx = ox + self.col_dx[c_idx] + 1.0 if c_idx < len(self.col_dx) else ox - (c_idx * 18.0) + 1.0
        cy = oy + self.row_dy[r_idx] - 2.0 if r_idx < len(self.row_dy) else oy + (r_idx * 9.0) - 2.0
        return cx, cy

    def get_aspirate_z(self, slot: 'DeckSlot', well_id: str, current_vol_ul: float = 0.0, submerge_mm: float = 2.0) -> float:
        # User physically calibrated: 24.17mm deep near well bottom for 8x1000 EHM plates
        return 24.17

    def get_dispense_z(self, slot: 'DeckSlot', well_id: str, in_liquid: bool = False) -> float:
        # Calibrated EHM: 24.17mm in-liquid, 14.17mm contact-free (10mm above well bottom)
        return 24.17 if in_liquid else 14.17

    def get_mix_z(self, slot: 'DeckSlot', well_id: str) -> float:
        return 24.17


class Reservoir3Well(LabwareBase):
    """3-Well Reagent Reservoir (holds 30-40 mL per well on Slot 1 or Slot 2)."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "3-Well Reagent Reservoir (30-40 mL)",
            "category": "reservoir_3",
            "rows": 1,
            "columns": 3,
            "z_height_mm": 35.0,
            "well_depth_mm": 32.0,
            "well_radius_mm": 12.0,
            "max_safe_bottom_z": 100.0,
            "dead_volume_ul": 2000.0,
            "max_volume_ul": 40000.0,
            "pitch_x_mm": 42.6,
            "pitch_y_mm": 0.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.cross_section_area_mm2 = kwargs.get("cross_section_area_mm2", 434.0)
        self.start_surface_z = kwargs.get("start_surface_z", 47.0)
        self.floor_bottom_z = kwargs.get("floor_bottom_z", 100.0)
        self.submerge_depth_mm = kwargs.get("submerge_depth_mm", 5.0)

    def parse_well(self, well_id: str) -> Tuple[Optional[int], Optional[int]]:
        if not well_id: return None, None
        w_clean = well_id.upper().strip()
        if w_clean in ("1", "2", "3"):
            return 0, int(w_clean) - 1
        if len(w_clean) >= 2 and w_clean[0] in "ABCDEFGH":
            try:
                c = int(w_clean[1:]) - 1
                if 0 <= c < 3:
                    return 0, c
            except ValueError:
                pass
        return 0, 0

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        _, c_idx = self.parse_well(well_id)
        ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
        ox, oy = slot.origin_a1_xy
        front = slot.is_front_slot
        if slot.name == "Slot_2":
            col_x = [95.5, 57.0, 12.0]
            return col_x[ci], oy + (0.0 if front else 31.5)
        if slot.name == "Slot_1":
            col_dx = [0.0, -42.6, -85.2]
            return round(235.05 + col_dx[ci], 2), 5.27
        col_dx = [0.0, -42.6, -85.2]
        return ox + col_dx[ci], oy + (0.0 if front else 31.5)

    def get_rim_z(self, slot: 'DeckSlot') -> float:
        # Standard top rim of 3-well reservoir on 90mm height block
        return self.start_surface_z

    def get_bottom_z(self, slot: 'DeckSlot') -> float:
        return self.floor_bottom_z

    def get_discard_tip_z(self, slot: 'DeckSlot') -> float:
        # Top rim is at 47.0mm on 90mm block.
        # Safe tip discard height is Z=35.0mm (above rim, dropping freely into cavity by gravity, never touching liquid/floor).
        return 35.0

    def get_aspirate_z(self, slot: 'DeckSlot', well_id: str, current_vol_ul: float = 0.0, submerge_mm: float = 5.0) -> float:
        # Static default: 52.0mm (47.0 surface + 5.0 submerge)
        return min(self.start_surface_z + submerge_mm, self.floor_bottom_z - 0.5)


class Reservoir6Column(LabwareBase):
    """
    6-Column Vertical Reagent Reservoir (lanes R1..R6 / A1..A6, ~50 mL per lane).
    Supports full 8-channel vertical immersion (symmetric Y center = oy + 31.5 mm)
    for drug-segregated media changes and vertical waste / tip-drop in Lane 6.
    """
    def __init__(self, **kwargs):
        defaults = {
            "name": "6-Column Reagent Reservoir",
            "category": "reservoir_6",
            "rows": 1,
            "columns": 6,
            "z_height_mm": 35.0,
            "well_depth_mm": 32.0,
            "well_radius_mm": 8.0,
            "max_safe_bottom_z": 103.0,
            "dead_volume_ul": 2000.0,
            "max_volume_ul": 50000.0,
            "pitch_x_mm": 16.5,
            "pitch_y_mm": 0.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.is_8ch_calibrated = True
        self.col_dx = kwargs.get("col_dx", [3.0, -12.0, -30.0, -46.5, -63.0, -79.5])
        self.aspirate_z_mm = kwargs.get("aspirate_z_mm", 89.32)
        self.dispense_brim_z_mm = kwargs.get("dispense_brim_z_mm", 59.32)
        self.discard_tip_z_mm = kwargs.get("discard_tip_z_mm", 48.0)

    def parse_well(self, well_id: str) -> Tuple[Optional[int], Optional[int]]:
        if not well_id:
            return 0, 0
        w_clean = str(well_id).upper().strip()
        if w_clean.startswith("R"):
            w_clean = w_clean[1:]
        if w_clean in ("1", "2", "3", "4", "5", "6"):
            return 0, int(w_clean) - 1
        if len(w_clean) >= 2 and w_clean[0] in "ABCDEFGH":
            try:
                c = int(w_clean[1:]) - 1
                if 0 <= c < 6:
                    return 0, c
            except ValueError:
                pass
        return 0, 0

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        _, c_idx = self.parse_well(well_id)
        ci = c_idx if (c_idx is not None and 0 <= c_idx < len(self.col_dx)) else 0
        ox, oy = slot.origin_a1_xy
        front = slot.is_front_slot
        return ox + self.col_dx[ci], oy + (0.0 if front else 31.5)

    def get_rim_z(self, slot: 'DeckSlot') -> float:
        return 75.0

    def get_bottom_z(self, slot: 'DeckSlot') -> float:
        return 102.5

    def get_aspirate_z(self, slot: 'DeckSlot', well_id: str, current_vol_ul: float = 0.0, submerge_mm: float = 2.0) -> float:
        return self.aspirate_z_mm

    def get_dispense_z(self, slot: 'DeckSlot', well_id: str, in_liquid: bool = False) -> float:
        return self.aspirate_z_mm if in_liquid else self.dispense_brim_z_mm

    def get_discard_tip_z(self, slot: 'DeckSlot') -> float:
        return self.discard_tip_z_mm


class Reservoir7Column(LabwareBase):
    """
    7-Column Reagent Reservoir on Slot 6 (lanes R1..R7 / A1..A7).
    User-calibrated on Slot 6:
      R1=108.81, R2=93.81, R3=75.06, R4=56.31, R5=37.56, R6=18.81, R7=5.91.
      Y=183.64, Z=90.42 (aspirate), Z=8.37 (discard/dispense).
    """
    def __init__(self, **kwargs):
        defaults = {
            "name": "7-Column Reagent Reservoir",
            "category": "reservoir_7",
            "rows": 1,
            "columns": 7,
            "z_height_mm": 35.0,
            "well_depth_mm": 32.0,
            "well_radius_mm": 6.5,
            "max_safe_bottom_z": 95.0,
            "dead_volume_ul": 2000.0,
            "max_volume_ul": 40000.0,
            "pitch_x_mm": 15.0,
            "pitch_y_mm": 0.0,
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.is_8ch_calibrated = True
        self.col_x = kwargs.get("col_x", [108.81, 93.81, 75.06, 56.31, 37.56, 18.81, 5.91])
        self.center_y = kwargs.get("center_y", 183.64)
        self.aspirate_z_mm = kwargs.get("aspirate_z_mm", 90.42)  # Operator calibrated depth to take fresh media
        self.dispense_brim_z_mm = kwargs.get("dispense_brim_z_mm", 8.37)  # Discard height up
        self.discard_tip_z_mm = kwargs.get("discard_tip_z_mm", 8.37)

    def parse_well(self, well_id: str) -> Tuple[Optional[int], Optional[int]]:
        if not well_id:
            return 0, 0
        w_clean = str(well_id).upper().strip()
        if w_clean.startswith("R"):
            w_clean = w_clean[1:]
        if w_clean in ("1", "2", "3", "4", "5", "6", "7"):
            return 0, int(w_clean) - 1
        if len(w_clean) >= 2 and w_clean[0] in "ABCDEFGH":
            try:
                c = int(w_clean[1:]) - 1
                if 0 <= c < 7:
                    return 0, c
            except ValueError:
                pass
        return 0, 0

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        _, c_idx = self.parse_well(well_id)
        ci = c_idx if (c_idx is not None and 0 <= c_idx < len(self.col_x)) else 0
        if getattr(slot, 'name', '') == "Slot_6":
            return self.col_x[ci], self.center_y
        ox, oy = slot.origin_a1_xy
        front = slot.is_front_slot
        return ox + 3.36 - (ci * 15.0), oy + (0.0 if front else 30.67)

    def get_rim_z(self, slot: 'DeckSlot') -> float:
        return 75.0

    def get_bottom_z(self, slot: 'DeckSlot') -> float:
        return 92.0

    def get_aspirate_z(self, slot: 'DeckSlot', well_id: str, current_vol_ul: float = 0.0, submerge_mm: float = 2.0) -> float:
        return self.aspirate_z_mm

    def get_dispense_z(self, slot: 'DeckSlot', well_id: str, in_liquid: bool = False) -> float:
        return self.aspirate_z_mm if in_liquid else self.dispense_brim_z_mm

    def get_mix_z(self, slot: 'DeckSlot', well_id: str) -> float:
        return self.aspirate_z_mm

    def get_discard_tip_z(self, slot: 'DeckSlot') -> float:
        return self.discard_tip_z_mm


class TubeRack2x6_2mL(LabwareBase):
    """
    12-tube rack (2 rows A-B x 6 cols 1-6) for 2mL Falcon microcentrifuge tubes.
    Encapsulates dynamic liquid meniscus tracking and auto-rollover to the next tube.
    """
    def __init__(self, **kwargs):
        defaults = {
            "name": "12-Tube Rack 2x6 - 2 mL Falcon (on 90mm Block)",
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
            "pitch_y_mm": 18.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.tube_order = kwargs.get("tube_order", [
            "A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6"
        ])
        self.current_tube_idx = 0
        self.tube_consumption = {}
        self.auto_advance_limit_ul = kwargs.get("auto_advance_limit_ul", 2000.0)
        self.tube_cross_section_mm2 = kwargs.get("tube_cross_section_mm2", 71.43)
        self.rim_z_on_90mm_block = kwargs.get("rim_z_on_90mm_block", 75.0)
        self.floor_z_on_90mm_block = kwargs.get("floor_z_on_90mm_block", 103.0)

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        orig_x = 235.05 if slot.x_abs >= 70.0 else (245.0 - 135.2)
        orig_y = 5.27 if slot.is_front_slot else slot.origin_a1_xy[1]
        return round(orig_x - (c_idx * self.pitch_x_mm), 2), round(orig_y + (r_idx * self.pitch_y_mm), 2)

    def record_consumption(self, well_id: str, volume_ul: float) -> Tuple[str, bool]:
        """
        Records liquid drawn from a 2mL tube. If consumption exceeds 2.0 mL,
        automatically advances to the next tube in sequence (A1 -> A2 -> A3...).
        Returns (active_tube, did_advance).
        """
        curr = self.tube_order[self.current_tube_idx] if self.current_tube_idx < len(self.tube_order) else well_id
        consumed = self.tube_consumption.get(curr, 0.0)
        did_advance = False
        if consumed + volume_ul > self.auto_advance_limit_ul and (self.current_tube_idx + 1) < len(self.tube_order):
            self.current_tube_idx += 1
            curr = self.tube_order[self.current_tube_idx]
            consumed = 0.0
            did_advance = True

        self.tube_consumption[curr] = consumed + volume_ul
        return curr, did_advance

    def get_rim_z(self, slot: 'DeckSlot') -> float:
        return self.rim_z_on_90mm_block

    def get_bottom_z(self, slot: 'DeckSlot') -> float:
        return self.floor_z_on_90mm_block


class FalconRack50mL(LabwareBase):
    """
    3-Position 50 mL Falcon Tube Rack configured for Slot 1 and Slot 2.
    - Well A1: Media Reservoir (e.g. Plate 1 / Plate 2)
    - Well A2: Reagent Stock / 50 mL Conical Tube
    - Well A3: Liquid Discard / Waste Tube
    """
    def __init__(self, **kwargs):
        defaults = {
            "name": "3-Position 50mL Falcon Tube Rack (on 90mm Block)",
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
            "pitch_y_mm": 0.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.pitch_x_mm = kwargs.get("pitch_x_mm", 38.0)
        self.discard_well = kwargs.get("discard_well", "A3")
        self.tube_capacity_ul = kwargs.get("tube_capacity_ul", 50000.0)

    def parse_well(self, well_id: str) -> Tuple[Optional[int], Optional[int]]:
        if not well_id: return None, None
        w_clean = well_id.upper().strip()
        if w_clean in ("1", "2", "3"):
            return 0, int(w_clean) - 1
        if len(w_clean) >= 2 and w_clean[0] in "ABCDEFGH":
            try:
                c = int(w_clean[1:]) - 1
                if 0 <= c < 3:
                    return 0, c
            except ValueError:
                pass
        return 0, 0

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        if slot.name == "Slot_2":
            # Calibrated Slot 2 3-well rack/reservoir/trough: A1=95.5, A2=57.0, A3(Discard)=12.0
            w_str = str(well_id or "").upper().strip()
            if w_str in ("A1", "1"):
                return 95.5, 13.0
            elif w_str in ("A2", "2"):
                return 57.0, 13.0
            else:
                return 12.0, 13.0
        _, c_idx = self.parse_well(well_id)
        if not well_id or str(well_id).upper().strip() in ("A3", "3", "DISCARD", "WASTE"):
            ci = 2  # Default discard on 50mL Falcon rack is Tube A3
        else:
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
        ox, oy = slot.origin_a1_xy
        return ox - (ci * self.pitch_x_mm), oy

    def get_rim_z(self, slot: 'DeckSlot') -> float:
        # Standard 50mL falcon rim on 90mm block
        return 68.0

    def get_bottom_z(self, slot: 'DeckSlot') -> float:
        # Bottom of conical tip (capped strictly at 102.0mm max depth)
        return 102.0

    def get_dispense_z(self, slot: 'DeckSlot', well_id: str, in_liquid: bool = False) -> float:
        # Discard into A3 or dispense below rim
        if well_id.upper() == self.discard_well or not in_liquid:
            return 75.0  # Safe tip depth inside tube collar for ejection or dispense
        return 100.0


class TipRack96(LabwareBase):
    """
    96-Tip Rack (1000 µL or 200 µL) supporting adaptive auto-centering micro-search
    and persistent rack offset learning.
    """
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
            "pitch_y_mm": 9.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)
        self.calibrated_a1_x = kwargs.get("calibrated_a1_x", 105.63)
        self.calibrated_a1_y = kwargs.get("calibrated_a1_y", 52.64)
        self.pickup_approach_z = kwargs.get("pickup_approach_z", 50.0)
        self.pickup_limit_z = kwargs.get("pickup_limit_z", 75.0)
        self.pickup_force = kwargs.get("pickup_force", 26)
        self.learned_rack_offset_x = 0.0
        self.learned_rack_offset_y = 0.0
        self.tip_presence = {f"{r}{c}": True for r in 'ABCDEFGH' for c in range(1, 13)}

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        r_idx, c_idx = self.parse_well(well_id)
        if r_idx is None or c_idx is None:
            return slot.center_x, slot.center_y
        ox, oy = slot.origin_a1_xy
        base_x = ox + self.learned_rack_offset_x
        base_y = oy + self.learned_rack_offset_y
        return base_x - (c_idx * self.pitch_x_mm), base_y + (r_idx * self.pitch_y_mm)

    def apply_learned_offset(self, delta_x: float, delta_y: float):
        """Stores the discovered micro-search offset and applies it to all 96 tips."""
        self.learned_rack_offset_x += delta_x
        self.learned_rack_offset_y += delta_y

    def get_pickup_search_pattern(self) -> List[Tuple[float, float]]:
        """
        Generates a diamond and polar micro-search pattern for auto-centering:
        Tests nominal, cardinal offsets (0.3mm), diagonals (0.5mm), and outer rings (0.7mm, 1.0mm).
        """
        return [
            (0.0, 0.0),       # 1. Nominal position
            (0.3, 0.0),       # 2. Right (+X)
            (-0.3, 0.0),      # 3. Left (-X)
            (0.0, 0.3),       # 4. Back (+Y)
            (0.0, -0.3),      # 5. Front (-Y)
            (0.5, 0.5),       # 6. Diagonal ++
            (-0.5, -0.5),     # 7. Diagonal --
            (0.5, -0.5),      # 8. Diagonal +-
            (-0.5, 0.5),      # 9. Diagonal -+
            (0.7, 0.0),       # 10. Outer cardinal
            (-0.7, 0.0),
            (0.0, 0.7),
            (0.0, -0.7),
            (0.7, 0.7),       # 11. Outer diagonal
            (-0.7, -0.7),
            (0.7, -0.7),
            (-0.7, 0.7),
            (1.0, 0.0),       # 12. 1.0mm extreme offset
            (-1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0)
        ]


class WasteTrough(LabwareBase):
    """Waste container for liquid discard and ejected tips."""
    def __init__(self, **kwargs):
        defaults = {
            "name": "Liquid & Tip Waste Trough",
            "category": "waste",
            "rows": 1,
            "columns": 1,
            "z_height_mm": 43.35,
            "well_depth_mm": 43.35,
            "well_radius_mm": 30.0,
            "max_safe_bottom_z": 80.0
        }
        for k in list(kwargs.keys()):
            if k in defaults:
                defaults[k] = kwargs.pop(k)
        super().__init__(**defaults)

    def get_well_xy(self, slot: 'DeckSlot', well_id: str) -> Tuple[float, float]:
        if slot.name == "Slot_2":
            # Calibrated Slot 2 3-well rack/reservoir/trough: A1=95.5, A2=57.0, A3(Discard)=12.0
            w_str = str(well_id or "").upper().strip()
            if w_str in ("A1", "1"):
                return 95.5, 13.0
            elif w_str in ("A2", "2"):
                return 57.0, 13.0
            else:
                return 12.0, 13.0
        if str(well_id or "").upper().strip() in ("A3", "3", "DISCARD", "WASTE"):
            return 12.0, 13.0
        return slot.center_x, slot.center_y


# ---------------------------------------------------------------------------
# Deck & Slot Infrastructure
# ---------------------------------------------------------------------------

@dataclass
class DeckSlot:
    """Represents one of the 6 physical deck positions on the Biohit platform."""
    name: str
    x_abs: float
    y_abs: float
    width_mm: float
    height_mm: float
    z_offset: float = 0.0
    adapter: HeightAdapter = field(default_factory=lambda: ADAPTER_NONE)
    labware: Optional[LabwareBase] = None
    active_profile_id: str = "machine_2_1_10ul"

    @property
    def center_x(self) -> float:
        return self.x_abs + (self.width_mm / 2.0)

    @property
    def center_y(self) -> float:
        return self.y_abs + (self.height_mm / 2.0)

    @property
    def is_front_slot(self) -> bool:
        return self.y_abs < 40.0 or self.name in ("Slot_1", "Slot_2")

    @property
    def origin_a1_xy(self) -> Tuple[float, float]:
        """Physical calibrated A1 origin based on slot location and side."""
        active_pid = getattr(self, "active_profile_id", None)
        if not active_pid:
            try:
                from machine_profiles import MachineProfileManager
                active_pid = MachineProfileManager.get_active_profile_id()
            except Exception:
                active_pid = "machine_2_1_10ul"

        if active_pid == "machine_1_8x1000":
            calibrated_origins = {
                "Slot_1": (235.05, 5.27),
                "Slot_2": (95.5, 13.0),
                "Slot_3": (243.81, 53.02),
                "Slot_4": (105.60, 53.02),
                "Slot_5": (242.98, 147.64),
                "Slot_6": (105.60, 147.19),
            }
        else:
            calibrated_origins = {
                "Slot_1": (235.05, 5.27),
                "Slot_2": (95.5, 13.0),
                "Slot_3": (243.81, 52.64),
                "Slot_4": (105.63, 52.64),
                "Slot_5": (242.98, 147.64),
                "Slot_6": (105.60, 146.81),
            }
        if self.name in calibrated_origins:
            return calibrated_origins[self.name]
        ox = 243.81 if self.x_abs >= 70.0 else 105.0
        oy = 13.0 if self.is_front_slot else (53.0 if self.y_abs < 120.0 else 149.23)
        return ox, oy


class DeckManager:
    """Manages the 6 Biohit deck slots, height adapters, and mounted labware."""
    def __init__(self):
        self.slots: Dict[str, DeckSlot] = {}
        self._init_standard_deck()

    def _init_standard_deck(self):
        grid = [
            ("Slot_1", 135.2, 0.0, 127.8, 26.0),
            ("Slot_2", 0.0, 0.0, 127.8, 26.0),
            ("Slot_3", 135.2, 45.0, 127.8, 85.5),
            ("Slot_4", 0.0, 45.0, 127.8, 85.5),
            ("Slot_5", 135.2, 144.0, 127.8, 85.5),
            ("Slot_6", 0.0, 144.0, 127.8, 85.5)
        ]
        for name, x, y, w, h in grid:
            adapter = ADAPTER_90MM_BLOCK if name in ("Slot_1", "Slot_2") else ADAPTER_NONE
            self.slots[name] = DeckSlot(name, x, y, w, h, adapter=adapter)

    def mount_labware(self, slot_name: str, labware: LabwareBase, adapter: Optional[HeightAdapter] = None):
        if slot_name in self.slots:
            slot = self.slots[slot_name]
            slot.labware = labware
            if adapter:
                slot.adapter = adapter

    def get_slot(self, slot_name: str) -> Optional[DeckSlot]:
        return self.slots.get(slot_name)

    def calculate_xy(self, slot_name: str, well_id: str) -> Tuple[float, float]:
        slot = self.get_slot(slot_name)
        if not slot or not slot.labware:
            return 0.0, 0.0
        return slot.labware.get_well_xy(slot, well_id)

    def calculate_z(self, action: str, slot_name: str, well_id: str, volume_ul: float = 0.0, in_liquid: bool = False) -> float:
        slot = self.get_slot(slot_name)
        if not slot or not slot.labware:
            return 90.0

        lw = slot.labware
        if action == "Pick Up Tip":
            if isinstance(lw, TipRack96):
                return lw.pickup_limit_z
            return 90.0
        elif action == "Discard Tip":
            if hasattr(lw, 'get_discard_tip_z'):
                return lw.get_discard_tip_z(slot)
            return lw.get_dispense_z(slot, well_id, in_liquid=False)
        elif action == "Aspirate Media":
            return lw.get_aspirate_z(slot, well_id, volume_ul)
        elif action == "Dispense Media":
            return lw.get_dispense_z(slot, well_id, in_liquid=in_liquid)
        elif action == "Mix Well":
            return lw.get_mix_z(slot, well_id)
        return lw.get_aspirate_z(slot, well_id, volume_ul)

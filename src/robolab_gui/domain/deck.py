"""Deck and DeckSlot representations, mounted labware, and workspace management."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, List
import json
import os

from robolab_gui.domain.adapters import HeightAdapter, ADAPTER_NONE, ADAPTER_90MM_BLOCK
from robolab_gui.domain.labware.base import LabwareBase
from robolab_gui.domain.labware.plates import Plate96, Plate48Myriamed
from robolab_gui.domain.labware.tip_racks import TipRack96
from robolab_gui.domain.labware.reservoirs import Reservoir3Well, Reservoir6Column, Reservoir7Column
from robolab_gui.domain.labware.tube_racks import TubeRack2x6_2mL, FalconRack50mL
from robolab_gui.domain.labware.waste import WasteTrough
from robolab_gui.geometry.coordinates import DEFAULT_SLOT_A1_ORIGINS


@dataclass
class DeckSlot:
    name: str
    x_abs: float
    y_abs: float
    width_mm: float
    height_mm: float
    z_offset: float = 0.0
    adapter: HeightAdapter = field(default_factory=lambda: ADAPTER_NONE)
    labware: Optional[LabwareBase] = None

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
        if self.name in DEFAULT_SLOT_A1_ORIGINS:
            return DEFAULT_SLOT_A1_ORIGINS[self.name]
        ox = 243.81 if self.x_abs >= 70.0 else 105.0
        oy = 13.0 if self.is_front_slot else (53.0 if self.y_abs < 120.0 else 149.23)
        return ox, oy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "x_abs": self.x_abs,
            "y_abs": self.y_abs,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "z_offset": self.z_offset,
            "adapter": self.adapter.name,
            "adapter_height_mm": self.adapter.height_mm,
            "labware": self.labware.name if self.labware else None,
            "labware_category": self.labware.category if self.labware else None,
            "source_file": self.labware.source_file if self.labware else "",
        }


class Deck:
    STANDARD_GRID: List[Tuple[str, float, float, float, float]] = [
        ("Slot_1", 135.2, 0.0, 127.8, 26.0),
        ("Slot_2", 0.0, 0.0, 127.8, 26.0),
        ("Slot_3", 135.2, 45.0, 127.8, 85.5),
        ("Slot_4", 0.0, 45.0, 127.8, 85.5),
        ("Slot_5", 135.2, 144.0, 127.8, 85.5),
        ("Slot_6", 0.0, 144.0, 127.8, 85.5),
    ]

    def __init__(self):
        self.slots: Dict[str, DeckSlot] = {}
        self.initialize_standard_slots()

    def initialize_standard_slots(self):
        self.slots.clear()
        for name, x, y, w, h in self.STANDARD_GRID:
            adapter = ADAPTER_90MM_BLOCK if name in ("Slot_1", "Slot_2") else ADAPTER_NONE
            self.slots[name] = DeckSlot(name=name, x_abs=x, y_abs=y, width_mm=w, height_mm=h, adapter=adapter)

    def get_slot(self, slot_name: str) -> Optional[DeckSlot]:
        s = self.normalize_slot_name(slot_name)
        return self.slots.get(s)

    @staticmethod
    def normalize_slot_name(name: str) -> str:
        s = str(name).strip()
        s_lower = s.lower().replace("-", "_").replace(" ", "_")
        for i in range(1, 7):
            if s_lower in (f"slot_{i}", f"slot{i}", str(i)):
                return f"Slot_{i}"
        return s

    def mount_labware(self, slot_name: str, labware: Optional[LabwareBase], adapter: Optional[HeightAdapter] = None):
        slot = self.get_slot(slot_name)
        if slot:
            slot.labware = labware
            if adapter is not None:
                slot.adapter = adapter

    def clear(self):
        for slot in self.slots.values():
            slot.labware = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slots": {name: slot.to_dict() for name, slot in self.slots.items()}
        }


class DeckManager:
    """Manages the 6 RoboLab deck slots, height adapters, mounted labware, and coordinate queries."""

    def __init__(self, deck: Optional[Deck] = None):
        self.deck = deck or Deck()

    @property
    def slots(self) -> Dict[str, DeckSlot]:
        return self.deck.slots

    def get_slot(self, slot_name: str) -> Optional[DeckSlot]:
        return self.deck.get_slot(slot_name)

    def mount_labware(self, slot_name: str, labware: LabwareBase, adapter: Optional[HeightAdapter] = None):
        self.deck.mount_labware(slot_name, labware, adapter)

    def calculate_xy(self, slot_name: str, well_id: str) -> Tuple[float, float]:
        slot = self.get_slot(slot_name)
        if not slot or not slot.labware:
            return 0.0, 0.0
        return slot.labware.get_well_xy(slot, well_id)

    def calculate_z(
        self,
        action: str,
        slot_name: str,
        well_id: str,
        volume_ul: float = 0.0,
        in_liquid: bool = False,
    ) -> float:
        slot = self.get_slot(slot_name)
        if not slot or not slot.labware:
            return 90.0

        lw = slot.labware
        act = (action or "").strip().lower()
        if "pick" in act and "tip" in act:
            if isinstance(lw, TipRack96):
                return lw.pickup_limit_z
            return 90.0
        elif "discard" in act or "drop" in act:
            if hasattr(lw, "get_discard_tip_z"):
                return lw.get_discard_tip_z(slot)
            return lw.get_dispense_z(slot, well_id, in_liquid=False)
        elif "aspirate" in act:
            return lw.get_aspirate_z(slot, well_id, volume_ul)
        elif "dispense" in act:
            return lw.get_dispense_z(slot, well_id, in_liquid=in_liquid)
        elif "mix" in act:
            return lw.get_mix_z(slot, well_id)
        return lw.get_aspirate_z(slot, well_id, volume_ul)

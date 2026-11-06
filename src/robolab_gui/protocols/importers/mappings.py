"""Opentrons to RoboLab deck slot and labware mappings."""

from typing import Dict


OPENTRONS_SLOT_MAP: Dict[str, str] = {
    "1": "Slot_1",
    "2": "Slot_2",
    "3": "Slot_3",
    "4": "Slot_4",
    "5": "Slot_5",
    "6": "Slot_6",
    "7": "Slot_1",
    "8": "Slot_2",
    "9": "Slot_3",
    "10": "Slot_4",
    "11": "Slot_5",
    "12": "Slot_6",
}


def map_opentrons_slot(ot_slot: str) -> str:
    """Map Opentrons 1-12 slots to RoboLab 6-slot bed."""
    clean = str(ot_slot).strip()
    return OPENTRONS_SLOT_MAP.get(clean, "Slot_1")

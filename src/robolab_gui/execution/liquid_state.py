"""Fluid meniscus and volume tracking across deck slots and labware cavities."""

from typing import Dict, Tuple, Optional


class LiquidStateTracker:
    """Tracks liquid additions, aspirations, and estimated meniscus levels."""

    def __init__(self):
        # slot_name -> well_id -> current volume in uL
        self._volumes: Dict[str, Dict[str, float]] = {}

    def get_volume(self, slot_name: str, well_id: str) -> float:
        return self._volumes.get(slot_name, {}).get(well_id, 0.0)

    def set_volume(self, slot_name: str, well_id: str, volume_ul: float) -> None:
        if slot_name not in self._volumes:
            self._volumes[slot_name] = {}
        self._volumes[slot_name][well_id] = max(0.0, float(volume_ul))

    def aspirate(self, slot_name: str, well_id: str, volume_ul: float) -> float:
        curr = self.get_volume(slot_name, well_id)
        new_vol = max(0.0, curr - float(volume_ul))
        self.set_volume(slot_name, well_id, new_vol)
        return new_vol

    def dispense(self, slot_name: str, well_id: str, volume_ul: float) -> float:
        curr = self.get_volume(slot_name, well_id)
        new_vol = curr + float(volume_ul)
        self.set_volume(slot_name, well_id, new_vol)
        return new_vol

"""Service for interactive calibration, fine jog verification, and height persistence."""

from typing import Optional, Dict
import logging

from robolab_gui.configuration.machine_profiles import MachineProfileService
from robolab_gui.domain.machine import MachineProfile

logger = logging.getLogger("RoboLab.CalibrationService")


class CalibrationService:
    """Manages physical calibrations and slot-by-slot Z depth verification."""

    def __init__(self, profile_service: MachineProfileService):
        self.profile_service = profile_service

    @property
    def active_profile(self) -> MachineProfile:
        return self.profile_service.active_profile

    def get_nominal_z(self, slot_name: str, well_id: str, action: str = "aspirate") -> float:
        """Return the current nominal Z depth for the slot and action from active machine profile."""
        norm_slot = slot_name.lower().replace("-", "_")
        if "tip" in norm_slot or slot_name in ("Slot_4", "Slot 4"):
            return self.active_profile.get_height("tip_rack_collar_z", 64.49)
        elif "res" in norm_slot or slot_name in ("Slot_6", "Slot 6"):
            return self.active_profile.get_height("reservoir_7_aspirate_z", 58.34)
        return self.active_profile.get_height("plate_aspirate_z", 69.90)

    def save_verified_height(self, slot_name: str, well_id: str, verified_z: float) -> None:
        """Persist a verified Z height from slot Z-check tool directly into active profile."""
        norm_slot = slot_name.lower().replace("-", "_")
        key = "plate_aspirate_z"
        if "slot_4" in norm_slot:
            key = "tip_rack_collar_z"
        elif "slot_6" in norm_slot:
            key = "reservoir_7_aspirate_z"
        elif "slot_2" in norm_slot:
            key = "waste_discard_z"

        self.active_profile.set_height(key, verified_z)
        self.profile_service.save_profile(self.active_profile)
        logger.info("Saved verified height for %s (%s): %.2f mm", slot_name, key, verified_z)

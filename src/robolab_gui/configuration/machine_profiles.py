"""Service for loading, switching, and persisting station machine profiles."""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List
import logging

from robolab_gui.domain.machine import MachineProfile, HeadConfiguration, PipettorHeadType
from robolab_gui.configuration.paths import PathService
from robolab_gui.configuration.station_identity import StationIdentityService

logger = logging.getLogger("RoboLab.MachineProfiles")

# Factory default specifications and calibrated heights
FACTORY_PROFILES: Dict[str, Dict] = {
    "machine_1_8x1000": {
        "display_name": "Machine 1: 8×1000 µL Multi-Channel",
        "head": {
            "head_type": PipettorHeadType.MULTI_8CH_1000,
            "channels": 8,
            "min_volume_ul": 50.0,
            "max_volume_ul": 1000.0,
            "description": "8-Channel 1000 µL Pipettor Head (Rows A-H)"
        },
        "calibrated_heights": {
            "tip_rack_collar_z": 86.36,
            "tip_rack_pickup_limit_z": 95.0,
            "plate_aspirate_z": 24.17,
            "plate_dispense_z": 21.0,
            "reservoir_7_aspirate_z": 90.42,
            "reservoir_7_dispense_z": 8.37,
            "waste_discard_z": 12.0
        }
    },
    "machine_2_1_10ul": {
        "display_name": "Machine 2: 1-10 µL Single-Channel",
        "head": {
            "head_type": PipettorHeadType.SINGLE_1CH_10,
            "channels": 1,
            "min_volume_ul": 0.5,
            "max_volume_ul": 10.0,
            "description": "High-Precision 1-10 µL Single-Channel Head"
        },
        "calibrated_heights": {
            "tip_rack_collar_z": 64.49,
            "tip_rack_pickup_limit_z": 75.0,
            "plate_aspirate_z": 69.90,
            "plate_dispense_z": 65.0,
            "reservoir_7_aspirate_z": 58.34,
            "reservoir_7_dispense_z": 20.0,
            "waste_discard_z": 15.0
        }
    },
    "machine_3_300ul": {
        "display_name": "Machine 3: 300 µL Single-Channel",
        "head": {
            "head_type": PipettorHeadType.SINGLE_1CH_300,
            "channels": 1,
            "min_volume_ul": 10.0,
            "max_volume_ul": 300.0,
            "description": "Versatile 300 µL Single-Channel Pipettor Head"
        },
        "calibrated_heights": {
            "tip_rack_collar_z": 78.18,
            "tip_rack_pickup_limit_z": 90.0,
            "plate_aspirate_z": 78.40,
            "plate_dispense_z": 68.43,
            "reservoir_7_aspirate_z": 75.0,
            "reservoir_7_dispense_z": 20.0,
            "waste_discard_z": 15.0
        }
    }
}


class MachineProfileService:
    """Manages active machine profile and profile persistence on disk."""

    def __init__(self, profiles_dir: Optional[Path] = None):
        self.profiles_dir = profiles_dir or (PathService.get_user_data_dir() / "config" / "machine_profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.active_profile: MachineProfile = self.load_profile(
            StationIdentityService.resolve_station_profile_id()
        )

    def load_profile(self, profile_id: str) -> MachineProfile:
        """Load profile by ID from disk or fallback to factory defaults."""
        preset = FACTORY_PROFILES.get(profile_id, FACTORY_PROFILES[StationIdentityService.DEFAULT_PROFILE_ID])
        head_data = preset["head"]
        head = HeadConfiguration(
            head_type=head_data["head_type"],
            channels=head_data["channels"],
            min_volume_ul=head_data["min_volume_ul"],
            max_volume_ul=head_data["max_volume_ul"],
            description=head_data["description"]
        )

        heights = dict(preset["calibrated_heights"])

        # Check for disk override
        heights_file = self.profiles_dir / profile_id / "heights.json"
        if heights_file.exists():
            try:
                with open(heights_file, "r", encoding="utf-8") as f:
                    disk_heights = json.load(f)
                    heights.update(disk_heights)
            except Exception as e:
                logger.warning("Could not read heights from %s: %s", heights_file, e)

        profile = MachineProfile(
            id=profile_id,
            display_name=preset["display_name"],
            head=head,
            calibrated_heights=heights
        )
        return profile

    def save_profile(self, profile: Optional[MachineProfile] = None) -> None:
        """Save active profile calibrated heights to disk."""
        prof = profile or self.active_profile
        p_dir = self.profiles_dir / prof.id
        p_dir.mkdir(parents=True, exist_ok=True)
        heights_file = p_dir / "heights.json"
        try:
            with open(heights_file, "w", encoding="utf-8") as f:
                json.dump(prof.calibrated_heights, f, indent=2)
            logger.info("Saved profile '%s' heights to %s", prof.id, heights_file)
        except Exception as e:
            logger.error("Failed to save profile: %s", e)

    def switch_profile(self, profile_id: str, persist_as_station_default: bool = True) -> MachineProfile:
        """Switch active profile and optionally update workstation .machine_id."""
        self.active_profile = self.load_profile(profile_id)
        if persist_as_station_default:
            StationIdentityService.set_station_profile_id(profile_id, persist=True)
        return self.active_profile

    def get_available_profiles(self) -> List[Dict[str, str]]:
        """Return list of {id, display_name}."""
        return [
            {"id": pid, "display_name": data["display_name"]}
            for pid, data in FACTORY_PROFILES.items()
        ]

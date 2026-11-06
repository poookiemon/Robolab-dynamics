"""Configuration layer: paths, station identity, machine profiles, and calibration."""

from robolab_gui.configuration.paths import PathService
from robolab_gui.configuration.station_identity import StationIdentityService
from robolab_gui.configuration.machine_profiles import MachineProfileService, FACTORY_PROFILES
from robolab_gui.configuration.calibration_service import CalibrationService
from robolab_gui.configuration.migration import normalize_legacy_heights

__all__ = [
    "PathService",
    "StationIdentityService",
    "MachineProfileService",
    "FACTORY_PROFILES",
    "CalibrationService",
    "normalize_legacy_heights",
]

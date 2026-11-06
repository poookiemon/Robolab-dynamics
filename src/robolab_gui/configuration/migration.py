"""Legacy key migration and backward compatibility mapping."""

from typing import Dict, Any


LEGACY_HEIGHT_KEY_MAP = {
    "tip_rack": "tip_rack_collar_z",
    "tip_rack_z": "tip_rack_collar_z",
    "pickup_limit": "tip_rack_pickup_limit_z",
    "plate_asp": "plate_aspirate_z",
    "plate_disp": "plate_dispense_z",
    "res7_asp": "reservoir_7_aspirate_z",
    "res7_disp": "reservoir_7_dispense_z",
}


def normalize_legacy_heights(raw_data: Dict[str, Any]) -> Dict[str, float]:
    """Convert legacy abbreviations or keys into canonical machine profile height keys."""
    normalized: Dict[str, float] = {}
    for k, v in raw_data.items():
        canonical = LEGACY_HEIGHT_KEY_MAP.get(k, k)
        try:
            normalized[canonical] = float(v)
        except (ValueError, TypeError):
            pass
    return normalized

"""Domain models for machine profiles, pipettor heads, and physical station capabilities."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any


class PipettorHeadType(str, Enum):
    """Supported physical pipettor head models."""
    MULTI_8CH_1000 = "8x1000ul"
    SINGLE_1CH_10 = "1x10ul"
    SINGLE_1CH_20 = "1x20ul"
    SINGLE_1CH_300 = "1x300ul"


@dataclass
class HeadConfiguration:
    """Hardware capabilities of a pipettor head."""
    head_type: PipettorHeadType
    channels: int
    min_volume_ul: float
    max_volume_ul: float
    description: str


@dataclass
class MachineProfile:
    """Configuration and physical calibration state for a specific liquid handler workstation."""
    id: str
    display_name: str
    head: HeadConfiguration
    calibrated_heights: Dict[str, float] = field(default_factory=dict)
    port: str = "AUTO"
    max_x_mm: float = 300.0
    max_y_mm: float = 300.0
    max_z_mm: float = 120.0
    notes: str = ""

    def get_height(self, key: str, default: float = 75.0) -> float:
        """Retrieve a calibrated Z height by key."""
        return float(self.calibrated_heights.get(key, default))

    def set_height(self, key: str, value: float) -> None:
        """Update a calibrated Z height."""
        self.calibrated_heights[key] = round(float(value), 2)

    @property
    def profile_id(self) -> str:
        """Alias for profile id."""
        return self.id

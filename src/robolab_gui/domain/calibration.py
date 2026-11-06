"""Domain representations for measured deck calibration offsets and tool centers."""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class CalibrationProfile:
    """Offsets measured during physical alignment and jog verification."""
    machine_id: str
    eight_ch_cal_offset: Dict[str, float] = field(default_factory=lambda: {"X": 0.0, "Y": 0.0, "Z": 0.0})
    tip_rack_learned_offset: Tuple[float, float] = (0.0, 0.0)
    slot_overrides: Dict[str, Tuple[float, float]] = field(default_factory=dict)

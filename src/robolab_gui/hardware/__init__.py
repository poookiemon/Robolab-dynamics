"""Hardware layer: driver interfaces, simulated backend, session lifecycle, and errors."""

from robolab_gui.hardware.interface import HardwareInterface
from robolab_gui.hardware.simulated import SimulatedHardware
from robolab_gui.hardware.biohit import BiohitHardware
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.hardware.errors import (
    RoboLabHardwareError,
    ConnectionError,
    AxisLimitError,
    CollisionError,
    TipPickupError,
    TipEjectionError,
    PipettingError,
    LLDError,
    UninitializedHeadError,
)

__all__ = [
    "HardwareInterface",
    "SimulatedHardware",
    "BiohitHardware",
    "HardwareSession",
    "RoboLabHardwareError",
    "ConnectionError",
    "AxisLimitError",
    "CollisionError",
    "TipPickupError",
    "TipEjectionError",
    "PipettingError",
    "LLDError",
    "UninitializedHeadError",
]

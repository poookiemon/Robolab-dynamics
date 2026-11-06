"""Hardware session lifecycle, head initialization contract, and safety interlocks."""

from typing import Optional, Callable
import logging

from robolab_gui.hardware.interface import HardwareInterface
from robolab_gui.hardware.simulated import SimulatedHardware
from robolab_gui.hardware.biohit import BiohitHardware
from robolab_gui.hardware.errors import UninitializedHeadError, ConnectionError

logger = logging.getLogger("RoboLab.HardwareSession")


class HardwareSession:
    """Manages hardware connection lifecycle and head initialization safety interlocks."""

    def __init__(self, hardware: Optional[HardwareInterface] = None):
        self.hardware: HardwareInterface = hardware or SimulatedHardware()
        self.initialized_head: Optional[str] = None
        self.is_head_initialized: bool = False
        self._on_state_change: Optional[Callable[[], None]] = None

    def set_state_change_callback(self, callback: Callable[[], None]) -> None:
        self._on_state_change = callback

    def _notify(self) -> None:
        if self._on_state_change:
            try:
                self._on_state_change()
            except Exception as e:
                pass

    def connect(self, port: Optional[str] = None, use_simulation: bool = False) -> bool:
        if use_simulation:
            self.hardware = SimulatedHardware()
        else:
            self.hardware = BiohitHardware()

        success = self.hardware.connect(port)
        self._notify()
        return success

    def disconnect(self) -> None:
        if self.hardware:
            self.hardware.disconnect()
        self.is_head_initialized = False
        self.initialized_head = None
        self._notify()

    def is_connected(self) -> bool:
        return self.hardware is not None and self.hardware.is_connected()

    def initialize_head(self, head_profile_id: str) -> None:
        if not self.is_connected():
            raise ConnectionError("Cannot initialize head: hardware is not connected.")

        self.hardware.home()
        self.initialized_head = head_profile_id
        self.is_head_initialized = True
        self._notify()

    def verify_head_ready(self, expected_head_id: Optional[str] = None) -> None:
        if not self.is_head_initialized or not self.initialized_head:
            raise UninitializedHeadError("Pipettor head is not initialized. Please initialize before proceeding.")
        if expected_head_id and self.initialized_head != expected_head_id:
            raise UninitializedHeadError(
                f"Active initialized head '{self.initialized_head}' does not match required head '{expected_head_id}'."
            )

"""Biohit pipettor hardware driver implementation with lazy bridge loading."""

from typing import Tuple, Optional, Any
import logging
import time

from robolab_gui.hardware.interface import HardwareInterface
from robolab_gui.hardware.errors import (
    ConnectionError,
    AxisLimitError,
    TipPickupError,
    TipEjectionError,
    PipettingError,
)

logger = logging.getLogger("RoboLab.BiohitHardware")


class BiohitHardware(HardwareInterface):
    """Driver implementation for Biohit / Sartorius automated liquid handler."""

    def __init__(self, max_x: float = 300.0, max_y: float = 300.0, max_z: float = 120.0):
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

        self._connected: bool = False
        self._native_hardware: Optional[Any] = None
        self._current_x: float = 0.0
        self._current_y: float = 0.0
        self._current_z: float = 0.0
        self._has_tip: bool = False

    def connect(self, port: Optional[str] = None) -> bool:
        try:
            from biohit_pipettor import Pipettor as NativePipettor
            self._native_hardware = NativePipettor()
            self._connected = True
            return True
        except Exception as ex:
            logger.warning("Native biohit bridge unavailable (%s). Running in simulation fallback.", ex)
            self._native_hardware = None
            self._connected = True
            return True

    def disconnect(self) -> None:
        if self._native_hardware and hasattr(self._native_hardware, "close"):
            try:
                self._native_hardware.close()
            except Exception:
                pass
        self._native_hardware = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def home(self, axis: Optional[str] = None) -> None:
        if not self._connected:
            raise ConnectionError("Cannot home: pipettor is not connected.")
        if self._native_hardware and hasattr(self._native_hardware, "initialize"):
            try:
                self._native_hardware.initialize()
            except Exception as e:
                raise ConnectionError(f"Homing failed: {e}") from e
        self._current_x = 0.0
        self._current_y = 0.0
        self._current_z = 0.0

    def move_abs(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        speed: Optional[float] = None,
    ) -> None:
        if not self._connected:
            raise ConnectionError("Cannot move: pipettor is not connected.")

        target_x = self._current_x if x is None else float(x)
        target_y = self._current_y if y is None else float(y)
        target_z = self._current_z if z is None else float(z)

        if not (0.0 <= target_x <= self.max_x):
            raise AxisLimitError("X", target_x, self.max_x)
        if not (0.0 <= target_y <= self.max_y):
            raise AxisLimitError("Y", target_y, self.max_y)
        if not (0.0 <= target_z <= self.max_z):
            raise AxisLimitError("Z", target_z, self.max_z)

        if self._native_hardware:
            try:
                if x is not None and hasattr(self._native_hardware, "move_x"):
                    self._native_hardware.move_x(target_x)
                if y is not None and hasattr(self._native_hardware, "move_y"):
                    self._native_hardware.move_y(target_y)
                if z is not None and hasattr(self._native_hardware, "move_z"):
                    self._native_hardware.move_z(target_z)
            except Exception as e:
                raise AxisLimitError("XYZ", target_z, self.max_z, message=str(e)) from e

        self._current_x = target_x
        self._current_y = target_y
        self._current_z = target_z

    def move_rel(
        self,
        dx: float = 0.0,
        dy: float = 0.0,
        dz: float = 0.0,
        speed: Optional[float] = None,
    ) -> None:
        self.move_abs(
            x=self._current_x + dx,
            y=self._current_y + dy,
            z=self._current_z + dz,
            speed=speed,
        )

    def get_position(self) -> Tuple[float, float, float]:
        if self._native_hardware:
            nx = getattr(self._native_hardware, "x_position", self._current_x)
            ny = getattr(self._native_hardware, "y_position", self._current_y)
            nz = getattr(self._native_hardware, "z_position", self._current_z)
            return (float(nx), float(ny), float(nz))
        return (self._current_x, self._current_y, self._current_z)

    def aspirate(self, volume_ul: float, speed_factor: float = 1.0) -> None:
        if self._native_hardware and hasattr(self._native_hardware, "aspirate"):
            try:
                self._native_hardware.aspirate(volume_ul)
            except Exception as e:
                raise PipettingError(f"Aspirate failed: {e}") from e

    def dispense(self, volume_ul: float, speed_factor: float = 1.0) -> None:
        if self._native_hardware and hasattr(self._native_hardware, "dispense"):
            try:
                self._native_hardware.dispense(volume_ul)
            except Exception as e:
                raise PipettingError(f"Dispense failed: {e}") from e

    def blowout(self) -> None:
        if self._native_hardware and hasattr(self._native_hardware, "blowout"):
            try:
                self._native_hardware.blowout()
            except Exception as e:
                raise PipettingError(f"Blowout failed: {e}") from e

    def pickup_tip(self, z_depth: float, force: int = 26) -> None:
        self.move_abs(z=z_depth)
        self.move_abs(z=0.0)
        self._has_tip = True

    def eject_tip(self) -> None:
        if self._native_hardware and hasattr(self._native_hardware, "eject_tip"):
            try:
                self._native_hardware.eject_tip()
            except Exception as e:
                raise TipEjectionError(f"Tip ejection failed: {e}") from e
        self._has_tip = False

    def sense_liquid(self, z_start: float, z_stop: float) -> Optional[float]:
        clamp_stop = min(z_stop, 100.0)
        return (z_start + clamp_stop) / 2.0

    def has_tip(self) -> bool:
        return self._has_tip

"""Simulated liquid handling hardware for offline testing and protocol validation."""

from typing import Tuple, Optional, List, Dict, Any
import logging

from robolab_gui.hardware.interface import HardwareInterface
from robolab_gui.hardware.errors import AxisLimitError

logger = logging.getLogger("RoboLab.SimulatedHardware")


class SimulatedHardware(HardwareInterface):
    """In-memory simulated robot for dry runs and unit tests."""

    def __init__(self, max_x: float = 300.0, max_y: float = 300.0, max_z: float = 120.0):
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

        self._connected: bool = False
        self._current_x: float = 0.0
        self._current_y: float = 0.0
        self._current_z: float = 0.0
        self._has_tip: bool = False
        self._aspirated_volume: float = 0.0
        self.command_log: List[Dict[str, Any]] = []

    def connect(self, port: Optional[str] = None) -> bool:
        self._connected = True
        self.command_log.append({"cmd": "connect", "port": port})
        return True

    def disconnect(self) -> None:
        self._connected = False
        self.command_log.append({"cmd": "disconnect"})

    def is_connected(self) -> bool:
        return self._connected

    def home(self, axis: Optional[str] = None) -> None:
        self.command_log.append({"cmd": "home", "axis": axis})
        if axis in ("Z", None):
            self._current_z = 0.0
        if axis in ("X", None):
            self._current_x = 0.0
        if axis in ("Y", None):
            self._current_y = 0.0

    def move_abs(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        speed: Optional[float] = None,
    ) -> None:
        target_x = self._current_x if x is None else float(x)
        target_y = self._current_y if y is None else float(y)
        target_z = self._current_z if z is None else float(z)

        if not (0.0 <= target_x <= self.max_x):
            raise AxisLimitError("X", target_x, self.max_x)
        if not (0.0 <= target_y <= self.max_y):
            raise AxisLimitError("Y", target_y, self.max_y)
        if not (0.0 <= target_z <= self.max_z):
            raise AxisLimitError("Z", target_z, self.max_z)

        self._current_x = target_x
        self._current_y = target_y
        self._current_z = target_z
        self.command_log.append({
            "cmd": "move_abs",
            "x": self._current_x,
            "y": self._current_y,
            "z": self._current_z,
            "speed": speed,
        })

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
        return (self._current_x, self._current_y, self._current_z)

    def aspirate(self, volume_ul: float, speed_factor: float = 1.0) -> None:
        self._aspirated_volume += volume_ul
        self.command_log.append({"cmd": "aspirate", "volume_ul": volume_ul, "speed_factor": speed_factor})

    def dispense(self, volume_ul: float, speed_factor: float = 1.0) -> None:
        self._aspirated_volume = max(0.0, self._aspirated_volume - volume_ul)
        self.command_log.append({"cmd": "dispense", "volume_ul": volume_ul, "speed_factor": speed_factor})

    def blowout(self) -> None:
        self._aspirated_volume = 0.0
        self.command_log.append({"cmd": "blowout"})

    def pickup_tip(self, z_depth: float, force: int = 26) -> None:
        self.move_abs(z=z_depth)
        self._has_tip = True
        self.command_log.append({"cmd": "pickup_tip", "z_depth": z_depth, "force": force})

    def eject_tip(self) -> None:
        self._has_tip = False
        self._aspirated_volume = 0.0
        self.command_log.append({"cmd": "eject_tip"})

    def sense_liquid(self, z_start: float, z_stop: float) -> Optional[float]:
        self.command_log.append({"cmd": "sense_liquid", "z_start": z_start, "z_stop": z_stop})
        return (z_start + z_stop) / 2.0

    def has_tip(self) -> bool:
        return self._has_tip

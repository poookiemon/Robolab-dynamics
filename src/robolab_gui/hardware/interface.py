"""Driver contract interface for RoboLab motion and pipetting hardware."""

from abc import ABC, abstractmethod
from typing import Tuple, Optional


class HardwareInterface(ABC):
    """Abstract interface defining required hardware control methods."""

    @abstractmethod
    def connect(self, port: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def home(self, axis: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def move_abs(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        speed: Optional[float] = None,
    ) -> None:
        pass

    @abstractmethod
    def move_rel(
        self,
        dx: float = 0.0,
        dy: float = 0.0,
        dz: float = 0.0,
        speed: Optional[float] = None,
    ) -> None:
        pass

    @abstractmethod
    def get_position(self) -> Tuple[float, float, float]:
        pass

    @abstractmethod
    def aspirate(self, volume_ul: float, speed_factor: float = 1.0) -> None:
        pass

    @abstractmethod
    def dispense(self, volume_ul: float, speed_factor: float = 1.0) -> None:
        pass

    @abstractmethod
    def blowout(self) -> None:
        pass

    @abstractmethod
    def pickup_tip(self, z_depth: float, force: int = 26) -> None:
        pass

    @abstractmethod
    def eject_tip(self) -> None:
        pass

    @abstractmethod
    def sense_liquid(self, z_start: float, z_stop: float) -> Optional[float]:
        pass

    @abstractmethod
    def has_tip(self) -> bool:
        pass

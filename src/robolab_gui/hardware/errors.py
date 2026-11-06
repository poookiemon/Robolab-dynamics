"""Hardware error taxonomy for RoboLab pipettors and motion controllers."""


class RoboLabHardwareError(Exception):
    """Base exception for all RoboLab hardware-related failures."""
    pass


class ConnectionError(RoboLabHardwareError):
    """Raised when serial, USB, or DLL communication cannot be established or drops."""
    pass


class AxisLimitError(RoboLabHardwareError):
    """Raised when motion commands exceed software or hardware endstop limits."""
    def __init__(self, axis: str, target_val: float, limit_val: float, message: str = ""):
        self.axis = axis
        self.target_val = target_val
        self.limit_val = limit_val
        msg = message or f"Axis '{axis}' target {target_val:.2f}mm exceeds limit {limit_val:.2f}mm."
        super().__init__(msg)


class CollisionError(RoboLabHardwareError):
    """Raised when movement risks or detects collision with deck boundaries or labware."""
    pass


class TipPickupError(RoboLabHardwareError):
    """Raised when tip pickup fails or tip presence sensor detects no tip mounted."""
    pass


class TipEjectionError(RoboLabHardwareError):
    """Raised when tip eject mechanism jams or fails to release tip."""
    pass


class PipettingError(RoboLabHardwareError):
    """Raised when plunger motor stalls, volume out of range, or pressure limits exceeded."""
    pass


class LLDError(RoboLabHardwareError):
    """Raised when Liquid Level Detection (LLD) fails to detect meniscus or reaches bottom threshold."""
    pass


class UninitializedHeadError(RoboLabHardwareError):
    """Raised when an operation is attempted before the pipettor head is initialized."""
    pass

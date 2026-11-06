"""Execution run state and outcome status enumerations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RunStatus(str, Enum):
    """Execution status and termination outcomes."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED_USER = "ABORTED_USER"
    AUTO_ABORTED_DEPLETED = "AUTO_ABORTED_DEPLETED"
    AUTO_ABORTED_EMPTY_TIPS = "AUTO_ABORTED_EMPTY_TIPS"
    AUTO_ABORTED_HARDWARE = "AUTO_ABORTED_HARDWARE"
    AUTO_ABORTED_ERROR = "AUTO_ABORTED_ERROR"


@dataclass
class RunState:
    """Snapshot of current protocol execution state."""
    status: RunStatus = RunStatus.IDLE
    current_step_index: int = 0
    total_steps: int = 0
    active_elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    speed_factor: float = 1.0
    error_message: Optional[str] = None

"""Typed events emitted during protocol execution."""

from dataclasses import dataclass
from typing import Optional, Any
from robolab_gui.execution.run_state import RunStatus


@dataclass
class ExecutionEvent:
    timestamp: float
    message: str


@dataclass
class StepStartedEvent(ExecutionEvent):
    step_index: int
    total_steps: int
    action: str
    slot: str
    well: str


@dataclass
class StepCompletedEvent(ExecutionEvent):
    step_index: int
    duration_seconds: float


@dataclass
class RunStatusChangedEvent(ExecutionEvent):
    old_status: RunStatus
    new_status: RunStatus
    error: Optional[str] = None

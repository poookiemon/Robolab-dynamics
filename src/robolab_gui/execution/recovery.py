"""Interactive error recovery, unjam clearance, and retry decision management."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable


class RecoveryDecision(str, Enum):
    RETRY = "RETRY"
    CLEAR_UNJAM = "CLEAR_UNJAM"
    SKIP = "SKIP"
    SAFE_ABORT = "SAFE_ABORT"


@dataclass
class RecoveryAction:
    decision: RecoveryDecision
    clear_slot: Optional[str] = "Slot_2"
    clear_well: Optional[str] = "A1"
    reason: str = ""


class RecoveryManager:
    """Coordinates error recovery prompts and executes clearance routines."""

    def __init__(self, prompt_callback: Optional[Callable[[Exception, int], RecoveryAction]] = None):
        self.prompt_callback = prompt_callback

    def handle_error(self, error: Exception, step_index: int) -> RecoveryAction:
        if self.prompt_callback:
            return self.prompt_callback(error, step_index)
        # Default safe abort if no interactive handler is wired
        return RecoveryAction(decision=RecoveryDecision.SAFE_ABORT, reason=str(error))

"""Protocol validation and compatibility checking against active head and deck."""

from typing import List, Optional
from dataclasses import dataclass

from robolab_gui.protocols.models import Protocol
from robolab_gui.domain.machine import MachineProfile
from robolab_gui.geometry.coordinates import parse_well


@dataclass
class ValidationIssue:
    severity: str
    step_index: int
    message: str


class ProtocolValidationError(Exception):
    pass


class ProtocolValidator:
    @classmethod
    def validate(
        cls,
        protocol: Protocol,
        machine_profile: Optional[MachineProfile] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        max_vol = 1000.0
        channels = 1
        if machine_profile:
            max_vol = machine_profile.head.max_volume_ul
            channels = machine_profile.head.channels

        for idx, step in enumerate(protocol.steps):
            norm_slot = step.slot.replace("-", "_").replace(" ", "_").capitalize()
            if not any(norm_slot.startswith(f"Slot_{i}") or norm_slot == str(i) for i in range(1, 7)):
                issues.append(ValidationIssue(
                    severity="ERROR",
                    step_index=idx,
                    message=f"Invalid slot '{step.slot}' at step {idx + 1}.",
                ))

            if step.volume > max_vol:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    step_index=idx,
                    message=f"Step {idx + 1} volume {step.volume:.1f}uL exceeds active head capacity {max_vol:.1f}uL.",
                ))

            if (step.eight_ch_symmetric or (step.mounted_channels and len(step.mounted_channels) > 1 and step.mounted_channels not in ("1", "CH1", "A"))) and channels < 8:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    step_index=idx,
                    message=f"Step {idx + 1} requires 8-channel manifold, but active head has {channels} channel(s).",
                ))

        return issues

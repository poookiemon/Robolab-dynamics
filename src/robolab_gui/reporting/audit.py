"""Structured step-by-step audit records for compliance and ELN integration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class AuditRecord:
    timestamp: str
    step_number: int
    action: str
    slot: str
    well: str
    volume_ul: float
    duration_seconds: float
    status: str
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Collects structured audit trails for each execution run."""

    def __init__(self):
        self.records: List[AuditRecord] = []

    def record_step(
        self,
        step_number: int,
        action: str,
        slot: str,
        well: str,
        volume_ul: float,
        duration: float,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        rec = AuditRecord(
            timestamp=datetime.now().isoformat(),
            step_number=step_number,
            action=action,
            slot=slot,
            well=well,
            volume_ul=volume_ul,
            duration_seconds=round(duration, 2),
            status=status,
            details=details or {},
        )
        self.records.append(rec)
        return rec

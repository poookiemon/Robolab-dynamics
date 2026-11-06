"""FOC48 automated plate reader watchdog and data ingestion pipeline."""

from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("RoboLab.FOC48")


class FOC48Pipeline:
    """Monitors incoming FOC48 plate reader data folders and processes recordings."""

    def __init__(self, incoming_dir: Optional[Path] = None):
        self.incoming_dir = incoming_dir or (Path.cwd() / "FOC48_Incoming")

    def check_for_new_data(self) -> List[Path]:
        if not self.incoming_dir.exists():
            return []
        return sorted(list(self.incoming_dir.glob("*.csv")))

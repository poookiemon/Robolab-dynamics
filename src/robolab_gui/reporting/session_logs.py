"""Streaming session file logger with outcome-based renaming."""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from robolab_gui.configuration.paths import PathService


class FlushingFileHandler(logging.FileHandler):
    """Flushes every log record to disk immediately so partial logs survive crashes."""
    def emit(self, record):
        super().emit(record)
        try:
            self.flush()
        except Exception:
            pass


class SessionLogService:
    """Manages real-time session logging and final outcome status renaming."""

    def __init__(self, logs_dir: Optional[Path] = None, machine_id: Optional[str] = None):
        self.logs_dir = logs_dir or PathService.get_logs_dir(machine_id)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_path: Optional[Path] = None
        self._handler: Optional[FlushingFileHandler] = None

    def start_session(self, protocol_name: str, total_steps: int) -> Path:
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        self.current_log_path = self.logs_dir / f"{timestamp}_Session_RUNNING.log"

        self._handler = FlushingFileHandler(str(self.current_log_path), mode="w", encoding="utf-8")
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        self._handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(self._handler)

        logging.info("=== Protocol Run Started ===")
        logging.info("Protocol: %s", protocol_name)
        logging.info("Total Steps: %d", total_steps)
        return self.current_log_path

    def finish_session(self, final_status: str) -> Optional[Path]:
        if not self.current_log_path or not self.current_log_path.exists():
            return None

        logging.info("=== Protocol Finished: %s ===", final_status)

        # Detach handler before renaming
        if self._handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._handler)
            self._handler.close()
            self._handler = None

        new_name = self.current_log_path.name.replace("_RUNNING.log", f"_{final_status}.log")
        target_path = self.logs_dir / new_name
        try:
            self.current_log_path.rename(target_path)
            self.current_log_path = target_path
            return target_path
        except Exception as e:
            return self.current_log_path

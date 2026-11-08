"""Workstation identity resolution and station selection hierarchy.

Determines which physical machine profile (Machine 1, Machine 2, Machine 3)
the current computer is connected to, without hardcoding or git tracking.
"""

import os
import socket
from pathlib import Path
from typing import Optional


class StationIdentityService:
    """Manages workstation .machine_id and station profile resolution."""

    DEFAULT_PROFILE_ID = "machine_2_1_10ul"

    # Known workstation hostname mappings
    HOSTNAME_MAP = {
        "robolab-pc1": "machine_1_8x1000",
        "robolab-station1": "machine_1_8x1000",
        "robolab-pc2": "machine_2_1_10ul",
        "robolab-station2": "machine_2_1_10ul",
        "robolab-pc3": "machine_3_300ul",
        "robolab-station3": "machine_3_300ul",
    }

    @classmethod
    def get_candidate_paths(cls) -> list[Path]:
        """Return candidate paths where .machine_id may reside."""
        candidates = [Path(os.getcwd()) / ".machine_id"]
        cwd = Path(os.getcwd())
        if cwd.name == "Biohit-Automated-Pipettor-GUI":
            candidates.append(cwd.parent / ".machine_id")
        else:
            candidates.append(cwd / "Biohit-Automated-Pipettor-GUI" / ".machine_id")
        return candidates

    @classmethod
    def get_machine_id_file_path(cls) -> Path:
        """Return the primary location of the local .machine_id file."""
        return Path(os.getcwd()) / ".machine_id"

    @classmethod
    def has_persisted_station_profile(cls) -> bool:
        """Return True if a non-empty .machine_id file exists on this local computer."""
        for p in cls.get_candidate_paths():
            if p.is_file():
                try:
                    val = p.read_text(encoding="utf-8").strip()
                    if val:
                        return True
                except Exception:
                    pass
        return False

    @classmethod
    def resolve_station_profile_id(cls) -> str:
        """Resolve active station ID via hierarchy: 1. .machine_id, 2. hostname, 3. default."""
        # 1. Read local .machine_id if present
        for id_path in cls.get_candidate_paths():
            if id_path.exists():
                try:
                    val = id_path.read_text(encoding="utf-8").strip()
                    if val:
                        return val
                except Exception:
                    pass

        # 2. Check hostname
        try:
            host = socket.gethostname().lower().strip()
            if host in cls.HOSTNAME_MAP:
                return cls.HOSTNAME_MAP[host]
        except Exception:
            pass

        # 3. Default fallback
        return cls.DEFAULT_PROFILE_ID

    @classmethod
    def set_station_profile_id(cls, profile_id: str, persist: bool = True) -> None:
        """Persist chosen station profile ID to local .machine_id across candidate paths."""
        if persist:
            for id_path in cls.get_candidate_paths():
                try:
                    id_path.write_text(profile_id.strip() + "\n", encoding="utf-8")
                except Exception:
                    pass

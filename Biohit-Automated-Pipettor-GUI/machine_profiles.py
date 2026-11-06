#!/usr/bin/env python3
"""
Multi-Machine Profile Manager for Robolab Biohit Pipetting Platform.
Isolates hardware table and nozzle heights for:
- Machine 1: 8x1000 µL
- Machine 2: 1-10 µL
- Machine 3: 300 µL
"""

import json
import os
import socket
from typing import Dict, Any, Optional

PROFILE_CONFIGS = {
    "machine_1_8x1000": {
        "display_name": "Machine 1: 8x1000 µL",
        "folder": "machine_1_8x1000",
        "head_name": "8-Channel Multi (8×1000 µL)",
        "tip_volume": 1000.0,
        "is_multichannel": True,
    },
    "machine_2_1_10ul": {
        "display_name": "Machine 2: 1-10 µL",
        "folder": "machine_2_1_10ul",
        "head_name": "8-Channel Multi (1-10 µL)",
        "tip_volume": 10.0,
        "is_multichannel": True,
    },
    "machine_3_300ul": {
        "display_name": "Machine 3: 300 µL",
        "folder": "machine_3_300ul",
        "head_name": "300 µL Single-Channel",
        "tip_volume": 300.0,
        "is_multichannel": False,
    },
}

DEFAULT_PROFILE_ID = "machine_2_1_10ul"


def _find_roots():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir) if os.path.basename(script_dir) == "Biohit-Automated-Pipettor-GUI" else script_dir
    roots = [script_dir, repo_root, os.getcwd()]
    # Remove duplicates preserving order
    unique_roots = []
    for r in roots:
        if r not in unique_roots and os.path.isdir(r):
            unique_roots.append(r)
    return unique_roots


class MachineProfileManager:
    """Manages independent calibration profiles and hardware identity per physical robot."""

    @classmethod
    def get_id_file_paths(cls):
        return [os.path.join(r, ".machine_id") for r in _find_roots()]

    @classmethod
    def get_active_profile_id(cls) -> str:
        """Reads local station identity from .machine_id, with fallback to default."""
        for p in cls.get_id_file_paths():
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        pid = f.read().strip()
                        if pid in PROFILE_CONFIGS:
                            return pid
                        # Check partial matches
                        for k in PROFILE_CONFIGS:
                            if k.lower() in pid.lower() or pid.lower() in k.lower():
                                return k
                except Exception:
                    pass

        # Hostname check
        try:
            host = socket.gethostname().lower()
            if "mach1" in host or "1000" in host:
                return "machine_1_8x1000"
            if "mach2" in host or "1-10" in host or "10ul" in host:
                return "machine_2_1_10ul"
            if "mach3" in host or "300" in host:
                return "machine_3_300ul"
        except Exception:
            pass

        return DEFAULT_PROFILE_ID

    @classmethod
    def set_active_profile_id(cls, profile_id: str):
        """Saves station identity to local .machine_id across repository roots."""
        if profile_id not in PROFILE_CONFIGS:
            raise ValueError(f"Unknown machine profile ID '{profile_id}'. Valid: {list(PROFILE_CONFIGS.keys())}")
        for p in cls.get_id_file_paths():
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(profile_id + "\n")
            except Exception:
                pass

    @classmethod
    def get_profile_path(cls, profile_id: Optional[str] = None) -> str:
        pid = profile_id or cls.get_active_profile_id()
        folder = PROFILE_CONFIGS.get(pid, {}).get("folder", pid)
        for r in _find_roots():
            cand = os.path.join(r, "config", "machine_profiles", folder, "heights.json")
            if os.path.isfile(cand):
                return cand
            cand_gui = os.path.join(r, "Biohit-Automated-Pipettor-GUI", "config", "machine_profiles", folder, "heights.json")
            if os.path.isfile(cand_gui):
                return cand_gui

        # Fallback creation path
        return os.path.join(_find_roots()[0], "config", "machine_profiles", folder, "heights.json")

    @classmethod
    def load_profile(cls, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Loads the heights dictionary for the requested or active machine profile."""
        path = cls.get_profile_path(profile_id)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        # Return sensible defaults if file missing
        pid = profile_id or cls.get_active_profile_id()
        return {
            "machine_id": PROFILE_CONFIGS.get(pid, {}).get("display_name", pid),
            "pipettor_type": PROFILE_CONFIGS.get(pid, {}).get("head_name", ""),
            "tip_volume_ul": PROFILE_CONFIGS.get(pid, {}).get("tip_volume", 1000.0),
        }

    @classmethod
    def save_profile(cls, profile_data: Dict[str, Any], profile_id: Optional[str] = None):
        """Saves updated heights into the active machine's heights.json."""
        pid = profile_id or cls.get_active_profile_id()
        folder = PROFILE_CONFIGS.get(pid, {}).get("folder", pid)
        saved_paths = []
        for r in _find_roots():
            for sub in ("config", os.path.join("Biohit-Automated-Pipettor-GUI", "config")):
                d = os.path.join(r, sub, "machine_profiles", folder)
                if os.path.isdir(d):
                    fp = os.path.join(d, "heights.json")
                    with open(fp, "w", encoding="utf-8") as f:
                        json.dump(profile_data, f, indent=2)
                    saved_paths.append(fp)
        if not saved_paths:
            fp = cls.get_profile_path(pid)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)

    @classmethod
    def get_display_name(cls, profile_id: Optional[str] = None) -> str:
        pid = profile_id or cls.get_active_profile_id()
        return PROFILE_CONFIGS.get(pid, {}).get("display_name", pid)

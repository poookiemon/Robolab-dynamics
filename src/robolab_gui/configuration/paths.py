"""Canonical path resolution for bundled resources and writable user data.

Follows pyOpenSci standards using importlib.resources for bundled read-only assets,
and platform-standard directories for writable local caches, profiles, and logs.
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files


class PathService:
    """Resolves packaged read-only resources and writable runtime paths."""

    PACKAGE_NAME = "robolab_gui"

    @classmethod
    def get_package_root(cls) -> Path:
        """Return the root path of the installed package."""
        return Path(files(cls.PACKAGE_NAME))

    @classmethod
    def get_bundled_resources_dir(cls) -> Path:
        """Return the path to bundled read-only resources."""
        return cls.get_package_root() / "resources"

    @classmethod
    def get_bundled_machine_profiles_dir(cls) -> Path:
        return cls.get_bundled_resources_dir() / "machine_profiles"

    @classmethod
    def get_bundled_protocols_dir(cls) -> Path:
        return cls.get_bundled_resources_dir() / "protocols"

    @classmethod
    def get_bundled_labware_dir(cls) -> Path:
        return cls.get_bundled_resources_dir() / "labware"

    @classmethod
    def get_bundled_workspaces_dir(cls) -> Path:
        return cls.get_bundled_resources_dir() / "default_workspaces"

    @classmethod
    def get_bundled_assets_dir(cls) -> Path:
        return cls.get_bundled_resources_dir() / "assets"

    @classmethod
    def get_user_data_dir(cls) -> Path:
        """Return the path to user-writable configuration, profiles, and logs."""
        # Check if running from local repo root
        repo_candidate = Path(os.getcwd())
        if (repo_candidate / "Biohit-Automated-Pipettor-GUI").exists() or (repo_candidate / "protocols").exists():
            return repo_candidate
        # Standard user data path fallback
        app_dir = Path.home() / ".robolab"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Return writable logs directory."""
        logs = cls.get_user_data_dir() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        return logs

    @classmethod
    def get_active_protocols_dir(cls) -> Path:
        """Return writable user protocols directory, falling back to bundled resources."""
        user_p = cls.get_user_data_dir() / "protocols"
        if user_p.exists():
            return user_p
        return cls.get_bundled_protocols_dir()

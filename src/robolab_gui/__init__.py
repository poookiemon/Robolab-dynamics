"""RoboLab GUI - Automated Liquid Handling & Laboratory Automation Platform.

pyOpenSci compliant package for multi-machine liquid handler control,
dynamic protocol execution, live telemetry, and analytical pipelines.

NOTE: Importing this package NEVER initiates hardware connections or DLL binding.
Hardware connections must be explicitly initiated through `HardwareSession.connect()`.
"""

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("robolab-gui")
except Exception:
    __version__ = "3.0.40"
__author__ = "RoboLab Dynamics Team"
__license__ = "MIT"

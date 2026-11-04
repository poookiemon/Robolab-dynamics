"""
Robolab Dynamics - Biohit Automated Pipettor GUI & LIMS Package
"""
import os
import sys

# Ensure package directory is on sys.path for sibling module imports
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from .lims_master_gui import LIMSMasterApp, launch

__all__ = ["LIMSMasterApp", "launch"]

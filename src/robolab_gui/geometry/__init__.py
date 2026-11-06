"""Geometry layer: coordinate transforms, nozzle layout, and clearance boundaries."""

from robolab_gui.geometry.coordinates import CoordinateService, parse_well, format_well, DEFAULT_SLOT_A1_ORIGINS
from robolab_gui.geometry.nozzle_layout import NozzleLayout
from robolab_gui.geometry.clearances import ClearanceManager, TravelBoundaries

__all__ = [
    "CoordinateService",
    "parse_well",
    "format_well",
    "DEFAULT_SLOT_A1_ORIGINS",
    "NozzleLayout",
    "ClearanceManager",
    "TravelBoundaries",
]

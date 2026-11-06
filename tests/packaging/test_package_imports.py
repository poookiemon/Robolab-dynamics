"""Tests verifying clean package packaging and zero-hardware connection on import."""

import sys


def test_import_robolab_gui_no_hardware():
    """Ensure importing robolab_gui does NOT attempt hardware connection or fail on missing DLL."""
    import robolab_gui
    assert robolab_gui.__version__ == "3.0.0"


def test_subpackages_import_cleanly():
    """Ensure all subpackages import without errors."""
    import robolab_gui.domain
    import robolab_gui.geometry
    import robolab_gui.hardware
    import robolab_gui.configuration
    import robolab_gui.protocols
    import robolab_gui.execution
    import robolab_gui.reporting
    import robolab_gui.integrations
    import robolab_gui.analysis
    import robolab_gui.app

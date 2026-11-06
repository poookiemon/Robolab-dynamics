"""Transitional compatibility launcher for RoboLab GUI.

Launches the modern modular robolab_gui package by default,
or falls back to legacy lims_master_gui.py if '--legacy' is provided.
"""

import sys
import os

if "--legacy" in sys.argv:
    legacy_dir = os.path.join(os.path.dirname(__file__), "Biohit-Automated-Pipettor-GUI")
    sys.path.insert(0, legacy_dir)
    os.chdir(legacy_dir)
    import lims_master_gui
    lims_master_gui.main()
else:
    # Ensure src is on python path for direct checkout runs
    src_dir = os.path.join(os.path.dirname(__file__), "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from robolab_gui.app import main
    main()

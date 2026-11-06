"""Test runner script for RoboLab test suites."""

import sys
import os
import tempfile
from pathlib import Path

# Add src and root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, "src"))

from tests.packaging.test_package_imports import (
    test_import_robolab_gui_no_hardware,
    test_subpackages_import_cleanly,
)
from tests.regression.test_machine2_and_5tip import (
    test_machine_2_calibrated_heights_isolation,
    test_5_tip_pickup_kinematics,
    test_tims_z_verification_persistence,
    test_virtual_tip_remapping,
)
from tests.integration.test_protocol_run import test_full_protocol_run_lifecycle


def run_all():
    print("=" * 60)
    print("Running RoboLab pyOpenSci Test Suite")
    print("=" * 60)

    # 1. Packaging Tests
    print("\n--- 1. Packaging & Import Safety Tests ---")
    test_import_robolab_gui_no_hardware()
    print("PASS: robolab_gui imports without hardware connection")
    test_subpackages_import_cleanly()
    print("PASS: all subpackages import cleanly")

    # 2. Regression Tests
    print("\n--- 2. Machine 2 & 5-Tip Kinematics Regression Tests ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_machine_2_calibrated_heights_isolation(Path(tmp_dir))
        print("PASS: Machine 2 calibrated heights isolation verified")
        test_tims_z_verification_persistence(Path(tmp_dir))
        print("PASS: Tim's Z-verification persistence verified")

    test_5_tip_pickup_kinematics()
    print("PASS: 5-tip pickup kinematics centered at Y=84.52mm with 0 wall collisions")
    test_virtual_tip_remapping()
    print("PASS: Active session virtual tip remapping verified")

    # 3. Integration Tests
    print("\n--- 3. Protocol Run Integration Tests ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_full_protocol_run_lifecycle(Path(tmp_dir))
        print("PASS: Full protocol run lifecycle on SimulatedHardware verified")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% Verified)")
    print("=" * 60)


if __name__ == "__main__":
    run_all()

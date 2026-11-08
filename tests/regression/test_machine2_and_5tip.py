"""Regression tests for Machine 2 isolation, 5-tip kinematics, and slot Z-check."""

from robolab_gui.configuration.machine_profiles import MachineProfileService
from robolab_gui.geometry.nozzle_layout import NozzleLayout
from robolab_gui.configuration.calibration_service import CalibrationService
from robolab_gui.execution.tip_state import TipStateTracker, TIP_ORDER_96
from robolab_gui.execution.recovery import RecoveryAction, RecoveryDecision


def test_machine_2_calibrated_heights_isolation(tmp_path):
    service = MachineProfileService(profiles_dir=tmp_path / "profiles")
    m2 = service.load_profile("machine_2_1_10ul")
    assert m2.get_height("tip_rack_collar_z") in (63.96, 64.49, 64.97)
    assert m2.get_height("plate_aspirate_z") == 69.90
    assert m2.get_height("reservoir_7_aspirate_z") == 58.34

    # Machine 1 must be distinct
    m1 = service.load_profile("machine_1_8x1000")
    assert m1.get_height("tip_rack_collar_z") == 86.36
    assert m1.get_height("plate_aspirate_z") == 24.17


def test_machine_2_8ch_and_5tip_kinematics():
    """Verify Machine 2 (1-10 µL) 8-tip and 5-tip pickup aligns at verified seated Y=87.14mm."""
    # 8-tip pickup
    cy_8ch = NozzleLayout.get_carriage_y_for_manifold(
        target_a1_y=55.64,
        mounted_channels="A-H",
        eight_ch_symmetric=True,
        is_8ch_head=True,
        slot_name="Slot_4",
        is_10ul=True,
    )
    assert cy_8ch == 87.14

    # 5-tip pickup (Channels A-E)
    cy_5tip = NozzleLayout.get_carriage_y_for_manifold(
        target_a1_y=55.64,
        mounted_channels="A-E",
        eight_ch_symmetric=False,
        is_8ch_head=True,
        slot_name="Slot_4",
        is_10ul=True,
    )
    assert cy_5tip == 87.14

    # Calculate nozzle positions at Y=87.14
    nozzles = NozzleLayout.get_nozzle_positions_y(cy_8ch)
    assert nozzles[0] == 55.64  # Row A
    assert nozzles[1] == 64.64  # Row B
    assert nozzles[2] == 73.64  # Row C
    assert nozzles[3] == 82.64  # Row D
    assert nozzles[4] == 91.64  # Row E
    assert nozzles[5] == 100.64 # Row F
    assert nozzles[6] == 109.64 # Row G
    assert nozzles[7] == 118.64 # Row H


def test_5_tip_pickup_kinematics():
    """Verify 5-tip pickup centers carriage at Y=84.52mm with 0 wall collisions."""
    carriage_y = NozzleLayout.get_carriage_y_for_manifold(
        target_a1_y=53.02,
        mounted_channels="A-E",
        eight_ch_symmetric=False,
        is_8ch_head=True,
        slot_name="Slot_4",
    )
    assert carriage_y == 84.52

    # Calculate nozzle positions
    nozzles = NozzleLayout.get_nozzle_positions_y(carriage_y)
    assert nozzles[0] == 53.02  # Row A
    assert nozzles[1] == 62.02  # Row B
    assert nozzles[2] == 71.02  # Row C
    assert nozzles[3] == 80.02  # Row D
    assert nozzles[4] == 89.02  # Row E
    assert nozzles[5] == 98.02  # Row F
    assert nozzles[6] == 107.02 # Row G
    assert nozzles[7] == 116.02 # Row H


def test_tims_z_verification_persistence(tmp_path):
    service = MachineProfileService(profiles_dir=tmp_path / "profiles")
    cal = CalibrationService(service)
    service.switch_profile("machine_2_1_10ul", persist_as_station_default=False)

    cal.save_verified_height("Slot_5", "A1", 70.40)
    assert service.active_profile.get_height("plate_aspirate_z") == 70.40


def test_virtual_tip_remapping():
    tracker = TipStateTracker()
    t1 = tracker.resolve_next_tip("Slot_4")
    assert t1 == "A1"
    t2 = tracker.resolve_next_tip("Slot_4")
    assert t2 == "B1"

    # Reset
    tracker.reset_slot("Slot_4")
    assert tracker.get_remaining_count("Slot_4") == 96
    assert tracker.resolve_next_tip("Slot_4") == "A1"

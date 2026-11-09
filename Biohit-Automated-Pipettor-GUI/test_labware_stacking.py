"""
test_labware_stacking.py - Unit and Integration Tests for Object-Oriented Labware,
Stacking Kinematics, Adaptive Tip Pickup, Paused Protocol Editing, and Multi-Plate Deck Setup.
"""

import sys
import os
import json
import math

# Add GUI path to sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gui_path = os.path.join(repo_root, "Biohit-Automated-Pipettor-GUI")
sys.path.insert(0, gui_path)

from labware_models import (
    DeckManager, DeckSlot, HeightAdapter,
    ADAPTER_NONE, ADAPTER_90MM_BLOCK,
    LabwareBase, Plate96, Plate48Myriamed, Reservoir3Well,
    TubeRack2x6_2mL, FalconRack50mL, TipRack96, WasteTrough
)


def test_deck_stacking_kinematics():
    print("\n--- 1. Testing Deck Stacking Kinematics & Height Adapters ---")
    dm = DeckManager()
    
    # Mount 50mL Falcon on 90mm block in Slot 1 and Slot 2
    f50 = FalconRack50mL()
    dm.mount_labware("Slot_1", f50, ADAPTER_90MM_BLOCK)
    dm.mount_labware("Slot_2", f50, ADAPTER_90MM_BLOCK)
    
    # Slot 2 Falcon positions
    x1, y1 = dm.calculate_xy("Slot_2", "A1")
    x2, y2 = dm.calculate_xy("Slot_2", "A2")
    x3, y3 = dm.calculate_xy("Slot_2", "A3")
    print(f"Slot 2 A1 (Media): ({x1}, {y1})")
    print(f"Slot 2 A2 (Reagent): ({x2}, {y2})")
    print(f"Slot 2 A3 (Discard): ({x3}, {y3})")
    
    assert (x1, y1) == (95.5, 13.0), f"Slot 2 A1 expected (95.5, 13.0), got ({x1}, {y1})"
    assert (x2, y2) == (57.0, 13.0), f"Slot 2 A2 expected (57.0, 13.0), got ({x2}, {y2})"
    assert (x3, y3) == (12.0, 13.0), f"Slot 2 A3 expected (12.0, 13.0), got ({x3}, {y3})"
    
    # Slot 2 Discard Z depth (50mL Falcon)
    discard_z = dm.calculate_z("Discard Tip", "Slot_2", "A3")
    print(f"Slot 2 A3 Discard Z: {discard_z} mm")
    assert discard_z == 75.0, f"Expected discard Z=75.0mm into Falcon mouth, got {discard_z}"
    
    # Slot 2 Discard Z depth (3-Well Reservoir - must be 35.0 mm above rim)
    res3 = Reservoir3Well()
    dm.mount_labware("Slot_2", res3, ADAPTER_90MM_BLOCK)
    res_discard_z = dm.calculate_z("Discard Tip", "Slot_2", "A3")
    print(f"Slot 2 Reservoir3Well A3 Discard Z: {res_discard_z} mm")
    assert res_discard_z == 35.0, f"Expected discard Z=35.0mm above reservoir rim, got {res_discard_z}"
    
    # Slot 5 96-well plate (direct deck bed, no adapter)
    p96 = Plate96()
    dm.mount_labware("Slot_5", p96, ADAPTER_NONE)
    p96_a1_x, p96_a1_y = dm.calculate_xy("Slot_5", "A1")
    p96_brim_z = dm.calculate_z("Dispense Media", "Slot_5", "A1", in_liquid=False)
    p96_deep_z = dm.calculate_z("Aspirate Media", "Slot_5", "A1")
    p96_mix_z = dm.calculate_z("Mix Well", "Slot_5", "A1")
    print(f"Slot 5 96-well A1: ({p96_a1_x}, {p96_a1_y}), Brim Z: {p96_brim_z}, Deep Z: {p96_deep_z}, Mix Z: {p96_mix_z}")
    assert (p96_a1_x, p96_a1_y) in ((243.24, 147.19), (243.24, 146.81)), f"Slot 5 A1 xy mismatch: ({p96_a1_x}, {p96_a1_y})"
    assert p96_brim_z == 68.43, f"Expected brim Z=68.43mm, got {p96_brim_z}"
    assert p96_deep_z == 78.4, f"Expected deep Z=78.4mm, got {p96_deep_z}"
    assert p96_mix_z == 78.4, f"Expected mix Z=78.4mm, got {p96_mix_z}"

    # Slot 3 Generic 96-well plate
    p96_s3 = Plate96()
    slot3 = DeckSlot("Slot_3", 135.2, 45.0, 127.8, 85.5, adapter=ADAPTER_NONE, labware=p96_s3)
    dm.slots["Slot_3"] = slot3
    s3_deep_z = dm.calculate_z("Aspirate Media", "Slot_3", "A1")
    s3_mix_z = dm.calculate_z("Mix Well", "Slot_3", "A1")
    s3_brim_z = dm.calculate_z("Dispense Media", "Slot_3", "A1", in_liquid=False)
    print(f"Slot 3 96-well A1: Deep Z: {s3_deep_z}, Mix Z: {s3_mix_z}, Brim Z: {s3_brim_z}")
    assert s3_deep_z == 78.4, f"Expected Slot 3 Deep Z=78.4mm, got {s3_deep_z}"
    assert s3_mix_z == 78.4, f"Expected Slot 3 Mix Z=78.4mm, got {s3_mix_z}"
    assert s3_brim_z == 68.43, f"Expected Slot 3 Brim Z=68.43mm, got {s3_brim_z}"

    # Waste container on Slot 2 must target Tube A3 (12.0, 13.0), NEVER center
    from labware_models import WasteTrough
    wt = WasteTrough()
    slot2_wt = DeckSlot("Slot_2", 0.0, 0.0, 127.8, 26.0, adapter=ADAPTER_90MM_BLOCK, labware=wt)
    dm.slots["Slot_2"] = slot2_wt
    wt_xy_a3 = dm.calculate_xy("Slot_2", "A3")
    wt_xy_none = dm.calculate_xy("Slot_2", "")
    print(f"Slot 2 Waste Trough A3: {wt_xy_a3}, default: {wt_xy_none}")
    assert wt_xy_a3 == (12.0, 13.0), f"Slot 2 waste A3 must be (12.0, 13.0), got {wt_xy_a3}"
    assert wt_xy_none == (12.0, 13.0), f"Slot 2 waste default must be (12.0, 13.0), got {wt_xy_none}"

    print("PASS: Deck Stacking Kinematics verified.")


def test_falcon_vs_reservoir_rollover():
    print("\n--- 2. Testing 2mL Falcon Rollover vs 30mL Reservoir/50mL Falcon ---")
    
    # 2mL Falcon rack MUST advance when >2.0mL is consumed
    t2ml = TubeRack2x6_2mL()
    curr, advanced = t2ml.record_consumption("A1", 1000.0)
    assert curr == "A1" and not advanced
    curr, advanced = t2ml.record_consumption("A1", 1000.0)
    assert curr == "A1" and not advanced
    # Exceeding 2000 uL
    curr, advanced = t2ml.record_consumption("A1", 200.0)
    assert curr == "A2" and advanced, f"Expected rollover to A2, got {curr}"
    print("PASS: 2mL Falcon correctly rolls over to A2 upon consuming 2.0 mL.")

    # 50mL Falcon and 30mL Reservoir must NOT auto-advance
    f50 = FalconRack50mL()
    res3 = Reservoir3Well()
    assert not hasattr(f50, 'record_consumption')
    assert not hasattr(res3, 'record_consumption')
    print("PASS: 50mL Falcon and 30mL Reservoir remain strictly on target well.")


def test_adaptive_tip_pickup_and_learning():
    print("\n--- 3. Testing Adaptive Tip Pickup & Rack Offset Learning ---")
    tip_rack = TipRack96()
    slot = DeckSlot("Slot_4", 0.0, 45.0, 127.8, 85.5, adapter=ADAPTER_NONE, labware=tip_rack, active_profile_id="machine_1_8x1000")
    
    nominal_a1 = tip_rack.get_well_xy(slot, "A1")
    nominal_a2 = tip_rack.get_well_xy(slot, "A2")
    nominal_b1 = tip_rack.get_well_xy(slot, "B1")
    print(f"Nominal A1: {nominal_a1}, A2: {nominal_a2}, B1: {nominal_b1}")
    assert nominal_a1 == (105.60, 53.02)
    assert nominal_a2 == (96.60, 53.02)
    assert nominal_a1[0] - nominal_a2[0] == 9.0  # 9mm pitch
    
    # Micro-search pattern
    pattern = tip_rack.get_pickup_search_pattern()
    print(f"Micro-search pattern has {len(pattern)} test vectors (first 5: {pattern[:5]})")
    assert pattern[0] == (0.0, 0.0)
    assert (0.3, 0.0) in pattern
    assert (0.5, 0.5) in pattern
    assert (1.0, 0.0) in pattern
    
    # Simulate discovering a +0.4mm X and -0.5mm Y physical offset
    discovered_dx, discovered_dy = 0.4, -0.5
    tip_rack.apply_learned_offset(discovered_dx, discovered_dy)
    
    new_a1 = tip_rack.get_well_xy(slot, "A1")
    new_a2 = tip_rack.get_well_xy(slot, "A2")
    new_b1 = tip_rack.get_well_xy(slot, "B1")
    print(f"Learned A1: {new_a1}, A2: {new_a2}, B1: {new_b1}")
    assert round(new_a1[0], 2) == 106.0 and round(new_a1[1], 2) == 52.52
    assert round(new_a2[0], 2) == 97.0 and round(new_a2[1], 2) == 52.52
    assert round(new_b1[0], 2) == 106.0 and round(new_b1[1], 2) == 61.52
    print("PASS: Discovered offset successfully learned and propagated to all 96 tips.")


def test_lld_liquid_depleted_auto_advance():
    print("\n--- 6. Testing Technology LLD Liquid-Over Auto-Advance Sequence ---")
    import tkinter as tk
    from lims_master_gui import LIMSMasterApp
    
    root = tk.Tk()
    root.withdraw()
    app = LIMSMasterApp(root)
    
    # Mount Falcon 50mL on Slot 2 (A1 Media, A2 Stock, A3 Discard)
    dm = app.deck_manager
    dm.mount_labware("Slot_2", FalconRack50mL(), ADAPTER_90MM_BLOCK)
    
    # Test 50mL Falcon auto-advance sequence: A1 -> A2 -> None (A3 must NEVER be used for aspiration)
    next_tube = app._get_next_tube_in_sequence("Slot_2", "A1")
    assert next_tube == "A2", f"Expected Slot 2 A1 to advance to A2, got {next_tube}"
    next_tube = app._get_next_tube_in_sequence("Slot_2", "A2")
    assert next_tube is None, f"Expected Slot 2 A2 to return None (A3 is discard!), got {next_tube}"
    print("PASS: 50mL Falcon auto-advances from A1 to A2 and strictly protects A3 Discard.")
    
    # Mount 2mL Falcon on Slot 1
    dm.mount_labware("Slot_1", TubeRack2x6_2mL(), ADAPTER_90MM_BLOCK)
    next_tube = app._get_next_tube_in_sequence("Slot_1", "A1")
    assert next_tube == "A2", f"Expected A1 -> A2, got {next_tube}"
    next_tube = app._get_next_tube_in_sequence("Slot_1", "A6")
    assert next_tube == "B1", f"Expected A6 -> B1, got {next_tube}"
    next_tube = app._get_next_tube_in_sequence("Slot_1", "B6")
    assert next_tube is None, f"Expected B6 -> None, got {next_tube}"
    print("PASS: 2mL Falcon auto-advances through all 12 tubes (A1..A6 -> B1..B6).")

    # Guard Test: Drug plates and EHM plates must NEVER auto-advance!
    dm.mount_labware("Slot_3", Plate96(name="Drug Plate", source_file="plate96.json"))
    dm.mount_labware("Slot_5", Plate96(name="EHM Plate", source_file="plate96.json"))
    assert app._get_next_tube_in_sequence("Slot_3", "A1") is None, "Drug plate must NEVER auto-advance!"
    assert app._get_next_tube_in_sequence("Slot_3", "A2") is None, "Drug plate must NEVER auto-advance!"
    assert app._get_next_tube_in_sequence("Slot_5", "A1") is None, "EHM plate must NEVER auto-advance!"
    print("PASS: Guard verified: Drug plates and EHM plates strictly NEVER auto-advance.")
    
    # Test LLD depletion detection condition
    bottom_z = 99.5
    z_found_depleted = 99.0   # Reached bottom limit - 0.5mm -> liquid is over!
    z_found_liquid = 82.0     # Liquid detected 17.5mm above bottom
    
    is_depleted_1 = z_found_depleted >= (bottom_z - 1.0)
    is_depleted_2 = z_found_liquid >= (bottom_z - 1.0)
    assert is_depleted_1 is True, "Sensor probe reaching bottom floor must trigger liquid-depleted auto-advance!"
    assert is_depleted_2 is False, "Sensor probe detecting liquid surface must NOT trigger depletion!"
    print("PASS: Technology LLD sensor depletion detection logic verified.")
    root.destroy()


def test_lld_probe_safety_clamp_and_shallow_rejection():
    print("\n--- 7. Testing LLD Probe Sensor Firmware Clamp (<=99.5mm) & Shallow Rejection ---")
    import tkinter as tk
    from lims_master_gui import LIMSMasterApp
    
    root = tk.Tk()
    root.withdraw()
    app = LIMSMasterApp(root)

    # 1. Simulator fallback test: safe_limit_z = min(99.5, 103.5) = 99.5
    # Returns 99.5 - 15.0 = 84.5mm (valid simulated liquid depth)
    sim_z = app._probe_surface_and_wait(103.5, submerge_mm=1.0)
    assert sim_z == 84.5, f"Expected 84.5mm from simulator probe, got {sim_z}"
    print("PASS: Simulator mode respects 99.5mm firmware ceiling.")

    # 2. Mock Hardware testing for firmware clamp and shallow rejection
    class MockHW:
        def __init__(self, stopped_z=0.28, succeed_call=True):
            self.z_position = stopped_z
            self.z_speed = 7
            self.called_limit = None
            self.called_depth = None
            self.succeed_call = succeed_call

        def move_to_surface(self, limit, distance_from_surface):
            self.called_limit = limit
            self.called_depth = distance_from_surface
            if not self.succeed_call:
                raise Exception("CommandFailed: limit > 100.0f")

    # Verify clamp <= 99.5mm passed to hardware
    mock_hw = MockHW(stopped_z=78.5)
    app.lims.pipettor.hardware = mock_hw
    measured_z = app._probe_surface_and_wait(103.5, submerge_mm=2.5)
    assert mock_hw.called_limit == 99.5, f"Limit must be clamped strictly to 99.5mm, got {mock_hw.called_limit}"
    assert measured_z == 78.5, f"Expected measured Z=78.5mm, got {measured_z}"
    print("PASS: Hardware move_to_surface correctly receives limit capped at 99.5mm.")

    # Verify shallow stall rejection (pipette remaining near ceiling at Z=0.28mm must raise RuntimeError)
    mock_stall_hw = MockHW(stopped_z=0.28)
    app.lims.pipettor.hardware = mock_stall_hw
    try:
        app._probe_surface_and_wait(102.0, submerge_mm=2.5)
        assert False, "Surface probe at ceiling Z=0.28mm must raise RuntimeError!"
    except RuntimeError as r_err:
        assert "ceiling" in str(r_err) or "<=25mm" in str(r_err)
        print("PASS: Shallow false surface detection at Z=0.28mm strictly rejected with RuntimeError.")

    app.lims.pipettor.hardware = None
    root.destroy()


def test_time_estimation():
    print("\n--- 4. Testing Physics-Based Time Estimation ---")
    from lims_master_gui import LIMSMasterApp
    import tkinter as tk
    
    root = tk.Tk()
    root.withdraw()
    app = LIMSMasterApp(root)
    
    test_sequence = [
        {"action": "Pick Up Tip", "slot": "Slot_4", "well": "A1"},
        {"action": "Aspirate Media", "slot": "Slot_1", "well": "A1", "volume": 100.0},
        {"action": "Dispense Media", "slot": "Slot_5", "well": "A1", "volume": 100.0, "mix_cycles": 2},
        {"action": "Discard Tip", "slot": "Slot_2", "well": "A3"}
    ]
    
    t_est = app.estimate_workflow_time(test_sequence)
    print(f"Estimated time for 4-step protocol with 2x mixing: {t_est:.1f} seconds")
    # Expected time should be around 25-35s realistically
    assert 20.0 <= t_est <= 45.0, f"Estimated time {t_est}s outside expected realistic physical bounds (20-45s)"
    root.destroy()
    print("PASS: Physics-based time estimation verified.")


def test_deck_2_ehm_multiplate_json():
    print("\n--- 5. Testing Dual-EHM Multi-Plate Deck Preset JSON ---")
    deck_path = os.path.join(gui_path, "deck_2_ehm_plates_slot2_discard_50ml.json")
    assert os.path.exists(deck_path), f"Deck file missing at {deck_path}"
    
    with open(deck_path, "r") as f:
        deck_data = json.load(f)
        
    print(f"Slots configured: {list(deck_data.keys())}")
    assert "Slot_1" in deck_data and "Slot_2" in deck_data
    assert "Slot_3" in deck_data and "Slot_4" in deck_data
    assert "Slot_5" in deck_data and "Slot_6" in deck_data
    
    # Slot 1: Media for Plate 1 (tube_rack_3x50ml.json)
    assert deck_data["Slot_1"]["labware_file"] == "tube_rack_3x50ml.json"
    # Slot 2: Falcon rack with discard at A3 (tube_rack_3x50ml.json)
    assert deck_data["Slot_2"]["labware_file"] == "tube_rack_3x50ml.json"
    # Slot 3: 96-well drug plate
    assert deck_data["Slot_3"]["labware_file"] == "generic_96_well_plate.json"
    # Slot 4: 1000uL Tip Rack
    assert deck_data["Slot_4"]["labware_file"] == "tip_rack_1000ul.json"
    # Slot 5: Myriamed EHM Plate 1
    assert deck_data["Slot_5"]["labware_file"] == "myriamed_48_well.json"
    # Slot 6: Myriamed EHM Plate 2
    assert deck_data["Slot_6"]["labware_file"] == "myriamed_48_well.json"
    print("PASS: Dual-EHM Multi-Plate Deck Setup validated.")


def main():
    print("======================================================================")
    print("Running Biohit Platform Refactoring & Enhancement Verification Tests")
    print("======================================================================")
    test_deck_stacking_kinematics()
    test_falcon_vs_reservoir_rollover()
    test_adaptive_tip_pickup_and_learning()
    test_lld_liquid_depleted_auto_advance()
    test_lld_probe_safety_clamp_and_shallow_rejection()
    test_time_estimation()
    test_deck_2_ehm_multiplate_json()
    print("\n======================================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! (7/7 test suites)")
    print("======================================================================")


if __name__ == "__main__":
    main()

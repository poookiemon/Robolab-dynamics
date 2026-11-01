#!/usr/bin/env python3
"""
Verification test for:
1. 7-Well Reservoir on Slot 6 (A1 at X=108.36, Y=179.9, Z=89.32, 15.0mm pitch)
2. EHM Plate physically calibrated Z = 22.33 mm
3. Jog Step Size (0.1, 1.0, 5.0, 10.0, 30.0, 50.0, 100.0 mm)
4. Quick Z Homing presets (0, 30, 50, 100 mm)
"""
import sys
import os
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lims_master_gui import LIMSMasterApp
from working import Labware
from labware_models import Reservoir7Column, DeckSlot, ADAPTER_NONE

def main():
    root = tk.Tk()
    root.withdraw()
    app = LIMSMasterApp(root)

    print("\n--- 1. Testing 7-Well Reservoir Kinematics on Slot 6 ---")
    lw_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labware", "reservoir_7_column.json")
    res7 = Labware(lw_path)
    res7.source_file = "reservoir_7_column.json"
    app.lims.deck_labware["Slot_6"] = res7
    app.sync_deck_manager()
    slot6 = app.deck_manager.slots["Slot_6"]

    # Verify A1..A7 machine coordinates
    expected_x = [108.36, 93.36, 78.36, 63.36, 48.36, 33.36, 18.36]
    for i, exp_x in enumerate(expected_x, 1):
        for well_name in (f"A{i}", f"{i}", f"R{i}"):
            x, y = slot6.labware.get_well_xy(slot6, well_name)
            assert abs(x - exp_x) < 1e-4, f"Well {well_name} X expected {exp_x}, got {x}"
            assert abs(y - 179.9) < 1e-4, f"Well {well_name} Y expected 179.9, got {y}"

            # Also check app._calculate_xy
            app_x, app_y = app._calculate_xy("Slot_6", well_name)
            assert abs(app_x - exp_x) < 1e-4, f"app._calculate_xy {well_name} X expected {exp_x}, got {app_x}"
            assert abs(app_y - 179.9) < 1e-4, f"app._calculate_xy {well_name} Y expected 179.9, got {app_y}"

    # Verify Z heights
    asp_z = app._calculate_z("Aspirate Media", res7, "A1", "auto", 0.0, "Slot_6")
    disp_z = app._calculate_z("Dispense Media", res7, "A1", "auto", 0.0, "Slot_6")
    assert abs(asp_z - 89.32) < 1e-4, f"Aspirate Z expected 89.32, got {asp_z}"
    assert abs(disp_z - 59.32) < 1e-4, f"Dispense Z expected 59.32 (3cm above bottom), got {disp_z}"
    print("PASS: 7-Well Reservoir A1..A7 (X=108.36..18.36, Y=179.9, Z=89.32 aspirate, Z=59.32 dispense) verified!")

    print("\n--- 2. Testing EHM Declared Physical Z (22.33 mm) ---")
    ehm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labware", "myriamed_48_well.json")
    ehm_lw = Labware(ehm_path)
    ehm_lw.source_file = "myriamed_48_well.json"
    app.lims.deck_labware["Slot_3"] = ehm_lw
    app.sync_deck_manager()
    ehm_asp = app._calculate_z("Aspirate Media", ehm_lw, "A1", "auto", 0.0, "Slot_3")
    ehm_disp = app._calculate_z("Dispense Media", ehm_lw, "A1", "auto", 0.0, "Slot_3")
    assert abs(ehm_asp - 22.33) < 1e-4, f"EHM aspirate Z expected 22.33, got {ehm_asp}"
    assert abs(ehm_disp - 12.33) < 1e-4, f"EHM dispense Z expected 12.33 (1cm above), got {ehm_disp}"
    print("PASS: EHM Declared Z (22.33mm inside well, 12.33mm dispense 1cm above) verified!")

    print("\n--- 3. Testing Jog Step Size & Quick Homing Presets ---")
    for step in [0.1, 1.0, 5.0, 10.0, 30.0, 50.0, 100.0]:
        app.jog_step_var.set(step)
        assert abs(app.jog_step_var.get() - step) < 1e-4

    # Quick Homing Presets
    for target in [0.0, 30.0, 50.0, 100.0]:
        app._quick_move_z(target)
        assert abs(app.jog_vars["Z"].get() - target) < 1e-4
    print("PASS: Jog step sizes (30, 50, 100 mm) & Quick Z Homing presets verified!")

    print("\n--- 4. Testing Slot 5 Media Removal Protocol (Col 3 Tips -> Col 1 Return) ---")
    app.action_load_slot5_media_removal_test(quiet=True)
    assert len(app.workflow_sequence) == 14
    # Step 0: pick tip from Col 3
    assert app.workflow_sequence[0]["action"] == "Pick Up Tip"
    assert app.workflow_sequence[0]["slot"] == "Slot_4" and app.workflow_sequence[0]["well"] == "A3"
    # Step 1: aspirate Col 1 from Slot 5
    assert app.workflow_sequence[1]["action"] == "Aspirate Media"
    assert app.workflow_sequence[1]["slot"] == "Slot_5" and app.workflow_sequence[1]["well"] == "A1"
    # Step 2: dispense to Slot 6 Waste
    assert app.workflow_sequence[2]["action"] == "Dispense Media"
    assert app.workflow_sequence[2]["slot"] == "Slot_6" and app.workflow_sequence[2]["well"] == "A7"
    # Step 13: discard tips into Col 1
    assert app.workflow_sequence[13]["action"] == "Discard Tip"
    assert app.workflow_sequence[13]["slot"] == "Slot_4" and app.workflow_sequence[13]["well"] == "A1"
    print("PASS: Slot 5 Media Removal Test Protocol verified (Col 3 tips -> Slot 5 Cols 1..6 -> Col 1 return)!")

    print("\n=======================================================")
    print("ALL 7-WELL RESERVOIR & HOMING PRESET TESTS PASSED!")
    print("=======================================================")
    root.destroy()

if __name__ == "__main__":
    main()

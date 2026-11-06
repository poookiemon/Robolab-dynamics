#!/usr/bin/env python3
"""
Test Suite for Unified Protocols and GUI Deck Setup & Loading:
- 8-Channel Multi (8x1000 uL)
- 300 uL Single-Channel
- 20 uL Single-Channel
"""

import json
import os
import sys
import tkinter as tk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from lims_master_gui import LIMSMasterApp

def test_protocol_files_exist():
    print("--- 1. Testing Protocol JSON File Generation ---")
    repo_root = os.path.dirname(SCRIPT_DIR)
    expected_files = [
        "ehm_8ch_1000ul_media_change_and_drug_7.5uL.json",
        "ehm_8ch_1000ul_media_change_and_drug_5.0uL.json",
        "ehm_8ch_1000ul_dmso_drug_dilution.json",
        "ehm_8ch_1000ul_media_change_plate5_plate6.json",
        "ehm_8ch_10ul_drug_addition_to_ehm_7.5uL.json",
        "ehm_8ch_10ul_drug_addition_to_ehm_5.0uL.json",
        "ehm_1ch_300ul_media_change_and_drug_7.5uL.json",
        "ehm_1ch_300ul_media_change_and_drug_5.0uL.json",
        "ehm_1ch_300ul_dmso_drug_dilution.json",
        "ehm_1ch_20ul_drug_addition_7.5uL.json",
        "ehm_1ch_20ul_drug_addition_5.0uL.json",
        "ehm_1ch_20ul_dmso_drug_dilution.json",
    ]

    for d in [os.path.join(SCRIPT_DIR, "protocols"), os.path.join(repo_root, "protocols")]:
        for fn in expected_files:
            fp = None
            for root, _, files in os.walk(d):
                if fn in files:
                    fp = os.path.join(root, fn)
                    break
            assert fp and os.path.exists(fp), f"Missing protocol file: {fn} in {d}"
            with open(fp, "r") as f:
                steps = json.load(f)
            assert isinstance(steps, list) and len(steps) > 0, f"Protocol {fn} is empty!"
            # Verify 20uL volumes
            if "20ul" in fn:
                for s in steps:
                    v = float(s.get("volume", 0.0))
                    assert v <= 20.0, f"Step volume {v} exceeds 20 uL in {fn}!"
    print(f"PASS: All {len(expected_files)} protocols verified in both protocol directories.")

def test_gui_loading():
    print("\n--- 2. Testing GUI Protocol Loading & Deck Setup Methods ---")
    root = tk.Tk()
    root.withdraw()
    try:
        app = LIMSMasterApp(root)

        # 1. 8-Channel Media Change + 7.5 uL Drug
        app.switch_pipettor_head(True, quiet=True)
        assert app.lims.pipettor.multichannel is True

        p8_path = LIMSMasterApp.resolve_protocol_path("ehm_8ch_1000ul_media_change_and_drug_7.5uL.json")
        with open(p8_path, "r") as f:
            seq8 = json.load(f)
        app._populate_workflow_from_sequence(seq8, "8-CH Media Change + 7.5uL Drug")
        assert len(app.workflow_sequence) == 72
        assert app.wf_box.size() == 72
        print("PASS: 8-Channel Media Change + 7.5 uL Drug loaded (72 steps).")

        # 2. 8-Channel DMSO Dilution
        p8_dmso = LIMSMasterApp.resolve_protocol_path("ehm_8ch_1000ul_dmso_drug_dilution.json")
        with open(p8_dmso, "r") as f:
            seq8_dmso = json.load(f)
        app._populate_workflow_from_sequence(seq8_dmso, "8-CH DMSO Dilution")
        assert len(app.workflow_sequence) == 26
        print("PASS: 8-Channel DMSO Dilution loaded (26 steps).")

        # 2b. 1-10 µL Single-Channel Dedicated Drug Addition to BOTH EHM Plates
        p10_path = LIMSMasterApp.resolve_protocol_path("ehm_1ch_10ul_drug_addition_to_ehm_7.5uL.json")
        with open(p10_path, "r") as f:
            seq10 = json.load(f)
        app._populate_workflow_from_sequence(seq10, "1-10 uL Drug Addition to EHM 7.5uL")
        assert len(app.workflow_sequence) == 252, f"Expected 252 steps, got {len(app.workflow_sequence)}"
        p1_steps = [s for s in seq10 if s.get("slot") == "Slot_5" and s.get("action") == "Dispense Media"]
        p2_steps = [s for s in seq10 if s.get("slot") == "Slot_6" and s.get("action") == "Dispense Media"]
        assert len(p1_steps) == 48, f"Expected 48 dispenses for Plate 1 (Slot 5), got {len(p1_steps)}"
        assert len(p2_steps) == 42, f"Expected 42 dispenses for Plate 2 (Slot 6), got {len(p2_steps)}"
        assert all(s.get("slot") == "Slot_3" for s in seq10 if s.get("action") == "Aspirate Media"), "All drug aspirations must come from Slot 3"
        pick_tips = [s.get("well") for s in seq10 if s.get("action") == "Pick Up Tip"]
        discard_tips = [s.get("well") for s in seq10 if s.get("action") == "Discard Tip"]
        assert len(pick_tips) == 36, f"Expected 36 tips picked, got {len(pick_tips)}"
        assert len(discard_tips) == 36, f"Expected 36 tips discarded, got {len(discard_tips)}"
        # Verify fresh tips come from Cols 1..5 and graveyard is Cols 7..11
        assert all(int(w[1:]) <= 5 for w in pick_tips), "All fresh tips must be picked from Columns 1..5"
        assert all(int(w[1:]) >= 7 for w in discard_tips), "All used tips must be discarded to Graveyard Columns 7..11"
        assert all(s.get("discard_z_override") == 40.5 for s in seq10 if s.get("action") == "Discard Tip"), "Graveyard discard Z must be 40.5 mm"
        print("PASS: 1-10 µL Single-Channel Drug Addition to Both EHMs verified (252 steps: 36 tips, Slot 3 Drug -> Slot 5 Plt 1 & Slot 6 Plt 2).")

        # 3. 300 uL Single-Channel Media Change + 7.5 uL Drug
        app.switch_pipettor_head(False, quiet=True)
        assert app.lims.pipettor.multichannel is False
        p300_path = LIMSMasterApp.resolve_protocol_path("ehm_1ch_300ul_media_change_and_drug_7.5uL.json")
        with open(p300_path, "r") as f:
            seq300 = json.load(f)
        app._populate_workflow_from_sequence(seq300, "300 uL Media Change + 7.5uL Drug")
        assert len(app.workflow_sequence) == 1372
        print("PASS: 300 uL Single-Channel Media Change + 7.5 uL Drug loaded (1372 steps).")

        # 4. 20 uL Single-Channel Drug Addition (7.5 uL)
        p20_path = LIMSMasterApp.resolve_protocol_path("ehm_1ch_20ul_drug_addition_7.5uL.json")
        with open(p20_path, "r") as f:
            seq20 = json.load(f)
        app._populate_workflow_from_sequence(seq20, "20 uL Drug Addition 7.5uL")
        assert len(app.workflow_sequence) == 206
        print("PASS: 20 uL Single-Channel Drug Addition loaded (206 steps).")

        # 5. 20 uL Single-Channel DMSO Dilution
        p20_dmso = LIMSMasterApp.resolve_protocol_path("ehm_1ch_20ul_dmso_drug_dilution.json")
        with open(p20_dmso, "r") as f:
            seq20_dmso = json.load(f)
        app._populate_workflow_from_sequence(seq20_dmso, "20 uL DMSO Dilution")
        assert len(app.workflow_sequence) == 122
        print("PASS: 20 uL Single-Channel DMSO Dilution loaded (122 steps).")

        # 5b. Verify 7-column and 6-column reservoir options & calibrated depths
        from labware_models import Reservoir6Column, Reservoir7Column
        app.switch_pipettor_head(True, quiet=True)
        res6 = Reservoir6Column(source_file="reservoir_6_column.json")
        res7 = Reservoir7Column(source_file="reservoir_7_column.json")
        assert app._calculate_z("Aspirate Media", res6, "A1", "auto", 0.0, "Slot_6") == 90.42
        assert app._calculate_z("Dispense Media", res6, "A6", "auto", 0.0, "Slot_6") == 8.37
        assert app._calculate_z("Aspirate Media", res7, "A1", "auto", 0.0, "Slot_6") == 90.42
        assert app._calculate_z("Dispense Media", res7, "A7", "auto", 0.0, "Slot_6") == 8.37
        print("PASS: Calibrated heights verified identical (Z=90.42 take, Z=8.37 discard) for both 6-col and 7-col reservoirs.")

        # 6. Test Tip Requirements and Clearance Slots Analysis
        print("\n--- 3. Testing Tip Requirements & Empty Clearance Slots ---")
        # 8-CH protocol check
        ti8, es8, as8 = app._analyze_protocol_tips_and_slots(
            sequence=seq8,
            is_multichannel=True,
            deck_setup={"Slot_1": "plate.json", "Slot_2": "(Empty / Clearance)", "Slot_3": "p5.json", "Slot_4": "tips.json", "Slot_5": "p6.json", "Slot_6": "res.json"},
            slot_descriptions={"Slot_2": "Clearance zone (Empty)"}
        )
        assert any("48 fresh tips" in t for t in ti8), f"Expected 48 tips for 8-ch, got: {ti8}"
        assert "Slot 2" in es8, f"Expected Slot 2 in empty slots, got: {es8}"
        print(f"PASS: 8-CH Tip & Clearance Analysis: {ti8} | Empty: {es8}")

        # 20 uL protocol check
        ti20, es20, as20 = app._analyze_protocol_tips_and_slots(
            sequence=seq20,
            is_multichannel=False,
            deck_setup={"Slot_1": "(Empty / Clearance)", "Slot_2": "res.json", "Slot_3": "plate.json", "Slot_4": "tips.json", "Slot_5": "p1.json", "Slot_6": "p2.json"},
            slot_descriptions={"Slot_1": "Clearance zone (Empty)"}
        )
        assert any("7 fresh tips" in t for t in ti20), f"Expected 7 tips for 20uL, got: {ti20}"
        assert "Slot 1" in es20, f"Expected Slot 1 in empty slots, got: {es20}"
        print(f"PASS: 20 uL Tip & Clearance Analysis: {ti20} | Empty: {es20}")

        # 300 uL protocol check (All slots occupied)
        ti300, es300, as300 = app._analyze_protocol_tips_and_slots(
            sequence=seq300,
            is_multichannel=False,
            deck_setup={"Slot_1": "res.json", "Slot_2": "res.json", "Slot_3": "plate.json", "Slot_4": "tips.json", "Slot_5": "p1.json", "Slot_6": "p2.json"},
            slot_descriptions={"Slot_1": "Fresh", "Slot_2": "Waste", "Slot_3": "Drug", "Slot_4": "Tips", "Slot_5": "P1", "Slot_6": "P2"}
        )
        assert any("20 fresh tips" in t for t in ti300), f"Expected 20 tips for 300uL, got: {ti300}"
        assert len(es300) == 0, f"Expected 0 empty slots for 300uL full deck, got: {es300}"
        print(f"PASS: 300 uL Tip & Clearance Analysis: {ti300} | Empty: {es300}")

        # Check Tab 4 dynamic deck summary widget
        assert hasattr(app, "lbl_deck_summary"), "lbl_deck_summary missing on Tab 4 run_frame"
        app._update_deck_and_tip_preview()
        summary_text = app.lbl_deck_summary.cget("text")
        assert "Tips Needed" in summary_text and "KEEP EMPTY" in summary_text, f"Summary widget text malformed: {summary_text}"
        print(f"PASS: Tab 4 Live Deck & Tip Summary: {summary_text.replace(chr(10), ' | ')}")

        # 7. Test 2-Step Dynamic Protocol Dropdown & Homing Tools
        print("\n--- 4. Testing 2-Step Dynamic Protocol Dropdown & Homing Tools ---")
        assert hasattr(app, "proto_pipettor_cb"), "proto_pipettor_cb missing"
        assert hasattr(app, "proto_workflow_cb"), "proto_workflow_cb missing"
        assert hasattr(app, "btn_load_proto"), "btn_load_proto missing"

        # 7a. Test 1-10 µL Single-Channel
        app.proto_pipettor_var.set("1-10 µL Single-Channel [Drug Addition to EHM]")
        app._on_proto_pipettor_selected()
        assert app.lims.pipettor.multichannel is False
        assert app.lims.pipettor.tip_volume == 10.0
        assert "1-10 µL SINGLE" in app.lbl_head_badge.cget("text")
        p10_choices = list(app.proto_workflow_cb["values"])
        assert any("7.5 µL" in c for c in p10_choices)
        assert any("5.0 µL" in c for c in p10_choices)
        print(f"PASS: 1-10 uL Single Pipettor selected -> {len(p10_choices)} protocols populated: {p10_choices}")

        # 7b. Test 300 uL Single-Channel
        app.proto_pipettor_var.set("300 µL Single-Channel [Prepping DMSO-Drug]")
        app._on_proto_pipettor_selected()
        assert app.lims.pipettor.multichannel is False
        assert app.lims.pipettor.tip_volume == 300.0
        assert "1×300 µL SINGLE" in app.lbl_head_badge.cget("text")
        p300_choices = list(app.proto_workflow_cb["values"])
        assert any("DMSO-Drug" in c or "96-Well" in c for c in p300_choices)
        print(f"PASS: 300 uL Single Pipettor selected -> {len(p300_choices)} protocols populated: {p300_choices}")

        # 7c. Test 8-Channel Multi (8x1000 uL)
        app.proto_pipettor_var.set("8-Channel Multi (8×1000 µL) [Media Change]")
        app._on_proto_pipettor_selected()
        assert app.lims.pipettor.multichannel is True
        assert app.lims.pipettor.tip_volume == 1000.0
        assert "8×1000 µL MULTI" in app.lbl_head_badge.cget("text")
        p1000_choices = list(app.proto_workflow_cb["values"])
        assert any("Media Change" in c for c in p1000_choices)
        assert any("Fresh Media Only" in c for c in p1000_choices)
        assert any("Test Slot 5" in c for c in p1000_choices)
        print(f"PASS: 8x1000 uL Multi Pipettor selected -> {len(p1000_choices)} protocols populated: {p1000_choices}")

        # 7e. Test Quick Homing & Safe Z Tools
        app.current_pos = {"X": 45.0, "Y": 60.0, "Z": 25.0}
        app.jog_vars["X"].set(45.0)
        app.jog_vars["Z"].set(25.0)
        app.quick_home_head()
        assert app.current_pos["X"] == 0.0 and app.current_pos["Y"] == 0.0 and app.current_pos["Z"] == 0.0
        assert app.jog_vars["X"].get() == 0.0 and app.jog_vars["Z"].get() == 0.0
        print("PASS: Quick Home Head verified (origin reset to 0,0,0).")

        app.jog_vars["Z"].set(89.32)
        app.quick_safe_z()
        assert app.jog_vars["Z"].get() == 0.0
        print("PASS: Quick Safe Z verified (Z clearance reset to 0.0 mm).")

    finally:
        try:
            app.on_closing()
        except Exception:
            pass

    print("\n=======================================================")
    print("ALL UNIFIED PROTOCOL TESTS & GUI CHECKS PASSED (100%)!")
    print("=======================================================")

if __name__ == "__main__":
    test_protocol_files_exist()
    test_gui_loading()

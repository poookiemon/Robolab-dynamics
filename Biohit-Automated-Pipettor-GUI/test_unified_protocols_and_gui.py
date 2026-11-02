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
        "ehm_1ch_300ul_media_change_and_drug_7.5uL.json",
        "ehm_1ch_300ul_media_change_and_drug_5.0uL.json",
        "ehm_1ch_300ul_dmso_drug_dilution.json",
        "ehm_1ch_20ul_drug_addition_7.5uL.json",
        "ehm_1ch_20ul_drug_addition_5.0uL.json",
        "ehm_1ch_20ul_dmso_drug_dilution.json",
    ]

    for d in [os.path.join(SCRIPT_DIR, "protocols"), os.path.join(repo_root, "protocols")]:
        for fn in expected_files:
            fp = os.path.join(d, fn)
            assert os.path.exists(fp), f"Missing protocol file: {fp}"
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

        p8_path = os.path.join(SCRIPT_DIR, "protocols", "ehm_8ch_1000ul_media_change_and_drug_7.5uL.json")
        with open(p8_path, "r") as f:
            seq8 = json.load(f)
        app._populate_workflow_from_sequence(seq8, "8-CH Media Change + 7.5uL Drug")
        assert len(app.workflow_sequence) == 84
        assert app.wf_box.size() == 84
        print("PASS: 8-Channel Media Change + 7.5 uL Drug loaded (84 steps).")

        # 2. 8-Channel DMSO Dilution
        p8_dmso = os.path.join(SCRIPT_DIR, "protocols", "ehm_8ch_1000ul_dmso_drug_dilution.json")
        with open(p8_dmso, "r") as f:
            seq8_dmso = json.load(f)
        app._populate_workflow_from_sequence(seq8_dmso, "8-CH DMSO Dilution")
        assert len(app.workflow_sequence) == 26
        print("PASS: 8-Channel DMSO Dilution loaded (26 steps).")

        # 3. 300 uL Single-Channel Media Change + 7.5 uL Drug
        app.switch_pipettor_head(False, quiet=True)
        assert app.lims.pipettor.multichannel is False
        p300_path = os.path.join(SCRIPT_DIR, "protocols", "ehm_1ch_300ul_media_change_and_drug_7.5uL.json")
        with open(p300_path, "r") as f:
            seq300 = json.load(f)
        app._populate_workflow_from_sequence(seq300, "300 uL Media Change + 7.5uL Drug")
        assert len(app.workflow_sequence) == 1372
        print("PASS: 300 uL Single-Channel Media Change + 7.5 uL Drug loaded (1372 steps).")

        # 4. 20 uL Single-Channel Drug Addition (7.5 uL)
        p20_path = os.path.join(SCRIPT_DIR, "protocols", "ehm_1ch_20ul_drug_addition_7.5uL.json")
        with open(p20_path, "r") as f:
            seq20 = json.load(f)
        app._populate_workflow_from_sequence(seq20, "20 uL Drug Addition 7.5uL")
        assert len(app.workflow_sequence) == 206
        print("PASS: 20 uL Single-Channel Drug Addition loaded (206 steps).")

        # 5. 20 uL Single-Channel DMSO Dilution
        p20_dmso = os.path.join(SCRIPT_DIR, "protocols", "ehm_1ch_20ul_dmso_drug_dilution.json")
        with open(p20_dmso, "r") as f:
            seq20_dmso = json.load(f)
        app._populate_workflow_from_sequence(seq20_dmso, "20 uL DMSO Dilution")
        assert len(app.workflow_sequence) == 122
        print("PASS: 20 uL Single-Channel DMSO Dilution loaded (122 steps).")

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

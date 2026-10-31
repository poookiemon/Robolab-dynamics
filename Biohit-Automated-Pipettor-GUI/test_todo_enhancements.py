"""
test_todo_enhancements.py - End-to-End Verification Suite for:
1. DMSO-Drug Plate Prep Auto-Import & Custom Stock Drug Well Remapping
2. Automated Session Logging System (DDMMYYYY_HHMMSS_Session_<STATUS>.log)
3. Active Session Tip Memory (Virtual Tip Remapping & Deck Visualizer Graying)
4. Weighted Dynamic Time Estimation, HHh MMm SSs Timer, Speed Factor & Pause Compensation
"""

import json
import os
import re
import sys
import tkinter as tk

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
sys.path.insert(0, script_dir)

from lims_master_gui import LIMSMasterApp, TIP_ORDER_96
from working import Labware


def test_dmso_drug_plate_prep_popup_remapping(app: LIMSMasterApp):
    print("\n--- 1. Testing DMSO-Drug Plate Prep Auto-Import & Stock Drug Well Remapping ---")
    for fname in ("1_Serial_Dilution_Plate.json", "bakar_v2_drug_dmso_initial_loading.json"):
        p = os.path.join(script_dir, "protocols", fname)
        assert os.path.exists(p), f"Missing synced protocol: {p}"
        with open(p, "r") as f:
            seq = json.load(f)
        assert len(seq) == 125, f"Expected 125 steps in {fname}, got {len(seq)}"

        # Switch to 8-ch first to verify auto-revert to 1x200 uL single-channel
        app.switch_pipettor_head(True, quiet=True)
        assert app.lims.pipettor.multichannel is True

        custom_wells = ["C2", "D4", "E6", "F8", "H12"]
        deck_setup = {
            "Slot_1": "tube_rack_2x6_2ml.json",
            "Slot_2": "waste_trough.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "generic_96_well_plate.json",
        }
        app.apply_drug_well_mapping_and_load(
            seq,
            protocol_name=f"Test {fname}",
            deck_setup=deck_setup,
            chosen_wells=custom_wells,
            dmso_labware="reservoir_3_well.json",
        )

        # Must auto-revert to 1x200 uL single-channel
        assert app.lims.pipettor.multichannel is False, "DMSO-Drug Plate Prep must switch to 1x200 uL single-channel!"
        assert len(app.workflow_sequence) == 125

        # Steps 13, 38, 63, 88, 113 (0-based: 12, 37, 62, 87, 112) must be remapped to custom_wells
        drug_indices = [12, 37, 62, 87, 112]
        actual_drug_wells = [app.workflow_sequence[idx]["well"] for idx in drug_indices]
        assert actual_drug_wells == custom_wells, f"Expected {custom_wells}, got {actual_drug_wells}"
        for idx in drug_indices:
            assert app.workflow_sequence[idx]["slot"] == "Slot_3"
            assert float(app.workflow_sequence[idx]["volume"]) == 22.0

        # Slot_1 steps must use selected DMSO labware
        slot1_lws = {s["labware"] for s in app.workflow_sequence if s.get("slot") == "Slot_1"}
        assert slot1_lws == {"reservoir_3_well.json"}, f"Expected reservoir_3_well.json on Slot_1, got {slot1_lws}"

        # All 5 waste dispenses (24,49,74,99,124) & 5 discards (25,50,75,100,125) must target Slot_2 A1
        for end_idx in (23, 24, 48, 49, 73, 74, 98, 99, 123, 124):
            st = app.workflow_sequence[end_idx]
            assert st["slot"] == "Slot_2" and st["well"] == "A1" and st["labware"] == "waste_trough.json", (
                f"Step {end_idx+1} not routed to Slot_2 A1: {st}"
            )

    # Validation check: invalid well format must raise ValueError
    try:
        app.apply_drug_well_mapping_and_load(seq, "Invalid Test", deck_setup, ["A1", "Z99", "A3", "A4", "B1"])
        assert False, "Expected ValueError for invalid well Z99"
    except ValueError:
        pass

    print("PASS: DMSO-Drug Plate Prep remapping, Slot 1 DMSO selector, and Slot 2 A1 waste routing verified.")


def test_session_logging_all_statuses(app: LIMSMasterApp):
    print("\n--- 2. Testing Automated Session Logging System (All 6 Status Suffixes) ---")
    logs_dir = app.get_logs_dir()
    created_logs = []

    try:
        app.reset_tip_rack_memory(announce=False)
        app._set_has_tip(False)

        # (A) _COMPLETED.log
        app.workflow_sequence = [
            {"action": "Pick Up Tip", "mode": "auto", "slot": "Slot_4", "well": "A1", "volume": 0.0, "labware": "tip_rack_1000ul.json"},
            {"action": "Discard Tip", "mode": "auto", "slot": "Slot_2", "well": "A1", "volume": 0.0, "labware": "waste_trough.json"},
        ]
        app.run_sequence()
        created_logs.append(app.last_session_log_path)
        assert app.last_session_log_path.endswith("_Session_COMPLETED.log"), f"Got {app.last_session_log_path}"
        assert re.match(r"^\d{8}_\d{6}_Session_COMPLETED\.log$", os.path.basename(app.last_session_log_path))
        assert os.path.exists(app.last_session_log_path)
        with open(app.last_session_log_path, "r", encoding="utf-8") as f:
            txt = f.read()
        assert "SESSION LOG STARTED:" in txt and "Status: COMPLETED" in txt

        # (B) _ABORTED_USER.log
        app.reset_tip_rack_memory(announce=False)
        app._set_has_tip(False)
        orig_move_to = app.lims.hw.move_to

        def _abort_on_move(*args, **kwargs):
            app.stop_run()

        app.lims.hw.move_to = _abort_on_move
        try:
            app.workflow_sequence = [
                {"action": "Pick Up Tip", "mode": "auto", "slot": "Slot_4", "well": "A1", "volume": 0.0, "labware": "tip_rack_1000ul.json"},
                {"action": "Discard Tip", "mode": "auto", "slot": "Slot_2", "well": "A1", "volume": 0.0, "labware": "waste_trough.json"},
            ]
            app.run_sequence()
        finally:
            app.lims.hw.move_to = orig_move_to
        created_logs.append(app.last_session_log_path)
        assert app.last_session_log_path.endswith("_Session_ABORTED_USER.log"), f"Got {app.last_session_log_path}"

        # (C) _AUTO_ABORTED_EMPTY_TIPS.log
        app._set_has_tip(False)
        for w in TIP_ORDER_96:
            app.mark_tip_consumed("Slot_4", w, redraw=False)
        app.workflow_sequence = [
            {"action": "Pick Up Tip", "mode": "auto", "slot": "Slot_4", "well": "A1", "volume": 0.0, "labware": "tip_rack_1000ul.json"},
        ]
        app.run_sequence()
        created_logs.append(app.last_session_log_path)
        assert app.last_session_log_path.endswith("_Session_AUTO_ABORTED_EMPTY_TIPS.log"), f"Got {app.last_session_log_path}"
        app.reset_tip_rack_memory(announce=False)

        # (D) _AUTO_ABORTED_HARDWARE.log (critical ejection / collision hardware fault)
        class FailingEjectHW:
            z_position = 55.0
            z_speed = 7
            tip_pickup_force = 26

            def move_z(self, z, wait=True):
                self.z_position = z

            def eject_tip(self):
                raise RuntimeError("Motor jam on tip ejector")

        app._set_has_tip(True)
        app.lims.pipettor.hardware = FailingEjectHW()
        try:
            app.workflow_sequence = [
                {"action": "Discard Tip", "mode": "auto", "slot": "Slot_2", "well": "A1", "volume": 0.0, "labware": "waste_trough.json"},
            ]
            app.run_sequence()
        finally:
            app.lims.pipettor.hardware = None
            app._set_has_tip(False)
        created_logs.append(app.last_session_log_path)
        assert app.last_session_log_path.endswith("_Session_AUTO_ABORTED_HARDWARE.log"), f"Got {app.last_session_log_path}"
        with open(app.last_session_log_path, "r", encoding="utf-8") as f:
            hw_txt = f.read()
        assert "Traceback" in hw_txt and "ejection failed" in hw_txt

        # (E) _AUTO_ABORTED_DEPLETED.log (LLD reaches bottom floor on last reservoir well and aborts)
        class DepletedLLDHW:
            z_position = 99.2
            z_speed = 7

            def move_z(self, z, wait=True):
                self.z_position = z

            def aspirate(self, vol):
                pass

            def move_to_surface(self, limit, distance_from_surface):
                self.z_position = limit - 0.1  # Reached floor -> liquid depleted!

        lw_res = os.path.join(app.get_labware_dir(), "reservoir_3_well.json")
        app.lims.deck_labware["Slot_1"] = Labware(lw_res)
        app.lims.deck_labware["Slot_1"].source_file = "reservoir_3_well.json"
        app.sync_deck_manager()
        app._set_has_tip(True)
        app.lims.pipettor.hardware = DepletedLLDHW()
        orig_probe = app._probe_surface_and_wait
        orig_after = app.root.after

        def _auto_no_refill(ms, func=None, *args):
            if callable(func) and getattr(func, "__name__", "") == "_prompt_empty_rack":
                app.refill_decision = "abort"
                return None
            return orig_after(ms, func, *args) if func else None

        app._probe_surface_and_wait = lambda lim, submerge_mm=2.5: lim - 0.2
        app.root.after = _auto_no_refill
        try:
            app.workflow_sequence = [
                {"action": "Aspirate Media", "mode": "auto", "slot": "Slot_1", "well": "A1", "volume": 150.0, "labware": "reservoir_3_well.json"},
            ]
            app.run_sequence()
        finally:
            app._probe_surface_and_wait = orig_probe
            app.root.after = orig_after
            app.lims.pipettor.hardware = None
            app._set_has_tip(False)
        created_logs.append(app.last_session_log_path)
        assert app.last_session_log_path.endswith("_Session_AUTO_ABORTED_DEPLETED.log"), f"Got {app.last_session_log_path}"

        # (F) _AUTO_ABORTED_ERROR.log (unhandled runtime exception in worker)
        orig_sync = app.sync_deck_manager

        def _boom():
            app._start_session_log(total_steps=1, est_seconds=5.0)
            raise ZeroDivisionError("synthetic unhandled crash")

        app.sync_deck_manager = _boom
        try:
            app.workflow_sequence = [{"action": "Pick Up Tip", "slot": "Slot_4", "well": "A1"}]
            app.run_sequence()
        finally:
            app.sync_deck_manager = orig_sync
        created_logs.append(app.last_session_log_path)
        assert app.last_session_log_path.endswith("_Session_AUTO_ABORTED_ERROR.log"), f"Got {app.last_session_log_path}"

        # Ensure zero leftover _RUNNING.log files
        running_left = [f for f in os.listdir(logs_dir) if f.endswith("_RUNNING.log")]
        assert not running_left, f"Stale _RUNNING.log files left behind: {running_left}"
        print("PASS: All 6 Session Log status suffixes (_COMPLETED, _ABORTED_USER, _AUTO_ABORTED_EMPTY_TIPS, _AUTO_ABORTED_HARDWARE, _AUTO_ABORTED_DEPLETED, _AUTO_ABORTED_ERROR) verified!")
    finally:
        for p in created_logs:
            if p and os.path.exists(p):
                os.remove(p)


def test_active_session_tip_memory_and_visualizer(app: LIMSMasterApp):
    print("\n--- 3. Testing Active Session Tip Memory (Virtual Tip Remapping) & Deck Graying ---")
    logs_to_clean = []
    try:
        lw_tip = os.path.join(app.get_labware_dir(), "tip_rack_1000ul.json")
        app.lims.deck_labware["Slot_4"] = Labware(lw_tip)
        app.lims.deck_labware["Slot_4"].source_file = "tip_rack_1000ul.json"
        if "Slot_4" not in app.placed_slots:
            app.placed_slots.append("Slot_4")
        app.sync_deck_manager()
        app.reset_tip_rack_memory(announce=False)
        app._set_has_tip(False)

        # Standard 3-tip protocol hardcoded to A1, B1, C1
        standard_proto = [
            {"action": "Pick Up Tip", "mode": "auto", "slot": "Slot_4", "well": "A1", "labware": "tip_rack_1000ul.json"},
            {"action": "Discard Tip", "mode": "auto", "slot": "Slot_2", "well": "A1", "labware": "waste_trough.json"},
            {"action": "Pick Up Tip", "mode": "auto", "slot": "Slot_4", "well": "B1", "labware": "tip_rack_1000ul.json"},
            {"action": "Discard Tip", "mode": "auto", "slot": "Slot_2", "well": "A1", "labware": "waste_trough.json"},
            {"action": "Pick Up Tip", "mode": "auto", "slot": "Slot_4", "well": "C1", "labware": "tip_rack_1000ul.json"},
            {"action": "Discard Tip", "mode": "auto", "slot": "Slot_2", "well": "A1", "labware": "waste_trough.json"},
        ]

        # Run 1: Consumes A1, B1, C1
        app.workflow_sequence = [dict(s) for s in standard_proto]
        app.run_sequence()
        logs_to_clean.append(app.last_session_log_path)
        consumed_r1 = set(app.session_tip_tracker["Slot_4"]["consumed"])
        assert consumed_r1 == {"A1", "B1", "C1"}, f"Expected A1..C1 consumed, got {consumed_r1}"
        # Protocol step dicts must remain completely untouched!
        assert [s["well"] for s in app.workflow_sequence if s["action"] == "Pick Up Tip"] == ["A1", "B1", "C1"]

        # Run 2 (WITHOUT resetting tip rack): Same hardcoded A1, B1, C1 -> must dynamically remap to D1, E1, F1!
        app.workflow_sequence = [dict(s) for s in standard_proto]
        app.run_sequence()
        logs_to_clean.append(app.last_session_log_path)
        consumed_r2 = set(app.session_tip_tracker["Slot_4"]["consumed"])
        assert consumed_r2 == {"A1", "B1", "C1", "D1", "E1", "F1"}, f"Expected A1..F1 consumed, got {consumed_r2}"
        next_tip, _ = app.resolve_session_tip("Slot_4", "A1")
        assert next_tip == "G1", f"Expected next virtual tip G1, got {next_tip}"

        # Verify Deck Visualizer grays out the 6 consumed tips (#d6d8db) vs 90 fresh tips (#e7f5ff)
        app.draw_deck()
        oval_fills = [
            app.canvas.itemcget(item_id, "fill")
            for item_id in app.canvas.find_all()
            if app.canvas.type(item_id) == "oval"
        ]
        gray_count = oval_fills.count("#d6d8db")
        blue_count = oval_fills.count("#e7f5ff")
        assert gray_count == 6 and blue_count == 90, f"Expected 6 gray & 90 blue tip ovals, got gray={gray_count}, blue={blue_count}"

        # Verify 8-channel offset socket expansion helper
        socks_abc = app._expand_8ch_tip_sockets({"tip_offset_rows": +5, "mounted_channels": "A-C"}, "A1")
        assert socks_abc == ["F1", "G1", "H1"], f"Got {socks_abc}"
        socks_gh = app._expand_8ch_tip_sockets({"tip_offset_rows": -6, "mounted_channels": "G-H"}, "A1")
        assert socks_gh == ["A1", "B1"], f"Got {socks_gh}"

        # Reset Tip Rack -> back to A1, 0 gray & 96 blue
        app.reset_tip_rack_memory("Slot_4", announce=False)
        app.draw_deck()
        oval_fills_after = [
            app.canvas.itemcget(item_id, "fill")
            for item_id in app.canvas.find_all()
            if app.canvas.type(item_id) == "oval"
        ]
        assert oval_fills_after.count("#d6d8db") == 0 and oval_fills_after.count("#e7f5ff") == 96
        next_after_reset, remapped = app.resolve_session_tip("Slot_4", "A1")
        assert next_after_reset == "A1" and remapped is False
        print("PASS: Virtual Tip Remapping across runs, 8-ch offset tracking, Reset Tip Rack, and Deck Graying verified.")
    finally:
        for p in logs_to_clean:
            if p and os.path.exists(p):
                os.remove(p)


def test_weighted_time_estimation_speed_factor_and_pause_compensation(app: LIMSMasterApp):
    print("\n--- 4. Testing Weighted Time Estimation, HHh MMm SSs Format, Speed Factor & Pause Compensation ---")
    # 1. HHh MMm SSs format
    assert app.format_hms(16335) == "04h 32m 15s"
    assert app.format_hms(0) == "00h 00m 00s"

    # 2. Full 1,372-step 2-plate Media Change + Drug protocol baseline (~4.5 - 4.8 hours)
    full_proto_path = os.path.join(repo_root, "protocols", "media_change_and_drug_addition_2_plates_7.5uL.json")
    with open(full_proto_path, "r") as f:
        seq_1372 = json.load(f)
    assert len(seq_1372) == 1372
    app.switch_pipettor_head(False, quiet=True)
    app.enable_mixing_for_run = True
    est_1372 = app.estimate_workflow_time(seq_1372)
    est_hours = est_1372 / 3600.0
    print(f"Full 1,372-step baseline: {est_1372:.1f}s = {est_hours:.2f}h ({app.format_hms(est_1372)})")
    assert 4.45 <= est_hours <= 4.85, f"Expected ~4.5-4.8 hours for 1,372-step protocol, got {est_hours:.2f}h"

    # 3. Deterministic Speed Factor & Pause Compensation verification
    app.workflow_sequence = [
        {"action": "Pick Up Tip", "slot": "Slot_4", "well": "A1"},
        {"action": "Aspirate Media", "slot": "Slot_1", "well": "A1", "volume": 150.0, "labware": "reservoir_3_well.json"},
        {"action": "Dispense Media", "slot": "Slot_5", "well": "A1", "volume": 150.0, "mix_cycles": 2},
        {"action": "Discard Tip", "slot": "Slot_2", "well": "A1"},
    ]
    app.step_baseline_times = [10.0, 10.0, 10.0, 10.0]  # 40.0s nominal baseline
    app.estimated_total_time = 40.0
    app.completed_baseline_time = 0.0
    app.live_speed_factor = 1.0
    app.current_step_idx = 0
    app.run_start_time = 1000.0
    app.total_paused_seconds = 0.0
    app.pause_started_at = None
    app.active_elapsed_at_step_start = 0.0

    # At t=1004 (4s into step 1): remaining = 40 - 4 = 36s
    assert abs(app.compute_remaining_time(now=1004.0) - 36.0) < 1e-6

    # Operator pauses at t=1004 for 120 seconds (until t=1124):
    app._begin_pause_tracking(now=1004.0)
    assert abs(app.get_active_elapsed_time(now=1064.0) - 4.0) < 1e-6
    assert abs(app.compute_remaining_time(now=1124.0) - 36.0) < 1e-6, "Timer must freeze completely during pause!"
    app._end_pause_tracking(now=1124.0)
    assert abs(app.total_paused_seconds - 120.0) < 1e-6

    # Step 1 finishes at t=1132 -> active elapsed = (1132 - 1000) - 120 = 12.0s vs 10.0s baseline -> Speed Factor = 1.20x!
    app.record_step_completion_for_timer(step_baseline=10.0, now=1132.0)
    app.current_step_idx = 1
    assert abs(app.live_speed_factor - 1.20) < 1e-6, f"Expected Speed Factor 1.20x, got {app.live_speed_factor}"

    # Remaining 3 steps have 30.0s baseline -> scaled by 1.20x = 36.0s!
    rem_scaled = app.compute_remaining_time(now=1132.0)
    assert abs(rem_scaled - 36.0) < 1e-6, f"Expected 36.0s scaled remaining, got {rem_scaled}"
    print("PASS: HHh MMm SSs timer, 4.6h 1,372-step baseline, Live Speed Factor (1.20x), and Pause Compensation verified.")


def main():
    print("======================================================================")
    print("Running To-Do Enhancements & DMSO-Drug Plate Prep Verification Suite")
    print("======================================================================")
    root = tk.Tk()
    root.withdraw()
    app = LIMSMasterApp(root)
    try:
        test_dmso_drug_plate_prep_popup_remapping(app)
        test_session_logging_all_statuses(app)
        test_active_session_tip_memory_and_visualizer(app)
        test_weighted_time_estimation_speed_factor_and_pause_compensation(app)
    finally:
        app.on_closing()
    print("\n======================================================================")
    print("ALL TO-DO ENHANCEMENT TESTS PASSED SUCCESSFULLY! (4/4 test suites)")
    print("======================================================================")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
End-to-End Kinematics, 8-Nozzle Socket Occupancy, Head-Switch, and Zero-Cross-Contamination
Verification Suite for the 8x1000 uL EHM Media Change Protocol (Plate 5 & Plate 6).
"""

import os
import sys
import tkinter as tk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from working import Pipettor, Labware
from generate_8ch_1000ul_ehm_media_change import build_8ch_ehm_media_change_steps
from lims_master_gui import LIMSMasterApp


ROWS = "ABCDEFGH"


def parse_channel_mask(ch_str: str):
    """'A-C' -> [0, 1, 2], 'H' -> [7], 'A-H' -> [0..7]."""
    ch_str = ch_str.strip().upper()
    if "-" in ch_str:
        a, b = ch_str.split("-", 1)
        return list(range(ROWS.index(a), ROWS.index(b) + 1))
    return [ROWS.index(c) for c in ch_str.replace(",", "") if c in ROWS]


def test_head_reconfigure():
    print("--- 1. Testing 1x200 uL <-> 8x1000 uL Live Head Reconfiguration ---")
    p = Pipettor(tip_volume=200.0, multichannel=False)
    assert not p.multichannel and p.tip_volume == 200.0 and p.channels == 1

    class MockRealDriver:
        def __init__(self):
            self._AbstractPipettor__multichannel = False
            self._tip_vol = 200

        @property
        def is_multichannel(self):
            return self._AbstractPipettor__multichannel

        @property
        def tip_volume(self):
            return self._tip_vol

        @tip_volume.setter
        def tip_volume(self, v):
            if v == 200 and self.is_multichannel:
                raise RuntimeError("OperationNotSupported: Multi-channel requires 1000uL")
            self._tip_vol = v

    mock_hw = MockRealDriver()
    p.hardware = mock_hw

    ok, msg = p.reconfigure(1000.0, True)
    assert ok, msg
    assert p.multichannel is True and p.tip_volume == 1000.0 and p.channels == 8
    assert mock_hw.is_multichannel is True and mock_hw.tip_volume == 1000

    ok2, msg2 = p.reconfigure(200.0, False)
    assert ok2, msg2
    assert p.multichannel is False and p.tip_volume == 200.0 and p.channels == 1
    assert mock_hw.is_multichannel is False and mock_hw.tip_volume == 200
    print("PASS: Live in-place driver head switching verified without COM teardown or OperationNotSupported.")


def simulate_protocol_variant(app: LIMSMasterApp, name: str, steps, loaded_cols, pre_removed_tips=()):
    print(f"\n--- Simulating Variant: {name} ({len(steps)} steps) ---")
    lw_dir = app.get_labware_dir()
    for empty_s in ("Slot_1", "Slot_2"):
        app.lims.deck_labware.pop(empty_s, None)
    for s_name, lw_file in {
        "Slot_3": "myriamed_48_well.json",
        "Slot_4": "tip_rack_1000ul.json",
        "Slot_5": "myriamed_48_well.json",
        "Slot_6": "reservoir_6_column.json",
    }.items():
        lp = os.path.join(lw_dir, lw_file)
        app.lims.deck_labware[s_name] = Labware(lp)
        app.lims.deck_labware[s_name].source_file = lw_file
    app.sync_deck_manager()
    app.switch_pipettor_head(True, quiet=True)
    app.eight_ch_cal_offset = {"X": 0.0, "Y": 0.0, "Z": 0.0}

    # Initialize Slot_4 96-socket rack state: True = tip standing in socket
    rack = {
        (r_idx, c_idx): ((c_idx + 1) in loaded_cols)
        for r_idx in range(8)
        for c_idx in range(12)
    }
    for tip_id in pre_removed_tips:
        r_i = ROWS.index(tip_id[0])
        c_i = int(tip_id[1:]) - 1
        rack[(r_i, c_i)] = False

    mounted = [False] * 8  # True if tip currently mounted on channel 0..7
    tip_taint = [None] * 8  # Tracks condition/waste touched by each mounted tip
    res_taint = {f"A{i}": set() for i in range(1, 7)}

    # Expected drug layout per plate & row:
    expected_p5 = {
        "A": ("A1", "Drug 11"), "B": ("A1", "Drug 11"), "C": ("A1", "Drug 11"),
        "D": ("A2", "Drug 12"), "E": ("A2", "Drug 12"), "F": ("A2", "Drug 12"),
        "G": ("A3", "Drug 13"), "H": ("A3", "Drug 13"),
    }
    expected_p6 = {
        "A": ("A3", "Drug 13"),
        "B": ("A4", "Drug 14"), "C": ("A4", "Drug 14"), "D": ("A4", "Drug 14"),
        "E": ("A5", "Drug 15"), "F": ("A5", "Drug 15"), "G": ("A5", "Drug 15"),
        "H": ("A4", "Control"),
    }
    removed_wells = {"Slot_3": set(), "Slot_5": set()}
    filled_wells = {"Slot_3": {}, "Slot_5": {}}
    held_source_lane = None

    for idx, step in enumerate(steps, 1):
        action = step["action"]
        slot = step["slot"]
        well = step["well"]
        tx, ty = app._resolve_step_xy(step, slot, well)

        is_8ch = bool(app.lims.pipettor.multichannel or step.get("eight_ch_symmetric"))
        if action == "Pick Up Tip":
            tz = 90.50 if is_8ch else 55.09
        elif action == "Discard Tip" and step.get("discard_z_override") is not None:
            tz = float(step["discard_z_override"])
        else:
            tz = app._calculate_z(action, app.lims.deck_labware.get(slot), well, "auto", 0.0, slot)
            if is_8ch:
                tz = max(0.0, tz - app.EIGHT_CH_TIP_Z_COMP_MM)

        # Strict machine workspace envelope checks
        assert 0.0 <= tx <= 263.0, f"Step {idx} X out of bounds: {tx}"
        assert 0.0 <= ty <= 212.0, f"Step {idx} Y out of bounds: {ty} ({step.get('label')})"
        assert 0.0 <= tz <= 102.0, f"Step {idx} Z out of bounds: {tz} ({step.get('label')})"

        expected_ch = parse_channel_mask(step["mounted_channels"])

        if action == "Pick Up Tip":
            assert not any(mounted), f"Step {idx}: Pick Up Tip called while tips still mounted: {mounted}"
            c_idx = round((105.12 - tx) / 9.0)
            assert 0 <= c_idx < 12, f"Step {idx}: Invalid tip column X={tx}"

            actual_picked = []
            for ch in range(8):
                nozzle_y = (ty - 31.5) + ch * 9.0
                r_float = (nozzle_y - 53.62) / 9.0
                r_idx = round(r_float)
                assert abs(r_float - r_idx) < 1e-4, f"Step {idx}: Misaligned row Y={nozzle_y}"
                if 0 <= r_idx < 8:
                    if rack[(r_idx, c_idx)]:
                        rack[(r_idx, c_idx)] = False
                        mounted[ch] = True
                        tip_taint[ch] = "CLEAN"
                        actual_picked.append(ch)
            assert actual_picked == expected_ch, (
                f"Step {idx} ({step.get('label')}): Expected channels {expected_ch}, "
                f"but physically picked {actual_picked}!"
            )

        elif action == "Discard Tip":
            active_ch = [c for c in range(8) if mounted[c]]
            assert active_ch == expected_ch, f"Step {idx}: Expected mounted {expected_ch}, got {active_ch}"
            if slot == "Slot_4":
                assert abs(tz - 42.0) < 1e-6, f"Step {idx}: Rack drop/shovel Z must be 42.0mm, got {tz}"
                c_idx = round((105.12 - tx) / 9.0)
                for ch in range(8):
                    nozzle_y = (ty - 31.5) + ch * 9.0
                    r_idx = round((nozzle_y - 53.62) / 9.0)
                    if 0 <= r_idx < 8:
                        # Bare nozzles MUST NOT hit a standing tip, and dropped tips MUST land in an empty socket!
                        assert not rack[(r_idx, c_idx)], (
                            f"Step {idx} ({step.get('label')}): COLLISION at Slot_4 {ROWS[r_idx]}{c_idx + 1} "
                            f"(socket already occupied)!"
                        )
                        if mounted[ch]:
                            if step.get("is_shovel_place"):
                                assert tip_taint[ch] == "CLEAN", "Shoveled tip must be 100% clean!"
                            rack[(r_idx, c_idx)] = True
            else:
                assert slot == "Slot_6" and well == "A6" and abs(tz - 48.0) < 1e-6
            mounted = [False] * 8
            tip_taint = [None] * 8
            held_source_lane = None

        elif action == "Aspirate Media":
            active_ch = [c for c in range(8) if mounted[c]]
            assert active_ch == expected_ch
            if slot in ("Slot_3", "Slot_5"):
                # Old media removal from EHM plate (Z = 86.0 - 20.5 = 65.5 mm with 1000uL tip compensation)
                assert abs(tz - 65.5) < 1e-6, f"Expected 65.5mm, got {tz}"
                col_num = int(well[1:])
                for ch in active_ch:
                    w_id = f"{ROWS[ch]}{col_num}"
                    removed_wells[slot].add(w_id)
                    tip_taint[ch] = f"OLD_{slot}_{ROWS[ch]}"
                held_source_lane = "OLD_MEDIA"
            elif slot == "Slot_6":
                # Fresh media aspiration from Reservoir R1..R5 (Z = 101.0 - 20.5 = 80.5 mm with 1000uL tip compensation)
                assert abs(tz - 80.5) < 1e-6, f"Expected 80.5mm, got {tz}"
                lbl = step.get("label", "")
                if "Control" in lbl:
                    # CRITICAL: R4 must have ZERO drug taint when Control is aspirated!
                    assert len(res_taint[well]) == 0, f"Step {idx}: R4 contaminated before Control: {res_taint[well]}"
                    cond = "Control"
                else:
                    cond = next(d for d in ("Drug 11", "Drug 12", "Drug 13", "Drug 14", "Drug 15") if d in lbl)
                    res_taint[well].add(cond)
                for ch in active_ch:
                    assert tip_taint[ch] in ("CLEAN", cond), (
                        f"Step {idx}: Cross-contamination on Ch {ROWS[ch]} ({tip_taint[ch]} vs {cond})"
                    )
                    tip_taint[ch] = cond
                held_source_lane = (well, cond)

        elif action == "Dispense Media":
            active_ch = [c for c in range(8) if mounted[c]]
            assert active_ch == expected_ch
            if slot == "Slot_6":
                # Dispensing old media waste into R6 at brim Z = 78.0 - 20.5 = 57.5 mm
                assert well == "A6" and abs(tz - 57.5) < 1e-6, f"Expected 57.5mm, got {tz}"
                assert held_source_lane == "OLD_MEDIA"
            elif slot in ("Slot_3", "Slot_5"):
                # Dispensing fresh media onto EHM plate at brim Z = 81.0 - 20.5 = 60.5 mm
                assert abs(tz - 60.5) < 1e-6, f"Expected 60.5mm, got {tz}"
                col_num = int(well[1:])
                res_lane, cond = held_source_lane
                exp_map = expected_p5 if slot == "Slot_3" else expected_p6
                for ch in active_ch:
                    r_letter = ROWS[ch]
                    assert exp_map[r_letter] == (res_lane, cond), (
                        f"Step {idx}: Row {r_letter} on {slot} expected {exp_map[r_letter]}, got {(res_lane, cond)}"
                    )
                    w_id = f"{r_letter}{col_num}"
                    assert w_id not in filled_wells[slot], f"Step {idx}: Duplicate fill on {slot} {w_id}"
                    filled_wells[slot][w_id] = (res_lane, cond, step["volume"])

    # Verify all 48 wells of Plate 5 and all 48 wells of Plate 6 received exact fresh media
    all_48 = {f"{r}{c}" for r in ROWS for c in range(1, 7)}
    assert set(filled_wells["Slot_3"].keys()) == all_48, "Plate 5 missing wells!"
    assert set(filled_wells["Slot_5"].keys()) == all_48, "Plate 6 missing wells!"
    if len(loaded_cols) >= 4 and len(steps) > 110:
        assert removed_wells["Slot_3"] == all_48, "Plate 5 old media removal incomplete!"
        assert removed_wells["Slot_5"] == all_48, "Plate 6 old media removal incomplete!"

    print(f"PASS: {name} -> 96/96 wells verified, 0 nozzle/tip collisions, 0 cross-contamination, all XYZ in bounds!")


def main():
    test_head_reconfigure()

    root = tk.Tk()
    root.withdraw()
    try:
        app = LIMSMasterApp(root)

        # Variant A: Default Full Hands-Free Media Change (Cols 1-4 loaded, Cols 5-12 empty graveyard)
        steps_full = build_8ch_ehm_media_change_steps(
            include_old_media_removal=True,
            remove_vol_ul=550.0,
            fresh_vol_ul=500.0,
            tip_drop_mode="rack_graveyard",
            use_shovel=True,
        )
        simulate_protocol_variant(app, "Full Media Change (Shovel + Rack Graveyard)", steps_full, loaded_cols={1, 2, 3, 4})

        # Variant B: Fresh Media Only (Cols 1-2 loaded, Slot_6 R6 Vertical Tip-Drop)
        steps_fresh = build_8ch_ehm_media_change_steps(
            include_old_media_removal=False,
            fresh_vol_ul=500.0,
            tip_drop_mode="slot6_r6",
            use_shovel=True,
        )
        simulate_protocol_variant(app, "Fresh Media Only (Shovel + Slot_6 R6 Tip-Drop)", steps_fresh, loaded_cols={1, 2})

        # Variant C: Zero-Shovel Fallback (Cols 1-5 loaded, E4 & E5 pre-removed)
        steps_no_shovel = build_8ch_ehm_media_change_steps(
            include_old_media_removal=True,
            remove_vol_ul=550.0,
            fresh_vol_ul=500.0,
            tip_drop_mode="rack_graveyard",
            use_shovel=False,
        )
        simulate_protocol_variant(
            app,
            "Full Media Change (Zero-Shovel Fallback)",
            steps_no_shovel,
            loaded_cols={1, 2, 3, 4, 5},
            pre_removed_tips=("E4", "E5"),
        )
    finally:
        try:
            app.on_closing()
        except Exception:
            pass

    print("\n======================================================================")
    print("ALL 8x1000 uL EHM MEDIA CHANGE VERIFICATION TESTS PASSED (4/4)!")
    print("======================================================================")


if __name__ == "__main__":
    main()

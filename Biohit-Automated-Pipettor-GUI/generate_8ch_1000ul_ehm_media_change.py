#!/usr/bin/env python3
"""
Generator for 8-Channel (8x1000 uL) EHM Media Change Protocols (Plate 5 & Plate 6)
Supports:
1. All 8 Channels Full-Parallel Mode (Default):
   - Fast, symmetrical, 100% hands-free media addition using all 8 channels across Rows A-H.
   - Plate 5: 8 tips aspirate fresh media from Slot 6 R1 and fill Columns 1-6 in 6 single strokes.
   - Plate 6: 8 tips aspirate fresh media from Slot 6 R2 and fill Columns 1-6 in 6 single strokes.
   - Old media removal (optional): uses 8 tips to aspirate Columns 1-6 into Slot 6 Waste (R7 / R6).
2. Offset Tip-Picking Multi-Drug Mode (Legacy fallback):
   - Uses partial tip picking (1..3 tips) for individual drug conditions (D11..D15 + Control) + shovel move.

Deck Layout (8x1000 uL Mode):
- Slot_1: Empty clearance zone
- Slot_2: Empty clearance zone
- Slot_3: Plate 5 (Myriamed 48-Well EHM Plate, Cols 1..6)
- Slot_4: 1000 uL 96-Tip Rack (Cols 1-4 for Full Media Change; Cols 1-2 for Fresh-Only)
- Slot_5: Plate 6 (Myriamed 48-Well EHM Plate, Cols 1..6)
- Slot_6: 7-Column (or 6-Column) Reagent Reservoir:
    * R1 (A1): Fresh Media for Plate 5
    * R2 (A2): Fresh Media for Plate 6
    * R7 (A7) or R6 (A6): Old Media Liquid Waste and/or Tip-Drop
"""

import json
import os
from typing import List, Dict, Any


def build_8ch_ehm_media_change_steps(
    include_old_media_removal: bool = True,
    remove_vol_ul: float = 500.0,
    fresh_vol_ul: float = 500.0,
    tip_drop_mode: str = "rack_graveyard",
    use_shovel: bool = True,
    media_addition_mode: str = "all_8ch",
    p5_res_lane: int = 6,
    p6_res_lane: int = 7,
    p5_waste_lane: int = 1,
    p6_waste_lane: int = 2,
    waste_lane: int = None,
    reservoir_labware: str = "reservoir_7_column.json",
    multi_dispense: bool = True,
) -> List[Dict[str, Any]]:
    """
    Builds the complete 100% hands-free 8x1000 uL step list for Plate 5 (Slot_3) & Plate 6 (Slot_5).

    :param include_old_media_removal: If True, removes old media column-by-column (8 tips at once per plate)
                                      into Slot_6 Waste immediately before refilling each plate.
    :param remove_vol_ul: Volume (uL) aspirated per well during old media removal (single 1000 uL stroke).
    :param fresh_vol_ul: Volume (uL) dispensed per well during fresh media addition (single 1000 uL stroke).
    :param tip_drop_mode:
        - "rack_graveyard": Drops each used tip group into its own dedicated empty column in Slot_4
                            (Cols 12..5 + emptied Col 1) at guided Z=42.0mm.
        - "slot6_r6" / "slot6_waste": Drops used tips vertically into Slot_6 Waste lane at Z=48.0mm.
    :param use_shovel:
        - True (Default for offset mode): Uses the automated 1-shovel sequence on standard full tip columns.
        - False: Zero-shovel fallback.
    :param media_addition_mode:
        - "all_8ch" (Default): Media addition uses all 8 channels across rows A-H simultaneously.
        - "offset_drugs": Legacy multi-drug condition offset tip-picking.
    :param p5_res_lane: Reservoir lane number for Plate 5 fresh media (default 6 -> A6).
    :param p6_res_lane: Reservoir lane number for Plate 6 fresh media (default 7 -> A7).
    :param p5_waste_lane: Reservoir lane number for Plate 5 discard (default 1 -> A1).
    :param p6_waste_lane: Reservoir lane number for Plate 6 discard (default 2 -> A2).
    :param waste_lane: General reservoir lane number for liquid waste (defaults to p6_waste_lane).
    :param reservoir_labware: Labware JSON filename for Slot 6 (default "reservoir_7_column.json").
    """
    steps: List[Dict[str, Any]] = []

    if "reservoir_6" in str(reservoir_labware):
        if p5_res_lane == 6 and p6_res_lane == 7:
            p5_res_lane = 5
            p6_res_lane = 6
        if waste_lane is None or waste_lane == 7:
            waste_lane = 2
    if waste_lane is None:
        waste_lane = p6_waste_lane

    waste_well = f"A{waste_lane}"

    if include_old_media_removal:
        p5_rem_col = 1
        p5_fresh_col = 2
        p6_rem_col = 3
        p6_fresh_col = 4
        shovel_dest_col = 3  # Emptied by Plate 6 old media removal
        zero_shovel_extra_col = 5
        graveyard_cols = [12, 11, 10, 9, 8, 7, 6, 1, 2] if not use_shovel else [12, 11, 10, 9, 8, 7, 6, 5, 1]
    else:
        p5_rem_col = None
        p5_fresh_col = 1
        p6_rem_col = None
        p6_fresh_col = 2
        shovel_dest_col = 1  # Emptied by Plate 5 fresh media steps
        zero_shovel_extra_col = 3
        graveyard_cols = [12, 11, 10, 9, 8, 7, 6]

    grave_idx = 0

    def add_pick_tip(col: int, offset_rows: int, channels_str: str, tips_str: str, desc: str):
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": f"A{col}",
            "volume": 0.0,
            "labware": "tip_rack_1000ul.json",
            "eight_ch_symmetric": True,
            "tip_offset_rows": int(offset_rows),
            "mounted_channels": channels_str,
            "label": f"[PICK 8-CH] Slot_4 Col {col} ({tips_str} -> Ch {channels_str}) | {desc}",
        })

    def add_discard_tip(channels_str: str, desc: str):
        nonlocal grave_idx
        if tip_drop_mode == "rack_graveyard":
            g_col = graveyard_cols[grave_idx % len(graveyard_cols)]
            grave_idx += 1
            steps.append({
                "action": "Discard Tip",
                "mode": "auto",
                "slot": "Slot_4",
                "well": f"A{g_col}",
                "volume": 0.0,
                "labware": "tip_rack_1000ul.json",
                "eight_ch_symmetric": True,
                "tip_offset_rows": 0,
                "discard_z_override": 40.5,
                "mounted_channels": channels_str,
                "label": f"[DROP 8-CH] Ch {channels_str} -> Slot_4 Col {g_col} | {desc}",
            })
        else:
            steps.append({
                "action": "Discard Tip",
                "mode": "auto",
                "slot": "Slot_6",
                "well": waste_well,
                "volume": 0.0,
                "labware": reservoir_labware,
                "eight_ch_symmetric": True,
                "tip_offset_rows": 0,
                "discard_z_override": 8.37,
                "mounted_channels": channels_str,
                "label": f"[DROP 8-CH] Ch {channels_str} -> Slot_6 {waste_well} Waste | {desc}",
            })

    def add_plate_removal(plate_slot: str, plate_label: str, tip_col: int, waste_lane_num: int = None):
        target_waste_lane = waste_lane_num if waste_lane_num is not None else waste_lane
        target_waste_well = f"A{target_waste_lane}"
        add_pick_tip(tip_col, 0, "A-H", f"A{tip_col}-H{tip_col}", f"{plate_label} Old Media Removal")
        if multi_dispense and remove_vol_ul <= 500.0:
            # Pooled Multi-Aspirate (500+500 µL): Aspirate 500 µL from Col 1, 500 µL from Col 2 -> Dispense 1000 µL to Waste
            for pair_col1, pair_col2 in [(1, 2), (3, 4), (5, 6)]:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": plate_slot,
                    "well": f"A{pair_col1}",
                    "volume": float(remove_vol_ul),
                    "labware": "myriamed_48_well.json",
                    "eight_ch_symmetric": True,
                    "mounted_channels": "A-H",
                    "track_liquid": False,
                    "no_air_cushion": True,
                    "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from {plate_label} Col {pair_col1} (1/2 to {remove_vol_ul*2:g} µL pooled) [Rows A-H]",
                })
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": plate_slot,
                    "well": f"A{pair_col2}",
                    "volume": float(remove_vol_ul),
                    "labware": "myriamed_48_well.json",
                    "eight_ch_symmetric": True,
                    "mounted_channels": "A-H",
                    "track_liquid": False,
                    "no_air_cushion": True,
                    "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from {plate_label} Col {pair_col2} (2/2 to {remove_vol_ul*2:g} µL pooled) [Rows A-H]",
                })
                pooled_dispense = float(remove_vol_ul * 2)
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": target_waste_well,
                    "volume": pooled_dispense,
                    "labware": reservoir_labware,
                    "eight_ch_symmetric": True,
                    "mounted_channels": "A-H",
                    "track_liquid": False,
                    "label": f"[WASTE 8-CH] Dispense {pooled_dispense:g} µL pooled to Slot_6 {target_waste_well} Waste ({plate_label} Cols {pair_col1}&{pair_col2})",
                })
        else:
            for c in range(1, 7):
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": plate_slot,
                    "well": f"A{c}",
                    "volume": float(remove_vol_ul),
                    "labware": "myriamed_48_well.json",
                    "eight_ch_symmetric": True,
                    "mounted_channels": "A-H",
                    "track_liquid": False,
                    "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from {plate_label} Col {c} [Rows A-H]",
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": target_waste_well,
                    "volume": float(remove_vol_ul),
                    "labware": reservoir_labware,
                    "eight_ch_symmetric": True,
                    "mounted_channels": "A-H",
                    "track_liquid": False,
                    "label": f"[WASTE 8-CH] Dispense {remove_vol_ul:g} µL to Slot_6 {target_waste_well} Waste ({plate_label} Col {c})",
                })
        add_discard_tip("A-H", f"{plate_label} Old Media Tips")

    def add_reservoir_to_plate(res_lane: int, plate_slot: str, plate_label: str, channels_str: str, cond_label: str):
        if multi_dispense and fresh_vol_ul == 500.0 and channels_str == "A-H":
            # Multi-dispense: Aspirate 1000 uL once, dispense 500 uL into Col 1, then 500 uL into Col 2 (saves 50% travel time)
            for pair_col1, pair_col2 in [(1, 2), (3, 4), (5, 6)]:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": f"A{res_lane}",
                    "volume": 1000.0,
                    "labware": reservoir_labware,
                    "eight_ch_symmetric": True,
                    "mounted_channels": channels_str,
                    "track_liquid": False,
                    "label": f"[ASPIRATE 8-CH] 1000 µL from Slot_6 R{res_lane} (Ch {channels_str}: {cond_label}, for Cols {pair_col1}&{pair_col2})",
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": plate_slot,
                    "well": f"A{pair_col1}",
                    "volume": float(fresh_vol_ul),
                    "labware": "myriamed_48_well.json",
                    "eight_ch_symmetric": True,
                    "mounted_channels": channels_str,
                    "track_liquid": False,
                    "no_blowout": True,
                    "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> {plate_label} Col {pair_col1}",
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": plate_slot,
                    "well": f"A{pair_col2}",
                    "volume": float(fresh_vol_ul),
                    "labware": "myriamed_48_well.json",
                    "eight_ch_symmetric": True,
                    "mounted_channels": channels_str,
                    "track_liquid": False,
                    "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> {plate_label} Col {pair_col2}",
                })
        else:
            for c in range(1, 7):
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": f"A{res_lane}",
                    "volume": float(fresh_vol_ul),
                    "labware": reservoir_labware,
                    "eight_ch_symmetric": True,
                    "mounted_channels": channels_str,
                    "track_liquid": False,
                    "label": f"[ASPIRATE 8-CH] {fresh_vol_ul:g} µL from Slot_6 R{res_lane} (Ch {channels_str}: {cond_label}, Col {c})",
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": plate_slot,
                    "well": f"A{c}",
                    "volume": float(fresh_vol_ul),
                    "labware": "myriamed_48_well.json",
                    "eight_ch_symmetric": True,
                    "mounted_channels": channels_str,
                    "track_liquid": False,
                    "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> {plate_label} Col {c}",
                })

    # =========================================================================
    # OPTION A: ALL 8 CHANNELS FULL-PARALLEL MEDIA ADDITION (DEFAULT)
    # =========================================================================
    if media_addition_mode == "all_8ch":
        # 1. PLATE 5 (Slot_3) -> Waste to Lane 1 (A1)
        if include_old_media_removal and p5_rem_col is not None:
            add_plate_removal("Slot_3", "Plate 5", p5_rem_col, p5_waste_lane)

        add_pick_tip(p5_fresh_col, 0, "A-H", f"A{p5_fresh_col}-H{p5_fresh_col}", "Plate 5 Fresh Media (All 8 Channels)")
        add_reservoir_to_plate(p5_res_lane, "Slot_3", "Plate 5", "A-H", "Fresh Media")
        add_discard_tip("A-H", "Plate 5 Fresh Media Tips")

        # 2. PLATE 6 (Slot_5) -> Waste to Lane 2 (A2)
        if include_old_media_removal and p6_rem_col is not None:
            add_plate_removal("Slot_5", "Plate 6", p6_rem_col, p6_waste_lane)

        add_pick_tip(p6_fresh_col, 0, "A-H", f"A{p6_fresh_col}-H{p6_fresh_col}", "Plate 6 Fresh Media (All 8 Channels)")
        add_reservoir_to_plate(p6_res_lane, "Slot_5", "Plate 6", "A-H", "Fresh Media")
        add_discard_tip("A-H", "Plate 6 Fresh Media Tips")

        return steps

    # =========================================================================
    # OPTION B: LEGACY MULTI-DRUG OFFSET TIP-PICKING
    # =========================================================================
    # PLATE 5 (Slot_3): 3 Conditions (Rows A-C Drug 11, Rows D-F Drug 12, Rows G-H Drug 13)
    if include_old_media_removal and p5_rem_col is not None:
        add_plate_removal("Slot_3", "Plate 5", p5_rem_col, p5_waste_lane)

    # 1) Drug 11 (Rows A, B, C) <- Tips F,G,H on Ch A,B,C (+5 rows) <- R1
    add_pick_tip(p5_fresh_col, +5, "A-C", f"F{p5_fresh_col}-H{p5_fresh_col}", "Plate 5 Drug 11 (Rows A-C)")
    add_reservoir_to_plate(1, "Slot_3", "Plate 5", "A-C", "Drug 11")
    add_discard_tip("A-C", "Plate 5 Drug 11")

    # 2) Drug 13 rep 1-2 (Rows G, H) <- Tips A,B on Ch G,H (-6 rows) <- R3
    add_pick_tip(p5_fresh_col, -6, "G-H", f"A{p5_fresh_col}-B{p5_fresh_col}", "Plate 5 Drug 13 (Rows G-H)")
    add_reservoir_to_plate(3, "Slot_3", "Plate 5", "G-H", "Drug 13")
    add_discard_tip("G-H", "Plate 5 Drug 13")

    # 3) Drug 12 (Rows D, E, F) <- Remaining Tips C,D,E on Ch D,E,F (-1 row) <- R2
    add_pick_tip(p5_fresh_col, -1, "D-F", f"C{p5_fresh_col}-E{p5_fresh_col}", "Plate 5 Drug 12 (Rows D-F)")
    add_reservoir_to_plate(2, "Slot_3", "Plate 5", "D-F", "Drug 12")
    add_discard_tip("D-F", "Plate 5 Drug 12")

    # PLATE 6 (Slot_5): 4 Conditions (Row H Control, Row A Drug 13, Rows B-D Drug 14, Rows E-G Drug 15)
    if include_old_media_removal and p6_rem_col is not None:
        add_plate_removal("Slot_5", "Plate 6", p6_rem_col, p6_waste_lane)

    # 4) Control / Drug 0 (Row H) <- Tip A on Ch H (-7 rows) <- CLEAN R4
    add_pick_tip(p6_fresh_col, -7, "H", f"A{p6_fresh_col}", "Plate 6 Control (Row H from clean R4)")
    add_reservoir_to_plate(4, "Slot_5", "Plate 6", "H", "Control (Clean R4)")
    add_discard_tip("H", "Plate 6 Control")

    # 5) Drug 13 rep 3 (Row A) <- Tip H on Ch A (+7 rows) <- R3
    add_pick_tip(p6_fresh_col, +7, "A", f"H{p6_fresh_col}", "Plate 6 Drug 13 (Row A)")
    add_reservoir_to_plate(3, "Slot_5", "Plate 6", "A", "Drug 13")
    add_discard_tip("A", "Plate 6 Drug 13")

    # 6) Drug 14 (Rows B, C, D) <- R4
    if use_shovel:
        add_pick_tip(
            p6_fresh_col, +4, "A-C",
            f"E{p6_fresh_col}-G{p6_fresh_col}",
            f"Shovel Pick -> move to B{shovel_dest_col}-D{shovel_dest_col}"
        )
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": f"A{shovel_dest_col}",
            "volume": 0.0,
            "labware": "tip_rack_1000ul.json",
            "eight_ch_symmetric": True,
            "tip_offset_rows": +1,
            "discard_z_override": 40.5,
            "mounted_channels": "A-C",
            "is_shovel_place": True,
            "label": f"[SHOVEL PLACE 8-CH] Ch A-C -> Slot_4 Empty B{shovel_dest_col}-D{shovel_dest_col} (shift +1 row, Z=40.5mm)",
        })
        add_pick_tip(
            shovel_dest_col, 0, "B-D",
            f"B{shovel_dest_col}-D{shovel_dest_col}",
            "Plate 6 Drug 14 (Rows B-D from still-clean R4)"
        )
    else:
        add_pick_tip(
            zero_shovel_extra_col, +4, "B-D",
            f"F{zero_shovel_extra_col}-H{zero_shovel_extra_col}",
            f"Plate 6 Drug 14 (Zero-Shovel: requires E{p6_fresh_col} & E{zero_shovel_extra_col} pre-removed)"
        )

    add_reservoir_to_plate(4, "Slot_5", "Plate 6", "B-D", "Drug 14 (R4)")
    add_discard_tip("B-D", "Plate 6 Drug 14")

    # 7) Drug 15 (Rows E, F, G) <- Remaining Tips B,C,D of p6_fresh_col onto Ch E,F,G (-3 rows) <- R5
    add_pick_tip(p6_fresh_col, -3, "E-G", f"B{p6_fresh_col}-D{p6_fresh_col}", "Plate 6 Drug 15 (Rows E-G)")
    add_reservoir_to_plate(5, "Slot_5", "Plate 6", "E-G", "Drug 15 (R5)")
    add_discard_tip("E-G", "Plate 6 Drug 15")

    return steps


def build_slot5_media_removal_test(
    remove_vol_ul: float = 550.0,
    pick_col: int = 3,
    return_col: int = 1,
    waste_lane: int = 7,
    reservoir_labware: str = "reservoir_7_column.json",
) -> List[Dict[str, Any]]:
    """
    Test protocol for Slot 5 (Plate 6) Media Removal:
    - Picks clean 8 tips from Slot 4 Column 3.
    - Aspirates 550 uL from Columns 1 to 6 of Plate 6 (Slot 5).
    - Dispenses old media into Slot 6 Waste.
    - Returns/discards used tips into Slot 4 Column 1.
    """
    steps: List[Dict[str, Any]] = []

    # 1. Pick tips from Column 3
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": f"A{pick_col}",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": f"[PICK 8-CH] Slot_4 Col {pick_col} (A{pick_col}-H{pick_col} -> Ch A-H) | Slot 5 Media Removal Test",
    })

    # 2. Aspirate from Slot 5 (Cols 1..6) and dispense to Slot 6 Waste
    for c in range(1, 7):
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c}",
            "volume": float(remove_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Slot_5 Col {c} [Rows A-H]",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": f"A{waste_lane}",
            "volume": float(remove_vol_ul),
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[WASTE 8-CH] Dispense {remove_vol_ul:g} µL to Slot_6 A{waste_lane} Waste (Slot 5 Col {c})",
        })

    # 3. Put tips back into Column 1
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": f"A{return_col}",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": f"[DROP 8-CH] Put back tips onto Slot_4 Col {return_col}",
    })

    return steps


def save_default_protocols():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    out_dirs = [
        os.path.join(script_dir, "protocols", "Machine 1 - 8x1000 uL"),
        os.path.join(repo_root, "protocols", "Machine 1 - 8x1000 uL"),
    ]

    slot5_test_steps = build_slot5_media_removal_test(
        remove_vol_ul=550.0,
        pick_col=3,
        return_col=1,
        waste_lane=2,
        reservoir_labware="reservoir_7_column.json",
    )
    full_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=True,
        remove_vol_ul=500.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="rack_graveyard",
        media_addition_mode="all_8ch",
        p5_res_lane=6,
        p6_res_lane=7,
        p5_waste_lane=1,
        p6_waste_lane=2,
        reservoir_labware="reservoir_7_column.json",
        multi_dispense=True,
    )
    full_multi_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=True,
        remove_vol_ul=500.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="rack_graveyard",
        media_addition_mode="all_8ch",
        p5_res_lane=6,
        p6_res_lane=7,
        p5_waste_lane=1,
        p6_waste_lane=2,
        reservoir_labware="reservoir_7_column.json",
        multi_dispense=True,
    )
    fresh_only_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=False,
        remove_vol_ul=550.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="slot6_waste",
        media_addition_mode="all_8ch",
        p5_res_lane=6,
        p6_res_lane=7,
        p5_waste_lane=1,
        p6_waste_lane=2,
        waste_lane=2,
        reservoir_labware="reservoir_7_column.json",
        multi_dispense=True,
    )
    fresh_multi_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=False,
        remove_vol_ul=550.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="slot6_waste",
        media_addition_mode="all_8ch",
        p5_res_lane=6,
        p6_res_lane=7,
        p5_waste_lane=1,
        p6_waste_lane=2,
        waste_lane=2,
        reservoir_labware="reservoir_7_column.json",
        multi_dispense=True,
    )
    legacy_offset_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=True,
        remove_vol_ul=550.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="rack_graveyard",
        use_shovel=True,
        media_addition_mode="offset_drugs",
        reservoir_labware="reservoir_6_column.json",
        waste_lane=6,
    )

    for d in out_dirs:
        os.makedirs(d, exist_ok=True)
        p_slot5 = os.path.join(d, "test_slot5_media_removal_col3_to_col1.json")
        p_full = os.path.join(d, "ehm_8ch_1000ul_media_change_plate5_plate6.json")
        p_full_multi = os.path.join(d, "ehm_8ch_1000ul_media_change_multi_dispense.json")
        p_fresh = os.path.join(d, "ehm_8ch_1000ul_fresh_media_only_plate5_plate6.json")
        p_fresh_multi = os.path.join(d, "ehm_8ch_1000ul_fresh_media_only_multi_dispense.json")
        p_legacy = os.path.join(d, "ehm_8ch_1000ul_media_change_offset_drugs.json")
        with open(p_slot5, "w") as f:
            json.dump(slot5_test_steps, f, indent=2)
        with open(p_full, "w") as f:
            json.dump(full_steps, f, indent=2)
        with open(p_full_multi, "w") as f:
            json.dump(full_multi_steps, f, indent=2)
        with open(p_fresh, "w") as f:
            json.dump(fresh_only_steps, f, indent=2)
        with open(p_fresh_multi, "w") as f:
            json.dump(fresh_multi_steps, f, indent=2)
        with open(p_legacy, "w") as f:
            json.dump(legacy_offset_steps, f, indent=2)
        print(f"Saved {len(slot5_test_steps)} steps -> {p_slot5}")
        print(f"Saved {len(full_steps)} steps -> {p_full}")
        print(f"Saved {len(full_multi_steps)} steps -> {p_full_multi}")
        print(f"Saved {len(fresh_only_steps)} steps -> {p_fresh}")
        print(f"Saved {len(fresh_multi_steps)} steps -> {p_fresh_multi}")
        print(f"Saved {len(legacy_offset_steps)} steps -> {p_legacy}")


if __name__ == "__main__":
    save_default_protocols()


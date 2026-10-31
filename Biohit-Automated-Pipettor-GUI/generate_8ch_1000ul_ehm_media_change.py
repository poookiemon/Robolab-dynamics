#!/usr/bin/env python3
"""
Generator for 8-Channel (8x1000 uL) EHM Media Change Protocols (Plate 5 & Plate 6)
Implements Dr. Tim Meyers' offset tip-picking + symmetric column transfer strategy:

Deck Layout (8x1000 uL Mode):
- Slot_1: Empty half-slot
- Slot_2: Empty half-slot (MUST remain clear for -Y bare-nozzle overhang during Slot_4 offset tip pickup)
- Slot_3: Plate 5 (Myriamed 48-Well EHM Plate: Rows A-C = Drug 11, Rows D-F = Drug 12, Rows G-H = Drug 13)
- Slot_4: 1000 uL 96-Tip Rack (Cols 1-4 used for Full Media Change; Cols 1-2 used for Fresh Media Only)
- Slot_5: Plate 6 (Myriamed 48-Well EHM Plate: Row A = Drug 13, Rows B-D = Drug 14, Rows E-G = Drug 15, Row H = Control)
- Slot_6: 6-Column Vertical Reagent Reservoir:
    * R1 (A1): Fresh Media for Drug 11 (Plate 5 A-C)
    * R2 (A2): Fresh Media for Drug 12 (Plate 5 D-F)
    * R3 (A3): Fresh Media for Drug 13 (Plate 5 G-H + Plate 6 A)
    * R4 (A4): Fresh Media for Control (Plate 6 H, pipetted FIRST while clean!) + Drug 14 (Plate 6 B-D)
    * R5 (A5): Fresh Media for Drug 15 (Plate 6 E-G)
    * R6 (A6): Old Media Liquid Waste (~48-53 mL) and/or Vertical 8-Ch Tip-Drop
"""

import json
import os
from typing import List, Dict, Any


def build_8ch_ehm_media_change_steps(
    include_old_media_removal: bool = True,
    remove_vol_ul: float = 550.0,
    fresh_vol_ul: float = 500.0,
    tip_drop_mode: str = "rack_graveyard",
    use_shovel: bool = True,
) -> List[Dict[str, Any]]:
    """
    Builds the complete 100% hands-free 8x1000 uL step list for Plate 5 (Slot_3) & Plate 6 (Slot_5).

    :param include_old_media_removal: If True, removes old media column-by-column (8 tips at once per plate)
                                      into Slot_6 R6 (A6) immediately before refilling each plate.
    :param remove_vol_ul: Volume (uL) aspirated per well during old media removal (single 1000 uL stroke).
    :param fresh_vol_ul: Volume (uL) dispensed per well during fresh media addition (single 1000 uL stroke).
    :param tip_drop_mode:
        - "rack_graveyard": Drops each used tip group into its own dedicated empty column in Slot_4
                            (Cols 12..5 + emptied Col 1) at guided Z=42.0mm so Slot_6 R6 is dedicated to liquid waste.
        - "slot6_r6": Drops used tips vertically into Slot_6 R6 (A6) at Z=48.0mm (vertical 100 mL tip-drop).
    :param use_shovel:
        - True (Default): Uses Dr. Tim's automated 1-shovel sequence on standard full tip columns.
        - False: Zero-shovel fallback (uses extra column where Tip E is pre-removed by operator).
    """
    steps: List[Dict[str, Any]] = []

    if include_old_media_removal:
        p5_rem_col = 1
        p5_fresh_col = 2
        p6_rem_col = 3
        p6_fresh_col = 4
        shovel_dest_col = 3  # Emptied by Plate 6 old media removal
        zero_shovel_extra_col = 5
        # Graveyard empty columns: Cols 12..6 (if zero_shovel uses 5) or Cols 12..5 + emptied Col 1 & Col 2
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
            "label": f"[PICK 8-CH] Slot_4 Col {col} ({tips_str} -> Ch {channels_str}, shift {offset_rows:+d} rows) | {desc}",
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
                "discard_z_override": 42.0,
                "mounted_channels": channels_str,
                "label": f"[DROP 8-CH] Ch {channels_str} -> Slot_4 Empty Col {g_col} (Z=42.0mm) | {desc}",
            })
        else:
            steps.append({
                "action": "Discard Tip",
                "mode": "auto",
                "slot": "Slot_6",
                "well": "A6",
                "volume": 0.0,
                "labware": "reservoir_6_column.json",
                "eight_ch_symmetric": True,
                "tip_offset_rows": 0,
                "discard_z_override": 48.0,
                "mounted_channels": channels_str,
                "label": f"[DROP 8-CH] Ch {channels_str} -> Slot_6 R6 Vertical Tip-Drop (Z=48.0mm) | {desc}",
            })

    def add_plate_removal(plate_slot: str, plate_label: str, tip_col: int):
        add_pick_tip(tip_col, 0, "A-H", f"A{tip_col}-H{tip_col}", f"{plate_label} Old Media Removal")
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
                "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g}uL from {plate_label} ({plate_slot}) Col {c} [Rows A-H]",
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": "A6",
                "volume": float(remove_vol_ul),
                "labware": "reservoir_6_column.json",
                "eight_ch_symmetric": True,
                "mounted_channels": "A-H",
                "track_liquid": False,
                "label": f"[WASTE 8-CH] Dispense {remove_vol_ul:g}uL to Slot_6 R6 Waste ({plate_label} Col {c})",
            })
        add_discard_tip("A-H", f"{plate_label} Old Media Tips")

    def add_reservoir_to_plate(res_lane: int, plate_slot: str, plate_label: str, channels_str: str, cond_label: str):
        for c in range(1, 7):
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": f"A{res_lane}",
                "volume": float(fresh_vol_ul),
                "labware": "reservoir_6_column.json",
                "eight_ch_symmetric": True,
                "mounted_channels": channels_str,
                "track_liquid": False,
                "label": f"[ASPIRATE 8-CH] {fresh_vol_ul:g}uL from Slot_6 R{res_lane} (Ch {channels_str}: {cond_label})",
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
                "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g}uL -> {plate_label} ({plate_slot}) Col {c} (Rows {channels_str}: {cond_label})",
            })

    # =========================================================================
    # PLATE 5 (Slot_3): 3 Conditions (Rows A-C Drug 11, Rows D-F Drug 12, Rows G-H Drug 13)
    # =========================================================================
    if include_old_media_removal and p5_rem_col is not None:
        add_plate_removal("Slot_3", "Plate 5", p5_rem_col)

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

    # =========================================================================
    # PLATE 6 (Slot_5): 4 Conditions (Row H Control, Row A Drug 13, Rows B-D Drug 14, Rows E-G Drug 15)
    # =========================================================================
    if include_old_media_removal and p6_rem_col is not None:
        add_plate_removal("Slot_5", "Plate 6", p6_rem_col)

    # 4) Control / Drug 0 (Row H) <- Tip A on Ch H (-7 rows) <- CLEAN R4 (pipetted BEFORE Drug 14!)
    add_pick_tip(p6_fresh_col, -7, "H", f"A{p6_fresh_col}", "Plate 6 Control (Row H from clean R4)")
    add_reservoir_to_plate(4, "Slot_5", "Plate 6", "H", "Control (Clean R4)")
    add_discard_tip("H", "Plate 6 Control")

    # 5) Drug 13 rep 3 (Row A) <- Tip H on Ch A (+7 rows) <- R3
    add_pick_tip(p6_fresh_col, +7, "A", f"H{p6_fresh_col}", "Plate 6 Drug 13 (Row A)")
    add_reservoir_to_plate(3, "Slot_5", "Plate 6", "A", "Drug 13")
    add_discard_tip("A", "Plate 6 Drug 13")

    # 6) Drug 14 (Rows B, C, D) <- R4 (still clean!)
    if use_shovel:
        # 6a) Shovel E,F,G onto Ch A,B,C (+4 rows), place gently into empty B,C,D of shovel_dest_col (+1 row, Z=42.0mm)
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
            "tip_offset_rows": +1,  # Ch A(0)->Row B(1), Ch B(1)->Row C(2), Ch C(2)->Row D(3)
            "discard_z_override": 42.0,
            "mounted_channels": "A-C",
            "is_shovel_place": True,
            "label": f"[SHOVEL PLACE 8-CH] Ch A-C -> Slot_4 Empty B{shovel_dest_col}-D{shovel_dest_col} (shift +1 row, Z=42.0mm)",
        })
        # 6b) Pick B,C,D from shovel_dest_col onto Ch B,C,D (0 row shift)
        add_pick_tip(
            shovel_dest_col, 0, "B-D",
            f"B{shovel_dest_col}-D{shovel_dest_col}",
            "Plate 6 Drug 14 (Rows B-D from still-clean R4)"
        )
    else:
        # Zero-shovel fallback:
        # - Pre-remove Tip E from zero_shovel_extra_col (so Ch A hits empty E while Ch B-D pick F-H at +4 rows)
        # - Pre-remove Tip E from p6_fresh_col (so in Step 7 Ch H hits empty E while Ch E-G pick B-D at -3 rows)
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


def save_default_protocols():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    out_dirs = [
        os.path.join(script_dir, "protocols"),
        os.path.join(repo_root, "protocols"),
    ]

    full_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=True,
        remove_vol_ul=550.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="rack_graveyard",
        use_shovel=True,
    )
    fresh_only_steps = build_8ch_ehm_media_change_steps(
        include_old_media_removal=False,
        remove_vol_ul=550.0,
        fresh_vol_ul=500.0,
        tip_drop_mode="slot6_r6",
        use_shovel=True,
    )

    for d in out_dirs:
        os.makedirs(d, exist_ok=True)
        p_full = os.path.join(d, "ehm_8ch_1000ul_media_change_plate5_plate6.json")
        p_fresh = os.path.join(d, "ehm_8ch_1000ul_fresh_media_only_plate5_plate6.json")
        with open(p_full, "w") as f:
            json.dump(full_steps, f, indent=2)
        with open(p_fresh, "w") as f:
            json.dump(fresh_only_steps, f, indent=2)
        print(f"Saved {len(full_steps)} steps -> {p_full}")
        print(f"Saved {len(fresh_only_steps)} steps -> {p_fresh}")


if __name__ == "__main__":
    save_default_protocols()

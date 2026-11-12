#!/usr/bin/env python3
"""
Generator for Unified EHM Protocols across all 3 Pipettor Heads:
1. 8-Channel Multi Pipettor (8×1000 µL)
2. 300 µL Single-Channel Pipette (1×300 µL / 200 µL)
3. 20 µL Single-Channel Pipette (1×20 µL)

Workflows Generated:
- Media Change + 7.5 µL Drug Addition
- Media Change + 5.0 µL Drug Addition
- DMSO-Drug Dilution Protocol (Interactive Drug Source Wells on Slot 3)
- Media Change Only (500 µL, 0-Contamination)
"""

import json
import os
from typing import List, Dict, Any

ROWS = "ABCDEFGH"

# =============================================================================
# 1. 8-CHANNEL MULTI PIPETTOR (8x1000 uL)
# =============================================================================

def build_8ch_media_change_and_drug_steps(
    drug_vol_ul: float = 7.5,
    remove_vol_ul: float = 500.0,
    fresh_vol_ul: float = 500.0,
    reservoir_labware: str = "reservoir_7_column.json",
    drug_source_slot: str = "Slot_1",
    drug_source_labware: str = "generic_96_well_plate.json",
    p5_waste_lane: int = 1,
    p6_waste_lane: int = 2,
    p5_fresh_lane: int = 6,
    p6_fresh_lane: int = 7,
) -> List[Dict[str, Any]]:
    """
    Builds 100% 0-contamination 8-channel protocol for Plate 5 (Slot 3) & Plate 6 (Slot 5).
    - Media removal: Plate 5 -> Slot 6 R1 (A1), Plate 6 -> Slot 6 R2 (A2) at Z=59.32 (contact-free).
    - Fresh media addition: Plate 5 from Slot 6 R6 (A6), Plate 6 from Slot 6 R7 (A7) at Z=12.33 (contact-free).
    - Drug addition: Rows A-H, drug_vol_ul from Drug Plate (Slot 1) into Col 1..6 with 5x 100 uL in-place mixing.
    """
    steps: List[Dict[str, Any]] = []

    if "reservoir_6" in reservoir_labware:
        p5_fresh_lane = 5
        p6_fresh_lane = 6
        p5_waste_lane = 1
        p6_waste_lane = 2

    # Plate 5 configuration:
    # Tips: Col 1 for removal, Col 2 for fresh media, Col 5 for drug addition
    # Graveyard: Col 12, Col 11, Col 10
    # -------------------------------------------------------------
    # 1. PLATE 5 (Slot 3)
    # -------------------------------------------------------------
    # Step A: Media Removal (Col 1 Tips) -> Slot 6 Lane 1 (A1) Discard (Pooled 500+500 µL)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A1",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": "[PICK 8-CH] Slot_4 Col 1 (A1-H1) | Plate 5 Old Media Removal",
    })
    for c1, c2 in [(1, 2), (3, 4), (5, 6)]:
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": f"A{c1}",
            "volume": float(remove_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "no_air_cushion": True,
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Plate 5 Col {c1} (1/2 to {remove_vol_ul*2:g} µL pooled) [Rows A-H]",
        })
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": f"A{c2}",
            "volume": float(remove_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "no_air_cushion": True,
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Plate 5 Col {c2} (2/2 to {remove_vol_ul*2:g} µL pooled) [Rows A-H]",
        })
        pooled_rem = float(remove_vol_ul * 2)
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": f"A{p5_waste_lane}",
            "volume": pooled_rem,
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[WASTE 8-CH] Dispense {pooled_rem:g} µL pooled to Slot_6 A{p5_waste_lane} Waste (Plate 5 Cols {c1}&{c2})",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A12",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 5 Old Media Tips -> Slot_4 Col 12 Graveyard",
    })

    # Step B: Fresh Media Addition (Col 2 Tips) - Multi-Dispense from Slot 6 Lane 6 (A6)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A2",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": "[PICK 8-CH] Slot_4 Col 2 (A2-H2) | Plate 5 Fresh Media Addition",
    })
    for c1, c2 in [(1, 2), (3, 4), (5, 6)]:
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": f"A{p5_fresh_lane}",
            "volume": 1000.0,
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[ASPIRATE 8-CH] 1000 µL from Slot_6 R{p5_fresh_lane} (Plate 5 Cols {c1}&{c2})",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": f"A{c1}",
            "volume": float(fresh_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "no_blowout": True,
            "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> Plate 5 Col {c1} (Contact-Free 1cm above)",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": f"A{c2}",
            "volume": float(fresh_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> Plate 5 Col {c2} (Contact-Free 1cm above)",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A11",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 5 Fresh Media Tips -> Slot_4 Col 11 Graveyard",
    })

    # Step C: Drug Addition (Col 5 Tips)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A5",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": f"[PICK 8-CH] Slot_4 Col 5 (A5-H5) | Plate 5 Drug Addition ({drug_vol_ul:g} µL)",
    })
    for c in range(1, 7):
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": drug_source_slot,
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": drug_source_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[ASPIRATE 8-CH DRUG] {drug_vol_ul:g} µL from {drug_source_slot} Col {c} [Rows A-H]",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "mix_cycles": 5,
            "mix_volume": 100.0,
            "track_liquid": False,
            "label": f"[DRUG+MIX 8-CH] {drug_vol_ul:g} µL -> Plate 5 Col {c} [5x 100 µL In-Place Mix]",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A10",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 5 Drug Tips -> Slot_4 Col 10 Graveyard",
    })

    # -------------------------------------------------------------
    # 2. PLATE 6 (Slot 5)
    # -------------------------------------------------------------
    # Step A: Media Removal (Col 3 Tips) -> Slot 6 Lane 2 (A2) Discard (Pooled 500+500 µL)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A3",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": "[PICK 8-CH] Slot_4 Col 3 (A3-H3) | Plate 6 Old Media Removal",
    })
    for c1, c2 in [(1, 2), (3, 4), (5, 6)]:
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c1}",
            "volume": float(remove_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "no_air_cushion": True,
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Plate 6 Col {c1} (1/2 to {remove_vol_ul*2:g} µL pooled) [Rows A-H]",
        })
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c2}",
            "volume": float(remove_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "no_air_cushion": True,
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Plate 6 Col {c2} (2/2 to {remove_vol_ul*2:g} µL pooled) [Rows A-H]",
        })
        pooled_rem = float(remove_vol_ul * 2)
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": f"A{p6_waste_lane}",
            "volume": pooled_rem,
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[WASTE 8-CH] Dispense {pooled_rem:g} µL pooled to Slot_6 A{p6_waste_lane} Waste (Plate 6 Cols {c1}&{c2})",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A9",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 6 Old Media Tips -> Slot_4 Col 9 Graveyard",
    })

    # Step B: Fresh Media Addition (Col 4 Tips) - Multi-Dispense from Slot 6 Lane 7 (A7)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A4",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": "[PICK 8-CH] Slot_4 Col 4 (A4-H4) | Plate 6 Fresh Media Addition",
    })
    for c1, c2 in [(1, 2), (3, 4), (5, 6)]:
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": f"A{p6_fresh_lane}",
            "volume": 1000.0,
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[ASPIRATE 8-CH] 1000 µL from Slot_6 R{p6_fresh_lane} (Plate 6 Cols {c1}&{c2})",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c1}",
            "volume": float(fresh_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "no_blowout": True,
            "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> Plate 6 Col {c1} (Contact-Free 1cm above)",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c2}",
            "volume": float(fresh_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[DISPENSE 8-CH] {fresh_vol_ul:g} µL -> Plate 6 Col {c2} (Contact-Free 1cm above)",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A8",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 6 Fresh Media Tips -> Slot_4 Col 8 Graveyard",
    })

    # Step C: Drug Addition (Col 6 Tips)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A6",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "mounted_channels": "A-H",
        "label": f"[PICK 8-CH] Slot_4 Col 6 (A6-H6) | Plate 6 Drug Addition ({drug_vol_ul:g} µL)",
    })
    for c in range(1, 7):
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": drug_source_slot,
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": drug_source_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[ASPIRATE 8-CH DRUG] {drug_vol_ul:g} µL from {drug_source_slot} Col {c} [Rows A-H]",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "mix_cycles": 5,
            "mix_volume": 100.0,
            "track_liquid": False,
            "label": f"[DRUG+MIX 8-CH] {drug_vol_ul:g} µL -> Plate 6 Col {c} [5x 100 µL In-Place Mix]",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A7",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "tip_offset_rows": 0,
        "discard_z_override": 40.5,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 6 Drug Tips -> Slot_4 Col 7 Graveyard",
    })

    return steps


def build_8ch_dmso_dilution_steps(dmso_labware: str = "reservoir_7_column.json") -> List[Dict[str, Any]]:
    """
    Builds 8-channel parallel serial dilution across 96-well plate (Slot 5).
    Pre-fills DMSO into Cols 2..6, transfers stock drug from Slot 3 (Cols user-selected) into Col 1,
    and performs 8-channel serial dilutions across Columns 1..6.
    Supports either 7-column or 6-column reservoir on Slot 6.
    """
    steps: List[Dict[str, Any]] = []

    # 1. Fill DMSO into Cols 2..6 of Slot 5 (using Col 1 tips)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A1",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "mounted_channels": "A-H",
        "label": "[PICK 8-CH] Slot_4 Col 1 (A1-H1) | DMSO Pre-Fill",
    })
    for c in range(2, 7):
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": "A1",
            "volume": 100.0,
            "labware": dmso_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "label": f"[ASPIRATE 8-CH] 100 µL DMSO from Slot_6 A1",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c}",
            "volume": 100.0,
            "labware": "generic_96_well_plate.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "label": f"[DISPENSE 8-CH] 100 µL DMSO -> Slot_5 Col {c}",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A12",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "label": "[DROP 8-CH] Discard DMSO Tips -> Slot_4 Col 12",
    })

    # 2. Transfer Stock Drug from Slot 3 into Slot 5 Col 1 (using Col 2 tips)
    # The Slot 3 well (A1 default) is dynamically remapped by prompt_drug_wells_and_load!
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A2",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "mounted_channels": "A-H",
        "label": "[PICK 8-CH] Slot_4 Col 2 (A2-H2) | Stock Drug Transfer",
    })
    steps.append({
        "action": "Aspirate Media",
        "mode": "auto",
        "slot": "Slot_3",
        "well": "A1",
        "volume": 150.0,
        "labware": "generic_96_well_plate.json",
        "eight_ch_symmetric": True,
        "mounted_channels": "A-H",
        "label": "[ASPIRATE 8-CH] 150 µL Stock Drug from Slot_3 A1",
    })
    steps.append({
        "action": "Dispense Media",
        "mode": "auto",
        "slot": "Slot_5",
        "well": "A1",
        "volume": 150.0,
        "labware": "generic_96_well_plate.json",
        "eight_ch_symmetric": True,
        "mounted_channels": "A-H",
        "mix_cycles": 3,
        "mix_volume": 80.0,
        "label": "[DISPENSE 8-CH] 150 µL Stock Drug -> Slot_5 Col 1 (Mix 3x 80 µL)",
    })

    # 3. Serial Dilution Col 1 -> Col 2 -> Col 3 -> Col 4 -> Col 5 -> Col 6
    for c in range(1, 6):
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c}",
            "volume": 50.0,
            "labware": "generic_96_well_plate.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "label": f"[SERIAL 8-CH] Transfer 50 µL from Col {c} -> Col {c+1}",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"A{c+1}",
            "volume": 50.0,
            "labware": "generic_96_well_plate.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "mix_cycles": 5,
            "mix_volume": 80.0,
            "label": f"[SERIAL 8-CH MIX] 50 µL in Col {c+1} (5x 80 µL Mix)",
        })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "A11",
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "eight_ch_symmetric": True,
        "label": "[DROP 8-CH] Discard Serial Dilution Tips -> Slot_4 Col 11",
    })

    return steps


# =============================================================================
# 1b. 8-CHANNEL MULTI (1-10 µL) - PARALLEL 5-TIP DRUG ADDITION TO BOTH EHMs
# =============================================================================

def build_8ch_10ul_parallel_drug_addition_steps(
    drug_vol_ul: float = 7.5,
    drug_source_slot: str = "Slot_3",
    drug_source_labware: str = "generic_96_well_plate.json",
    ehm_plate1_slot: str = "Slot_5",
    ehm_plate2_slot: str = "Slot_6",
    ehm_labware: str = "myriamed_48_well.json",
    tip_rack_slot: str = "Slot_4",
    tip_labware: str = "tip_rack_1000ul.json",
    mix_cycles: int = 5,
    mix_vol_ul: float = 8.0,
    discard_z: float = 40.5,
) -> List[Dict[str, Any]]:
    """
    Builds dedicated 8-Channel Multi (1-10 µL) Parallel Drug Addition protocol for BOTH EHM Plates.
    Transfers 5 prepped drugs (Rows A..E) across Columns 1..6 simultaneously:
    - 5 tips picked per column (Slot 4 Columns 1..6, mounted on Channels A–E)
    - Kinematics centered at Y=84.52 mm (Nozzles 1..5 in Rows A..E, Nozzles 6..8 over empty sockets, 0 wall collisions)
    - High-precision drug aspiration (7.5 µL or 5.0 µL) from Slot 3 Ready Plate
    - In-place dispense & mix (5x 8.0 µL) into Plate 1 (Slot 5) and Plate 2 (Slot 6)
    - Ejects used tips into Slot 4 empty rack graveyard (Cols 7..12) at Z=40.5 mm
    Deck:
    - Slot 1: Empty clearance zone
    - Slot 2: Empty clearance zone
    - Slot 3: Prepped DMSO-Drug Diluted Ready Plate (96-well, Rows A..E: 5 drugs, Cols 1..6: 6 concs)
    - Slot 4: 1-10 µL Tip Rack (30 Fresh Tips: Rows A–E in Cols 1..6; Graveyard: Cols 7..12)
    - Slot 5: Plate 1 (Myriamed 48-well EHM, Cols 1..6)
    - Slot 6: Plate 2 (Myriamed 48-well EHM, Cols 1..6)
    """
    steps: List[Dict[str, Any]] = []

    for c in range(1, 7):
        # 1. Pick 5 tips from Slot 4 Column c (Channels A–E)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": tip_rack_slot,
            "well": f"A{c}",
            "volume": 0.0,
            "labware": tip_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-E",
            "label": f"[PICK 1-10µL TIPS] Slot_4 Col {c} (5 Tips: Rows A–E) | Col {c} Drug Addition",
        })

        # 2. Aspirate from Slot 3 Ready Plate Col c for Plate 1
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": drug_source_slot,
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": drug_source_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-E",
            "track_liquid": False,
            "label": f"[ASPIRATE 5-DRUGS] {drug_vol_ul:g} µL from Slot_3 Ready Plate Col {c} [Rows A-E]",
        })

        # 3. Dispense & mix into Plate 1 (Slot 5) Col c
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": ehm_plate1_slot,
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": ehm_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-E",
            "mix_cycles": mix_cycles,
            "mix_volume": float(mix_vol_ul),
            "track_liquid": False,
            "label": f"[DRUG+MIX] {drug_vol_ul:g} µL -> Plate 1 Col {c} [{mix_cycles}x {mix_vol_ul:g} µL Mix, Rows A-E]",
        })

        # 4. Aspirate from Slot 3 Ready Plate Col c for Plate 2
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": drug_source_slot,
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": drug_source_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-E",
            "track_liquid": False,
            "label": f"[ASPIRATE 5-DRUGS] {drug_vol_ul:g} µL from Slot_3 Ready Plate Col {c} [Rows A-E]",
        })

        # 5. Dispense & mix into Plate 2 (Slot 6) Col c
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": ehm_plate2_slot,
            "well": f"A{c}",
            "volume": float(drug_vol_ul),
            "labware": ehm_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-E",
            "mix_cycles": mix_cycles,
            "mix_volume": float(mix_vol_ul),
            "track_liquid": False,
            "label": f"[DRUG+MIX] {drug_vol_ul:g} µL -> Plate 2 Col {c} [{mix_cycles}x {mix_vol_ul:g} µL Mix, Rows A-E]",
        })

        # 6. Discard 5 tips to Slot 4 Graveyard Column c+6 (Cols 7..12) at Z=40.5mm
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": tip_rack_slot,
            "well": f"A{c + 6}",
            "volume": 0.0,
            "labware": tip_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-E",
            "discard_z_override": float(discard_z),
            "label": f"[DROP TIPS] Eject 5 Tips -> Slot_4 Col {c + 6} Graveyard (Z={discard_z}mm)",
        })

    return steps


# =============================================================================
# 1c. 1-10 µL TRIPLICATE DOSE-RESPONSE PROTOCOL (36 CONDITIONS IN TRIPLICATE)
# =============================================================================

def build_1ch_10ul_drug_addition_steps(
    drug_vol_ul: float = 7.5,
    drug_source_slot: str = "Slot_3",
    drug_source_labware: str = "generic_96_well_plate.json",
    ehm_plate1_slot: str = "Slot_5",
    ehm_plate2_slot: str = "Slot_6",
    ehm_labware: str = "myriamed_48_well.json",
    tip_rack_slot: str = "Slot_4",
    tip_labware: str = "tip_rack_1000ul.json",
    mix_cycles: int = 3,
    mix_vol_ul: float = None,
    discard_z: float = 40.5,
) -> List[Dict[str, Any]]:
    """
    Builds dedicated 1-10 µL Single-Channel Drug Addition protocol for BOTH EHM Plates.
    Directly matches the established triplicate dose-response protocol layout:
    - Drug 1 (Ready Plate Row A: A1..A6) -> Plate 1 Rows A, B, C (Triplicates for conc 1..6)
    - Drug 2 (Ready Plate Row B: B1..B6) -> Plate 1 Rows D, E, F (Triplicates for conc 1..6)
    - Drug 3 (Ready Plate Row C: C1..C6) -> Plate 1 Rows G, H (Rep 1, 2) & Plate 2 Row A (Rep 3)
    - Drug 4 (Ready Plate Row D: D1..D6) -> Plate 2 Rows B, C, D (Triplicates for conc 1..6)
    - Drug 5 (Ready Plate Row E: E1..E6) -> Plate 2 Rows E, F, G (Triplicates for conc 1..6)

    Tips:
    - 36 clean tips picked sequentially from Slot 4 Columns 1..5 (A1 to D5).
    - 36 used tips discarded sequentially into Slot 4 Graveyard Columns 7..11 (A7 to D11) at Z=40.5 mm.
    - Zero reservoirs used anywhere on deck.
    """
    if mix_vol_ul is None:
        mix_vol_ul = min(float(drug_vol_ul), 8.0)

    # 36 Drug transfer operations: (Drug_name, src_well, target_slot, dest_wells, plate_name)
    # Matching drug_addition_only_2_ehm_plates.json exactly!
    operations = []

    # Drug 1 (Row A on Slot 3): 6 concentrations -> Plate 1 Rows A, B, C
    for c in range(1, 7):
        operations.append((
            f"Drug 1 (Conc {c})",
            f"A{c}",
            ehm_plate1_slot,
            [f"A{c}", f"B{c}", f"C{c}"],
            "Plate 1"
        ))

    # Drug 2 (Row B on Slot 3): 6 concentrations -> Plate 1 Rows D, E, F
    for c in range(1, 7):
        operations.append((
            f"Drug 2 (Conc {c})",
            f"B{c}",
            ehm_plate1_slot,
            [f"D{c}", f"E{c}", f"F{c}"],
            "Plate 1"
        ))

    # Drug 3 (Row C on Slot 3): 6 concentrations split across Plate 1 (G, H) and Plate 2 (A)
    # Plate 1 portion:
    for c in range(1, 7):
        operations.append((
            f"Drug 3 (Conc {c}, Reps 1-2)",
            f"C{c}",
            ehm_plate1_slot,
            [f"G{c}", f"H{c}"],
            "Plate 1"
        ))
    # Plate 2 portion:
    for c in range(1, 7):
        operations.append((
            f"Drug 3 (Conc {c}, Rep 3)",
            f"C{c}",
            ehm_plate2_slot,
            [f"A{c}"],
            "Plate 2"
        ))

    # Drug 4 (Row D on Slot 3): 6 concentrations -> Plate 2 Rows B, C, D
    for c in range(1, 7):
        operations.append((
            f"Drug 4 (Conc {c})",
            f"D{c}",
            ehm_plate2_slot,
            [f"B{c}", f"C{c}", f"D{c}"],
            "Plate 2"
        ))

    # Drug 5 (Row E on Slot 3): 6 concentrations -> Plate 2 Rows E, F, G
    for c in range(1, 7):
        operations.append((
            f"Drug 5 (Conc {c})",
            f"E{c}",
            ehm_plate2_slot,
            [f"E{c}", f"F{c}", f"G{c}"],
            "Plate 2"
        ))

    assert len(operations) == 36, f"Expected 36 operations, got {len(operations)}"

    steps: List[Dict[str, Any]] = []

    for idx, (drug_desc, src_well, tgt_slot, dest_wells, plate_name) in enumerate(operations):
        # Fresh tip from Cols 1..5: A1..H1, A2..H2, A3..H3, A4..H4, A5..D5
        fresh_row = ROWS[idx % 8]
        fresh_col = (idx // 8) + 1
        fresh_tip_well = f"{fresh_row}{fresh_col}"

        # Graveyard socket in Cols 7..11: A7..H7, A8..H8, A9..H9, A10..H10, A11..D11
        gy_row = ROWS[idx % 8]
        gy_col = (idx // 8) + 7
        gy_well = f"{gy_row}{gy_col}"

        # 1. Pick clean tip
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": tip_rack_slot,
            "well": fresh_tip_well,
            "volume": 0.0,
            "labware": tip_labware,
            "label": f"[PICK 1-10µL TIP] Slot_4 {fresh_tip_well} | {drug_desc} ({plate_name})",
        })

        # 2. For each replicate well, aspirate from ready plate and dispense + mix
        for dw in dest_wells:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": drug_source_slot,
                "well": src_well,
                "volume": float(drug_vol_ul),
                "labware": drug_source_labware,
                "track_liquid": False,
                "label": f"[ASPIRATE DRUG] {drug_vol_ul:g} µL {drug_desc} from Slot_3 {src_well}",
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": tgt_slot,
                "well": dw,
                "volume": float(drug_vol_ul),
                "labware": ehm_labware,
                "mix_cycles": mix_cycles,
                "mix_volume": float(mix_vol_ul),
                "track_liquid": False,
                "label": f"[DISPENSE+MIX] {drug_vol_ul:g} µL -> {plate_name} {dw} ({mix_cycles}x {mix_vol_ul:g} µL Mix)",
            })

        # 3. Discard tip to graveyard
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": tip_rack_slot,
            "well": gy_well,
            "volume": 0.0,
            "labware": tip_labware,
            "discard_z_override": float(discard_z),
            "label": f"[DISCARD TIP] Discard {drug_desc} Tip -> Slot_4 Graveyard {gy_well} (Z={discard_z}mm)",
        })

    return steps


# Aliases
build_8ch_10ul_drug_addition_steps = build_8ch_10ul_parallel_drug_addition_steps
build_1ch_10ul_triplicate_drug_addition_steps = build_1ch_10ul_drug_addition_steps


# =============================================================================
# 2. 300 uL SINGLE-CHANNEL PIPETTE
# =============================================================================

def build_1ch_300ul_media_change_and_drug_steps(drug_vol_ul: float = 7.5) -> List[Dict[str, Any]]:
    """
    Builds complete 300 uL Single-Channel Media Change + Drug Addition protocol for 2 EHM Plates.
    Deck:
    - Slot 1: Media Reservoir (A1 Plate 1, A2 Plate 2)
    - Slot 2: Falcon Rack / Waste Trough (A1 Waste, A2 Plt 1 Tips, A3 Plt 2 Tips)
    - Slot 3: Stock Drug Plate (generic 96 well)
    - Slot 4: 300 uL Tip Rack
    - Slot 5: Plate 1 (Myriamed 48 well)
    - Slot 6: Plate 2 (Myriamed 48 well)
    """
    # Import logic from existing generator
    from generate_media_change_and_drug_addition_json import generate_protocol
    steps, _ = generate_protocol(drug_vol=drug_vol_ul)
    return steps


def build_1ch_300ul_dmso_dilution_steps(dmso_labware: str = "reservoir_3_well.json") -> List[Dict[str, Any]]:
    """
    Builds Single-Channel 300 uL DMSO-Drug Serial Dilution protocol for Slot 5 dilution plate.
    Transfers 100 uL DMSO from Slot 1 (3-Well Reservoir), 22 uL drug from Slot 3 (user-selected wells), and serial mixes.
    Slot 6 is left completely empty for clearance.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "protocols", "Machine 3 - 300 uL", "1_Serial_Dilution_Plate.json"),
        os.path.join(script_dir, "protocols", "1_Serial_Dilution_Plate.json"),
        os.path.join(script_dir, "protocols", "Machine 3 - 300 uL", "bakar_v2_drug_dmso_initial_loading.json"),
        os.path.join(script_dir, "protocols", "bakar_v2_drug_dmso_initial_loading.json"),
    ]
    steps = None
    for cand in candidates:
        if os.path.exists(cand):
            with open(cand, "r") as f:
                steps = json.load(f)
            break
    if steps is None:
        steps = []
    for s in steps:
        if s.get("slot") in ("Slot_1", "Slot_6") or "dmso" in s.get("label", "").lower():
            s["slot"] = "Slot_1"
            s["labware"] = dmso_labware
            s["well"] = "A1"
            if "label" in s:
                s["label"] = s["label"].replace("Slot_6", "Slot_1")
        if (
            s.get("action") == "Aspirate Media"
            and s.get("slot") == "Slot_1"
            and s.get("well") == "A1"
            and float(s.get("volume", 0.0)) >= 150.0
        ):
            s["no_air_cushion"] = True
    return steps


def build_1ch_300ul_drug_addition_steps(
    drug_vol_ul: float = 7.5,
    drug_source_slot: str = "Slot_3",
    drug_source_labware: str = "generic_96_well_plate.json",
    ehm_plate1_slot: str = "Slot_5",
    ehm_plate2_slot: str = "Slot_6",
    ehm_labware: str = "myriamed_48_well.json",
    tip_rack_slot: str = "Slot_4",
    tip_labware: str = "tip_rack_1000ul.json",
    waste_slot: str = "Slot_2",
    waste_well: str = "A3",
    mix_cycles: int = 2,
    mix_vol_ul: float = 150.0,
) -> List[Dict[str, Any]]:
    """
    Builds dedicated 300 uL Single-Channel Drug Addition protocol for BOTH EHM Plates.
    Replicate layout matches Dr. Bakar's triplicate dose-response protocol layout:
    - Drug 1 (Ready Plate Row A: A1..A6) -> Plate 1 Rows A, B, C (Triplicates for conc 1..6)
    - Drug 2 (Ready Plate Row B: B1..B6) -> Plate 1 Rows D, E, F (Triplicates for conc 1..6)
    - Drug 3 (Ready Plate Row C: C1..C6) -> Plate 1 Rows G, H (Reps 1, 2) & Plate 2 Row A (Rep 3)
    - Drug 4 (Ready Plate Row D: D1..D6) -> Plate 2 Rows B, C, D (Triplicates for conc 1..6)
    - Drug 5 (Ready Plate Row E: E1..E6) -> Plate 2 Rows E, F, G (Triplicates for conc 1..6)
    - Plate 2 Row H: Control (untouched)

    Tips:
    - 36 clean 300 µL tips picked sequentially from Slot 4 Columns 1..5 (A1 to D5).
    - Single aspiration of total volume (e.g. 3 x 7.5 = 22.5 µL or 3 x 5.0 = 15.0 µL) from Slot 3.
    - Multi-dispense into destination wells with in-well mixing.
    - Discard tip to Slot 2 waste (A3).
    """
    operations = []

    # Drug 1 (Row A on Slot 3): 6 concentrations -> Plate 1 Rows A, B, C
    for c in range(1, 7):
        operations.append((
            f"Drug 1 (Conc {c})",
            f"A{c}",
            ehm_plate1_slot,
            [f"A{c}", f"B{c}", f"C{c}"],
            "Plate 1"
        ))

    # Drug 2 (Row B on Slot 3): 6 concentrations -> Plate 1 Rows D, E, F
    for c in range(1, 7):
        operations.append((
            f"Drug 2 (Conc {c})",
            f"B{c}",
            ehm_plate1_slot,
            [f"D{c}", f"E{c}", f"F{c}"],
            "Plate 1"
        ))

    # Drug 3 (Row C on Slot 3): 6 concentrations split across Plate 1 (G, H) and Plate 2 (A)
    for c in range(1, 7):
        operations.append((
            f"Drug 3 (Conc {c}, Reps 1-2)",
            f"C{c}",
            ehm_plate1_slot,
            [f"G{c}", f"H{c}"],
            "Plate 1"
        ))
    for c in range(1, 7):
        operations.append((
            f"Drug 3 (Conc {c}, Rep 3)",
            f"C{c}",
            ehm_plate2_slot,
            [f"A{c}"],
            "Plate 2"
        ))

    # Drug 4 (Row D on Slot 3): 6 concentrations -> Plate 2 Rows B, C, D
    for c in range(1, 7):
        operations.append((
            f"Drug 4 (Conc {c})",
            f"D{c}",
            ehm_plate2_slot,
            [f"B{c}", f"C{c}", f"D{c}"],
            "Plate 2"
        ))

    # Drug 5 (Row E on Slot 3): 6 concentrations -> Plate 2 Rows E, F, G
    for c in range(1, 7):
        operations.append((
            f"Drug 5 (Conc {c})",
            f"E{c}",
            ehm_plate2_slot,
            [f"E{c}", f"F{c}", f"G{c}"],
            "Plate 2"
        ))

    assert len(operations) == 36, f"Expected 36 operations, got {len(operations)}"

    steps: List[Dict[str, Any]] = []

    for idx, (drug_desc, src_well, tgt_slot, dest_wells, plate_name) in enumerate(operations):
        fresh_row = ROWS[idx % 8]
        fresh_col = (idx // 8) + 1
        fresh_tip_well = f"{fresh_row}{fresh_col}"
        total_vol = round(float(drug_vol_ul) * len(dest_wells), 2)

        # 1. Pick clean tip
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": tip_rack_slot,
            "well": fresh_tip_well,
            "volume": 0.0,
            "labware": tip_labware,
            "label": f"[PICK 300µL TIP] Slot_4 {fresh_tip_well} | {drug_desc} ({plate_name})",
        })

        # 2. Aspirate total drug volume in one draw
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": drug_source_slot,
            "well": src_well,
            "volume": float(total_vol),
            "labware": drug_source_labware,
            "track_liquid": False,
            "label": f"[ASPIRATE DRUG] {total_vol:g} µL {drug_desc} from Slot_3 {src_well}",
        })

        # 3. Dispense into each destination well with in-well mix
        for dw in dest_wells:
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": tgt_slot,
                "well": dw,
                "volume": float(drug_vol_ul),
                "labware": ehm_labware,
                "mix_cycles": mix_cycles,
                "mix_volume": float(mix_vol_ul),
                "track_liquid": False,
                "label": f"[DISPENSE+MIX] {drug_vol_ul:g} µL -> {plate_name} {dw} ({mix_cycles}x {mix_vol_ul:g} µL Mix)",
            })

        # 4. Discard tip to Slot 2 waste
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": waste_slot,
            "well": waste_well,
            "volume": 0.0,
            "labware": "waste_trough.json",
            "label": f"[DISCARD TIP] Discard {drug_desc} Tip -> Slot_2 Waste ({waste_well})",
        })

    return steps


# =============================================================================
# 3. 20 uL SINGLE-CHANNEL PIPETTE (HIGH PRECISION DRUG & DILUTION)
# =============================================================================

def build_1ch_20ul_drug_addition_steps(drug_vol_ul: float = 7.5) -> List[Dict[str, Any]]:
    """
    Builds dedicated High-Precision 20 uL Single-Channel Drug Addition protocol for Plate 1 (Slot 5) & Plate 2 (Slot 6).
    Transfers exact drug_vol_ul (5.0 or 7.5 uL) with dedicated condition tips and 3x 15 uL in-place mixing.
    """
    steps: List[Dict[str, Any]] = []
    tip_counter = 1

    def next_tip():
        nonlocal tip_counter
        r = ROWS[(tip_counter - 1) % 8]
        c = ((tip_counter - 1) // 8) + 1
        tip_counter += 1
        return f"{r}{c}"

    # Conditions mapping:
    # Plate 1 (Slot 5):
    # Rows A-C: D11 (Slot 3 A1)
    # Rows D-F: D12 (Slot 3 B1)
    # Rows G-H: D13 (Slot 3 C1)
    # Plate 2 (Slot 6):
    # Row A:    D13 (Slot 3 C1)
    # Rows B-D: D14 (Slot 3 D1)
    # Rows E-G: D15 (Slot 3 E1)
    # Row H:    Control (Slot 3 F1)

    p1_drugs = [
        ("A1", [f"{r}{c}" for c in range(1, 7) for r in "ABC"], "D11"),
        ("B1", [f"{r}{c}" for c in range(1, 7) for r in "DEF"], "D12"),
        ("C1", [f"{r}{c}" for c in range(1, 7) for r in "GH"],  "D13"),
    ]
    p2_drugs = [
        ("C1", [f"A{c}" for c in range(1, 7)], "D13"),
        ("D1", [f"{r}{c}" for c in range(1, 7) for r in "BCD"], "D14"),
        ("E1", [f"{r}{c}" for c in range(1, 7) for r in "EFG"], "D15"),
        ("F1", [f"H{c}" for c in range(1, 7)], "Control"),
    ]

    # Plate 1
    for src_well, dest_wells, d_label in p1_drugs:
        t_id = next_tip()
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": t_id,
            "volume": 0.0,
            "labware": "tip_rack_1000ul.json",
            "label": f"[PICK 20µL TIP] Slot_4 {t_id} | Condition {d_label} (Plate 1)",
        })
        for dw in dest_wells:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_3",
                "well": src_well,
                "volume": float(drug_vol_ul),
                "labware": "generic_96_well_plate.json",
                "label": f"[ASPIRATE DRUG] {drug_vol_ul:g} µL {d_label} from Slot_3 {src_well}",
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_5",
                "well": dw,
                "volume": float(drug_vol_ul),
                "labware": "myriamed_48_well.json",
                "mix_cycles": 3,
                "mix_volume": 15.0,
                "label": f"[DISPENSE+MIX] {drug_vol_ul:g} µL {d_label} -> Plate 1 {dw} (Mix 3x 15 µL)",
            })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A2",
            "volume": 0.0,
            "labware": "reservoir_3_well.json",
            "label": f"[DROP 20µL TIP] Eject {d_label} Tip -> Slot_2 Waste",
        })

    # Plate 2
    for src_well, dest_wells, d_label in p2_drugs:
        t_id = next_tip()
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": t_id,
            "volume": 0.0,
            "labware": "tip_rack_1000ul.json",
            "label": f"[PICK 20µL TIP] Slot_4 {t_id} | Condition {d_label} (Plate 2)",
        })
        for dw in dest_wells:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_3",
                "well": src_well,
                "volume": float(drug_vol_ul),
                "labware": "generic_96_well_plate.json",
                "label": f"[ASPIRATE DRUG] {drug_vol_ul:g} µL {d_label} from Slot_3 {src_well}",
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": dw,
                "volume": float(drug_vol_ul),
                "labware": "myriamed_48_well.json",
                "mix_cycles": 3,
                "mix_volume": 15.0,
                "label": f"[DISPENSE+MIX] {drug_vol_ul:g} µL {d_label} -> Plate 2 {dw} (Mix 3x 15 µL)",
            })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A3",
            "volume": 0.0,
            "labware": "reservoir_3_well.json",
            "label": f"[DROP 20µL TIP] Eject {d_label} Tip -> Slot_2 Waste",
        })

    return steps


def build_1ch_20ul_dmso_dilution_steps(dmso_labware: str = "reservoir_7_column.json") -> List[Dict[str, Any]]:
    """
    Builds Single-Channel 20 uL High-Precision DMSO-Drug Serial Dilution protocol on Slot 5.
    Transfers 15.0 uL DMSO into dilution columns, transfers 15.0 uL drug from Slot 3, and performs 20 uL serial mixing.
    Supports either 7-column or 6-column reservoir on Slot 6.
    """
    steps: List[Dict[str, Any]] = []
    tip_counter = 1

    def next_tip():
        nonlocal tip_counter
        r = ROWS[(tip_counter - 1) % 8]
        c = ((tip_counter - 1) // 8) + 1
        tip_counter += 1
        return f"{r}{c}"

    # 1. Pre-fill DMSO into dilution wells (Cols 2..6 of Row A..E)
    t_dmso = next_tip()
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": t_dmso,
        "volume": 0.0,
        "labware": "tip_rack_1000ul.json",
        "label": f"[PICK 20µL TIP] Slot_4 {t_dmso} | DMSO Dilution Buffer",
    })
    for r in "ABCDE":
        for c in range(2, 7):
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": "A1",
                "volume": 15.0,
                "labware": dmso_labware,
                "label": f"[ASPIRATE DMSO] 15.0 µL from Slot_6 A1",
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_5",
                "well": f"{r}{c}",
                "volume": 15.0,
                "labware": "generic_96_well_plate.json",
                "label": f"[DISPENSE DMSO] 15.0 µL -> Slot_5 {r}{c}",
            })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_2",
        "well": "A1",
        "volume": 0.0,
        "labware": "waste_trough.json",
        "label": "[DROP 20µL TIP] Discard DMSO Tip -> Slot_2",
    })

    # 2. For each drug series (Rows A-E): Transfer stock drug from Slot 3 and serial dilute
    default_stock_wells = ["A1", "A2", "A3", "A4", "B1"]
    for idx, r in enumerate("ABCDE"):
        stock_w = default_stock_wells[idx]
        t_drug = next_tip()
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": t_drug,
            "volume": 0.0,
            "labware": "tip_rack_1000ul.json",
            "label": f"[PICK 20µL TIP] Slot_4 {t_drug} | Drug Series {r}",
        })
        # Aspirate stock drug from Slot 3 (user-customizable) into Col 1
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": stock_w,
            "volume": 18.0,
            "labware": "generic_96_well_plate.json",
            "label": f"[ASPIRATE STOCK] 18.0 µL from Slot_3 {stock_w}",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_5",
            "well": f"{r}1",
            "volume": 18.0,
            "labware": "generic_96_well_plate.json",
            "mix_cycles": 3,
            "mix_volume": 12.0,
            "label": f"[DISPENSE STOCK] 18.0 µL -> Slot_5 {r}1 (Mix 3x 12 µL)",
        })

        # Serial dilute Col 1 -> Col 2 -> Col 3 -> Col 4 -> Col 5 -> Col 6
        for c in range(1, 6):
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_5",
                "well": f"{r}{c}",
                "volume": 7.5,
                "labware": "generic_96_well_plate.json",
                "label": f"[SERIAL TRANSFER] 7.5 µL from {r}{c} -> {r}{c+1}",
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_5",
                "well": f"{r}{c+1}",
                "volume": 7.5,
                "labware": "generic_96_well_plate.json",
                "mix_cycles": 4,
                "mix_volume": 12.0,
                "label": f"[SERIAL MIX] 7.5 µL in {r}{c+1} (4x 12 µL Mix)",
            })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A1",
            "volume": 0.0,
            "labware": "waste_trough.json",
            "label": f"[DROP 20µL TIP] Eject Series {r} Tip -> Slot_2 Waste",
        })

    return steps


# =============================================================================
# SAVE ALL PROTOCOLS TO BOTH FOLDERS
# =============================================================================

def save_all_unified_protocols():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    out_dirs = [
        os.path.join(script_dir, "protocols"),
        os.path.join(repo_root, "protocols"),
    ]

    protocols = {
        # 1. 8-Channel Multi (8x1000 uL)
        "ehm_8ch_1000ul_media_change_and_drug_7.5uL.json": build_8ch_media_change_and_drug_steps(7.5),
        "ehm_8ch_1000ul_media_change_and_drug_5.0uL.json": build_8ch_media_change_and_drug_steps(5.0),
        "ehm_8ch_1000ul_dmso_drug_dilution.json": build_8ch_dmso_dilution_steps(),

        # 1c. 1-10 µL Triplicate Dose-Response Protocol (36 conditions in triplicate)
        "ehm_1ch_10ul_triplicate_drug_addition_7.5uL.json": build_1ch_10ul_triplicate_drug_addition_steps(7.5),
        "ehm_1ch_10ul_triplicate_drug_addition_5.0uL.json": build_1ch_10ul_triplicate_drug_addition_steps(5.0),
        "ehm_1ch_10ul_drug_addition_to_ehm_7.5uL.json": build_1ch_10ul_triplicate_drug_addition_steps(7.5),
        "ehm_1ch_10ul_drug_addition_to_ehm_5.0uL.json": build_1ch_10ul_triplicate_drug_addition_steps(5.0),

        # 2. 300 uL Single-Channel
        "ehm_1ch_300ul_drug_addition_7.5uL.json": build_1ch_300ul_drug_addition_steps(7.5),
        "ehm_1ch_300ul_drug_addition_5.0uL.json": build_1ch_300ul_drug_addition_steps(5.0),
        "ehm_1ch_300ul_media_change_and_drug_7.5uL.json": build_1ch_300ul_media_change_and_drug_steps(7.5),
        "ehm_1ch_300ul_media_change_and_drug_5.0uL.json": build_1ch_300ul_media_change_and_drug_steps(5.0),
        "ehm_1ch_300ul_dmso_drug_dilution.json": build_1ch_300ul_dmso_dilution_steps(),

        # 3. 20 uL Single-Channel
        "ehm_1ch_20ul_drug_addition_7.5uL.json": build_1ch_20ul_drug_addition_steps(7.5),
        "ehm_1ch_20ul_drug_addition_5.0uL.json": build_1ch_20ul_drug_addition_steps(5.0),
        "ehm_1ch_20ul_dmso_drug_dilution.json": build_1ch_20ul_dmso_dilution_steps(),
    }

    machine_subfolders = {
        "1000ul": "Machine 1 - 8x1000 uL",
        "10ul": "Machine 2 - 1-10 uL",
        "20ul": "Machine 2 - 1-10 uL",
        "300ul": "Machine 3 - 300 uL",
    }

    all_roots = [
        os.path.join(script_dir, "protocols"),
        os.path.join(repo_root, "protocols"),
        os.path.join(repo_root, "src", "robolab_gui", "resources", "protocols"),
    ]

    for root in all_roots:
        os.makedirs(root, exist_ok=True)
        for name, steps in protocols.items():
            # Root copy
            out_p = os.path.join(root, name)
            with open(out_p, "w") as f:
                json.dump(steps, f, indent=2)
            print(f"Saved {len(steps)} steps -> {out_p}")

            # Machine subfolder copy
            for key, subf in machine_subfolders.items():
                if key in name:
                    sub_dir = os.path.join(root, subf)
                    os.makedirs(sub_dir, exist_ok=True)
                    sub_p = os.path.join(sub_dir, name)
                    with open(sub_p, "w") as f:
                        json.dump(steps, f, indent=2)
                    print(f"Saved {len(steps)} steps -> {sub_p}")
                    break


if __name__ == "__main__":
    save_all_unified_protocols()

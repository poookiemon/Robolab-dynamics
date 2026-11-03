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
    remove_vol_ul: float = 550.0,
    fresh_vol_ul: float = 500.0,
    reservoir_labware: str = "reservoir_7_column.json",
    drug_source_slot: str = "Slot_1",
    drug_source_labware: str = "generic_96_well_plate.json",
) -> List[Dict[str, Any]]:
    """
    Builds 100% 0-contamination 8-channel protocol for Plate 5 (Slot 3) & Plate 6 (Slot 5).
    - Media removal: Rows A-H, Col 1..6 low-to-high into Slot 6 Waste (A7) at Z=59.32 (3cm above, contact-free).
    - Fresh media addition: Rows A-H, 500 uL from Slot 6 R1/R2, contact-free at Z=12.33 (1cm above rim).
    - Drug addition: Rows A-H, drug_vol_ul from Drug Plate (Slot 1) into Col 1..6 with 5x 100 uL in-place mixing.
    """
    steps: List[Dict[str, Any]] = []
    waste_well = "A7" if "reservoir_7" in reservoir_labware else "A6"

    # Plate 5 configuration:
    # Tips: Col 1 for removal, Col 2 for fresh media, Col 5 for drug addition
    # Graveyard: Col 12, Col 11, Col 10
    # -------------------------------------------------------------
    # 1. PLATE 5 (Slot 3)
    # -------------------------------------------------------------
    # Step A: Media Removal (Col 1 Tips)
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
    for c in range(1, 7):
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_3",
            "well": f"A{c}",
            "volume": float(remove_vol_ul),
            "labware": "myriamed_48_well.json",
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Plate 5 Col {c} [Rows A-H]",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": waste_well,
            "volume": float(remove_vol_ul),
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[WASTE 8-CH] Dispense {remove_vol_ul:g} µL to Slot_6 {waste_well} Waste (Plate 5 Col {c})",
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
        "discard_z_override": 42.0,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 5 Old Media Tips -> Slot_4 Col 12 Graveyard",
    })

    # Step B: Fresh Media Addition (Col 2 Tips) - Multi-Dispense: Aspirate 1000 µL, Dispense 500 µL + 500 µL Contact-Free
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
            "well": "A1",
            "volume": 1000.0,
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[ASPIRATE 8-CH] 1000 µL from Slot_6 R1 (Plate 5 Cols {c1}&{c2})",
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
        "discard_z_override": 42.0,
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
        "discard_z_override": 42.0,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 5 Drug Tips -> Slot_4 Col 10 Graveyard",
    })

    # -------------------------------------------------------------
    # 2. PLATE 6 (Slot 5)
    # -------------------------------------------------------------
    # Step A: Media Removal (Col 3 Tips)
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
            "label": f"[REMOVE 8-CH] Aspirate {remove_vol_ul:g} µL from Plate 6 Col {c} [Rows A-H]",
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_6",
            "well": waste_well,
            "volume": float(remove_vol_ul),
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[WASTE 8-CH] Dispense {remove_vol_ul:g} µL to Slot_6 {waste_well} Waste (Plate 6 Col {c})",
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
        "discard_z_override": 42.0,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 6 Old Media Tips -> Slot_4 Col 9 Graveyard",
    })

    # Step B: Fresh Media Addition (Col 4 Tips) - Multi-Dispense: Aspirate 1000 µL, Dispense 500 µL + 500 µL Contact-Free
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
            "well": "A2",
            "volume": 1000.0,
            "labware": reservoir_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "track_liquid": False,
            "label": f"[ASPIRATE 8-CH] 1000 µL from Slot_6 R2 (Plate 6 Cols {c1}&{c2})",
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
        "discard_z_override": 42.0,
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
        "discard_z_override": 42.0,
        "mounted_channels": "A-H",
        "label": "[DROP 8-CH] Eject Plate 6 Drug Tips -> Slot_4 Col 7 Graveyard",
    })

    return steps


def build_8ch_dmso_dilution_steps(dmso_labware: str = "reservoir_7_column.json") -> List[Dict[str, Any]]:
    """
    Builds 8-channel parallel serial dilution across 96-well plate (Slot 5).
    Pre-fills DMSO into Cols 2..6, transfers stock drug from Slot 3 (Cols user-selected) into Col 1,
    and performs 8-channel serial dilutions across Columns 1..6.
    Supports either 7-column or 6-column reservoir on Slot 1.
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
            "slot": "Slot_1",
            "well": "A1",
            "volume": 100.0,
            "labware": dmso_labware,
            "eight_ch_symmetric": True,
            "mounted_channels": "A-H",
            "label": f"[ASPIRATE 8-CH] 100 µL DMSO from Slot_1 A1",
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


def build_1ch_300ul_dmso_dilution_steps(dmso_labware: str = "reservoir_7_column.json") -> List[Dict[str, Any]]:
    """
    Builds Single-Channel 300 uL DMSO-Drug Serial Dilution protocol for Slot 5 dilution plate.
    Transfers 100 uL DMSO, 22 uL drug from Slot 3 (user-selected wells), and serial mixes.
    Supports either 7-column or 6-column reservoir on Slot 1.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_p = os.path.join(script_dir, "protocols", "1_Serial_Dilution_Plate.json")
    if os.path.exists(source_p):
        with open(source_p, "r") as f:
            steps = json.load(f)
    else:
        source_b = os.path.join(script_dir, "protocols", "bakar_v2_drug_dmso_initial_loading.json")
        with open(source_b, "r") as f:
            steps = json.load(f)
    for s in steps:
        if s.get("slot") == "Slot_1":
            s["labware"] = dmso_labware
            s["well"] = "A1"
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
    Supports either 7-column or 6-column reservoir on Slot 1.
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
                "slot": "Slot_1",
                "well": "A1",
                "volume": 15.0,
                "labware": dmso_labware,
                "label": f"[ASPIRATE DMSO] 15.0 µL from Slot_1 A1",
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

        # 2. 300 uL Single-Channel
        "ehm_1ch_300ul_media_change_and_drug_7.5uL.json": build_1ch_300ul_media_change_and_drug_steps(7.5),
        "ehm_1ch_300ul_media_change_and_drug_5.0uL.json": build_1ch_300ul_media_change_and_drug_steps(5.0),
        "ehm_1ch_300ul_dmso_drug_dilution.json": build_1ch_300ul_dmso_dilution_steps(),

        # 3. 20 uL Single-Channel
        "ehm_1ch_20ul_drug_addition_7.5uL.json": build_1ch_20ul_drug_addition_steps(7.5),
        "ehm_1ch_20ul_drug_addition_5.0uL.json": build_1ch_20ul_drug_addition_steps(5.0),
        "ehm_1ch_20ul_dmso_drug_dilution.json": build_1ch_20ul_dmso_dilution_steps(),
    }

    for d in out_dirs:
        os.makedirs(d, exist_ok=True)
        for name, steps in protocols.items():
            out_p = os.path.join(d, name)
            with open(out_p, "w") as f:
                json.dump(steps, f, indent=2)
            print(f"Saved {len(steps)} steps -> {out_p}")


if __name__ == "__main__":
    save_all_unified_protocols()

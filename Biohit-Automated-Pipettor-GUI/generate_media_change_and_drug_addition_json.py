import json
import os

# Section definitions for Plate 1 and Plate 2
# Each section performs:
# 1. Media Removal: 3 x 190 uL -> Slot 2 Well A1 (Falcon A Media Waste)
# 2. Fresh Media Addition: 3 x 165 uL from Slot 1 (A1 for Plate 1, A2 for Plate 2)
# 3. Drug Addition: 1 single tip for the entire drug compound across all concentrations!
#    Tip Discard: Falcon B (Slot 2 Well A2) for Plate 1, Falcon C (Slot 2 Well A3) for Plate 2

p1_sections = [
    ("S1", 
     [f"{r}{c}" for c in range(1, 7) for r in "ABC"], 
     [f"{r}{c}" for c in range(1, 7) for r in "ABC"], 
     [("A1", ["A1","B1","C1"]), ("A2", ["A2","B2","C2"]), ("A3", ["A3","B3","C3"]), ("A4", ["A4","B4","C4"]), ("A5", ["A5","B5","C5"]), ("A6", ["A6","B6","C6"])]),
    ("S2", 
     [f"{r}{c}" for c in range(1, 7) for r in "DEF"], 
     [f"{r}{c}" for c in range(1, 7) for r in "DEF"], 
     [("B1", ["D1","E1","F1"]), ("B2", ["D2","E2","F2"]), ("B3", ["D3","E3","F3"]), ("B4", ["D4","E4","F4"]), ("B5", ["D5","E5","F5"]), ("B6", ["D6","E6","F6"])]),
    ("S3_P1", 
     [f"{r}{c}" for c in range(1, 7) for r in "GH"], 
     [f"{r}{c}" for c in range(1, 7) for r in "GH"], 
     [("C1", ["G1","H1"]), ("C2", ["G2","H2"]), ("C3", ["G3","H3"]), ("C4", ["G4","H4"]), ("C5", ["G5","H5"]), ("C6", ["G6","H6"])])
]

p2_sections = [
    ("S3_P2", 
     [f"A{c}" for c in range(1, 7)], 
     [f"A{c}" for c in range(1, 7)], 
     [("C1", ["A1"]), ("C2", ["A2"]), ("C3", ["A3"]), ("C4", ["A4"]), ("C5", ["A5"]), ("C6", ["A6"])]),
    ("S4", 
     [f"{r}{c}" for c in range(1, 7) for r in "BCD"], 
     [f"{r}{c}" for c in range(1, 7) for r in "BCD"], 
     [("D1", ["B1","C1","D1"]), ("D2", ["B2","C2","D2"]), ("D3", ["B3","C3","D3"]), ("D4", ["B4","C4","D4"]), ("D5", ["B5","C5","D5"]), ("D6", ["B6","C6","D6"])]),
    ("S5", 
     [f"{r}{c}" for c in range(1, 7) for r in "EFG"], 
     [f"{r}{c}" for c in range(1, 7) for r in "EFG"], 
     [("E1", ["E1","F1","G1"]), ("E2", ["E2","F2","G2"]), ("E3", ["E3","F3","G3"]), ("E4", ["E4","F4","G4"]), ("E5", ["E5","F5","G5"]), ("E6", ["E6","F6","G6"])])
]

def generate_protocol(drug_vol: float = 7.5):
    tip_cols = [f"{r}{c}" for c in range(1, 13) for r in "ABCDEFGH"]
    tip_idx = 0
    def get_tip():
        nonlocal tip_idx
        t = tip_cols[tip_idx % len(tip_cols)]
        tip_idx += 1
        return t

    steps = []

    # -------------------------------------------------------------
    # PHASE 1: PLATE 1 (Slot 5) - All tips to Falcon B (Slot 2 Well A2)
    # -------------------------------------------------------------
    for sec_name, rem_wells, fresh_wells, drug_steps in p1_sections:
        # 1. Media Removal (1 fresh tip per section)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        for w in rem_wells:
            for cv in [190.0, 190.0, 190.0]:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_5",
                    "well": w,
                    "volume": cv,
                    "labware": "myriamed_48_well.json"
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_2",
                    "well": "A1",  # Falcon A: Media Waste
                    "volume": cv,
                    "labware": "reservoir_3_well.json"
                })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A2",  # Falcon B: Plate 1 Tips
            "labware": "reservoir_3_well.json"
        })

        # 2. Fresh Media Addition (1 clean tip per section)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        for w in fresh_wells:
            for cv in [165.0, 165.0, 165.0]:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_1",
                    "well": "A1",
                    "volume": cv,
                    "labware": "reservoir_3_well.json"
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_5",
                    "well": w,
                    "volume": cv,
                    "labware": "myriamed_48_well.json"
                })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A2",  # Falcon B: Plate 1 Tips
            "labware": "reservoir_3_well.json"
        })

        # 3. Drug Addition (1 single tip for the entire drug compound!)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        for src, dest_wells in drug_steps:
            for dw in dest_wells:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_3",
                    "well": src,
                    "volume": drug_vol,
                    "labware": "generic_96_well_plate.json"
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_5",
                    "well": dw,
                    "volume": drug_vol,
                    "mix_cycles": 2,
                    "mix_volume": 100.0,
                    "labware": "myriamed_48_well.json"
                })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A2",  # Falcon B: Plate 1 Tips
            "labware": "reservoir_3_well.json"
        })

    # -------------------------------------------------------------
    # PHASE 2: PLATE 2 (Slot 6) - All tips to Falcon C (Slot 2 Well A3)
    # -------------------------------------------------------------
    for sec_name, rem_wells, fresh_wells, drug_steps in p2_sections:
        # 1. Media Removal (1 fresh tip per section)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        for w in rem_wells:
            for cv in [190.0, 190.0, 190.0]:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": w,
                    "volume": cv,
                    "labware": "myriamed_48_well.json"
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_2",
                    "well": "A1",  # Falcon A: Media Waste
                    "volume": cv,
                    "labware": "reservoir_3_well.json"
                })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A3",  # Falcon C: Plate 2 Tips
            "labware": "reservoir_3_well.json"
        })

        # 2. Fresh Media Addition (1 clean tip per section)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        for w in fresh_wells:
            for cv in [165.0, 165.0, 165.0]:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_1",
                    "well": "A2",
                    "volume": cv,
                    "labware": "reservoir_3_well.json"
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": w,
                    "volume": cv,
                    "labware": "myriamed_48_well.json"
                })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A3",  # Falcon C: Plate 2 Tips
            "labware": "reservoir_3_well.json"
        })

        # 3. Drug Addition (1 single tip for the entire drug compound!)
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        for src, dest_wells in drug_steps:
            for dw in dest_wells:
                steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_3",
                    "well": src,
                    "volume": drug_vol,
                    "labware": "generic_96_well_plate.json"
                })
                steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": dw,
                    "volume": drug_vol,
                    "mix_cycles": 2,
                    "mix_volume": 100.0,
                    "labware": "myriamed_48_well.json"
                })
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A3",  # Falcon C: Plate 2 Tips
            "labware": "reservoir_3_well.json"
        })

    # -------------------------------------------------------------
    # PHASE 3: PLATE 2 ROW H MEDIA CHANGE ONLY (Wells H1..H6)
    # Tips from Slot 4 (C3, D3) -> Discard to Falcon C (Slot 2 Well A3)
    # -------------------------------------------------------------
    p2_row_h = [f"H{c}" for c in range(1, 7)]
    # 1. Media Removal (1 clean tip: C3)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": get_tip(),
        "labware": "tip_rack_1000ul.json"
    })
    for w in p2_row_h:
        for cv in [190.0, 190.0, 190.0]:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": w,
                "volume": cv,
                "labware": "myriamed_48_well.json"
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_2",
                "well": "A1",  # Falcon A: Media Waste
                "volume": cv,
                "labware": "reservoir_3_well.json"
            })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_2",
        "well": "A3",  # Falcon C: Plate 2 Tips
        "labware": "reservoir_3_well.json"
    })

    # 2. Fresh Media Addition (1 clean tip: D3)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": get_tip(),
        "labware": "tip_rack_1000ul.json"
    })
    for w in p2_row_h:
        for cv in [165.0, 165.0, 165.0]:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_1",
                "well": "A2",  # Reservoir Well A2: Plate 2 Media
                "volume": cv,
                "labware": "reservoir_3_well.json"
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": w,
                "volume": cv,
                "labware": "myriamed_48_well.json"
            })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_2",
        "well": "A3",  # Falcon C: Plate 2 Tips
        "labware": "reservoir_3_well.json"
    })

    return steps, tip_idx


def generate_plate2_row_h_only_protocol():
    """Generates standalone protocol for JUST the last row (H1..H6) of Plate 2,
    taking tips C3 and D3 (where the full protocol ends)."""
    steps = []
    p2_row_h = [f"H{c}" for c in range(1, 7)]
    # 1. Media Removal (Tip C3)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "C3",
        "labware": "tip_rack_1000ul.json"
    })
    for w in p2_row_h:
        for cv in [190.0, 190.0, 190.0]:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": w,
                "volume": cv,
                "labware": "myriamed_48_well.json"
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_2",
                "well": "A1",
                "volume": cv,
                "labware": "reservoir_3_well.json"
            })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_2",
        "well": "A3",
        "labware": "reservoir_3_well.json"
    })

    # 2. Fresh Media Addition (Tip D3)
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_4",
        "well": "D3",
        "labware": "tip_rack_1000ul.json"
    })
    for w in p2_row_h:
        for cv in [165.0, 165.0, 165.0]:
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_1",
                "well": "A2",
                "volume": cv,
                "labware": "reservoir_3_well.json"
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": w,
                "volume": cv,
                "labware": "myriamed_48_well.json"
            })
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_2",
        "well": "A3",
        "labware": "reservoir_3_well.json"
    })
    return steps


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    for vol in [7.5, 5.0]:
        steps, total_tips = generate_protocol(drug_vol=vol)
        print(f"Generated {len(steps)} steps for {vol} uL protocol using {total_tips} tips.")

        # Paths for specific volume
        vol_suffix = f"_{vol:.1f}uL" if vol == 5.0 else "_7.5uL"
        paths_to_write = [
            os.path.join(repo_root, "protocols", f"media_change_and_drug_addition_2_plates{vol_suffix}.json"),
            os.path.join(script_dir, "protocols", f"media_change_and_drug_addition_2_plates{vol_suffix}.json"),
            os.path.join(repo_root, "protocols", f"2_EHM_Media_Change_and_Drug_Addition{vol_suffix}.json"),
            os.path.join(script_dir, "protocols", f"2_EHM_Media_Change_and_Drug_Addition{vol_suffix}.json"),
        ]
        
        # If default 7.5uL, also write standard base names
        if vol == 7.5:
            paths_to_write.extend([
                os.path.join(repo_root, "protocols", "media_change_and_drug_addition_2_plates.json"),
                os.path.join(script_dir, "protocols", "media_change_and_drug_addition_2_plates.json"),
                os.path.join(repo_root, "protocols", "2_EHM_Media_Change_and_Drug_Addition.json"),
                os.path.join(script_dir, "protocols", "2_EHM_Media_Change_and_Drug_Addition.json")
            ])

        for p in paths_to_write:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as out:
                json.dump(steps, out, indent=4)
            print(f"Saved {p}")

        # Also write resume from G1 (sliced from Step 516)
        resume_steps = steps[516:]
        resume_paths = [
            os.path.join(repo_root, "protocols", f"media_change_and_drug_addition_2_plates_resume_G1{vol_suffix}.json"),
            os.path.join(script_dir, "protocols", f"media_change_and_drug_addition_2_plates_resume_G1{vol_suffix}.json"),
            os.path.join(repo_root, "protocols", f"2_EHM_Media_Change_and_Drug_Addition_resume_G1{vol_suffix}.json"),
            os.path.join(script_dir, "protocols", f"2_EHM_Media_Change_and_Drug_Addition_resume_G1{vol_suffix}.json"),
        ]
        if vol == 7.5:
            resume_paths.extend([
                os.path.join(repo_root, "protocols", "media_change_and_drug_addition_2_plates_resume_G1.json"),
                os.path.join(script_dir, "protocols", "media_change_and_drug_addition_2_plates_resume_G1.json"),
                os.path.join(repo_root, "protocols", "2_EHM_Media_Change_and_Drug_Addition_resume_G1.json"),
                os.path.join(script_dir, "protocols", "2_EHM_Media_Change_and_Drug_Addition_resume_G1.json")
            ])
        for rp in resume_paths:
            os.makedirs(os.path.dirname(rp), exist_ok=True)
            with open(rp, "w") as out:
                json.dump(resume_steps, out, indent=4)
            print(f"Saved resume protocol {rp} ({len(resume_steps)} steps)")

    # Generate standalone Plate 2 Row H Media Change Only protocol (76 steps, tips C3 and D3)
    row_h_steps = generate_plate2_row_h_only_protocol()
    row_h_paths = [
        os.path.join(repo_root, "protocols", "media_change_plate2_rowH_only.json"),
        os.path.join(script_dir, "protocols", "media_change_plate2_rowH_only.json"),
        os.path.join(repo_root, "protocols", "plate2_rowH_media_change_only.json"),
        os.path.join(script_dir, "protocols", "plate2_rowH_media_change_only.json")
    ]
    for hp in row_h_paths:
        os.makedirs(os.path.dirname(hp), exist_ok=True)
        with open(hp, "w") as out:
            json.dump(row_h_steps, out, indent=4)
        print(f"Saved Plate 2 Row H standalone protocol {hp} ({len(row_h_steps)} steps)")

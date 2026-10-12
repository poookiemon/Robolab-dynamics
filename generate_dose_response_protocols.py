import json
import os

def create_initial_loading():
    steps = []
    tip_counter = 1
    
    def next_tip():
        nonlocal tip_counter
        # 96-tip layout: A1..A12, B1..B12, etc.
        row_char = chr(ord('A') + ((tip_counter - 1) // 12))
        col_num = ((tip_counter - 1) % 12) + 1
        tip_counter += 1
        return f"{row_char}{col_num}"

    # =========================================================================
    # PHASE 1: MEDIUM LOADING (745 uL total per well, split as 500 uL + 245 uL)
    # =========================================================================
    # 1 clean tip for bulk fresh medium distribution across all 18 target wells
    med_tip = next_tip()
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_3",
        "well": med_tip,
        "volume": 0.0,
        "extra_z": 0.0
    })

    # All 18 target wells across Rows A, B, C (replicates 1, 2, 3) and Cols 1-6
    target_wells = [f"{r}{c}" for r in ["A", "B", "C"] for c in range(1, 7)]
    for well in target_wells:
        # Stroke 1: 500 uL Medium (max pipette capacity)
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_1",
            "well": "A1",
            "volume": 500.0,
            "extra_z": 0.0
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_4",
            "well": well,
            "volume": 500.0,
            "extra_z": 0.0
        })
        # Stroke 2: 245 uL Medium (remaining medium volume for 745 uL total)
        # Note: for Column 1 (0 uM Control), 250 uL can be used if no 5 uL aliquot is added,
        # but 245 uL + 5 uL Vehicle ensures identical 750.0 uL final well volume.
        vol2 = 250.0 if well.endswith("1") else 245.0
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_1",
            "well": "A1",
            "volume": vol2,
            "extra_z": 0.0
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_4",
            "well": well,
            "volume": vol2,
            "extra_z": 0.0
        })

    # Discard medium tip into Waste (Slot 6)
    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_6",
        "well": "A1",
        "volume": 0.0,
        "extra_z": 0.0
    })

    # =========================================================================
    # PHASE 2: 5 uL DRUG ADDITION (Columns 1 to 6 from Slot 5 Reservoir A1..A6)
    # =========================================================================
    # Reagent Map on Slot 5:
    # Col 1: Vehicle (0 uM)
    # Col 2: 15 uM stock (Target 0.1 uM in 750 uL)
    # Col 3: 45 uM stock (Target 0.3 uM in 750 uL)
    # Col 4: 150 uM stock (Target 1.0 uM in 750 uL)
    # Col 5: 450 uM stock (Target 3.0 uM in 750 uL)
    # Col 6: 1.5 mM stock (Target 10.0 uM in 750 uL)
    for col in range(1, 7):
        drug_res_well = f"A{col}"
        # Clean tip for this specific drug concentration
        drug_tip = next_tip()
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_3",
            "well": drug_tip,
            "volume": 0.0,
            "extra_z": 0.0
        })

        for row in ["A", "B", "C"]:
            well = f"{row}{col}"
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_5",
                "well": drug_res_well,
                "volume": 5.0,
                "extra_z": 0.0
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_4",
                "well": well,
                "volume": 5.0,
                "extra_z": 0.0
            })

        # Discard drug tip into Waste (Slot 6)
        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_6",
            "well": "A1",
            "volume": 0.0,
            "extra_z": 0.0
        })

    # Return head to Home position
    steps.append({
        "action": "Dispense Media",
        "mode": "manual",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "volume": 0.0
    })

    return steps


def create_media_change():
    steps = []
    tip_counter = 8  # Continue after initial loading tips (A8)

    def next_tip():
        nonlocal tip_counter
        row_char = chr(ord('A') + ((tip_counter - 1) // 12))
        col_num = ((tip_counter - 1) % 12) + 1
        tip_counter += 1
        return f"{row_char}{col_num}"

    # =========================================================================
    # PHASE 1: REMOVE 500 uL FROM EACH WELL TO WASTE (Leave 250 uL in well)
    # =========================================================================
    # Group by concentration column to prevent cross-contamination across doses
    for col in range(1, 7):
        waste_tip = next_tip()
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_3",
            "well": waste_tip,
            "volume": 0.0,
            "extra_z": 0.0
        })

        for row in ["A", "B", "C"]:
            well = f"{row}{col}"
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_4",
                "well": well,
                "volume": 500.0,
                "extra_z": 0.0
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_6",
                "well": "A1",
                "volume": 500.0,
                "extra_z": 0.0
            })

        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_6",
            "well": "A1",
            "volume": 0.0,
            "extra_z": 0.0
        })

    # =========================================================================
    # PHASE 2: DISPENSE 495 uL FRESH MEDIUM TO EACH WELL (Single stroke <= 500 uL)
    # =========================================================================
    med_tip = next_tip()
    steps.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_3",
        "well": med_tip,
        "volume": 0.0,
        "extra_z": 0.0
    })

    target_wells = [f"{r}{c}" for r in ["A", "B", "C"] for c in range(1, 7)]
    for well in target_wells:
        # For Column 1 (0 uM Control), 500 uL can be used if no 5 uL vehicle is added
        vol_med = 500.0 if well.endswith("1") else 495.0
        steps.append({
            "action": "Aspirate Media",
            "mode": "auto",
            "slot": "Slot_1",
            "well": "A1",
            "volume": vol_med,
            "extra_z": 0.0
        })
        steps.append({
            "action": "Dispense Media",
            "mode": "auto",
            "slot": "Slot_4",
            "well": well,
            "volume": vol_med,
            "extra_z": 0.0
        })

    steps.append({
        "action": "Discard Tip",
        "mode": "auto",
        "slot": "Slot_6",
        "well": "A1",
        "volume": 0.0,
        "extra_z": 0.0
    })

    # =========================================================================
    # PHASE 3: 5 uL DRUG ADDITION (Subsequent Change Stock Solutions: A1..A6)
    # =========================================================================
    # Reagent Map on Slot 5 for Subsequent Change:
    # Col 1: Vehicle (0 uM)
    # Col 2: 10 uM stock (Replenishes 0.050 nmol -> Target 0.1 uM in 750 uL)
    # Col 3: 30 uM stock (Replenishes 0.150 nmol -> Target 0.3 uM in 750 uL)
    # Col 4: 100 uM stock (Replenishes 0.500 nmol -> Target 1.0 uM in 750 uL)
    # Col 5: 300 uM stock (Replenishes 1.500 nmol -> Target 3.0 uM in 750 uL)
    # Col 6: 1.0 mM stock (Replenishes 5.000 nmol -> Target 10.0 uM in 750 uL)
    for col in range(1, 7):
        drug_res_well = f"A{col}"
        drug_tip = next_tip()
        steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_3",
            "well": drug_tip,
            "volume": 0.0,
            "extra_z": 0.0
        })

        for row in ["A", "B", "C"]:
            well = f"{row}{col}"
            steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_5",
                "well": drug_res_well,
                "volume": 5.0,
                "extra_z": 0.0
            })
            steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": "Slot_4",
                "well": well,
                "volume": 5.0,
                "extra_z": 0.0
            })

        steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_6",
            "well": "A1",
            "volume": 0.0,
            "extra_z": 0.0
        })

    # Return head to Home position
    steps.append({
        "action": "Dispense Media",
        "mode": "manual",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "volume": 0.0
    })

    return steps

if __name__ == "__main__":
    p_initial = create_initial_loading()
    p_change = create_media_change()

    os.makedirs("protocols", exist_ok=True)
    os.makedirs("Biohit-Automated-Pipettor-GUI/protocols", exist_ok=True)

    with open("protocols/dose_response_initial_loading.json", "w") as f:
        json.dump(p_initial, f, indent=4)
    with open("Biohit-Automated-Pipettor-GUI/protocols/dose_response_initial_loading.json", "w") as f:
        json.dump(p_initial, f, indent=4)

    with open("protocols/dose_response_media_change.json", "w") as f:
        json.dump(p_change, f, indent=4)
    with open("Biohit-Automated-Pipettor-GUI/protocols/dose_response_media_change.json", "w") as f:
        json.dump(p_change, f, indent=4)

    print(f"Generated Initial Loading: {len(p_initial)} steps")
    print(f"Generated Media Change: {len(p_change)} steps")

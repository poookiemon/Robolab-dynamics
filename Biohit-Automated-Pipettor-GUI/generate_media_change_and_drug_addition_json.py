import json
import re
import os

py_source = "Bakar/26.10 Initianl Media with drug .py"
if not os.path.exists(py_source):
    py_source = "/Users/shri/Downloads/26.10 Initianl Media with drug .py"

with open(py_source, "r") as f:
    orig_code = f.read()

# Tip tracking: columns 1..12, rows A..H (A1..H1, A2..H2, ...)
tip_cols = [f"{r}{c}" for c in range(1, 13) for r in "ABCDEFGH"]
tip_idx = 0

def get_next_tip():
    global tip_idx
    t = tip_cols[tip_idx % len(tip_cols)]
    tip_idx += 1
    return t

biohit_steps = []

step_blocks = re.findall(r"(# Step \d+: [^\n]+)\n(.*?)(?=\n\s*# Step|\nCUSTOM_LABWARE|\Z)", orig_code, re.DOTALL)
print(f"Found {len(step_blocks)} step blocks.")

for header, body in step_blocks:
    step_num = int(re.search(r"# Step (\d+):", header).group(1))
    step_title = header.split(":", 1)[1].strip()
    
    # 1. Media Removal Step
    if "Removing Media" in step_title:
        p1_wells = re.findall(r"well_plate_1\[\"([^\"]+)\"\]", body)
        p2_wells = re.findall(r"well_plate_2\[\"([^\"]+)\"\]", body)
        
        # Pick fresh tip for removal
        biohit_steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_next_tip(),
            "labware": "tip_rack_1000ul.json"
        })
            
        all_removal_wells = [("Slot_5", w) for w in p1_wells] + [("Slot_6", w) for w in p2_wells]
        for slot, well in all_removal_wells:
            # 500 uL removal split into 200 + 200 + 100
            for chunk_vol in [200.0, 200.0, 100.0]:
                biohit_steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": slot,
                    "well": well,
                    "volume": chunk_vol,
                    "labware": "myriamed_48_well.json"
                })
                biohit_steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_2",
                    "well": "A1",
                    "volume": chunk_vol,
                    "labware": "reservoir_3_well.json"
                })
                
        # Drop tip into Slot 2 A1
        biohit_steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A1",
            "labware": "reservoir_3_well.json"
        })

    # 2. Adding Media Step
    elif "Adding Media" in step_title:
        p1_wells = re.findall(r"well_plate_1\[\"([^\"]+)\"\]", body)
        p2_wells = re.findall(r"well_plate_2\[\"([^\"]+)\"\]", body)
        
        # Pick fresh tip for fresh media
        biohit_steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_next_tip(),
            "labware": "tip_rack_1000ul.json"
        })
            
        # Target wells for Plate 1 (Slot 5) receive fresh media from Slot 1 Well A1
        for w in p1_wells:
            for chunk_vol in [200.0, 200.0, 95.0]:
                biohit_steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_1",
                    "well": "A1",
                    "volume": chunk_vol,
                    "labware": "reservoir_3_well.json"
                })
                biohit_steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_5",
                    "well": w,
                    "volume": chunk_vol,
                    "labware": "myriamed_48_well.json"
                })
                
        # Target wells for Plate 2 (Slot 6) receive fresh media from Slot 1 Well A2
        for w in p2_wells:
            for chunk_vol in [200.0, 200.0, 95.0]:
                biohit_steps.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_1",
                    "well": "A2",
                    "volume": chunk_vol,
                    "labware": "reservoir_3_well.json"
                })
                biohit_steps.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": w,
                    "volume": chunk_vol,
                    "labware": "myriamed_48_well.json"
                })
                
        # Discard tip into Slot 2 A1
        biohit_steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A1",
            "labware": "reservoir_3_well.json"
        })

    # 3. Drug Addition Step
    elif "Adding DMSO-DRUG" in step_title:
        src_wells = re.findall(r"well_plate_3\[\"([^\"]+)\"\]", body)
        src = src_wells[0] if src_wells else "A1"
        
        p1_dests = re.findall(r"well_plate_1\[\"([^\"]+)\"\]", body)
        p2_dests = re.findall(r"well_plate_2\[\"([^\"]+)\"\]", body)
        all_dests = [("Slot_5", w) for w in p1_dests] + [("Slot_6", w) for w in p2_dests]
        
        vol_match = re.search(r"volume=([0-9.]+)", body)
        drug_vol = float(vol_match.group(1)) if vol_match else 7.5
        
        # Pick fresh tip for each drug concentration step
        biohit_steps.append({
            "action": "Pick Up Tip",
            "mode": "auto",
            "slot": "Slot_4",
            "well": get_next_tip(),
            "labware": "tip_rack_1000ul.json"
        })
        
        # Discrete Aspirate (drug_vol) -> Dispense (drug_vol) -> Mix (2x 100 uL) per destination well
        # Eliminates multi-dispense blowout dumping bug completely!
        for slot, well in all_dests:
            biohit_steps.append({
                "action": "Aspirate Media",
                "mode": "auto",
                "slot": "Slot_3",
                "well": src,
                "volume": drug_vol,
                "labware": "generic_96_well_plate.json"
            })
            biohit_steps.append({
                "action": "Dispense Media",
                "mode": "auto",
                "slot": slot,
                "well": well,
                "volume": drug_vol,
                "mix_cycles": 2,
                "mix_volume": 100.0,
                "labware": "myriamed_48_well.json"
            })
            
        # Discard tip into Slot 2 Well A1
        biohit_steps.append({
            "action": "Discard Tip",
            "mode": "auto",
            "slot": "Slot_2",
            "well": "A1",
            "labware": "reservoir_3_well.json"
        })

print(f"Generated {len(biohit_steps)} total Biohit protocol steps.")
print(f"Total tips used: {tip_idx}")

actions = [s["action"] for s in biohit_steps]
print("Action counts:", {a: actions.count(a) for a in set(actions)})

# Save to destination paths
out_paths = [
    "protocols/media_change_and_drug_addition_2_plates.json",
    "Biohit-Automated-Pipettor-GUI/protocols/media_change_and_drug_addition_2_plates.json",
    "protocols/2_EHM_Media_Change_and_Drug_Addition.json",
    "Biohit-Automated-Pipettor-GUI/protocols/2_EHM_Media_Change_and_Drug_Addition.json"
]

for p in out_paths:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as out:
        json.dump(biohit_steps, out, indent=4)
    print(f"Saved {p}")

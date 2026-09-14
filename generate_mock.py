import json
import os

protocol = []

# SIPA Test on 48-well plate (Slot_4). Rows A-B, Cols 1-6.
rows = ['A', 'B'] 
volumes = 50.0 

tip_idx = 1
for row in rows:
    protocol.append({
        "action": "Pick Tip",
        "mode": "auto",
        "slot": "Slot_2",
        "well": f"A{tip_idx}",
        "volume": 0.0,
        "extra_z": 0.0
    })
    for col in range(1, 7):
        protocol.append({"action": "Aspirate Media", "mode": "auto", "slot": "Slot_3", "well": f"{row}{col}", "volume": volumes})
        protocol.append({"action": "Dispense Media", "mode": "auto", "slot": "Slot_4", "well": f"{row}{col}", "volume": volumes})
    protocol.append({"action": "Drop Tip", "mode": "auto", "slot": "Slot_1", "well": "A1"})
    tip_idx += 1

# UNIFIED WORKFLOW: ALL EXTERNAL SUBSYSTEMS ARE NOW PROTOCOL STEPS
protocol.append({"action": "System: Incubate (Wait)", "mode": "auto", "volume": 300.0})
protocol.append({"action": "System: FOC48 Measurement", "mode": "auto", "well": "A1"})
protocol.append({"action": "System: Data Analysis", "mode": "auto", "folder": "C:/Data", "type": "Hill Equation"})
protocol.append({"action": "System: Database Upload", "mode": "auto", "config": "db.json"})

path = "/Users/shri/.gemini/antigravity/scratch/robolab-merge/Robolab-dynamics/protocols/acute_sipa_mock.json"
with open(path, "w") as f:
    json.dump(protocol, f, indent=4)
print(f"Generated {path} successfully!")

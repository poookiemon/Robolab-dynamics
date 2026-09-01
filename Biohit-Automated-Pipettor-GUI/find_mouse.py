import json


def get_volume_chunks(total_volume, max_capacity=200.0):
    """
    Splits a total volume into chunks that fit within the tip's maximum capacity.
    """
    chunks = []
    remaining = total_volume
    while remaining > 0:
        chunk = min(remaining, max_capacity)
        chunks.append(chunk)
        remaining -= chunk
    return chunks


def generate_tip_rack_wells():
    """
    Generates a list of 96 wells for tip tracking (A1, A2 ... H12).
    """
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    cols = range(1, 13)
    return [f"{row}{col}" for row in rows for col in cols]


# Extracted protocol parameters from CSV: (Volume µL, Source Boat Well)
protocol_steps = [
    (500.0, "A1"),  # Step 1: Ca-free
    (45.0, "A2"),  # Step 2: alpha mem
    (50.0, "A2"),  # Step 3: alpha mem
    (58.0, "A2"),  # Step 4: alpha mem
    (58.0, "A2"),  # Step 5: alpha mem
    (60.0, "A2"),  # Step 6: alpha mem
    (70.0, "A2"),  # Step 7: alpha mem
    (75.0, "A2"),  # Step 8: alpha mem
    (85.0, "A2"),  # Step 9: alpha mem
    (42.0, "A3"),  # Step 10: 10mM
    (44.0, "A3"),  # Step 11: 10mM
    (47.0, "A3"),  # Step 12: 10mM
    (50.0, "A3"),  # Step 13: 10mM
    (107.0, "A3"),  # Step 14: 10mM
    (450.0, "A1")  # Step 15: Ca-free
]

# Plate dimensions for EHM plates (Includes Row H for controls)
plate_rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
plate_cols = range(1, 7)  # Columns 1 through 6

sequence = []
tip_wells = generate_tip_rack_wells()
tip_index = 0  # Tracks which tip is currently available in Slot 3

# Outer Loop: Iterate through each of the 15 protocol steps
for step_index, (vol, boat) in enumerate(protocol_steps, start=1):

    volume_chunks = get_volume_chunks(vol)

    # ---------------------------------------------------------
    # PHASE 1: EVACUATION (Target wells to Waste)
    # ---------------------------------------------------------

    # Pick up a fresh tip for the evacuation phase
    sequence.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_3",
        "well": tip_wells[tip_index],
        "volume": 0.0,
        "extra_z": 0.0
    })

    # Empty all 48 wells (A1 through H6)
    for row in plate_rows:
        for col in plate_cols:
            target_well = f"{row}{col}"

            for chunk_vol in volume_chunks:
                sequence.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_4",
                    "well": target_well,
                    "volume": chunk_vol,
                    "extra_z": 0.0
                })
                sequence.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_6",
                    "well": "A1",
                    "volume": chunk_vol,
                    "extra_z": 0.0
                })

    # Discard the evacuation tip into the trash chute (Slot 1, A1)
    sequence.append({
        "action": "Drop Tip",
        "mode": "auto",
        "slot": "Slot_1",
        "well": "A1",
        "volume": 0.0,
        "extra_z": 0.0
    })
    tip_index += 1  # Advance tip tracker

    # ---------------------------------------------------------
    # PHASE 2: REPLENISHMENT (Source Boat to Target wells)
    # ---------------------------------------------------------

    # Pick up a fresh tip for the replenishment phase
    sequence.append({
        "action": "Pick Up Tip",
        "mode": "auto",
        "slot": "Slot_3",
        "well": tip_wells[tip_index],
        "volume": 0.0,
        "extra_z": 0.0
    })

    # Fill all 48 wells from the active boat
    for row in plate_rows:
        for col in plate_cols:
            target_well = f"{row}{col}"

            for chunk_vol in volume_chunks:
                sequence.append({
                    "action": "Aspirate Media",
                    "mode": "auto",
                    "slot": "Slot_5",
                    "well": boat,
                    "volume": chunk_vol,
                    "extra_z": 0.0
                })
                sequence.append({
                    "action": "Dispense Media",
                    "mode": "auto",
                    "slot": "Slot_4",
                    "well": target_well,
                    "volume": chunk_vol,
                    "extra_z": 0.0
                })

    # Discard the replenishment tip into the trash chute
    sequence.append({
        "action": "Drop Tip",
        "mode": "auto",
        "slot": "Slot_1",
        "well": "A1",
        "volume": 0.0,
        "extra_z": 0.0
    })
    tip_index += 1  # Advance tip tracker

    # ---------------------------------------------------------
    # PHASE 3: SYSTEM MACROS (Wait -> Read)
    # ---------------------------------------------------------

    # Pre-Read Incubation set to 5 minutes (300.0 seconds)
    sequence.append({
        "action": "System: Incubate (Wait)",
        "mode": "auto",
        "volume": 300.0
    })

    # FOC48 Measurement trigger
    sequence.append({
        "action": "System: FOC48 Measurement",
        "mode": "auto",
        "well": "A1"
    })

    # Post-Read Incubation removed. System will immediately transition to next step.

# Export the payload
with open('liquid_handler_crc_48well_5min_inc.json', 'w') as f:
    json.dump(sequence, f, indent=4)

print(f"Protocol generated! Total tips required for run: {tip_index}")
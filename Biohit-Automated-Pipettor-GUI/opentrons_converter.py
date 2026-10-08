import json
import os

class OpentronsConverter:
    def __init__(self, deck_calibration_path):
        # Load the Biohit absolute slot locations
        with open(deck_calibration_path, 'r') as f:
            self.biohit_deck = json.load(f)
            
        # Map Opentrons slot names (1-11) to Biohit Slot names (Slot_1 - Slot_6)
        # We will assume Opentrons 1-6 map directly to Biohit Slot_1 to Slot_6 for now.
        self.slot_mapping = {
            "1": "Slot_1", "2": "Slot_2", "3": "Slot_3",
            "4": "Slot_4", "5": "Slot_5", "6": "Slot_6"
        }

    def convert_protocol(self, json_filepath):
        print(f"Loading Opentrons Protocol: {json_filepath}")
        with open(json_filepath, 'r') as f:
            protocol = json.load(f)

        # In Opentrons v5/v6 JSON, labware definitions are embedded!
        # This means we don't even need to calculate Grid Math manually, 
        # Opentrons gives us the exact X, Y offsets for every single well!
        labware_instances = protocol.get('labware', {})
        labware_defs = protocol.get('labwareDefinitions', {})
        commands = protocol.get('commands', [])

        biohit_script = []

        for cmd in commands:
            cmd_type = cmd.get('commandType') or cmd.get('command')
            params = cmd.get('params', {})

            if cmd_type in ['pickUpTip', 'dropTip', 'aspirate', 'dispense']:
                labware_id = params.get('labwareId') or params.get('labware')
                well_name = params.get('wellName') or params.get('well')
                volume = params.get('volume', 0)

                # Look up where this labware is on the deck
                labware_info = labware_instances.get(labware_id, {})
                opentrons_slot = str(labware_info.get('slot'))
                biohit_slot_name = self.slot_mapping.get(opentrons_slot)

                if not biohit_slot_name:
                    print(f"Warning: Protocol uses Opentrons slot {opentrons_slot} which isn't mapped to Biohit deck!")
                    continue

                biohit_slot_data = self.biohit_deck.get(biohit_slot_name, {})
                slot_x = biohit_slot_data.get('x_abs', 0)
                slot_y = biohit_slot_data.get('y_abs', 0)

                # Look up the exact X, Y well offset from the Opentrons definition
                def_id = labware_info.get('definitionId')
                labware_def = labware_defs.get(def_id, {})
                wells = labware_def.get('wells', {})
                well_data = wells.get(well_name, {})
                
                # Calculate Absolute Biohit Coordinates!
                well_x = slot_x + well_data.get('x', 0)
                well_y = slot_y + well_data.get('y', 0)
                well_z = well_data.get('z', 0) # Base height of the well

                # Generate the Biohit sequence step
                step = {
                    "action": cmd_type,
                    "target_x": round(well_x, 2),
                    "target_y": round(well_y, 2),
                    "labware": def_id,
                    "well": well_name,
                    "volume": volume
                }
                biohit_script.append(step)

        return biohit_script

if __name__ == "__main__":
    print("Opentrons to Biohit Converter initialized!")
    print("Waiting for a sample protocol.json to test translation...")

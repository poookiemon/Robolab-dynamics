import json
from opentrons import protocol_api, types

metadata = {
    "protocolName": "EHM Media Change and Drug addition",
    "created": "2026-10-07T11:49:22.533Z",
    "internalAppBuildDate": "Thu, 13 Aug 2026 17:57:06 GMT",
    "lastModified": "2026-10-21T23:32:42.708Z",
    "protocolDesigner": "26.6.0",
    "source": "Protocol Designer",
}

requirements = {"robotType": "OT-2", "apiLevel": "2.28"}

def run(protocol: protocol_api.ProtocolContext) -> None:
    # Load Labware:
    tip_rack_1 = protocol.load_labware(
        "opentrons_96_tiprack_300ul",
        location="8",
        label="Opentrons OT-2 96 Tip Rack 300 µL (1)",
        namespace="opentrons",
        version=1,
    )
    well_plate_1 = protocol.load_labware_from_definition(
        CUSTOM_LABWARE["custom_beta/myriamed_48_wellplate_800ul/1"],
        location="4",
    )
    tube_rack_1 = protocol.load_labware(
        "opentrons_10_tuberack_nest_4x50ml_6x15ml_conical",
        location="10",
        namespace="opentrons",
        version=2,
    )

    # Load Pipettes:
    pipette_right = protocol.load_instrument("p300_single", "right")

    # Define Liquids:
    liquid_1 = protocol.define_liquid(
        "Medium",
        display_color="#b925ff",
    )
    liquid_2 = protocol.define_liquid(
        "DMSO Drug",
        display_color="#ffd600",
    )

    # Load Liquids:
    well_plate_1.load_liquid(
        wells=[
            "B1", "C1", "D1", "E1", "F1", "G1", "H1", "A1",
            "A2", "B2", "C2", "D2", "E2", "F2", "G2", "H2",
            "A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3",
            "A4", "B4", "C4", "D4", "E4", "F4", "G4", "H4",
            "A5", "B5", "C5", "D5", "E5", "F5", "G5", "H5",
            "A6", "B6", "C6", "D6", "E6", "F6", "G6", "H6"
        ],
        liquid=liquid_1,
        volume=750,
    )
    tube_rack_1.load_liquid(
        wells=["A3", "B3"],
        liquid=liquid_1,
        volume=30000,
    )

    # PROTOCOL STEPS

    # Step 1: Removing Media
    pipette_right.transfer_with_liquid_class(
        volume=500,
        source=[well_plate_1["A1"], well_plate_1["B1"], well_plate_1["C1"], well_plate_1["D1"], well_plate_1["E1"], well_plate_1["F1"], well_plate_1["G1"], well_plate_1["H1"], well_plate_1["A2"], well_plate_1["B2"], well_plate_1["C2"], well_plate_1["D2"], well_plate_1["E2"], well_plate_1["F2"], well_plate_1["G2"], well_plate_1["H2"], well_plate_1["A3"], well_plate_1["B3"], well_plate_1["C3"], well_plate_1["D3"], well_plate_1["E3"], well_plate_1["F3"], well_plate_1["G3"], well_plate_1["H3"], well_plate_1["A4"], well_plate_1["B4"], well_plate_1["C4"], well_plate_1["D4"], well_plate_1["E4"], well_plate_1["F4"], well_plate_1["G4"], well_plate_1["H4"], well_plate_1["A5"], well_plate_1["B5"], well_plate_1["C5"], well_plate_1["D5"], well_plate_1["E5"], well_plate_1["F5"], well_plate_1["G5"], well_plate_1["H5"], well_plate_1["A6"], well_plate_1["B6"], well_plate_1["C6"], well_plate_1["D6"], well_plate_1["E6"], well_plate_1["F6"], well_plate_1["G6"], well_plate_1["H6"]],
        dest=[tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"], tube_rack_1["A4"]],
        new_tip="once",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_1",
            properties={"p300_single": {"opentrons/opentrons_96_tiprack_300ul/1": {
                "aspirate": {
                    "aspirate_position": {
                        "offset": {"x": 0, "y": 0, "z": 1},
                        "position_reference": "well-bottom",
                    },
                    "flow_rate_by_volume": [(0, 150)],
                    "pre_wet": False,
                    "correction_by_volume": [(0, 0)],
                    "delay": {"enabled": False},
                    "mix": {"enabled": False},
                    "submerge": {
                        "delay": {"enabled": False},
                        "speed": 125,
                        "start_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                    },
                    "retract": {
                        "air_gap_by_volume": [(0, 0)],
                        "delay": {"enabled": False},
                        "end_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                        "speed": 125,
                        "touch_tip": {"enabled": False},
                    },
                },
                "dispense": {
                    "dispense_position": {
                        "offset": {"x": 0, "y": 0, "z": 1},
                        "position_reference": "well-bottom",
                    },
                    "flow_rate_by_volume": [(0, 300)],
                    "delay": {"enabled": False},
                    "submerge": {
                        "delay": {"enabled": False},
                        "speed": 125,
                        "start_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                    },
                    "retract": {
                        "air_gap_by_volume": [(0, 0)],
                        "delay": {"enabled": False},
                        "end_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                        "speed": 125,
                        "touch_tip": {"enabled": False},
                        "blowout": {"enabled": False},
                    },
                    "correction_by_volume": [(0, 0)],
                    "push_out_by_volume": [(0, 0)],
                    "mix": {"enabled": False},
                },
            }}},
        ),
        tips=[tip_rack_1["A1"]],
    )

    # Step 2: Adding Media
    pipette_right.transfer_with_liquid_class(
        volume=500,
        source=[tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"]],
        dest=[well_plate_1["A1"], well_plate_1["B1"], well_plate_1["C1"], well_plate_1["D1"], well_plate_1["E1"], well_plate_1["F1"], well_plate_1["G1"], well_plate_1["H1"], well_plate_1["A2"], well_plate_1["B2"], well_plate_1["C2"], well_plate_1["D2"], well_plate_1["E2"], well_plate_1["F2"], well_plate_1["G2"], well_plate_1["H2"], well_plate_1["A3"], well_plate_1["B3"], well_plate_1["C3"], well_plate_1["D3"], well_plate_1["E3"], well_plate_1["F3"], well_plate_1["G3"], well_plate_1["H3"], well_plate_1["A4"], well_plate_1["B4"], well_plate_1["C4"], well_plate_1["D4"], well_plate_1["E4"], well_plate_1["F4"], well_plate_1["G4"], well_plate_1["H4"], well_plate_1["A5"], well_plate_1["B5"], well_plate_1["C5"], well_plate_1["D5"], well_plate_1["E5"], well_plate_1["F5"], well_plate_1["G5"], well_plate_1["H5"], well_plate_1["A6"], well_plate_1["B6"], well_plate_1["C6"], well_plate_1["D6"], well_plate_1["E6"], well_plate_1["F6"], well_plate_1["G6"], well_plate_1["H6"]],
        new_tip="once",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_2",
            properties={"p300_single": {"opentrons/opentrons_96_tiprack_300ul/1": {
                "aspirate": {
                    "aspirate_position": {
                        "offset": {"x": 0, "y": 0, "z": 1},
                        "position_reference": "well-bottom",
                    },
                    "flow_rate_by_volume": [(0, 150)],
                    "pre_wet": False,
                    "correction_by_volume": [(0, 0)],
                    "delay": {"enabled": False},
                    "mix": {"enabled": False},
                    "submerge": {
                        "delay": {"enabled": False},
                        "speed": 125,
                        "start_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                    },
                    "retract": {
                        "air_gap_by_volume": [(0, 0)],
                        "delay": {"enabled": False},
                        "end_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                        "speed": 125,
                        "touch_tip": {"enabled": False},
                    },
                },
                "dispense": {
                    "dispense_position": {
                        "offset": {"x": 0, "y": 0, "z": 1},
                        "position_reference": "well-bottom",
                    },
                    "flow_rate_by_volume": [(0, 300)],
                    "delay": {"enabled": False},
                    "submerge": {
                        "delay": {"enabled": False},
                        "speed": 125,
                        "start_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                    },
                    "retract": {
                        "air_gap_by_volume": [(0, 0)],
                        "delay": {"enabled": False},
                        "end_position": {
                            "offset": {"x": 0, "y": 0, "z": 2},
                            "position_reference": "well-top",
                        },
                        "speed": 125,
                        "touch_tip": {"enabled": False},
                        "blowout": {"enabled": False},
                    },
                    "correction_by_volume": [(0, 0)],
                    "push_out_by_volume": [(0, 0)],
                    "mix": {"enabled": False},
                },
            }}},
        ),
        tips=[tip_rack_1["B1"]],
    )

CUSTOM_LABWARE = json.loads("""{"custom_beta/myriamed_48_wellplate_800ul/1":{"ordering":[["A1","B1","C1","D1","E1","F1","G1","H1"],["A2","B2","C2","D2","E2","F2","G2","H2"],["A3","B3","C3","D3","E3","F3","G3","H3"],["A4","B4","C4","D4","E4","F4","G4","H4"],["A5","B5","C5","D5","E5","F5","G5","H5"],["A6","B6","C6","D6","E6","F6","G6","H6"]],"brand":{"brand":"myriamed","brandId":["TM5x0001"]},"metadata":{"displayName":"Myriamed 48 Well Plate 800 µL","displayCategory":"wellPlate","displayVolumeUnits":"µL","tags":[]},"dimensions":{"xDimension":127.5,"yDimension":85.5,"zDimension":18},"wells":{"A1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":77,"z":11},"B1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":68,"z":11},"C1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":59,"z":11},"D1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":50,"z":11},"E1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":41,"z":11},"F1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":32,"z":11},"G1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":23,"z":11},"H1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":14,"z":11},"A2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":77,"z":11},"B2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":68,"z":11},"C2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":59,"z":11},"D2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":50,"z":11},"E2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":41,"z":11},"F2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":32,"z":11},"G2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":23,"z":11},"H2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":14,"z":11},"A3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":77,"z":11},"B3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":68,"z":11},"C3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":59,"z":11},"D3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":50,"z":11},"E3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":41,"z":11},"F3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":32,"z":11},"G3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":23,"z":11},"H3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":14,"z":11},"A4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":77,"z":11},"B4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":68,"z":11},"C4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":59,"z":11},"D4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":50,"z":11},"E4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":41,"z":11},"F4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":32,"z":11},"G4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":23,"z":11},"H4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":14,"z":11},"A5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":77,"z":11},"B5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":68,"z":11},"C5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":59,"z":11},"D5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":50,"z":11},"E5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":41,"z":11},"F5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":32,"z":11},"G5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":23,"z":11},"H5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":14,"z":11},"A6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":77,"z":11},"B6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":68,"z":11},"C6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":59,"z":11},"D6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":50,"z":11},"E6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":41,"z":11},"F6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":32,"z":11},"G6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":23,"z":11},"H6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":14,"z":11}},"groups":[{"metadata":{"wellBottomShape":"flat"},"wells":["A1","B1","C1","D1","E1","F1","G1","H1","A2","B2","C2","D2","E2","F2","G2","H2","A3","B3","C3","D3","E3","F3","G3","H3","A4","B4","C4","D4","E4","F4","G4","H4","A5","B5","C5","D5","E5","F5","G5","H5","A6","B6","C6","D6","E6","F6","G6","H6"]}],"parameters":{"format":"irregular","quirks":[],"isTiprack":false,"isMagneticModuleCompatible":false,"loadName":"myriamed_48_wellplate_800ul"},"namespace":"custom_beta","version":1,"schemaVersion":2,"cornerOffsetFromSlot":{"x":0,"y":0,"z":0}}}""")

DESIGNER_APPLICATION = """{"robot":{"model":"OT-2 Standard"},"designerApplication":{"name":"opentrons/protocol-designer","version":"2606.0.0","data":{"pipetteTiprackAssignments":{"08b41b2f-6dbd-4954-af18-9c4bc803b76a":["opentrons/opentrons_96_tiprack_300ul/1"]},"dismissedWarnings":{"form":["TIP_POSITIONED_LOW_IN_TUBE"],"timeline":["ASPIRATE_FROM_PRISTINE_WELL"]},"ingredients":{"0":{"displayName":"Medium","displayColor":"#b925ff","description":null,"liquidGroupId":"0"},"1":{"displayName":"DMSO Drug","displayColor":"#ffd600","description":null,"liquidGroupId":"1"}},"ingredLocations":{"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1":{"B1":{"0":{"volume":750}},"C1":{"0":{"volume":750}},"D1":{"0":{"volume":750}},"E1":{"0":{"volume":750}},"F1":{"0":{"volume":750}},"G1":{"0":{"volume":750}},"H1":{"0":{"volume":750}},"A1":{"0":{"volume":750}},"A2":{"0":{"volume":750}},"B2":{"0":{"volume":750}},"C2":{"0":{"volume":750}},"D2":{"0":{"volume":750}},"E2":{"0":{"volume":750}},"F2":{"0":{"volume":750}},"G2":{"0":{"volume":750}},"H2":{"0":{"volume":750}},"A3":{"0":{"volume":750}},"B3":{"0":{"volume":750}},"C3":{"0":{"volume":750}},"D3":{"0":{"volume":750}},"E3":{"0":{"volume":750}},"F3":{"0":{"volume":750}},"G3":{"0":{"volume":750}},"H3":{"0":{"volume":750}},"A4":{"0":{"volume":750}},"B4":{"0":{"volume":750}},"C4":{"0":{"volume":750}},"D4":{"0":{"volume":750}},"E4":{"0":{"volume":750}},"F4":{"0":{"volume":750}},"G4":{"0":{"volume":750}},"H4":{"0":{"volume":750}},"A5":{"0":{"volume":750}},"B5":{"0":{"volume":750}},"C5":{"0":{"volume":750}},"D5":{"0":{"volume":750}},"E5":{"0":{"volume":750}},"F5":{"0":{"volume":750}},"G5":{"0":{"volume":750}},"H5":{"0":{"volume":750}},"A6":{"0":{"volume":750}},"B6":{"0":{"volume":750}},"C6":{"0":{"volume":750}},"D6":{"0":{"volume":750}},"E6":{"0":{"volume":750}},"F6":{"0":{"volume":750}},"G6":{"0":{"volume":750}},"H6":{"0":{"volume":750}}},"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2":{"A3":{"0":{"volume":30000}},"B3":{"0":{"volume":30000}}}},"savedStepForms":{"__INITIAL_DECK_SETUP_STEP__":{"stepType":"manualIntervention","id":"__INITIAL_DECK_SETUP_STEP__","labwareLocationUpdate":{"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1":"8","b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1":"4","ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2":"10"},"pipetteLocationUpdate":{"08b41b2f-6dbd-4954-af18-9c4bc803b76a":"right"},"moduleLocationUpdate":{},"moduleStateUpdate":{},"trashBinLocationUpdate":{"cdc13737-e06e-44b5-906e-e510a66d325d:trashBin":"cutout12"},"wasteChuteLocationUpdate":{},"stagingAreaLocationUpdate":{},"gripperLocationUpdate":{}},"78343e39-56ef-4b58-b6a5-36297352951a":{"id":"78343e39-56ef-4b58-b6a5-36297352951a","stepType":"moveLiquid","stepName":"Removing Media","stepDetails":"","stepNumber":0,"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A1","B1","C1","D1","E1","F1","G1","H1","A2","B2","C2","D2","E2","F2","G2","H2","A3","B3","C3","D3","E3","F3","G3","H3","A4","B4","C4","D4","E4","F4","G4","H4","A5","B5","C5","D5","E5","F5","G5","H5","A6","B6","C6","D6","E6","F6","G6","H6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["A1"]],"volume":"500"},"8f422ee1-157c-4954-beee-3df515201757":{"id":"8f422ee1-157c-4954-beee-3df515201757","stepType":"moveLiquid","stepName":"Adding Media","stepDetails":"","stepNumber":0,"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A1","B1","C1","D1","E1","F1","G1","H1","A2","B2","C2","D2","E2","F2","G2","H2","A3","B3","C3","D3","E3","F3","G3","H3","A4","B4","C4","D4","E4","F4","G4","H4","A5","B5","C5","D5","E5","F5","G5","H5","A6","B6","C6","D6","E6","F6","G6","H6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"500"}},"orderedStepIds":["78343e39-56ef-4b58-b6a5-36297352951a","8f422ee1-157c-4954-beee-3df515201757"],"pipettes":{"08b41b2f-6dbd-4954-af18-9c4bc803b76a":{"pipetteName":"p300_single"}},"modules":{},"labware":{"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1":{"displayName":"Opentrons OT-2 96 Tip Rack 300 µL (1)","labwareDefURI":"opentrons/opentrons_96_tiprack_300ul/1"},"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1":{"displayName":"Myriamed 48 Well Plate 800 µL","labwareDefURI":"custom_beta/myriamed_48_wellplate_800ul/1"},"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2":{"displayName":"Opentrons 10 Tube Rack with NEST 4x50 mL, 6x15 mL Conical","labwareDefURI":"opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2"}}}},"metadata":{"protocolName":"EHM Media Change and Drug addition","author":"","description":"","source":"Protocol Designer","created":1791373762533,"lastModified":1792625562708}}"""

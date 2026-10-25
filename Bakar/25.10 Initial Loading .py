import json
from opentrons import protocol_api, types

metadata = {
    "protocolName": "EHM Media Change and Drug addition",
    "created": "2026-10-07T11:49:22.533Z",
    "internalAppBuildDate": "Thu, 13 Aug 2026 17:57:06 GMT",
    "lastModified": "2026-10-21T09:54:13.367Z",
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
    well_plate_2 = protocol.load_labware_from_definition(
        CUSTOM_LABWARE["custom_beta/myriamed_48_wellplate_800ul/1"],
        location="5",
        label="Myriamed 48 Well Plate 800 µL (1)",
    )
    well_plate_3 = protocol.load_labware(
        "nunc_96_wellplate_450ul",
        location="7",
        namespace="opentrons",
        version=1,
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
        volume=0,
    )
    well_plate_2.load_liquid(
        wells=[
            "B1", "C1", "D1", "E1", "F1", "G1", "H1", "A1",
            "A2", "B2", "C2", "D2", "E2", "F2", "G2", "H2",
            "A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3",
            "A4", "B4", "C4", "D4", "E4", "F4", "G4", "H4",
            "A5", "B5", "C5", "D5", "E5", "F5", "G5", "H5",
            "A6", "B6", "C6", "D6", "E6", "F6", "G6", "H6"
        ],
        liquid=liquid_1,
        volume=0,
    )
    well_plate_3.load_liquid(
        wells=[
            "B1", "C1", "D1", "E1", "F1", "G1", "H1", "B2",
            "C2", "D2", "E2", "F2", "G2", "H2", "B3", "C3",
            "D3", "E3", "F3", "G3", "H3", "B4", "C4", "D4",
            "E4", "F4", "G4", "H4", "B5", "C5", "D5", "E5",
            "F5", "G5", "H5", "B6", "C6", "D6", "E6", "F6",
            "G6", "H6", "B7", "C7", "D7", "E7", "F7", "G7",
            "H7", "B8", "C8", "D8", "E8", "F8", "G8", "H8",
            "B9", "C9", "D9", "E9", "F9", "G9", "H9", "B10",
            "C10", "D10", "E10", "F10", "G10", "H10", "B11", "C11",
            "D11", "E11", "F11", "G11", "H11", "B12", "C12", "D12",
            "E12", "F12", "G12", "H12", "A1", "A2", "A3", "A4",
            "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12"
        ],
        liquid=liquid_2,
        volume=100,
    )
    tube_rack_1.load_liquid(
        wells=["A3", "B3"],
        liquid=liquid_1,
        volume=30000,
    )

    # PROTOCOL STEPS

    
    # Step 2: Adding Media 745 S1
    pipette_right.transfer_with_liquid_class(
        volume=745,
        source=[tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"]],
        dest=[well_plate_1["A1"], well_plate_1["B1"], well_plate_1["C1"], well_plate_1["A2"], well_plate_1["B2"], well_plate_1["C2"], well_plate_1["A3"], well_plate_1["B3"], well_plate_1["C3"], well_plate_1["A4"], well_plate_1["B4"], well_plate_1["C4"], well_plate_1["A5"], well_plate_1["B5"], well_plate_1["C5"], well_plate_1["A6"], well_plate_1["B6"], well_plate_1["C6"]],
        new_tip="once",
                       return_tip=None,
                       keep_last_tip=True,
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
        tips=[tip_rack_1["A1"]],
    )

    # Step 3: Adding DMSO-DRUG S1 No Drug
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["A1"]],
        dest=[well_plate_1["A1"], well_plate_1["B1"], well_plate_1["C1"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_3",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["A1"]],
    )

    # Step 4: Adding DMSO-DRUG S1C1
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["A2"]],
        dest=[well_plate_1["A2"], well_plate_1["B2"], well_plate_1["C2"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_4",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["A1"]],
    )

    # Step 5: Adding DMSO-DRUG S1C2
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["A3"]],
        dest=[well_plate_1["A3"], well_plate_1["B3"], well_plate_1["C3"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_5",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["A1"]],
    )

    # Step 6: Adding DMSO-DRUG S1C3
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["A4"]],
        dest=[well_plate_1["A4"], well_plate_1["B4"], well_plate_1["C4"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_6",
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
                                            "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                                        },
                                    }}},
                                ),
        tips=[tip_rack_1["A1"]],
    )

    # Step 7: Adding DMSO-DRUG S1C4
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["A5"]],
        dest=[well_plate_1["A5"], well_plate_1["B5"], well_plate_1["C5"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_7",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["A1"]],
    )

    # Step 8: Adding DMSO-DRUG S1C5
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["A6"]],
        dest=[well_plate_1["A6"], well_plate_1["B6"], well_plate_1["C6"]],
        new_tip="never",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_8",
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
                                            "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                                        },
                                    }}},
                                ),
        tips=[tip_rack_1["A1"]],
    )
    pipette_right.drop_tip()
    
    # Step 10: Adding Media 745 S2
    pipette_right.transfer_with_liquid_class(
        volume=745,
        source=[tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"]],
        dest=[well_plate_1["D1"], well_plate_1["E1"], well_plate_1["F1"], well_plate_1["D2"], well_plate_1["E2"], well_plate_1["F2"], well_plate_1["D3"], well_plate_1["E3"], well_plate_1["F3"], well_plate_1["D4"], well_plate_1["E4"], well_plate_1["F4"], well_plate_1["D5"], well_plate_1["E5"], well_plate_1["F5"], well_plate_1["D6"], well_plate_1["E6"], well_plate_1["F6"]],
        new_tip="once",
        return_tip=None,
               keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_10",
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

    # Step 11: Adding DMSO-DRUG S1 No Drug
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["B1"]],
        dest=[well_plate_1["D1"], well_plate_1["E1"], well_plate_1["F1"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_11",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["B1"]],
    )

    # Step 12: Adding DMSO-DRUG S2C1
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["B2"]],
        dest=[well_plate_1["D2"], well_plate_1["E2"], well_plate_1["F2"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_12",
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
                                            "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                                        },
                                    }}},
                                ),
        tips=[tip_rack_1["B1"]],
    )

    # Step 13: Adding DMSO-DRUG S2C2
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["B3"]],
        dest=[well_plate_1["D3"], well_plate_1["E3"], well_plate_1["F3"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_13",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["B1"]],
    )

    # Step 14: Adding DMSO-DRUG S2C3
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["B4"]],
        dest=[well_plate_1["D4"], well_plate_1["E4"], well_plate_1["F4"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_14",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["B1"]],
    )

    # Step 15: Adding DMSO-DRUG S2C4
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["B5"]],
        dest=[well_plate_1["D5"], well_plate_1["E5"], well_plate_1["F5"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_15",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["B1"]],
    )

    # Step 16: Adding DMSO-DRUG S2C5
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["B6"], well_plate_3["B6"], well_plate_3["B6"]],
        dest=[well_plate_1["D6"], well_plate_1["E6"], well_plate_1["F6"]],
        new_tip="never",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_16",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["B1"]],
    )
    pipette_right.drop_tip()

    

    

    # Step 19: Adding Media 495 S3 2 Row
    pipette_right.transfer_with_liquid_class(
        volume=745,
        source=[tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"], tube_rack_1["A3"]],
        dest=[well_plate_1["G1"], well_plate_1["H1"], well_plate_1["G2"], well_plate_1["H2"], well_plate_1["G3"], well_plate_1["H3"], well_plate_1["G4"], well_plate_1["H4"], well_plate_1["G5"], well_plate_1["H5"], well_plate_1["G6"], well_plate_1["H6"]],
        new_tip="once",
        return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_19",
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
        tips=[tip_rack_1["C1"]],
    )

    # Step 20: Adding Media 495 S3 1 Row
    pipette_right.transfer_with_liquid_class(
        volume=745,
        source=[tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"]],
        dest=[well_plate_2["A1"], well_plate_2["A2"], well_plate_2["A3"], well_plate_2["A4"], well_plate_2["A5"], well_plate_2["A6"]],
       new_tip="never",
                      return_tip=None,
                      keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_20",
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
        tips=[tip_rack_1["C1"]],
    )

    # Step 21: Adding DMSO-DRUG S3 No Drug 2Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C1"], well_plate_3["C1"]],
        dest=[well_plate_1["G1"], well_plate_1["H1"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_21",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 22: Adding DMSO-DRUG S1 No Drug 1 Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C1"]],
        dest=[well_plate_2["A1"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_22",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 23: Adding DMSO-DRUG S3C1
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C2"]],
        dest=[well_plate_1["G2"], well_plate_1["H2"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_23",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 24: Adding DMSO-DRUG S3C1 1Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C2"]],
        dest=[well_plate_2["A2"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_24",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 25: Adding DMSO-DRUG S3C2
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C3"]],
        dest=[well_plate_1["G3"], well_plate_1["H3"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_25",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 26: Adding DMSO-DRUG S3C2 1 Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C3"]],
        dest=[well_plate_2["A3"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_26",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 27: Adding DMSO-DRUG S3C3 2 Row
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C4"]],
        dest=[well_plate_1["G4"], well_plate_1["H4"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_27",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 28: Adding DMSO-DRUG S3C3 1 Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C4"]],
        dest=[well_plate_2["A4"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_28",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 29: Adding DMSO-DRUG S3C4 2Row
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C5"]],
        dest=[well_plate_1["G5"], well_plate_1["H5"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_29",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 30: Adding DMSO-DRUG S3C4 1 Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C5"]],
        dest=[well_plate_2["A5"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_30",
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
                                            "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                                        },
                                    }}},
                                ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 31: Adding DMSO-DRUG S3C5 2 Row
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C6"]],
        dest=[well_plate_1["G6"], well_plate_1["H6"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_31",
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
                                           "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                                       },
                                   }}},
                               ),
        tips=[tip_rack_1["C1"]],
    )

    # Step 32: Adding DMSO-DRUG S3C5 1 Row
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["C6"]],
        dest=[well_plate_2["A6"]],
        new_tip="never",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_32",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["C1"]],
    )
    pipette_right.drop_tip()

    

    # Step 34: Adding Media 745 S4 
    pipette_right.transfer_with_liquid_class(
        volume=745,
        source=[tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"]],
        dest=[well_plate_2["B1"], well_plate_2["C1"], well_plate_2["D1"], well_plate_2["B2"], well_plate_2["C2"], well_plate_2["D2"], well_plate_2["B3"], well_plate_2["C3"], well_plate_2["D3"], well_plate_2["B4"], well_plate_2["C4"], well_plate_2["D4"], well_plate_2["B5"], well_plate_2["C5"], well_plate_2["D5"], well_plate_2["B6"], well_plate_2["C6"], well_plate_2["D6"]],
        new_tip="once",
        return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_34",
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
        tips=[tip_rack_1["D1"]],
    )

    # Step 35: Adding DMSO-DRUG S4 No Drug 
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D1"]],
        dest=[well_plate_2["B1"], well_plate_2["C1"], well_plate_2["D1"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_35",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["D1"]],
    )

    # Step 36: Adding DMSO-DRUG S4C1
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D2"]],
        dest=[well_plate_2["B2"], well_plate_2["C2"], well_plate_2["D2"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_36",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["D1"]],
    )

    # Step 37: Adding DMSO-DRUG S4C2
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D3"]],
        dest=[well_plate_2["B3"], well_plate_2["C3"], well_plate_2["D3"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_37",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["D1"]],
    )

    # Step 38: Adding DMSO-DRUG S4C3
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D4"]],
        dest=[well_plate_2["B4"], well_plate_2["C4"], well_plate_2["D4"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_38",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["D1"]],
    )

    # Step 39: Adding DMSO-DRUG S4C4
    pipette_right.transfer_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D5"], well_plate_3["D5"], well_plate_3["D5"]],
        dest=[well_plate_2["B5"], well_plate_2["C5"], well_plate_2["D5"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_39",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["D1"]],
    )

    # Step 40: Adding DMSO-DRUG S4C5 
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D6"]],
        dest=[well_plate_2["B6"], well_plate_2["C6"], well_plate_2["D6"]],
        new_tip="never",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_40",
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
                               "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                           },
                       }}},
                   ),
        tips=[tip_rack_1["D1"]],
    )
    pipette_right.drop_tip()

    
    # Step 42: Adding Media 745 S5
    pipette_right.transfer_with_liquid_class(
        volume=745,
        source=[tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"], tube_rack_1["B3"]],
        dest=[well_plate_2["E1"], well_plate_2["F1"], well_plate_2["G1"], well_plate_2["E2"], well_plate_2["F2"], well_plate_2["G2"], well_plate_2["E3"], well_plate_2["F3"], well_plate_2["G3"], well_plate_2["E4"], well_plate_2["F4"], well_plate_2["G4"], well_plate_2["E5"], well_plate_2["F5"], well_plate_2["G5"], well_plate_2["E6"], well_plate_2["F6"], well_plate_2["G6"]],
        new_tip="once",
        return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="transfer_step_42",
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
        tips=[tip_rack_1["E1"]],
    )

    # Step 43: Adding DMSO-DRUG S5 No Drug 
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["E1"]],
        dest=[well_plate_2["E1"], well_plate_2["F1"], well_plate_2["G1"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_43",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["E1"]],
    )

    # Step 44: Adding DMSO-DRUG S5C1
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["E2"]],
        dest=[well_plate_2["E2"], well_plate_2["F2"], well_plate_2["G2"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_44",
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
                               "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                           },
                       }}},
                   ),
        tips=[tip_rack_1["E1"]],
    )

    # Step 45: Adding DMSO-DRUG S5C2
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["E3"]],
        dest=[well_plate_2["E3"], well_plate_2["F3"], well_plate_2["G3"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_45",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["E1"]],
    )

    # Step 46: Adding DMSO-DRUG S5C3
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["E4"]],
        dest=[well_plate_2["E4"], well_plate_2["F4"], well_plate_2["G4"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_46",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["E1"]],
    )

    # Step 47: Adding DMSO-DRUG S5C4
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["D6"]],
        dest=[well_plate_2["E5"], well_plate_2["F5"], well_plate_2["G5"]],
        new_tip="never",
                       return_tip=None,
                       keep_last_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_47",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["E1"]],
    )

    # Step 48: Adding DMSO-DRUG S5C5 
    pipette_right.distribute_with_liquid_class(
        volume=7.5,
        source=[well_plate_3["E6"]],
        dest=[well_plate_2["E6"], well_plate_2["F6"], well_plate_2["G6"]],
        new_tip="never",
        return_tip=True,
        tip_racks=[tip_rack_1],
        liquid_class=protocol.define_liquid_class(
            name="distribute_step_48",
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
                                "mix": {"enabled": True, "repetitions": 3, "volume": 200},
                            },
                        }}},
                    ),
        tips=[tip_rack_1["E1"]],
    )
    pipette_right.drop_tip()
CUSTOM_LABWARE = json.loads("""{"custom_beta/myriamed_48_wellplate_800ul/1":{"ordering":[["A1","B1","C1","D1","E1","F1","G1","H1"],["A2","B2","C2","D2","E2","F2","G2","H2"],["A3","B3","C3","D3","E3","F3","G3","H3"],["A4","B4","C4","D4","E4","F4","G4","H4"],["A5","B5","C5","D5","E5","F5","G5","H5"],["A6","B6","C6","D6","E6","F6","G6","H6"]],"brand":{"brand":"myriamed","brandId":["TM5x0001"]},"metadata":{"displayName":"Myriamed 48 Well Plate 800 µL","displayCategory":"wellPlate","displayVolumeUnits":"µL","tags":[]},"dimensions":{"xDimension":127.5,"yDimension":85.5,"zDimension":18},"wells":{"A1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":77,"z":11},"B1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":68,"z":11},"C1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":59,"z":11},"D1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":50,"z":11},"E1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":41,"z":11},"F1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":32,"z":11},"G1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":23,"z":11},"H1":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":11.5,"y":14,"z":11},"A2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":77,"z":11},"B2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":68,"z":11},"C2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":59,"z":11},"D2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":50,"z":11},"E2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":41,"z":11},"F2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":32,"z":11},"G2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":23,"z":11},"H2":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":29.5,"y":14,"z":11},"A3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":77,"z":11},"B3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":68,"z":11},"C3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":59,"z":11},"D3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":50,"z":11},"E3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":41,"z":11},"F3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":32,"z":11},"G3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":23,"z":11},"H3":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":47.5,"y":14,"z":11},"A4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":77,"z":11},"B4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":68,"z":11},"C4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":59,"z":11},"D4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":50,"z":11},"E4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":41,"z":11},"F4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":32,"z":11},"G4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":23,"z":11},"H4":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":65.5,"y":14,"z":11},"A5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":77,"z":11},"B5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":68,"z":11},"C5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":59,"z":11},"D5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":50,"z":11},"E5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":41,"z":11},"F5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":32,"z":11},"G5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":23,"z":11},"H5":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":83.5,"y":14,"z":11},"A6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":77,"z":11},"B6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":68,"z":11},"C6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":59,"z":11},"D6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":50,"z":11},"E6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":41,"z":11},"F6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":32,"z":11},"G6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":23,"z":11},"H6":{"depth":7,"totalLiquidVolume":800,"shape":"rectangular","xDimension":17.5,"yDimension":8.5,"x":101.5,"y":14,"z":11}},"groups":[{"metadata":{"wellBottomShape":"flat"},"wells":["A1","B1","C1","D1","E1","F1","G1","H1","A2","B2","C2","D2","E2","F2","G2","H2","A3","B3","C3","D3","E3","F3","G3","H3","A4","B4","C4","D4","E4","F4","G4","H4","A5","B5","C5","D5","E5","F5","G5","H5","A6","B6","C6","D6","E6","F6","G6","H6"]}],"parameters":{"format":"irregular","quirks":[],"isTiprack":false,"isMagneticModuleCompatible":false,"loadName":"myriamed_48_wellplate_800ul"},"namespace":"custom_beta","version":1,"schemaVersion":2,"cornerOffsetFromSlot":{"x":0,"y":0,"z":0}}}""")

DESIGNER_APPLICATION = """{"robot":{"model":"OT-2 Standard"},"designerApplication":{"name":"opentrons/protocol-designer","version":"2606.0.0","data":{"pipetteTiprackAssignments":{"08b41b2f-6dbd-4954-af18-9c4bc803b76a":["opentrons/opentrons_96_tiprack_300ul/1"]},"dismissedWarnings":{"form":["TIP_POSITIONED_LOW_IN_TUBE"],"timeline":["ASPIRATE_FROM_PRISTINE_WELL"]},"ingredients":{"0":{"displayName":"Medium","displayColor":"#b925ff","description":null,"liquidGroupId":"0"},"1":{"displayName":"DMSO Drug","displayColor":"#ffd600","description":null,"liquidGroupId":"1"}},"ingredLocations":{"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1":{"B1":{"0":{"volume":750}},"C1":{"0":{"volume":750}},"D1":{"0":{"volume":750}},"E1":{"0":{"volume":750}},"F1":{"0":{"volume":750}},"G1":{"0":{"volume":750}},"H1":{"0":{"volume":750}},"A1":{"0":{"volume":750}},"A2":{"0":{"volume":750}},"B2":{"0":{"volume":750}},"C2":{"0":{"volume":750}},"D2":{"0":{"volume":750}},"E2":{"0":{"volume":750}},"F2":{"0":{"volume":750}},"G2":{"0":{"volume":750}},"H2":{"0":{"volume":750}},"A3":{"0":{"volume":750}},"B3":{"0":{"volume":750}},"C3":{"0":{"volume":750}},"D3":{"0":{"volume":750}},"E3":{"0":{"volume":750}},"F3":{"0":{"volume":750}},"G3":{"0":{"volume":750}},"H3":{"0":{"volume":750}},"A4":{"0":{"volume":750}},"B4":{"0":{"volume":750}},"C4":{"0":{"volume":750}},"D4":{"0":{"volume":750}},"E4":{"0":{"volume":750}},"F4":{"0":{"volume":750}},"G4":{"0":{"volume":750}},"H4":{"0":{"volume":750}},"A5":{"0":{"volume":750}},"B5":{"0":{"volume":750}},"C5":{"0":{"volume":750}},"D5":{"0":{"volume":750}},"E5":{"0":{"volume":750}},"F5":{"0":{"volume":750}},"G5":{"0":{"volume":750}},"H5":{"0":{"volume":750}},"A6":{"0":{"volume":750}},"B6":{"0":{"volume":750}},"C6":{"0":{"volume":750}},"D6":{"0":{"volume":750}},"E6":{"0":{"volume":750}},"F6":{"0":{"volume":750}},"G6":{"0":{"volume":750}},"H6":{"0":{"volume":750}}},"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1":{"B1":{"0":{"volume":750}},"C1":{"0":{"volume":750}},"D1":{"0":{"volume":750}},"E1":{"0":{"volume":750}},"F1":{"0":{"volume":750}},"G1":{"0":{"volume":750}},"H1":{"0":{"volume":750}},"A1":{"0":{"volume":750}},"A2":{"0":{"volume":750}},"B2":{"0":{"volume":750}},"C2":{"0":{"volume":750}},"D2":{"0":{"volume":750}},"E2":{"0":{"volume":750}},"F2":{"0":{"volume":750}},"G2":{"0":{"volume":750}},"H2":{"0":{"volume":750}},"A3":{"0":{"volume":750}},"B3":{"0":{"volume":750}},"C3":{"0":{"volume":750}},"D3":{"0":{"volume":750}},"E3":{"0":{"volume":750}},"F3":{"0":{"volume":750}},"G3":{"0":{"volume":750}},"H3":{"0":{"volume":750}},"A4":{"0":{"volume":750}},"B4":{"0":{"volume":750}},"C4":{"0":{"volume":750}},"D4":{"0":{"volume":750}},"E4":{"0":{"volume":750}},"F4":{"0":{"volume":750}},"G4":{"0":{"volume":750}},"H4":{"0":{"volume":750}},"A5":{"0":{"volume":750}},"B5":{"0":{"volume":750}},"C5":{"0":{"volume":750}},"D5":{"0":{"volume":750}},"E5":{"0":{"volume":750}},"F5":{"0":{"volume":750}},"G5":{"0":{"volume":750}},"H5":{"0":{"volume":750}},"A6":{"0":{"volume":750}},"B6":{"0":{"volume":750}},"C6":{"0":{"volume":750}},"D6":{"0":{"volume":750}},"E6":{"0":{"volume":750}},"F6":{"0":{"volume":750}},"G6":{"0":{"volume":750}},"H6":{"0":{"volume":750}}},"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1":{"B1":{"1":{"volume":100}},"C1":{"1":{"volume":100}},"D1":{"1":{"volume":100}},"E1":{"1":{"volume":100}},"F1":{"1":{"volume":100}},"G1":{"1":{"volume":100}},"H1":{"1":{"volume":100}},"B2":{"1":{"volume":100}},"C2":{"1":{"volume":100}},"D2":{"1":{"volume":100}},"E2":{"1":{"volume":100}},"F2":{"1":{"volume":100}},"G2":{"1":{"volume":100}},"H2":{"1":{"volume":100}},"B3":{"1":{"volume":100}},"C3":{"1":{"volume":100}},"D3":{"1":{"volume":100}},"E3":{"1":{"volume":100}},"F3":{"1":{"volume":100}},"G3":{"1":{"volume":100}},"H3":{"1":{"volume":100}},"B4":{"1":{"volume":100}},"C4":{"1":{"volume":100}},"D4":{"1":{"volume":100}},"E4":{"1":{"volume":100}},"F4":{"1":{"volume":100}},"G4":{"1":{"volume":100}},"H4":{"1":{"volume":100}},"B5":{"1":{"volume":100}},"C5":{"1":{"volume":100}},"D5":{"1":{"volume":100}},"E5":{"1":{"volume":100}},"F5":{"1":{"volume":100}},"G5":{"1":{"volume":100}},"H5":{"1":{"volume":100}},"B6":{"1":{"volume":100}},"C6":{"1":{"volume":100}},"D6":{"1":{"volume":100}},"E6":{"1":{"volume":100}},"F6":{"1":{"volume":100}},"G6":{"1":{"volume":100}},"H6":{"1":{"volume":100}},"B7":{"1":{"volume":100}},"C7":{"1":{"volume":100}},"D7":{"1":{"volume":100}},"E7":{"1":{"volume":100}},"F7":{"1":{"volume":100}},"G7":{"1":{"volume":100}},"H7":{"1":{"volume":100}},"B8":{"1":{"volume":100}},"C8":{"1":{"volume":100}},"D8":{"1":{"volume":100}},"E8":{"1":{"volume":100}},"F8":{"1":{"volume":100}},"G8":{"1":{"volume":100}},"H8":{"1":{"volume":100}},"B9":{"1":{"volume":100}},"C9":{"1":{"volume":100}},"D9":{"1":{"volume":100}},"E9":{"1":{"volume":100}},"F9":{"1":{"volume":100}},"G9":{"1":{"volume":100}},"H9":{"1":{"volume":100}},"B10":{"1":{"volume":100}},"C10":{"1":{"volume":100}},"D10":{"1":{"volume":100}},"E10":{"1":{"volume":100}},"F10":{"1":{"volume":100}},"G10":{"1":{"volume":100}},"H10":{"1":{"volume":100}},"B11":{"1":{"volume":100}},"C11":{"1":{"volume":100}},"D11":{"1":{"volume":100}},"E11":{"1":{"volume":100}},"F11":{"1":{"volume":100}},"G11":{"1":{"volume":100}},"H11":{"1":{"volume":100}},"B12":{"1":{"volume":100}},"C12":{"1":{"volume":100}},"D12":{"1":{"volume":100}},"E12":{"1":{"volume":100}},"F12":{"1":{"volume":100}},"G12":{"1":{"volume":100}},"H12":{"1":{"volume":100}},"A1":{"1":{"volume":100}},"A2":{"1":{"volume":100}},"A3":{"1":{"volume":100}},"A4":{"1":{"volume":100}},"A5":{"1":{"volume":100}},"A6":{"1":{"volume":100}},"A7":{"1":{"volume":100}},"A8":{"1":{"volume":100}},"A9":{"1":{"volume":100}},"A10":{"1":{"volume":100}},"A11":{"1":{"volume":100}},"A12":{"1":{"volume":100}}},"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2":{"A3":{"0":{"volume":30000}},"B3":{"0":{"volume":30000}}}},"savedStepForms":{"__INITIAL_DECK_SETUP_STEP__":{"stepType":"manualIntervention","id":"__INITIAL_DECK_SETUP_STEP__","labwareLocationUpdate":{"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1":"8","b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1":"4","6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1":"5","fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1":"7","ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2":"10"},"pipetteLocationUpdate":{"08b41b2f-6dbd-4954-af18-9c4bc803b76a":"right"},"moduleLocationUpdate":{},"moduleStateUpdate":{},"trashBinLocationUpdate":{"cdc13737-e06e-44b5-906e-e510a66d325d:trashBin":"cutout12"},"wasteChuteLocationUpdate":{},"stagingAreaLocationUpdate":{},"gripperLocationUpdate":{}},"84fc9262-751e-4f2c-a423-7e0bac49dab5":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A1","C6","B1","C1","A2","B2","C2","A3","B3","C3","A4","B4","C4","A5","B5","C5","A6","B6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["A1"]],"volume":"500","id":"84fc9262-751e-4f2c-a423-7e0bac49dab5","stepType":"moveLiquid","stepName":"Removing Media S1 ALL","stepDetails":"","stepNumber":0},"641328e2-911f-434e-b6b0-e3a8cbe60650":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A1","B1","C1","A2","B2","C2","A3","B3","C3","A4","B4","C4","A5","B5","C5","A6","B6","C6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"495","id":"641328e2-911f-434e-b6b0-e3a8cbe60650","stepType":"moveLiquid","stepName":"Adding Media 495 S1","stepDetails":"","stepNumber":0},"c2d008ed-7143-47e8-918e-b3fedd80c95b":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A1"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A1","B1","C1"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"5","id":"c2d008ed-7143-47e8-918e-b3fedd80c95b","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1 No Drug","stepDetails":"","stepNumber":0},"03f5c66d-3165-4632-a5b5-c1624f8aa752":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A2"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A2","B2","C2"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"5","id":"03f5c66d-3165-4632-a5b5-c1624f8aa752","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1C1","stepDetails":"","stepNumber":0},"99090b3b-ce62-4dc9-b34b-1d810d2b1477":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A3","B3","C3"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"5","id":"99090b3b-ce62-4dc9-b34b-1d810d2b1477","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1C2","stepDetails":"","stepNumber":0},"1aab84ae-6e5d-484c-b832-0b4bfa98841d":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A4"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4","B4","C4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"5","id":"1aab84ae-6e5d-484c-b832-0b4bfa98841d","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1C3","stepDetails":"","stepNumber":0},"6ef3150f-0f8a-4c25-b287-c8858eb03084":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A5"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A5","B5","C5"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"5","id":"6ef3150f-0f8a-4c25-b287-c8858eb03084","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1C4","stepDetails":"","stepNumber":0},"cdd66e12-b204-45c5-9c63-cde4c3f300db":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A6","B6","C6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B1"]],"volume":"5","id":"cdd66e12-b204-45c5-9c63-cde4c3f300db","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1C5","stepDetails":"","stepNumber":0},"744d3f85-329b-4bad-8395-73651283e1bc":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D1","E1","F1","D2","E2","F2","D3","E3","F3","D4","E4","F4","D5","E5","F5","D6","E6","F6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["C1"]],"volume":"500","id":"744d3f85-329b-4bad-8395-73651283e1bc","stepType":"moveLiquid","stepName":"Removing Media S2 ALL","stepDetails":"","stepNumber":0},"f5fb7814-5f30-4bfb-82c2-58cd59ec65b9":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D1","E1","F1","D2","E2","F2","D3","E3","F3","D4","E4","F4","D5","E5","F5","D6","E6","F6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"495","id":"f5fb7814-5f30-4bfb-82c2-58cd59ec65b9","stepType":"moveLiquid","stepName":"Adding Media 495 S2","stepDetails":"","stepNumber":0},"140dac96-4c38-415a-815f-8ba568e9d133":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B1"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D1","E1","F1"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"5","id":"140dac96-4c38-415a-815f-8ba568e9d133","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1 No Drug","stepDetails":"","stepNumber":0},"e79e0bb6-b984-4f02-8f45-2a645ab97a4b":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B2"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D2","F2","E2"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"5","id":"e79e0bb6-b984-4f02-8f45-2a645ab97a4b","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C1","stepDetails":"","stepNumber":0},"80258b5c-f7b8-44b6-94b0-caa4f4760508":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D3","E3","F3"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"5","id":"80258b5c-f7b8-44b6-94b0-caa4f4760508","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C2","stepDetails":"","stepNumber":0},"a5a22d74-c93a-49d3-bcff-bc8ed7dbe804":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B4"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D4","F4","E4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"5","id":"a5a22d74-c93a-49d3-bcff-bc8ed7dbe804","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C3","stepDetails":"","stepNumber":0},"66155918-762f-4987-8dd7-eec9e1df1c7e":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B5"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D5","E5","F5"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"5","id":"66155918-762f-4987-8dd7-eec9e1df1c7e","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C4","stepDetails":"","stepNumber":0},"341a3add-1606-429a-81f2-8c55fcbc696f":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["D6","E6","F6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["D1"]],"volume":"5","id":"341a3add-1606-429a-81f2-8c55fcbc696f","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C5","stepDetails":"","stepNumber":0},"b7ada2b0-f07a-4808-86e5-69dd12e9e648":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["G1","H1","G2","H2","G3","H3","G4","H4","G5","H5","G6","H6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["E1"]],"volume":"500","id":"b7ada2b0-f07a-4808-86e5-69dd12e9e648","stepType":"moveLiquid","stepName":"Removing Media S3 2 Row","stepDetails":"","stepNumber":0},"98f160ef-18b2-4839-bddd-2c2c5d4abd77":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G1","H1","G2","H2","G3","H3","G4","H4","G5","H5","G6","H6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"495","id":"98f160ef-18b2-4839-bddd-2c2c5d4abd77","stepType":"moveLiquid","stepName":"Adding Media 495 S3 2 Row","stepDetails":"","stepNumber":0},"eebdfbd8-e207-496c-b220-b09ffae36c24":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C1"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G1","H1"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"eebdfbd8-e207-496c-b220-b09ffae36c24","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3 No Drug 2Row","stepDetails":"","stepNumber":0},"8f19ede2-0a5a-4bf8-b206-1b701acd70e9":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C2"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G2","H2"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"8f19ede2-0a5a-4bf8-b206-1b701acd70e9","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C1","stepDetails":"","stepNumber":0},"66539543-df5e-44f5-923d-8c899acee3dd":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G3","H3"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"66539543-df5e-44f5-923d-8c899acee3dd","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C2","stepDetails":"","stepNumber":0},"89a97929-7443-4ac0-8359-e966d3f3d80a":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C4"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G4","H4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"89a97929-7443-4ac0-8359-e966d3f3d80a","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C3 2 Row","stepDetails":"","stepNumber":0},"91a7a7e8-1d4d-421b-9dd4-6f0c9c4b02bd":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C5"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G5","H5"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"91a7a7e8-1d4d-421b-9dd4-6f0c9c4b02bd","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C4 2Row","stepDetails":"","stepNumber":0},"7ee627b3-5d49-45c1-a28b-26dbdfc27d22":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["G6","H6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"7ee627b3-5d49-45c1-a28b-26dbdfc27d22","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C5 2 Row","stepDetails":"","stepNumber":0},"7829b718-bafd-44c8-aa15-5fd1464c3d0e":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["A1","A2","A3","A4","A5","A6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["E1"]],"volume":"500","id":"7829b718-bafd-44c8-aa15-5fd1464c3d0e","stepType":"moveLiquid","stepName":"Removing Media S3 1 Row","stepDetails":"","stepNumber":0},"77f6a9bb-c0d6-4705-9239-c03f7e2b4989":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A1","A2","A3","A4","A5","A6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"495","id":"77f6a9bb-c0d6-4705-9239-c03f7e2b4989","stepType":"moveLiquid","stepName":"Adding Media 495 S3 1 Row","stepDetails":"","stepNumber":0},"80ff3090-39f0-4dca-b547-da4cbd3c31ed":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C1"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A1"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"80ff3090-39f0-4dca-b547-da4cbd3c31ed","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S1 No Drug 1 Row","stepDetails":"","stepNumber":0},"9e5afeb0-1581-4ae0-a6c9-08cd952ff727":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B1","C1","D1","B2","C2","D2","B3","C3","D3","B4","C4","D4","B5","C5","D5","B6","C6","D6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["G1"]],"volume":"500","id":"9e5afeb0-1581-4ae0-a6c9-08cd952ff727","stepType":"moveLiquid","stepName":"Removing Media S4","stepDetails":"","stepNumber":0},"3d3995cb-6295-4f19-9eb3-dce8cfb18924":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B1","C1","D1","B2","C2","D2","B3","C3","D3","B4","C4","D4","B5","C5","D5","B6","C6","D6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"495","id":"3d3995cb-6295-4f19-9eb3-dce8cfb18924","stepType":"moveLiquid","stepName":"Adding Media 495 S4 ","stepDetails":"","stepNumber":0},"12575b98-f7d1-4494-b7d6-278e2a141c35":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D1"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B1","C1","D1"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"5","id":"12575b98-f7d1-4494-b7d6-278e2a141c35","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S4 No Drug ","stepDetails":"","stepNumber":0},"9793e578-4907-456e-92c4-b1d292a05372":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D2"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B2","C2","D2"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"5","id":"9793e578-4907-456e-92c4-b1d292a05372","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S4C1","stepDetails":"","stepNumber":0},"5ff436c4-4002-43f4-a089-55508b0e570a":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B3","C3","D3"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"5","id":"5ff436c4-4002-43f4-a089-55508b0e570a","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S4C2","stepDetails":"","stepNumber":0},"047f922e-b745-4167-a334-585ebeb54f82":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D4"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B4","C4","D4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"5","id":"047f922e-b745-4167-a334-585ebeb54f82","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S4C3","stepDetails":"","stepNumber":0},"c25375d0-0753-4d8f-a9f7-379dccec3a0a":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D5"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B5","C5","D5"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"5","id":"c25375d0-0753-4d8f-a9f7-379dccec3a0a","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S4C4","stepDetails":"","stepNumber":0},"5e7b250f-0d2c-4d31-af10-2652696d166a":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["B6","C6","D6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["H1"]],"volume":"5","id":"5e7b250f-0d2c-4d31-af10-2652696d166a","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S4C5 ","stepDetails":"","stepNumber":0},"48264b14-3b03-411f-9306-32d949487bca":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["E1","F1","G1","E2","F2","G2","E3","F3","G3","E4","F4","G4","E5","F5","G5","E6","F6","G6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["A2"]],"volume":"500","id":"48264b14-3b03-411f-9306-32d949487bca","stepType":"moveLiquid","stepName":"Removing Media S5","stepDetails":"","stepNumber":0},"3a7bd32f-6a32-4a82-95eb-4555d41749f0":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["B3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":null,"blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":"","dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E1","F1","G1","E2","F2","G2","E3","F3","G3","E4","F4","G4","E5","F5","G5","E6","F6","G6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"495","id":"3a7bd32f-6a32-4a82-95eb-4555d41749f0","stepType":"moveLiquid","stepName":"Adding Media 495 S5","stepDetails":"","stepNumber":0},"39d623fa-c685-4a16-bb8f-55d4442fcca3":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["E1"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E1","F1","G1"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"5","id":"39d623fa-c685-4a16-bb8f-55d4442fcca3","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S5 No Drug ","stepDetails":"","stepNumber":0},"09c3c729-5e29-4c81-a51f-796781fd688f":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["E2"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E2","F2","G2"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"5","id":"09c3c729-5e29-4c81-a51f-796781fd688f","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S5C1","stepDetails":"","stepNumber":0},"8a6a9c3a-3454-4c61-8657-44dde878fc56":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["E3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E3","F3","G3"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"5","id":"8a6a9c3a-3454-4c61-8657-44dde878fc56","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S5C2","stepDetails":"","stepNumber":0},"2c2d563c-a99b-475c-b717-59cd1c5eaa53":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["E4"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E4","F4","G4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"5","id":"2c2d563c-a99b-475c-b717-59cd1c5eaa53","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S5C3","stepDetails":"","stepNumber":0},"5e00290d-eb5a-4414-947b-5d4562d36fca":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["D6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E5","F5","G5"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"5","id":"5e00290d-eb5a-4414-947b-5d4562d36fca","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S5C4","stepDetails":"","stepNumber":0},"fd01f9b3-221d-4e84-890d-05ee25a0d45d":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["E6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["E6","F6","G6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":true,"disposalVolume_volume":"30","dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"multiDispense","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["B2"]],"volume":"5","id":"fd01f9b3-221d-4e84-890d-05ee25a0d45d","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S5C5 ","stepDetails":"","stepNumber":0},"222b8fe4-bb6f-4df1-833c-e221f7888259":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C2"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A2"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"222b8fe4-bb6f-4df1-833c-e221f7888259","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C1 1Row","stepDetails":"","stepNumber":0},"3303b89b-119f-4b5f-a0eb-14cc4a3b45f0":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C3"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A3"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"3303b89b-119f-4b5f-a0eb-14cc4a3b45f0","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S2C2 1 Row","stepDetails":"","stepNumber":0},"95c190bf-a41c-433e-a3c9-710c3fa41b66":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C4"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A4"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"95c190bf-a41c-433e-a3c9-710c3fa41b66","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C3 1 Row","stepDetails":"","stepNumber":0},"0767c06c-a7ae-44e9-a511-706cd06783ac":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C5"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A5"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"0767c06c-a7ae-44e9-a511-706cd06783ac","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C4 1 Row","stepDetails":"","stepNumber":0},"5fd62ee8-c3d2-4a35-ac3c-0f381f2787d3":{"aspirate_airGap_checkbox":false,"aspirate_airGap_volume":"","aspirate_delay_checkbox":false,"aspirate_delay_seconds":"1","aspirate_flowRate":"150","aspirate_labware":"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1","aspirate_mix_checkbox":false,"aspirate_mix_times":"","aspirate_mix_volume":null,"aspirate_mmFromBottom":null,"aspirate_position_reference":"well-bottom","aspirate_retract_delay_seconds":"0","aspirate_retract_mmFromBottom":2,"aspirate_retract_speed":"125","aspirate_retract_x_position":0,"aspirate_retract_y_position":0,"aspirate_retract_position_reference":"well-top","aspirate_submerge_delay_seconds":"0","aspirate_submerge_speed":"125","aspirate_submerge_mmFromBottom":2,"aspirate_submerge_x_position":0,"aspirate_submerge_y_position":0,"aspirate_submerge_position_reference":"well-top","aspirate_touchTip_checkbox":false,"aspirate_touchTip_mmFromTop":null,"aspirate_touchTip_speed":60,"aspirate_touchTip_mmFromEdge":0,"aspirate_wellOrder_first":"t2b","aspirate_wellOrder_second":"l2r","aspirate_wells_grouped":false,"aspirate_wells":["C6"],"aspirate_x_position":0,"aspirate_y_position":0,"blowout_checkbox":false,"blowout_flowRate":"1000","blowout_location":"source_well","blowout_mmFromBottom":null,"blowout_x_position":null,"blowout_y_position":null,"blowout_position_reference":"well-top","changeTip":"once","conditioning_checkbox":false,"conditioning_volume":null,"dispense_airGap_checkbox":false,"dispense_airGap_volume":"","dispense_delay_checkbox":false,"dispense_delay_seconds":"1","dispense_flowRate":"300","dispense_labware":"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1","dispense_mix_checkbox":false,"dispense_mix_times":null,"dispense_mix_volume":null,"dispense_mmFromBottom":null,"dispense_position_reference":"well-bottom","dispense_retract_delay_seconds":"0","dispense_retract_mmFromBottom":2,"dispense_retract_speed":"125","dispense_retract_x_position":0,"dispense_retract_y_position":0,"dispense_retract_position_reference":"well-top","dispense_submerge_delay_seconds":"0","dispense_submerge_speed":"125","dispense_submerge_mmFromBottom":2,"dispense_submerge_x_position":0,"dispense_submerge_y_position":0,"dispense_submerge_position_reference":"well-top","dispense_touchTip_checkbox":false,"dispense_touchTip_mmFromTop":null,"dispense_touchTip_speed":60,"dispense_touchTip_mmFromEdge":0,"dispense_wellOrder_first":"t2b","dispense_wellOrder_second":"l2r","dispense_wells":["A6"],"dispense_x_position":0,"dispense_y_position":0,"disposalVolume_checkbox":false,"disposalVolume_volume":null,"dropTip_location":"opentrons/opentrons_96_tiprack_300ul/1","liquidClassesSupported":true,"liquidClass":"none","nozzles":"ALL","path":"single","pipette":"08b41b2f-6dbd-4954-af18-9c4bc803b76a","preWetTip":false,"primaryNozzle":"A1","pushOut_checkbox":false,"pushOut_volume":"0","tipRack":"opentrons/opentrons_96_tiprack_300ul/1","tip_tracking":"manual","tiprack_selected":"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1","tips_selected":[["F1"]],"volume":"5","id":"5fd62ee8-c3d2-4a35-ac3c-0f381f2787d3","stepType":"moveLiquid","stepName":"Adding DMSO-DRUG S3C5 1 Row","stepDetails":"","stepNumber":0}},"orderedStepIds":["84fc9262-751e-4f2c-a423-7e0bac49dab5","641328e2-911f-434e-b6b0-e3a8cbe60650","c2d008ed-7143-47e8-918e-b3fedd80c95b","03f5c66d-3165-4632-a5b5-c1624f8aa752","99090b3b-ce62-4dc9-b34b-1d810d2b1477","1aab84ae-6e5d-484c-b832-0b4bfa98841d","6ef3150f-0f8a-4c25-b287-c8858eb03084","cdd66e12-b204-45c5-9c63-cde4c3f300db","744d3f85-329b-4bad-8395-73651283e1bc","f5fb7814-5f30-4bfb-82c2-58cd59ec65b9","140dac96-4c38-415a-815f-8ba568e9d133","e79e0bb6-b984-4f02-8f45-2a645ab97a4b","80258b5c-f7b8-44b6-94b0-caa4f4760508","a5a22d74-c93a-49d3-bcff-bc8ed7dbe804","66155918-762f-4987-8dd7-eec9e1df1c7e","341a3add-1606-429a-81f2-8c55fcbc696f","b7ada2b0-f07a-4808-86e5-69dd12e9e648","7829b718-bafd-44c8-aa15-5fd1464c3d0e","98f160ef-18b2-4839-bddd-2c2c5d4abd77","77f6a9bb-c0d6-4705-9239-c03f7e2b4989","eebdfbd8-e207-496c-b220-b09ffae36c24","80ff3090-39f0-4dca-b547-da4cbd3c31ed","8f19ede2-0a5a-4bf8-b206-1b701acd70e9","222b8fe4-bb6f-4df1-833c-e221f7888259","66539543-df5e-44f5-923d-8c899acee3dd","3303b89b-119f-4b5f-a0eb-14cc4a3b45f0","89a97929-7443-4ac0-8359-e966d3f3d80a","95c190bf-a41c-433e-a3c9-710c3fa41b66","91a7a7e8-1d4d-421b-9dd4-6f0c9c4b02bd","0767c06c-a7ae-44e9-a511-706cd06783ac","7ee627b3-5d49-45c1-a28b-26dbdfc27d22","5fd62ee8-c3d2-4a35-ac3c-0f381f2787d3","9e5afeb0-1581-4ae0-a6c9-08cd952ff727","3d3995cb-6295-4f19-9eb3-dce8cfb18924","12575b98-f7d1-4494-b7d6-278e2a141c35","9793e578-4907-456e-92c4-b1d292a05372","5ff436c4-4002-43f4-a089-55508b0e570a","047f922e-b745-4167-a334-585ebeb54f82","c25375d0-0753-4d8f-a9f7-379dccec3a0a","5e7b250f-0d2c-4d31-af10-2652696d166a","48264b14-3b03-411f-9306-32d949487bca","3a7bd32f-6a32-4a82-95eb-4555d41749f0","39d623fa-c685-4a16-bb8f-55d4442fcca3","09c3c729-5e29-4c81-a51f-796781fd688f","8a6a9c3a-3454-4c61-8657-44dde878fc56","2c2d563c-a99b-475c-b717-59cd1c5eaa53","5e00290d-eb5a-4414-947b-5d4562d36fca","fd01f9b3-221d-4e84-890d-05ee25a0d45d"],"pipettes":{"08b41b2f-6dbd-4954-af18-9c4bc803b76a":{"pipetteName":"p300_single"}},"modules":{},"labware":{"2ca47d79-7c45-46ae-966a-50b5b6a89ed0:opentrons/opentrons_96_tiprack_300ul/1":{"displayName":"Opentrons OT-2 96 Tip Rack 300 µL (1)","labwareDefURI":"opentrons/opentrons_96_tiprack_300ul/1"},"b0faf5c1-28c3-44c5-b739-d267422ab200:custom_beta/myriamed_48_wellplate_800ul/1":{"displayName":"Myriamed 48 Well Plate 800 µL","labwareDefURI":"custom_beta/myriamed_48_wellplate_800ul/1"},"6735ff7b-37df-4fef-9094-60725ab6012c:custom_beta/myriamed_48_wellplate_800ul/1":{"displayName":"Myriamed 48 Well Plate 800 µL (1)","labwareDefURI":"custom_beta/myriamed_48_wellplate_800ul/1"},"fea6c281-9754-4c58-9260-0f02fc833de9:opentrons/nunc_96_wellplate_450ul/1":{"displayName":"Nunc 96 Well Plate 450 µL","labwareDefURI":"opentrons/nunc_96_wellplate_450ul/1"},"ee4c64e4-d676-4429-8738-54cc1d6c3841:opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2":{"displayName":"Opentrons 10 Tube Rack with NEST 4x50 mL, 6x15 mL Conical","labwareDefURI":"opentrons/opentrons_10_tuberack_nest_4x50ml_6x15ml_conical/2"}}}},"metadata":{"protocolName":"EHM Media Change and Drug addition","author":"","description":"","source":"Protocol Designer","created":1791373762533,"lastModified":1792576453367}}"""

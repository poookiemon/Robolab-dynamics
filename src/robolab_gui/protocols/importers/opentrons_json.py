"""Opentrons JSON protocol format importer."""

import json
from pathlib import Path
from typing import Union
from robolab_gui.protocols.models import Protocol, ProtocolStep
from robolab_gui.protocols.importers.mappings import map_opentrons_slot


class OpentronsJSONImporter:
    """Converts Opentrons JSON protocols into RoboLab Protocol objects."""

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> Protocol:
        p = Path(file_path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        steps = []
        commands = data.get("commands", [])
        for cmd in commands:
            c_type = cmd.get("command", "")
            params = cmd.get("params", {})
            if "pickUpTip" in c_type:
                steps.append(ProtocolStep(
                    action="Pick Up Tip",
                    slot=map_opentrons_slot(params.get("pipette", "4")),
                    well=params.get("well", "A1"),
                ))
            elif "aspirate" in c_type:
                steps.append(ProtocolStep(
                    action="Aspirate Media",
                    slot=map_opentrons_slot(params.get("slot", "3")),
                    well=params.get("well", "A1"),
                    volume=float(params.get("volume", 0.0)),
                ))
            elif "dispense" in c_type:
                steps.append(ProtocolStep(
                    action="Dispense Media",
                    slot=map_opentrons_slot(params.get("slot", "5")),
                    well=params.get("well", "A1"),
                    volume=float(params.get("volume", 0.0)),
                ))
            elif "dropTip" in c_type:
                steps.append(ProtocolStep(
                    action="Discard Tip",
                    slot="Slot_2",
                    well="A1",
                ))

        return Protocol(
            name=p.stem,
            description="Imported from Opentrons JSON",
            steps=steps,
        )

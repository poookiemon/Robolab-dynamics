"""Opentrons Python protocol importer and AST interpreter."""

import re
from pathlib import Path
from typing import Union
from robolab_gui.protocols.models import Protocol, ProtocolStep
from robolab_gui.protocols.importers.mappings import map_opentrons_slot


class OpentronsPythonImporter:
    """Extracts transfer actions from Opentrons Python protocol scripts."""

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> Protocol:
        p = Path(file_path)
        content = p.read_text(encoding="utf-8")
        steps = []

        # Find simple transfers: transfer(volume, source, dest)
        transfers = re.findall(r"transfer\(\s*([\d\.]+)\s*,\s*([^,]+),\s*([^\)]+)\)", content)
        for vol_str, src, dst in transfers:
            try:
                v = float(vol_str)
            except ValueError:
                v = 10.0
            steps.append(ProtocolStep(action="Pick Up Tip", slot="Slot_4", well="A1"))
            steps.append(ProtocolStep(action="Aspirate Media", slot="Slot_3", well="A1", volume=v))
            steps.append(ProtocolStep(action="Dispense Media", slot="Slot_5", well="A1", volume=v))
            steps.append(ProtocolStep(action="Discard Tip", slot="Slot_2", well="A1"))

        return Protocol(
            name=p.stem,
            description="Imported from Opentrons Python script",
            steps=steps,
        )

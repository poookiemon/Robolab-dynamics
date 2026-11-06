"""Serial dilution protocol builders."""

from typing import List
from robolab_gui.protocols.models import ProtocolStep


def build_serial_dilution_steps(
    transfer_vol_ul: float = 24.0,
    dmso_vol_ul: float = 24.0,
    dilution_factors: int = 6,
    mix_cycles: int = 5,
    mix_vol_ul: float = 40.0,
) -> List[ProtocolStep]:
    """Build multi-step serial dilution across a 96-well plate column."""
    steps: List[ProtocolStep] = []
    # Load DMSO diluent
    for i in range(1, dilution_factors + 1):
        steps.append(ProtocolStep(
            action="Pick Up Tip",
            slot="Slot_4",
            well=f"A{i}",
            volume=0.0,
            labware="tip_rack_300ul.json",
            label=f"[PICK] Dilution Tip {i}",
        ))
        steps.append(ProtocolStep(
            action="Aspirate Media",
            slot="Slot_1",
            well="A1",
            volume=dmso_vol_ul,
            labware="reservoir_3_well.json",
            label=f"[ASP] {dmso_vol_ul}uL DMSO",
        ))
        steps.append(ProtocolStep(
            action="Dispense Media",
            slot="Slot_5",
            well=f"A{i}",
            volume=dmso_vol_ul,
            labware="generic_96_well_plate.json",
            label=f"[DISP] DMSO to Well A{i}",
        ))
        steps.append(ProtocolStep(
            action="Discard Tip",
            slot="Slot_2",
            well="A1",
            volume=0.0,
            labware="waste_trough.json",
            label="[DISCARD] Tip to Slot 2",
        ))
    return steps

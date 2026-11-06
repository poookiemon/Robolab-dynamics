"""Calcium curve and FOC automation assay builders."""

from typing import List
from robolab_gui.protocols.models import ProtocolStep


def build_calcium_assay_steps(
    calcium_concentrations_ul: List[float] = None,
    source_slot: str = "Slot_1",
    target_slot: str = "Slot_5",
) -> List[ProtocolStep]:
    """Build steps for calcium concentration titration curve."""
    concs = calcium_concentrations_ul or [1.0, 2.5, 5.0, 10.0, 20.0]
    steps: List[ProtocolStep] = []

    for idx, vol in enumerate(concs):
        steps.append(ProtocolStep(
            action="Pick Up Tip",
            slot="Slot_4",
            well=f"A{idx + 1}",
            volume=0.0,
            labware="tip_rack_300ul.json",
            label=f"[PICK] Calcium Addition Tip {idx + 1}",
        ))
        steps.append(ProtocolStep(
            action="Aspirate Media",
            slot=source_slot,
            well=f"A{idx + 1}",
            volume=vol,
            labware="reservoir_6_column.json",
            label=f"[ASP] {vol}uL Calcium Stock {idx + 1}",
        ))
        steps.append(ProtocolStep(
            action="Dispense Media",
            slot=target_slot,
            well=f"A{idx + 1}",
            volume=vol,
            labware="myriamed_48_well.json",
            mix_cycles=2,
            mix_volume_ul=40.0,
            label=f"[DISP] Add to Well A{idx + 1}",
        ))
        steps.append(ProtocolStep(
            action="Discard Tip",
            slot="Slot_2",
            well="A1",
            volume=0.0,
            labware="waste_trough.json",
            label="[DISCARD] Discard Tip",
        ))
    return steps

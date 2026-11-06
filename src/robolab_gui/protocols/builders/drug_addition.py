"""Drug addition protocol builders for single-channel and multi-tip configurations."""

from typing import List, Dict, Any
from robolab_gui.protocols.models import ProtocolStep


def build_drug_addition_steps(
    drug_vol_ul: float = 7.5,
    drug_source_slot: str = "Slot_3",
    destination_slot: str = "Slot_5",
    drug_wells: List[str] = None,
    mix_cycles: int = 3,
    mix_vol_ul: float = 50.0,
) -> List[ProtocolStep]:
    """Build drug addition and in-place mixing steps."""
    steps: List[ProtocolStep] = []
    wells = drug_wells or ["A1", "A2", "A3", "A4", "A5"]

    for idx, well in enumerate(wells):
        # Pick tip
        steps.append(ProtocolStep(
            action="Pick Up Tip",
            slot="Slot_4",
            well=f"A{idx + 1}",
            volume=0.0,
            labware="tip_rack_10ul.json",
            label=f"[PICK] Tip for Condition {idx + 1}",
        ))
        # Aspirate drug
        steps.append(ProtocolStep(
            action="Aspirate Media",
            slot=drug_source_slot,
            well=well,
            volume=drug_vol_ul,
            labware="generic_96_well_plate.json",
            label=f"[ASP] {drug_vol_ul:.1f}uL Drug {idx + 1} from {well}",
        ))
        # Dispense into target column
        steps.append(ProtocolStep(
            action="Dispense Media",
            slot=destination_slot,
            well=f"A{idx + 1}",
            volume=drug_vol_ul,
            labware="myriamed_48_well.json",
            mix_cycles=mix_cycles,
            mix_volume_ul=mix_vol_ul,
            label=f"[DISP+MIX] Drug {idx + 1} into Col {idx + 1}",
        ))
        # Discard tip to waste trough Slot 2 Well A1
        steps.append(ProtocolStep(
            action="Discard Tip",
            slot="Slot_2",
            well="A1",
            volume=0.0,
            labware="waste_trough.json",
            label="[DISCARD] Tip to Slot 2 Waste Trough",
        ))

    return steps

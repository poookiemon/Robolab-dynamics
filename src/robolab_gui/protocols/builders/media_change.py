"""Media change protocol builders for 8-channel and single-channel heads."""

from typing import List, Dict, Any, Optional
from robolab_gui.protocols.models import Protocol, ProtocolStep


def build_8ch_media_change_steps(
    remove_vol_ul: float = 500.0,
    fresh_vol_ul: float = 500.0,
    include_removal: bool = True,
    p5_fresh_lane: int = 6,
    p6_fresh_lane: int = 7,
    p5_waste_lane: int = 1,
    p6_waste_lane: int = 2,
    reservoir_labware: str = "reservoir_7_column.json",
) -> List[ProtocolStep]:
    """Build 8-channel media change steps for Plate 5 (Slot 3) and Plate 6 (Slot 5)."""
    steps: List[ProtocolStep] = []

    # 1. PLATE 5 (Slot 3)
    if include_removal:
        steps.append(ProtocolStep(
            action="Pick Up Tip",
            slot="Slot_4",
            well="A1",
            volume=0.0,
            labware="tip_rack_1000ul.json",
            eight_ch_symmetric=True,
            mounted_channels="A-H",
            label="[PICK 8-CH] Slot_4 Col 1 (A1-H1) | Plate 5 Removal",
        ))
        for col in range(1, 7):
            steps.append(ProtocolStep(
                action="Aspirate Media",
                slot="Slot_3",
                well=f"A{col}",
                volume=remove_vol_ul,
                labware="myriamed_48_well.json",
                eight_ch_symmetric=True,
                mounted_channels="A-H",
                label=f"[REMOVE 8-CH] Plate 5 Col {col}",
            ))
            steps.append(ProtocolStep(
                action="Dispense Media",
                slot="Slot_6",
                well=f"A{p5_waste_lane}",
                volume=remove_vol_ul,
                labware=reservoir_labware,
                eight_ch_symmetric=True,
                mounted_channels="A-H",
                label=f"[WASTE 8-CH] Discard to Slot 6 Lane {p5_waste_lane}",
            ))
        steps.append(ProtocolStep(
            action="Discard Tip",
            slot="Slot_4",
            well="A12",
            volume=0.0,
            labware="tip_rack_1000ul.json",
            eight_ch_symmetric=True,
            mounted_channels="A-H",
            label="[DROP 8-CH] Return to Slot 4 Graveyard Col 12",
        ))

    # Fresh media addition Plate 5
    steps.append(ProtocolStep(
        action="Pick Up Tip",
        slot="Slot_4",
        well="A2",
        volume=0.0,
        labware="tip_rack_1000ul.json",
        eight_ch_symmetric=True,
        mounted_channels="A-H",
        label="[PICK 8-CH] Slot_4 Col 2 (A1-H1) | Plate 5 Fresh Media",
    ))
    for col in range(1, 7):
        steps.append(ProtocolStep(
            action="Aspirate Media",
            slot="Slot_6",
            well=f"A{p5_fresh_lane}",
            volume=fresh_vol_ul,
            labware=reservoir_labware,
            eight_ch_symmetric=True,
            mounted_channels="A-H",
            label=f"[FRESH 8-CH] Aspirate from Slot 6 Lane {p5_fresh_lane}",
        ))
        steps.append(ProtocolStep(
            action="Dispense Media",
            slot="Slot_3",
            well=f"A{col}",
            volume=fresh_vol_ul,
            labware="myriamed_48_well.json",
            eight_ch_symmetric=True,
            mounted_channels="A-H",
            label=f"[ADD 8-CH] Add fresh media to Plate 5 Col {col}",
        ))
    steps.append(ProtocolStep(
        action="Discard Tip",
        slot="Slot_4",
        well="A11",
        volume=0.0,
        labware="tip_rack_1000ul.json",
        eight_ch_symmetric=True,
        mounted_channels="A-H",
        label="[DROP 8-CH] Return to Slot 4 Graveyard Col 11",
    ))

    return steps

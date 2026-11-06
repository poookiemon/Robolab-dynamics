"""Nozzle geometry, manifold footprint, channel masks, and multi-tip centering.

Ensures that 8-channel and partial-channel (e.g. 5-tip A-E) pipetting operations
are perfectly aligned to well columns and rack wells without colliding with partition walls.
"""

from typing import List, Dict, Optional, Tuple, Set


class NozzleLayout:
    """Calculates carriage and nozzle physical coordinates for 1-channel and 8-channel heads."""

    NOZZLE_PITCH_MM: float = 9.0
    TOTAL_CHANNELS: int = 8
    MANIFOLD_HALF_SPAN_MM: float = 31.50
    DEFAULT_8CH_CENTER_Y: float = 84.52

    ROW_LETTERS: List[str] = ["A", "B", "C", "D", "E", "F", "G", "H"]

    @classmethod
    def parse_channel_mask(cls, mounted_channels: Optional[str]) -> List[int]:
        if not mounted_channels:
            return [0]

        s = str(mounted_channels).strip().upper()
        if s in ("A-H", "ALL", "8", "8CH", "8-CHANNEL"):
            return list(range(8))
        if s in ("A-E", "5", "5CH", "5-TIP"):
            return list(range(5))
        if s in ("A-D", "4", "4CH"):
            return list(range(4))

        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2 and parts[0] in cls.ROW_LETTERS and parts[1] in cls.ROW_LETTERS:
                start = cls.ROW_LETTERS.index(parts[0])
                end = cls.ROW_LETTERS.index(parts[1])
                return list(range(min(start, end), max(start, end) + 1))

        if s in cls.ROW_LETTERS:
            return [cls.ROW_LETTERS.index(s)]

        if s.isdigit():
            val = int(s) - 1
            if 0 <= val < 8:
                return [val]

        return [0]

    @classmethod
    def is_multi_channel(cls, mounted_channels: Optional[str], eight_ch_symmetric: bool = False) -> bool:
        if eight_ch_symmetric:
            return True
        mask = cls.parse_channel_mask(mounted_channels)
        return len(mask) > 1

    @classmethod
    def get_carriage_y_for_manifold(
        cls,
        target_a1_y: float,
        mounted_channels: Optional[str] = None,
        eight_ch_symmetric: bool = False,
        is_8ch_head: bool = True,
        tip_offset_rows: int = 0,
        slot_name: str = "Slot_4",
    ) -> float:
        multi = cls.is_multi_channel(mounted_channels, eight_ch_symmetric)

        if not is_8ch_head:
            return target_a1_y + (tip_offset_rows * cls.NOZZLE_PITCH_MM)

        if multi:
            if slot_name in ("Slot_3", "Slot_4"):
                base_y = cls.DEFAULT_8CH_CENTER_Y
            elif slot_name in ("Slot_5", "Slot_6"):
                base_y = 178.69
            else:
                base_y = target_a1_y + cls.MANIFOLD_HALF_SPAN_MM

            return base_y + (tip_offset_rows * cls.NOZZLE_PITCH_MM)
        else:
            return target_a1_y + cls.MANIFOLD_HALF_SPAN_MM + (tip_offset_rows * cls.NOZZLE_PITCH_MM)

    @classmethod
    def get_nozzle_positions_y(cls, carriage_y: float) -> List[float]:
        start_y = carriage_y - cls.MANIFOLD_HALF_SPAN_MM
        return [round(start_y + (i * cls.NOZZLE_PITCH_MM), 2) for i in range(cls.TOTAL_CHANNELS)]

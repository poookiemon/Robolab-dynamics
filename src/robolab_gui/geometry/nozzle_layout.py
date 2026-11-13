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

    @staticmethod
    def m2_slot4_tip_base_xy(tip_count: int) -> Tuple[float, float]:
        """Return Slot 4 Col 1 base (X, Y) for Machine 2 (1-10 uL) for 1..8 tips."""
        n = max(1, min(8, int(tip_count)))
        if n <= 5:
            t = (n - 1) / 4.0
            bx = 105.66
            by = round(21.53 + t * (56.83 - 21.53) + 1e-9, 2)
        else:
            t = (n - 5) / 3.0
            bx = round(105.66 + t * (105.47 - 105.66), 2)
            by = round(56.83 + t * (84.99 - 56.83), 2)
        return bx, by

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
        is_10ul: bool = False,
    ) -> float:
        multi = cls.is_multi_channel(mounted_channels, eight_ch_symmetric)

        if not is_8ch_head:
            return target_a1_y + (tip_offset_rows * cls.NOZZLE_PITCH_MM)

        if multi:
            if is_10ul and slot_name == "Slot_4":
                # Machine 2 (1-10 µL): Physically verified seated coordinates
                # 1 tip: Y=21.53mm | 5 tips (Rows A-E): Y=56.83mm | 8 tips: Y=84.99mm
                mask = cls.parse_channel_mask(mounted_channels)
                num_tips = len(mask) if mask else 8
                _, base_y = cls.m2_slot4_tip_base_xy(num_tips)
            elif is_10ul and slot_name == "Slot_3":
                mask = cls.parse_channel_mask(mounted_channels)
                num_tips = len(mask) if mask else 8
                if num_tips == 5:
                    base_y = 57.12
                elif num_tips == 8:
                    base_y = 84.14
                else:
                    base_y = round(84.14 - (8 - num_tips) * 9.06, 2)
            elif is_10ul and slot_name in ("Slot_5", "Slot_6"):
                mask = cls.parse_channel_mask(mounted_channels)
                num_tips = len(mask) if mask else 8
                if num_tips == 5:
                    base_y = round(56.96 + 94.17, 2)
                elif num_tips == 8:
                    base_y = 178.31
                else:
                    base_y = round(178.31 - (8 - num_tips) * 9.06, 2)
            elif slot_name in ("Slot_3", "Slot_4"):
                base_y = cls.DEFAULT_8CH_CENTER_Y
            elif slot_name in ("Slot_5", "Slot_6"):
                base_y = 178.69
            else:
                base_y = target_a1_y + cls.MANIFOLD_HALF_SPAN_MM

            return base_y + (tip_offset_rows * cls.NOZZLE_PITCH_MM)
        else:
            if is_10ul and slot_name == "Slot_4":
                _, base_y = cls.m2_slot4_tip_base_xy(1 + tip_offset_rows)
                return base_y
            elif is_10ul and slot_name == "Slot_3":
                return round(84.14 + (tip_offset_rows * cls.NOZZLE_PITCH_MM), 2)
            elif is_10ul and slot_name in ("Slot_5", "Slot_6"):
                return round(178.31 + (tip_offset_rows * cls.NOZZLE_PITCH_MM), 2)
            return target_a1_y + cls.MANIFOLD_HALF_SPAN_MM + (tip_offset_rows * cls.NOZZLE_PITCH_MM)

    @classmethod
    def get_nozzle_positions_y(cls, carriage_y: float) -> List[float]:
        start_y = carriage_y - cls.MANIFOLD_HALF_SPAN_MM
        return [round(start_y + (i * cls.NOZZLE_PITCH_MM), 2) for i in range(cls.TOTAL_CHANNELS)]

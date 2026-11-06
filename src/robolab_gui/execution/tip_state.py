"""Active session tip memory and virtual tip remapping."""

from typing import Dict, List, Optional, Tuple, Set

# Canonical column-major 96-well tip order (A1..H1 -> A2..H2 -> ... -> A12..H12)
TIP_ORDER_96: List[str] = [f"{r}{c}" for c in range(1, 13) for r in "ABCDEFGH"]


class TipStateTracker:
    """Tracks tip consumption and dynamically remaps consumed wells to fresh tips."""

    def __init__(self):
        # slot_name -> set of consumed well strings (e.g. {"A1", "B1"})
        self._consumed: Dict[str, Set[str]] = {}

    def get_consumed_count(self, slot_name: str) -> int:
        return len(self._consumed.get(slot_name, set()))

    def get_remaining_count(self, slot_name: str) -> int:
        return 96 - self.get_consumed_count(slot_name)

    def is_consumed(self, slot_name: str, well_id: str) -> bool:
        return well_id in self._consumed.get(slot_name, set())

    def reset_slot(self, slot_name: str) -> None:
        """Reset tip tracker for a fresh box (0/96 consumed)."""
        self._consumed[slot_name] = set()

    def resolve_next_tip(
        self,
        slot_name: str,
        is_8ch_pickup: bool = False,
        requested_well: Optional[str] = None,
    ) -> Optional[str]:
        """Dynamically resolve next available tip well without modifying protocol files."""
        if slot_name not in self._consumed:
            self._consumed[slot_name] = set()
        consumed = self._consumed[slot_name]

        if is_8ch_pickup:
            # Must find an entire column with 0 tips used (e.g. A1..H1)
            for col in range(1, 13):
                col_wells = [f"{r}{col}" for r in "ABCDEFGH"]
                if not any(w in consumed for w in col_wells):
                    # Consume all 8
                    for w in col_wells:
                        consumed.add(w)
                    return f"A{col}"
            return None  # Tip rack exhausted

        # Single tip pickup in column-major order
        for well in TIP_ORDER_96:
            if well not in consumed:
                consumed.add(well)
                return well

        return None  # Exhausted

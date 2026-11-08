"""Active session tip memory and virtual tip remapping."""

import re
from typing import Dict, List, Optional, Set, Tuple

# Canonical column-major 96-well tip order (A1..H1 -> A2..H2 -> ... -> A12..H12)
TIP_ORDER_96: List[str] = [f"{r}{c}" for c in range(1, 13) for r in "ABCDEFGH"]


class TipStateTracker:
    """Tracks tip consumption and dynamically remaps consumed wells to fresh tips across all machines."""

    def __init__(self):
        # slot_name -> set of consumed well strings (e.g. {"A1", "B1"})
        self._consumed: Dict[str, Set[str]] = {}

    def get_consumed_count(self, slot_name: str) -> int:
        return len(self._consumed.get(slot_name, set()))

    def get_remaining_count(self, slot_name: str) -> int:
        return 96 - self.get_consumed_count(slot_name)

    def is_consumed(self, slot_name: str, well_id: str) -> bool:
        return well_id in self._consumed.get(slot_name, set())

    def mark_consumed(self, slot_name: str, well_id: str) -> None:
        if slot_name not in self._consumed:
            self._consumed[slot_name] = set()
        self._consumed[slot_name].add(well_id.strip().upper())

    def reset_slot(self, slot_name: str) -> None:
        """Reset tip tracker for a fresh box (0/96 consumed)."""
        self._consumed[slot_name] = set()

    @staticmethod
    def expand_8ch_sockets(well_id: str, mounted_channels: Optional[str] = None) -> List[str]:
        """Return physical sockets touched by an 8-channel or partial manifold pickup."""
        m = re.match(r"^[A-H](\d+)$", (well_id or "").strip().upper())
        if not m:
            return []
        col = int(m.group(1))
        if mounted_channels:
            s_mounted = str(mounted_channels).strip().upper()
            if "-" in s_mounted:
                parts = s_mounted.split("-")
                r_start, r_end = parts[0].strip(), parts[1].strip()
                all_rows = "ABCDEFGH"
                if r_start in all_rows and r_end in all_rows:
                    i1, i2 = all_rows.index(r_start), all_rows.index(r_end)
                    return [f"{all_rows[i]}{col}" for i in range(min(i1, i2), max(i1, i2) + 1)]
            else:
                return [f"{s_mounted}{col}"]
        return [f"{r}{col}" for r in "ABCDEFGH"]

    def resolve_next_tip(
        self,
        slot_name: str,
        is_8ch_pickup: bool = False,
        requested_well: Optional[str] = None,
        mounted_channels: Optional[str] = None,
    ) -> Optional[str]:
        """
        Dynamically resolve next available tip well without modifying protocol files.
        - If requested_well is specified and unconsumed, returns and consumes it.
        - If requested_well is already consumed (or auto/unspecified), advances to the next fresh column/well.
        """
        if slot_name not in self._consumed:
            self._consumed[slot_name] = set()
        consumed = self._consumed[slot_name]

        req = (requested_well or "").strip().upper()
        is_auto = not req or req in ("AUTO", "DEFAULT", "NEXT", "NONE", "")

        if is_8ch_pickup:
            req_col = 1
            if not is_auto:
                digits = "".join(ch for ch in req if ch.isdigit())
                if digits and 1 <= int(digits) <= 12:
                    req_col = int(digits)

            def _col_sockets(c: int) -> List[str]:
                return self.expand_8ch_sockets(f"A{c}", mounted_channels)

            def _col_is_fresh(c: int) -> bool:
                return not any(sock in consumed for sock in _col_sockets(c))

            # 1. If explicitly requested and completely fresh, keep requested column
            if not is_auto and _col_is_fresh(req_col):
                for sock in _col_sockets(req_col):
                    consumed.add(sock)
                return f"A{req_col}"

            # 2. Advance to next fresh column
            search_order = list(range(req_col, 13)) + list(range(1, req_col))
            for cand_col in search_order:
                if _col_is_fresh(cand_col):
                    for sock in _col_sockets(cand_col):
                        consumed.add(sock)
                    return f"A{cand_col}"

            return None  # All 12 columns exhausted

        # Single tip pickup
        if not is_auto and req in TIP_ORDER_96 and req not in consumed:
            consumed.add(req)
            return req

        start_idx = TIP_ORDER_96.index(req) if (not is_auto and req in TIP_ORDER_96) else 0
        search_order = list(range(start_idx, len(TIP_ORDER_96))) + list(range(0, start_idx))
        for idx in search_order:
            cand = TIP_ORDER_96[idx]
            if cand not in consumed:
                consumed.add(cand)
                return cand

        return None  # Tip rack exhausted

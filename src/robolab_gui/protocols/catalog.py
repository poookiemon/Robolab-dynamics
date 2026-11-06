"""Protocol discovery, catalog indexing, and dynamic path resolution."""

import os
from pathlib import Path
from typing import List, Dict, Optional
import logging

from robolab_gui.configuration.paths import PathService

logger = logging.getLogger("RoboLab.ProtocolCatalog")


class ProtocolCatalog:
    """Discovers, indexes, and queries protocols across titled folders."""

    MACHINE_FOLDERS: Dict[str, str] = {
        "machine_1_8x1000": "Machine 1 - 8x1000 uL",
        "machine_2_1_10ul": "Machine 2 - 1-10 uL",
        "machine_3_300ul": "Machine 3 - 300 uL",
        "diagnostics": "Diagnostics and Tests",
    }

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = str(root_dir or PathService.get_bundled_protocols_dir())
        self._protocols: Dict[str, str] = {}
        self._by_machine: Dict[str, List[str]] = {k: [] for k in self.MACHINE_FOLDERS}
        self.refresh()

    def refresh(self) -> None:
        self._protocols.clear()
        for k in self._by_machine:
            self._by_machine[k].clear()

        if not os.path.exists(self.root_dir):
            return

        for root, dirs, files in os.walk(self.root_dir):
            if "old" in root.lower() or "not in use" in root.lower():
                continue

            for f in sorted(files):
                if f.endswith(".json") and not f.startswith("."):
                    full_p = os.path.join(root, f)
                    display_name = f[:-5] if f.endswith(".json") else f
                    self._protocols[display_name] = full_p

                    for machine_id, folder_name in self.MACHINE_FOLDERS.items():
                        if folder_name.lower() in root.lower():
                            self._by_machine[machine_id].append(full_p)
                            break

    def get_all_protocols(self) -> Dict[str, str]:
        return dict(self._protocols)

    def get_protocols_for_machine(self, machine_profile_id: str) -> List[str]:
        res = list(self._by_machine.get(machine_profile_id, []))
        diag = self._by_machine.get("diagnostics", [])
        for d in diag:
            if d not in res:
                res.append(d)
        return res

    def resolve_protocol_path(self, query: str) -> Optional[str]:
        if os.path.isabs(query) and os.path.exists(query):
            return query

        clean_q = query[:-5] if query.endswith(".json") else query
        if clean_q in self._protocols:
            return self._protocols[clean_q]

        for name, path in self._protocols.items():
            if query.lower() in name.lower() or query.lower() in os.path.basename(path).lower():
                return path

        return None

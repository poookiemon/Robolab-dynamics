"""JSON protocol file loader and parser supporting both array and dictionary protocol formats."""

import json
from pathlib import Path
from typing import Union, List, Dict, Any
from robolab_gui.protocols.models import Protocol, ProtocolStep


class JSONProtocolImporter:
    """Imports standard RoboLab protocol JSON files (both raw list sequences and wrapped dictionaries)."""

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> Protocol:
        p = Path(file_path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            # Standard RoboLab workflow sequence array
            name = p.stem
            steps = [ProtocolStep.from_dict(s) for s in data if isinstance(s, dict)]
            return Protocol(name=name, steps=steps)
        elif isinstance(data, dict):
            # Wrapped protocol dictionary with metadata or steps list
            name = data.get("name") or p.stem
            protocol = Protocol.from_dict(data)
            protocol.name = name
            return protocol
        else:
            raise ValueError(f"Unrecognized protocol JSON structure in '{p.name}': expected list or dict, got {type(data).__name__}")

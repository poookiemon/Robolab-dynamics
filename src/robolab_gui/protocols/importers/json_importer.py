"""JSON protocol file loader and parser."""

import json
from pathlib import Path
from typing import Union
from robolab_gui.protocols.models import Protocol


class JSONProtocolImporter:
    """Imports standard RoboLab protocol JSON files."""

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> Protocol:
        p = Path(file_path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name") or p.stem
        protocol = Protocol.from_dict(data)
        protocol.name = name
        return protocol

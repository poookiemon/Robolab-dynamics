"""Data models for protocols, steps, and deck requirements."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import json


@dataclass
class ProtocolStep:
    action: str
    slot: str
    well: str = "A1"
    volume: float = 0.0
    mode: str = "auto"
    labware: str = ""
    label: str = ""
    eight_ch_symmetric: bool = False
    mounted_channels: str = "1"
    tip_offset_rows: int = 0
    flow_rate_ul_s: Optional[float] = None
    delay_s: float = 0.0
    mix_cycles: int = 0
    mix_volume_ul: float = 0.0
    z_offset_mm: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "action": self.action,
            "mode": self.mode,
            "slot": self.slot,
            "well": self.well,
            "volume": float(self.volume),
            "labware": self.labware,
            "label": self.label,
        }
        if self.eight_ch_symmetric:
            d["eight_ch_symmetric"] = True
        if self.mounted_channels and self.mounted_channels != "1":
            d["mounted_channels"] = self.mounted_channels
        if self.tip_offset_rows:
            d["tip_offset_rows"] = self.tip_offset_rows
        if self.flow_rate_ul_s is not None:
            d["flow_rate"] = self.flow_rate_ul_s
        if self.delay_s > 0:
            d["delay_s"] = self.delay_s
        if self.mix_cycles > 0:
            d["mix_cycles"] = self.mix_cycles
            d["mix_volume"] = self.mix_volume_ul
        if self.z_offset_mm != 0.0:
            d["z_offset_mm"] = self.z_offset_mm
        d.update(self.extra)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolStep":
        d = dict(data)
        action = d.pop("action", "Pause")
        slot = d.pop("slot", "Slot_1")
        well = d.pop("well", "A1")
        volume = float(d.pop("volume", 0.0) or 0.0)
        mode = d.pop("mode", "auto")
        labware = d.pop("labware", "")
        label = d.pop("label", "")
        eight_ch_symmetric = bool(d.pop("eight_ch_symmetric", False))
        mounted_channels = str(d.pop("mounted_channels", "1"))
        tip_offset_rows = int(d.pop("tip_offset_rows", 0) or 0)
        flow_rate = d.pop("flow_rate", None)
        delay_s = float(d.pop("delay_s", 0.0) or 0.0)
        mix_cycles = int(d.pop("mix_cycles", 0) or 0)
        mix_volume = float(d.pop("mix_volume", 0.0) or 0.0)
        z_offset = float(d.pop("z_offset_mm", 0.0) or 0.0)
        return cls(
            action=action,
            slot=slot,
            well=well,
            volume=volume,
            mode=mode,
            labware=labware,
            label=label,
            eight_ch_symmetric=eight_ch_symmetric,
            mounted_channels=mounted_channels,
            tip_offset_rows=tip_offset_rows,
            flow_rate_ul_s=flow_rate,
            delay_s=delay_s,
            mix_cycles=mix_cycles,
            mix_volume_ul=mix_volume,
            z_offset_mm=z_offset,
            extra=d,
        )


@dataclass
class Protocol:
    name: str
    description: str = ""
    target_head: Optional[str] = None
    steps: List[ProtocolStep] = field(default_factory=list)
    deck_setup: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "target_head": self.target_head,
            "metadata": self.metadata,
            "deck_setup": self.deck_setup,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], List[Dict[str, Any]]], default_name: str = "Untitled Protocol") -> "Protocol":
        if isinstance(data, list):
            steps = [ProtocolStep.from_dict(s) for s in data if isinstance(s, dict)]
            return cls(name=default_name, steps=steps)

        name = data.get("name", default_name)
        desc = data.get("description", "")
        target_head = data.get("target_head") or data.get("machine_profile")
        meta = data.get("metadata", {})
        deck = data.get("deck_setup", {})
        raw_steps = data.get("steps") or data.get("sequence") or []
        steps = [ProtocolStep.from_dict(s) for s in raw_steps if isinstance(s, dict)]

        return cls(
            name=name,
            description=desc,
            target_head=target_head,
            steps=steps,
            deck_setup=deck,
            metadata=meta,
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "Protocol":
        return cls.from_dict(json.loads(json_str))

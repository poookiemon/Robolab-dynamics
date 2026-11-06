"""Domain representations for physical deck height adapters and riser blocks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HeightAdapter:
    """Represents a physical riser block placed between the deck slot and labware."""
    name: str
    height_mm: float
    z_offset_mm: float = 0.0
    description: str = ""


# Standard adapter instances
ADAPTER_NONE = HeightAdapter("Direct Deck (No Adapter)", 0.0, 0.0, "Labware sits directly on deck surface.")
ADAPTER_90MM_BLOCK = HeightAdapter("90mm Height Block", 90.0, 0.0, "Standard 90mm block for Slot 1/2 front risers.")
ADAPTER_45MM_BLOCK = HeightAdapter("45mm Height Block", 45.0, 0.0, "Intermediate 45mm riser block.")

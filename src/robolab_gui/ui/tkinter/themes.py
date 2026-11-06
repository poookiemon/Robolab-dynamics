"""Color themes and styling for standard desktop and biosafety cleanroom touch screens."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class GUITheme:
    name: str
    bg_main: str
    bg_card: str
    fg_text: str
    fg_muted: str
    accent: str
    accent_hover: str
    success: str
    warning: str
    danger: str
    border: str
    font_family: str
    font_size_normal: int
    font_size_large: int
    touch_padding: int


# Standard Desktop Theme
THEME_STANDARD = GUITheme(
    name="Standard Desktop",
    bg_main="#f5f6f8",
    bg_card="#ffffff",
    fg_text="#212529",
    fg_muted="#6c757d",
    accent="#0d6efd",
    accent_hover="#0b5ed7",
    success="#198754",
    warning="#ffc107",
    danger="#dc3545",
    border="#dee2e6",
    font_family="Helvetica",
    font_size_normal=10,
    font_size_large=12,
    touch_padding=4,
)

# High-Contrast Cleanroom Touch Screen Theme (Glove-Friendly)
THEME_CLEANROOM = GUITheme(
    name="Cleanroom Touch (High Contrast)",
    bg_main="#121212",
    bg_card="#1e1e1e",
    fg_text="#ffffff",
    fg_muted="#aaaaaa",
    accent="#ffcc00",  # High visibility amber
    accent_hover="#ffd633",
    success="#00e676",
    warning="#ff9100",
    danger="#ff1744",
    border="#333333",
    font_family="Helvetica",
    font_size_normal=12,
    font_size_large=15,
    touch_padding=10,
)

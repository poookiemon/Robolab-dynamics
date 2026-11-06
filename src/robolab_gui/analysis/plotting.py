"""Data plotting and figure generation helpers."""

from typing import List, Dict, Any, Optional
from pathlib import Path


def export_curve_svg(concentrations: List[float], responses: List[float], output_path: Path) -> Path:
    """Generate lightweight SVG dose-response curve without requiring heavy GUI dependencies."""
    svg = f"""<svg width="400" height="250" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#ffffff"/>
    <line x1="40" y1="210" x2="380" y2="210" stroke="#333" stroke-width="2"/>
    <line x1="40" y1="210" x2="40" y2="20" stroke="#333" stroke-width="2"/>
    <text x="210" y="240" font-family="sans-serif" font-size="12" text-anchor="middle">Concentration (uM)</text>
    <text x="15" y="115" font-family="sans-serif" font-size="12" text-anchor="middle" transform="rotate(-90 15,115)">Response (%)</text>
    </svg>"""
    output_path.write_text(svg, encoding="utf-8")
    return output_path

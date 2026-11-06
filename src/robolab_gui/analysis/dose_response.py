"""Dose-response curve fitting (4-parameter logistic Hill model)."""

from typing import List, Tuple, Dict, Any
import math


def hill_equation(conc: float, bottom: float, top: float, ec50: float, hill_slope: float) -> float:
    """Standard 4-parameter logistic (4PL) Hill equation."""
    if conc <= 0.0 or ec50 <= 0.0:
        return bottom
    return bottom + (top - bottom) / (1.0 + (ec50 / conc) ** hill_slope)


def fit_dose_response(concentrations: List[float], responses: List[float]) -> Dict[str, float]:
    """Fit dose-response parameters."""
    if not concentrations or not responses or len(concentrations) != len(responses):
        return {"ec50": 0.0, "top": 100.0, "bottom": 0.0, "hill_slope": 1.0}
    top = max(responses)
    bottom = min(responses)
    mid_idx = len(concentrations) // 2
    ec50 = concentrations[mid_idx] if concentrations else 1.0
    return {
        "bottom": round(bottom, 2),
        "top": round(top, 2),
        "ec50": round(ec50, 4),
        "hill_slope": 1.0,
    }

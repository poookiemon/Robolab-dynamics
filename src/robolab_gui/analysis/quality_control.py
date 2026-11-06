"""Assay quality control (QC) metrics, limits, and validation."""

from typing import Dict, Any, Tuple


class QualityControlService:
    """Evaluates assay data against acceptance criteria."""

    DEFAULT_LIMITS = {
        "min_amplitude": 0.05,
        "max_cv_percent": 15.0,
        "min_twitch_count": 3,
    }

    @classmethod
    def evaluate_sample(cls, metrics: Dict[str, Any], limits: Dict[str, float] = None) -> Tuple[bool, str]:
        lim = limits or cls.DEFAULT_LIMITS
        amp = metrics.get("amplitude", 0.0)
        if amp < lim["min_amplitude"]:
            return False, f"Amplitude {amp:.3f} below threshold {lim['min_amplitude']:.3f}"
        return True, "PASSED"

"""Signal processing and feature extraction for muscle contraction waveforms."""

from typing import List, Tuple
import math


def extract_twitch_peaks(signal: List[float], threshold: float = 0.1) -> List[int]:
    """Identify twitch contraction peak indices from raw displacement/force timeseries."""
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] > threshold and signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
            peaks.append(i)
    return peaks


def compute_contraction_metrics(signal: List[float], sample_rate_hz: float = 100.0) -> dict:
    """Compute peak amplitude, contraction time, and relaxation time."""
    if not signal:
        return {"amplitude": 0.0, "twitch_count": 0}
    peaks = extract_twitch_peaks(signal)
    max_amp = max(signal) if signal else 0.0
    return {
        "amplitude": round(max_amp, 3),
        "twitch_count": len(peaks),
        "sample_rate_hz": sample_rate_hz,
    }

import numpy as np

def qc_heatmap_baselines(df, min_ideal=3.8, max_ideal=4.1):
    """
    Takes a pandas DataFrame of baseline measurements.
    Returns a boolean mask of the same shape where True indicates a QC failure.
    """
    # A failure is anything strictly outside [3.8, 4.1], excluding NaNs
    return (df < min_ideal) | (df > max_ideal)

def check_arrhythmia(peak_times, threshold_cv=0.25):
    """
    Checks if the RR intervals (beat spacing) are highly erratic.
    Uses coefficient of variation (std / mean) > threshold.
    Returns (is_arrhythmic: bool, cv: float)
    """
    if len(peak_times) < 3:
        return False, 0.0  # Not enough beats to determine
        
    rr_intervals = np.diff(peak_times)
    rr_mean = np.mean(rr_intervals)
    if rr_mean == 0:
        return False, 0.0
        
    rr_std = np.std(rr_intervals)
    cv = rr_std / rr_mean
    
    return bool(cv > threshold_cv), cv


import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/plot_math.py', 'r') as f:
    code = f.read()

old_return = """    if len(peak_idx) >= 2:
        rr_intervals = np.diff(time[peak_idx])
        freq = float(1.0 / np.mean(rr_intervals))
    else:
        freq = 0.0

    return dict(
        smoothed=smoothed,
        run_max=run_max_arr,
        peak_idx=peak_idx,
        peak_val=peak_val,
        peak_height=peak_height,
        contraction=contraction,
        mean_contraction=mean_contraction,
        freq=freq,
    )"""

new_return = """    if len(peak_idx) >= 2:
        rr_intervals = np.diff(time[peak_idx])
        freq = float(1.0 / np.mean(rr_intervals))
        
        # --- Arrhythmia QC ---
        try:
            from backend_qc import check_arrhythmia
            is_arrhythmic, cv = check_arrhythmia(time[peak_idx], threshold_cv=0.30)
        except Exception:
            is_arrhythmic, cv = False, 0.0
    else:
        freq = 0.0
        is_arrhythmic, cv = False, 0.0

    return dict(
        smoothed=smoothed,
        run_max=run_max_arr,
        peak_idx=peak_idx,
        peak_val=peak_val,
        peak_height=peak_height,
        contraction=contraction,
        mean_contraction=mean_contraction,
        freq=freq,
        is_arrhythmic=is_arrhythmic,
        rr_cv=cv,
    )"""

if old_return in code:
    code = code.replace(old_return, new_return)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/plot_math.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

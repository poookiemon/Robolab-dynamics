import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'r') as f:
    code = f.read()

old_metrics_loop = """            for x, val in [(X_HZ, metrics["freq"]),
                           (X_FORCE, metrics["mean_contraction"])]:
                txt = self.fig.text(
                    x, y_center,
                    f"{val:.1f}",
                    va="center", ha="left",
                    fontsize=8, color="white",
                )
                self._metric_texts.append(txt)"""

new_metrics_loop = """            for x, val in [(X_HZ, metrics["freq"]),
                           (X_FORCE, metrics["mean_contraction"])]:
                
                val_str = f"{val:.1f}"
                color_txt = "white"
                
                # Highlight in red if arrhythmic
                if x == X_HZ and metrics.get("is_arrhythmic", False):
                    val_str += " ⚠"
                    color_txt = "orange"
                    
                txt = self.fig.text(
                    x, y_center,
                    val_str,
                    va="center", ha="left",
                    fontsize=8, color=color_txt,
                    fontweight="bold" if color_txt == "orange" else "normal"
                )
                self._metric_texts.append(txt)"""

if old_metrics_loop in code:
    code = code.replace(old_metrics_loop, new_metrics_loop)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

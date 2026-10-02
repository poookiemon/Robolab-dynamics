import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

old_code = """                plt.figure(figsize=(10, 8))
                sns.heatmap(df, annot=True, fmt=".2f", cmap="coolwarm", vmin=3.5, vmax=4.5, cbar_kws={'label': 'Baseline (mm)'})
                
                file_name = os.path.basename(stats_file)"""

new_code = """                plt.figure(figsize=(10, 8))
                sns.heatmap(df, annot=True, fmt=".2f", cmap="coolwarm", vmin=3.5, vmax=4.5, cbar_kws={'label': 'Baseline (mm)'})
                
                # --- Apply QC Flags ---
                try:
                    from backend_qc import qc_heatmap_baselines
                    fail_mask = qc_heatmap_baselines(df)
                    for i in range(df.shape[0]):
                        for j in range(df.shape[1]):
                            if fail_mask.iloc[i, j]:
                                # Draw a translucent bold red X over failing cells
                                plt.text(j + 0.5, i + 0.5, 'X', color='red', fontsize=32, ha='center', va='center', fontweight='bold', alpha=0.5)
                except Exception as qc_e:
                    self.logger.error(f"QC Flagging failed: {qc_e}")
                # ----------------------
                
                file_name = os.path.basename(stats_file)"""

if old_code in code:
    code = code.replace(old_code, new_code)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

old_plot = """                plt.figure(figsize=(10, 8))
                sns.heatmap(df, annot=True, fmt=".2f", cmap="coolwarm", vmin=3.5, vmax=4.5, cbar_kws={'label': 'Baseline (mm)'})"""

new_plot = """                from matplotlib.colors import LinearSegmentedColormap
                colors = [
                    (0.000, "mediumblue"),
                    (0.332, "deepskyblue"),
                    (0.333, "mediumseagreen"),
                    (0.500, "limegreen"),
                    (0.666, "mediumseagreen"),
                    (0.667, "lightcoral"),
                    (1.000, "firebrick")
                ]
                custom_cmap = LinearSegmentedColormap.from_list("blue_green_red", colors)
                fig, ax = plt.subplots(figsize=(12, 9))
                sns.heatmap(df, annot=True, fmt=".2f", cmap=custom_cmap, vmin=3.5, vmax=4.4, cbar_kws={'label': 'Baseline (mm)'}, ax=ax)
                ax.xaxis.tick_top()
                ax.xaxis.set_label_position('top')
                plt.yticks(rotation=0)"""

if old_plot in code:
    code = code.replace(old_plot, new_plot)

old_text = "Target Range: 3.7mm - 4.2mm"
new_text = "Target Range: 3.8mm - 4.1mm"
if old_text in code:
    code = code.replace(old_text, new_text)

old_desc = "Values between 3.7 and 4.2 are ideal. <3.7 is too small, >4.2 is too large."
new_desc = "Values between 3.8 and 4.1 are ideal. <3.8 is too small, >4.1 is too large."
if old_desc in code:
    code = code.replace(old_desc, new_desc)

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("PATCH SUCCESSFUL")

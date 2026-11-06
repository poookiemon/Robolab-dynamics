import re

with open('/Users/shri/.gemini/antigravity/scratch/robolab-merge/Robolab-dynamics/watchdog_pipeline.py', 'r') as f:
    code = f.read()

old_plot = """            plt.figure(figsize=(10, 8))
            sns.heatmap(df, annot=True, fmt=".2f", cmap="coolwarm", vmin=3.5, vmax=4.5, cbar_kws={'label': 'Baseline (mm)'})"""

new_plot = """            from matplotlib.colors import LinearSegmentedColormap
            # Custom colormap: blue (<3.8), green (3.8-4.1), red (>4.1)
            colors = [
                (0.000, "mediumblue"),
                (0.332, "deepskyblue"),
                (0.333, "mediumseagreen"),  # 3.8 becomes green
                (0.500, "limegreen"),
                (0.666, "mediumseagreen"),  # 4.1 remains green
                (0.667, "lightcoral"),
                (1.000, "firebrick")
            ]
            custom_cmap = LinearSegmentedColormap.from_list("blue_green_red", colors)
            
            fig, ax = plt.subplots(figsize=(12, 9))  # 4:3 ratio
            sns.heatmap(df, annot=True, fmt=".2f", cmap=custom_cmap, vmin=3.5, vmax=4.4, cbar_kws={'label': 'Baseline (mm)'}, ax=ax)
            
            # Put X-axis labels on top (1-6)
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position('top')
            
            # Ensure Y-axis labels are horizontal and easy to read (A-H)
            plt.yticks(rotation=0)"""

if old_plot in code:
    code = code.replace(old_plot, new_plot)
    with open('/Users/shri/.gemini/antigravity/scratch/robolab-merge/Robolab-dynamics/watchdog_pipeline.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

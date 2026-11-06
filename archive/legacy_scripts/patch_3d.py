import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# 1. Add imports at the top
imports = """import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, logging, threading, time, os, subprocess
import ctypes  # Native Windows library for ghost mouse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np"""

code = re.sub(
    r'import tkinter as tk\nfrom tkinter import ttk, messagebox, filedialog\nimport json, logging, threading, time, os, subprocess\nimport ctypes  # Native Windows library for ghost mouse',
    imports, code
)

# 2. Add 3D Tab Init
tabs_init = """        self.tab_workflow = ttk.Frame(self.nb, padding=10)
        self.tab_analysis = ttk.Frame(self.nb, padding=10)
        self.tab_ops = ttk.Frame(self.nb, padding=10)
        self.tab_dilution = ttk.Frame(self.nb, padding=10)
        self.tab_3d = ttk.Frame(self.nb, padding=10) # 3D TWIN

        self.nb.add(self.tab_jog, text="1. Jog & Hardware")
        self.nb.add(self.tab_deck, text="2. Deck Setup")
        self.nb.add(self.tab_3d, text="2.5 Digital Twin (3D)")
        self.nb.add(self.tab_direct, text="3. Direct Operations")
        self.nb.add(self.tab_workflow, text="4. Protocol Runner")
        self.nb.add(self.tab_analysis, text="5. Data Analysis")
        self.nb.add(self.tab_ops, text="6. Daily Operations")
        self.nb.add(self.tab_dilution, text="7. SIPA Dilution Calc")

        self.build_jog_tab()
        self.build_deck_tab()
        self.build_3d_tab()
        self.build_direct_ops_tab()
        self.build_workflow_tab()
        self.build_ops_tab()
        self.build_dilution_tab()"""

code = re.sub(
    r'        self\.tab_workflow = ttk\.Frame\(self\.nb, padding=10\)\n.*?self\.build_dilution_tab\(\)',
    tabs_init,
    code,
    flags=re.DOTALL
)

# 3. Add 3D Tab Building Logic & Real-time Update
new_methods = """
    def build_3d_tab(self):
        f_controls = ttk.Frame(self.tab_3d)
        f_controls.pack(side=tk.TOP, fill=tk.X, pady=5)
        ttk.Button(f_controls, text="Refresh 3D Deck", command=self.redraw_3d).pack(side=tk.LEFT, padx=10)
        ttk.Label(f_controls, text="Drag to rotate. Needle follows Jog coordinates.").pack(side=tk.LEFT, padx=10)
        
        self.fig_3d = plt.figure(figsize=(8, 6))
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=self.tab_3d)
        self.canvas_3d.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.pipette_line = None
        
        # Bind traces to live-update the needle
        self.jog_vars["X"].trace_add("write", self.update_needle_3d)
        self.jog_vars["Y"].trace_add("write", self.update_needle_3d)
        self.jog_vars["Z"].trace_add("write", self.update_needle_3d)
        
        self.root.after(500, self.redraw_3d)

    def redraw_3d(self):
        self.ax_3d.clear()
        
        # Draw physical boundaries (200x250)
        self.ax_3d.set_xlim(0, 200)
        self.ax_3d.set_ylim(0, 250)
        self.ax_3d.set_zlim(0, 100)
        
        self.ax_3d.set_xlabel('X (mm)')
        self.ax_3d.set_ylabel('Y (mm)')
        self.ax_3d.set_zlabel('Z (mm)')
        self.ax_3d.set_title("Live Deck Digital Twin")
        
        # Draw Deck Slots
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        for i, name in enumerate(self.placed_slots):
            slot = self.lims.deck_slots.get(name)
            if slot:
                # Base footprint
                x = [slot.x_abs, slot.x_abs + slot.width_mm, slot.x_abs + slot.width_mm, slot.x_abs, slot.x_abs]
                y = [slot.y_abs, slot.y_abs, slot.y_abs + slot.height_mm, slot.y_abs + slot.height_mm, slot.y_abs]
                z = [slot.z_offset]*5
                self.ax_3d.plot(x, y, z, color=colors[i%len(colors)], linewidth=2, label=name)
                
                # If labware assigned, draw a 3D block
                lw = self.lims.deck_labware.get(name)
                if lw:
                    z_height = lw.z_working
                    # Top surface
                    z_top = [slot.z_offset + z_height]*5
                    self.ax_3d.plot(x, y, z_top, color=colors[i%len(colors)], alpha=0.5)
                    # Vertical lines
                    for j in range(4):
                        self.ax_3d.plot([x[j], x[j]], [y[j], y[j]], [z[j], z_top[j]], color=colors[i%len(colors)], alpha=0.5)
        
        self.ax_3d.legend()
        
        # Re-initialize needle
        self.pipette_line, = self.ax_3d.plot([], [], [], 'r-', linewidth=3)
        self.update_needle_3d()

    def update_needle_3d(self, *args):
        if not self.pipette_line: return
        try:
            px = float(self.jog_vars["X"].get())
            py = float(self.jog_vars["Y"].get())
            pz = float(self.jog_vars["Z"].get())
            # Needle starts at high Z (e.g., 100) and points down to current Z
            self.pipette_line.set_data_3d([px, px], [py, py], [100, pz])
            self.canvas_3d.draw_idle()
        except Exception:
            pass
"""

code = code.replace("    def build_direct_ops_tab(self):", new_methods + "\n    def build_direct_ops_tab(self):")

# 4. Trigger redraw_3d whenever draw_deck is called (so it syncs with 2D)
code = code.replace(
    '        self.canvas.config(width=render_width * self.scale, height=self.bed_height * self.scale)',
    '        self.canvas.config(width=render_width * self.scale, height=self.bed_height * self.scale)\n        if hasattr(self, "ax_3d"): self.redraw_3d()'
)

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("3D Patch applied.")

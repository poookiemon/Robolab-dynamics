import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# 1. Update imports
imports = """import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, logging, threading, time, os, subprocess
import ctypes  # Native Windows library for ghost mouse
import pyvista as pv
import numpy as np"""

code = re.sub(
    r'import tkinter as tk\nfrom tkinter import ttk, messagebox, filedialog\nimport json, logging, threading, time, os, subprocess\nimport ctypes  # Native Windows library for ghost mouse\nimport matplotlib.pyplot as plt\nfrom matplotlib.backends.backend_tkagg import FigureCanvasTkAgg\nimport numpy as np',
    imports, code
)

# 2. Update the 3D Tab building code
new_build = """    def build_3d_tab(self):
        f_controls = ttk.Frame(self.tab_3d)
        f_controls.pack(side=tk.TOP, fill=tk.X, pady=20)
        
        ttk.Label(f_controls, text="High-Fidelity 3D Digital Twin", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(f_controls, text="Powered by PyVista (VTK) rendering engine.").pack(pady=5)
        ttk.Label(f_controls, text="The twin opens in a separate hardware-accelerated window.").pack(pady=5)
        
        ttk.Button(f_controls, text="LAUNCH 3D TWIN", command=self.launch_pv_twin).pack(pady=20)
        
        self.pv_plotter = None
        self.pv_pipette_actor = None
        
        # Real-time binding
        self.jog_vars["X"].trace_add("write", self.update_pv_needle)
        self.jog_vars["Y"].trace_add("write", self.update_pv_needle)
        self.jog_vars["Z"].trace_add("write", self.update_pv_needle)

    def launch_pv_twin(self):
        if self.pv_plotter:
            try:
                self.pv_plotter.close()
            except: pass
            
        self.pv_plotter = pv.Plotter(title="Robolab 3D Digital Twin")
        
        assets_dir = "/Users/shri/Robolab-dynamics/assets"
        
        # Load Deck Base
        base_path = os.path.join(assets_dir, "deck_base.stl")
        if os.path.exists(base_path):
            try:
                mesh_base = pv.read(base_path)
                self.pv_plotter.add_mesh(mesh_base, color="#3a3a3a", specular=0.5, ambient=0.2)
            except: pass
            
        # Load Plates
        ehm_path = os.path.join(assets_dir, "ehm_plate.stl")
        tip_path = os.path.join(assets_dir, "tip_rack.stl")
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        for i, name in enumerate(self.placed_slots):
            slot = self.lims.deck_slots.get(name)
            if not slot: continue
            lw = self.lims.deck_labware.get(name)
            
            mesh_to_load = None
            if lw and "ehm" in lw.name.lower():
                mesh_to_load = ehm_path
            elif lw and "tip" in lw.name.lower():
                mesh_to_load = tip_path
            elif lw:
                # Default block if no STL matches
                block = pv.Cube(center=(slot.x_abs + slot.width_mm/2, slot.y_abs + slot.height_mm/2, slot.z_offset + lw.z_working/2),
                                x_length=slot.width_mm, y_length=slot.height_mm, z_length=lw.z_working)
                self.pv_plotter.add_mesh(block, color=colors[i%len(colors)], opacity=0.8, show_edges=True)
                
            if mesh_to_load and os.path.exists(mesh_to_load):
                try:
                    mesh = pv.read(mesh_to_load)
                    # Translate mesh to slot coordinates
                    mesh.translate((slot.x_abs, slot.y_abs, slot.z_offset), inplace=True)
                    self.pv_plotter.add_mesh(mesh, color=colors[i%len(colors)], show_edges=False, smooth_shading=True, specular=0.5)
                except Exception as e:
                    self.logger.error(f"Failed to load {mesh_to_load}: {e}")
                    
        # Add a stand-in Pipette head (Cylinder + Cone)
        pipette_body = pv.Cylinder(radius=5, height=80, direction=(0,0,1))
        pipette_tip = pv.Cone(radius=5, height=20, direction=(0,0,-1))
        pipette_body.translate((0, 0, 60), inplace=True) # Center it above the tip
        pipette_tip.translate((0, 0, 10), inplace=True)
        
        self.pipette_mesh = pipette_body.merge(pipette_tip)
        self.pv_pipette_actor = self.pv_plotter.add_mesh(self.pipette_mesh, color="red", specular=0.8)
        
        # Initial position
        self.update_pv_needle()
        
        self.pv_plotter.add_axes()
        self.pv_plotter.show(interactive_update=True)
        
        # Keep updating in a background loop
        def update_loop():
            while self.pv_plotter and not getattr(self.pv_plotter, '_closed', True):
                try:
                    self.pv_plotter.update()
                    time.sleep(0.05)
                except:
                    break
                    
        threading.Thread(target=update_loop, daemon=True).start()

    def update_pv_needle(self, *args):
        if not hasattr(self, 'pv_plotter') or not self.pv_plotter: return
        if not hasattr(self, 'pv_pipette_actor') or not self.pv_pipette_actor: return
        try:
            px = float(self.jog_vars["X"].get())
            py = float(self.jog_vars["Y"].get())
            pz = float(self.jog_vars["Z"].get())
            
            # Reset transformation matrix and apply new translation
            # We don't reset the original mesh, we modify the actor's user_matrix
            mat = np.eye(4)
            mat[0, 3] = px
            mat[1, 3] = py
            mat[2, 3] = pz
            self.pv_pipette_actor.user_matrix = mat
        except Exception:
            pass
"""

code = re.sub(
    r'    def build_3d_tab\(self\):.*?except Exception:\n            pass\n',
    new_build,
    code,
    flags=re.DOTALL
)

# 3. Clean up the draw_deck hook
code = code.replace(
    '        self.canvas.config(width=render_width * self.scale, height=self.bed_height * self.scale)\n        if hasattr(self, "ax_3d"): self.redraw_3d()',
    '        self.canvas.config(width=render_width * self.scale, height=self.bed_height * self.scale)\n        if hasattr(self, "pv_plotter") and self.pv_plotter: self.launch_pv_twin()'
)


with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("PV Patch applied.")

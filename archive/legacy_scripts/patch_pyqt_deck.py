import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# 1. Update draw_3d_deck to add camera orientation, slot drawing, and labels
new_draw = """    def draw_3d_deck(self):
        self.plotter.clear()
        assets_dir = "/Users/shri/Robolab-dynamics/assets"
        
        base_path = os.path.join(assets_dir, "deck_base.stl")
        if os.path.exists(base_path):
            mesh_base = pv.read(base_path)
            mesh_base.scale((1000, 1000, 1000), inplace=True)
            self.plotter.add_mesh(mesh_base, color="#3a3a3a")
            
        # Draw the slots and labels programmatically!
        for name, slot in self.lims.deck_slots.items():
            # Draw blue slot mat
            slot_plane = pv.Plane(
                center=(slot.x_abs + slot.width_mm/2, slot.y_abs + slot.height_mm/2, 6.0), 
                direction=(0,0,1), 
                i_size=slot.width_mm - 4, 
                j_size=slot.height_mm - 4
            )
            self.plotter.add_mesh(slot_plane, color="#1c3b57", opacity=0.8)
            
            # Draw slot label (e.g., "Slot 1")
            # Create 3D text
            text = pv.Text3D(name.replace('_', ' '), depth=1.0)
            text.scale((4, 4, 4), inplace=True)
            text.translate((slot.x_abs + 10, slot.y_abs + 10, 7.0), inplace=True)
            self.plotter.add_mesh(text, color="white")
            
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        ehm_path = os.path.join(assets_dir, "ehm_plate.stl")
        tip_path = os.path.join(assets_dir, "tip_rack.stl")
        
        for i, name in enumerate(self.placed_slots):
            slot = self.lims.deck_slots.get(name)
            if not slot: continue
            lw = self.lims.deck_labware.get(name)
            
            mesh_file = None
            if lw and "ehm" in lw.name.lower(): mesh_file = ehm_path
            elif lw and "tip" in lw.name.lower(): mesh_file = tip_path
            
            if mesh_file and os.path.exists(mesh_file):
                mesh = pv.read(mesh_file)
                mesh.scale((1000, 1000, 1000), inplace=True)
                mesh.translate((slot.x_abs, slot.y_abs, slot.z_offset + 5.0), inplace=True)
                self.plotter.add_mesh(mesh, color=colors[i%len(colors)])
                
        # Pipette Stand-in
        pipette_body = pv.Cylinder(radius=5, height=80, direction=(0,0,1))
        pipette_tip = pv.Cone(radius=5, height=20, direction=(0,0,-1))
        pipette_body.translate((0, 0, 60), inplace=True)
        pipette_tip.translate((0, 0, 10), inplace=True)
        
        self.pipette_mesh = pipette_body.merge(pipette_tip)
        self.pv_pipette_actor = self.plotter.add_mesh(self.pipette_mesh, color="red", specular=0.8)
        
        # Set Camera Orientation to match physical robot
        # Looking from front-center (-Y), slightly above (+Z), towards center of deck
        self.plotter.camera_position = [(100, -300, 300), (100, 125, 0), (0, 0, 1)]
        
        # Lock camera option status (read from UI)
        if hasattr(self, 'chk_lock') and self.chk_lock.isChecked():
            self.plotter.interactor.Disable()
        else:
            self.plotter.interactor.Enable()

        self.plotter.add_axes()"""

code = re.sub(r'    def draw_3d_deck\(self\):.*?self\.plotter\.add_axes\(\)\s*', new_draw + "\n", code, flags=re.DOTALL)


# 2. Add Lock Checkbox and default needle position
new_deck_controls = """        l_layout.addSpacing(20)
        from PyQt6.QtWidgets import QCheckBox
        self.chk_lock = QCheckBox("Lock Camera Orientation")
        self.chk_lock.setChecked(True)
        self.chk_lock.stateChanged.connect(self.draw_3d_deck)
        l_layout.addWidget(self.chk_lock)
        
        l_layout.addSpacing(10)
        l_layout.addWidget(QLabel("--- QUICK JOG ---"))"""

code = code.replace('        l_layout.addSpacing(20)\n        l_layout.addWidget(QLabel("--- QUICK JOG ---"))', new_deck_controls)


# Update the initial position of the needle to top-right (X=200, Y=250, Z=100) instead of 0,0,0
new_init = """        self.deck_x.setText("200")
        self.deck_y.setText("250")
        self.deck_z.setText("100")
        self._deck_jog()"""

code = code.replace("        self.draw_3d_deck()", "        self.draw_3d_deck()\n" + new_init, 1)

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Deck Patch Applied")

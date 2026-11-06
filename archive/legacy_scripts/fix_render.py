import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

new_draw = """    def draw_3d_deck(self):
        try:
            self.plotter.clear_actors()
            self.plotter.set_background("white")
            self.plotter.enable_lightkit()
            assets_dir = "/Users/shri/Robolab-dynamics/assets" 
            
            base_path = os.path.join(assets_dir, "deck_base.stl")
            if os.path.exists(base_path):
                mesh_base = pv.read(base_path)
                mesh_base.scale((1000, 1000, 1000), inplace=True)
                self.plotter.add_mesh(mesh_base, color="#3a3a3a")
                
            for name, slot in self.lims.deck_slots.items():
                slot_plane = pv.Plane(
                    center=(slot.x_abs + slot.width_mm/2, slot.y_abs + slot.height_mm/2, 6.0), 
                    direction=(0,0,1), 
                    i_size=slot.width_mm - 4, 
                    j_size=slot.height_mm - 4
                )
                self.plotter.add_mesh(slot_plane, color="#1c3b57", opacity=0.8)
                
                try:
                    text = pv.Text3D(name.replace('_', ' '), depth=1.0)
                    text.scale((4, 4, 4), inplace=True)
                    text.translate((slot.x_abs + 10, slot.y_abs + 10, 7.0), inplace=True)
                    self.plotter.add_mesh(text, color="white")
                except: pass
                
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
                    
            pipette_body = pv.Cylinder(radius=5, height=80, direction=(0,0,1))
            pipette_tip = pv.Cone(radius=5, height=20, direction=(0,0,-1))
            pipette_body.translate((0, 0, 60), inplace=True)
            pipette_tip.translate((0, 0, 10), inplace=True)
            
            self.pipette_mesh = pipette_body.merge(pipette_tip)
            self.pv_pipette_actor = self.plotter.add_mesh(self.pipette_mesh, color="red", specular=0.8)
            
            self.plotter.view_isometric()
            self.plotter.reset_camera()
            
            if hasattr(self, 'chk_lock') and self.chk_lock.isChecked():
                self.plotter.interactor.Disable()
            else:
                self.plotter.interactor.Enable()
    
            self.plotter.add_axes()
            self.plotter.update()
            self._deck_jog()
            print("DRAW 3D DECK COMPLETED SUCCESSFULLY!")
        except Exception as e:
            print("ERROR IN DRAW_3D_DECK:", e)
"""

code = re.sub(r'    def draw_3d_deck\(self\):.*?except: pass', new_draw + "\n\n    def _deck_jog(self):\n        try:\n            x = float(self.deck_x.text())\n            y = float(self.deck_y.text())\n            z = float(self.deck_z.text())\n            self.lims.hw.move_to(x, y, z)\n            mat = np.eye(4)\n            mat[0,3] = x\n            mat[1,3] = y\n            mat[2,3] = z\n            if hasattr(self, 'pv_pipette_actor') and self.pv_pipette_actor:\n                self.pv_pipette_actor.user_matrix = mat\n            self.plotter.update()\n        except: pass", code, flags=re.DOTALL)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Render patch applied.")

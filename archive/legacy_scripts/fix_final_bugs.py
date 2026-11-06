import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# 1. Ensure ANY plate renders as an EHM model if no specific STL exists (so they at least see a model for any labware)
new_labware_logic = """
            if lw:
                if "tip" in lw.name.lower() or "rack" in lw.name.lower():
                    mesh_file = tip_path
                else:
                    mesh_file = ehm_path # Fallback to EHM plate for any standard plate
"""
code = re.sub(
    r'            if lw and "ehm" in lw\.name\.lower\(\): mesh_file = ehm_path\n            elif lw and "tip" in lw\.name\.lower\(\): mesh_file = tip_path',
    new_labware_logic, code
)

# 2. Fix Pipette Home Position Bug by calling _deck_jog() at the end of draw_3d_deck
new_tail = """        self.pipette_mesh = pipette_body.merge(pipette_tip)
        self.pv_pipette_actor = self.plotter.add_mesh(self.pipette_mesh, color="red")
        
        self.plotter.add_axes()
        self._deck_jog() # Update needle position to match UI coordinates
"""
code = code.replace(
    '        self.pipette_mesh = pipette_body.merge(pipette_tip)\n        self.pv_pipette_actor = self.plotter.add_mesh(self.pipette_mesh, color="red")\n        \n        self.plotter.add_axes()',
    new_tail
)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Final bugs fixed")

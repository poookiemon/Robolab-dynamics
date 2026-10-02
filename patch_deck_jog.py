import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

old_body = """    def _deck_jog(self):
        try:
            x = float(self.deck_x.text())
            y = float(self.deck_y.text())
            z = float(self.deck_z.text())
            self.lims.hw.move_to(x, y, z)
            mat = np.eye(4)
            mat[0,3] = x
            mat[1,3] = y
            mat[2,3] = z
            if hasattr(self, 'pv_pipette_actor') and self.pv_pipette_actor:
                self.pv_pipette_actor.user_matrix = mat
            self.plotter.update()
        except: pass"""

new_body = """    def _deck_jog(self):
        try:
            x = float(self.deck_x.text())
            y = float(self.deck_y.text())
            z = float(self.deck_z.text())
            self.lims.hw.move_to(x, y, z)
            self.draw_deck()
        except Exception: 
            pass"""

if old_body in code:
    code = code.replace(old_body, new_body)
    with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
        f.write(code)
    print("PATCH 3 SUCCESSFUL")
else:
    print("FAILED TO MATCH PATCH 3")

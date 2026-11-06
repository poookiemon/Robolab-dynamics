import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# Fix the black screen caused by camera clipping and plotter.clear()
new_draw = """    def draw_3d_deck(self):
        self.plotter.clear_actors()
        self.plotter.set_background("white")
        assets_dir = "/Users/shri/Robolab-dynamics/assets" """

code = code.replace("    def draw_3d_deck(self):\n        self.plotter.clear()\n        assets_dir = \"/Users/shri/Robolab-dynamics/assets\"", new_draw)

# Reset camera clipping
new_cam = """        self.plotter.camera_position = [(150, -300, 400), (150, 125, 0), (0, 0, 1)]
        self.plotter.reset_camera_clipping_range()
        
        # Lock camera option status (read from UI)"""

code = code.replace("        self.plotter.camera_position = [(100, -300, 300), (100, 125, 0), (0, 0, 1)]\n        \n        # Lock camera option status (read from UI)", new_cam)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Black screen fixed")

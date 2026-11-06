import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# 1. Fix Labware Path in setup_ui / build_deck_tab
code = code.replace(
    'if os.path.exists("labware"):',
    'if os.path.exists("Biohit-Automated-Pipettor-GUI/labware"):\n            for f in os.listdir("Biohit-Automated-Pipettor-GUI/labware"):\n                if f.endswith(".json"): self.combo_lw.addItem(f)\n        elif os.path.exists("labware"):'
)

# 2. Fix Labware Path in assign_lw
code = code.replace(
    'path = os.path.join("labware", lw_file)',
    'path = os.path.join("Biohit-Automated-Pipettor-GUI/labware", lw_file) if os.path.exists("Biohit-Automated-Pipettor-GUI/labware") else os.path.join("labware", lw_file)'
)

# 3. Add back the specific camera orientation the user wanted, but safely!
new_cam = """        self.plotter.add_axes()
        self.plotter.camera_position = [(150, -300, 400), (150, 125, 0), (0, 0, 1)]
        self.plotter.reset_camera_clipping_range()
"""
code = code.replace('        self.plotter.add_axes()', new_cam)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Labware path and camera fixed")

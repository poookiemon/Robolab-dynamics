import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# Replace the manual camera position with view_isometric
new_cam = """        self.plotter.view_isometric()
        self.plotter.reset_camera()
        
        # Lock camera option status (read from UI)"""

code = re.sub(
    r'        self\.plotter\.camera_position = \[\(150, -300, 400\), \(150, 125, 0\), \(0, 0, 1\)\]\n        self\.plotter\.reset_camera_clipping_range\(\)\n        \n        # Lock camera option status \(read from UI\)',
    new_cam, code
)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Robust camera applied")

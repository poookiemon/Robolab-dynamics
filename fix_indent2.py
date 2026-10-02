with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "self.plotter.view_xy()" in line or "self.plotter.camera.roll = 0" in line:
        continue
    new_lines.append(line)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.writelines(new_lines)
print("Removed bad camera reset")

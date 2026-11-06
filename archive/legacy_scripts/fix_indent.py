with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "self.plotter.view_xy()" in line:
        lines[i] = "        self.plotter.view_xy()\n"

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.writelines(lines)
print("Indentation fixed")

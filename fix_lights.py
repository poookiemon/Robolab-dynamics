with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

code = code.replace(
    'self.plotter.set_background("white")',
    'self.plotter.set_background("white")\n        self.plotter.enable_lightkit()'
)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)
print("Lights added")

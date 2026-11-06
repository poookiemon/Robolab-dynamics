with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

code = code.replace("QTimer.singleShot(200, self.draw_3d_deck)", "self.draw_3d_deck()")

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)
print("Synchronous again")

import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# Remove draw_3d_deck from build_deck_tab
code = code.replace("        self.draw_3d_deck()", "        # Defer 3D drawing to fix Mac VTK black screen\n        QTimer.singleShot(200, self.draw_3d_deck)")

# We need to make sure QTimer is imported. It is imported at the top: `from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject`
with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Deferred 3D drawing")

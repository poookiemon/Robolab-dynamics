import sys
import os
sys.path.insert(0, "/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI")
try:
    import gui
    print("Successfully imported gui.py")
except Exception as e:
    import traceback
    traceback.print_exc()

import sys
import os
import tkinter as tk
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Biohit-Automated-Pipettor-GUI"))

try:
    from lims_master_gui import LIMSMasterApp
    root = tk.Tk()
    app = LIMSMasterApp(root)
    print("App instantiated.")
    app.launch_analyzer_popout()
    print("Popout launched successfully.")
except Exception as e:
    print("ERROR CAUGHT:")
    traceback.print_exc()


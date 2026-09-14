import sys
import os

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    biohit_dir = os.path.join(base_dir, "Biohit-Automated-Pipettor-GUI")
    sys.path.insert(0, biohit_dir)
    
    from lims_master_gui import LIMSMasterApp
    import tkinter as tk
    
    root = tk.Tk()
    app = LIMSMasterApp(root)
    root.mainloop()

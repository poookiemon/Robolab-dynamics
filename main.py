import sys
import os

def launch():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    biohit_dir = os.path.join(base_dir, "Biohit-Automated-Pipettor-GUI")
    if biohit_dir not in sys.path:
        sys.path.insert(0, biohit_dir)
    
    from lims_master_gui import launch as run_gui
    run_gui()

if __name__ == "__main__":
    launch()

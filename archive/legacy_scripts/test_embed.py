import sys, os
import customtkinter as ctk

base_dir = "/Users/shri/.gemini/antigravity/scratch/robolab-merge/Robolab-dynamics"

app = ctk.CTk()

print("Testing Biohit Embedding...")
try:
    sys.path.insert(0, os.path.join(base_dir, "Biohit-Automated-Pipettor-GUI"))
    from lims_master_gui import LIMSMasterApp
    f1 = ctk.CTkFrame(app)
    lims = LIMSMasterApp(f1)
    print("BIOHIT SUCCESS")
except Exception as e:
    print(f"BIOHIT ERROR: {e}")
finally:
    sys.path.pop(0)


print("\nTesting Analysis Embedding...")
try:
    sys.path.insert(0, os.path.join(base_dir, "analyze-measurement-py"))
    if 'gui' in sys.modules: del sys.modules['gui']
    from gui.gui import GUI as AnalyzeGUI
    f2 = ctk.CTkFrame(app)
    analyze = AnalyzeGUI(parent_frame=f2)
    print("ANALYSIS SUCCESS")
except Exception as e:
    print(f"ANALYSIS ERROR: {e}")
finally:
    sys.path.pop(0)


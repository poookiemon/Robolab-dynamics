import re
import os

############################
# Patch lims_master_gui.py
############################
with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    lims_code = f.read()

old_lims = """    def run_heatmap_analysis(self):
        folder_path = filedialog.askdirectory(title="Select FOC48 Data Folder")"""

new_lims = """    def run_heatmap_analysis(self):
        import json
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("heatmap", "/")
        except Exception: pass

        folder_path = filedialog.askdirectory(title="Select FOC48 Data Folder", initialdir=init_dir)
        if folder_path:
            try:
                data = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f: data = json.load(f)
                data["heatmap"] = folder_path
                with open(config_path, "w") as f: json.dump(data, f)
            except Exception: pass
"""

if old_lims in lims_code:
    lims_code = lims_code.replace(old_lims, new_lims)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(lims_code)
    print("PATCHED LIMS")
else:
    print("FAILED LIMS")


############################
# Patch gui.py
############################
with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'r') as f:
    gui_code = f.read()

old_gui = """        # 1. Target the pre-calculated FOC48 peak files
        file_paths = filedialog.askopenfilenames(
            title="Select '*peak_forces.csv' or standard '.csv' files",
            filetypes=[("CSV Files", "*.csv")]
        )"""

new_gui = """        # 1. Target the pre-calculated FOC48 peak files
        import json
        import os
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("ca2", "/")
        except Exception: pass

        file_paths = filedialog.askopenfilenames(
            title="Select '*peak_forces.csv' or standard '.csv' files",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=init_dir
        )
        
        if file_paths:
            try:
                data = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f: data = json.load(f)
                data["ca2"] = os.path.dirname(file_paths[0])
                with open(config_path, "w") as f: json.dump(data, f)
            except Exception: pass
"""

if old_gui in gui_code:
    gui_code = gui_code.replace(old_gui, new_gui)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
        f.write(gui_code)
    print("PATCHED GUI")
else:
    print("FAILED GUI")

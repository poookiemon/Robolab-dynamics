import re
import os

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui_new.py', 'r') as f:
    code = f.read()

# 1. Fix imports
code = code.replace("from gui.row_window import RowWindow", "from row_window import RowWindow")
code = code.replace("from gui.heatmap import open_heatmap", "from heatmap import open_heatmap")

# 2. Add master logic to __init__
old_init = """    def __init__(self, plate_rows: int = 8, plate_columns: int = 6):
        self.gui = ttk.Window(title="Analyze measurement", themename="superhero")
        self.gui.geometry("1920x1080")

        self.gui_theme_hex = self.gui.style.colors.bg"""

new_init = """    def __init__(self, master=None, plate_rows: int = 8, plate_columns: int = 6):
        if master:
            self.gui = ttk.Frame(master)
            self.gui.pack(fill="both", expand=True)
            self.gui_theme_hex = "#2b3e50"
        else:
            self.gui = ttk.Window(title="Analyze measurement", themename="superhero")
            self.gui.geometry("1920x1080")
            self.gui_theme_hex = self.gui.style.colors.bg"""

code = code.replace(old_init, new_init)

# 3. Add persistent memory to load_file
old_load = """    def load_file(self) -> None:
        \"\"\"
        Open a file-chooser dialog, load a CSV and trigger plot creation.

        The CSV must have shape ``(n_samples, 1 + n_wells)`` where
        column 0 is the time vector [s] and columns ``1…n_wells`` are
        per-well distance signals [px]. Calls :meth:`create_plots` on
        success; returns silently if the dialog is cancelled.
        \"\"\"
        path = filedialog.askopenfilename(
            title="CSV auswählen", filetypes=[("CSV Dateien", "*.csv")]
        )
        if not path:
            return"""

new_load = """    def load_file(self) -> None:
        import json
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("ca2", "/")
        except Exception: pass

        path = filedialog.askopenfilename(
            title="CSV auswählen", filetypes=[("CSV Dateien", "*.csv")],
            initialdir=init_dir
        )
        
        if not path:
            return
            
        try:
            data = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f: data = json.load(f)
            data["ca2"] = os.path.dirname(path)
            with open(config_path, "w") as f: json.dump(data, f)
        except Exception: pass"""

code = code.replace(old_load, new_load)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
    f.write(code)


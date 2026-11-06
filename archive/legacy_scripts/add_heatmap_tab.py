import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# 1. Add imports at the top
imports = """import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, logging, threading, time, os, subprocess
import ctypes  # Native Windows library for ghost mouse
from working import LIMSOrchestrator, Labware, DeckSlot, Pipettor
from gui import GUI as AnalyzerGUI

import xml.etree.ElementTree as ET
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re
"""
code = re.sub(r'import tkinter as tk.*?from gui import GUI as AnalyzerGUI\n', imports, code, flags=re.DOTALL)

# 2. Add self.build_analysis_tab() call
code = code.replace(
    "self.build_workflow_tab()",
    "self.build_workflow_tab()\n        self.build_analysis_tab()"
)

# 3. Add the build_analysis_tab method
new_methods = """
    def build_analysis_tab(self):
        lbl = ttk.Label(self.tab_analysis, text="FOC48 Baseline Heatmap Analysis", font=("Arial", 16, "bold"))
        lbl.pack(pady=20)
        
        desc = ttk.Label(self.tab_analysis, text="Select an FOC48 generated folder to automatically parse all .stats.xml files\\nand generate baseline d0 heatmaps.", justify=tk.CENTER)
        desc.pack(pady=10)
        
        btn_folder = ttk.Button(self.tab_analysis, text="Select FOC48 Data Folder", command=self.run_heatmap_analysis)
        btn_folder.pack(pady=20)

    def run_heatmap_analysis(self):
        folder_path = filedialog.askdirectory(title="Select FOC48 Data Folder")
        if not folder_path: return
        
        import glob
        search_pattern = os.path.join(folder_path, "*.stats.xml")
        stats_files = glob.glob(search_pattern)
        
        if not stats_files:
            messagebox.showinfo("No Files", f"No .stats.xml files found in {folder_path}")
            return
            
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = ['1', '2', '3', '4', '5', '6']
        
        for stats_file in stats_files:
            base_xml = stats_file.replace(".stats.xml", ".xml")
            pix2mm = 28.7
            
            def clean_and_parse(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    xml_data = f.read()
                xml_data = xml_data.replace('encoding="UTF - 8"', 'encoding="UTF-8"').replace('version="1.1"', 'version="1.0"')
                xml_data = re.sub(r'<!.*?>', '', xml_data)
                return ET.fromstring(xml_data)
            
            if os.path.exists(base_xml):
                try:
                    b_root = clean_and_parse(base_xml)
                    p_node = b_root.find("pixel_per_mm")
                    if p_node is not None: pix2mm = float(p_node.text)
                except Exception as e:
                    self.logger.warning(f"Could not read pix2mm: {e}")
            
            try:
                root = clean_and_parse(stats_file)
                df = pd.DataFrame(index=rows, columns=cols, dtype=float)
                for r in rows:
                    for c in cols:
                        w_node = root.find(f"{r}{c}")
                        if w_node is not None:
                            b_pix = w_node.find("baseline")
                            if b_pix is not None:
                                df.at[r, c] = float(b_pix.text) / pix2mm
                                
                plt.figure(figsize=(10, 8))
                sns.heatmap(df, annot=True, fmt=".2f", cmap="coolwarm", vmin=3.5, vmax=4.5, cbar_kws={'label': 'Baseline (mm)'})
                plt.title(f"d0 Measurement: {os.path.basename(stats_file)}\\n(Calculated using {pix2mm} pixels/mm)\\nTarget Range: 3.7mm - 4.2mm", fontsize=14)
                plt.xlabel("Columns")
                plt.ylabel("Rows")
                plt.figtext(0.5, 0.01, "Values between 3.7 and 4.2 are ideal. <3.7 is too small, >4.2 is too large.", ha="center", fontsize=10, bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})
                plt.show()
            except Exception as e:
                self.logger.error(f"Error parsing {stats_file}: {e}")
                messagebox.showerror("Error", f"Failed to process {os.path.basename(stats_file)}\\n{e}")

    def build_ops_tab(self):"""

code = code.replace("    def build_ops_tab(self):", new_methods)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
    
print("Added heatmap tab")

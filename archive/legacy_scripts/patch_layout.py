import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# 1. Patch the Analyzer instantiation
old_analyzer = "self.analyzer = AnalyzerGUI(master=self.tab_analysis)"
new_analyzer = "self.analyzer = AnalyzerGUI(master=self.frame_ca2)"
code = code.replace(old_analyzer, new_analyzer)

# 2. Patch the build_analysis_tab
old_build_tab = """    def build_analysis_tab(self):
        lbl = ttk.Label(self.tab_analysis, text="FOC48 Baseline Heatmap Analysis", font=("Arial", 16, "bold"))
        lbl.pack(pady=20)
        
        desc = ttk.Label(self.tab_analysis, text="Select an FOC48 generated folder to automatically parse all .stats.xml files\\nand generate baseline d0 heatmaps.", justify=tk.CENTER)
        desc.pack(pady=10)
        
        btn_folder = ttk.Button(self.tab_analysis, text="Select FOC48 Data Folder", command=self.run_heatmap_analysis)
        btn_folder.pack(pady=20)"""

new_build_tab = """    def build_analysis_tab(self):
        # Create left and right container boxes
        self.frame_heatmap = ttk.LabelFrame(self.tab_analysis, text="Quality Control (d0 Baseline Heatmaps)")
        self.frame_heatmap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Kinetic Traces (Ca2+ Curves)")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Place heatmap logic in the left box
        lbl = ttk.Label(self.frame_heatmap, text="FOC48 Baseline Heatmaps", font=("Arial", 16, "bold"))
        lbl.pack(pady=20)
        
        desc = ttk.Label(self.frame_heatmap, text="Automatically parses .stats.xml and .xml files\\nto generate Day 0 baseline heatmaps.", justify=tk.CENTER)
        desc.pack(pady=10)
        
        btn_folder = ttk.Button(self.frame_heatmap, text="Select Folder for Heatmaps", command=self.run_heatmap_analysis)
        btn_folder.pack(pady=20)"""

if old_build_tab in code:
    code = code.replace(old_build_tab, new_build_tab)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO FIND OLD BUILD TAB")


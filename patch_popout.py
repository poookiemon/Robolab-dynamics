import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# 1. Remove the old analyzer instantiation from __init__
old_init_call = "        self.analyzer = AnalyzerGUI(master=self.frame_ca2)"
if old_init_call in code:
    code = code.replace(old_init_call, "        # AnalyzerGUI is now launched via pop-out button")

# 2. Add the button to frame_ca2 in build_analysis_tab
old_build_ca2 = """        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Analyze Measurement")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)"""

new_build_ca2 = """        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Analyze Measurement")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        lbl_ca2 = ttk.Label(self.frame_ca2, text="Kinetic Traces & Peak Forces", font=("Arial", 16, "bold"))
        lbl_ca2.pack(pady=5)
        
        desc_ca2 = ttk.Label(self.frame_ca2, text="Launch the full-screen interactive dashboard\\nto analyze measurements and kinetic traces.", justify=tk.CENTER)
        desc_ca2.pack(pady=5)
        
        btn_launch = ttk.Button(self.frame_ca2, text="Launch Dashboard", command=self.launch_analyzer_popout)
        btn_launch.pack(pady=20)"""

if old_build_ca2 in code:
    code = code.replace(old_build_ca2, new_build_ca2)


# 3. Inject the launch_analyzer_popout method
old_methods = """    def build_ops_tab(self):"""

new_methods = """    def launch_analyzer_popout(self):
        popout = ttk.Toplevel(self.root)
        popout.title("Analyze Measurement Dashboard")
        popout.geometry("1600x900")
        
        # Instantiate the AnalyzerGUI inside the new full-screen Toplevel window
        from gui import GUI as AnalyzerGUI
        self.analyzer = AnalyzerGUI(master=popout)

    def build_ops_tab(self):"""

if old_methods in code:
    code = code.replace(old_methods, new_methods)


with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("PATCH SUCCESSFUL")


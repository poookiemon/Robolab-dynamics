import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# Remove pyvista imports if they exist
code = re.sub(r'^import pyvista as pv\n', '', code, flags=re.MULTILINE)
code = re.sub(r'^from vtkmodules.*?\n', '', code, flags=re.MULTILINE)

# Remove the LAUNCH 3D TWIN button
code = re.sub(r'        ttk\.Button\(f_controls, text="LAUNCH 3D TWIN", command=self\.launch_pv_twin\)\.pack\(pady=20\)\n', '', code)

# Remove the launch_pv_twin method entirely
method_pattern = r'    def launch_pv_twin\(self\):.*?(?=\n    def )'
code = re.sub(method_pattern, '', code, flags=re.DOTALL)

# Remove the hook that updates it
code = re.sub(r'        if hasattr\(self, "pv_plotter"\) and self\.pv_plotter: self\.launch_pv_twin\(\)\n', '', code)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)

print("Reverted Tkinter GUI")

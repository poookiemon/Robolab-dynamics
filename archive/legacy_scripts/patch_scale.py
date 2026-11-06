import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# Fix the microscopic scaling
new_base = """        if os.path.exists(base_path):
            try:
                mesh_base = pv.read(base_path)
                mesh_base.scale((1000, 1000, 1000), inplace=True) # Fix Blender Meter to MM export
                self.pv_plotter.add_mesh(mesh_base, color="#3a3a3a", specular=0.5, ambient=0.2)"""

code = re.sub(
    r'        if os\.path\.exists\(base_path\):\n            try:\n                mesh_base = pv\.read\(base_path\)\n                self\.pv_plotter\.add_mesh\(mesh_base, color="#3a3a3a", specular=0\.5, ambient=0\.2\)',
    new_base, code
)

new_plate = """                try:
                    mesh = pv.read(mesh_to_load)
                    mesh.scale((1000, 1000, 1000), inplace=True) # Fix Blender Meter to MM export
                    # Translate mesh to slot coordinates"""

code = re.sub(
    r'                try:\n                    mesh = pv\.read\(mesh_to_load\)\n                    # Translate mesh to slot coordinates',
    new_plate, code
)

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("Scale patched.")

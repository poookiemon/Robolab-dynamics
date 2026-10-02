import trimesh
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os

assets_dir = "/Users/shri/Robolab-dynamics/assets"
if not os.path.exists(assets_dir):
    print("Assets not found in standard dir, using local")
    assets_dir = "assets"

mesh_path = os.path.join(assets_dir, 'ehm_plate.stl')
try:
    mesh = trimesh.load(mesh_path)
    print("Mesh loaded! Faces:", len(mesh.faces))
except Exception as e:
    print("Error:", e)

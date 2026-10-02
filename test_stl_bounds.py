import trimesh
import os

assets_dir = "/Users/shri/Robolab-dynamics/assets"
for f in ["deck_base.stl", "ehm_plate.stl", "tip_rack.stl"]:
    try:
        mesh = trimesh.load(os.path.join(assets_dir, f))
        print(f, "Bounds:", mesh.bounds, "Extents:", mesh.extents)
    except Exception as e:
        print(f, "Error:", e)

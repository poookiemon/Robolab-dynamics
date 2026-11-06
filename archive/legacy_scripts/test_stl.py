import trimesh
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

mesh = trimesh.load('assets/ehm_plate.stl')
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
poly = Poly3DCollection(mesh.triangles, alpha=0.5, facecolors='cyan', edgecolors='black')
ax.add_collection3d(poly)
ax.set_xlim(mesh.bounds[0][0], mesh.bounds[1][0])
ax.set_ylim(mesh.bounds[0][1], mesh.bounds[1][1])
ax.set_zlim(mesh.bounds[0][2], mesh.bounds[1][2])
print("Loaded and generated poly collection successfully!")

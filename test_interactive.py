import pyvista as pv
import time
import numpy as np

p = pv.Plotter()
p.add_mesh(pv.Sphere())
p.show(interactive_update=True)
print("Started interactive")
for i in range(5):
    p.update()
    print("tick")
    time.sleep(0.5)
p.close()

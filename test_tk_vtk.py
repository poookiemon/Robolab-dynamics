import tkinter as tk
from vtkmodules.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
import pyvista as pv

root = tk.Tk()
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True)

vtkWidget = vtkTkRenderWindowInteractor(frame, width=400, height=400)
vtkWidget.pack(fill=tk.BOTH, expand=True)

plotter = pv.Plotter(off_screen=False, notebook=False)
plotter.render_window = vtkWidget.GetRenderWindow()

plotter.add_mesh(pv.Sphere())

vtkWidget.Initialize()
# vtkWidget.Start() # Do not block

def update():
    plotter.render_window.Render()
    root.after(50, update)

root.after(50, update)
print("Started Tkinter loop")
# root.mainloop()

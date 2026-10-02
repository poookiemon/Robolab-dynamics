import tkinter as tk
import pyvista as pv
from pyvista.trame.ui import plotter_ui # Wait, no.

try:
    from pyvista.plotting.tk_interactor import vtkTkRenderWindowInteractor
    print("Has pyvista tk interactor")
except ImportError:
    print("No pyvista tk interactor")


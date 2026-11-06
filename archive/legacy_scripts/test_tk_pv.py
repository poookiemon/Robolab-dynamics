import tkinter as tk
import pyvista as pv

root = tk.Tk()
try:
    from pyvista.plotting.tk_interactor import TkInteractor
    print("Has pyvista.plotting.tk_interactor")
except ImportError:
    print("No TkInteractor in pyvista")
    

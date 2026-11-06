try:
    from pyvista.plotting.tk_interactor import vtkTkRenderWindowInteractor
    print("Has pyvista tk interactor")
except ImportError:
    try:
        from vtkmodules.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
        print("Has vtk tk interactor")
    except ImportError:
        print("No tk interactor found")

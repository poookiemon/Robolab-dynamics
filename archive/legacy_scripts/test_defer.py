import pyvista as pv
from PyQt6.QtWidgets import QApplication, QMainWindow
from pyvistaqt import QtInteractor
from PyQt6.QtCore import QTimer
import sys

app = QApplication(sys.argv)
window = QMainWindow()
plotter = QtInteractor(window)
window.setCentralWidget(plotter.interactor)
window.resize(600, 400)

def draw():
    print("Drawing...")
    plotter.clear_actors()
    plotter.set_background("white")
    plotter.enable_lightkit()
    plotter.add_mesh(pv.Sphere(), color="red")
    plotter.view_isometric()
    plotter.reset_camera()
    print("Done drawing.")

# QTimer.singleShot(500, draw)
draw() # try without defer first

window.show()
QTimer.singleShot(2000, app.quit)
sys.exit(app.exec())

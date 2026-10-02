import pyvista as pv
from PyQt6.QtWidgets import QApplication, QMainWindow
from pyvistaqt import QtInteractor
import sys

app = QApplication(sys.argv)
window = QMainWindow()
plotter = QtInteractor(window)
window.setCentralWidget(plotter.interactor)
window.resize(600, 400)

plotter.clear_actors()
plotter.set_background("white")

mesh = pv.Cube(center=(100, 125, 0), x_length=200, y_length=250, z_length=5)
plotter.add_mesh(mesh, color="gray")

# Camera
plotter.camera_position = [(150, -300, 400), (150, 125, 0), (0, 0, 1)]
plotter.reset_camera_clipping_range()

window.show()
QTimer = __import__('PyQt6.QtCore', fromlist=['QTimer']).QTimer
QTimer.singleShot(2000, app.quit)
sys.exit(app.exec())

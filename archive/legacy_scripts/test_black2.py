import pyvista as pv
from PyQt6.QtWidgets import QApplication, QMainWindow
from pyvistaqt import QtInteractor
import sys

app = QApplication(sys.argv)
window = QMainWindow()
plotter = QtInteractor(window)
window.setCentralWidget(plotter.interactor)
window.resize(600, 400)

plotter.add_mesh(pv.Sphere())
plotter.clear()
plotter.add_mesh(pv.Sphere(), color="red")
plotter.camera_position = [(100, -300, 300), (100, 125, 0), (0, 0, 1)]

window.show()
QTimer = __import__('PyQt6.QtCore', fromlist=['QTimer']).QTimer
QTimer.singleShot(2000, app.quit)
sys.exit(app.exec())

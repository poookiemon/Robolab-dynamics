import pyvista as pv
from PyQt6.QtWidgets import QApplication, QMainWindow
from pyvistaqt import QtInteractor
import sys

app = QApplication(sys.argv)
window = QMainWindow()
plotter = QtInteractor(window)
window.setCentralWidget(plotter.interactor)
window.resize(600, 400)

plotter.set_background("white")
text = pv.Text3D("Slot 1", depth=1.0)
plotter.add_mesh(text, color="black")

window.show()
QTimer = __import__('PyQt6.QtCore', fromlist=['QTimer']).QTimer
QTimer.singleShot(2000, app.quit)
sys.exit(app.exec())

"""Optional PyQt6 interface using the same underlying backend services."""

try:
    from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    QMainWindow = object


class QtMainWindow(QMainWindow):
    """PyQt6 main window implementation."""

    def __init__(self, services=None):
        if not HAS_PYQT6:
            raise ImportError("PyQt6 is not installed. Install via pip install 'robolab-gui[qt]'")
        super().__init__()
        self.setWindowTitle("RoboLab GUI (PyQt6)")
        self.resize(1100, 720)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("RoboLab PyQt6 Interface Active"))
        self.setCentralWidget(central)

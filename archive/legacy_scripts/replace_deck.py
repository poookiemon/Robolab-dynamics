import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# Replace the layout block that adds the checkbox and the plotter
old_block = """        l_layout.addSpacing(20)
        from PyQt6.QtWidgets import QCheckBox
        self.chk_lock = QCheckBox("Lock Camera Orientation")
        self.chk_lock.setChecked(True)
        self.chk_lock.stateChanged.connect(self.draw_3d_deck)
        l_layout.addWidget(self.chk_lock)
        
        l_layout.addSpacing(10)
        l_layout.addWidget(QLabel("--- QUICK JOG ---"))
        btn_home = QPushButton("Home XYZ")
        btn_home.clicked.connect(lambda: self.lims.hw.home_all())
        l_layout.addWidget(btn_home)
        
        self.deck_x = QLineEdit("0")
        self.deck_y = QLineEdit("0")
        self.deck_z = QLineEdit("0")
        btn_go = QPushButton("Go To Coordinates")
        btn_go.clicked.connect(self._deck_jog)
        l_layout.addWidget(QLabel("X:"))
        l_layout.addWidget(self.deck_x)
        l_layout.addWidget(QLabel("Y:"))
        l_layout.addWidget(self.deck_y)
        l_layout.addWidget(QLabel("Z:"))
        l_layout.addWidget(self.deck_z)
        l_layout.addWidget(btn_go)

        layout.addWidget(left_pane, 1)
        self.plotter = QtInteractor(self.tab_deck)
        layout.addWidget(self.plotter.interactor, 3)
        # Defer 3D drawing to fix Mac VTK black screen
        self.draw_3d_deck()
        self.deck_x.setText("200")
        self.deck_y.setText("250")
        self.deck_z.setText("100")
        self._deck_jog()

    def draw_3d_deck(self):"""

new_block = """        l_layout.addSpacing(20)
        
        l_layout.addSpacing(10)
        l_layout.addWidget(QLabel("--- QUICK JOG ---"))
        btn_home = QPushButton("Home XYZ")
        btn_home.clicked.connect(lambda: self.lims.hw.home_all())
        l_layout.addWidget(btn_home)
        
        self.deck_x = QLineEdit("0")
        self.deck_y = QLineEdit("0")
        self.deck_z = QLineEdit("0")
        btn_go = QPushButton("Go To Coordinates")
        btn_go.clicked.connect(self._deck_jog)
        l_layout.addWidget(QLabel("X:"))
        l_layout.addWidget(self.deck_x)
        l_layout.addWidget(QLabel("Y:"))
        l_layout.addWidget(self.deck_y)
        l_layout.addWidget(QLabel("Z:"))
        l_layout.addWidget(self.deck_z)
        l_layout.addWidget(btn_go)

        layout.addWidget(left_pane, 1)
        
        from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view, 3)
        
        self.deck_x.textChanged.connect(lambda: self.draw_deck())
        self.deck_y.textChanged.connect(lambda: self.draw_deck())
        
        self.draw_deck()
        self.deck_x.setText("200")
        self.deck_y.setText("250")
        self.deck_z.setText("100")
        self._deck_jog()

    def draw_deck(self):"""

if old_block in code:
    code = code.replace(old_block, new_block)
    with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
        f.write(code)
    print("PATCH 1 SUCCESSFUL")
else:
    print("FAILED TO MATCH PATCH 1")

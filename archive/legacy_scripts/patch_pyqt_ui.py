import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# 1. Set default camera view to top-down (view_xy) so it's not "tilted"
code = code.replace(
    "self.plotter.add_axes()",
    "self.plotter.add_axes()\n        self.plotter.view_xy()\n        self.plotter.camera.roll = 0"
)

# 2. Add Labware Assignment Combobox
new_deck = """        btn_remove = QPushButton("Remove <-")
        btn_remove.clicked.connect(self.remove_slot)
        l_layout.addWidget(btn_remove)
        
        l_layout.addWidget(QLabel("Assign Labware to Selected Slot:"))
        self.combo_lw = QComboBox()
        if os.path.exists("labware"):
            for f in os.listdir("labware"):
                if f.endswith(".json"): self.combo_lw.addItem(f)
        l_layout.addWidget(self.combo_lw)
        btn_assign = QPushButton("Assign Labware")
        btn_assign.clicked.connect(self.assign_lw)
        l_layout.addWidget(btn_assign)"""

code = code.replace(
    '        btn_remove = QPushButton("Remove <-")\n        btn_remove.clicked.connect(self.remove_slot)\n        l_layout.addWidget(btn_remove)',
    new_deck
)

# Add assign_lw method
assign_lw_method = """    def assign_lw(self):
        sel = self.list_placed.selectedItems()
        if not sel: return
        slot_name = sel[0].text()
        lw_file = self.combo_lw.currentText()
        if lw_file:
            path = os.path.join("labware", lw_file)
            lw = Labware(path)
            self.lims.assign_labware_to_slot(slot_name, lw)
            self.refresh_ui()
"""
code = code.replace("    def place_slot(self):", assign_lw_method + "\n    def place_slot(self):")


# 3. Dilution Calculator improvement
new_calc = """    def build_ops_tab(self):
        # We will patch the calculator in the actual method""" # Actually, let's just write a regex for the calc function.

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Patch 1 Applied")

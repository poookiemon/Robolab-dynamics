import os

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write('''import sys
import os
import time
import json
import logging
import threading
import subprocess
import ctypes
import numpy as np

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QLabel, QLineEdit, QPushButton, QComboBox,
                             QListWidget, QGroupBox, QGridLayout, QMessageBox, QFileDialog, 
                             QPlainTextEdit, QFormLayout, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
import pyvista as pv
from pyvistaqt import QtInteractor

from working import LIMSOrchestrator, Pipettor, Labware

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)

class LIMSPyQtApp(QMainWindow):
    def __init__(self, is_multi=False):
        super().__init__()
        self.setWindowTitle("ROBOLAB DYNAMICS // 3D LIMS")
        self.resize(1200, 800)
        
        self.lims = LIMSOrchestrator(hardware=Pipettor(tip_volume=200.0, multichannel=is_multi))
        self.workflow_sequence = []
        self.speed_var = 1500
        
        self.setup_ui()
        self.lims.load_deck_profile("deck_calibration.json")
        self.placed_slots = list(self.lims.deck_labware.keys())
        self.refresh_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.tab_jog = QWidget()
        self.tab_deck = QWidget()
        self.tab_ops = QWidget()
        self.tab_workflow = QWidget()
        
        self.tabs.addTab(self.tab_jog, "1. Jog & Hardware")
        self.tabs.addTab(self.tab_deck, "2. 3D Deck Designer")
        self.tabs.addTab(self.tab_workflow, "3. Protocol Runner")
        self.tabs.addTab(self.tab_ops, "4. Daily Operations")
        
        self.build_jog_tab()
        self.build_deck_tab()
        self.build_workflow_tab()
        self.build_ops_tab()
        
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(150)
        layout.addWidget(QLabel("Diagnostic Output:"))
        layout.addWidget(self.console)

    def log(self, text):
        self.console.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {text}")

    def build_jog_tab(self):
        layout = QVBoxLayout(self.tab_jog)
        layout.addWidget(QLabel("Jog controls will go here."))
        # Implement full jog tab later

    def build_deck_tab(self):
        layout = QHBoxLayout(self.tab_deck)
        
        left_pane = QWidget()
        l_layout = QVBoxLayout(left_pane)
        l_layout.addWidget(QLabel("Inventory"))
        self.list_unplaced = QListWidget()
        l_layout.addWidget(self.list_unplaced)
        btn_place = QPushButton("Place on Deck ->")
        btn_place.clicked.connect(self.place_slot)
        l_layout.addWidget(btn_place)
        self.list_placed = QListWidget()
        l_layout.addWidget(self.list_placed)
        btn_remove = QPushButton("Remove <-")
        btn_remove.clicked.connect(self.remove_slot)
        l_layout.addWidget(btn_remove)
        
        layout.addWidget(left_pane, 1)
        
        # PyVista 3D Viewer
        self.plotter = QtInteractor(self.tab_deck)
        layout.addWidget(self.plotter.interactor, 3)
        
        self.draw_3d_deck()

    def draw_3d_deck(self):
        self.plotter.clear()
        assets_dir = "/Users/shri/Robolab-dynamics/assets"
        
        base_path = os.path.join(assets_dir, "deck_base.stl")
        if os.path.exists(base_path):
            mesh_base = pv.read(base_path)
            mesh_base.scale((1000, 1000, 1000), inplace=True)
            self.plotter.add_mesh(mesh_base, color="#3a3a3a")
            
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        ehm_path = os.path.join(assets_dir, "ehm_plate.stl")
        tip_path = os.path.join(assets_dir, "tip_rack.stl")
        
        for i, name in enumerate(self.placed_slots):
            slot = self.lims.deck_slots.get(name)
            if not slot: continue
            lw = self.lims.deck_labware.get(name)
            
            mesh_file = None
            if lw and "ehm" in lw.name.lower(): mesh_file = ehm_path
            elif lw and "tip" in lw.name.lower(): mesh_file = tip_path
            
            if mesh_file and os.path.exists(mesh_file):
                mesh = pv.read(mesh_file)
                mesh.scale((1000, 1000, 1000), inplace=True)
                mesh.translate((slot.x_abs, slot.y_abs, slot.z_offset), inplace=True)
                self.plotter.add_mesh(mesh, color=colors[i%len(colors)])
                
        self.plotter.add_axes()

    def place_slot(self):
        sel = self.list_unplaced.selectedItems()
        if not sel: return
        slot_name = sel[0].text()
        self.placed_slots.append(slot_name)
        self.refresh_ui()
        
    def remove_slot(self):
        sel = self.list_placed.selectedItems()
        if not sel: return
        slot_name = sel[0].text()
        if slot_name in self.placed_slots:
            self.placed_slots.remove(slot_name)
        self.refresh_ui()

    def refresh_ui(self):
        self.list_unplaced.clear()
        self.list_placed.clear()
        for slot in self.lims.deck_slots.keys():
            if slot in self.placed_slots:
                self.list_placed.addItem(slot)
            else:
                self.list_unplaced.addItem(slot)
        self.draw_3d_deck()

    def build_workflow_tab(self):
        layout = QVBoxLayout(self.tab_workflow)
        layout.addWidget(QLabel("Workflow logic goes here"))

    def build_ops_tab(self):
        layout = QVBoxLayout(self.tab_ops)
        layout.addWidget(QLabel("Daily Ops goes here"))

def main():
    app = QApplication(sys.argv)
    window = LIMSPyQtApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
''')

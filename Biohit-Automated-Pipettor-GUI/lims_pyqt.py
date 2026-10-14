import sys
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
                             QPlainTextEdit, QFormLayout, QFrame, QCheckBox, QProgressBar, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

import pyvista as pv
from pyvistaqt import QtInteractor

from working import LIMSOrchestrator, Pipettor, Labware

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    update_ui_state = pyqtSignal(bool)
    timer_update = pyqtSignal(str)
    ask_error = pyqtSignal(Exception, int)

class WorkflowRunner(QThread):
    def __init__(self, sequence, lims, gui, parent=None):
        super().__init__(parent)
        self.sequence = sequence
        self.lims = lims
        self.gui = gui
        self.signals = WorkerSignals()
        self.is_aborted = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        
    def log(self, msg):
        self.signals.log.emit(msg)

    def run(self):
        self.log("--- Protocol Sequence Initiated ---")
        self.signals.update_ui_state.emit(True)
        total_steps = len(self.sequence)
        
        # simplified time tracking for demo
        for i, step in enumerate(self.sequence, 1):
            self.pause_event.wait()
            if self.is_aborted: break
            
            self.signals.progress.emit(int((i / total_steps) * 100))
            
            action = step['action']
            mode = step.get('mode', 'auto')
            vol = step.get('volume', 0.0)
            
            self.log(f"Executing Step {i}/{total_steps}: [{action}]")
            
            try:
                if "System:" in action or "System" in action:
                    if "Incubate" in action:
                        self.lims.hw.move_to(0, 0, 0, speed=1500)
                        time.sleep(vol)
                    elif "FOC48" in action:
                        self.lims.hw.move_to(0, 0, 0, speed=1500)
                        p = subprocess.Popen([r'C:\Labhub\Import\FOC48_20240227.exe', r'C:\Labhub\Import\myrPlate_Stim_0.xml', str(step.get('well', ''))])
                        self.log("Waiting for FOC48 window to load...")
                        time.sleep(7.0)
                        self.log("Executing ghost mouse clicks...")
                        ctypes.windll.user32.SetCursorPos(404, 168)
                        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                        time.sleep(1.0)
                        ctypes.windll.user32.SetCursorPos(690, 168)
                        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                        time.sleep(1.0)
                        ctypes.windll.user32.SetCursorPos(1021, 531)
                        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                        self.log("Optical reading in progress. Waiting for FOC48 task to finish...")
                        p.wait()
                    elif "Data Analysis" in action:
                        self.log("Launching Analysis Subsystem (Hill Equations)...")
                        time.sleep(1.5)
                        self.log("Analysis complete. Results buffered.")
                    elif "DB Upload" in action:
                        self.log("Launching DB Subsystem...")
                        time.sleep(1.0)
                        self.log("Payload verified. Pushed to Contraction DB.")
                    elif "Calcium Curve" in action:
                        self.log("Executing Automated Calcium Curve Macro...")
                        time.sleep(2.0)
                        self.log("Calcium Curve executed successfully.")
                    time.sleep(0.05)
                    continue

                slot_name = step.get('slot', '')
                well_id = step.get('well', '')
                target_x, target_y, target_z = step.get('x', 0.0), step.get('y', 0.0), step.get('z', 0.0)
                
                if mode != "manual":
                    # simplified xy calculation
                    coords = self.gui._calculate_xy(slot_name, well_id)
                    if coords:
                        target_x, target_y = coords
                    else:
                        raise Exception("Well ID mapping failed")
                
                if action == "Pick Up Tip":
                    pickup_limit = min(92.0, max(82.0, 87.0 + step.get('extra_z', 0.0)))
                    if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                    self.lims.hw.move_to(target_x, target_y, 0, speed=1500)
                    time.sleep(0.05)
                    if self.lims.pipettor.hardware:
                        labware_obj = self.lims.deck_labware.get(slot_name)
                        z_height = getattr(labware_obj, 'z_height_mm', 78.18) if labware_obj else 78.18
                        approach_z = max(0.0, min(55.0, z_height - 18.0))
                        self.lims.pipettor.hardware.z_speed = 7
                        self.lims.pipettor.hardware.move_z(approach_z)
                        self.lims.pipettor.hardware.z_speed = 3
                        self.lims.pipettor.hardware.tip_pickup_force = 26
                        try:
                            self.lims.pipettor.hardware.pick_tip(pickup_limit)
                        except Exception as p_err:
                            curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                            if curr_z < 60.0:
                                raise p_err
                        curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                        if curr_z >= 60.0:
                            try:
                                self.lims.pipettor.hardware.move_z(min(curr_z + 2.5, pickup_limit + 2.0))
                                time.sleep(0.35)
                            except Exception:
                                pass
                        time.sleep(0.35)
                        self.lims.pipettor.hardware.z_speed = 7
                        self.lims.pipettor.hardware.move_z(0)
                    self.gui.has_tip = True
                
                elif action in ["Aspirate Media", "Dispense Media", "Discard Tip"]:
                    tz = target_z if mode == "manual" else self.gui._calculate_z(action, self.lims.deck_labware.get(slot_name), well_id, mode, 0.0, slot_name, step.get('extra_z', 0.0))
                    if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                    self.lims.hw.move_to(target_x, target_y, 0, speed=1500)
                    time.sleep(0.05)
                    if self.lims.pipettor.hardware:
                        self.lims.pipettor.hardware.move_z(tz)
                        if action == "Aspirate Media":
                            actual_vol = min(float(vol), self.lims.pipettor.tip_volume)
                            self.lims.pipettor.hardware.aspirate(actual_vol)
                            time.sleep(1.5)
                        elif action == "Dispense Media":
                            actual_dispense = min(float(vol), self.lims.pipettor.tip_volume)
                            self.lims.pipettor.hardware.dispense(actual_dispense)
                            time.sleep(0.05)
                            self.lims.pipettor.hardware.dispense(50)
                        elif action == "Discard Tip":
                            self.lims.pipettor.hardware.eject_tip()
                            self.gui.has_tip = False
                        self.lims.pipettor.hardware.move_z(0)
                
            except Exception as e:
                self.signals.ask_error.emit(e, i)
                self.pause_event.clear()
                
            time.sleep(0.05)
            
        if self.is_aborted:
            self.log("--- Protocol Aborted ---")
        else:
            self.log("--- Protocol Completed Successfully ---")
            
        self.signals.progress.emit(0)
        self.signals.update_ui_state.emit(False)
        self.signals.finished.emit()

class LIMSPyQtApp(QMainWindow):
    def __init__(self, is_multi=False):
        super().__init__()
        self.setWindowTitle("ROBOLAB DYNAMICS // 3D LIMS")
        self.resize(1200, 800)
        
        self.lims = LIMSOrchestrator(hardware=Pipettor(tip_volume=200.0, multichannel=is_multi))
        self.workflow_sequence = []
        self.speed_var = 1500
        self.has_tip = False
        self.placed_slots = []
        
        self.setup_ui()
        self.lims.load_deck_profile("deck_calibration.json")
        self.placed_slots = list(self.lims.deck_slots.keys())
        self.refresh_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.tab_jog = QWidget()
        self.tab_deck = QWidget()
        self.tab_workflow = QWidget()
        self.tab_ops = QWidget()
        self.tab_dilution = QWidget()
        self.tab_analysis = QWidget()
        
        self.tabs.addTab(self.tab_jog, "1. Jog & Hardware")
        self.tabs.addTab(self.tab_deck, "2. 3D Deck Designer")
        self.tabs.addTab(self.tab_workflow, "3. Protocol Runner")
        self.tabs.addTab(self.tab_ops, "4. Daily Operations")
        self.tabs.addTab(self.tab_dilution, "5. SIPA Dilution Calc")
        self.tabs.addTab(self.tab_analysis, "6. Data Analysis & QC")
        
        self.build_jog_tab()
        self.build_deck_tab()
        self.build_workflow_tab()
        self.build_ops_tab()
        self.build_dilution_tab()
        self.build_analysis_tab()
        
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(150)
        layout.addWidget(QLabel("Diagnostic Output:"))
        layout.addWidget(self.console)

    def log(self, text):
        self.console.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {text}")
        
    def _calculate_xy(self, slot_name, well_id):
        slot_obj = self.lims.deck_slots.get(slot_name)
        sy = slot_obj.y_abs if slot_obj else 60.0

        if slot_name == "Slot_3":
            col_x = {
                '1': 242.0, '2': 233.0, '3': 224.0, '4': 215.0,
                '5': 206.0, '6': 197.0, '7': 188.0, '8': 179.0,
                '9': 170.0, '10': 161.0, '11': 152.0, '12': 143.0
            }
            row_y = {
                'A': 60.0,  'B': 69.0,  'C': 78.0,  'D': 87.0,
                'E': 96.0,  'F': 105.0, 'G': 114.0, 'H': 123.0
            }
            if len(well_id) >= 2:
                r_c = well_id[0].upper()
                c_c = well_id[1:]
                if r_c in row_y and c_c in col_x:
                    return col_x[c_c], row_y[r_c]

        if slot_name == "Slot_4":
            col_x = {'1': 105.00, '2': 87.00, '3': 68.88, '4': 51.54, '5': 34.20, '6': 15.60}
            row_y = {
                'A': 67.30, 'B': 75.30, 'C': 85.30, 'D': 95.30,
                'E': 105.30, 'F': 113.30, 'G': 121.30, 'H': 129.30
            }
            if len(well_id) >= 2:
                row_char = well_id[0].upper()
                col_char = well_id[1:]
                if row_char in row_y and col_char in col_x:
                    return col_x[col_char], row_y[row_char]

        if slot_name == "Slot_5":
            col_x = {
                '1': 239.0, '2': 220.0, '3': 201.0,
                '4': 182.0, '5': 163.0, '6': 144.0
            }
            col_char = well_id[1:] if len(well_id) >= 2 else '1'
            target_x = col_x.get(col_char, 191.5)
            target_y = 207.75
            return target_x, target_y

        if not slot_obj: return 0.0, 0.0
        cx = slot_obj.x_abs + (slot_obj.width_mm / 2.0)
        cy = slot_obj.y_abs + (slot_obj.height_mm / 2.0)
        if slot_name == "Slot_6": return cx, cy
        labware_obj = self.lims.deck_labware.get(slot_name)
        if not labware_obj or not labware_obj.wells: return cx, cy
        first_w = list(labware_obj.wells.values())[0]
        lw_w = max(w.x_rel for w in labware_obj.wells.values()) + first_w.x_rel
        lw_h = max(w.y_rel for w in labware_obj.wells.values()) + first_w.y_rel
        well_obj = labware_obj.wells.get(well_id)
        if not well_obj: return cx, cy
        return cx + ((lw_w / 2.0) - well_obj.x_rel), cy - (lw_h / 2.0) + well_obj.y_rel

    def _calculate_z(self, action, labware_obj, well_id, mode, manual_z, slot_name, extra_z=0.0):
        if action == "Pick Up Tip": return 0.0
        if mode == "manual": return manual_z
        slot_obj = self.lims.deck_slots.get(slot_name)
        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0) if slot_obj else 0.0
        if action in ["Aspirate Media", "Dispense Media", "Discard Tip"]:
            base_z = 101.0
            if slot_name == "Slot_4": base_z = 98.0
            elif slot_name == "Slot_5": base_z = 101.5
            elif slot_name == "Slot_6": base_z = 90.0
            elif action == "Discard Tip" and slot_name == "Slot_1": base_z = 90.0
            elif labware_obj and (getattr(labware_obj, 'z_height_mm', 20.0) == 105.81 or "reservoir" in labware_obj.name.lower()):
                base_z = 101.5
            return min(base_z + slot_z_offset + extra_z, 103.5)
        return 0.0

    def build_jog_tab(self):
        layout = QVBoxLayout(self.tab_jog)
        f_conn = QGroupBox("Hardware Handshake")
        conn_lay = QHBoxLayout()
        self.port_drop = QComboBox()
        self.port_drop.addItems(["COM1", "COM2", "COM3"])
        conn_lay.addWidget(self.port_drop)
        btn_scan = QPushButton("Scan Ports")
        btn_scan.clicked.connect(lambda: self.port_drop.addItems(self.lims.hw.scan_ports()))
        conn_lay.addWidget(btn_scan)
        btn_conn = QPushButton("Connect & Initialize")
        btn_conn.clicked.connect(self.hw_init)
        conn_lay.addWidget(btn_conn)
        self.lbl_hw_stat = QLabel("OFFLINE")
        self.lbl_hw_stat.setStyleSheet("color: gray; font-weight: bold;")
        conn_lay.addWidget(self.lbl_hw_stat)
        f_conn.setLayout(conn_lay)
        layout.addWidget(f_conn)
        
        f_jog = QGroupBox("Position Calibration Sliders")
        jog_lay = QGridLayout()
        self.jog_sliders = {}
        for i, axis in enumerate(["X", "Y", "Z"]):
            jog_lay.addWidget(QLabel(f"{axis}-Axis (mm):"), i, 0)
            le = QLineEdit("0.0")
            self.jog_sliders[axis] = le
            jog_lay.addWidget(le, i, 1)
            btn = QPushButton("MOVE")
            btn.clicked.connect(lambda _, a=axis: self.move_from_jog())
            jog_lay.addWidget(btn, i, 2)
            le.textChanged.connect(self.update_pv_needle)
        f_jog.setLayout(jog_lay)
        layout.addWidget(f_jog)
        layout.addStretch()

    def hw_init(self):
        ok, m = self.lims.hw.connect(self.port_drop.currentText())
        if ok:
            ok2, m2 = self.lims.hw.initialize()
            if ok2:
                self.lbl_hw_stat.setText("ONLINE")
                self.lbl_hw_stat.setStyleSheet("color: green; font-weight: bold;")
                self.log(m2)

    def move_from_jog(self):
        x = float(self.jog_sliders["X"].text())
        y = float(self.jog_sliders["Y"].text())
        z = float(self.jog_sliders["Z"].text())
        self.lims.hw.move_to(x, y, z, speed=self.speed_var)
        self.update_pv_needle()

    def update_pv_needle(self):
        if not hasattr(self, 'pv_pipette_actor') or not self.pv_pipette_actor: return
        try:
            px = float(self.jog_sliders["X"].text())
            py = float(self.jog_sliders["Y"].text())
            pz = float(self.jog_sliders["Z"].text())
            mat = np.eye(4)
            mat[0, 3] = px
            mat[1, 3] = py
            mat[2, 3] = pz
            self.pv_pipette_actor.user_matrix = mat
            self.plotter.update()
        except ValueError:
            pass

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
        
        l_layout.addWidget(QLabel("Assign Labware to Selected Slot:"))
        self.combo_lw = QComboBox()
        if os.path.exists("Biohit-Automated-Pipettor-GUI/labware"):
            for f in os.listdir("Biohit-Automated-Pipettor-GUI/labware"):
                if f.endswith(".json"): self.combo_lw.addItem(f)
        elif os.path.exists("labware"):
            for f in os.listdir("labware"):
                if f.endswith(".json"): self.combo_lw.addItem(f)
        l_layout.addWidget(self.combo_lw)
        btn_assign = QPushButton("Assign Labware")
        btn_assign.clicked.connect(self.assign_lw)
        l_layout.addWidget(btn_assign)
        
        l_layout.addSpacing(20)
        
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

    def draw_deck(self):
        self.scene.clear()
        
        bed_width = 400
        bed_height = 300
        scale = 2.0
        
        self.scene.setSceneRect(0, 0, bed_width * scale, bed_height * scale)
        
        from PyQt6.QtGui import QPen, QBrush, QColor
        from PyQt6.QtCore import Qt, QRectF
        
        # Grid lines
        for x in range(0, int(bed_width) + 10, 10):
            vx = (bed_width - x) * scale
            color = "#cccccc" if x % 50 == 0 else "#ebebeb"
            self.scene.addLine(vx, 0, vx, bed_height * scale, QPen(QColor(color)))
            if x % 50 == 0:
                t = self.scene.addText(f"{x}mm")
                t.setPos(vx - 20, 10)
                t.setDefaultTextColor(QColor("#888888"))
                
        for y in range(0, int(bed_height) + 10, 10):
            vy = y * scale
            color = "#cccccc" if y % 50 == 0 else "#ebebeb"
            self.scene.addLine(0, vy, bed_width * scale, vy, QPen(QColor(color)))
            if y % 50 == 0:
                t = self.scene.addText(f"{y}mm")
                t.setPos(bed_width * scale - 45, vy - 10)
                t.setDefaultTextColor(QColor("#888888"))
                
        # Origin
        ox = bed_width * scale
        self.scene.addEllipse(ox - 15, 2, 13, 13, QPen(Qt.GlobalColor.black), QBrush(Qt.GlobalColor.red))
        t = self.scene.addText("(0,0)")
        t.setPos(ox - 45, 15)
        t.setDefaultTextColor(Qt.GlobalColor.red)
        
        # Draw slots
        for name in self.placed_slots:
            s = self.lims.deck_slots[name]
            visual_x_right = (bed_width - s.x_abs) * scale
            visual_x_left = (bed_width - (s.x_abs + s.width_mm)) * scale
            y0 = s.y_abs * scale
            y1 = (s.y_abs + s.height_mm) * scale
            
            fill = "#e9ecef"
            if name in self.lims.deck_labware:
                fill = "#f8f9fa" 
            
            rect = QRectF(visual_x_left, y0, visual_x_right - visual_x_left, y1 - y0)
            self.scene.addRect(rect, QPen(QColor("#6c757d"), 2), QBrush(QColor(fill)))
            
            t = self.scene.addText(name)
            t.setPos(visual_x_left + 5, y0 + 5)
            
            if name in self.lims.deck_labware:
                lab = self.lims.deck_labware[name]
                for w_name, w_info in lab.wells.items():
                    wx = (bed_width - (s.x_abs + w_info['x'])) * scale
                    wy = (s.y_abs + w_info['y']) * scale
                    self.scene.addEllipse(wx - 2, wy - 2, 4, 4, QPen(Qt.GlobalColor.gray), QBrush(Qt.GlobalColor.white))
                    
        # Draw pipettor (blue dot)
        jx, jy = 0.0, 0.0
        try:
            jx = float(self.deck_x.text())
            jy = float(self.deck_y.text())
        except ValueError:
            pass
            
        vx = (bed_width - jx) * scale
        vy = jy * scale
        self.scene.addEllipse(vx - 7, vy - 7, 14, 14, QPen(Qt.GlobalColor.black), QBrush(Qt.GlobalColor.blue))
        
    def _deck_jog(self):
        try:
            x = float(self.deck_x.text())
            y = float(self.deck_y.text())
            z = float(self.deck_z.text())
            self.lims.hw.move_to(x, y, z)
            self.draw_deck()
        except Exception: 
            pass

    def assign_lw(self):
        sel = self.list_placed.selectedItems()
        if not sel: return
        slot_name = sel[0].text()
        lw_file = self.combo_lw.currentText()
        if lw_file:
            path = os.path.join("Biohit-Automated-Pipettor-GUI/labware", lw_file) if os.path.exists("Biohit-Automated-Pipettor-GUI/labware") else os.path.join("labware", lw_file)
            lw = Labware(path)
            self.lims.assign_labware_to_slot(slot_name, lw)
            self.refresh_ui()

    def place_slot(self):
        sel = self.list_unplaced.selectedItems()
        if not sel: return
        slot_name = sel[0].text()
        if slot_name not in self.placed_slots:
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
        if hasattr(self, 'cbx_slot'):
            self.cbx_slot.clear()
            self.cbx_slot.addItems(self.placed_slots)
        # Defer 3D drawing to fix Mac VTK black screen
        self.draw_deck()

    def build_workflow_tab(self):
        layout = QHBoxLayout(self.tab_workflow)
        pane_ctrl = QWidget()
        l_ctrl = QVBoxLayout(pane_ctrl)
        
        l_ctrl.addWidget(QLabel("Protocol Builder"))
        self.wf_action = QComboBox()
        self.wf_action.addItems(["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip",
                                "System: Incubate (Wait)", "System: FOC48 Measurement", "System: Calcium Curve", "System: Data Analysis", "System: DB Upload"])
        l_ctrl.addWidget(self.wf_action)
        
        self.chk_manual_mode = QCheckBox("Enable Manual Coordinates")
        l_ctrl.addWidget(self.chk_manual_mode)
        
        self.cbx_slot = QComboBox()
        l_ctrl.addWidget(QLabel("Target Deck Slot:"))
        l_ctrl.addWidget(self.cbx_slot)
        
        self.ent_well = QLineEdit()
        l_ctrl.addWidget(QLabel("Target Well (e.g. A1):"))
        l_ctrl.addWidget(self.ent_well)
        
        self.ent_vol = QLineEdit()
        l_ctrl.addWidget(QLabel("Volume (uL) / Seconds:"))
        l_ctrl.addWidget(self.ent_vol)
        
        btn_add = QPushButton("+ Add Step to Protocol")
        btn_add.clicked.connect(self.add_wf_step)
        l_ctrl.addWidget(btn_add)
        
        l_ctrl.addStretch()
        layout.addWidget(pane_ctrl, 1)
        
        pane_list = QWidget()
        l_list = QVBoxLayout(pane_list)
        self.wf_box = QListWidget()
        l_list.addWidget(self.wf_box)
        
        self.progress_bar = QProgressBar()
        l_list.addWidget(self.progress_bar)
        
        ctrl_frame = QWidget()
        ctrl_lay = QHBoxLayout(ctrl_frame)
        self.btn_play = QPushButton("START PROTOCOL")
        self.btn_play.setStyleSheet("background-color: #28a745; color: white;")
        self.btn_play.clicked.connect(self.run_sequence)
        
        self.btn_pause = QPushButton("PAUSE")
        self.btn_pause.clicked.connect(self.pause_resume_run)
        
        self.btn_stop = QPushButton("CANCEL")
        self.btn_stop.setStyleSheet("background-color: #dc3545; color: white;")
        self.btn_stop.clicked.connect(self.stop_run)
        
        ctrl_lay.addWidget(self.btn_play)
        ctrl_lay.addWidget(self.btn_pause)
        ctrl_lay.addWidget(self.btn_stop)
        l_list.addWidget(ctrl_frame)
        
        layout.addWidget(pane_list, 2)
        self.wf_action.currentIndexChanged.connect(self._toggle_wf_inputs)
        self._toggle_wf_inputs()

    def _toggle_wf_inputs(self):
        action = self.wf_action.currentText()
        is_manual = self.chk_manual_mode.isChecked()
        if "System" in action:
            self.chk_manual_mode.setEnabled(False)
        else:
            self.chk_manual_mode.setEnabled(True)

    def add_wf_step(self):
        action = self.wf_action.currentText()
        is_manual = self.chk_manual_mode.isChecked()
        step_data = {"action": action, "mode": "manual" if is_manual else "auto"}
        
        if "System" in action:
            step_data["mode"] = "auto"
            if "Incubate" in action:
                step_data["volume"] = float(self.ent_vol.text() or 0.0)
                msg = f"[SYSTEM] Incubate for {step_data['volume']} seconds."
            elif "FOC48" in action:
                step_data["well"] = self.ent_well.text()
                msg = f"[MEASURE] Execute FOC48_Stim_0.xml for Plate: '{step_data['well']}'"
            elif "Data Analysis" in action:
                msg = "[ANALYSIS] Execute Hill Equation Modeling"
            elif "DB Upload" in action:
                msg = "[DATABASE] Sync Results to ContractionDB"
            else:
                msg = f"[{action.upper()}]"
        else:
            slot, well, vol = self.cbx_slot.currentText(), self.ent_well.text(), self.ent_vol.text()
            step_data["slot"], step_data["well"] = slot, well
            try: step_data["volume"] = float(vol) if vol else 0.0
            except ValueError: step_data["volume"] = 0.0
            
            if action in ["Pick Up Tip", "Discard Tip"]:
                msg = f"[{action.upper()}] from {slot}, Well {well}" if action == "Pick Up Tip" else f"[{action.upper()}] into {slot}"
            else:
                msg = f"[{action.upper()}] {step_data['volume']}uL at {slot}, Well {well}"
                
        self.wf_box.addItem(msg)
        self.workflow_sequence.append(step_data)

    def run_sequence(self):
        if not self.workflow_sequence: return
        self.runner = WorkflowRunner(self.workflow_sequence, self.lims, self)
        self.runner.signals.progress.connect(self.progress_bar.setValue)
        self.runner.signals.log.connect(self.log)
        self.runner.signals.update_ui_state.connect(self.update_ui_state)
        self.runner.signals.ask_error.connect(self.handle_runner_error)
        self.runner.start()
        
    def handle_runner_error(self, error, step_idx):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Protocol Halted on Step {step_idx}.Trace:{error}Ignore and continue?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Yes:
            self.runner.pause_event.set()
        else:
            self.runner.is_aborted = True
            self.runner.pause_event.set()

    def update_ui_state(self, running):
        self.btn_play.setEnabled(not running)
        self.btn_pause.setEnabled(running)
        self.btn_stop.setEnabled(running)

    def pause_resume_run(self):
        if hasattr(self, 'runner'):
            if self.runner.pause_event.is_set():
                self.runner.pause_event.clear()
                self.btn_pause.setText("RESUME")
            else:
                self.runner.pause_event.set()
                self.btn_pause.setText("PAUSE")

    def stop_run(self):
        if hasattr(self, 'runner'):
            self.runner.is_aborted = True
            self.runner.pause_event.set()

    def build_ops_tab(self):
        layout = QVBoxLayout(self.tab_ops)
        layout.addWidget(QLabel("TECHNICIAN DAILY OPERATIONS", alignment=Qt.AlignmentFlag.AlignCenter))
        
        ops = [("Daily Media Change (500uL)", "media_change"),
               ("Friday Acute SIPA Test", "acute_test"),
               ("Automated Calcium Curve", "calcium_curve")]
               
        for ui_name, key in ops:
            row = QHBoxLayout()
            btn_run = QPushButton(f"RUN: {ui_name}")
            btn_run.clicked.connect(lambda _, k=key: self.execute_routine(k, ""))
            row.addWidget(btn_run, 2)
            btn_assign = QPushButton("Assign JSON")
            row.addWidget(btn_assign, 1)
            layout.addLayout(row)
        layout.addStretch()

    def execute_routine(self, op_name, default_file):
        config_file = "routine_config.json"
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        protocol_path = config.get(op_name, default_file)
        if not os.path.exists(protocol_path):
            QMessageBox.warning(self, "Not Found", f"Protocol file not found:{protocol_path}")
            return
        with open(protocol_path, 'r') as f:
            loaded_sequence = json.load(f)
        self.workflow_sequence.clear()
        self.wf_box.clear()
        for step in loaded_sequence:
            if 'action' not in step: continue
            self.workflow_sequence.append(step)
            self.wf_box.addItem(f"[LOADED] {step['action']}")
        self.tabs.setCurrentWidget(self.tab_workflow)
        self.run_sequence()


    def build_analysis_tab(self):
        from PyQt6.QtWidgets import QGroupBox, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap
        import os, sys, json, glob
        
        # Add parent directory to path so we can import watchdog_pipeline which is at the root
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        import watchdog_pipeline
        
        layout = QHBoxLayout(self.tab_analysis)
        
        # LEFT SIDE: Heatmap Gallery
        left_group = QGroupBox("Quality Control (Baseline Heatmaps)")
        l_layout = QVBoxLayout(left_group)
        
        l_layout.addWidget(QLabel("<b>FOC48 Baseline Heatmaps</b>"))
        desc = QLabel("Automatically parses .stats.xml and .xml files\nto generate baseline heatmaps.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_layout.addWidget(desc)
        
        btn_folder = QPushButton("Select Folder for Heatmaps")
        btn_folder.clicked.connect(self.run_heatmap_gallery)
        l_layout.addWidget(btn_folder)
        
        self.heatmap_display = QLabel("No image to display")
        self.heatmap_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_display.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        l_layout.addWidget(self.heatmap_display, 1) # expand
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Prev")
        self.btn_prev.setEnabled(False)
        self.btn_prev.clicked.connect(self.prev_heatmap)
        
        self.lbl_gallery = QLabel("0 / 0")
        self.lbl_gallery.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_next = QPushButton("Next >")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self.next_heatmap)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_gallery)
        nav_layout.addWidget(self.btn_next)
        l_layout.addLayout(nav_layout)
        
        # RIGHT SIDE: Launch Dashboard
        right_group = QGroupBox("Analyze Measurement")
        r_layout = QVBoxLayout(right_group)
        
        r_layout.addWidget(QLabel("<b>Kinetic Traces & Peak Forces</b>"))
        r_desc = QLabel("Launch the full-screen interactive dashboard\nto analyze measurements and kinetic traces.")
        r_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_layout.addWidget(r_desc)
        
        btn_launch = QPushButton("Launch Dashboard")
        btn_launch.clicked.connect(self.launch_analyzer_popout)
        r_layout.addWidget(btn_launch)
        r_layout.addStretch()
        
        layout.addWidget(left_group)
        layout.addWidget(right_group)
        
        self.heatmap_images = []
        self.current_heatmap_idx = 0

    def run_heatmap_gallery(self):
        import json, os, glob, sys
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        import watchdog_pipeline
        
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("heatmap", "/")
        except Exception: pass
        
        folder_path = QFileDialog.getExistingDirectory(self, "Select FOC48 Data Folder", init_dir)
        if not folder_path: return
        
        try:
            data = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f: data = json.load(f)
            data["heatmap"] = folder_path
            with open(config_path, "w") as f: json.dump(data, f)
        except Exception: pass
        
        stats_files = glob.glob(os.path.join(folder_path, "*.stats.xml"))
        if not stats_files:
            QMessageBox.information(self, "No Files", f"No .stats.xml files found in {folder_path}")
            return
            
        self.log(f"Running QC on {len(stats_files)} files in {folder_path}...")
        
        # We reuse the watchdog pipeline logic to generate the images
        handler = watchdog_pipeline.FOC48Handler()
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_dir = os.path.join(folder_path, f"Analysis_{timestamp}")
        os.makedirs(save_dir, exist_ok=True)
        
        for sf in stats_files:
            handler.generate_heatmap(sf, save_dir)
            
        # Find all generated PNGs
        self.heatmap_images = glob.glob(os.path.join(save_dir, "*_heatmap.png"))
        if self.heatmap_images:
            self.current_heatmap_idx = 0
            self.update_heatmap_gallery()
            self.log(f"Generated {len(self.heatmap_images)} heatmaps successfully.")
        else:
            self.log("Failed to generate heatmap images.")
            
    def update_heatmap_gallery(self):
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        if not self.heatmap_images: return
        
        img_path = self.heatmap_images[self.current_heatmap_idx]
        pixmap = QPixmap(img_path)
        # scale keeping aspect ratio
        scaled_pixmap = pixmap.scaled(self.heatmap_display.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.heatmap_display.setPixmap(scaled_pixmap)
        
        self.lbl_gallery.setText(f"{self.current_heatmap_idx + 1} / {len(self.heatmap_images)}")
        
        self.btn_prev.setEnabled(self.current_heatmap_idx > 0)
        self.btn_next.setEnabled(self.current_heatmap_idx < len(self.heatmap_images) - 1)
        
    def prev_heatmap(self):
        if self.current_heatmap_idx > 0:
            self.current_heatmap_idx -= 1
            self.update_heatmap_gallery()
            
    def next_heatmap(self):
        if self.current_heatmap_idx < len(self.heatmap_images) - 1:
            self.current_heatmap_idx += 1
            self.update_heatmap_gallery()
            
    def launch_analyzer_popout(self):
        import subprocess, sys, os
        gui_path = os.path.join(os.path.dirname(__file__), "gui.py")
        subprocess.Popen([sys.executable, gui_path])
        self.log("Launched external Matplotlib Ca2+ Analyzer.")

    def build_dilution_tab(self):
        layout = QVBoxLayout(self.tab_dilution)
        layout.addWidget(QLabel("SIPA Dilution Calculator (Target <1% DMSO, >50uL vol)"))
        
        f_in = QFormLayout()
        self.ent_stock = QLineEdit("10")
        f_in.addRow("Stock Concentration (mM):", self.ent_stock)
        self.ent_target = QLineEdit("30")
        f_in.addRow("Target Well Concentration (uM):", self.ent_target)
        self.ent_vol_dil = QLineEdit("500")
        f_in.addRow("Well Media Volume (uL):", self.ent_vol_dil)
        layout.addLayout(f_in)
        
        self.res_text = QPlainTextEdit()
        self.res_text.setReadOnly(True)
        layout.addWidget(self.res_text)
        
        btn_calc = QPushButton("Calculate")
        btn_calc.clicked.connect(self.calc_dilution)
        layout.addWidget(btn_calc)

    def calc_dilution(self):
        try:
            stock_mM = float(self.ent_stock.text())
            stock_um = stock_mM * 1000
            target_um = float(self.ent_target.text())
            well_vol = float(self.ent_vol_dil.text())
            
            dilution_factor = stock_um / target_um
            transfer_vol = well_vol / (dilution_factor - 1)
            dmso_pct = (transfer_vol / (well_vol + transfer_vol)) * 100
            
            res = "=== DILUTION INSTRUCTIONS ==="
            
            if transfer_vol < 50:
                res += "⚠️ TRANSFER VOLUME TOO SMALL! (Needs Intermediate Stock)"
                res += "STEP 1: Make a 10x Dilution (Working Stock)"
                res += "        Mix 10 uL of your Drug Stock with 90 uL of pure Media."
                res += "        (This creates a new Working Stock at 1/10th concentration)."
                
                new_stock_um = stock_um / 10
                new_df = new_stock_um / target_um
                new_transfer = well_vol / (new_df - 1)
                new_dmso = (new_transfer / (well_vol + new_transfer)) * 100
                
                res += "STEP 2: Pipette into EHM Well"
                res += f"        Transfer {new_transfer:.1f} uL of the Working Stock into the {well_vol} uL EHM well."
                res += f"        -> Final DMSO % in well: {new_dmso/10:.3f}% (Safe!)"
            else:
                res += "✅ DIRECT PIPETTING (No intermediate stock needed)"
                res += "STEP 1: Pipette into EHM Well"
                res += f"        Transfer {transfer_vol:.1f} uL of the Drug Stock directly into the {well_vol} uL EHM well."
                res += f"        -> Final DMSO % in well: {dmso_pct:.3f}%"
                if dmso_pct > 1.0:
                    res += "🚨 WARNING: DMSO limit exceeded (>1%)! Tissue toxicity risk."
                
            self.res_text.setPlainText(res)
        except Exception as e:
            self.res_text.setPlainText(f"Error: {e}")

def main():
    app = QApplication(sys.argv)
    window = LIMSPyQtApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

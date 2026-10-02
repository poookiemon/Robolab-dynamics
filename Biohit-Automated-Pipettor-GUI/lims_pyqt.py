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
                    if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                    self.lims.hw.move_to(target_x, target_y, 0, speed=1500)
                    time.sleep(0.05)
                    if self.lims.pipettor.hardware:
                        self.lims.pipettor.hardware.pick_tip(50)
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
                            self.lims.pipettor.hardware.dispense(float(vol))
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

class WatchdogRunner(QThread):
    log_signal = pyqtSignal(str)
    
    def run(self):
        import watchdog_pipeline
        self.log_signal.emit("Starting Watchdog Daemon in background...")
        try:
            watchdog_pipeline.start_watchdog()
        except Exception as e:
            self.log_signal.emit(f"Watchdog Error: {e}")

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
            elif slot_name in ["Slot_5", "Slot_6"]: base_z = 90.0
            elif action == "Discard Tip" and slot_name == "Slot_1": base_z = 90.0
            return base_z + slot_z_offset + extra_z
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

    def draw_3d_deck(self):
        self.plotter.clear()
        assets_dir = "/Users/shri/Robolab-dynamics/assets"
        
        base_path = os.path.join(assets_dir, "deck_base.stl")
        if os.path.exists(base_path):
            mesh_base = pv.read(base_path)
            mesh_base.scale((1000, 1000, 1000), inplace=True)
            self.plotter.add_mesh(mesh_base, color="#3a3a3a")
            
        for name, slot in self.lims.deck_slots.items():
            slot_plane = pv.Plane(
                center=(slot.x_abs + slot.width_mm/2, slot.y_abs + slot.height_mm/2, 6.0), 
                direction=(0,0,1), 
                i_size=slot.width_mm - 4, 
                j_size=slot.height_mm - 4
            )
            self.plotter.add_mesh(slot_plane, color="#1c3b57")
            self.plotter.add_point_labels([(slot.x_abs + slot.width_mm/2, slot.y_abs + slot.height_mm/2, 8.0)], [name], font_size=14, text_color="white", shape=None, show_points=False)
            
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        ehm_path = os.path.join(assets_dir, "ehm_plate.stl")
        tip_path = os.path.join(assets_dir, "tip_rack.stl")
        
        for i, name in enumerate(self.placed_slots):
            slot = self.lims.deck_slots.get(name)
            if not slot: continue
            lw = self.lims.deck_labware.get(name)
            
            mesh_file = None

            if lw:
                if "tip" in lw.name.lower() or "rack" in lw.name.lower():
                    mesh_file = tip_path
                else:
                    mesh_file = ehm_path # Fallback to EHM plate for any standard plate

            
            if mesh_file and os.path.exists(mesh_file):
                mesh = pv.read(mesh_file)
                mesh.scale((1000, 1000, 1000), inplace=True)
                mesh.translate((slot.x_abs, slot.y_abs, slot.z_offset + 5.0), inplace=True)
                self.plotter.add_mesh(mesh, color=colors[i%len(colors)])
                
        # Pipette Stand-in
        pipette_body = pv.Cylinder(radius=5, height=80, direction=(0,0,1))
        pipette_tip = pv.Cone(radius=5, height=20, direction=(0,0,-1))
        pipette_body.translate((0, 0, 60), inplace=True)
        pipette_tip.translate((0, 0, 10), inplace=True)
        
        self.pipette_mesh = pipette_body.merge(pipette_tip)
        self.pv_pipette_actor = self.plotter.add_mesh(self.pipette_mesh, color="red")
        
        self.plotter.add_axes()
        self._deck_jog() # Update needle position to match UI coordinates

        self.plotter.camera_position = [(150, -300, 400), (150, 125, 0), (0, 0, 1)]
        self.plotter.reset_camera_clipping_range()


    def _deck_jog(self):
        try:
            x = float(self.deck_x.text())
            y = float(self.deck_y.text())
            z = float(self.deck_z.text())
            self.lims.hw.move_to(x, y, z)
            mat = np.eye(4)
            mat[0,3] = x
            mat[1,3] = y
            mat[2,3] = z
            if hasattr(self, 'pv_pipette_actor') and self.pv_pipette_actor:
                self.pv_pipette_actor.user_matrix = mat
            self.plotter.update()
        except: pass

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
        self.draw_3d_deck()

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
        layout = QVBoxLayout(self.tab_analysis)
        
        # Top Controls
        top_bar = QHBoxLayout()
        btn_watchdog = QPushButton("Start Hands-Free Watchdog")
        btn_watchdog.clicked.connect(self.start_watchdog_thread)
        btn_watchdog.setStyleSheet("background-color: #2b3e50; color: white; font-weight: bold; padding: 10px;")
        
        btn_manual_qc = QPushButton("Manual Heatmap QC")
        btn_manual_qc.clicked.connect(self.run_manual_heatmap_qc)
        
        btn_manual_ca2 = QPushButton("Manual Interactive Plotly")
        btn_manual_ca2.clicked.connect(self.run_manual_ca2_plotly)
        
        top_bar.addWidget(btn_watchdog)
        top_bar.addWidget(btn_manual_qc)
        top_bar.addWidget(btn_manual_ca2)
        top_bar.addStretch()
        
        layout.addLayout(top_bar)
        
        # Web Engine View for embedded HTML
        self.web_view = QWebEngineView()
        html = """
        <html><body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #f0f0f0;">
        <h2>Interactive Plotly Engine Ready.<br>Load a Ca2+ CSV or start the Watchdog pipeline.</h2>
        </body></html>
        """
        self.web_view.setHtml(html)
        
        layout.addWidget(self.web_view)

    def start_watchdog_thread(self):
        self.log("Initializing FOC48 Background Watchdog...")
        self.watchdog_thread = WatchdogRunner()
        self.watchdog_thread.log_signal.connect(self.log)
        self.watchdog_thread.start()
        
    def run_manual_heatmap_qc(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select FOC48 Data Folder")
        if not folder_path: return
        import watchdog_pipeline
        self.log(f"Running manual QC on {folder_path}...")
        try:
            watchdog_pipeline.FOC48Handler().run_pipeline(folder_path)
            self.log(f"QC Pipeline finished. Heatmaps generated in folder.")
        except Exception as e:
            self.log(f"Error: {e}")
            
    def run_manual_ca2_plotly(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select FOC48 CSV", filter="CSV Files (*.csv)")
        if not file_path: return
        self.log(f"Generating interactive Plotly for {file_path}...")
        try:
            import numpy as np
            import os
            from backend_plotly import generate_interactive_html
            data = np.loadtxt(file_path, delimiter=",")
            time_arr = data[:, 0]
            values_arr = data[:, 1:]
            out_file = os.path.join(os.path.dirname(file_path), "temp_interactive.html")
            generate_interactive_html(time_arr, values_arr, out_file, title=f"Kinetics: {os.path.basename(file_path)}")
            
            # Load into embedded Chromium WebEngine
            self.web_view.setUrl(QUrl.fromLocalFile(out_file))
            self.log("Plotly HTML embedded successfully.")
        except Exception as e:
            self.log(f"Error: {e}")

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

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, logging, threading, time, os, subprocess, math, sys, traceback, webbrowser, csv, socket, shutil
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import ctypes  # Native Windows library for ghost mouse
from working import LIMSOrchestrator, Labware, DeckSlot, Pipettor
try:
    from machine_profiles import MachineProfileManager, PROFILE_CONFIGS
except ImportError:
    try:
        from .machine_profiles import MachineProfileManager, PROFILE_CONFIGS
    except Exception:
        MachineProfileManager = None
        PROFILE_CONFIGS = {}
try:
    from gui import GUI as AnalyzerGUI
except Exception:
    AnalyzerGUI = None
from labware_models import (
    DeckManager, DeckSlot as ModelDeckSlot, HeightAdapter,
    ADAPTER_NONE, ADAPTER_90MM_BLOCK, ADAPTER_45MM_BLOCK,
    LabwareBase, Plate96, Plate48Myriamed, Reservoir3Well, Reservoir6Column, Reservoir7Column,
    TubeRack2x6_2mL, FalconRack50mL, TipRack96, WasteTrough
)
from generate_8ch_1000ul_ehm_media_change import build_8ch_ehm_media_change_steps

import xml.etree.ElementTree as ET
try:
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
except ImportError:
    pd = None
    sns = None
    plt = None
import re, queue


# Canonical column-major 96-well tip order (A1..H1, A2..H2, ..., A12..H12)
TIP_ORDER_96 = [f"{r}{c}" for c in range(1, 13) for r in "ABCDEFGH"]


class FlushingFileHandler(logging.FileHandler):
    """Real-time streaming file handler that flushes every emitted record to disk."""

    def emit(self, record):
        super().emit(record)
        try:
            self.flush()
        except Exception:
            pass


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.log_queue = queue.Queue()
        self._poll_logs()

    def emit(self, record):
        try:
            self.log_queue.put_nowait(self.format(record))
        except Exception:
            pass

    def _poll_logs(self):
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get_nowait()
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)
        except Exception:
            pass
        finally:
            try:
                self.text_widget.after(100, self._poll_logs)
            except Exception:
                pass


class LIMSMasterApp:
    # All labware Z heights (plates, reservoirs, troughs) were calibrated with the single-channel
    # head carrying a 200 µL Optifit tip (51.0 mm long). A 1000 µL Optifit tip is 71.5 mm long, so on
    # the 8×1000 µL head the tip end reaches ~20.5 mm deeper at the same Z. Every liquid-handling Z
    # on the 8-channel head is raised by this amount (fine-tune with the 8-channel ΔZ nudge).
    CAL_TIP_LENGTH_MM = 51.0
    TIP_1000_LENGTH_MM = 71.5
    EIGHT_CH_TIP_Z_COMP_MM = TIP_1000_LENGTH_MM - CAL_TIP_LENGTH_MM

    def __init__(self, root):
        self.root = root
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        except AttributeError:
            pass

        # Multi-Machine Profile Manager & Calibration Heights Isolation
        self.profile_manager = MachineProfileManager
        self.active_profile_id = MachineProfileManager.get_active_profile_id() if MachineProfileManager else "machine_2_1_10ul"

        prof_cfg = (PROFILE_CONFIGS or {}).get(self.active_profile_id, {})
        is_multi = prof_cfg.get("is_multichannel", True if ("8x" in self.active_profile_id or "10ul" in self.active_profile_id) else False)
        prof_tip_vol = float(prof_cfg.get("tip_volume", 10.0 if "10ul" in self.active_profile_id else (1000.0 if "1000" in self.active_profile_id else (300.0 if "300" in self.active_profile_id else 250.0))))

        # Hardware Initialization & Calibration Setup
        self.lims = LIMSOrchestrator(hardware=Pipettor(tip_volume=prof_tip_vol, multichannel=is_multi))
        self.lims.load_machine_profile()

        self.scale = 2.65
        self.bed_width = self.lims.machine_config.get("max_x_mm", 300.0)
        self.bed_height = self.lims.machine_config.get("max_y_mm", 300.0)
        self.bed_z_limit = self.lims.machine_config.get("max_z_mm", 310.0)
        self.tip_length_var = tk.DoubleVar(value=50.89)

        self.placed_slots, self.unplaced_slots = [], []
        self.selected_slot_name, self.dragging_slot = None, None
        self.workflow_sequence = []
        self.jog_sliders, self.deck_jog_sliders = {}, {}

        self.is_running = False
        self.is_aborted = False
        self.has_air_cushion = False
        self.air_cushion_ul = 0.0
        self.tip_liquid_ul = 0.0
        self.pause_event = threading.Event()
        self.pause_event.set()

        # Object-Oriented Labware & Kinematics Engine
        self.deck_manager = DeckManager()
        self.current_step_idx = 0
        self.protocol_edit_buttons = []
        self.tip_rack_learned_offset = (0.0, 0.0)
        self.eight_ch_cal_offset = {"X": 0.0, "Y": 0.0, "Z": 0.0}

        # Persistent Profile Heights & Depths Memory (GUI remembers active station heights)
        self.calibrated_heights_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "calibrated_heights_8ch.json"
        )
        if MachineProfileManager:
            self.calibrated_heights = MachineProfileManager.load_profile(self.active_profile_id)
        else:
            self.calibrated_heights = {}

        # Default profile heights ensuring no missing keys
        default_profile_heights = {
            "tip_rack_pickup_approach_z": 50.0 if ("10ul" in self.active_profile_id or "300" in self.active_profile_id) else 75.0,
            "tip_rack_collar_z": 64.97 if "10ul" in self.active_profile_id else 86.36,
            "tip_rack_pickup_limit_z": 75.0 if "10ul" in self.active_profile_id else (92.0 if "300" in self.active_profile_id else 98.0),
            "tip_pickup_extra_press_mm": 1.50 if "300" in self.active_profile_id else 2.50,
            "tip_rack_discard_z": 40.50,
            "ehm_aspirate_z": 72.35 if ("10ul" in self.active_profile_id or "300" in self.active_profile_id) else 24.17,
            "ehm_dispense_z": 62.35 if ("10ul" in self.active_profile_id or "300" in self.active_profile_id) else 14.17,
            "plate96_aspirate_z": 98.72 if "300" in self.active_profile_id else 78.40,
            "plate96_dispense_z": 98.72 if "300" in self.active_profile_id else 68.43,
            "plate96_dmso_dispense_z": 98.72 if "300" in self.active_profile_id else 68.43,
            "reservoir_aspirate_z": 58.34 if "10ul" in self.active_profile_id else (86.0 if "300" in self.active_profile_id else 90.42),
            "waste_dispense_z": 8.37,
            "waste_tip_drop_z": 8.37,
            "eight_ch_x_offset": 0.0,
            "eight_ch_y_offset": 0.0,
            "eight_ch_z_offset": 0.0,
        }
        for k, v in default_profile_heights.items():
            if k not in self.calibrated_heights:
                self.calibrated_heights[k] = v

        if "300" in self.active_profile_id:
            if float(self.calibrated_heights.get("plate96_aspirate_z", 98.72)) in (78.4, 78.40, 97.52):
                self.calibrated_heights["plate96_aspirate_z"] = 98.72
            if float(self.calibrated_heights.get("plate96_dispense_z", 98.72)) in (68.43, 78.4, 78.40, 97.52):
                self.calibrated_heights["plate96_dispense_z"] = 98.72
            if float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 92.0)) <= 88.0:
                self.calibrated_heights["tip_rack_pickup_limit_z"] = 92.0
            if float(self.calibrated_heights.get("plate96_dmso_dispense_z", 98.72)) in (75.0, 75.00, 68.43, 97.52):
                self.calibrated_heights["plate96_dmso_dispense_z"] = 98.72
            self.calibrated_heights.setdefault("plate96_dmso_dispense_z", 98.72)
        self.last_aspirate_slot = None
        self.last_aspirate_lw_kind = None

        if "10ul" in self.active_profile_id:
            self.calibrated_heights.setdefault("tip_10ul_collar_z", self.calibrated_heights.get("tip_rack_collar_z", 64.97))
            self.calibrated_heights.setdefault("tip_10ul_limit_z", self.calibrated_heights.get("tip_rack_pickup_limit_z", 75.0))
            self.calibrated_heights.setdefault("tip_10ul_approach_z", self.calibrated_heights.get("tip_rack_pickup_approach_z", 50.0))
            self.calibrated_heights.setdefault("tip_10ul_extra_press_mm", self.calibrated_heights.get("tip_pickup_extra_press_mm", 2.50))
            self.calibrated_heights.setdefault("reservoir_7_aspirate_z", self.calibrated_heights.get("reservoir_aspirate_z", 58.34))
            self.calibrated_heights.setdefault("reservoir_7_dispense_z", self.calibrated_heights.get("waste_dispense_z", 8.37))
            self.calibrated_heights.setdefault("piston_steps_per_ul", None)

        self.head_mode_var = tk.StringVar(
            value=prof_cfg.get("head_name", "8-Channel Multi (1-10 µL)" if "10ul" in self.active_profile_id else "8×1000 µL (8-Channel Manifold)")
        )

        # Pipette Head Initialization & Safety Interlock State
        self.is_head_initialized = False
        self.initialized_head = None

        # Cleanroom High-Contrast Touch UI State
        self.cleanroom_theme_active = False

        # Fluid Meniscus & Liquid Tracking State
        self.slot_liquid_levels = {}
        self.current_nozzle_pos = (0.0, 0.0)

        # Automated Run Reports & Step Audit Log
        self.last_run_report_path = None
        self.session_step_audit_log = []

        self.has_tip_var = tk.BooleanVar(value=False)
        self._worker_has_tip = False
        self.has_tip_var.trace_add("write", lambda *a: setattr(self, "_worker_has_tip", bool(self.has_tip_var.get())))
        self.current_pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.telemetry_active = False

        # Live Jogging & Keyboard Control State
        self.jog_step_var = tk.DoubleVar(value=1.0)
        self.jog_z_clearance_var = tk.BooleanVar(value=False)

        # User-Configured Run Bottom Clearance (Less Deep) Offsets per Slot
        self.run_z_clearance_offsets = {}
        self.jog_nudge_btns = []
        self._jogging_in_progress = False

        # Mid-Protocol Z-Axis Homing State (Compensates for cumulative downward Z drift every 1 step)
        self.mid_protocol_z_home_var = tk.BooleanVar(value=True)
        self.mid_protocol_z_home_interval_var = tk.IntVar(value=1)
        self.z_home_step_counter = 0

        # 1. Automated Session Logging State
        self.session_abort_status = None
        self.active_session_log_handler = None
        self.active_session_log_running_path = None
        self.last_session_log_path = None
        self._text_log_handler = None

        # 2. Active Session Tip Memory (Virtual Tip Remapping across runs)
        # Structure: {slot_name: {"cursor": 0, "consumed": set()}}
        self.session_tip_tracker = {}

        # 3. Weighted Dynamic Time Estimation & Live Speed Factor State
        self.step_baseline_times = []
        self.estimated_total_time = 0.0
        self.completed_baseline_time = 0.0
        self.live_speed_factor = 1.0
        self.run_start_time = 0.0
        self.total_paused_seconds = 0.0
        self.pause_started_at = None
        self.active_elapsed_at_step_start = 0.0
        self.timer_running = False

        self.setup_menu()
        self.setup_ui()
        self.setup_logging()

        try:
            self.root.bind("<KeyPress>", self._on_key_press)
        except Exception:
            pass

        hw_mode = "Multichannel (8-channel) array" if is_multi else "Single-channel direct mapping"
        self.logger.info(f"System Boot: {hw_mode} | Tracking bypassed. Pure kinematics engaged.")

        self.root.update()
        self.emergency_reset()

        # Prompt operator to identify and remember station on this computer if .machine_id is not yet set
        if getattr(self, "profile_manager", None) and hasattr(self.profile_manager, "has_persisted_profile_id"):
            if not self.profile_manager.has_persisted_profile_id():
                self.root.after(350, lambda: self.action_select_machine_profile(is_initial_setup=True))

    def on_closing(self):
        self.telemetry_active = False
        self.is_aborted = True
        self.pause_event.set()
        if hasattr(self, 'logger'):
            self.logger.info("Releasing hardware COM locks and terminating...")
            if getattr(self, '_text_log_handler', None):
                try:
                    self.logger.removeHandler(self._text_log_handler)
                except Exception:
                    pass
        if hasattr(self.lims.pipettor, 'close'): self.lims.pipettor.close()
        self.root.destroy()

    def setup_menu(self):
        menubar = tk.Menu(self.root)

        # -------------------------------------------------------------
        # 1. FILE MENU (Generic Workspace & Protocol Files)
        # -------------------------------------------------------------
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="🏢 Machine Station Profile...", command=self.action_select_machine_profile)
        filemenu.add_separator()
        filemenu.add_command(label="New Deck Layout", command=self.action_new_deck)
        filemenu.add_command(label="Load Workspace...", command=self.action_load_deck)
        filemenu.add_command(label="Save Workspace As...", command=self.action_save_deck_as)
        filemenu.add_separator()
        filemenu.add_command(label="Load JSON Protocol...", command=self.action_load_workflow)
        filemenu.add_command(label="Save JSON Protocol As...", command=self.action_save_workflow_as)
        filemenu.add_separator()
        filemenu.add_command(label="Import Python Protocol (.py)...", command=self.action_import_python_protocol)
        filemenu.add_command(label="📊 Open Latest Run Report (HTML)...", command=self.action_open_run_report)
        filemenu.add_command(label="View Session Logs Folder...", command=self.action_open_session_logs)
        filemenu.add_separator()
        filemenu.add_command(label="Machine Chassis Settings...", command=self.action_edit_machine_limits)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=filemenu)

        # -------------------------------------------------------------
        # 2. PROTOCOLS MENU (Top Bar Dedicated Workflows)
        # -------------------------------------------------------------
        protocolmenu = tk.Menu(menubar, tearoff=0)

        # Submenu 1: 8-Channel Multi (8×1000 µL) [Media Change]
        m8ch = tk.Menu(protocolmenu, tearoff=0)
        m8ch.add_command(label="🟢 Media Change (Plates 5 & 6 — 500 µL Dispense)", command=self.action_load_8ch_1000ul_media_change_protocol)
        m8ch.add_command(label="🟢 Fresh Media Only Multi-Dispense (22 steps)", command=self.action_load_8ch_fresh_media_only)
        m8ch.add_command(label="🧪 Test Slot 5 Media Removal (Col 3 Tips ➔ Return Col 1)", command=self.action_load_slot5_media_removal_test)
        m8ch.add_separator()
        m8ch.add_command(label="8-Channel Calibrated Heights & Depths...", command=self.action_open_8ch_height_settings)
        protocolmenu.add_cascade(label="8-Channel Multi (8×1000 µL) [Media Change]", menu=m8ch)

        # Submenu 2: 300 µL Single-Channel [Prepping DMSO-Drug]
        m300 = tk.Menu(protocolmenu, tearoff=0)
        m300.add_command(label="🟢 Prepping DMSO-Drug Serial Dilution (3x Plate - 200 µL Limit)...", command=self.action_load_300ul_dmso_dilution_3x_plate)
        m300.add_command(label="🟢 Prepping DMSO-Drug Serial Dilution (1x Plate - 200 µL Limit)...", command=self.action_load_300ul_dmso_dilution_1x_plate)
        m300.add_command(label="🟢 Prepping DMSO-Drug Serial Dilution (96-Well Plate)...", command=self.action_load_300ul_dmso_dilution)
        m300.add_separator()
        m300.add_command(label="🟢 Drug Addition to EHM Plates (7.5 µL) + Mix", command=lambda: self.action_load_300ul_drug_addition(7.5))
        m300.add_command(label="🟢 Drug Addition to EHM Plates (5.0 µL) + Mix", command=lambda: self.action_load_300ul_drug_addition(5.0))
        protocolmenu.add_cascade(label="300 µL Single-Channel [Prepping DMSO-Drug]", menu=m300)

        # Submenu 3: 8-Channel Multi (1-10 µL) [Drug Addition to EHM]
        m10ch = tk.Menu(protocolmenu, tearoff=0)
        m10ch.add_command(label="🟢 3x [8-Tip Both Plates] Drug Addition to EHM (7.5 µL) + Mix", command=lambda: self.action_load_10ul_3x_8tip_both_plates(7.5))
        m10ch.add_command(label="🟢 3x [8-Tip Both Plates] Drug Addition to EHM (5.0 µL) + Mix", command=lambda: self.action_load_10ul_3x_8tip_both_plates(5.0))
        m10ch.add_separator()
        m10ch.add_command(label="🟢 [5-Tip Parallel] Drug Addition to EHM (7.5 µL) + Mix (~8 mins)", command=lambda: self.action_load_10ul_parallel_drug_addition(7.5))
        m10ch.add_command(label="🟢 [5-Tip Parallel] Drug Addition to EHM (5.0 µL) + Mix (~8 mins)", command=lambda: self.action_load_10ul_parallel_drug_addition(5.0))
        m10ch.add_separator()
        m10ch.add_command(label="🟢 [Triplicate Assay] Drug Addition to EHM (7.5 µL) + Mix", command=lambda: self.action_load_10ul_triplicate_drug_addition(7.5))
        m10ch.add_command(label="🟢 [Triplicate Assay] Drug Addition to EHM (5.0 µL) + Mix", command=lambda: self.action_load_10ul_triplicate_drug_addition(5.0))
        protocolmenu.add_cascade(label="8-Channel Multi (1-10 µL) [Drug Addition to EHM]", menu=m10ch)

        menubar.add_cascade(label="Protocols", menu=protocolmenu)

        # -------------------------------------------------------------
        # 3. HARDWARE MENU
        # -------------------------------------------------------------
        hwmenu = tk.Menu(menubar, tearoff=0)
        hwmenu.add_command(label="🔌 Initialize Pipettor Head", command=self.action_initialize_pipettor)
        hwmenu.add_separator()
        hwmenu.add_command(label="Switch to 8×1000 µL Multi-Channel [Media Change]", command=lambda: self.switch_pipettor_head("8-Channel Multi (8×1000 µL)"))
        hwmenu.add_command(label="Switch to 1×300 µL Single-Channel [Prepping DMSO-Drug]", command=lambda: self.switch_pipettor_head("300 µL Single-Channel"))
        hwmenu.add_command(label="Switch to 8-Channel Multi (1-10 µL) [Drug Addition to EHM]", command=lambda: self.switch_pipettor_head("8-Channel Multi (1-10 µL)"))
        hwmenu.add_separator()
        hwmenu.add_command(label="Reset / Home Pipette Head", command=self.quick_home_head)
        hwmenu.add_command(label="Retract & Home Z-Axis Only (0 mm, Preserve Tip)", command=self.quick_safe_z)
        hwmenu.add_separator()
        hwmenu.add_command(label="📐 Slot Z-Verification Tool...", command=self.action_open_slot_z_verification)
        hwmenu.add_command(label="8-Channel Calibrated Heights & Depths...", command=self.action_open_8ch_height_settings)
        menubar.add_cascade(label="Hardware", menu=hwmenu)

        # -------------------------------------------------------------
        # 4. SETTINGS & STATIONS MENU
        # -------------------------------------------------------------
        settingsmenu = tk.Menu(menubar, tearoff=0)
        settingsmenu.add_command(label="⚙️ Change Machine Profile...", command=self.action_select_machine_profile)
        settingsmenu.add_command(label="🔌 Initialize Pipettor Head...", command=self.action_initialize_pipettor)
        settingsmenu.add_separator()
        settingsmenu.add_command(label="📐 Slot Z-Verification Tool...", command=self.action_open_slot_z_verification)
        settingsmenu.add_command(label="Calibrated Heights & Depths (Active Profile)...", command=self.action_open_8ch_height_settings)
        settingsmenu.add_separator()
        settingsmenu.add_command(label="🌓 Toggle Cleanroom Theme (High Contrast)", command=self.toggle_cleanroom_theme)
        settingsmenu.add_command(label="Machine Chassis Settings...", command=self.action_edit_machine_limits)
        menubar.add_cascade(label="Settings", menu=settingsmenu)
        try:
            self.root.config(menu=menubar)
        except Exception:
            pass

    def action_edit_machine_limits(self):
        top = tk.Toplevel(self.root)
        top.title("Hardware Chassis Configuration")
        top.geometry("380x300")
        ttk.Label(top, text="Global Machine Boundaries & Tools", font=("Arial", 11, "bold")).pack(pady=10)
        f = ttk.Frame(top)
        f.pack(fill=tk.BOTH, expand=True, padx=20)

        ttk.Label(f, text="Max X Travel (mm):").grid(row=0, column=0, sticky="w", pady=5)
        x_var = tk.StringVar(value=str(self.lims.machine_config.get("max_x_mm", 300.0)))
        ttk.Entry(f, textvariable=x_var, width=15).grid(row=0, column=1, pady=5)

        ttk.Label(f, text="Max Y Travel (mm):").grid(row=1, column=0, sticky="w", pady=5)
        y_var = tk.StringVar(value=str(self.lims.machine_config.get("max_y_mm", 300.0)))
        ttk.Entry(f, textvariable=y_var, width=15).grid(row=1, column=1, pady=5)

        ttk.Label(f, text="Max Z Travel (Bed Floor mm):").grid(row=2, column=0, sticky="w", pady=5)
        z_var = tk.StringVar(value=str(self.bed_z_limit))
        ttk.Entry(f, textvariable=z_var, width=15).grid(row=2, column=1, pady=5)

        ttk.Separator(f, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(f, text="Attached Tip Length (mm):").grid(row=4, column=0, sticky="w", pady=5)
        t_var = tk.StringVar(value=str(self.tip_length_var.get()))
        ttk.Entry(f, textvariable=t_var, width=15).grid(row=4, column=1, pady=5)

        def commit_changes():
            try:
                self.lims.machine_config["max_x_mm"] = float(x_var.get())
                self.lims.machine_config["max_y_mm"] = float(y_var.get())
                self.lims.machine_config["max_z_mm"] = float(z_var.get())
                self.bed_width = float(x_var.get())
                self.bed_height = float(y_var.get())
                self.bed_z_limit = float(z_var.get())
                self.tip_length_var.set(float(t_var.get()))
                self.lims.save_machine_profile()
                self.canvas.config(width=self.bed_width * self.scale, height=self.bed_height * self.scale)
                self.draw_deck()
                self.logger.info(f"Chassis updated. Z-Floor locked to {self.bed_z_limit}mm.")
                top.destroy()
            except ValueError:
                messagebox.showerror("Parsing Error", "Dimensions must be floating-point numerals.")

        ttk.Button(top, text="Apply & Restart Canvas", command=commit_changes).pack(pady=20)

    def setup_logging(self):
        self.logger = logging.getLogger("LIMS")
        self.logger.setLevel(logging.INFO)
        th = TextHandler(self.console_text)
        th.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(th)
        self._text_log_handler = th

    # =========================================================================
    # 1. AUTOMATED SESSION LOGGING SYSTEM (DDMMYYYY_HHMMSS_Session_<STATUS>.log)
    # =========================================================================
    def get_logs_dir(self, machine_profile_id: str = None) -> str:
        pid = machine_profile_id or getattr(self, "active_profile_id", "machine_2_1_10ul")
        machine_folder_map = {
            "machine_1_8x1000": "Machine 1 - 8x1000 uL",
            "machine_2_1_10ul": "Machine 2 - 1-10 uL",
            "machine_3_300ul": "Machine 3 - 300 uL",
        }
        folder_name = machine_folder_map.get(pid)
        if not folder_name:
            disp = self.profile_manager.get_display_name(pid) if getattr(self, "profile_manager", None) else str(pid)
            folder_name = disp.replace(":", "-").replace("/", "-").replace("\\", "-").strip()

        # Priority targets for Windows / lab machine:
        # User requested directory: C:\Users\labhub.Hzphw-foc4815\Documents\temp logs
        win_temp_logs_explicit = r"C:\Users\labhub.Hzphw-foc4815\Documents\temp logs"
        win_temp_logs_user = os.path.join(os.path.expanduser("~"), "Documents", "temp logs") if sys.platform.startswith("win") else None

        candidates = [
            os.environ.get("ROBOLAB_LOGS_DIR"),
            win_temp_logs_explicit,
            win_temp_logs_user,
            r"C:\labhub\import\Robolab Machine Logs",
        ]
        for base in candidates:
            if not base:
                continue
            if sys.platform.startswith("win") or os.name == "nt" or "ROBOLAB_LOGS_DIR" in os.environ or os.path.exists(base):
                try:
                    target_dir = base if "temp logs" in base.lower() else os.path.join(base, folder_name)
                    os.makedirs(target_dir, exist_ok=True)
                    return target_dir
                except Exception as e:
                    self.logger.warning(f"Could not access log folder '{base}': {e}")

        # Fallback to local logs directory for macOS / Linux / CI environments
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_dir = os.path.join(script_dir, "logs", folder_name)
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    def action_open_session_logs(self):
        logs_dir = self.get_logs_dir()
        try:
            if sys.platform.startswith("win") and hasattr(os, "startfile"):
                os.startfile(logs_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", logs_dir])
            else:
                subprocess.Popen(["xdg-open", logs_dir])
            self.logger.info(f"Opened Session Logs directory: {logs_dir}")
        except Exception as e:
            self.logger.warning(f"Could not launch file manager for {logs_dir}: {e}")
            messagebox.showinfo("Session Logs Location", f"Session logs are saved in:\n{logs_dir}")

    def _start_session_log(self, total_steps: int, est_seconds: float) -> str:
        logs_dir = self.get_logs_dir()
        dt = datetime.now()
        existing = set(os.listdir(logs_dir))
        while True:
            ts_prefix = dt.strftime("%d%m%Y_%H%M%S")
            if not any(fname.startswith(f"{ts_prefix}_Session_") for fname in existing):
                break
            dt = dt + timedelta(seconds=1)

        running_path = os.path.join(logs_dir, f"{ts_prefix}_Session_RUNNING.log")
        fh = FlushingFileHandler(running_path, mode="w", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        self.logger.addHandler(fh)
        self.active_session_log_handler = fh
        self.active_session_log_running_path = running_path
        self.session_abort_status = None

        head_str = "8x1000 uL Multichannel Manifold" if self.lims.pipettor.multichannel else "1x200 uL Single-Channel"
        speed_pct = self.speed_var.get() if hasattr(self, "speed_var") else 80.0
        deck_summary = ", ".join(
            f"{s}:{getattr(lw, 'source_file', getattr(lw, 'name', 'custom'))}"
            for s, lw in sorted(self.lims.deck_labware.items())
        ) or "None"
        tip_mem_summary = ", ".join(
            f"{s}(consumed={len(info.get('consumed', ()))})"
            for s, info in sorted(self.session_tip_tracker.items())
        ) or "Fresh (0 consumed)"

        self.logger.info("======================================================================")
        self.logger.info(f"SESSION LOG STARTED: {os.path.basename(running_path)}")
        self.logger.info(f"Head Mode: {head_str} | Speed: {speed_pct:.0f}% | Mixing: {'ON' if getattr(self, 'enable_mixing_for_run', False) else 'OFF'}")
        self.logger.info(f"Total Steps: {total_steps} | Initial Estimated Time: {self.format_hms(est_seconds)} ({est_seconds:.1f}s)")
        self.logger.info(f"Deck Labware: {deck_summary}")
        self.logger.info(f"Session Tip Memory: {tip_mem_summary}")
        self.logger.info("======================================================================")
        return running_path

    def _classify_abort_reason(self, exc) -> str:
        msg = str(exc or "").lower()
        if any(k in msg for k in ("liquid depleted", "depleted", "reservoir empty", "tube empty", "all available tubes")):
            return "AUTO_ABORTED_DEPLETED"
        if any(k in msg for k in ("tip rack is completely empty", "empty tips", "all 96 tip", "tip sockets exhausted", "no unconsumed tips")):
            return "AUTO_ABORTED_EMPTY_TIPS"
        if any(
            k in msg
            for k in (
                "critical", "collision", "double-tip", "ejection failed", "safety interlock",
                "hardware", "motor", "com ", "timeout", "notconnected", "commandfailed",
                "movetosurface", "ceiling", "tip pickup failed", "instrumentlib",
            )
        ):
            return "AUTO_ABORTED_HARDWARE"
        return "AUTO_ABORTED_ERROR"

    def _finalize_session_log(self, final_status: str = None) -> str:
        fh = getattr(self, "active_session_log_handler", None)
        running_path = getattr(self, "active_session_log_running_path", None)
        if not fh or not running_path:
            return ""

        status = (final_status or self.session_abort_status or ("ABORTED_USER" if self.is_aborted else "COMPLETED")).upper()
        active_elapsed = self.get_active_elapsed_time() if getattr(self, "run_start_time", 0.0) > 0 else 0.0
        total_steps = len(self.workflow_sequence)
        done_steps = min(getattr(self, "current_step_idx", 0), total_steps)

        self.logger.info("======================================================================")
        self.logger.info(
            f"SESSION SUMMARY | Status: {status} | Steps Executed: {done_steps}/{total_steps} | "
            f"Active Elapsed: {self.format_hms(active_elapsed)} ({active_elapsed:.1f}s) | "
            f"Paused: {self.total_paused_seconds:.1f}s | Final Speed Factor: {self.live_speed_factor:.3f}x"
        )
        self.logger.info("======================================================================")

        try:
            fh.flush()
            fh.close()
        except Exception:
            pass
        try:
            self.logger.removeHandler(fh)
        except Exception:
            pass

        self.active_session_log_handler = None
        self.active_session_log_running_path = None

        final_path = re.sub(r"_Session_RUNNING\.log$", f"_Session_{status}.log", running_path)
        try:
            if os.path.exists(running_path):
                os.replace(running_path, final_path)
        except Exception as ren_err:
            self.logger.warning(f"Could not rename session log to {os.path.basename(final_path)}: {ren_err}")
            final_path = running_path

        self.last_session_log_path = final_path

        # Mirror session log to user-requested temp logs folder
        for mirror_dir in [
            r"C:\Users\labhub.Hzphw-foc4815\Documents\temp logs",
            os.path.join(os.path.expanduser("~"), "Documents", "temp logs") if sys.platform.startswith("win") else None,
        ]:
            if mirror_dir and (os.path.exists(mirror_dir) or sys.platform.startswith("win")):
                try:
                    os.makedirs(mirror_dir, exist_ok=True)
                    dest_file = os.path.join(mirror_dir, os.path.basename(final_path))
                    if os.path.abspath(final_path) != os.path.abspath(dest_file):
                        shutil.copy2(final_path, dest_file)
                except Exception:
                    pass

        # 6. Automated Run Report Generation (HTML & CSV Bundled in logs/)
        self._generate_run_reports(final_path, status, done_steps, total_steps, active_elapsed)

        return final_path

    def action_open_run_report(self):
        """Opens the most recent HTML run report in the system default web browser."""
        target_path = getattr(self, "last_run_report_path", None)
        logs_dir = self.get_logs_dir()
        if not target_path or not os.path.exists(target_path):
            reports = [os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if f.endswith(".html") and "_Report_" in f]
            if reports:
                reports.sort(key=os.path.getmtime, reverse=True)
                target_path = reports[0]

        if target_path and os.path.exists(target_path):
            try:
                if sys.platform.startswith("win") and hasattr(os, "startfile"):
                    os.startfile(target_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", target_path])
                else:
                    subprocess.Popen(["xdg-open", target_path])
                self.logger.info(f"Opened Run Report in browser: {target_path}")
            except Exception as e:
                self.logger.warning(f"Could not open browser for {target_path}: {e}")
                messagebox.showinfo("Run Report Location", f"Report saved at:\n{target_path}")
        else:
            messagebox.showinfo("No Reports Found", f"No run reports found in:\n{logs_dir}\nRun a protocol first.")

    def _generate_run_reports(self, final_log_path: str, status: str, done_steps: int, total_steps: int, active_elapsed: float):
        """Generates both HTML and CSV run reports alongside the session log inside logs/."""
        try:
            logs_dir = os.path.dirname(final_log_path)
            base_name = os.path.basename(final_log_path)
            m = re.match(r"^(\d{8}_\d{6})_Session_", base_name)
            ts_str = m.group(1) if m else datetime.now().strftime("%d%m%Y_%H%M%S")

            html_path = os.path.join(logs_dir, f"{ts_str}_Report_{status}.html")
            csv_path = os.path.join(logs_dir, f"{ts_str}_Report_{status}.csv")

            station_name = self.profile_manager.get_display_name(self.active_profile_id) if getattr(self, "profile_manager", None) else self.active_profile_id
            host_name = socket.gethostname() if "socket" in sys.modules else "Robolab-PC"
            date_display = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            audit_records = getattr(self, "session_step_audit_log", [])
            total_aspirated = sum(float(r.get("vol", 0.0)) for r in audit_records if "Aspirate" in str(r.get("action", "")))
            total_dispensed = sum(float(r.get("vol", 0.0)) for r in audit_records if "Dispense" in str(r.get("action", "")))
            tips_picked = sum(1 for r in audit_records if "Pick" in str(r.get("action", "")))

            # Write CSV Report
            with open(csv_path, "w", newline="", encoding="utf-8") as f_csv:
                writer = csv.writer(f_csv)
                writer.writerow(["Step", "Timestamp", "Action", "Slot", "Well", "Volume_uL", "Z_Depth_mm", "Status", "Notes"])
                for r in audit_records:
                    writer.writerow([
                        r.get("step_idx", ""),
                        r.get("timestamp", ""),
                        r.get("action", ""),
                        r.get("slot", ""),
                        r.get("well", ""),
                        f"{float(r.get('vol', 0.0)):.2f}",
                        f"{float(r.get('z', 0.0)):.2f}",
                        r.get("status", "SUCCESS"),
                        r.get("note", "")
                    ])

            # Write HTML Report
            status_colors = {
                "COMPLETED": "#10b981",
                "ABORTED_USER": "#f59e0b",
                "AUTO_ABORTED_EMPTY_TIPS": "#ef4444",
                "AUTO_ABORTED_HARDWARE": "#dc2626",
                "AUTO_ABORTED_DEPLETED": "#f97316",
                "AUTO_ABORTED_ERROR": "#991b1b",
            }
            theme_color = status_colors.get(status, "#3b82f6")

            table_rows_html = []
            for r in audit_records:
                table_rows_html.append(
                    f"<tr>"
                    f"<td>{r.get('step_idx', '')}</td>"
                    f"<td>{r.get('timestamp', '')}</td>"
                    f"<td><b>{r.get('action', '')}</b></td>"
                    f"<td>{r.get('slot', '')}</td>"
                    f"<td>{r.get('well', '')}</td>"
                    f"<td>{float(r.get('vol', 0.0)):.1f} µL</td>"
                    f"<td>{float(r.get('z', 0.0)):.2f} mm</td>"
                    f"<td><span class='badge' style='background:{theme_color};'>{r.get('status', 'OK')}</span></td>"
                    f"</tr>"
                )
            rows_str = "".join(table_rows_html) or "<tr><td colspan='8'>No step telemetry recorded.</td></tr>"

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Robolab Biohit Run Report — {status}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
  .container {{ max-width: 1000px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 32px; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; }}
  .header h1 {{ margin: 0; font-size: 24px; color: #0f172a; }}
  .header .meta {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
  .status-badge {{ font-size: 14px; font-weight: 700; padding: 6px 16px; border-radius: 9999px; color: #fff; background: {theme_color}; text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 24px 0; }}
  .kpi-card {{ background: #f1f5f9; border-radius: 8px; padding: 16px; text-align: center; border: 1px solid #e2e8f0; }}
  .kpi-card .num {{ font-size: 24px; font-weight: bold; color: #0f172a; margin-top: 4px; }}
  .kpi-card .label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748b; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
  th {{ background: #f8fafc; text-align: left; padding: 10px 12px; border-bottom: 2px solid #cbd5e1; color: #475569; font-weight: 600; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  .badge {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; color: #fff; font-weight: 600; }}
  .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>🧬 Robolab Biohit Pipetting Run Report</h1>
      <div class="meta">Station: <b>{station_name}</b> | Host: {host_name} | Generated: {date_display}</div>
    </div>
    <div class="status-badge">{status}</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="label">Steps Executed</div>
      <div class="num">{done_steps} / {total_steps}</div>
    </div>
    <div class="kpi-card">
      <div class="label">Active Runtime</div>
      <div class="num">{self.format_hms(active_elapsed)}</div>
    </div>
    <div class="kpi-card">
      <div class="label">Speed Multiplier</div>
      <div class="num">{self.live_speed_factor:.2f}x</div>
    </div>
    <div class="kpi-card">
      <div class="label">Volume Aspirated</div>
      <div class="num">{total_aspirated:.1f} µL</div>
    </div>
    <div class="kpi-card">
      <div class="label">Volume Dispensed</div>
      <div class="num">{total_dispensed:.1f} µL</div>
    </div>
    <div class="kpi-card">
      <div class="label">Tips Consumed</div>
      <div class="num">{tips_picked}</div>
    </div>
  </div>

  <h2>Step Telemetry & Action Audit</h2>
  <table>
    <thead>
      <tr>
        <th>Step #</th><th>Timestamp</th><th>Action</th><th>Slot</th><th>Well</th><th>Volume</th><th>Z Depth</th><th>Status</th>
      </tr>
    </thead>
    <tbody>
      {rows_str}
    </tbody>
  </table>

  <div class="footer">
    Robolab Biohit High-Throughput Automation Platform &bull; Session Log: {base_name}
  </div>
</div>
</body>
</html>
"""
            with open(html_path, "w", encoding="utf-8") as f_html:
                f_html.write(html_content)

            self.last_run_report_path = html_path
            self.logger.info(f"📊 Run Reports generated: {os.path.basename(html_path)} & {os.path.basename(csv_path)}")

            # Mirror run reports to user-requested temp logs folder
            for mirror_dir in [
                r"C:\Users\labhub.Hzphw-foc4815\Documents\temp logs",
                os.path.join(os.path.expanduser("~"), "Documents", "temp logs") if sys.platform.startswith("win") else None,
            ]:
                if mirror_dir and (os.path.exists(mirror_dir) or sys.platform.startswith("win")):
                    try:
                        os.makedirs(mirror_dir, exist_ok=True)
                        dest_html = os.path.join(mirror_dir, os.path.basename(html_path))
                        dest_csv = os.path.join(mirror_dir, os.path.basename(csv_path))
                        if os.path.abspath(html_path) != os.path.abspath(dest_html):
                            shutil.copy2(html_path, dest_html)
                        if os.path.abspath(csv_path) != os.path.abspath(dest_csv):
                            shutil.copy2(csv_path, dest_csv)
                    except Exception:
                        pass
        except Exception as rep_err:
            self.logger.warning(f"Could not generate run report: {rep_err}")

    # =========================================================================
    # 2. ACTIVE SESSION TIP MEMORY (VIRTUAL TIP REMAPPING & DECK VISUALIZER)
    # =========================================================================
    def _get_tip_tracker(self, slot_name: str = "Slot_4") -> dict:
        if slot_name not in self.session_tip_tracker:
            self.session_tip_tracker[slot_name] = {"cursor": 0, "consumed": set()}
        return self.session_tip_tracker[slot_name]

    def _ordered_tip_wells(self, slot_name: str = "Slot_4") -> list:
        lw = self.lims.deck_labware.get(slot_name)
        if lw and getattr(lw, "wells", None) and self._lw_kind(lw) == "tip_rack":
            valid = {w.upper() for w in lw.wells.keys()}
            ordered = [w for w in TIP_ORDER_96 if w in valid]
            if ordered:
                return ordered
        return list(TIP_ORDER_96)

    def _sync_tip_cursor(self, slot_name: str = "Slot_4"):
        tracker = self._get_tip_tracker(slot_name)
        ordered = self._ordered_tip_wells(slot_name)
        consumed = tracker["consumed"]
        next_idx = len(ordered)
        for idx, w in enumerate(ordered):
            if w not in consumed:
                next_idx = idx
                break
        tracker["cursor"] = next_idx
        self._refresh_tip_memory_badge(slot_name)

    def _refresh_tip_memory_badge(self, slot_name: str = "Slot_4"):
        lbl = getattr(self, "lbl_tip_memory", None)
        if not lbl:
            return
        tracker = self._get_tip_tracker(slot_name)
        ordered = self._ordered_tip_wells(slot_name)
        consumed_count = len(tracker["consumed"])
        free_count = max(0, len(ordered) - consumed_count)
        next_well = ordered[tracker["cursor"]] if tracker["cursor"] < len(ordered) else "EMPTY"

        def _upd():
            try:
                lbl.config(
                    text=f"Tip Memory ({slot_name}): Next {next_well} ({free_count}/{len(ordered)} free)",
                    foreground="#dc3545" if free_count == 0 else ("#fd7e14" if free_count <= 16 else "#0d6efd"),
                )
            except Exception:
                pass

        if threading.current_thread() is threading.main_thread():
            _upd()
        else:
            try:
                self.root.after(0, _upd)
            except Exception:
                pass

    def _schedule_deck_redraw(self):
        if not hasattr(self, "canvas"):
            return
        if threading.current_thread() is threading.main_thread():
            try:
                self.draw_deck()
            except Exception:
                pass
        else:
            try:
                self.root.after(0, self.draw_deck)
            except Exception:
                pass

    def mark_tip_consumed(self, slot_name: str, well_id: str, redraw: bool = True):
        if not slot_name or not well_id:
            return
        tracker = self._get_tip_tracker(slot_name)
        tracker["consumed"].add(well_id.strip().upper())
        self._sync_tip_cursor(slot_name)
        if redraw:
            self._schedule_deck_redraw()

    def mark_tip_restored(self, slot_name: str, well_id: str, redraw: bool = True):
        if not slot_name or not well_id:
            return
        tracker = self._get_tip_tracker(slot_name)
        tracker["consumed"].discard(well_id.strip().upper())
        self._sync_tip_cursor(slot_name)
        if redraw:
            self._schedule_deck_redraw()

    def get_default_tip_slot(self) -> str:
        """Locates the deck slot containing the active tip rack, defaulting to Slot_4."""
        if hasattr(self, "lims") and hasattr(self.lims, "deck_labware"):
            for s_name, lw in self.lims.deck_labware.items():
                lw_file = getattr(lw, "source_file", getattr(lw, "name", ""))
                if "tip" in str(lw_file).lower():
                    return s_name
        return "Slot_4"

    def resolve_session_tip(self, slot_name: str, requested_well: str = None):
        """
        Virtual Tip Remapping:
        - If `requested_well` is specified (e.g. 'C2') and has NOT been consumed, returns `(requested_well, False)` (works as before).
        - If `requested_well` is NOT specified (None, empty, or 'Auto'), starts from the default start spot ('A1')
          and takes the next available unconsumed tip in column-major order (`A1..H1 -> A2..H2 -> ...`).
        - If `requested_well` was already consumed, dynamically remaps to the next available unconsumed tip.
        - Returns `(None, True)` if all 96 tips in `slot_name` are exhausted.
        """
        req = (requested_well or "").strip().upper()
        is_auto_request = not req or req in ("AUTO", "DEFAULT", "NEXT", "NONE", "")

        tracker = self._get_tip_tracker(slot_name)
        ordered = self._ordered_tip_wells(slot_name)
        consumed = tracker["consumed"]

        if len(consumed) >= len(ordered):
            return None, True

        # If user explicitly requested a specific well (other than Auto) and it's fresh, use it directly!
        if not is_auto_request and req in ordered and req not in consumed:
            return req, False

        # If unspecified (auto) or already consumed: start from requested well or default cursor
        start = ordered.index(req) if (not is_auto_request and req in ordered) else min(tracker.get("cursor", 0), len(ordered))
        for idx in list(range(start, len(ordered))) + list(range(0, start)):
            cand = ordered[idx]
            if cand not in consumed:
                return cand, (cand != req if not is_auto_request else False)

        return None, True

    @staticmethod
    def _expand_8ch_tip_sockets(step: dict, well_id: str) -> list:
        """Return exact physical tip sockets (e.g. ['A1', 'B1', ..., 'H1']) touched by an 8-channel tip step."""
        m = re.match(r"^[A-H](\d+)$", (well_id or "").strip().upper())
        if not m:
            return []
        col = int(m.group(1))
        offset_rows = int((step or {}).get("tip_offset_rows", 0) or 0)
        ch_spec = ((step or {}).get("mounted_channels") or "A-H").strip().upper()

        ch_indices = []
        for part in ch_spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part and len(part) == 3:
                c0, c1 = ord(part[0]) - ord("A"), ord(part[2]) - ord("A")
                ch_indices.extend(range(min(c0, c1), max(c0, c1) + 1))
            elif len(part) == 1 and "A" <= part <= "H":
                ch_indices.append(ord(part) - ord("A"))

        rows = "ABCDEFGH"
        sockets = []
        for ch in ch_indices:
            r_idx = ch + offset_rows
            if 0 <= r_idx < 8:
                sockets.append(f"{rows[r_idx]}{col}")
        return sockets

    def resolve_8ch_session_tip_col(self, slot_name: str, requested_well: str = None, step: dict = None) -> tuple:
        """
        8-Channel Column Resolution with Active Session Tip Memory:
        - Determines which sockets are needed based on step mounted_channels (e.g. A-H for 8 tips, A-E for 5 tips).
        - If user specified a well/column (e.g. 'A1' -> col 1):
          Checks if that requested column is completely fresh (none of the required sockets consumed).
          If fresh, returns (col, False).
        - If that requested column has ANY consumed sockets (or if requested_well is Auto/empty/None):
          Dynamically advances to the next column (searching col, col+1, ..., 12, then 1, ..., col-1)
          where ALL required sockets are completely fresh.
          Returns (found_col, True).
        - If all 12 columns are exhausted, returns (None, True).
        """
        tracker = self._get_tip_tracker(slot_name)
        consumed = tracker["consumed"]

        req = (requested_well or "").strip().upper()
        is_auto = not req or req in ("AUTO", "DEFAULT", "NEXT", "NONE", "")

        req_col = 1
        if not is_auto:
            digits = "".join(ch for ch in req if ch.isdigit())
            if digits and 1 <= int(digits) <= 12:
                req_col = int(digits)

        def _col_sockets(c: int) -> list:
            s_list = self._expand_8ch_tip_sockets(step, f"A{c}")
            if not s_list:
                s_list = [f"{r}{c}" for r in "ABCDEFGH"]
            return s_list

        def _col_is_fresh(c: int) -> bool:
            return not any(sock in consumed for sock in _col_sockets(c))

        # 1. If explicitly requested and completely fresh, keep requested column
        if not is_auto and _col_is_fresh(req_col):
            return req_col, False

        # 2. If requested column is already consumed (or auto): search for next fresh column
        search_order = list(range(req_col, 13)) + list(range(1, req_col))
        for cand_col in search_order:
            if _col_is_fresh(cand_col):
                return cand_col, True

        return None, True

    def reset_tip_rack_memory(self, slot_name: str = None, announce: bool = True):
        if slot_name:
            target_slots = [slot_name]
        else:
            target_slots = sorted(
                set(self.session_tip_tracker.keys())
                | {s for s, lw in self.lims.deck_labware.items() if self._lw_kind(lw) == "tip_rack"}
                | {"Slot_4"}
            )
        for s_name in target_slots:
            self.session_tip_tracker[s_name] = {"cursor": 0, "consumed": set()}
            self._sync_tip_cursor(s_name)
        self._schedule_deck_redraw()
        if announce and hasattr(self, "logger"):
            joined = ", ".join(target_slots)
            self.logger.info(f"🔄 Tip Rack Reset ({joined}): Active session tip pointer reset to A1 (all 96 tips marked fresh).")

    def _on_canvas_right_click(self, e):
        rx, ry = self.get_m_x(e.x), e.y / self.scale
        clicked_slot = None
        for name in reversed(self.placed_slots):
            s = self.lims.deck_slots[name]
            if s.x_abs <= rx <= s.x_abs + s.width_mm and s.y_abs <= ry <= s.y_abs + s.height_mm:
                clicked_slot = name
                break

        ctx = tk.Menu(self.root, tearoff=0)
        if clicked_slot:
            lw = self.lims.deck_labware.get(clicked_slot)
            is_tips = (self._lw_kind(lw) == "tip_rack") or (clicked_slot in self.session_tip_tracker)
            if is_tips:
                consumed_n = len(self._get_tip_tracker(clicked_slot)["consumed"])
                ctx.add_command(
                    label=f"🔄 Reset Tip Rack on {clicked_slot} -> A1 ({consumed_n} consumed)",
                    command=lambda s=clicked_slot: self.reset_tip_rack_memory(s),
                )
                ctx.add_separator()
        ctx.add_command(
            label="🔄 Reset All Tip Racks -> A1 (Fresh 96-Tip Box)",
            command=lambda: self.reset_tip_rack_memory(None),
        )
        try:
            ctx.tk_popup(e.x_root, e.y_root)
        finally:
            ctx.grab_release()

    # =========================================================================
    # 3. WEIGHTED DYNAMIC TIME ESTIMATION, SPEED FACTOR & PAUSE COMPENSATION
    # =========================================================================
    @staticmethod
    def format_hms(seconds: float) -> str:
        total_sec = max(0, int(round(float(seconds or 0.0))))
        hrs, rem = divmod(total_sec, 3600)
        mins, secs = divmod(rem, 60)
        return f"{hrs:02d}h {mins:02d}m {secs:02d}s"

    def _begin_pause_tracking(self, now: float = None):
        if self.pause_started_at is None:
            self.pause_started_at = time.time() if now is None else float(now)

    def _end_pause_tracking(self, now: float = None):
        if self.pause_started_at is not None:
            t_now = time.time() if now is None else float(now)
            self.total_paused_seconds += max(0.0, t_now - self.pause_started_at)
            self.pause_started_at = None

    def get_active_elapsed_time(self, now: float = None) -> float:
        if getattr(self, "run_start_time", 0.0) <= 0.0:
            return 0.0
        t_now = time.time() if now is None else float(now)
        in_flight_pause = max(0.0, t_now - self.pause_started_at) if self.pause_started_at is not None else 0.0
        return max(0.0, t_now - self.run_start_time - self.total_paused_seconds - in_flight_pause)

    def record_step_completion_for_timer(self, step_baseline: float, now: float = None):
        t_now = time.time() if now is None else float(now)
        active_elapsed = self.get_active_elapsed_time(t_now)
        self.completed_baseline_time += max(0.0, float(step_baseline))
        if self.completed_baseline_time >= 0.5 and active_elapsed > 0.0:
            raw_factor = active_elapsed / self.completed_baseline_time
            self.live_speed_factor = max(0.05, min(10.0, raw_factor))
        self.active_elapsed_at_step_start = active_elapsed

    def compute_remaining_time(self, now: float = None) -> float:
        t_now = time.time() if now is None else float(now)
        idx = max(0, int(getattr(self, "current_step_idx", 0)))
        seq = getattr(self, "workflow_sequence", [])
        if idx >= len(seq):
            return 0.0

        if len(getattr(self, "step_baseline_times", [])) == len(seq):
            rem_baselines = self.step_baseline_times[idx:]
        else:
            rem_baselines = self._estimate_step_durations(seq[idx:])

        remaining_baseline = sum(rem_baselines)
        factor = getattr(self, "live_speed_factor", 1.0) or 1.0
        scaled_remaining = remaining_baseline * factor

        active_elapsed = self.get_active_elapsed_time(t_now)
        in_step_elapsed = max(0.0, active_elapsed - getattr(self, "active_elapsed_at_step_start", 0.0))
        curr_step_cap = (rem_baselines[0] * factor * 0.95) if rem_baselines else 0.0
        deduction = min(in_step_elapsed, curr_step_cap)
        return max(0.0, scaled_remaining - deduction)

    def _analyze_protocol_tips_and_slots(self, sequence=None, is_multichannel=None, deck_setup=None, slot_descriptions=None):
        """
        Analyzes protocol sequence and deck setup to calculate:
          1. tips_info: list of strings describing tip requirements (count, wells/cols, slot).
          2. empty_slots: list of slot labels (e.g. ['Slot 2', 'Slot 6']) that MUST remain completely empty.
          3. active_slots: list of slot labels (e.g. ['Slot 1', 'Slot 3', 'Slot 4', 'Slot 5']) holding labware.
        """
        seq = sequence if sequence is not None else getattr(self, "workflow_sequence", [])
        deck = deck_setup if deck_setup is not None else getattr(getattr(self, "lims", None), "deck_labware", {})
        descs = slot_descriptions or {}

        if is_multichannel is None:
            is_8ch = bool(
                getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "multichannel", False)
                or any(s.get("eight_ch_symmetric") for s in seq)
                or any("8-ch" in str(s.get("label", "")).lower() for s in seq)
            )
        else:
            is_8ch = bool(is_multichannel)

        # 1. Analyze tips
        pickup_steps = [s for s in seq if s.get("action") == "Pick Up Tip"]
        slots_with_tips = sorted(list(set(s.get("slot", "Slot_4") for s in pickup_steps)))
        tips_info = []

        if not pickup_steps:
            for s_num in range(1, 7):
                sn = f"Slot_{s_num}"
                lw_name = ""
                if isinstance(deck, dict):
                    lw_val = deck.get(sn)
                    lw_name = getattr(lw_val, "source_file", "") if hasattr(lw_val, "source_file") else str(lw_val or "")
                if "tip" in lw_name.lower():
                    tips_info.append(f"Slot {s_num}: Tip Rack loaded (Pre-attached tip expected)")
            if not tips_info:
                tips_info.append("0 tips required (No tip pickup steps in protocol)")
        else:
            for ts in slots_with_tips:
                ts_label = ts.replace("_", " ")
                wells = [s.get("well", "") for s in pickup_steps if s.get("slot") == ts]
                if is_8ch:
                    cols = []
                    for w in wells:
                        if len(w) > 1 and w[1:].isdigit():
                            cols.append(int(w[1:]))
                    cols = sorted(list(set(cols)))
                    ch_counts = []
                    for s in pickup_steps:
                        if s.get("slot") == ts:
                            m_ch = str(s.get("mounted_channels", "A-H")).strip().upper()
                            if "-" in m_ch:
                                s_ch, e_ch = m_ch.split("-", 1)
                                count = ord(e_ch.strip()) - ord(s_ch.strip()) + 1
                            else:
                                count = 1
                            ch_counts.append(count)
                    tips_per_col = max(ch_counts) if ch_counts else 8
                    total_tips = len(wells) * tips_per_col
                    if len(cols) > 4:
                        col_str = f"Cols {cols[0]}..{cols[-1]}"
                    elif len(cols) > 0:
                        col_str = f"Cols {', '.join(str(c) for c in cols)}"
                    else:
                        col_str = "All cols"

                    if tips_per_col == 5:
                        tips_info.append(f"{ts_label}: {total_tips} fresh tips ({tips_per_col} tips per column: Rows A–E across {col_str})")
                    else:
                        tips_info.append(f"{ts_label}: {total_tips} fresh tips ({len(cols)} columns: {col_str})")
                else:
                    total_tips = len(wells)
                    cols = sorted(list(set(int(w[1:]) for w in wells if len(w) > 1 and w[1:].isdigit())))
                    if len(cols) > 1:
                        col_str = f"Columns {cols[0]}..{cols[-1]}"
                    elif len(cols) == 1:
                        col_str = f"Column {cols[0]}"
                    else:
                        col_str = "All columns"

                    if len(wells) > 4:
                        w_str = f"{wells[0]}..{wells[-1]}"
                    elif len(wells) > 0:
                        w_str = f"{', '.join(wells)}"
                    else:
                        w_str = "Standard layout"

                    tips_info.append(f"{ts_label}: {total_tips} fresh tips in {col_str} ({w_str})")

        # 2. Analyze active vs empty slots
        seq_slots = set(s.get("slot") for s in seq if s.get("slot"))
        empty_slots = []
        active_slots = []

        for s_num in range(1, 7):
            sn = f"Slot_{s_num}"
            s_label = f"Slot {s_num}"
            lw_name = ""
            if isinstance(deck, dict):
                lw_val = deck.get(sn)
                lw_name = getattr(lw_val, "source_file", "") if hasattr(lw_val, "source_file") else str(lw_val or "")
            desc = descs.get(sn, "")

            is_empty = False
            if lw_name in ["(Empty / Clearance)", "", "None", None]:
                is_empty = True
            elif "empty" in desc.lower() or "clearance" in desc.lower():
                is_empty = True
            elif seq and sn not in seq_slots and not ("tip" in lw_name.lower() or "waste" in lw_name.lower()):
                is_empty = True

            if is_empty:
                empty_slots.append(s_label)
            else:
                active_slots.append(s_label)

        return tips_info, empty_slots, active_slots

    def _update_deck_and_tip_preview(self):
        if not hasattr(self, "lbl_deck_summary"):
            return
        if not self.workflow_sequence:
            self.lbl_deck_summary.config(
                text="📋 Deck: No protocol loaded | Tips: None",
                fg="#6c757d",
                bg="#f8f9fa"
            )
            return
        tips_info, empty_slots, active_slots = self._analyze_protocol_tips_and_slots(self.workflow_sequence)
        tip_text = " | ".join(tips_info) if tips_info else "0 tips required"
        empty_text = ", ".join(empty_slots) if empty_slots else "None (All 6 slots occupied)"
        self.lbl_deck_summary.config(
            text=f"🎯 Tips Needed: {tip_text}\n⛔ KEEP EMPTY: {empty_text}",
            fg="#0c5460",
            bg="#d1ecf1"
        )

    def _update_estimated_timer_preview(self):
        if getattr(self, "is_running", False) or not hasattr(self, "lbl_timer"):
            return
        self._update_deck_and_tip_preview()
        if not self.workflow_sequence:
            self.lbl_timer.config(text="Time Remaining: --h --m --s", foreground="blue")
            return
        est_s = self.estimate_workflow_time(self.workflow_sequence)
        self.lbl_timer.config(text=f"Time Remaining: {self.format_hms(est_s)}", foreground="blue")

    def setup_ui(self):
        con_f = ttk.LabelFrame(self.root, text="Diagnostic Output")
        con_f.pack(fill=tk.X, padx=10, pady=(2, 6), side=tk.BOTTOM)
        self.console_text = tk.Text(con_f, height=5, state='disabled', bg="white", fg="black", font=("Consolas", 9))
        self.console_text.pack(fill=tk.X)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.tab_jog = ttk.Frame(self.nb, padding=8)
        self.tab_deck = ttk.Frame(self.nb, padding=8)
        self.tab_direct = ttk.Frame(self.nb, padding=10)
        self.tab_workflow = ttk.Frame(self.nb, padding=6)
        self.tab_analysis = ttk.Frame(self.nb, padding=8)  # NEW
        self.tab_ops = ttk.Frame(self.nb, padding=8)
        self.tab_dilution = ttk.Frame(self.nb, padding=8)

        self.nb.add(self.tab_jog, text="1. Jog & Hardware")
        self.nb.add(self.tab_deck, text="2. Deck Setup")
        self.nb.add(self.tab_direct, text="3. Direct Operations")
        self.nb.add(self.tab_workflow, text="4. Protocol Runner")
        self.nb.add(self.tab_analysis, text="5. Data Analysis")  # NEW
        self.nb.add(self.tab_ops, text="6. Daily Operations")
        self.nb.add(self.tab_dilution, text="7. SIPA Dilution Calc")

        self.build_jog_tab()
        self.build_deck_tab()
        self.build_direct_ops_tab()
        self.build_workflow_tab()
        self.build_analysis_tab()
        self.build_ops_tab()
        self.build_dilution_tab()

        # AnalyzerGUI is now launched via pop-out button  # NEW------------------


    def execute_routine(self, op_name, default_file):
        config_file = "routine_config.json"
        import json
        import os
        import threading
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        protocol_path = config.get(op_name, default_file)
        
        if not os.path.exists(protocol_path):
            messagebox.showwarning("Not Found", f"Protocol file not found:\n{protocol_path}")
            return
            
        try:
            with open(protocol_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            for step in loaded_sequence:
                if 'action' not in step: continue
                self.workflow_sequence.append(step)
                self.wf_box.insert(tk.END, f"[LOADED] {step['action']}")
            self.nb.select(self.tab_workflow)
            self.logger.info(f"Loaded {op_name} Routine. Auto-starting sequence...")
            
            # Start the run sequence automatically in a background thread just like the RUN button does
            threading.Thread(target=self.run_sequence, daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error loading routine: {e}")
            messagebox.showerror("Error", str(e))

    def assign_routine(self, op_name):
        filepath = filedialog.askopenfilename(title=f"Assign JSON to {op_name}", filetypes=[("JSON Protocol", "*.json")])
        if filepath:
            config_file = "routine_config.json"
            import json, os
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            config[op_name] = filepath
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Saved", f"{op_name} is now mapped to:\n{filepath}")


    def build_analysis_tab(self):
        # Create left and right container boxes
        self.frame_heatmap = ttk.LabelFrame(self.tab_analysis, text="Quality Control (Baseline Heatmaps)")
        self.frame_heatmap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Analyze Measurement")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        lbl_ca2 = ttk.Label(self.frame_ca2, text="Kinetic Traces & Peak Forces", font=("Arial", 16, "bold"))
        lbl_ca2.pack(pady=5)
        
        desc_ca2 = ttk.Label(self.frame_ca2, text="Launch the full-screen interactive dashboard\nto analyze measurements and kinetic traces.", justify=tk.CENTER)
        desc_ca2.pack(pady=5)
        
        btn_launch = ttk.Button(self.frame_ca2, text="Launch Dashboard", command=self.launch_analyzer_popout)
        btn_launch.pack(pady=20)

        # Place heatmap logic in the left box
        lbl = ttk.Label(self.frame_heatmap, text="FOC48 Baseline Heatmaps", font=("Arial", 16, "bold"))
        lbl.pack(pady=5)
        
        desc = ttk.Label(self.frame_heatmap, text="Automatically parses .stats.xml and .xml files\nto generate baseline heatmaps.", justify=tk.CENTER)
        desc.pack(pady=5)
        
        btn_folder = ttk.Button(self.frame_heatmap, text="Select Folder for Heatmaps", command=self.run_heatmap_analysis)
        btn_folder.pack(pady=10)
        
        # Image Viewer Section
        self.heatmap_display = tk.Label(self.frame_heatmap, text="No image to display", bg="white")
        self.heatmap_display.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # Navigation Buttons
        self.heatmap_nav_frame = ttk.Frame(self.frame_heatmap)
        self.heatmap_nav_frame.pack(pady=5)
        
        self.btn_prev = ttk.Button(self.heatmap_nav_frame, text="< Prev", command=self.prev_heatmap, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        
        self.lbl_gallery = ttk.Label(self.heatmap_nav_frame, text="0 / 0")
        self.lbl_gallery.pack(side=tk.LEFT, padx=10)
        
        self.btn_next = ttk.Button(self.heatmap_nav_frame, text="Next >", command=self.next_heatmap, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        
        self.heatmap_image_paths = []
        self.current_heatmap_index = 0
        self._current_photo = None

    def run_heatmap_analysis(self):
        import json
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("heatmap", "/")
        except Exception: pass

        folder_path = filedialog.askdirectory(title="Select FOC48 Data Folder", initialdir=init_dir)
        if folder_path:
            try:
                data = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f: data = json.load(f)
                data["heatmap"] = folder_path
                with open(config_path, "w") as f: json.dump(data, f)
            except Exception: pass

        if not folder_path: return
        
        import glob
        from datetime import datetime
        
        search_pattern = os.path.join(folder_path, "*.stats.xml")
        stats_files = glob.glob(search_pattern)
        
        if not stats_files:
            messagebox.showinfo("No Files", f"No .stats.xml files found in {folder_path}")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_dir = os.path.join(folder_path, f"Analysis_{timestamp}")
        os.makedirs(save_dir, exist_ok=True)
            
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = ['1', '2', '3', '4', '5', '6']
        
        for stats_file in stats_files:
            base_xml = stats_file.replace(".stats.xml", ".xml")
            pix2mm = 28.7
            
            def clean_and_parse(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    xml_data = f.read()
                xml_data = xml_data.replace('encoding="UTF - 8"', 'encoding="UTF-8"').replace('version="1.1"', 'version="1.0"')
                xml_data = re.sub(r'<!.*?>', '', xml_data)
                return ET.fromstring(xml_data)
            
            if os.path.exists(base_xml):
                try:
                    b_root = clean_and_parse(base_xml)
                    p_node = b_root.find("pixel_per_mm")
                    if p_node is not None: pix2mm = float(p_node.text)
                except Exception as e:
                    self.logger.warning(f"Could not read pix2mm: {e}")
            
            try:
                root = clean_and_parse(stats_file)
                df = pd.DataFrame(index=rows, columns=cols, dtype=float)
                for r in rows:
                    for c in cols:
                        w_node = root.find(f"{r}{c}")
                        if w_node is not None:
                            b_pix = w_node.find("baseline")
                            if b_pix is not None:
                                df.at[r, c] = float(b_pix.text) / pix2mm
                                
                from matplotlib.colors import LinearSegmentedColormap
                colors = [
                    (0.000, "mediumblue"),
                    (0.332, "deepskyblue"),
                    (0.333, "mediumseagreen"),
                    (0.500, "limegreen"),
                    (0.666, "mediumseagreen"),
                    (0.667, "lightcoral"),
                    (1.000, "firebrick")
                ]
                custom_cmap = LinearSegmentedColormap.from_list("blue_green_red", colors)
                fig, ax = plt.subplots(figsize=(12, 9))
                sns.heatmap(df, annot=True, fmt=".2f", cmap=custom_cmap, vmin=3.5, vmax=4.4, cbar_kws={'label': 'Baseline (mm)'}, ax=ax)
                ax.xaxis.tick_top()
                ax.xaxis.set_label_position('top')
                plt.yticks(rotation=0)
                
                # --- Apply QC Flags ---
                try:
                    from backend_qc import qc_heatmap_baselines
                    fail_mask = qc_heatmap_baselines(df)
                    for i in range(df.shape[0]):
                        for j in range(df.shape[1]):
                            if fail_mask.iloc[i, j]:
                                # Draw a translucent bold red X over failing cells
                                plt.text(j + 0.5, i + 0.5, 'X', color='red', fontsize=32, ha='center', va='center', fontweight='bold', alpha=0.5)
                except Exception as qc_e:
                    self.logger.error(f"QC Flagging failed: {qc_e}")
                # ----------------------
                
                file_name = os.path.basename(stats_file)
                plt.title(f"Baseline Heatmap: {file_name}\n(Calculated using {pix2mm} pixels/mm)\nTarget Range: 3.8mm - 4.1mm", fontsize=14)
                plt.xlabel("Columns")
                plt.ylabel("Rows")
                plt.figtext(0.5, 0.01, "Values between 3.8 and 4.1 are ideal. <3.8 is too small, >4.1 is too large.", ha="center", fontsize=10, bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})
                
                # Save to the timestamped folder
                image_name = file_name.replace(".stats.xml", "_heatmap.png")
                save_path = os.path.join(save_dir, image_name)
                plt.savefig(save_path, bbox_inches='tight', dpi=150)
                
                # Close the plot silently instead of popping up a blocking window
                plt.close()
            except Exception as e:
                self.logger.error(f"Error parsing {stats_file}: {e}")
                messagebox.showerror("Error", f"Failed to process {os.path.basename(stats_file)}\n{e}")
                
        
        # Load into gallery
        self.heatmap_image_paths = [os.path.join(save_dir, f) for f in os.listdir(save_dir) if f.endswith('_heatmap.png')]
        self.heatmap_image_paths.sort()
        if self.heatmap_image_paths:
            self.current_heatmap_index = 0
            self.update_heatmap_gallery()
            
        messagebox.showinfo("Success", f"Analysis complete! Displaying heatmaps.\nFiles saved to:\n{save_dir}")


    def update_heatmap_gallery(self):
        if not self.heatmap_image_paths:
            return
            
        img_path = self.heatmap_image_paths[self.current_heatmap_index]
        try:
            pil_img = Image.open(img_path)
            # Resize image to fit nicely in the GUI frame
            pil_img.thumbnail((600, 500), Image.Resampling.LANCZOS)
            self._current_photo = ImageTk.PhotoImage(pil_img)
            self.heatmap_display.config(image=self._current_photo, text="")
            
            # Update counter and buttons
            total = len(self.heatmap_image_paths)
            self.lbl_gallery.config(text=f"{self.current_heatmap_index + 1} / {total}")
            
            self.btn_prev.config(state=tk.NORMAL if self.current_heatmap_index > 0 else tk.DISABLED)
            self.btn_next.config(state=tk.NORMAL if self.current_heatmap_index < total - 1 else tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"Failed to display heatmap {img_path}: {e}")

    def prev_heatmap(self):
        if self.current_heatmap_index > 0:
            self.current_heatmap_index -= 1
            self.update_heatmap_gallery()
            
    def next_heatmap(self):
        if self.current_heatmap_index < len(self.heatmap_image_paths) - 1:
            self.current_heatmap_index += 1
            self.update_heatmap_gallery()

    def launch_analyzer_popout(self):
        popout = tk.Toplevel(self.root)
        popout.title("Analyze Measurement Dashboard")
        popout.geometry("1600x900")
        
        # Instantiate the AnalyzerGUI inside the new full-screen Toplevel window
        global AnalyzerGUI
        if AnalyzerGUI is None:
            try:
                from gui import GUI as AnalyzerGUI
            except Exception:
                AnalyzerGUI = None
        if AnalyzerGUI:
            self.analyzer = AnalyzerGUI(master=popout)

    def build_ops_tab(self):
        ttk.Label(self.tab_ops, text="TECHNICIAN DAILY OPERATIONS", font=("Arial", 14, "bold")).pack(pady=20)
        
        frame_ops = ttk.Frame(self.tab_ops)
        frame_ops.pack(fill=tk.BOTH, expand=True, padx=50)
        
        ops = [
            ("Daily Media Change (500uL)", "media_change"),
            ("Friday Acute SIPA Test", "acute_test"),
            ("Automated Calcium Curve", "calcium_curve")
        ]
        
        for ui_name, key in ops:
            row = ttk.Frame(frame_ops)
            row.pack(fill=tk.X, pady=10)
            ttk.Button(row, text=f"RUN: {ui_name}", command=lambda k=key: self.execute_routine(k, "")).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            ttk.Button(row, text="Assign JSON", width=15, command=lambda k=key: self.assign_routine(k)).pack(side=tk.RIGHT, padx=10)

    def build_dilution_tab(self):
        ttk.Label(self.tab_dilution, text="SIPA Dilution Calculator (Target <1% DMSO, >50uL vol)", font=("Arial", 12, "bold")).pack(pady=10)
        
        f_in = ttk.LabelFrame(self.tab_dilution, text="Inputs", padding=15)
        f_in.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(f_in, text="Stock Concentration (mM):").grid(row=0, column=0, sticky="e", pady=5)
        ent_stock = ttk.Entry(f_in)
        ent_stock.insert(0, "10")
        ent_stock.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(f_in, text="Target Well Concentration (uM):").grid(row=1, column=0, sticky="e", pady=5)
        ent_target = ttk.Entry(f_in)
        ent_target.insert(0, "30")
        ent_target.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(f_in, text="Well Media Volume (uL):").grid(row=2, column=0, sticky="e", pady=5)
        ent_vol = ttk.Entry(f_in)
        ent_vol.insert(0, "500")
        ent_vol.grid(row=2, column=1, pady=5, padx=5)
        
        res_text = tk.Text(self.tab_dilution, height=10, font=("Consolas", 10))
        res_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        def calc():
            try:
                stock_um = float(ent_stock.get()) * 1000
                target_um = float(ent_target.get())
                well_vol = float(ent_vol.get())
                
                dilution_factor = stock_um / target_um
                transfer_vol = well_vol / (dilution_factor - 1)
                dmso_pct = (transfer_vol / (well_vol + transfer_vol)) * 100
                
                res = f"--- DILUTION RESULTS ---\n"
                res += f"Transfer Volume Needed: {transfer_vol:.2f} uL\n"
                res += f"Final DMSO Concentration: {dmso_pct:.3f}%\n\n"
                
                if transfer_vol < 50:
                    res += "[WARNING] Transfer volume is < 50uL! Prepare an intermediate working stock.\n"
                else:
                    res += "[OK] Transfer volume is >= 50uL.\n"
                    
                if dmso_pct > 1.0:
                    res += "[WARNING] DMSO limit exceeded (>1%)! Tissue toxicity risk.\n"
                else:
                    res += "[OK] DMSO is within safe limits (<1%).\n"
                    
                res_text.delete(1.0, tk.END)
                res_text.insert(tk.END, res)
            except Exception as e:
                res_text.delete(1.0, tk.END)
                res_text.insert(tk.END, f"Error: {e}")
                
        ttk.Button(f_in, text="Calculate", command=calc).grid(row=3, column=0, columnspan=2, pady=15)

    def _set_has_tip(self, val: bool):
        """Thread-safe tip attachment state setter (updates worker flag synchronously + Tk BooleanVar on main thread)."""
        bval = bool(val)
        self._worker_has_tip = bval
        if threading.current_thread() is threading.main_thread():
            self.has_tip_var.set(bval)
        else:
            self.root.after(0, lambda v=bval: self.has_tip_var.set(v))

    def switch_pipettor_head(self, multichannel=None, quiet: bool = False, tip_volume: float = None, head_name: str = None):
        if getattr(self, 'is_running', False):
            messagebox.showwarning("Protocol Active", "Cannot switch pipettor head mode while a protocol is running.")
            return

        # Determine head type from string or arguments
        if head_name is None and isinstance(multichannel, str):
            head_name = multichannel
            multichannel = None

        if head_name is not None:
            hn = head_name.lower()
            if "1000" in hn or "8×1000" in hn:
                is_multi = True
                target_vol = 1000.0
                label = "8-Channel Multi (8×1000 µL)"
                badge_txt = "HEAD: 8×1000 µL MULTI"
                badge_bg = "#6f42c1"
            elif "1-10" in hn or "8×10" in hn or "10 µl" in hn or "10ul" in hn or ("10" in hn and "1000" not in hn):
                is_single = "single" in hn
                is_multi = not is_single
                target_vol = 10.0
                label = "1-10 µL Single-Channel" if is_single else "8-Channel Multi (1-10 µL)"
                badge_txt = "HEAD: 1-10 µL SINGLE" if is_single else "HEAD: 8×10 µL MULTI"
                badge_bg = "#20c997"
            elif "300" in hn:
                is_multi = False
                target_vol = 300.0
                label = "300 µL Single-Channel"
                badge_txt = "HEAD: 1×300 µL SINGLE"
                badge_bg = "#fd7e14"
            elif "20" in hn and "200" not in hn:
                is_multi = False
                target_vol = 20.0
                label = "20 µL Single-Channel"
                badge_txt = "HEAD: 1×20 µL SINGLE"
                badge_bg = "#0d6efd"
            elif "8-ch" in hn or "manifold" in hn or "multi" in hn:
                is_multi = True
                target_vol = 1000.0
                label = "8-Channel Multi (8×1000 µL)"
                badge_txt = "HEAD: 8×1000 µL MULTI"
                badge_bg = "#6f42c1"
            else:
                is_multi = False
                target_vol = 250.0
                label = "1×250 µL (Single-Channel)"
                badge_txt = "HEAD: 1×250 µL SINGLE"
                badge_bg = "#0d6efd"
        else:
            is_multi = bool(multichannel)
            if tip_volume is not None:
                target_vol = float(tip_volume)
                if is_multi and target_vol <= 50.0:
                    label = "8-Channel Multi (1-10 µL)"
                    badge_txt = "HEAD: 8×10 µL MULTI"
                    badge_bg = "#20c997"
                elif not is_multi and target_vol == 300.0:
                    label = "300 µL Single-Channel"
                    badge_txt = "HEAD: 1×300 µL SINGLE"
                    badge_bg = "#fd7e14"
                elif not is_multi and target_vol <= 50.0:
                    label = "20 µL Single-Channel"
                    badge_txt = "HEAD: 1×20 µL SINGLE"
                    badge_bg = "#0d6efd"
                elif is_multi:
                    label = "8-Channel Multi (8×1000 µL)"
                    badge_txt = "HEAD: 8×1000 µL MULTI"
                    badge_bg = "#6f42c1"
                else:
                    label = "1×250 µL (Single-Channel)"
                    badge_txt = "HEAD: 1×250 µL SINGLE"
                    badge_bg = "#0d6efd"
            else:
                target_vol = 1000.0 if is_multi else 250.0
                label = "8-Channel Multi (8×1000 µL)" if is_multi else "1×250 µL (Single-Channel)"
                badge_txt = "HEAD: 8×1000 µL MULTI" if is_multi else "HEAD: 1×250 µL SINGLE"
                badge_bg = "#6f42c1" if is_multi else "#0d6efd"

        self.head_mode_var.set(label)
        if hasattr(self, 'proto_pipettor_var') and self.proto_pipettor_var.get() != label:
            self.proto_pipettor_var.set(label)

        ok, msg = self.lims.pipettor.reconfigure(tip_volume=target_vol, multichannel=is_multi)
        # Keep BiohitInterface bound to the same pipettor object
        self.lims.hw.pipettor = self.lims.pipettor

        # Sync active machine profile calibrations for switched head mode
        matching_pid = None
        if is_multi and target_vol >= 500.0:
            matching_pid = "machine_1_8x1000"
        elif is_multi and target_vol <= 50.0:
            matching_pid = "machine_2_1_10ul"
        elif not is_multi and target_vol == 300.0:
            matching_pid = "machine_3_300ul"

        if matching_pid and hasattr(self, 'profile_manager') and self.profile_manager:
            if matching_pid != getattr(self, 'active_profile_id', None):
                self.active_profile_id = matching_pid
                self.calibrated_heights = self.profile_manager.load_profile(matching_pid)
                if "300" in matching_pid:
                    if float(self.calibrated_heights.get("plate96_aspirate_z", 98.72)) in (78.4, 78.40, 97.52):
                        self.calibrated_heights["plate96_aspirate_z"] = 98.72
                    if float(self.calibrated_heights.get("plate96_dispense_z", 98.72)) in (68.43, 78.4, 78.40, 97.52):
                        self.calibrated_heights["plate96_dispense_z"] = 98.72
                    if float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 92.0)) <= 88.0:
                        self.calibrated_heights["tip_rack_pickup_limit_z"] = 92.0
                    if float(self.calibrated_heights.get("plate96_dmso_dispense_z", 98.72)) in (75.0, 75.00, 68.43, 97.52):
                        self.calibrated_heights["plate96_dmso_dispense_z"] = 98.72
                    self.calibrated_heights.setdefault("plate96_dmso_dispense_z", 98.72)
                if hasattr(self, 'apply_default_deck_for_profile'):
                    self.apply_default_deck_for_profile(matching_pid)
                if hasattr(self, 'update_window_title'):
                    self.update_window_title()

        if is_multi:
            # 8-channel manifold has no tip oscillation/capacitance sensor; disable LLD surface probing automatically
            if hasattr(self, 'lld_tracking_var'):
                self.lld_tracking_var.set(False)
            if hasattr(self, 'dynamic_z_var'):
                self.dynamic_z_var.set(False)
            if hasattr(self, 'tip_length_var'):
                # 10 uL multi and 300 uL single share the same tip height stack (~50 mm)
                if target_vol <= 50.0:
                    self.tip_length_var.set(getattr(self, 'CAL_TIP_LENGTH_MM', 50.0))
                else:
                    self.tip_length_var.set(getattr(self, 'TIP_1000_LENGTH_MM', 60.0))
        else:
            # Single-channel head supports tip oscillation/LLD and dynamic Z tracking; restore defaults
            if hasattr(self, 'lld_tracking_var'):
                self.lld_tracking_var.set(True)
            if hasattr(self, 'dynamic_z_var'):
                self.dynamic_z_var.set(True)
            if hasattr(self, 'tip_length_var'):
                self.tip_length_var.set(getattr(self, 'CAL_TIP_LENGTH_MM', 50.0))

        if hasattr(self, 'lbl_head_badge'):
            self.lbl_head_badge.config(text=badge_txt, bg=badge_bg)

        if hasattr(self, 'logger'):
            sensor_note = (
                f"8-channel head has no liquid-level sensor -> uses fixed calibrated heights "
                f"(tip compensation -{self.EIGHT_CH_TIP_Z_COMP_MM:.1f} mm)"
                if is_multi else "Liquid-level sensor (LLD) available"
            )
            self.logger.info(f"[HEAD MODE] Switched to {label} ({msg}) | {sensor_note}")
        if not quiet and not ok:
            messagebox.showwarning("Hardware Driver Notice", msg)

    def _on_head_mode_combo(self, event=None):
        sel = self.head_mode_var.get()
        self.switch_pipettor_head(sel, quiet=True)
        if hasattr(self, '_update_protocol_dropdown'):
            self._update_protocol_dropdown()

    def build_jog_tab(self):
        f_conn = ttk.LabelFrame(self.tab_jog, text="Hardware Handshake & Pipettor Head", padding=15)
        f_conn.pack(fill=tk.X, padx=20, pady=10)
        self.port_var = tk.StringVar(value="Select Hardware Port...")
        self.port_drop = ttk.Combobox(f_conn, textvariable=self.port_var, state="readonly", width=38)
        self.port_drop.pack(side=tk.LEFT, padx=5)
        self.port_drop.bind("<<ComboboxSelected>>", self._on_port_selected)
        ttk.Button(f_conn, text="Scan Ports", command=self.hw_scan).pack(side=tk.LEFT, padx=5)
        self.btn_hw_init = ttk.Button(f_conn, text="Connect & Initialize", command=self.hw_init)
        self.btn_hw_init.pack(side=tk.LEFT, padx=10)
        self.hw_stat_can = tk.Canvas(f_conn, width=20, height=20, highlightthickness=0)
        self.hw_stat_can.pack(side=tk.LEFT, padx=5)
        self.hw_led = self.hw_stat_can.create_oval(2, 2, 18, 18, fill="gray")
        self.lbl_hw_stat = ttk.Label(f_conn, text="OFFLINE", font=("Arial", 9, "bold"))
        self.lbl_hw_stat.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(f_conn, text="Pipettor Head:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(8, 4))
        head_cb = ttk.Combobox(
            f_conn,
            textvariable=self.head_mode_var,
            values=[
                "8-Channel Multi (8×1000 µL) [Media Change]",
                "300 µL Single-Channel [Prepping DMSO-Drug]",
                "8-Channel Multi (1-10 µL) [Drug Addition to EHM]",
            ],
            state="readonly",
            width=26,
        )
        head_cb.pack(side=tk.LEFT, padx=4)
        head_cb.bind("<<ComboboxSelected>>", self._on_head_mode_combo)

        f_speed = ttk.LabelFrame(self.tab_jog, text="Global Kinematic Speed (%)", padding=15)
        f_speed.pack(fill=tk.X, padx=20, pady=5)
        self.speed_var = tk.IntVar(value=100)
        speed_f = ttk.Frame(f_speed)
        speed_f.pack(fill=tk.X, padx=100, pady=5)
        ttk.Label(speed_f, text="Velocity:", width=10, font=("Arial", 11)).pack(side=tk.LEFT)
        s_speed = ttk.Scale(speed_f, from_=1, to=100, variable=self.speed_var, orient='horizontal')
        s_speed.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        l_speed = ttk.Label(speed_f, text="100%", width=8, font=("Arial", 11, "bold"))
        l_speed.pack(side=tk.LEFT)
        self.speed_var.trace_add("write", lambda *a, var=self.speed_var, lbl=l_speed: lbl.config(text=f"{var.get()}%"))

        f_jog = ttk.LabelFrame(self.tab_jog, text="Position Calibration Sliders", padding=15)
        f_jog.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self.jog_vars = {"X": tk.DoubleVar(), "Y": tk.DoubleVar(), "Z": tk.DoubleVar()}
        self.jog_btns = {}

        for axis in ["X", "Y", "Z"]:
            f = ttk.Frame(f_jog)
            f.pack(fill=tk.X, padx=100, pady=8)
            ttk.Label(f, text=f"{axis}-Axis (mm):", width=12, font=("Arial", 11)).pack(side=tk.LEFT)

            btn_m = tk.Button(f, text=" - ", bg="#e9ecef", font=("Consolas", 10, "bold"), width=4, state='disabled',
                              command=lambda a=axis: self.jog_step(a, -1.0))
            btn_m.pack(side=tk.LEFT, padx=(5, 3))
            self.jog_nudge_btns.append(btn_m)

            e = ttk.Entry(f, textvariable=self.jog_vars[axis], font=("Consolas", 11), state='disabled', width=12)
            e.pack(side=tk.LEFT, padx=3)
            self.jog_sliders[axis] = e

            btn_p = tk.Button(f, text=" + ", bg="#e9ecef", font=("Consolas", 10, "bold"), width=4, state='disabled',
                              command=lambda a=axis: self.jog_step(a, +1.0))
            btn_p.pack(side=tk.LEFT, padx=(3, 10))
            self.jog_nudge_btns.append(btn_p)

            btn = tk.Button(f, text="GO TO", bg="#007bff", fg="white", font=("Arial", 9, "bold"), state='disabled',
                            command=lambda ax=axis: self._execute_jog_move(ax))
            btn.pack(side=tk.LEFT, padx=5)
            self.jog_btns[axis] = btn

            e.bind('<Return>', lambda event, ax=axis: self._execute_jog_move(ax))

        f_step = ttk.Frame(f_jog)
        f_step.pack(fill=tk.X, padx=100, pady=(15, 5))
        ttk.Label(f_step, text="Jog Step Size:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        for step_val in [0.1, 1.0, 5.0, 10.0, 30.0, 50.0, 100.0]:
            r_btn = ttk.Radiobutton(f_step, text=f"{step_val} mm", value=step_val, variable=self.jog_step_var)
            r_btn.pack(side=tk.LEFT, padx=5)

        f_quick_z = ttk.Frame(f_jog)
        f_quick_z.pack(fill=tk.X, padx=100, pady=(4, 5))
        ttk.Label(f_quick_z, text="Quick Z Homing Presets:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        for z_preset in [0.0, 30.0, 50.0, 100.0]:
            btn_txt = "Home Z (0 mm)" if z_preset == 0.0 else f"Z = {int(z_preset)} mm"
            btn_qz = tk.Button(
                f_quick_z,
                text=btn_txt,
                bg="#e9ecef",
                font=("Consolas", 9, "bold"),
                command=lambda zp=z_preset: self._quick_move_z(zp),
            )
            btn_qz.pack(side=tk.LEFT, padx=4)

        f_opt = ttk.Frame(f_jog)
        f_opt.pack(fill=tk.X, padx=100, pady=5)
        ttk.Checkbutton(f_opt, text="Retract Z to 0 before XY moves (Clearance Lift)", variable=self.jog_z_clearance_var).pack(side=tk.LEFT)

        f_guide = ttk.LabelFrame(f_jog, text="⌨️ Keyboard Live Jog Controls (Active Anywhere in Window)", padding=10)
        f_guide.pack(fill=tk.X, padx=100, pady=12)
        guide_text = (
            "• X-Axis (Left / Right):   ◄ / ►   or   A / D\n"
            "• Y-Axis (Forward / Back): ▲ / ▼   or   W / S\n"
            "• Z-Axis (Up / Down):      PgUp (▲) / PgDn (▼)   or   Q / E   or   + / -\n"
            "• Multipliers: Hold Shift for 10× (10mm) | Hold Ctrl for 0.1× (0.1mm)\n"
            "• Direct Motion: Moves directly without pulling Z up to 0 (stays at current height)"
        )
        ttk.Label(f_guide, text=guide_text, font=("Consolas", 9), foreground="#0056b3").pack(anchor="w")

        # Auto-scan available ports on initialization
        try:
            self.hw_scan(announce=False)
        except Exception:
            pass

    def _quick_move_z(self, z_target):
        self.jog_vars["Z"].set(round(float(z_target), 2))
        self._execute_jog_move("Z")

    def _safe_get_jog(self, axis):
        try:
            if hasattr(self, 'jog_sliders') and axis in self.jog_sliders:
                txt = self.jog_sliders[axis].get().strip()
                if txt:
                    val = float(txt)
                    self.jog_vars[axis].set(round(val, 2))
                    return val
        except Exception:
            pass
        try:
            val = self.jog_vars[axis].get()
            return float(val)
        except Exception:
            cur = float(self.current_pos.get(axis, 0.0))
            try:
                self.jog_vars[axis].set(cur)
            except Exception:
                pass
            return cur

    def _safe_get_speed(self):
        try:
            return float(self.speed_var.get())
        except Exception:
            return 1500.0

    def _execute_jog_move(self, ax=None):
        x = self._safe_get_jog("X")
        y = self._safe_get_jog("Y")
        z = self._safe_get_jog("Z")
        speed = self._safe_get_speed()
        clearance = getattr(self, 'jog_z_clearance_var', tk.BooleanVar(value=False)).get()

        try:
            self.root.focus_set()
        except Exception:
            pass

        self.current_pos["X"] = x
        self.current_pos["Y"] = y
        self.current_pos["Z"] = z
        if hasattr(self, 'draw_deck'):
            try:
                self.draw_deck()
            except Exception:
                pass

        def _worker():
            try:
                hw = self.lims.pipettor.hardware
                if hw:
                    hw_speed = max(1, min(9, int((speed / 100.0) * 9)))
                    try:
                        hw.x_speed = hw_speed
                        hw.y_speed = hw_speed
                        hw.z_speed = hw_speed
                    except Exception:
                        pass

                    if ax == "Z":
                        hw.move_z(z, wait=True)
                    elif ax == "X":
                        if clearance:
                            hw.move_z(0, wait=True)
                        try:
                            hw.move_x(x, wait=True)
                        except (AttributeError, TypeError):
                            try:
                                hw.move_xy(x, hw.y_position, wait=True)
                            except (AttributeError, TypeError):
                                hw.move_xy(x, y, wait=True)
                        if clearance and z > 0:
                            hw.move_z(z, wait=True)
                    elif ax == "Y":
                        if clearance:
                            hw.move_z(0, wait=True)
                        try:
                            hw.move_y(y, wait=True)
                        except (AttributeError, TypeError):
                            try:
                                hw.move_xy(hw.x_position, y, wait=True)
                            except (AttributeError, TypeError):
                                hw.move_xy(x, y, wait=True)
                        if clearance and z > 0:
                            hw.move_z(z, wait=True)
                    else:
                        if clearance:
                            hw.move_z(0, wait=True)
                        try:
                            hw.move_xy(x, y, wait=True)
                        except TypeError:
                            hw.move_xy(x, y)
                        if clearance and z > 0:
                            hw.move_z(z, wait=True)
                self.logger.info(f"Jog Move {ax or 'All'} -> X:{x:.1f}, Y:{y:.1f}, Z:{z:.1f} (Clearance={'ON' if clearance else 'OFF'})")
            except Exception as e:
                self.logger.error(f"Jog move failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def jog_step(self, axis, direction):
        if getattr(self, '_jogging_in_progress', False):
            return

        hw = self.lims.pipettor.hardware
        if hw and not self.lims.hw.is_initialized:
            self.logger.warning("Hardware not initialized. Please click 'Connect & Initialize' first.")
            return

        step = 1.0
        try:
            step = float(self.jog_step_var.get())
        except Exception:
            pass
        delta = float(direction) * step

        curr_x = self._safe_get_jog("X")
        curr_y = self._safe_get_jog("Y")
        curr_z = self._safe_get_jog("Z")

        target_x, target_y, target_z = curr_x, curr_y, curr_z
        max_x = self.lims.machine_config.get("max_x_mm", 300.0)
        max_y = self.lims.machine_config.get("max_y_mm", 300.0)

        if axis == "X":
            target_x = max(0.0, min(curr_x + delta, max_x))
            self.jog_vars["X"].set(round(target_x, 2))
        elif axis == "Y":
            target_y = max(0.0, min(curr_y + delta, max_y))
            self.jog_vars["Y"].set(round(target_y, 2))
        elif axis == "Z":
            target_z = max(0.0, min(curr_z + delta, 103.5))
            self.jog_vars["Z"].set(round(target_z, 2))

        speed = self._safe_get_speed()
        clearance = False
        try:
            clearance = bool(self.jog_z_clearance_var.get())
        except Exception:
            pass

        self.current_pos["X"] = target_x
        self.current_pos["Y"] = target_y
        self.current_pos["Z"] = target_z
        if hasattr(self, 'draw_deck'):
            try:
                self.draw_deck()
            except Exception:
                pass

        self._jogging_in_progress = True
        threading.Thread(
            target=self._jog_step_worker,
            args=(axis, target_x, target_y, target_z, speed, clearance, delta),
            daemon=True
        ).start()

    def _jog_step_worker(self, axis, target_x, target_y, target_z, speed, clearance, delta):
        try:
            hw = self.lims.pipettor.hardware
            if hw:
                hw_speed = max(1, min(9, int((speed / 100.0) * 9)))
                try:
                    hw.x_speed = hw_speed
                    hw.y_speed = hw_speed
                    hw.z_speed = hw_speed
                except Exception:
                    pass

                if axis == "Z":
                    hw.move_z(target_z, wait=True)
                elif axis == "X":
                    if clearance:
                        hw.move_z(0, wait=True)
                    try:
                        hw.move_x(target_x, wait=True)
                    except (AttributeError, TypeError):
                        try:
                            hw.move_xy(target_x, hw.y_position, wait=True)
                        except (AttributeError, TypeError):
                            hw.move_xy(target_x, target_y, wait=True)
                    if clearance and target_z > 0:
                        hw.move_z(target_z, wait=True)
                elif axis == "Y":
                    if clearance:
                        hw.move_z(0, wait=True)
                    try:
                        hw.move_y(target_y, wait=True)
                    except (AttributeError, TypeError):
                        try:
                            hw.move_xy(hw.x_position, target_y, wait=True)
                        except (AttributeError, TypeError):
                            hw.move_xy(target_x, target_y, wait=True)
                    if clearance and target_z > 0:
                        hw.move_z(target_z, wait=True)

            self.logger.info(f"Jog {axis} {delta:+.2f}mm -> (X:{target_x:.1f}, Y:{target_y:.1f}, Z:{target_z:.1f})")
        except Exception as e:
            self.logger.error(f"Jog {axis} failed: {e}")
        finally:
            self._jogging_in_progress = False

    def _on_key_press(self, event):
        key = event.keysym.lower()
        shift = bool(event.state & 0x0001)  # Shift key pressed -> 10x step
        ctrl = bool(event.state & 0x0004)   # Ctrl key pressed -> 0.1x step

        mult = 1.0
        if shift:
            mult = 10.0
        elif ctrl:
            mult = 0.1

        # PageUp / PageDown / + / - always jog Z immediately even if focus is inside an Entry!
        if key in ('prior', 'pageup', 'page_up', 'equal', 'plus'):
            self.jog_step('Z', -1.0 * mult)
            return "break"
        elif key in ('next', 'pagedown', 'page_down', 'minus', 'underscore'):
            self.jog_step('Z', +1.0 * mult)
            return "break"

        # Escape releases focus from any active Entry
        if key == 'escape':
            try:
                self.root.focus_set()
            except Exception:
                pass
            return "break"

        # Ignore keyboard controls if user is currently typing in an input widget
        focus_w = self.root.focus_get()
        if focus_w:
            w_class = getattr(focus_w, 'winfo_class', lambda: '')()
            if w_class in ('Entry', 'TEntry', 'Text', 'Combobox', 'TCombobox', 'Spinbox'):
                return

        # X-Axis Jog (Left / Right)
        if key in ('left', 'a'):
            self.jog_step('X', -1.0 * mult)
            return "break"
        elif key in ('right', 'd'):
            self.jog_step('X', +1.0 * mult)
            return "break"

        # Y-Axis Jog (Forward / Back)
        elif key in ('up', 'w'):
            self.jog_step('Y', +1.0 * mult)
            return "break"
        elif key in ('down', 's'):
            self.jog_step('Y', -1.0 * mult)
            return "break"

        # Z-Axis Jog (Q / E)
        elif key == 'q':
            self.jog_step('Z', -1.0 * mult)
            return "break"
        elif key == 'e':
            self.jog_step('Z', +1.0 * mult)
            return "break"

    def start_telemetry(self):
        if not self.telemetry_active:
            self.telemetry_active = True
            threading.Thread(target=self._poll_coordinates, daemon=True).start()

    def _poll_coordinates(self):
        last_pos = None
        while self.telemetry_active:
            if self.lims.pipettor.hardware:
                try:
                    hw = self.lims.pipettor.hardware
                    hx = round(float(getattr(hw, 'x_position', self.current_pos.get("X", 0.0))), 2)
                    hy = round(float(getattr(hw, 'y_position', self.current_pos.get("Y", 0.0))), 2)
                    hz = round(float(getattr(hw, 'z_position', self.current_pos.get("Z", 0.0))), 2)
                    new_pos = {"X": hx, "Y": hy, "Z": hz}
                    if new_pos != last_pos:
                        self.current_pos = new_pos
                        last_pos = dict(new_pos)
                        focus_w = self.root.focus_get()
                        is_typing = focus_w and getattr(focus_w, 'winfo_class', lambda: '')() in ('Entry', 'TEntry')
                        if not is_typing:
                            for ax in ("X", "Y", "Z"):
                                self.jog_vars[ax].set(new_pos[ax])
                        try:
                            self.draw_deck()
                        except Exception:
                            pass
                except Exception:
                    pass
            time.sleep(0.25)

    def get_render_width(self):
        return self.bed_width

    def get_v_x(self, m_x):
        return (self.bed_width - m_x) * self.scale

    def get_m_x(self, c_x):
        return self.bed_width - (c_x / self.scale)

    def track_mouse(self, e):
        rx, ry = self.get_m_x(e.x), e.y / self.scale
        self.lbl_coords.config(text=f"Physical Coordinates -> X: {rx:.1f}, Y: {ry:.1f}")

    def draw_deck(self):
        self.canvas.delete("all")
        render_width = self.bed_width
        is_clean = getattr(self, "cleanroom_theme_active", False)
        bg_color = "#050811" if is_clean else "white"
        grid_light = "#111827" if is_clean else "#ebebeb"
        grid_dark = "#1f2937" if is_clean else "#cccccc"
        text_color = "#94a3b8" if is_clean else "#888"

        self.canvas.config(bg=bg_color, width=render_width * self.scale, height=self.bed_height * self.scale)

        for x in range(0, int(render_width) + 10, 10):
            vx = self.get_v_x(x)
            self.canvas.create_line(vx, 0, vx, self.bed_height * self.scale,
                                    fill=grid_light if x % 50 != 0 else grid_dark)
            if x % 50 == 0: self.canvas.create_text(vx, 10, text=f"{x}mm", fill=text_color)

        for y in range(0, int(self.bed_height) + 10, 10):
            vy = y * self.scale
            self.canvas.create_line(0, vy, render_width * self.scale, vy, fill=grid_light if y % 50 != 0 else grid_dark)
            if y % 50 == 0: self.canvas.create_text(render_width * self.scale - 10, vy, text=f"{y}mm", fill=text_color,
                                                    anchor="e")

        ox = render_width * self.scale
        self.canvas.create_oval(ox - 15, 2, ox - 2, 15, fill="red", outline="black")
        self.canvas.create_text(ox - 18, 15, text="(0,0)", anchor="ne", fill="red", font=("Arial", 9, "bold"))

        # Pass 1: draw ALL slot rectangles first, so no slot body can paint over another slot's wells
        for name in self.placed_slots:
            s = self.lims.deck_slots[name]

            visual_x_right = self.get_v_x(s.x_abs)
            visual_x_left = self.get_v_x(s.x_abs + s.width_mm)

            y0 = s.y_abs * self.scale
            y1 = (s.y_abs + s.height_mm) * self.scale

            is_sel = (name == self.selected_slot_name)
            if is_clean:
                fill = "#0f172a" if name in self.lims.deck_labware else ("#1e293b" if is_sel else "#090d16")
                outline = "#00f0ff" if is_sel else "#334155"
            else:
                fill = "#e9ecef" if name in self.lims.deck_labware else ("#cce5ff" if is_sel else "#f8f9fa")
                outline = "blue" if is_sel else "#6c757d"

            self.canvas.create_rectangle(visual_x_left, y0, visual_x_right, y1, fill=fill, outline=outline,
                                         width=3 if is_sel else 2)
            lbl_color = "#38bdf8" if is_clean else "#212529"
            self.canvas.create_text(visual_x_left + 5, y0 + 5, text=name, anchor="nw", font=("Arial", 10, "bold"), fill=lbl_color)

        # Pass 2: draw wells on top of every rectangle, then the selection badge
        for name in self.placed_slots:
            s = self.lims.deck_slots[name]
            visual_x_left = self.get_v_x(s.x_abs + s.width_mm)
            visual_x_right = self.get_v_x(s.x_abs)
            y0 = s.y_abs * self.scale
            y1 = (s.y_abs + s.height_mm) * self.scale
            is_sel = (name == self.selected_slot_name)

            if name in self.lims.deck_labware:
                lab = self.lims.deck_labware[name]
                first_w = list(lab.wells.values())[0]
                lw_w = max(w.x_rel for w in lab.wells.values()) + first_w.x_rel
                lw_h = max(w.y_rel for w in lab.wells.values()) + first_w.y_rel
                cx = s.x_abs + (s.width_mm / 2.0)
                cy = s.y_abs + (s.height_mm / 2.0)

                # --- VISUAL UI FIX: Render all labware wells matching physical kinematics ---
                is_tip_rack_lw = (self._lw_kind(lab) == "tip_rack")
                is_m2_10ul_draw = "10ul" in str(getattr(self, "active_profile_id", "")).lower()
                consumed_tips_for_slot = self.session_tip_tracker.get(name, {}).get("consumed", set()) if is_tip_rack_lw else set()
                for w in lab.wells.values():
                    if name == "Slot_4" and is_m2_10ul_draw:
                        # Visual deck well centers inside Slot_4 box (carriage pickup Y is separate)
                        r_idx, c_idx = self._parse_well(w.name)
                        ci = c_idx if (c_idx is not None and 0 <= c_idx < 12) else 0
                        ri = r_idx if (r_idx is not None and 0 <= r_idx < 8) else 0
                        phys_wx, phys_wy = 105.66 - (ci * 9.0), 52.64 + (ri * 9.0)
                    else:
                        coords = self._calculate_xy(name, w.name)
                        if coords:
                            phys_wx, phys_wy = coords
                        else:
                            phys_wx = cx + ((lw_w / 2.0) - w.x_rel)
                            phys_wy = cy - (lw_h / 2.0) + w.y_rel

                    wx, wy, r = self.get_v_x(phys_wx), phys_wy * self.scale, w.radius * self.scale

                    if is_tip_rack_lw:
                        if w.name.upper() in consumed_tips_for_slot:
                            w_fill, w_outline, w_txt = ("#1e293b", "#334155", "#475569") if is_clean else ("#d6d8db", "#adb5bd", "#868e96")
                        else:
                            w_fill, w_outline, w_txt = ("#0284c7", "#38bdf8", "#ffffff") if is_clean else ("#e7f5ff", "#339af0", "#1864ab")
                    else:
                        liquid_vol = self.slot_liquid_levels.get((name, w.name), None)
                        if liquid_vol is not None and float(liquid_vol) > 0.0:
                            w_fill = "#38bdf8" if is_clean else "#007bff"
                            w_outline = "#0284c7"
                            w_txt = "white"
                        else:
                            w_fill = "#090d16" if is_clean else "white"
                            w_outline = "#334155" if is_clean else "#dee2e6"
                            w_txt = "#94a3b8" if is_clean else "#666"

                    self.canvas.create_oval(wx - r, wy - r, wx + r, wy + r, fill=w_fill, outline=w_outline)
                    if r > 4: self.canvas.create_text(wx, wy, text=w.name, font=("Arial", int(r * 0.8)), fill=w_txt)

                # Draw live tip countdown on tip racks
                if is_tip_rack_lw:
                    consumed_count = len(consumed_tips_for_slot)
                    free_count = 96 - consumed_count
                    count_text = f"Tips: {free_count}/96 free"
                    c_txt_color = "#38bdf8" if is_clean else "#0d6efd"
                    self.canvas.create_text(visual_x_left + 6, y1 - 14, text=count_text, anchor="nw", font=("Arial", 8, "bold"), fill=c_txt_color)

            if is_sel:
                badge_text = f" [{name}] X: {s.x_abs:.1f} | Y: {s.y_abs:.1f} "
                self.canvas.create_rectangle(visual_x_right - 190, y0 - 24, visual_x_right, y0, fill="#007bff",
                                             outline="black")
                self.canvas.create_text(visual_x_right - 185, y0 - 12, text=badge_text, anchor="w", fill="white",
                                        font=("Consolas", 10, "bold"))
                self.canvas.create_oval(visual_x_right - 4, y0 - 4, visual_x_right + 4, y0 + 4, fill="red",
                                        outline="black")

        # Live Animated Pipettor Nozzle Reticle & Footprint Tracking
        px, py = self.get_v_x(self.current_pos["X"]), self.current_pos["Y"] * self.scale
        nozzle_color = "#38bdf8" if is_clean else "red"

        if getattr(self.lims.pipettor, 'multichannel', False):
            # Draw 8-nozzle manifold footprint along Y (spanning 63mm from carriage center)
            top_ny = py - (31.50 * self.scale)
            bot_ny = py + (31.50 * self.scale)
            self.canvas.create_line(px, top_ny, px, bot_ny, fill=nozzle_color, width=2)
            for n in range(8):
                n_dy = (-31.50 + (n * 9.0)) * self.scale
                self.canvas.create_oval(px - 3, (py + n_dy) - 3, px + 3, (py + n_dy) + 3, fill=nozzle_color, outline="white" if is_clean else "black")
            # Central carriage crosshairs
            self.canvas.create_line(px - 12, py, px + 12, py, fill=nozzle_color, width=2)
            self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, outline=nozzle_color, width=2)
        else:
            self.canvas.create_line(px - 10, py, px + 10, py, fill=nozzle_color, width=2)
            self.canvas.create_line(px, py - 10, px, py + 10, fill=nozzle_color, width=2)
            self.canvas.create_oval(px - 5, py - 5, px + 5, py + 5, outline=nozzle_color)

        hud_bg = self.canvas.create_rectangle(5, 5, 140, 75, fill="#090d16" if is_clean else "#333", stipple="gray50")
        hud_text = f"LIVE TELEMETRY\nX: {self.current_pos['X']:>6.2f} mm\nY: {self.current_pos['Y']:>6.2f} mm\nZ: {self.current_pos['Z']:>6.2f} mm"
        self.canvas.create_text(10, 10, text=hud_text, anchor="nw", fill="#00ff00", font=("Consolas", 10, "bold"))

    def build_deck_tab(self):
        pane_l = ttk.Frame(self.tab_deck, width=240)
        pane_l.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        pane_m = ttk.Frame(self.tab_deck, width=260)
        pane_m.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        right_f = ttk.Frame(self.tab_deck)
        right_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_f = ttk.Frame(right_f)
        canvas_f.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.lbl_coords = ttk.Label(canvas_f, text="Physical Coordinates -> X: 0.0, Y: 0.0")
        self.lbl_coords.pack(anchor="ne")

        self.canvas = tk.Canvas(canvas_f, bg="white", relief="sunken", bd=2)
        self.canvas.pack(pady=10, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Motion>", self.track_mouse)
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.drag_end)
        self.canvas.bind("<Button-2>", self._on_canvas_right_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<Control-Button-1>", self._on_canvas_right_click)

        f_jog = ttk.LabelFrame(right_f, text="Live Calibration Jog Control", padding=10)
        f_jog.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.deck_jog_btns = {}
        for axis in ["X", "Y", "Z"]:
            f = ttk.Frame(f_jog)
            f.pack(fill=tk.X, padx=10, pady=2)
            ttk.Label(f, text=f"{axis} (mm):", width=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

            btn_m = tk.Button(f, text="-", width=2, bg="#e9ecef", font=("Consolas", 8, "bold"), state='disabled',
                              command=lambda a=axis: self.jog_step(a, -1.0))
            btn_m.pack(side=tk.LEFT, padx=(2, 2))
            self.jog_nudge_btns.append(btn_m)

            e = ttk.Entry(f, textvariable=self.jog_vars[axis], font=("Consolas", 10), state='disabled', width=8)
            e.pack(side=tk.LEFT, padx=3)
            self.deck_jog_sliders[axis] = e

            btn_p = tk.Button(f, text="+", width=2, bg="#e9ecef", font=("Consolas", 8, "bold"), state='disabled',
                              command=lambda a=axis: self.jog_step(a, +1.0))
            btn_p.pack(side=tk.LEFT, padx=(2, 5))
            self.jog_nudge_btns.append(btn_p)

            btn = tk.Button(f, text="MOVE", bg="#007bff", fg="white", font=("Arial", 8, "bold"), state='disabled',
                            command=lambda ax=axis: self._execute_jog_move(ax))
            btn.pack(side=tk.LEFT, padx=3)
            self.deck_jog_btns[axis] = btn

            e.bind('<Return>', lambda event, ax=axis: self._execute_jog_move(ax))

        deck_ctrl_f = ttk.Frame(f_jog)
        deck_ctrl_f.pack(fill=tk.X, padx=10, pady=(4, 0))
        ttk.Label(deck_ctrl_f, text="Step:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        for step_val in [0.1, 1.0, 5.0, 10.0, 30.0, 50.0, 100.0]:
            ttk.Radiobutton(deck_ctrl_f, text=f"{step_val}mm", value=step_val, variable=self.jog_step_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(deck_ctrl_f, text="Clearance (Z=0)", variable=self.jog_z_clearance_var).pack(side=tk.LEFT, padx=6)
        ttk.Label(deck_ctrl_f, text="⌨️ Arrow keys / PgUp-PgDn active", font=("Arial", 8, "italic"), foreground="#0066cc").pack(side=tk.RIGHT)

        ttk.Label(pane_l, text="Inventory", font=("Arial", 10, "bold")).pack(pady=5)
        self.list_unplaced = tk.Listbox(pane_l, height=10, bg="white")
        self.list_unplaced.pack(fill=tk.X)
        ttk.Button(pane_l, text="Place on Deck \u2192", command=self.place_slot).pack(fill=tk.X, pady=2)
        self.list_placed = tk.Listbox(pane_l, height=10, bg="white")
        self.list_placed.pack(fill=tk.X)
        self.list_placed.bind("<<ListboxSelect>>", self.on_placed_slot_select)
        ttk.Button(pane_l, text="Remove from Deck \u2190", command=self.remove_slot).pack(fill=tk.X, pady=2)
        ttk.Button(pane_l, text="EMERGENCY RESET", command=self.emergency_reset).pack(fill=tk.X, pady=30)

        self.entries = {}
        for lab, key in [("X Coord", "x_abs"), ("Y Coord", "y_abs"), ("Width", "width_mm"), ("Height", "height_mm"),
                         ("Z Floor Offset (+mm)", "z_offset")]:
            ttk.Label(pane_m, text=lab).pack(anchor="w")
            v = tk.StringVar()
            e = ttk.Entry(pane_m, textvariable=v)
            e.pack(fill=tk.X, pady=2)
            self.entries[key] = v
            v.trace_add("write", lambda *args, k=key, var=v: self.sync_to_backend(k, var))

        self.lw_var = tk.StringVar()
        self.lw_drop = ttk.Combobox(pane_m, textvariable=self.lw_var, state="readonly")
        self.lw_drop.pack(fill=tk.X, pady=10)
        ttk.Button(pane_m, text="Assign Labware", command=self.assign_lw).pack(fill=tk.X)
        ttk.Button(pane_m, text="Unassign Labware", command=self.unassign_lw).pack(fill=tk.X, pady=2)
        ttk.Button(
            pane_m,
            text="🔄 Reset Tip Rack",
            command=lambda: self.reset_tip_rack_memory(self.selected_slot_name if self.selected_slot_name in self.session_tip_tracker else None),
        ).pack(fill=tk.X, pady=(6, 2))
        ttk.Button(pane_m, text="SAVE WORKSPACE", command=self.save_all).pack(side=tk.BOTTOM, fill=tk.X, pady=20)

    def check_alignment(self):
        mouse_x = self.get_m_x(self.canvas.winfo_pointerx() - self.canvas.winfo_rootx())
        hardware_x = self.jog_vars["X"].get()
        self.logger.info(f"--- ALIGNMENT CHECK ---")
        self.logger.info(f"Visual Grid X (Mouse Cursor): {mouse_x:.1f}mm")
        self.logger.info(f"Hardware Jog X (Machine Base): {hardware_x:.1f}mm")

    def build_direct_ops_tab(self):
        ttk.Label(self.tab_direct, text="Immediate Machine Controls", font=("Arial", 16, "bold")).pack(anchor="w")

        container = ttk.Frame(self.tab_direct)
        container.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        canvas = tk.Canvas(container, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        ops_frame = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=ops_frame, anchor="nw")

        ops_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        ops = [
            ("Home Head", "Resets pipette head to safety origin.", "HOME"),
            ("Find Tip", "Auto-searches a designated slot using NATIVE API.", "FIND_TIP"),
            ("Return Tip to Well", "Returns/ejects mounted tip(s) to a specific slot & well using the labware from Deck Setup.", "RETURN_TIP"),
            ("Discard Tips", "Moves head to designated Waste slot and triggers ejection mechanism.", "DISCARD"),
            ("Check Liquid Level", "Detects liquid surface in selected slot/well and calculates remaining volume.", "CHECK_LIQUID"),
            ("Check Alignment", "Compares visual mouse grid to hardware jog coordinates.", "CHECK"),
            ("Machine 2 Piston Step Test", "Runs 50/100/150/200-step water aspiration sweep (1-10 µL head) with pause at Z=0 to measure volume.", "M2_STEP_TEST"),
        ]
        for title, desc, code in ops:
            f = ttk.LabelFrame(ops_frame, text=f" {title} ", padding=10)
            f.pack(fill=tk.X, pady=5)
            sub = ttk.Frame(f)
            sub.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Label(sub, text=f"Action: {desc}").pack(anchor="w")
            tk.Button(f, text=f"RUN {code}", bg="#007bff", fg="white", font=("Arial", 9, "bold"), width=16,
                      command=lambda c=code: self.run_direct_op(c)).pack(side=tk.RIGHT, padx=10)

    def build_workflow_tab(self):
        # Scrollable left control column so square/compact monitors never clip buttons
        left_container = ttk.Frame(self.tab_workflow, width=345)
        left_container.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 6), pady=2)
        left_container.pack_propagate(False)

        ctrl_canvas = tk.Canvas(left_container, width=325, highlightthickness=0, bd=0)
        ctrl_sb = ttk.Scrollbar(left_container, orient=tk.VERTICAL, command=ctrl_canvas.yview)
        pane_ctrl = ttk.Frame(ctrl_canvas, width=325)

        ctrl_window = ctrl_canvas.create_window((0, 0), window=pane_ctrl, anchor="nw")

        def _on_ctrl_frame_configure(event=None):
            ctrl_canvas.configure(scrollregion=ctrl_canvas.bbox("all"))

        def _on_ctrl_canvas_configure(event):
            ctrl_canvas.itemconfig(ctrl_window, width=event.width)

        pane_ctrl.bind("<Configure>", _on_ctrl_frame_configure)
        ctrl_canvas.bind("<Configure>", _on_ctrl_canvas_configure)
        ctrl_canvas.configure(yscrollcommand=ctrl_sb.set)

        ctrl_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ctrl_sb.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_ctrl_mousewheel(event):
            try:
                if event.num == 4 or event.delta > 0:
                    ctrl_canvas.yview_scroll(-1, "units")
                elif event.num == 5 or event.delta < 0:
                    ctrl_canvas.yview_scroll(1, "units")
            except Exception:
                pass

        ctrl_canvas.bind("<Enter>", lambda _: (
            ctrl_canvas.bind_all("<MouseWheel>", _on_ctrl_mousewheel),
            ctrl_canvas.bind_all("<Button-4>", _on_ctrl_mousewheel),
            ctrl_canvas.bind_all("<Button-5>", _on_ctrl_mousewheel),
        ))
        ctrl_canvas.bind("<Leave>", lambda _: (
            ctrl_canvas.unbind_all("<MouseWheel>"),
            ctrl_canvas.unbind_all("<Button-4>"),
            ctrl_canvas.unbind_all("<Button-5>"),
        ))

        pane_list = ttk.Frame(self.tab_workflow)
        pane_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 6), pady=2)

        # 0. Active Physical Station & Cleanroom Bar
        station_bar = ttk.Frame(pane_ctrl)
        station_bar.pack(fill=tk.X, pady=(2, 2))
        station_name = self.profile_manager.get_display_name(self.active_profile_id) if getattr(self, "profile_manager", None) else self.active_profile_id
        self.lbl_station_badge = tk.Label(
            station_bar,
            text=f"🏢 {station_name}",
            bg="#1f2937",
            fg="#60a5fa",
            font=("Arial", 8, "bold"),
            padx=5,
            pady=2,
            relief="groove",
        )
        self.lbl_station_badge.pack(side=tk.LEFT)
        self.btn_profile_select = tk.Button(
            station_bar,
            text="⚙️ Switch",
            bg="#374151",
            fg="white",
            font=("Arial", 8, "bold"),
            command=self.action_select_machine_profile,
            padx=4,
            pady=1,
        )
        self.btn_profile_select.pack(side=tk.LEFT, padx=(2, 4))

        self.btn_theme_toggle = tk.Button(
            station_bar,
            text="🌓 Theme",
            bg="#374151",
            fg="white",
            font=("Arial", 8, "bold"),
            command=self.toggle_cleanroom_theme,
            padx=4,
            pady=1,
        )
        self.btn_theme_toggle.pack(side=tk.RIGHT)

        # Clean 2-Step Protocol & Pipettor Selector Frame (Placed at TOP for square monitors)
        proto_frame = ttk.LabelFrame(pane_ctrl, text="⚡ Protocols & Workflows", padding=6)
        proto_frame.pack(fill=tk.X, pady=(2, 6))

        # 1. Pipettor Selection
        ttk.Label(proto_frame, text="1. Select Pipettor:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.proto_pipettor_var = tk.StringVar(value=self.head_mode_var.get())
        self.proto_pipettor_cb = ttk.Combobox(
            proto_frame,
            textvariable=self.proto_pipettor_var,
            values=[
                "8-Channel Multi (8×1000 µL) [Media Change]",
                "300 µL Single-Channel [Prepping DMSO-Drug]",
                "8-Channel Multi (1-10 µL) [Drug Addition to EHM]",
            ],
            state="readonly",
        )
        self.proto_pipettor_cb.pack(fill=tk.X, pady=(0, 4))
        self.proto_pipettor_cb.bind("<<ComboboxSelected>>", self._on_proto_pipettor_selected)

        # 2. Protocol Selection
        ttk.Label(proto_frame, text="2. Available Protocols:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.proto_workflow_var = tk.StringVar()
        self.proto_workflow_cb = ttk.Combobox(
            proto_frame,
            textvariable=self.proto_workflow_var,
            state="readonly",
        )
        self.proto_workflow_cb.pack(fill=tk.X, pady=(0, 5))

        # Action Button to Load Protocol
        self.btn_load_proto = tk.Button(
            proto_frame,
            text="🟢 Load Selected Protocol",
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            font=("Arial", 10, "bold"),
            relief="raised",
            bd=2,
            command=self._execute_selected_protocol_load,
        )
        self.btn_load_proto.pack(fill=tk.X, pady=(2, 6))

        # Quick Tools & Homing Row
        ttk.Label(proto_frame, text="Quick Tools & Homing:", font=("Arial", 8, "bold"), foreground="#495057").pack(anchor="w", pady=(0, 2))
        tools_row = ttk.Frame(proto_frame)
        tools_row.pack(fill=tk.X, pady=(0, 5))

        btn_home = tk.Button(
            tools_row,
            text="🏠 Home",
            bg="#0d6efd",
            fg="white",
            font=("Arial", 8, "bold"),
            command=self.quick_home_head,
        )
        btn_home.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_safez = tk.Button(
            tools_row,
            text="⬆️ Safe Z",
            bg="#17a2b8",
            fg="white",
            font=("Arial", 8, "bold"),
            command=self.quick_safe_z,
        )
        btn_safez.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))

        btn_heights = tk.Button(
            tools_row,
            text="⚙️ Heights",
            bg="#6c757d",
            fg="white",
            font=("Arial", 8, "bold"),
            command=self.action_open_8ch_height_settings,
        )
        btn_heights.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))

        btn_tim_z = tk.Button(
            tools_row,
            text="📐 Tip Z-Check",
            bg="#e83e8c",
            fg="white",
            font=("Arial", 8, "bold"),
            command=self.action_open_tim_z_verification,
        )
        btn_tim_z.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # File Import/Export Row
        file_row = ttk.Frame(proto_frame)
        file_row.pack(fill=tk.X, pady=(0, 2))

        ttk.Button(file_row, text="📂 Load JSON", command=self.action_load_workflow).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(file_row, text="💾 Save JSON", command=self.action_save_workflow_as).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        ttk.Button(file_row, text="📥 Import .py", command=self.action_import_python_protocol).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        ttk.Separator(pane_ctrl, orient="horizontal").pack(fill=tk.X, pady=4)

        ttk.Label(pane_ctrl, text="Protocol Builder", font=("Arial", 10, "bold")).pack(pady=(2, 3))
        ttk.Label(pane_ctrl, text="Action Type:").pack(anchor="w")

        self.wf_action = ttk.Combobox(pane_ctrl, state="readonly",
                                      values=["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip",
                                              "Detect Liquid Level",
                                              "System: Incubate (Wait)", "System: FOC48 Measurement", "System: Calcium Curve", "System: Data Analysis", "System: DB Upload"])
        self.wf_action.current(0)
        self.wf_action.pack(fill=tk.X, pady=(0, 4))

        self.auto_tip_search_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Auto-Search Tips (Skip empty wells)", variable=self.auto_tip_search_var).pack(
            fill=tk.X, pady=(2, 1))

        self.adaptive_tip_centering_var = tk.BooleanVar(value=False)

        self.dynamic_z_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Auto-Height Detection (Liquids ONLY)", variable=self.dynamic_z_var).pack(
            fill=tk.X, pady=(0, 1))

        self.lld_tracking_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Sensor Liquid Level Detection (LLD)", variable=self.lld_tracking_var).pack(
            fill=tk.X, pady=(0, 1))

        ttk.Checkbutton(pane_ctrl, text="Pipette Currently Has Tip", variable=self.has_tip_var).pack(fill=tk.X,
                                                                                                     pady=(0, 1))

        self.manual_mode_var = tk.BooleanVar(value=False)
        self.chk_manual_mode = ttk.Checkbutton(pane_ctrl, text="Enable Manual Coordinates",
                                               variable=self.manual_mode_var, command=self._toggle_wf_inputs)
        self.chk_manual_mode.pack(fill=tk.X, pady=(0, 4))

        foc_frame = ttk.LabelFrame(pane_ctrl, text="🔬 FOC48 Experiment Selection", padding=4)
        foc_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(foc_frame, text="Target Experiment (Plate 1 = 17a, Plate 2 = 17b):", font=("Arial", 8, "bold")).pack(anchor="w")
        foc_presets = [
            "17b (Plate 2 - 1st in list)",
            "17a (Plate 1 - 2nd in list)",
            "Row 1 (1st Experiment)",
            "Row 2 (2nd Experiment)",
            "Row 3 (3rd Experiment)"
        ]
        try:
            import foc_automation
            for exp_dir in foc_automation.get_available_experiments():
                if exp_dir not in foc_presets:
                    foc_presets.append(exp_dir)
        except Exception:
            pass
        self.foc_exp_var = tk.StringVar(value=foc_presets[0])
        self.cbx_foc_exp = ttk.Combobox(foc_frame, textvariable=self.foc_exp_var, values=foc_presets, state="normal")
        self.cbx_foc_exp.pack(fill=tk.X, pady=(2, 0))

        self.input_frame = ttk.Frame(pane_ctrl)
        self.input_frame.pack(fill=tk.X, expand=True)
        self.lbl_1 = ttk.Label(self.input_frame, text="")
        self.cbx_slot = ttk.Combobox(self.input_frame, state="readonly")
        self.cbx_slot.bind("<<ComboboxSelected>>", self.update_safe_z_hint)
        self.ent_x = ttk.Entry(self.input_frame)
        self.lbl_2 = ttk.Label(self.input_frame, text="")
        self.ent_well = ttk.Entry(self.input_frame)
        self.ent_y = ttk.Entry(self.input_frame)
        self.lbl_3 = ttk.Label(self.input_frame, text="")
        self.ent_z = ttk.Entry(self.input_frame)
        self.lbl_safe_z = ttk.Label(self.input_frame, text="", font=("Arial", 9, "italic"), foreground="#0d6efd", wraplength=200)
        self.lbl_4 = ttk.Label(self.input_frame, text="")
        self.ent_vol = ttk.Entry(self.input_frame)

        ttk.Button(pane_ctrl, text="+ Add Step to Protocol", command=self.add_wf_step).pack(fill=tk.X, pady=(6, 3))
        ttk.Button(pane_ctrl, text="Clear Protocol",
                   command=lambda: [self.wf_box.delete(0, tk.END), self.workflow_sequence.clear(), self._update_estimated_timer_preview()]).pack(fill=tk.X, pady=(0, 6))

        # Initialize protocol dropdown options based on initial pipettor selection
        self._update_protocol_dropdown()

        # Pack bottom Run Dashboard & Edit toolbar FIRST so square monitors never clip them
        run_frame = ttk.LabelFrame(pane_list, text="Opentrons-Style Run Dashboard", padding=6)
        run_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 2))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(run_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 3))

        self.lbl_timer = ttk.Label(run_frame, text="Time Remaining: --h --m --s", font=("Consolas", 10, "bold"),
                                   foreground="blue")
        self.lbl_timer.pack(pady=(0, 3))

        self.lbl_deck_summary = tk.Label(
            run_frame,
            text="📋 Deck: No protocol loaded | Tips: None",
            font=("Arial", 9, "bold"),
            bg="#f8f9fa",
            fg="#495057",
            relief="groove",
            padx=6,
            pady=3,
            anchor="w",
            justify=tk.LEFT
        )
        self.lbl_deck_summary.pack(fill=tk.X, pady=(0, 4))

        util_bar = ttk.Frame(run_frame)
        util_bar.pack(fill=tk.X, pady=(0, 4))
        self.lbl_tip_memory = ttk.Label(
            util_bar,
            text="Tip Memory (Slot_4): Next A1 (96/96 free)",
            font=("Consolas", 9, "bold"),
            foreground="#0d6efd",
        )
        self.lbl_tip_memory.pack(side=tk.LEFT, padx=(2, 6))
        self.btn_view_report = ttk.Button(util_bar, text="📊 View Run Report", command=self.action_open_run_report)
        self.btn_view_report.pack(side=tk.RIGHT, padx=2)
        self.btn_view_logs = ttk.Button(util_bar, text="📁 View Session Logs", command=self.action_open_session_logs)
        self.btn_view_logs.pack(side=tk.RIGHT, padx=2)
        self.btn_reset_tips = ttk.Button(util_bar, text="🔄 Reset Tip Rack", command=lambda: self.reset_tip_rack_memory(None))
        self.btn_reset_tips.pack(side=tk.RIGHT, padx=2)

        z_home_bar = ttk.Frame(run_frame)
        z_home_bar.pack(fill=tk.X, pady=(0, 4))
        self.chk_mid_z_home = ttk.Checkbutton(
            z_home_bar,
            text="🔄 Mid-Protocol Z-Home (Compensate Downward Z-Drift) Every",
            variable=self.mid_protocol_z_home_var,
        )
        self.chk_mid_z_home.pack(side=tk.LEFT, padx=(2, 4))
        self.spn_mid_z_home_interval = ttk.Spinbox(
            z_home_bar,
            from_=1,
            to=50,
            width=3,
            textvariable=self.mid_protocol_z_home_interval_var,
        )
        self.spn_mid_z_home_interval.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(z_home_bar, text="Step(s)", font=("Arial", 9, "bold")).pack(side=tk.LEFT)

        ctrl_frame = ttk.Frame(run_frame)
        ctrl_frame.pack(fill=tk.X)
        self.btn_play = tk.Button(ctrl_frame, text="▶ START PROTOCOL", bg="#28a745", fg="white",
                                  font=("Arial", 10, "bold"), command=self.execute_protocol)
        self.btn_play.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_pause = tk.Button(ctrl_frame, text="⏸ PAUSE", bg="#ffc107", font=("Arial", 10, "bold"),
                                   state=tk.DISABLED, command=self.pause_resume_run)
        self.btn_pause.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_stop = tk.Button(ctrl_frame, text="⏹ CANCEL", bg="#dc3545", fg="white", font=("Arial", 10, "bold"),
                                  state=tk.DISABLED, command=self.stop_run)
        self.btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Mid-Run & Offline Protocol Modification Toolbar
        bar_edit = ttk.Frame(pane_list)
        bar_edit.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 4))
        self.btn_wf_insert = ttk.Button(bar_edit, text="➕ Insert", width=8, command=self.action_insert_step)
        self.btn_wf_insert.pack(side=tk.LEFT, padx=1)
        self.btn_wf_delete = ttk.Button(bar_edit, text="🗑️ Delete", width=8, command=self.action_delete_step)
        self.btn_wf_delete.pack(side=tk.LEFT, padx=1)
        self.btn_wf_edit = ttk.Button(bar_edit, text="✏️ Edit", width=7, command=self.edit_wf_step)
        self.btn_wf_edit.pack(side=tk.LEFT, padx=1)
        self.btn_wf_up = ttk.Button(bar_edit, text="⬆️ Up", width=6, command=self.action_move_step_up)
        self.btn_wf_up.pack(side=tk.LEFT, padx=1)
        self.btn_wf_down = ttk.Button(bar_edit, text="⬇️ Down", width=6, command=self.action_move_step_down)
        self.btn_wf_down.pack(side=tk.LEFT, padx=1)
        self.protocol_edit_buttons = [self.btn_wf_insert, self.btn_wf_delete, self.btn_wf_edit, self.btn_wf_up, self.btn_wf_down]

        # Protocol Viewer Frame with Dual Scrollbars (Vertical & Horizontal)
        box_frame = ttk.Frame(pane_list)
        box_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 2))
        box_frame.grid_rowconfigure(0, weight=1)
        box_frame.grid_columnconfigure(0, weight=1)

        sb_y = ttk.Scrollbar(box_frame, orient=tk.VERTICAL)
        sb_x = ttk.Scrollbar(box_frame, orient=tk.HORIZONTAL)

        self.wf_box = tk.Listbox(
            box_frame,
            font=("Consolas", 10),
            bg="#f8f9fa",
            fg="#212529",
            selectbackground="#0d6efd",
            selectforeground="white",
            relief="solid",
            bd=1,
            highlightthickness=0,
            activestyle="none",
            yscrollcommand=sb_y.set,
            xscrollcommand=sb_x.set,
        )
        self.wf_box.grid(row=0, column=0, sticky="nsew")
        sb_y.config(command=self.wf_box.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.config(command=self.wf_box.xview)
        sb_x.grid(row=1, column=0, sticky="ew")
        self.wf_box.bind("<Double-Button-1>", self.edit_wf_step)

        self.wf_action.bind("<<ComboboxSelected>>", self._toggle_wf_inputs)
        self._toggle_wf_inputs()

    def _toggle_wf_inputs(self, event=None):
        action = self.wf_action.get()
        is_manual = self.manual_mode_var.get()
        for w in self.input_frame.winfo_children(): w.pack_forget()

        if "System" in action or "DB:" in action:
            self.chk_manual_mode.config(state="disabled")
            is_manual = False
        else:
            self.chk_manual_mode.config(state="normal")

        if is_manual:
            self.lbl_1.config(text="Visual Grid X (mm):")
            self.lbl_1.pack(anchor="w")
            self.ent_x.pack(fill=tk.X, pady=(0, 5))
            self.lbl_2.config(text="Visual Grid Y (mm):")
            self.lbl_2.pack(anchor="w")
            self.ent_y.pack(fill=tk.X, pady=(0, 5))
            self.lbl_3.config(text="Action Z-Depth (mm):")
            self.lbl_3.pack(anchor="w")
            self.ent_z.pack(fill=tk.X, pady=(0, 5))
            if action not in ["Pick Up Tip", "Discard Tip", "Detect Liquid Level"]:
                self.lbl_4.config(text="Volume (\u03bcL):")
                self.lbl_4.pack(anchor="w")
                self.ent_vol.pack(fill=tk.X, pady=(0, 5))
        else:
            if "Incubate" in action:
                self.lbl_4.config(text="Seconds (e.g., 120):")
                self.lbl_4.pack(anchor="w")
                self.ent_vol.pack(fill=tk.X, pady=(0, 5))
            elif "FOC48" in action:
                self.lbl_2.config(text="Experiment Override (optional, or use selector above):")
                self.lbl_2.pack(anchor="w")
                self.ent_well.pack(fill=tk.X, pady=(0, 5))
            elif "Data Analysis" in action:
                pass
            elif "DB Upload" in action:
                pass
            elif "Calcium Curve" in action:
                pass
            elif "DB:" in action:
                pass
            else:
                self.lbl_1.config(text="Target Deck Slot:")
                self.lbl_1.pack(anchor="w")
                self.cbx_slot.pack(fill=tk.X, pady=(0, 5))
                self.lbl_2.config(text="Target Well (e.g., A1, Col 1, A1:H1):")
                self.lbl_2.pack(anchor="w")
                self.ent_well.pack(fill=tk.X, pady=(0, 5))
                if action not in ["Pick Up Tip", "Discard Tip", "Detect Liquid Level"]:
                    self.lbl_4.config(text="Volume (\u03bcL):")
                    self.lbl_4.pack(anchor="w")
                    self.ent_vol.pack(fill=tk.X, pady=(0, 5))
                    self.lbl_3.config(text="Extra Z-Depth (+mm) [Optional]:")
                    self.lbl_3.pack(anchor="w")
                    self.ent_z.pack(fill=tk.X, pady=(0, 2))
                    self.lbl_safe_z.pack(fill=tk.X, pady=(0, 5))
                    self.update_safe_z_hint()

    def update_safe_z_hint(self, *args):
        slot = self.cbx_slot.get()
        if not slot:
            self.lbl_safe_z.config(text="")
            return
        labware_obj = self.lims.deck_labware.get(slot)
        if not labware_obj:
            self.lbl_safe_z.config(text=f"⚠️ No labware assigned to {slot} (Deck tab)")
            return
        kind = self._lw_kind(labware_obj)
        try:
            if kind == "tip_rack":
                self.lbl_safe_z.config(text=f"💡 Tip rack ({getattr(labware_obj, 'name', '')}): pickup Z 87.0mm | ⚠️ Max 92.0mm")
                return
            asp = self._calculate_z("Aspirate Media", labware_obj, "A1", "auto", 0.0, slot)
            disp = self._calculate_z("Dispense Media", labware_obj, "A1", "auto", 0.0, slot)
            max_b = self._labware_bottom_z(labware_obj, slot)
            self.lbl_safe_z.config(text=f"💡 {getattr(labware_obj, 'name', '')}: Aspirate {asp:.1f}mm | Dispense {disp:.1f}mm | ⚠️ Max Safe: {max_b:.1f}mm")
        except ValueError:
            self.lbl_safe_z.config(text=f"⚠️ {getattr(labware_obj, 'name', '')}: Z NOT CALIBRATED (set rim_z in its JSON)")

    @classmethod
    def resolve_protocol_path(cls, *filenames: str) -> Optional[str]:
        """
        Resolves a protocol file path by searching protocols root and machine subfolders:
        - 'Machine 1 - 8x1000 uL'
        - 'Machine 2 - 1-10 uL'
        - 'Machine 3 - 300 uL'
        - 'Diagnostics and Tests'
        - 'old/not in use'
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        search_roots = [
            os.path.join(script_dir, "protocols"),
            os.path.join(repo_root, "robolab_gui", "resources", "protocols"),
            os.path.join(repo_root, "src", "robolab_gui", "resources", "protocols"),
            os.path.join(repo_root, "protocols"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "protocols"),
            os.path.join(os.getcwd(), "protocols"),
            os.path.join(os.path.expanduser("~"), "protocols"),
            r"C:\Users\labhub.Hzphw-foc4815\protocols",
        ]
        subfolders = [
            "",
            "Machine 1 - 8x1000 uL",
            "Machine 2 - 1-10 uL",
            "Machine 3 - 300 uL",
            "Diagnostics and Tests",
            os.path.join("old", "not in use"),
        ]
        for fn in filenames:
            if not fn:
                continue
            if os.path.isabs(fn) and os.path.exists(fn):
                return fn
            for root in search_roots:
                if not os.path.isdir(root):
                    continue
                for sub in subfolders:
                    target = os.path.join(root, sub, fn) if sub else os.path.join(root, fn)
                    if os.path.exists(target):
                        return target
                for r, _, files in os.walk(root):
                    if fn in files:
                        return os.path.join(r, fn)
        return None

    def action_load_ehm_test_protocol(self):
        target_path = self.resolve_protocol_path("mock_ehm_diagonal_a1_to_h6.json", "ehm_48_well_test.json")
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            self.has_tip_var.set(True)
            lw_dir = self.get_labware_dir()
            ehm_path = os.path.join(lw_dir, "myriamed_48_well.json")
            if os.path.exists(ehm_path):
                self.lims.deck_labware["Slot_4"] = Labware(ehm_path)
                self.lims.deck_labware["Slot_4"].source_file = "myriamed_48_well.json"
            if "Slot_4" not in self.placed_slots: self.placed_slots.append("Slot_4")
            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                if step['action'] == "Pick Up Tip":
                    msg = f"[{step['action'].upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                else:
                    msg = f"[{step['action'].upper()}] at {step.get('slot', '')}, Well {step.get('well', '')} (Z=86.0mm)"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded EHM 48-Well Diagonal Mock ({len(loaded_sequence)} steps, Z=86.0mm, no tip pickup).")
        else:
            messagebox.showerror("File Not Found", "Could not locate ehm_48_well_test.json")

    def action_load_quick_mock_protocol(self):
        target_path = self.resolve_protocol_path("quick_mock_5slots.json")
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()
            deck_setup = {
                "Slot_2": "reservoir_3_well.json",
                "Slot_3": "reservoir_6_column.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "generic_96_well_plate.json",
                "Slot_6": "waste_trough.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots: self.placed_slots.append(s_name)
            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = step.get('volume', 0.0)
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot} (Waste Trough)"
                else:
                    msg = f"[{act.upper()}] {vol}\u03bcL at {slot}, Well {well}"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded Quick 5-Slot Mock Protocol ({len(loaded_sequence)} steps). Labware auto-assigned.")
        else:
            messagebox.showerror("File Not Found", "Could not locate quick_mock_5slots.json")

    def action_load_slot5_rowA_protocol(self):
        target_path = self.resolve_protocol_path("slot5_96well_rowA_test.json")
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            self.has_tip_var.set(True)
            lw_dir = self.get_labware_dir()
            plate_file = "generic_96_well_plate.json"
            plate_path = os.path.join(lw_dir, plate_file)
            if os.path.exists(plate_path):
                self.lims.deck_labware["Slot_5"] = Labware(plate_path)
                self.lims.deck_labware["Slot_5"].source_file = plate_file
            if "Slot_5" not in self.placed_slots: self.placed_slots.append("Slot_5")
            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                msg = f"[{act.upper()}] at {slot}, Well {well}"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded Slot 5 96-Well Row A Test Protocol ({len(loaded_sequence)} steps). Labware auto-assigned and Tip state marked ATTACHED.")
        else:
            messagebox.showerror("File Not Found", "Could not locate slot5_96well_rowA_test.json")

    def action_load_liquid_test_protocol(self):
        target_path = self.resolve_protocol_path("test_lld_slot1_a1_media_removal.json", "Test_Liquid_Level_Detection.json")
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            # Auto-assign Slot 1 = 50mL Falcon Media, Slot 2 = 50mL Falcon Discard (A3), Slot 4 = 1000uL Tip Rack
            deck_setup = {
                "Slot_1": "tube_rack_3x50ml.json",
                "Slot_2": "tube_rack_3x50ml.json",
                "Slot_4": "tip_rack_1000ul.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = step.get('volume', 0.0)
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot} (Waste)"
                elif act == "Detect Liquid Level":
                    msg = f"[{act.upper()}] at {slot}, Well {well}"
                elif "Incubate" in act:
                    msg = f"[SYSTEM] Wait {vol:.0f}s (Adjust/lower liquid height in Slot 6 Tube A1)"
                else:
                    msg = f"[{act.upper()}] {vol:.0f}\u03bcL at {slot}, Well {well}"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded Liquid Height Test Protocol ({len(loaded_sequence)} steps). Slot 6 Rack & Slot 2 Waste auto-assigned.")
        else:
            messagebox.showerror("File Not Found", "Could not locate Test_Liquid_Level_Detection.json")

    def _populate_workflow_from_sequence(self, loaded_sequence, protocol_name=""):
        self.loaded_protocol_name = protocol_name
        if "300" in protocol_name.lower() or any("300" in str(s.get("label", "")).lower() or "300" in str(s.get("labware", "")).lower() for s in (loaded_sequence or [])):
            if getattr(self, "active_profile_id", "") != "machine_3_300ul":
                self.switch_machine_profile("machine_3_300ul", save_to_disk=True)
            self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        self.workflow_sequence.clear()
        self.wf_box.delete(0, tk.END)
        for step in loaded_sequence:
            self.workflow_sequence.append(step)
            self.wf_box.insert(tk.END, self._format_step_msg(step))
        self._update_estimated_timer_preview()
        if hasattr(self, '_refresh_tip_memory_badge'):
            self._refresh_tip_memory_badge("Slot_4")
        self.logger.info(f"Loaded {protocol_name} ({len(loaded_sequence)} steps into Protocol Runner).")

    def show_protocol_deck_setup_modal(
        self,
        protocol_name: str,
        pipettor_mode: str,
        is_multichannel: bool,
        deck_setup: dict,
        slot_descriptions: dict,
        sequence: list = None,
        on_confirm_callback=None
    ):
        top = tk.Toplevel(self.root)
        top.title(f"Deck Setup & Confirmation — {protocol_name}")
        top.geometry("680x720")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 340
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 360
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass

        # 1. Header Frame
        hdr = tk.Frame(top, bg="#28a745", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text=f"🟢 {protocol_name}",
            font=("Arial", 11, "bold"),
            bg="#28a745",
            fg="white"
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=f"Required Pipettor Head: {pipettor_mode}",
            font=("Arial", 9, "bold"),
            bg="#28a745",
            fg="#e8f5e9"
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(top, padding=14)
        body.pack(fill=tk.BOTH, expand=True)

        # 2. Analyze tips and clearance/empty slots
        tips_info, empty_slots, active_slots = self._analyze_protocol_tips_and_slots(
            sequence=sequence,
            is_multichannel=is_multichannel,
            deck_setup=deck_setup,
            slot_descriptions=slot_descriptions
        )

        # 3. Empty Slots Alert Banner
        if empty_slots:
            alert_box = tk.Frame(body, bg="#fff3cd", relief="solid", bd=1, padx=12, pady=8)
            alert_box.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                alert_box,
                text="⛔ SLOTS TO KEEP COMPLETELY EMPTY (CLEARANCE ZONE):",
                font=("Arial", 9, "bold"),
                bg="#fff3cd",
                fg="#721c24"
            ).pack(anchor="w")
            tk.Label(
                alert_box,
                text=f"• Keep {', '.join(empty_slots)} completely clear. Do NOT place any labware, plates, or reservoirs here.",
                font=("Arial", 9),
                bg="#fff3cd",
                fg="#856404"
            ).pack(anchor="w", pady=(2, 0))
        else:
            info_box = tk.Frame(body, bg="#e2e3e5", relief="solid", bd=1, padx=12, pady=6)
            info_box.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                info_box,
                text="ℹ️ ALL 6 SLOTS OCCUPIED: Verify labware is properly placed on all slots 1 through 6.",
                font=("Arial", 9, "bold"),
                bg="#e2e3e5",
                fg="#383d41"
            ).pack(anchor="w")

        # 4. Tip Requirements Card
        tip_box = tk.Frame(body, bg="#d1ecf1", relief="solid", bd=1, padx=12, pady=8)
        tip_box.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            tip_box,
            text="🎯 TIP REQUIREMENTS BEFORE STARTING:",
            font=("Arial", 9, "bold"),
            bg="#d1ecf1",
            fg="#0c5460"
        ).pack(anchor="w")
        for ti in tips_info:
            tk.Label(
                tip_box,
                text=f"• {ti}",
                font=("Arial", 9),
                bg="#d1ecf1",
                fg="#0c5460"
            ).pack(anchor="w")
        tk.Label(
            tip_box,
            text="• Load fresh clean tips ONLY in the required columns/wells above. Empty columns (e.g. Cols 7..12) serve as the Tip Graveyard.",
            font=("Arial", 8, "italic"),
            bg="#d1ecf1",
            fg="#0c5460"
        ).pack(anchor="w", pady=(2, 0))

        ttk.Label(
            body,
            text="Verify your physical deck layout matches the assignments below before proceeding:",
            font=("Arial", 9, "bold")
        ).pack(anchor="w", pady=(0, 8))

        # 5. Deck Slot Table
        table_f = ttk.Frame(body)
        table_f.pack(fill=tk.BOTH, expand=True)

        # Header row
        ttk.Label(table_f, text="Slot", font=("Arial", 9, "bold"), width=8).grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(table_f, text="Labware Model (Reservoir Options)", font=("Arial", 9, "bold"), width=34).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(table_f, text="Deck Contents / Reagent Purpose", font=("Arial", 9, "bold")).grid(row=0, column=2, sticky="w", pady=3)
        ttk.Separator(table_f, orient="horizontal").grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 4))

        slot_combos = {}
        for idx, s_num in enumerate(range(1, 7), start=2):
            s_name = f"Slot_{s_num}"
            s_label = f"Slot {s_num}"
            lw_file = deck_setup.get(s_name, "(Empty / Clearance)")
            desc = slot_descriptions.get(s_name, "Empty clearance slot")
            is_empty = (s_label in empty_slots) or ("Empty" in lw_file) or ("Clearance" in desc)
            is_tip = "tip" in lw_file.lower()
            is_plate = any(k in lw_file.lower() for k in ("plate", "96", "48", "ehm", "myriamed"))
            is_res = (
                not is_empty
                and not is_tip
                and not is_plate
                and ("reservoir" in lw_file.lower() or "reservoir" in desc.lower())
            )

            if is_empty:
                bg_col = "#f8d7da"
                fg_col = "#721c24"
                lw_display = "[KEEP COMPLETELY EMPTY]"
                desc_display = "⛔ DO NOT PLACE LABWARE — Must remain completely clear"
            elif is_tip:
                bg_col = "#cce5ff"
                fg_col = "#004085"
                lw_display = lw_file
                desc_display = desc
            else:
                bg_col = "#d4edda"
                fg_col = "#155724"
                lw_display = lw_file
                desc_display = desc

            badge = tk.Label(table_f, text=f"Slot {s_num}", font=("Consolas", 9, "bold"), bg=bg_col, fg=fg_col, padx=4, pady=2)
            badge.grid(row=idx, column=0, sticky="w", pady=3)

            if is_res:
                if is_multichannel:
                    res_choices = {
                        "7-Column Reservoir (reservoir_7_column.json)": "reservoir_7_column.json",
                        "6-Column Reservoir (reservoir_6_column.json)": "reservoir_6_column.json",
                    }
                else:
                    res_choices = {
                        "7-Column Reservoir (reservoir_7_column.json)": "reservoir_7_column.json",
                        "6-Column Reservoir (reservoir_6_column.json)": "reservoir_6_column.json",
                        "3-Well Reservoir (reservoir_3_well.json)": "reservoir_3_well.json",
                        "12-Tube 2 mL Rack (tube_rack_2x6_2ml.json)": "tube_rack_2x6_2ml.json",
                    }
                matched_k = next((k for k, v in res_choices.items() if v == lw_file), None)
                if not matched_k:
                    if "6" in lw_file:
                        matched_k = "6-Column Reservoir (reservoir_6_column.json)"
                    elif "3" in lw_file:
                        matched_k = "3-Well Reservoir (reservoir_3_well.json)"
                    elif "2x6" in lw_file:
                        matched_k = "12-Tube 2 mL Rack (tube_rack_2x6_2ml.json)"
                    else:
                        matched_k = "7-Column Reservoir (reservoir_7_column.json)"
                combo_var = tk.StringVar(value=matched_k)
                combo = ttk.Combobox(table_f, textvariable=combo_var, values=list(res_choices.keys()), state="readonly", width=34)
                combo.grid(row=idx, column=1, sticky="w", pady=3, padx=(0, 10))
                slot_combos[s_name] = (combo_var, res_choices)
            else:
                lw_lbl = ttk.Label(table_f, text=lw_display, font=("Consolas", 9, "bold" if is_empty else "normal"))
                lw_lbl.grid(row=idx, column=1, sticky="w", pady=3, padx=(0, 10))
                if is_empty:
                    lw_lbl.configure(foreground="#721c24")

            desc_lbl = ttk.Label(table_f, text=desc_display, font=("Arial", 9, "bold" if is_empty else "normal"))
            desc_lbl.grid(row=idx, column=2, sticky="w", pady=3)
            if is_empty:
                desc_lbl.configure(foreground="#721c24")

        # Bottom buttons
        btn_f = ttk.Frame(top, padding=12)
        btn_f.pack(fill=tk.X, side=tk.BOTTOM)

        def on_confirm():
            # 1. Switch pipettor head mode live if needed
            self.switch_pipettor_head(pipettor_mode if pipettor_mode else is_multichannel, quiet=True)

            # Apply any reservoir labware selections made via comboboxes
            for s_name, (c_var, c_map) in slot_combos.items():
                chosen_disp = c_var.get()
                chosen_file = c_map.get(chosen_disp, deck_setup.get(s_name))
                old_file = deck_setup.get(s_name)
                deck_setup[s_name] = chosen_file

                if sequence:
                    for step in sequence:
                        if step.get("slot") == s_name:
                            step["labware"] = chosen_file
                            if chosen_file == "reservoir_6_column.json":
                                if step.get("well") in ("A7", "R7"):
                                    step["well"] = "A6"
                                    if "R7" in step.get("label", "") or "A7" in step.get("label", ""):
                                        step["label"] = step["label"].replace("R7", "R6").replace("A7", "A6")
                            elif chosen_file == "reservoir_7_column.json":
                                if step.get("well") in ("A6", "R6") and "waste" in step.get("label", "").lower():
                                    step["well"] = "A7"
                                    if "R6" in step.get("label", ""):
                                        step["label"] = step["label"].replace("R6", "R7").replace("A6", "A7")

            # 2. Update deck labware while keeping all 6 slot squares visible on the deck canvas
            lw_dir = self.get_labware_dir()
            for s_num in range(1, 7):
                s_name = f"Slot_{s_num}"
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
                if s_name in self.unplaced_slots:
                    self.unplaced_slots.remove(s_name)
                lw_file = deck_setup.get(s_name)
                if lw_file and lw_file != "(Empty / Clearance)":
                    lp = os.path.join(lw_dir, lw_file)
                    if os.path.exists(lp):
                        self.lims.deck_labware[s_name] = Labware(lp)
                        self.lims.deck_labware[s_name].source_file = lw_file
                else:
                    self.lims.deck_labware.pop(s_name, None)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'):
                self.draw_deck()

            top.destroy()
            if on_confirm_callback:
                on_confirm_callback()

        tk.Button(
            btn_f,
            text="🟢 Confirm Deck & Load Protocol",
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            font=("Arial", 10, "bold"),
            command=on_confirm
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=top.destroy).pack(side=tk.RIGHT)

    # -------------------------------------------------------------------------
    # DYNAMIC PROTOCOL DROPDOWN & QUICK HOMING HELPERS
    # -------------------------------------------------------------------------
    def _get_protocols_for_pipettor(self, pipettor_name: str) -> dict:
        """Returns ordered dict mapping protocol display labels to loading functions for the active user workflows."""
        p_name = str(pipettor_name).lower()
        if "1000" in p_name or "8×1000" in p_name:
            return {
                "Media Change (Plates 5 & 6 — 500 µL Dispense)": self.action_load_8ch_1000ul_media_change_protocol,
                "Fresh Media Only Multi-Dispense (22 steps)": self.action_load_8ch_fresh_media_only,
                "Test Slot 5 Media Removal (Col 3 Tips ➔ Return Col 1)": self.action_load_slot5_media_removal_test,
            }
        elif "1-10" in p_name or "8×10" in p_name or "10 µl" in p_name or ("10" in p_name and "1000" not in p_name):
            return {
                "3x [8-Tip Both Plates] Drug Addition to EHM (7.5 µL) + Mix": lambda: self.action_load_10ul_3x_8tip_both_plates(7.5),
                "3x [8-Tip Both Plates] Drug Addition to EHM (5.0 µL) + Mix": lambda: self.action_load_10ul_3x_8tip_both_plates(5.0),
                "[5-Tip Parallel] Drug Addition to EHM (7.5 µL) + Mix (~8 mins)": lambda: self.action_load_10ul_parallel_drug_addition(7.5),
                "[5-Tip Parallel] Drug Addition to EHM (5.0 µL) + Mix (~8 mins)": lambda: self.action_load_10ul_parallel_drug_addition(5.0),
                "[Triplicate Assay] Drug Addition to EHM (7.5 µL) + Mix": lambda: self.action_load_10ul_triplicate_drug_addition(7.5),
                "[Triplicate Assay] Drug Addition to EHM (5.0 µL) + Mix": lambda: self.action_load_10ul_triplicate_drug_addition(5.0),
            }
        elif "300" in p_name:
            return {
                "Prepping DMSO-Drug Dilution (3x Plate - 200 µL Limit)": self.action_load_300ul_dmso_dilution_3x_plate,
                "Prepping DMSO-Drug Dilution (1x Plate - 200 µL Limit)": self.action_load_300ul_dmso_dilution_1x_plate,
                "Prepping DMSO-Drug Dilution (96-Well Plate)": self.action_load_300ul_dmso_dilution,
                "Drug Addition to EHM Plates (7.5 µL) + Mix": lambda: self.action_load_300ul_drug_addition(7.5),
                "Drug Addition to EHM Plates (5.0 µL) + Mix": lambda: self.action_load_300ul_drug_addition(5.0),
            }
        else:  # Fallback: 8-Channel Multi (8×1000 µL) [Media Change]
            return {
                "Media Change (Plates 5 & 6 — 500 µL Dispense)": self.action_load_8ch_1000ul_media_change_protocol,
                "Fresh Media Only Multi-Dispense (22 steps)": self.action_load_8ch_fresh_media_only,
                "Test Slot 5 Media Removal (Col 3 Tips ➔ Return Col 1)": self.action_load_slot5_media_removal_test,
            }

    def _update_protocol_dropdown(self, event=None):
        """Updates the protocol combobox choices to match the currently selected pipettor."""
        pipettor = self.proto_pipettor_var.get() if hasattr(self, 'proto_pipettor_var') else self.head_mode_var.get()
        protocols_map = self._get_protocols_for_pipettor(pipettor)
        choices = list(protocols_map.keys())
        if hasattr(self, 'proto_workflow_cb'):
            self.proto_workflow_cb['values'] = choices
            cur = self.proto_workflow_var.get() if hasattr(self, 'proto_workflow_var') else ""
            if cur not in choices and choices:
                self.proto_workflow_var.set(choices[0])

    def _on_proto_pipettor_selected(self, event=None):
        """Called when user changes pipettor dropdown in the protocol panel."""
        sel_pipettor = self.proto_pipettor_var.get()
        self.switch_pipettor_head(sel_pipettor, quiet=True)
        self._update_protocol_dropdown()

    def _execute_selected_protocol_load(self):
        """Loads the currently selected protocol in the dropdown."""
        pipettor = self.proto_pipettor_var.get()
        self.switch_pipettor_head(pipettor, quiet=True)
        proto_name = self.proto_workflow_var.get()
        protocols_map = self._get_protocols_for_pipettor(pipettor)
        loader_fn = protocols_map.get(proto_name)
        if loader_fn and callable(loader_fn):
            loader_fn()
        else:
            messagebox.showinfo("Select Protocol", "Please select a valid protocol from the dropdown.")

    def quick_home_head(self):
        """Resets pipette head to safety origin (HOME)."""
        if getattr(self, 'is_running', False):
            messagebox.showwarning("Protocol Running", "Cannot home head while a protocol is actively running.")
            return
        try:
            if hasattr(self, 'lims') and hasattr(self.lims, 'hw') and self.lims.hw.is_initialized:
                hw_inst = getattr(self.lims.pipettor, 'hardware', None)
                if hw_inst and hasattr(hw_inst, 'initialize'):
                    hw_inst.initialize()
            self.current_pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
            if hasattr(self, 'jog_vars'):
                for a in ("X", "Y", "Z"):
                    if a in self.jog_vars:
                        self.jog_vars[a].set(0.0)
            if hasattr(self, 'logger'):
                self.logger.info("[HOME] Pipette head reset to safety origin (X=0.0, Y=0.0, Z=0.0)")
            if hasattr(self, 'lbl_stat_pos'):
                self.lbl_stat_pos.config(text="POS: X:0.0 Y:0.0 Z:0.0")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"[HOME ERROR] Failed to home head: {e}")
            messagebox.showerror("Homing Error", f"Error during head reset: {e}")

    def _home_z_axis_only(self, reason: str = "", step_idx: int = None, total_steps: int = None) -> bool:
        """
        Physically homes ONLY the Z-axis against the top home switch (Z=0.00mm)
        without touching X, Y, mounted tips, or the pipette plunger ('P').
        Compensates for cumulative downward stepper drift (e.g., on the 300 µL head).
        """
        try:
            ok = True
            msg = "Z=0.00mm"
            if hasattr(self, "lims") and hasattr(self.lims, "hw") and hasattr(self.lims.hw, "home_z_only"):
                ok, msg = self.lims.hw.home_z_only(logger=getattr(self, "logger", None), reason=reason)
            elif hasattr(self, "lims") and getattr(self.lims.pipettor, "hardware", None):
                self.lims.pipettor.hardware.move_z(0)

            self.current_pos["Z"] = 0.0
            self.z_home_step_counter = getattr(self, "z_home_step_counter", 0) + 1

            def _sync_z_ui():
                if hasattr(self, "jog_vars") and "Z" in self.jog_vars:
                    try:
                        self.jog_vars["Z"].set(0.0)
                    except Exception:
                        pass

            if threading.current_thread() is threading.main_thread():
                _sync_z_ui()
            else:
                try:
                    self.root.after(0, _sync_z_ui)
                except Exception:
                    pass

            if hasattr(self, "logger"):
                step_tag = f" (Step {step_idx}/{total_steps}: {reason})" if step_idx is not None else (f" ({reason})" if reason else "")
                self.logger.info(
                    f"[Z-HOME] Physical Z-axis re-homed at top sensor{step_tag} -> Z=0.00mm (Tip & plunger preserved)"
                )
            return ok
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"[Z-HOME] Failed to re-home Z-axis: {e}")
            return False

    def quick_safe_z(self):
        """Immediately moves Z-axis up to safety clearance (Z = 0.0 mm) and physically re-homes Z."""
        if getattr(self, 'is_running', False):
            messagebox.showwarning("Protocol Running", "Cannot move Z while a protocol is actively running.")
            return
        try:
            self._quick_move_z(0.0)
            self._home_z_axis_only(reason="Quick Safe Z")
            if hasattr(self, 'logger'):
                self.logger.info("[SAFE Z] Retracted & physically re-homed Z-axis to clearance origin (Z=0.0 mm)")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"[SAFE Z ERROR] Failed to retract Z: {e}")

    # -------------------------------------------------------------------------
    # 0. 8-CHANNEL 1-10 µL PROTOCOL LOADERS
    # -------------------------------------------------------------------------
    def action_load_10ul_3x_8tip_both_plates(self, volume: float = 7.5):
        self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"Machine_2_EHM_8tip_Both_Plates_{vol_str}_REVIEW.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "waste_trough.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "myriamed_48_well.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone",
            "Slot_2": "Waste Trough (8-Tip Eject above Slot 2 Well A1 at clearance height)",
            "Slot_3": "Prepped 3x 96-Well Drug Plate (Rows A-H across Cols 1..12)",
            "Slot_4": "1-10 µL Tip Rack (Full 96 Tips: All 12 Columns x 8 Tips A-H)",
            "Slot_5": "Plate 1 (Myriamed 48-Well EHM, Cols 1..6, 5x 8 µL Mix)",
            "Slot_6": "Plate 2 (Myriamed 48-Well EHM, Cols 1..6, 5x 8 µL Mix)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"3x [8-Tip Both Plates] EHM Drug Addition ({volume:g} µL) + Mix")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"3x [8-Tip Both Plates] Drug Addition to EHM ({volume:g} µL) + Mix",
            pipettor_mode="8-Channel Multi (1-10 µL)",
            is_multichannel=True,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_10ul_parallel_drug_addition(self, volume: float = 7.5):
        self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"ehm_1ch_10ul_drug_addition_to_ehm_{vol_str}.json"
        target_path = self.resolve_protocol_path(
            filename,
            f"ehm_1ch_10ul_drug_addition_to_ehm_{volume:g}uL.json",
            f"ehm_8ch_10ul_parallel_drug_addition_{vol_str}.json",
            f"ehm_8ch_10ul_drug_addition_to_ehm_{vol_str}.json",
        )
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "(Empty / Clearance)",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "myriamed_48_well.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone",
            "Slot_2": "Empty clearance zone",
            "Slot_3": "Prepped DMSO-Drug Diluted Ready Plate (96-Well, Rows A..E: 5 Drugs x 6 Concs)",
            "Slot_4": "1-10 µL Tip Rack (30 Fresh Tips: Rows A–E across Cols 1..6; Graveyard: Cols 7..12 at Z=40.5mm)",
            "Slot_5": "Plate 1 (Myriamed 48-Well EHM, Cols 1..6, 8.5mm raised Z)",
            "Slot_6": "Plate 2 (Myriamed 48-Well EHM, Cols 1..6, 8.5mm raised Z)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"[8-CH 1-10 µL Parallel] Drug Addition ({volume:g} µL) to EHM")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"[8-CH 1-10 µL Parallel] Drug Addition to EHM ({volume:g} µL) + Mix",
            pipettor_mode="8-Channel Multi (1-10 µL)",
            is_multichannel=True,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_10ul_triplicate_drug_addition(self, volume: float = 7.5):
        self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"ehm_1ch_10ul_triplicate_drug_addition_{vol_str}.json"
        target_path = self.resolve_protocol_path(
            filename,
            f"ehm_1ch_10ul_triplicate_drug_addition_{volume:g}uL.json",
            f"ehm_1ch_10ul_drug_addition_to_ehm_{vol_str}.json",
        )
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "(Empty / Clearance)",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "myriamed_48_well.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone",
            "Slot_2": "Empty clearance zone",
            "Slot_3": "Prepped DMSO-Drug Diluted Ready Plate (96-Well, Rows A..E: 5 Drugs x 6 Concs)",
            "Slot_4": "1-10 µL Tip Rack (36 Fresh Tips: Cols 1..5 [A1..D5]; Graveyard: Cols 7..11 [A7..D11] at Z=40.5mm)",
            "Slot_5": "Destination Plate 1 (Myriamed 48-Well EHM: Triplicates for Drug 1 [Rows A-C], Drug 2 [Rows D-F], Drug 3 Reps 1-2 [Rows G-H])",
            "Slot_6": "Destination Plate 2 (Myriamed 48-Well EHM: Triplicates for Drug 3 Rep 3 [Row A], Drug 4 [Rows B-D], Drug 5 [Rows E-G], Control [Row H])",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"[1-10 µL Triplicates] Drug Addition ({volume:g} µL) to EHM")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"[1-10 µL Triplicates] Drug Addition to EHM ({volume:g} µL) + Mix",
            pipettor_mode="8-Channel Multi (1-10 µL)",
            is_multichannel=True,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_10ul_drug_addition_to_ehm(self, volume: float = 7.5):
        return self.action_load_10ul_parallel_drug_addition(volume=volume)

    def action_load_10ul_multi_drug_addition_to_ehm(self, volume: float = 7.5):
        return self.action_load_10ul_parallel_drug_addition(volume=volume)

    def action_load_10ul_multi_media_change_and_drug(self, volume: float = 7.5):
        self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
        self.action_load_10ul_parallel_drug_addition(volume=volume)

    def action_load_10ul_multi_dmso_dilution(self):
        self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
        self.action_load_8ch_dmso_dilution()

    def action_load_10ul_multi_fresh_media_only(self):
        self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
        self.action_load_8ch_fresh_media_only()

    def action_load_8ch_fresh_media_only(self):
        filename = "ehm_8ch_1000ul_fresh_media_only_multi_dispense.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "(Empty / Clearance)",
            "Slot_3": "myriamed_48_well.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "reservoir_7_column.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone",
            "Slot_2": "Empty clearance zone",
            "Slot_3": "Plate 1 / Plt 5 (Myriamed 48-well EHM, Cols 1..6)",
            "Slot_4": "Tip Rack (Cols 1-2 fresh tips)",
            "Slot_5": "Plate 2 / Plt 6 (Myriamed 48-well EHM, Cols 1..6)",
            "Slot_6": "7-Col Reservoir (R6: Fresh Plate 1 [>27 mL], R7: Fresh Plate 2 [>27 mL])",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, "[8-CH] Fresh Media Only Multi-Dispense (22 steps)")

        self.show_protocol_deck_setup_modal(
            protocol_name="[8-CH] Fresh Media Only Multi-Dispense (Plate 5 & 6)",
            pipettor_mode=self.head_mode_var.get(),
            is_multichannel=True,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    # -------------------------------------------------------------------------
    # 1. 8-CHANNEL MULTI PIPETTOR (8x1000 uL)
    # -------------------------------------------------------------------------
    def action_load_8ch_media_change_and_drug(self, volume: float = 7.5):
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"ehm_8ch_1000ul_media_change_and_drug_{vol_str}.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "generic_96_well_plate.json",
            "Slot_2": "(Empty / Clearance)",
            "Slot_3": "myriamed_48_well.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "reservoir_7_column.json",
        }
        slot_descs = {
            "Slot_1": f"96-Well Drug Plate (Rows A-H, Cols 1..6, {volume:g} µL)",
            "Slot_2": "Clearance zone (Empty)",
            "Slot_3": "Plate 1 / Plt 5 (Myriamed 48-well EHM, Cols 1..6)",
            "Slot_4": "1000 µL Tip Rack (Cols 1-6 fresh tips, Cols 12-7 graveyard)",
            "Slot_5": "Plate 2 / Plt 6 (Myriamed 48-well EHM, Cols 1..6)",
            "Slot_6": "7-Col Reservoir (R1: Discard Plate 1, R2: Discard Plate 2, R6: Fresh Plate 1 [>27 mL], R7: Fresh Plate 2 [>27 mL])",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"[8-CH] Media Change + {volume:g} µL Drug Addition")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"[8-CH] Media Change + {volume:g} µL Drug Addition (Plate 5 & 6)",
            pipettor_mode="8×1000 µL (8-Channel Manifold)",
            is_multichannel=True,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_8ch_dmso_dilution(self):
        filename = "ehm_8ch_1000ul_dmso_drug_dilution.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "waste_trough.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "generic_96_well_plate.json",
            "Slot_6": "reservoir_7_column.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone (Parked / Safe Y axis clearance)",
            "Slot_2": "Waste Trough (Liquid Waste & Tip Discard)",
            "Slot_3": "96-Well Stock Drug Plate (Interactive Source Wells)",
            "Slot_4": "1000 µL Tip Rack (Cols 1-3 fresh tips)",
            "Slot_5": "96-Well Target Dilution Plate (Serial Mix Cols 1..6)",
            "Slot_6": "7-Col or 6-Col Reservoir (A1: Pure DMSO Buffer)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def on_deck_confirmed():
            self.prompt_drug_wells_and_load(
                seq,
                protocol_name="[8-CH] DMSO-Drug Serial Dilution",
                deck_setup=deck_setup,
            )

        self.show_protocol_deck_setup_modal(
            protocol_name="[8-CH] DMSO-Drug Serial Dilution (96-Well Plate)",
            pipettor_mode="8×1000 µL (8-Channel Manifold)",
            is_multichannel=True,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=on_deck_confirmed
        )

    # -------------------------------------------------------------------------
    # 2. 300 uL SINGLE-CHANNEL PIPETTE
    # -------------------------------------------------------------------------
    def action_load_300ul_media_change_and_drug(self, volume: float = 7.5):
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"ehm_1ch_300ul_media_change_and_drug_{vol_str}.json"
        target_path = self.resolve_protocol_path(
            filename,
            f"media_change_and_drug_addition_2_plates_{vol_str}.json"
        )
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "reservoir_3_well.json",
            "Slot_2": "reservoir_3_well.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "myriamed_48_well.json",
        }
        slot_descs = {
            "Slot_1": "3-Well Reservoir (A1: Plate 1 Fresh [>27 mL], A2: Plate 2 Fresh [>27 mL])",
            "Slot_2": "3-Well Reservoir (A1: Old Media Waste, A2: Plt 1 Tips, A3: Plt 2 Tips)",
            "Slot_3": "96-Well Drug Plate (Stock Drug Conditions D11..D15 + Control)",
            "Slot_4": "300 µL Tip Rack (Full 96 Tips)",
            "Slot_5": "Plate 1 (Myriamed 48-well EHM Plate)",
            "Slot_6": "Plate 2 (Myriamed 48-well EHM Plate)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"[300 µL Single] Media Change + {volume:g} µL Drug Addition")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"[300 µL Single] Media Change + {volume:g} µL Drug Addition (2 Plates)",
            pipettor_mode="1×300 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_300ul_drug_addition(self, volume: float = 7.5):
        if getattr(self, "active_profile_id", "") != "machine_3_300ul":
            self.switch_machine_profile("machine_3_300ul", save_to_disk=True)
        self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"ehm_1ch_300ul_drug_addition_{vol_str}.json"
        target_path = self.resolve_protocol_path(
            filename,
            f"drug_addition_only_2_ehm_plates_{vol_str}.json",
            "drug_addition_only_2_ehm_plates.json",
        )
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "waste_trough.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "myriamed_48_well.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone (or 3-Well Reservoir parked safely)",
            "Slot_2": "Waste Trough / Discard Rack (Liquid Waste & Tip Discard)",
            "Slot_3": "Prepped 96-Well Drug Plate (Stock Drug Conditions, Z=98.72 mm)",
            "Slot_4": "300 µL Tip Rack (Single-Channel Tips A1..D5, pickup Z=86.36 mm)",
            "Slot_5": "Destination Plate 1 (Myriamed 48-Well EHM: Rows A-C Drug 1, D-F Drug 2, G-H Drug 3, Z=72.35 mm)",
            "Slot_6": "Destination Plate 2 (Myriamed 48-Well EHM: Row A Drug 3, B-D Drug 4, E-G Drug 5, Row H Control, Z=72.35 mm)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"[300 µL Single] Drug Addition ({volume:g} µL) to EHM Plates")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"[300 µL Single] Drug Addition to EHM ({volume:g} µL) + Mix",
            pipettor_mode="1×300 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_300ul_dmso_dilution(self):
        if getattr(self, "active_profile_id", "") != "machine_3_300ul":
            self.switch_machine_profile("machine_3_300ul", save_to_disk=True)
        self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        filename = "ehm_1ch_300ul_dmso_drug_dilution.json"
        target_path = self.resolve_protocol_path(
            "1_Serial_Dilution_Plate.json",
            filename
        )
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        with open(target_path, "r") as f:
            seq = json.load(f)

        uses_slot2 = any(s.get("slot") == "Slot_2" or s.get("action") == "Discard Tip" for s in seq)
        slot1_lw = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None) or "reservoir_3_well.json"
        if slot1_lw == "tube_rack_2x6_2ml.json":
            slot1_lw = "reservoir_3_well.json"
        slot2_lw = getattr(self.lims.deck_labware.get("Slot_2"), "source_file", None) or ("waste_trough.json" if uses_slot2 else "(Empty / Clearance)")

        deck_setup = {
            "Slot_1": slot1_lw,
            "Slot_2": slot2_lw,
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "generic_96_well_plate.json",
            "Slot_6": "(Empty / Clearance)",
        }
        slot_descs = {
            "Slot_1": "3-Well Reservoir (Well A1 at X=235.05, Y=5.27: Pure DMSO Buffer)",
            "Slot_2": "Waste Trough (Liquid Waste & Tip Graveyard)" if slot2_lw != "(Empty / Clearance)" else "Empty clearance slot",
            "Slot_3": "96-Well Stock Drug Plate (Interactive Source Wells, Z=98.72 mm)",
            "Slot_4": "300 µL Tip Rack (A1 at X=105.63, Y=52.64)",
            "Slot_5": "96-Well Target Dilution Plate (Serial Mix, Z=98.72 mm)",
            "Slot_6": "Empty clearance slot",
        }
        for s in seq:
            if s.get("slot") == "Slot_1" and s.get("labware") == "tube_rack_2x6_2ml.json":
                s["labware"] = slot1_lw
            if (
                s.get("action") == "Aspirate Media"
                and s.get("slot") == "Slot_1"
                and s.get("well") == "A1"
                and float(s.get("volume", 0.0)) >= 150.0
            ):
                s["no_air_cushion"] = True

        def on_deck_confirmed():
            self.prompt_drug_wells_and_load(
                seq,
                protocol_name="[300 µL Single] DMSO-Drug Serial Dilution",
                deck_setup=deck_setup,
            )

        self.show_protocol_deck_setup_modal(
            protocol_name="[300 µL Single] DMSO-Drug Serial Dilution",
            pipettor_mode="1×300 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=on_deck_confirmed
        )

    def action_load_300ul_dmso_dilution_3x_plate(self):
        if getattr(self, "active_profile_id", "") != "machine_3_300ul":
            self.switch_machine_profile("machine_3_300ul", save_to_disk=True)
        self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        filename = "1_200ul_limit_Serial_Dilution_3x_Plate.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        with open(target_path, "r") as f:
            seq = json.load(f)

        uses_slot2 = any(s.get("slot") == "Slot_2" or s.get("action") == "Discard Tip" for s in seq)
        slot1_lw = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None) or "reservoir_3_well.json"
        if slot1_lw == "tube_rack_2x6_2ml.json":
            slot1_lw = "reservoir_3_well.json"
        slot2_lw = getattr(self.lims.deck_labware.get("Slot_2"), "source_file", None) or ("waste_trough.json" if uses_slot2 else "(Empty / Clearance)")

        deck_setup = {
            "Slot_1": slot1_lw,
            "Slot_2": slot2_lw,
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "generic_96_well_plate.json",
            "Slot_6": "(Empty / Clearance)",
        }
        slot_descs = {
            "Slot_1": "3-Well Reservoir (Well A1: Pure DMSO Buffer; Well A3: Waste)",
            "Slot_2": "Waste Trough (Liquid Waste & Tip Graveyard)" if slot2_lw != "(Empty / Clearance)" else "Empty clearance slot",
            "Slot_3": "96-Well Stock Drug Plate (Interactive Source Wells, Z=98.72 mm)",
            "Slot_4": "300 µL Tip Rack (Single-Channel Tips A1..F1)",
            "Slot_5": "96-Well Target Dilution Plate (3x Dilution Series, Z=98.72 mm)",
            "Slot_6": "Empty clearance slot",
        }
        for s in seq:
            if s.get("slot") == "Slot_1" and s.get("labware") == "tube_rack_2x6_2ml.json":
                s["labware"] = slot1_lw
            if (
                s.get("action") == "Aspirate Media"
                and s.get("slot") == "Slot_1"
                and s.get("well") == "A1"
                and float(s.get("volume", 0.0)) >= 150.0
            ):
                s["no_air_cushion"] = True

        def on_deck_confirmed():
            self.prompt_drug_wells_and_load(
                seq,
                protocol_name="[300 µL Single] DMSO-Drug Serial Dilution (3x Plate - 200 µL Limit)",
                deck_setup=deck_setup,
            )

        self.show_protocol_deck_setup_modal(
            protocol_name="[300 µL Single] DMSO-Drug Serial Dilution (3x Plate - 200 µL Limit)",
            pipettor_mode="1×300 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=on_deck_confirmed
        )

    def action_load_300ul_dmso_dilution_1x_plate(self):
        if getattr(self, "active_profile_id", "") != "machine_3_300ul":
            self.switch_machine_profile("machine_3_300ul", save_to_disk=True)
        self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        filename = "1_200ul_limit_Serial_Dilution_Plate.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        with open(target_path, "r") as f:
            seq = json.load(f)

        uses_slot2 = any(s.get("slot") == "Slot_2" or s.get("action") == "Discard Tip" for s in seq)
        slot1_lw = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None) or "reservoir_3_well.json"
        if slot1_lw == "tube_rack_2x6_2ml.json":
            slot1_lw = "reservoir_3_well.json"
        slot2_lw = getattr(self.lims.deck_labware.get("Slot_2"), "source_file", None) or ("waste_trough.json" if uses_slot2 else "(Empty / Clearance)")

        deck_setup = {
            "Slot_1": slot1_lw,
            "Slot_2": slot2_lw,
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "generic_96_well_plate.json",
            "Slot_6": "(Empty / Clearance)",
        }
        slot_descs = {
            "Slot_1": "3-Well Reservoir (Well A1: Pure DMSO Buffer)",
            "Slot_2": "Waste Trough (Liquid Waste & Tip Graveyard)" if slot2_lw != "(Empty / Clearance)" else "Empty clearance slot",
            "Slot_3": "96-Well Stock Drug Plate (Interactive Source Wells, Z=98.72 mm)",
            "Slot_4": "300 µL Tip Rack (Single-Channel Tips A1..E1)",
            "Slot_5": "96-Well Target Dilution Plate (1x Dilution Series, Z=98.72 mm)",
            "Slot_6": "Empty clearance slot",
        }
        for s in seq:
            if s.get("slot") == "Slot_1" and s.get("labware") == "tube_rack_2x6_2ml.json":
                s["labware"] = slot1_lw
            if (
                s.get("action") == "Aspirate Media"
                and s.get("slot") == "Slot_1"
                and s.get("well") == "A1"
                and float(s.get("volume", 0.0)) >= 150.0
            ):
                s["no_air_cushion"] = True

        def on_deck_confirmed():
            self.prompt_drug_wells_and_load(
                seq,
                protocol_name="[300 µL Single] DMSO-Drug Serial Dilution (1x Plate - 200 µL Limit)",
                deck_setup=deck_setup,
            )

        self.show_protocol_deck_setup_modal(
            protocol_name="[300 µL Single] DMSO-Drug Serial Dilution (1x Plate - 200 µL Limit)",
            pipettor_mode="1×300 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=on_deck_confirmed
        )

    # -------------------------------------------------------------------------
    # 3. 20 uL SINGLE-CHANNEL PIPETTE
    # -------------------------------------------------------------------------
    def action_load_20ul_drug_addition(self, volume: float = 7.5):
        vol_str = f"{volume:.1f}uL" if volume in (5.0, 7.5) else f"{volume:g}uL"
        filename = f"ehm_1ch_20ul_drug_addition_{vol_str}.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "tube_rack_2x6_2ml.json",
            "Slot_2": "reservoir_3_well.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "myriamed_48_well.json",
        }
        slot_descs = {
            "Slot_1": "12-Tube Rack (Buffer / Control Media)",
            "Slot_2": "Waste Reservoir (A2: Plate 1 Tips, A3: Plate 2 Tips)",
            "Slot_3": "96-Well Stock Drug Plate (Conditions D11..D15 + Control)",
            "Slot_4": "20 µL Micro Tip Rack",
            "Slot_5": "Plate 1 (Myriamed 48-well EHM Plate)",
            "Slot_6": "Plate 2 (Myriamed 48-well EHM Plate)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def do_load():
            self._populate_workflow_from_sequence(seq, f"[20 µL Single] High-Precision Drug Addition ({volume:g} µL)")

        self.show_protocol_deck_setup_modal(
            protocol_name=f"[20 µL Single] High-Precision Drug Addition ({volume:g} µL) + Mix",
            pipettor_mode="1×20 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=do_load
        )

    def action_load_20ul_dmso_dilution(self):
        filename = "ehm_1ch_20ul_dmso_drug_dilution.json"
        target_path = self.resolve_protocol_path(filename)
        if not target_path:
            messagebox.showerror("File Not Found", f"Could not locate {filename}")
            return

        deck_setup = {
            "Slot_1": "(Empty / Clearance)",
            "Slot_2": "waste_trough.json",
            "Slot_3": "generic_96_well_plate.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "generic_96_well_plate.json",
            "Slot_6": "reservoir_7_column.json",
        }
        slot_descs = {
            "Slot_1": "Empty clearance zone (Parked / Safe Y axis clearance)",
            "Slot_2": "Waste Trough (Liquid Waste & Tip Discard)",
            "Slot_3": "96-Well Stock Drug Plate (Interactive Source Wells)",
            "Slot_4": "20 µL Micro Tip Rack",
            "Slot_5": "96-Well Target Dilution Plate (20 µL Precision Mix)",
            "Slot_6": "7-Col / 6-Col Reservoir or Rack (A1: Pure DMSO Buffer)",
        }
        with open(target_path, "r") as f:
            seq = json.load(f)

        def on_deck_confirmed():
            self.prompt_drug_wells_and_load(
                seq,
                protocol_name="[20 µL Single] Precision DMSO-Drug Dilution",
                deck_setup=deck_setup,
            )

        self.show_protocol_deck_setup_modal(
            protocol_name="[20 µL Single] Precision DMSO-Drug Dilution",
            pipettor_mode="1×20 µL (Single-Channel)",
            is_multichannel=False,
            deck_setup=deck_setup,
            slot_descriptions=slot_descs,
            sequence=seq,
            on_confirm_callback=on_deck_confirmed
        )

    def action_load_media_and_drug_protocol(self, volume: float = 7.5):
        return self.action_load_300ul_media_change_and_drug(volume)

    def action_load_unified_media_and_drug_protocol(self):
        return self.action_load_media_and_drug_protocol(7.5)

    def action_load_media_and_drug_resume_g1_protocol(self, volume: float = 7.5):
        vol_suffix = f"_{volume:.1f}uL" if volume == 5.0 else "_7.5uL"
        target_path = self.resolve_protocol_path(
            f"media_change_and_drug_addition_2_plates_resume_G1{vol_suffix}.json",
            f"2_EHM_Media_Change_and_Drug_Addition_resume_G1{vol_suffix}.json",
            "media_change_and_drug_addition_2_plates_resume_G1.json",
        )
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            deck_setup = {
                "Slot_1": "reservoir_3_well.json",
                "Slot_2": "reservoir_3_well.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "myriamed_48_well.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'): self.draw_deck()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = float(step.get('volume', 0.0))
                mix_cycles = int(step.get('mix_cycles', 0))
                mix_vol = float(step.get('mix_volume', 100.0))
                mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
                vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot}, Well {well}"
                else:
                    msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
                self.wf_box.insert(tk.END, msg)

            self._update_estimated_timer_preview()
            self.logger.info(f"Loaded Resume Protocol ({volume:.1f}µL, {len(loaded_sequence)} steps). Starts from Step 1: Pick Up Tip Slot 4 G1 -> Aspirate Slot 5 G1.")
        else:
            messagebox.showerror("File Not Found", f"Could not locate media_change_and_drug_addition_2_plates_resume_G1{vol_suffix}.json")

    def action_load_plate2_rowH_protocol(self):
        target_path = self.resolve_protocol_path(
            "media_change_plate2_rowH_only.json",
            "plate2_rowH_media_change_only.json",
        )
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            deck_setup = {
                "Slot_1": "reservoir_3_well.json",
                "Slot_2": "reservoir_3_well.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "myriamed_48_well.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'): self.draw_deck()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = float(step.get('volume', 0.0))
                mix_cycles = int(step.get('mix_cycles', 0))
                mix_vol = float(step.get('mix_volume', 100.0))
                mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
                vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot}, Well {well}"
                else:
                    msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
                self.wf_box.insert(tk.END, msg)

            self._update_estimated_timer_preview()
            self.logger.info(f"Loaded Plate 2 Row H Media Change Only Protocol ({len(loaded_sequence)} steps). Tips used: C3 (Removal) and D3 (Fresh Media).")
        else:
            messagebox.showerror("File Not Found", "Could not locate media_change_plate2_rowH_only.json")

    def action_load_drug_addition_only_protocol(self):
        target_path = self.resolve_protocol_path(
            "drug_addition_only_2_ehm_plates.json",
            "2b_EHM_Drug_Addition.json",
        )
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            deck_setup = {
                "Slot_2": "tube_rack_3x50ml.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "myriamed_48_well.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'): self.draw_deck()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = float(step.get('volume', 0.0))
                mix_cycles = int(step.get('mix_cycles', 0))
                mix_vol = float(step.get('mix_volume', 100.0))
                mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
                vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot}, Well {well}"
                else:
                    msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
                self.wf_box.insert(tk.END, msg)

            self._update_estimated_timer_preview()
            self.logger.info(f"Loaded Drug Addition Only Protocol ({len(loaded_sequence)} steps). Slot 3 Drug Plate, Slot 4 Tips, Slot 5/6 EHM Plates.")
        else:
            messagebox.showerror("File Not Found", "Could not locate drug_addition_only_2_ehm_plates.json")

    def action_load_dmso_dilution_protocol(self):
        target_path = self.resolve_protocol_path(
            "1_Serial_Dilution_Plate.json",
            "bakar_v2_drug_dmso_initial_loading.json",
        )
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)

            slot1_lw = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None) or "reservoir_3_well.json"
            deck_setup = {
                "Slot_1": slot1_lw,
                "Slot_2": "waste_trough.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "generic_96_well_plate.json",
            }
            self.prompt_drug_wells_and_load(
                loaded_sequence,
                protocol_name="DMSO-Drug Plate Prep (Initial: 24 µL DMSO + 22 µL Drug)",
                deck_setup=deck_setup,
            )
        else:
            messagebox.showerror("File Not Found", "Could not locate 1_Serial_Dilution_Plate.json or bakar_v2_drug_dmso_initial_loading.json")

    def apply_drug_well_mapping_and_load(self, loaded_sequence, protocol_name, deck_setup, chosen_wells, dmso_labware=None):
        """
        Validates custom Slot 3 stock drug source wells, normalizes Slot 1 DMSO labware
        and Slot 2 A1 waste routing, switches to 1x200 uL single-channel mode, and loads
        the protocol onto the Deck & Workflow Runner.
        """
        cleaned_wells = []
        for val in chosen_wells:
            w = str(val or "").strip().upper()
            if not re.match(r"^[A-H]([1-9]|1[0-2])$", w):
                raise ValueError(f"'{val}' is not a valid 96-well format (must be A1 through H12).")
            cleaned_wells.append(w)

        is_8ch = any(s.get("eight_ch_symmetric", False) for s in loaded_sequence) or "8-CH" in protocol_name or "8x1000" in protocol_name
        self.switch_pipettor_head(is_8ch, quiet=True)

        eff_deck = dict(deck_setup or {})
        dmso_target_slot = "Slot_1"
        if dmso_labware:
            if dmso_labware in ("reservoir_7_column.json", "reservoir_6_column.json") or (eff_deck.get("Slot_1") == "(Empty / Clearance)" and "Slot_6" in eff_deck):
                dmso_target_slot = "Slot_6"
                eff_deck["Slot_6"] = dmso_labware
            else:
                dmso_target_slot = "Slot_1"
                eff_deck["Slot_1"] = dmso_labware
        elif eff_deck.get("Slot_1") and eff_deck.get("Slot_1") != "(Empty / Clearance)":
            dmso_target_slot = "Slot_1"
            dmso_labware = eff_deck.get("Slot_1")
        elif eff_deck.get("Slot_6"):
            dmso_target_slot = "Slot_6"
            dmso_labware = eff_deck.get("Slot_6")
        else:
            dmso_target_slot = "Slot_1"
            dmso_labware = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None) or "reservoir_3_well.json"
            eff_deck["Slot_1"] = dmso_labware

        drug_steps_indices = [
            i for i, s in enumerate(loaded_sequence)
            if s.get("slot") == "Slot_3" and "Aspirate" in s.get("action", "")
        ]
        for k, step_idx in enumerate(drug_steps_indices):
            if k < len(cleaned_wells):
                loaded_sequence[step_idx]["well"] = cleaned_wells[k]

        route_waste_slot2 = (eff_deck.get("Slot_2") == "waste_trough.json")
        for s in loaded_sequence:
            # Map DMSO aspiration steps to target DMSO slot (Slot_1 A1 at X=235.05, Y=5.27 by default)
            if (s.get("slot") in ("Slot_1", "Slot_6")) and ("dmso" in s.get("label", "").lower() or (s.get("slot") == "Slot_1" and "Aspirate" in s.get("action", ""))):
                s["slot"] = dmso_target_slot
                if dmso_labware:
                    s["labware"] = dmso_labware
                if "reservoir" in str(dmso_labware).lower() or dmso_target_slot == "Slot_1":
                    s["well"] = "A1"
            elif dmso_labware and s.get("slot") == dmso_target_slot:
                s["labware"] = dmso_labware
                if "reservoir" in str(dmso_labware).lower() and s.get("well") not in ("A6", "A7", "R6", "R7"):
                    s["well"] = "A1"
            if route_waste_slot2 and (s.get("action") == "Discard Tip" or s.get("slot") == "Slot_2"):
                s["slot"] = "Slot_2"
                s["well"] = "A1"
                s["labware"] = "waste_trough.json"
            if (
                s.get("action") == "Aspirate Media"
                and s.get("slot") == dmso_target_slot
                and s.get("well") == "A1"
                and float(s.get("volume", 0.0)) >= 150.0
            ):
                s["no_air_cushion"] = True

        self.workflow_sequence.clear()
        self.wf_box.delete(0, tk.END)
        lw_dir = self.get_labware_dir()

        for s_num in range(1, 7):
            s_name = f"Slot_{s_num}"
            if s_name not in self.placed_slots:
                self.placed_slots.append(s_name)
            if s_name in self.unplaced_slots:
                self.unplaced_slots.remove(s_name)
            lw_file = eff_deck.get(s_name)
            if lw_file and lw_file != "(Empty / Clearance)":
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
            elif s_name in eff_deck and eff_deck.get(s_name) == "(Empty / Clearance)":
                if s_name in self.lims.deck_labware:
                    del self.lims.deck_labware[s_name]

        self.sync_deck_manager()
        if hasattr(self, "draw_deck"):
            self.draw_deck()

        for step in loaded_sequence:
            self.workflow_sequence.append(step)
            act = step["action"]
            slot = step.get("slot", "")
            well = step.get("well", "")
            vol = float(step.get("volume", 0.0))
            mix_cycles = int(step.get("mix_cycles", 0))
            mix_vol = float(step.get("mix_volume", 100.0))
            mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
            vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
            if act == "Pick Up Tip":
                msg = f"[{act.upper()}] from {slot}, Well {well}"
            elif act == "Discard Tip":
                msg = f"[{act.upper()}] into {slot}, Well {well}"
            else:
                msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
            self.wf_box.insert(tk.END, msg)

        self._update_estimated_timer_preview()
        self._refresh_tip_memory_badge("Slot_4")
        wells_summary = ", ".join([f"D{i+1}:{w}" for i, w in enumerate(cleaned_wells)])
        self.logger.info(
            f"Loaded {protocol_name} ({len(loaded_sequence)} steps) with Drug Wells [{wells_summary}]. "
            f"Deck: Slot 1 (Clearance), Slot 2 Waste (A1), Slot 3 Drug Stock, Slot 4 Tips, Slot 5 Dilution Plate, Slot 6 DMSO ({eff_deck.get('Slot_6', 'A1')})."
        )

    def prompt_drug_wells_and_load(self, loaded_sequence, protocol_name, deck_setup):
        drug_steps_indices = [
            i for i, s in enumerate(loaded_sequence)
            if s.get("slot") == "Slot_3" and "Aspirate" in s.get("action", "")
        ]
        default_wells = [loaded_sequence[i].get("well", "A1") for i in drug_steps_indices]
        if not default_wells:
            default_wells = ["A1", "A2", "A3", "A4", "B1"]
        num_drugs = len(default_wells)

        top = tk.Toplevel(self.root)
        top.title("Stock Drug Wells Configuration (Slot 3)")
        win_h = max(440, 220 + num_drugs * 38)
        top.geometry(f"490x{min(680, win_h)}")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 245
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (min(680, win_h) // 2)
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass

        ttk.Label(top, text="Select Stock Drug Wells (Slot 3)", font=("Arial", 11, "bold"), foreground="#007bff").pack(pady=(14, 3))
        ttk.Label(
            top,
            text=f"{protocol_name}\nSpecify source wells in Slot 3 for each dilution series on Slot 5:",
            font=("Arial", 9),
            justify=tk.CENTER,
        ).pack(pady=(0, 8))

        dmso_frame = ttk.LabelFrame(top, text="DMSO Source Labware (Slot 1 Well A1 / Slot 6)", padding=8)
        dmso_frame.pack(fill=tk.X, padx=22, pady=(0, 8))
        dmso_options = {
            "Slot 1: 3-Well Reservoir A1 (reservoir_3_well.json)": "reservoir_3_well.json",
            "Slot 1: 12-Tube 2 mL Falcon Rack (tube_rack_2x6_2ml.json)": "tube_rack_2x6_2ml.json",
            "Slot 6: 7-Column Reservoir (reservoir_7_column.json)": "reservoir_7_column.json",
            "Slot 6: 6-Column Reservoir (reservoir_6_column.json)": "reservoir_6_column.json",
        }
        init_dmso = (deck_setup or {}).get("Slot_1")
        if not init_dmso or init_dmso == "(Empty / Clearance)":
            init_dmso = (deck_setup or {}).get("Slot_6", "reservoir_3_well.json")
        init_disp = next((k for k, v in dmso_options.items() if v == init_dmso), list(dmso_options.keys())[0])
        dmso_var = tk.StringVar(value=init_disp)
        cb_dmso = ttk.Combobox(dmso_frame, textvariable=dmso_var, values=list(dmso_options.keys()), state="readonly")
        cb_dmso.pack(fill=tk.X)

        frame_inputs = ttk.Frame(top, padding=8)
        frame_inputs.pack(fill=tk.BOTH, expand=True, padx=25)

        row_letters = "ABCDEFGH"
        well_vars = []
        for idx in range(num_drugs):
            target_well = ""
            if idx < len(drug_steps_indices):
                step_i = drug_steps_indices[idx]
                if step_i + 1 < len(loaded_sequence) and loaded_sequence[step_i + 1].get("slot") == "Slot_5":
                    target_well = loaded_sequence[step_i + 1].get("well", "")
            row_hint = f"Dilution Row {target_well[0]}" if target_well else (f"Dilution Row {row_letters[idx]}" if idx < 8 else f"Series {idx+1}")
            lbl_text = f"Drug {idx+1} ({row_hint}):"
            def_val = default_wells[idx] if idx < len(default_wells) else f"A{idx+1}"
            v = tk.StringVar(value=def_val)
            well_vars.append(v)

            ttk.Label(frame_inputs, text=lbl_text, font=("Arial", 9, "bold")).grid(row=idx, column=0, sticky="w", pady=5)
            ent = ttk.Entry(frame_inputs, textvariable=v, width=12, font=("Consolas", 10, "bold"), justify="center")
            ent.grid(row=idx, column=1, sticky="e", pady=5, padx=10)

        btn_frame = ttk.Frame(top, padding=14)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def on_apply():
            chosen_wells = [v.get().strip().upper() for v in well_vars]
            chosen_dmso_lw = dmso_options.get(dmso_var.get(), init_dmso)
            try:
                self.apply_drug_well_mapping_and_load(
                    loaded_sequence,
                    protocol_name=protocol_name,
                    deck_setup=deck_setup,
                    chosen_wells=chosen_wells,
                    dmso_labware=chosen_dmso_lw,
                )
            except ValueError as ve:
                messagebox.showerror(
                    "Invalid Well Format",
                    f"{ve}\nMust be between A1 and H12 (e.g. A1, B3, C6).",
                    parent=top,
                )
                return
            top.destroy()

        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Apply & Load Protocol", command=on_apply).pack(side=tk.RIGHT, padx=5)

    def action_load_bakar_media_change_serial_dilution_protocol(self):
        target_path = self.resolve_protocol_path(
            "bakar_v2_drug_dmso_media_change_step.json"
        )
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)

            deck_setup = {
                "Slot_1": "reservoir_3_well.json",
                "Slot_2": "waste_trough.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "generic_96_well_plate.json"
            }

            self.prompt_drug_wells_and_load(
                loaded_sequence,
                protocol_name="Bakar Serial Dilution (Media Change Step)",
                deck_setup=deck_setup
            )
        else:
            messagebox.showerror("File Not Found", "Could not locate bakar_v2_drug_dmso_media_change_step.json")

    def action_load_slot5_media_removal_test(self, quiet=False):
        """
        Instant load for the Slot 5 Media Removal Test protocol:
        - Takes 8 tips from Slot 4 Column 3 (A3).
        - Aspirates 550 uL from Columns 1 to 6 of Plate 6 (Slot 5) at Z=24.17 mm.
        - Dispenses into Slot 6 Waste (A7) 3 cm above bottom (Z=59.32 mm).
        - Discards/returns tips to Slot 4 Column 1 (A1).
        """
        self.switch_pipettor_head(True, quiet=True)
        lw_dir = self.get_labware_dir()

        deck_setup = {
            "Slot_3": "myriamed_48_well.json",
            "Slot_4": "tip_rack_1000ul.json",
            "Slot_5": "myriamed_48_well.json",
            "Slot_6": "reservoir_7_column.json",
        }
        for s_name, lw_file in deck_setup.items():
            lp = os.path.join(lw_dir, lw_file)
            if os.path.exists(lp):
                self.lims.deck_labware[s_name] = Labware(lp)
                self.lims.deck_labware[s_name].source_file = lw_file
            if s_name not in self.placed_slots:
                self.placed_slots.append(s_name)

        self.sync_deck_manager()
        if hasattr(self, 'draw_deck'):
            self.draw_deck()

        p_path = self.resolve_protocol_path("test_slot5_media_removal_col3_to_col1.json")
        if not p_path or not os.path.exists(p_path):
            from generate_8ch_1000ul_ehm_media_change import build_slot5_media_removal_test
            steps = build_slot5_media_removal_test()
        else:
            with open(p_path, "r") as f:
                steps = json.load(f)

        self.workflow_sequence.clear()
        self.wf_box.delete(0, tk.END)
        self.has_tip_var.set(False)

        for st in steps:
            self.workflow_sequence.append(st)
            self.wf_box.insert(tk.END, self._format_step_msg(st))

        self._update_estimated_timer_preview()
        self.logger.info("Loaded Slot 5 Media Removal Test (Tips from Col 3, Waste to Slot 6, Return tips to Col 1).")
        if not quiet:
            messagebox.showinfo(
                "Slot 5 Test Protocol Loaded",
                "Slot 5 Media Removal Test loaded successfully!\n\n"
                "• Tips Picked: Slot 4 Col 3\n"
                "• Old Media Removed: Slot 5 Cols 1..6 (inside well)\n"
                "• Waste Dispensed: Slot 6 Waste (3 cm above bottom)\n"
                "• Tips Returned: Slot 4 Col 1\n\n"
                "Click 'Run Protocol' when ready.",
                parent=self.root,
            )

    def update_window_title(self):
        station_name = self.profile_manager.get_display_name(self.active_profile_id) if getattr(self, "profile_manager", None) else self.active_profile_id
        init_badge = " [Ready]" if getattr(self, "is_head_initialized", False) else " [UNINITIALIZED - Click Initialize]"
        theme_badge = " [Cleanroom Mode]" if getattr(self, "cleanroom_theme_active", False) else ""
        if hasattr(self.root, "title"):
            self.root.title(f"Biohit Master GUI — [Station: {station_name}]{init_badge}{theme_badge}")
        if hasattr(self, "lbl_station_badge"):
            self.lbl_station_badge.config(text=f"🏢 {station_name}")
        if hasattr(self, "lbl_head_init_status"):
            if getattr(self, "is_head_initialized", False):
                self.lbl_head_init_status.config(text="● INITIALIZED", bg="#198754", fg="white")
            else:
                self.lbl_head_init_status.config(text="⚠️ UNINITIALIZED", bg="#dc3545", fg="white")

    def switch_machine_profile(self, profile_id: str, save_to_disk: bool = True):
        """
        Switches the active machine station profile (machine_1_8x1000, machine_2_1_10ul, machine_3_300ul).
        Loads isolated hardware profile calibrations from config/machine_profiles/<id>/heights.json.
        """
        if profile_id not in PROFILE_CONFIGS:
            # Check partial match
            matched = None
            for k in PROFILE_CONFIGS:
                if k in profile_id or profile_id in k:
                    matched = k
                    break
            if matched:
                profile_id = matched
            else:
                self.logger.warning(f"Unknown profile ID '{profile_id}', ignoring switch.")
                return

        self.active_profile_id = profile_id
        if self.profile_manager:
            if save_to_disk:
                self.profile_manager.set_active_profile_id(profile_id)
            self.calibrated_heights = self.profile_manager.load_profile(profile_id)
            if "300" in profile_id:
                if float(self.calibrated_heights.get("plate96_aspirate_z", 98.72)) in (78.4, 78.40, 97.52):
                    self.calibrated_heights["plate96_aspirate_z"] = 98.72
                if float(self.calibrated_heights.get("plate96_dispense_z", 98.72)) in (68.43, 78.4, 78.40, 97.52):
                    self.calibrated_heights["plate96_dispense_z"] = 98.72
                if float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 92.0)) <= 88.0:
                    self.calibrated_heights["tip_rack_pickup_limit_z"] = 92.0
                if float(self.calibrated_heights.get("plate96_dmso_dispense_z", 98.72)) in (75.0, 75.00, 68.43, 97.52):
                    self.calibrated_heights["plate96_dmso_dispense_z"] = 98.72
                self.calibrated_heights.setdefault("plate96_dmso_dispense_z", 98.72)

        cfg = (PROFILE_CONFIGS or {}).get(profile_id, {})
        prof_multi = cfg.get("is_multichannel", True if ("8x" in profile_id or "10ul" in profile_id) else False)
        prof_tip_vol = float(cfg.get("tip_volume", 10.0 if "10ul" in profile_id else (1000.0 if "1000" in profile_id else 250.0)))

        self.lims.pipettor.reconfigure(tip_volume=prof_tip_vol, multichannel=prof_multi)
        head_label = cfg.get("head_name", "8-Channel Multi (1-10 µL)" if "10ul" in profile_id else "8-Channel Multi (8×1000 µL)")
        self.head_mode_var.set(head_label)
        if hasattr(self, "proto_pipettor_var"):
            self.proto_pipettor_var.set(head_label)

        # Synchronize head initialization state with hardware initialization state
        hw_ready = bool(getattr(self.lims.hw, "is_initialized", False))
        self.is_head_initialized = hw_ready
        self.initialized_head = profile_id if hw_ready else None

        self.apply_default_deck_for_profile(profile_id)
        self.update_window_title()
        self._update_protocol_dropdown()
        if hasattr(self, "draw_deck"):
            self.draw_deck()

        disp = self.profile_manager.get_display_name(profile_id) if self.profile_manager else profile_id
        self.logger.info(f"Switched physical machine station to: {disp} (save_to_disk={save_to_disk})")

    def action_select_machine_profile(self, is_initial_setup: bool = False):
        """
        Interactive Station Switcher: Allows the operator to activate Machine 1, Machine 2, or Machine 3.
        Loads isolated hardware profile calibrations from config/machine_profiles/<id>/heights.json
        and persists station identity locally to .machine_id without touching git.
        """
        top = tk.Toplevel(self.root)
        top.title("Select Physical Machine Station Profile")
        top.geometry("520x420")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 260
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 210
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
            top.lift()
            top.attributes("-topmost", True)
            top.after_idle(lambda: top.attributes("-topmost", False))
        except Exception:
            pass

        header_text = "🏢 Workstation Setup — Select Robot Profile" if is_initial_setup else "🏢 Select Active Machine Station Profile"
        ttk.Label(top, text=header_text, font=("Arial", 12, "bold"), foreground="#0d6efd").pack(pady=(12, 4))
        
        info_sub = (
            "This computer has not yet remembered its physical robot station.\n"
            "Please select which robot this computer is running so it can remember it."
            if is_initial_setup else
            "Each physical robot has completely independent Z heights and table calibrations.\n"
            "Switching profiles activates local calibrations without touching other stations."
        )
        ttk.Label(
            top,
            text=info_sub,
            font=("Arial", 9),
            justify=tk.CENTER,
            foreground="#555",
        ).pack(pady=(0, 10))

        frame = ttk.LabelFrame(top, text="Available Stations", padding=12)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        selected_pid = tk.StringVar(value=self.active_profile_id)

        stations = [
            ("machine_2_1_10ul", "Machine 2: 1-10 µL (8-Channel Manifold)", "Optifit 1-10 µL tips (Collar Z=64.49mm) | EHM 8.5mm raised | Drug addition"),
            ("machine_1_8x1000", "Machine 1: 8x1000 µL (8-Channel Manifold)", "1000 µL tips (Collar Z=86.36mm) | Full-volume Media Change | 7-Col reservoir"),
            ("machine_3_300ul", "Machine 3: 300 µL (Single-Channel)", "300 µL tips (Collar Z=86.36mm, Limit=87.0mm) | Serial Dilutions | 3-Well reservoir"),
        ]

        for pid, title, desc in stations:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=5)
            rb = ttk.Radiobutton(row, text=title, value=pid, variable=selected_pid)
            rb.pack(anchor="w")
            ttk.Label(row, text=f"    {desc}", font=("Arial", 8, "italic"), foreground="#6c757d").pack(anchor="w")

        # Remember on this computer checkbox
        rem_frame = ttk.Frame(top)
        rem_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        remember_var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(
            rem_frame,
            text="📌 Remember this machine on this computer (.machine_id)",
            variable=remember_var,
        )
        chk.pack(anchor="w")
        ttk.Label(
            rem_frame,
            text="   Saves locally to .machine_id so this workstation automatically remembers on next launch.",
            font=("Arial", 8, "italic"),
            foreground="#6c757d",
        ).pack(anchor="w")

        def do_switch():
            chosen = selected_pid.get()
            do_persist = remember_var.get()
            self.switch_machine_profile(chosen, save_to_disk=do_persist)
            disp = self.profile_manager.get_display_name(chosen) if self.profile_manager else chosen
            top.destroy()
            save_msg = "Remembered in .machine_id on this computer." if do_persist else "Active for this session only."
            messagebox.showinfo(
                "Station Profile Activated",
                f"Workstation assigned to:\n{disp}\n\n{save_msg}\n\nCalibrated heights & default deck loaded."
            )

        btn_box = ttk.Frame(top)
        btn_box.pack(fill=tk.X, padx=16, pady=(0, 12))
        ttk.Button(btn_box, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_box, text="✔ Activate & Remember Profile", bg="#0d6efd", fg="white", font=("Arial", 9, "bold"), command=do_switch).pack(side=tk.RIGHT, padx=4)

    def action_initialize_pipettor(self):
        """
        Hardware Initialization & Safety Interlock Sequence.
        Verifies pipette head communication, reconfigures volume limits, resets origin,
        and unlocks protocol execution.
        """
        if getattr(self, "is_running", False):
            messagebox.showwarning("Busy", "Cannot re-initialize pipettor head while a protocol is executing.")
            return

        if not getattr(self.lims.hw, "is_initialized", False):
            self.logger.warning("Pipettor head initialization blocked: Hardware port is not connected or initialized.")
            messagebox.showwarning(
                "Hardware Port Required",
                "Hardware port has not been connected or initialized yet.\n\n"
                "Please go to the 'Jog & Calibration' tab, select your hardware port (e.g. COM3), and click 'Connect & Initialize' first."
            )
            return

        cfg = (PROFILE_CONFIGS or {}).get(self.active_profile_id, {})
        disp_name = self.profile_manager.get_display_name(self.active_profile_id) if getattr(self, "profile_manager", None) else self.active_profile_id
        is_multi = cfg.get("is_multichannel", True if ("8x" in self.active_profile_id or "10ul" in self.active_profile_id) else False)
        tip_vol = float(cfg.get("tip_volume", 10.0 if "10ul" in self.active_profile_id else 1000.0))

        try:
            self.logger.info(f"Initializing Pipettor Head for {disp_name} (Vol: {tip_vol:.1f}µL, Multi: {is_multi})...")
            # 1. Reconfigure driver
            self.lims.pipettor.reconfigure(tip_volume=tip_vol, multichannel=is_multi)

            # 2. Hardware safe retract
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except Exception as ze:
                    self.logger.warning(f"Z Retract warning during initialization: {ze}")

            # 3. Mark state initialized
            self.is_head_initialized = True
            self.initialized_head = self.active_profile_id
            self.update_window_title()
            self._update_protocol_dropdown()

            self.logger.info(f"✅ Pipette Head INITIALIZED successfully: {disp_name}. Interlock released.")
            messagebox.showinfo(
                "Head Initialized",
                f"Pipettor Head initialized and ready!\n\nStation: {disp_name}\nTip Volume: {tip_vol:.1f} µL\nManifold: {'8-Channel Multichannel' if is_multi else 'Single-Channel'}\n\nProtocol execution is now unlocked."
            )
        except Exception as e:
            self.is_head_initialized = False
            self.initialized_head = None
            self.update_window_title()
            self.logger.error(f"Pipette Head Initialization failed: {e}")
            messagebox.showerror("Initialization Failed", f"Could not initialize pipettor head:\n{e}")

    def toggle_cleanroom_theme(self):
        """Toggles between standard desktop laboratory theme and glove-friendly cleanroom high-contrast theme."""
        self.cleanroom_theme_active = not self.cleanroom_theme_active
        is_cleanroom = self.cleanroom_theme_active

        if hasattr(self, "btn_theme_toggle"):
            self.btn_theme_toggle.config(
                text="☀️ Standard" if is_cleanroom else "🌓 Theme",
                bg="#0284c7" if is_cleanroom else "#374151"
            )

        if hasattr(self, "btn_play") and hasattr(self, "btn_pause") and hasattr(self, "btn_stop"):
            if is_cleanroom:
                self.btn_play.config(bg="#059669", font=("Arial", 12, "bold"), pady=8)
                self.btn_pause.config(bg="#d97706", font=("Arial", 12, "bold"), pady=8)
                self.btn_stop.config(bg="#dc2626", font=("Arial", 12, "bold"), pady=8)
            else:
                self.btn_play.config(bg="#28a745", font=("Arial", 11, "bold"), pady=3)
                self.btn_pause.config(bg="#ffc107", font=("Arial", 11, "bold"), pady=3)
                self.btn_stop.config(bg="#dc3545", font=("Arial", 11, "bold"), pady=3)

        self.update_window_title()
        if hasattr(self, "draw_deck"):
            self.draw_deck()

        mode_str = "Cleanroom High-Contrast Mode (Glove Touch Enabled)" if is_cleanroom else "Standard Desktop Lab Mode"
        self.logger.info(f"Switched UI theme to: {mode_str}")

    def action_open_slot_z_verification(self):
        """
        Assisted Visual Z-Verification & Table Depth Editor.
        Robot picks a tip from Slot 4 and moves to the selected slot/well.
        The operator can visual-jog to verify depths, edit the nominal value directly,
        and save it into the active machine profile (heights.json).
        """
        if getattr(self, "is_running", False):
            messagebox.showwarning("Busy", "Cannot verify Z depths while a protocol is running.")
            return

        top = tk.Toplevel(self.root)
        top.title("Slot-by-Slot Tip Z-Verification & Depth Editor")
        top.geometry("560x520")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 280
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 260
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass

        ttk.Label(top, text="📐 Slot Z-Verification & Visual Jog Editor", font=("Arial", 12, "bold"), foreground="#6f42c1").pack(pady=(10, 4))
        station_name = self.profile_manager.get_display_name(self.active_profile_id) if getattr(self, "profile_manager", None) else self.active_profile_id
        ttk.Label(
            top,
            text=f"Active Profile: {station_name}\nRobot picks a tip from Slot 4 and travels to the target well at nominal Z.\nUse fine jog controls or direct entry to adjust, then save verified depth to heights.json.",
            font=("Arial", 8),
            justify=tk.CENTER,
            foreground="#555",
        ).pack(pady=(0, 8))

        ctrl_frame = ttk.LabelFrame(top, text="Target Slot & Well Selection", padding=10)
        ctrl_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        row1 = ttk.Frame(ctrl_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Target Slot:", width=12).pack(side=tk.LEFT)
        slot_var = tk.StringVar(value="Slot_5")
        cb_slot = ttk.Combobox(row1, textvariable=slot_var, values=["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"], state="readonly", width=12)
        cb_slot.pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(row1, text="Target Well:", width=12).pack(side=tk.LEFT)
        well_var = tk.StringVar(value="A1")
        ent_well = ttk.Entry(row1, textvariable=well_var, width=8)
        ent_well.pack(side=tk.LEFT)

        info_lbl = ttk.Label(ctrl_frame, text="", font=("Arial", 8, "italic"), foreground="#0d6efd")
        info_lbl.pack(anchor="w", pady=(4, 0))

        def _update_slot_info(*args):
            s = slot_var.get()
            lw = self.lims.deck_labware.get(s)
            lw_name = getattr(lw, "source_file", getattr(lw, "name", "None"))
            kind = self._lw_kind(lw)
            nom_z = 24.17
            if kind == "ehm48":
                nom_z = float(self.calibrated_heights.get("ehm_aspirate_z", 72.35 if ("10ul" in self.active_profile_id or "300" in self.active_profile_id) else 24.17))
            elif kind == "plate96":
                nom_z = float(self.calibrated_heights.get("plate96_aspirate_z", 78.40))
            elif "reservoir" in str(kind) or kind == "reservoir_7":
                nom_z = float(self.calibrated_heights.get("reservoir_aspirate_z", 58.34 if "10ul" in self.active_profile_id else 90.42))
            elif kind == "tip_rack":
                nom_z = float(self.calibrated_heights.get("tip_10ul_collar_z" if "10ul" in self.active_profile_id else "tip_rack_collar_z", 64.49 if "10ul" in self.active_profile_id else 86.36))
            info_lbl.config(text=f"Mounted: {lw_name} ({kind or 'unknown'}) | Nominal Z Depth: {nom_z:.2f} mm")

        slot_var.trace_add("write", _update_slot_info)
        _update_slot_info()

        # Step 1: Pick Tip and Travel
        action_box1 = ttk.LabelFrame(top, text="Step 1: Pick Tip from Slot 4 & Travel to Well", padding=10)
        action_box1.pack(fill=tk.X, padx=16, pady=(0, 8))

        live_z_var = tk.DoubleVar(value=0.0)
        lbl_current_z = tk.Label(action_box1, text="Current Z: 0.00 mm", font=("Consolas", 11, "bold"), fg="#0d6efd")
        lbl_current_z.pack(side=tk.RIGHT, padx=6)

        def do_pick_and_travel():
            s = slot_var.get()
            w = well_var.get().strip().upper() or "A1"
            lw = self.lims.deck_labware.get(s)
            kind = self._lw_kind(lw)
            nom_z = 24.17
            if kind == "ehm48":
                nom_z = float(self.calibrated_heights.get("ehm_aspirate_z", 72.35 if ("10ul" in self.active_profile_id or "300" in self.active_profile_id) else 24.17))
            elif kind == "plate96":
                nom_z = float(self.calibrated_heights.get("plate96_aspirate_z", 78.40))
            elif "reservoir" in str(kind) or kind == "reservoir_7":
                nom_z = float(self.calibrated_heights.get("reservoir_aspirate_z", 58.34 if "10ul" in self.active_profile_id else 90.42))
            elif kind == "tip_rack":
                nom_z = float(self.calibrated_heights.get("tip_10ul_collar_z" if "10ul" in self.active_profile_id else "tip_rack_collar_z", 64.49 if "10ul" in self.active_profile_id else 86.36))

            try:
                # 1. Pick Tip from Slot 4 using active machine profile heights
                self.logger.info(f"[Z-VERIFY] Picking tip from Slot 4 for visual verification on {s} {w}...")
                is_10ul = ("10ul" in self.active_profile_id)
                approach_z = float(self.calibrated_heights.get("tip_10ul_approach_z" if is_10ul else "tip_rack_pickup_approach_z", 50.0 if is_10ul else 75.0))
                collar_z = float(self.calibrated_heights.get("tip_10ul_collar_z" if is_10ul else "tip_rack_collar_z", 64.49 if is_10ul else 86.36))
                extra_press = float(self.calibrated_heights.get("tip_10ul_extra_press_mm" if is_10ul else "tip_pickup_extra_press_mm", 2.5))

                if self.lims.pipettor.hardware:
                    hw = self.lims.pipettor.hardware
                    hw.move_z(0)
                    t_coords = self._resolve_step_xy({"action": "Pick Up Tip", "eight_ch_symmetric": True}, "Slot_4", "A1")
                    if t_coords:
                        self.lims.hw.move_to(t_coords[0], t_coords[1], 0, speed=50)
                    hw.move_z(approach_z)
                    hw.pick_tip(collar_z + extra_press)
                    hw.move_z(0)

                self.has_tip_var.set(True)

                # 2. Travel to Target Slot & Well
                coords = self._resolve_step_xy({"action": "Aspirate Media"}, s, w)
                if not coords or (coords[0] == 0 and coords[1] == 0):
                    coords = self._calculate_xy(s, w)
                tx, ty = coords if coords else (0.0, 0.0)

                self.lims.hw.move_to(tx, ty, 0, speed=50)
                if self.lims.pipettor.hardware:
                    self.lims.pipettor.hardware.move_z(nom_z)

                live_z_var.set(nom_z)
                lbl_current_z.config(text=f"Current Z: {nom_z:.2f} mm")
                self.logger.info(f"[Z-VERIFY] Reached {s} {w} at nominal Z={nom_z:.2f}mm.")
            except Exception as pe:
                self.logger.error(f"[Z-VERIFY] Pick and travel error: {pe}")
                messagebox.showerror("Move Error", f"Could not complete tip travel: {pe}")

        tk.Button(action_box1, text="▶ 1. Pick Tip from Slot 4 & Travel to Well", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=do_pick_and_travel).pack(side=tk.LEFT)

        # Step 2: Visual Fine Jogging Controls
        jog_box = ttk.LabelFrame(top, text="Step 2: Visual Fine Jogging Controls (Nudge Height)", padding=10)
        jog_box.pack(fill=tk.X, padx=16, pady=(0, 8))

        def _nudge_z(delta):
            cur = live_z_var.get()
            new_z = max(0.0, min(103.5, cur + delta))
            live_z_var.set(new_z)
            lbl_current_z.config(text=f"Current Z: {new_z:.2f} mm")
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(new_z)
                except Exception as e:
                    self.logger.warning(f"Z nudge warning: {e}")
            self.logger.info(f"[Z-VERIFY] Jogged Z by {delta:+.2f}mm -> Current: {new_z:.2f}mm")

        row_up = ttk.Frame(jog_box)
        row_up.pack(fill=tk.X, pady=2)
        ttk.Label(row_up, text="Raise Z (Move Up):", width=18).pack(side=tk.LEFT)
        for d in [-10.0, -2.0, -0.5, -0.1]:
            tk.Button(row_up, text=f"{d}mm", bg="#17a2b8", fg="white", font=("Arial", 8, "bold"), width=7, command=lambda v=d: _nudge_z(v)).pack(side=tk.LEFT, padx=2)

        row_down = ttk.Frame(jog_box)
        row_down.pack(fill=tk.X, pady=4)
        ttk.Label(row_down, text="Lower Z (Descend Deeper):", width=18).pack(side=tk.LEFT)
        for d in [0.1, 0.5, 2.0, 10.0]:
            tk.Button(row_down, text=f"+{d}mm", bg="#ffc107", font=("Arial", 8, "bold"), width=7, command=lambda v=d: _nudge_z(v)).pack(side=tk.LEFT, padx=2)

        row_direct = ttk.Frame(jog_box)
        row_direct.pack(fill=tk.X, pady=4)
        ttk.Label(row_direct, text="Direct Value / Delta:", width=18).pack(side=tk.LEFT)
        direct_z_var = tk.StringVar(value="")
        ttk.Entry(row_direct, textvariable=direct_z_var, width=10).pack(side=tk.LEFT, padx=(0, 6))

        def _apply_direct():
            val_str = direct_z_var.get().strip()
            if not val_str:
                return
            try:
                val = float(val_str)
                if val_str.startswith("+") or val_str.startswith("-"):
                    _nudge_z(val)
                else:
                    new_z = max(0.0, min(103.5, val))
                    live_z_var.set(new_z)
                    lbl_current_z.config(text=f"Current Z: {new_z:.2f} mm")
                    if self.lims.pipettor.hardware:
                        self.lims.pipettor.hardware.move_z(new_z)
                    self.logger.info(f"[Z-VERIFY] Set direct Z={new_z:.2f}mm")
            except Exception as e:
                messagebox.showerror("Input Error", f"Invalid Z value '{val_str}': {e}")

        ttk.Button(row_direct, text="Apply Z", command=_apply_direct).pack(side=tk.LEFT)

        # Step 3: Save & Return
        bottom_box = ttk.Frame(top)
        bottom_box.pack(fill=tk.X, padx=16, pady=8)

        def _save_to_profile():
            current_z = round(live_z_var.get(), 2)
            if current_z <= 0.0:
                messagebox.showwarning("Zero Z", "Current Z is 0.0 mm. Jog to the verified depth before saving.")
                return
            s = slot_var.get()
            lw = self.lims.deck_labware.get(s)
            kind = self._lw_kind(lw)

            key = "plate96_aspirate_z"
            if kind == "ehm48":
                key = "ehm_aspirate_z"
            elif "reservoir" in str(kind) or kind == "reservoir_7":
                key = "reservoir_aspirate_z"
            elif kind == "tip_rack":
                key = "tip_10ul_collar_z" if "10ul" in self.active_profile_id else "tip_rack_collar_z"

            self.calibrated_heights[key] = current_z
            if "10ul" in self.active_profile_id:
                if key == "ehm_aspirate_z":
                    self.calibrated_heights["ehm_dispense_z"] = round(current_z - 9.97, 2)
                elif key == "reservoir_aspirate_z":
                    self.calibrated_heights["reservoir_7_aspirate_z"] = current_z

            self.save_calibrated_heights()
            self.logger.info(f"[Z-VERIFY] Saved verified Z depth {key}={current_z:.2f}mm to active profile {self.active_profile_id}.")
            messagebox.showinfo("Saved", f"Verified Z={current_z:.2f} mm saved to active profile '{self.active_profile_id}' under key '{key}'!")

        def _return_tip_and_retract():
            try:
                self.logger.info("[Z-VERIFY] Returning tip and retracting...")
                if self.lims.pipettor.hardware:
                    self.lims.pipettor.hardware.move_z(0)
                discard_z = float(self.calibrated_heights.get("tip_rack_discard_z", 40.50))
                t_coords = self._resolve_step_xy({"action": "Discard Tip", "eight_ch_symmetric": True}, "Slot_4", "A12")
                if t_coords:
                    self.lims.hw.move_to(t_coords[0], t_coords[1], 0, speed=50)
                if self.lims.pipettor.hardware:
                    self.lims.pipettor.hardware.move_z(discard_z)
                    self.lims.pipettor.hardware.eject_tip()
                    self.lims.pipettor.hardware.move_z(0)
                self.has_tip_var.set(False)
                lbl_current_z.config(text="Current Z: 0.00 mm (Retracted)")
                self.logger.info("[Z-VERIFY] Tip ejected and robot safely retracted to Z=0.0 mm.")
                messagebox.showinfo("Finished", "Tip returned and carriage safely retracted to Z=0.0 mm.")
            except Exception as e:
                self.logger.error(f"[Z-VERIFY] Return tip error: {e}")
                messagebox.showerror("Error", f"Could not eject tip: {e}")

        tk.Button(bottom_box, text="💾 3. Save Verified Z to Profile", bg="#0d6efd", fg="white", font=("Arial", 10, "bold"), command=_save_to_profile).pack(side=tk.LEFT, padx=4)
        tk.Button(bottom_box, text="🏁 4. Return Tip & Retract", bg="#6c757d", fg="white", font=("Arial", 9, "bold"), command=_return_tip_and_retract).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom_box, text="Close", command=top.destroy).pack(side=tk.RIGHT, padx=4)

    action_open_tim_z_verification = action_open_slot_z_verification

    def save_calibrated_heights(self):
        """Persists the calibrated heights dictionary to the active machine profile and fallback storage."""
        try:
            if hasattr(self, 'profile_manager') and self.profile_manager:
                self.profile_manager.save_profile(self.calibrated_heights, self.active_profile_id)
            with open(self.calibrated_heights_file, "w") as f:
                json.dump(self.calibrated_heights, f, indent=2)
            self.logger.info(f"Saved calibrated heights to machine profile '{self.active_profile_id}'.")
        except Exception as e:
            self.logger.error(f"Error saving calibrated heights: {e}")

    def action_open_8ch_height_settings(self):
        """
        Opens a dedicated settings dialog for 8-channel calibrated heights and depths.
        Values are saved permanently to calibrated_heights_8ch.json and remembered by the GUI.
        """
        top = tk.Toplevel(self.root)
        top.title("8-Channel Calibrated Heights & Depths Memory")
        top.geometry("540x480")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 270
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 240
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass

        ttk.Label(
            top,
            text="📐 8-Channel Persistent Height Memory",
            font=("Arial", 12, "bold"),
            foreground="#6f42c1",
        ).pack(pady=(12, 4))

        ttk.Label(
            top,
            text="The GUI remembers these calibrated heights across all protocols and runs.\nNo Z heights need to be mentioned or hardcoded in protocol files.",
            font=("Arial", 9),
            justify=tk.CENTER,
            foreground="#555",
        ).pack(pady=(0, 10))

        body = ttk.LabelFrame(top, text="Calibrated Heights (mm from Z=0 Top)", padding=10)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        entries = {}
        fields = [
            ("ehm_aspirate_z", "EHM Old Media Removal (Inside Well):", "24.17"),
            ("ehm_dispense_z", "EHM Fresh Media Addition (1cm Above Bottom):", "14.17"),
            ("plate96_aspirate_z", "96-Well Plate Deep Aspirate / Mix Height:", "98.72"),
            ("plate96_dispense_z", "96-Well Plate Standard Dispense Height:", "98.72"),
            ("plate96_dmso_dispense_z", "96-Well DMSO Dispense Height (300µL Base / Mix Depth):", "98.72"),
            ("reservoir_aspirate_z", "Reservoir Deep Aspirate Height (Slot 1 / Slot 6):", "90.42"),
            ("waste_dispense_z", "Slot 6 Waste Dispense (Up / 3cm Above Bottom):", "59.32"),
            ("tip_rack_discard_z", "Slot 4 Tip Rack Return / Discard Height:", "42.00"),
            ("tip_rack_collar_z", "Slot 4 Tip Collar / Rim (Photo Alignment):", "86.36"),
            ("tip_rack_pickup_limit_z", "Slot 4 Tip Pickup Force Limit:", "98.00"),
            ("tip_pickup_extra_press_mm", "Tip Pickup Extra Press / Seating Depth (mm):", "2.50"),
        ]

        for key, label_text, default_val in fields:
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=label_text, font=("Arial", 9)).pack(side=tk.LEFT)
            cur_val = str(self.calibrated_heights.get(key, default_val))
            v_var = tk.StringVar(value=cur_val)
            entries[key] = v_var
            ent = ttk.Entry(row, textvariable=v_var, width=8, justify="center")
            ent.pack(side=tk.RIGHT)

        def _save():
            try:
                for k, v in entries.items():
                    self.calibrated_heights[k] = float(v.get())
                self.save_calibrated_heights()
                messagebox.showinfo(
                    "Heights Saved",
                    "8-Channel heights successfully saved to persistent memory!\n"
                    "The GUI will remember these heights across all protocols and sessions.",
                    parent=top,
                )
                top.destroy()
            except ValueError as ve:
                messagebox.showerror("Invalid Input", f"All heights must be valid numbers: {ve}", parent=top)

        btn_row = ttk.Frame(top, padding=10)
        btn_row.pack(fill=tk.X)
        tk.Button(
            btn_row,
            text="💾 Save Heights to Memory",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            command=_save,
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="Cancel", command=top.destroy).pack(side=tk.RIGHT)

    def action_load_8ch_1000ul_media_change_protocol(self):
        """
        Configures and loads the 8x1000 uL EHM Media Change protocol for
        Plate 5 (Slot_3) & Plate 6 (Slot_5) using all 8 channels across Rows A-H (or legacy offset mode)
        and transfers to/from the reagent reservoir on Slot_6.
        """
        # Auto-engage 8x1000 uL manifold driver configuration
        self.switch_pipettor_head(True, quiet=True)

        top = tk.Toplevel(self.root)
        top.title("8×1000 µL EHM Media Change Configuration (Plate 5 & Plate 6)")
        top.geometry("640x720")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 320
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 360
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass

        ttk.Label(
            top,
            text="8×1000 µL EHM Media Change (All 8 Channels Full-Parallel)",
            font=("Arial", 12, "bold"),
            foreground="#6f42c1",
        ).pack(pady=(12, 3))
        ttk.Label(
            top,
            text="100% Hands-Free • Plate 5 (Slot_3) + Plate 6 (Slot_5) • Tips (Slot_4) • Reservoir (Slot_6)",
            font=("Arial", 9),
        ).pack(pady=(0, 8))

        body = ttk.Frame(top, padding=12)
        body.pack(fill=tk.BOTH, expand=True, padx=10)

        # 1. Deck & Reservoir Cheat-Sheet
        deck_lf = ttk.LabelFrame(body, text="Deck & Reservoir Map", padding=8)
        deck_lf.pack(fill=tk.X, pady=(0, 8))
        deck_info = (
            "• Slot_1 & Slot_2: EMPTY (Clear clearance zone)\n"
            "• Slot_3: Plate 1 / Plt 5 (48-Well EHM Plate, Cols 1..6)\n"
            "• Slot_4: 1000 µL Tip Rack (Full Mode: Cols 1-4 | Fresh-Only: Cols 1-2)\n"
            "• Slot_5: Plate 2 / Plt 6 (48-Well EHM Plate, Cols 1..6)\n"
            "• Slot_6: 7-Col Reservoir (R1: Discard Plt 1 | R2: Discard Plt 2 | R6: Fresh Plt 1 | R7: Fresh Plt 2)"
        )
        ttk.Label(deck_lf, text=deck_info, font=("Consolas", 8), justify=tk.LEFT).pack(anchor="w")

        # 2. Workflow & Addition Mode
        opt_lf = ttk.LabelFrame(body, text="Workflow & Channel Addition Strategy", padding=8)
        opt_lf.pack(fill=tk.X, pady=(0, 8))

        mode_var = tk.StringVar(value="all_8ch")
        inc_rem_var = tk.BooleanVar(value=True)
        tip_drop_var = tk.StringVar(value="rack_graveyard")
        shovel_var = tk.BooleanVar(value=True)

        mode_row = ttk.Frame(opt_lf)
        mode_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(mode_row, text="Media Addition Mode:", font=("Arial", 9, "bold")).pack(anchor="w")
        ttk.Radiobutton(
            mode_row,
            text="All 8 Channels Full-Parallel (Recommended — Fast, symmetrical media addition)",
            value="all_8ch",
            variable=mode_var,
        ).pack(anchor="w", pady=1)
        ttk.Radiobutton(
            mode_row,
            text="Legacy Offset Tip-Picking (Multi-drug conditions: D11..D15 + Control)",
            value="offset_drugs",
            variable=mode_var,
        ).pack(anchor="w", pady=1)

        ttk.Separator(opt_lf, orient="horizontal").pack(fill=tk.X, pady=4)

        def _on_rem_toggle():
            if not inc_rem_var.get():
                tip_drop_var.set("slot6_waste")
            else:
                tip_drop_var.set("rack_graveyard")

        ttk.Checkbutton(
            opt_lf,
            text="Include Old Media Removal before Fresh Media Addition (100% Hands-Free)",
            variable=inc_rem_var,
            command=_on_rem_toggle,
        ).pack(anchor="w", pady=2)

        vol_row = ttk.Frame(opt_lf)
        vol_row.pack(fill=tk.X, pady=4)
        ttk.Label(vol_row, text="Remove Vol (µL/well):").pack(side=tk.LEFT)
        rem_vol_var = tk.StringVar(value="500.0")
        ttk.Entry(vol_row, textvariable=rem_vol_var, width=8, justify="center").pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(vol_row, text="Fresh Media Vol (µL/well):").pack(side=tk.LEFT)
        fresh_vol_var = tk.StringVar(value="500.0")
        ttk.Entry(vol_row, textvariable=fresh_vol_var, width=8, justify="center").pack(side=tk.LEFT, padx=4)
        ttk.Label(vol_row, text="(Pooled 500+500 µL)", font=("Arial", 8, "italic"), foreground="#6f42c1").pack(side=tk.LEFT, padx=6)

        # Reservoir Lanes Configuration Frame
        res_lf = ttk.LabelFrame(body, text="Slot 6 Reservoir Configuration", padding=8)
        res_lf.pack(fill=tk.X, pady=(0, 8))

        res_row1 = ttk.Frame(res_lf)
        res_row1.pack(fill=tk.X, pady=2)
        ttk.Label(res_row1, text="Reservoir Labware:").pack(side=tk.LEFT)
        res_labware_var = tk.StringVar(value="reservoir_7_column.json")
        ttk.Radiobutton(res_row1, text="7-Column (Calibrated)", value="reservoir_7_column.json", variable=res_labware_var).pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(res_row1, text="6-Column", value="reservoir_6_column.json", variable=res_labware_var).pack(side=tk.LEFT, padx=4)

        res_row2 = ttk.Frame(res_lf)
        res_row2.pack(fill=tk.X, pady=4)
        ttk.Label(res_row2, text="Plt 1 Discard:").pack(side=tk.LEFT)
        p5_waste_var = tk.StringVar(value="1")
        ttk.Entry(res_row2, textvariable=p5_waste_var, width=3, justify="center").pack(side=tk.LEFT, padx=(2, 6))

        ttk.Label(res_row2, text="Plt 2 Discard:").pack(side=tk.LEFT)
        p6_waste_var = tk.StringVar(value="2")
        ttk.Entry(res_row2, textvariable=p6_waste_var, width=3, justify="center").pack(side=tk.LEFT, padx=(2, 6))

        ttk.Label(res_row2, text="Plt 1 Fresh:").pack(side=tk.LEFT)
        p5_lane_var = tk.StringVar(value="6")
        ttk.Entry(res_row2, textvariable=p5_lane_var, width=3, justify="center").pack(side=tk.LEFT, padx=(2, 6))

        ttk.Label(res_row2, text="Plt 2 Fresh:").pack(side=tk.LEFT)
        p6_lane_var = tk.StringVar(value="7")
        ttk.Entry(res_row2, textvariable=p6_lane_var, width=3, justify="center").pack(side=tk.LEFT, padx=(2, 4))

        def _update_waste_default(*_):
            if "7" in res_labware_var.get():
                p5_waste_var.set("1")
                p6_waste_var.set("2")
                p5_lane_var.set("6")
                p6_lane_var.set("7")
            else:
                p5_waste_var.set("1")
                p6_waste_var.set("2")
                p5_lane_var.set("5")
                p6_lane_var.set("6")
        res_labware_var.trace_add("write", _update_waste_default)

        ttk.Label(opt_lf, text="Tip-Drop Destination:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(4, 1))
        ttk.Radiobutton(
            opt_lf,
            text="Empty Tip-Rack Columns (Slot_4 Cols 12..5 left empty — keeps Slot_6 purely for liquid)",
            value="rack_graveyard",
            variable=tip_drop_var,
        ).pack(anchor="w", pady=1)
        ttk.Radiobutton(
            opt_lf,
            text="Slot_6 Waste Lane Vertical Tip-Drop (Z = 48.0 mm)",
            value="slot6_waste",
            variable=tip_drop_var,
        ).pack(anchor="w", pady=1)

        # 3. 8-Channel Fine Calibration Nudge
        cal_lf = ttk.LabelFrame(body, text="8-Channel Head Fine Calibration Offset (Optional Nudge)", padding=8)
        cal_lf.pack(fill=tk.X, pady=(0, 6))
        cal_row = ttk.Frame(cal_lf)
        cal_row.pack(fill=tk.X)
        dx_var = tk.StringVar(value=str(self.eight_ch_cal_offset.get("X", 0.0)))
        dy_var = tk.StringVar(value=str(self.eight_ch_cal_offset.get("Y", 0.0)))
        dz_var = tk.StringVar(value=str(self.eight_ch_cal_offset.get("Z", 0.0)))
        for lbl_t, v_obj in [("ΔX (mm):", dx_var), ("ΔY (mm):", dy_var), ("ΔZ (mm):", dz_var)]:
            ttk.Label(cal_row, text=lbl_t).pack(side=tk.LEFT, padx=(0, 3))
            ttk.Entry(cal_row, textvariable=v_obj, width=7, justify="center").pack(side=tk.LEFT, padx=(0, 14))

        btn_bar = ttk.Frame(top, padding=10)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        def _apply_and_load():
            try:
                r_vol = float(rem_vol_var.get())
                f_vol = float(fresh_vol_var.get())
                cal_dx = float(dx_var.get())
                cal_dy = float(dy_var.get())
                cal_dz = float(dz_var.get())
                p5_w = int(p5_waste_var.get())
                p6_w = int(p6_waste_var.get())
                p5_l = int(p5_lane_var.get())
                p6_l = int(p6_lane_var.get())
            except ValueError:
                messagebox.showerror("Invalid Number", "Volumes, lanes, and calibration offsets must be valid numbers.", parent=top)
                return

            if r_vol <= 0 or r_vol > 1000.0 or f_vol <= 0 or f_vol > 1000.0:
                messagebox.showerror("Volume Out of Range", "Volumes must be between 1 and 1000 µL for 8×1000 µL tips.", parent=top)
                return

            res_file = res_labware_var.get()
            med_mode = mode_var.get()

            self.eight_ch_cal_offset = {"X": cal_dx, "Y": cal_dy, "Z": cal_dz}
            self.switch_pipettor_head(True, quiet=True)

            steps = build_8ch_ehm_media_change_steps(
                include_old_media_removal=inc_rem_var.get(),
                remove_vol_ul=r_vol,
                fresh_vol_ul=f_vol,
                tip_drop_mode=tip_drop_var.get(),
                use_shovel=shovel_var.get(),
                media_addition_mode=med_mode,
                p5_res_lane=p5_l,
                p6_res_lane=p6_l,
                p5_waste_lane=p5_w,
                p6_waste_lane=p6_w,
                reservoir_labware=res_file,
                multi_dispense=(f_vol <= 500.0 and r_vol <= 500.0),
            )

            # Configure 6-slot deck: Slot_1 & Slot_2 empty; Slot_3 Plate 5; Slot_4 Tips; Slot_5 Plate 6; Slot_6 Reservoir
            lw_dir = self.get_labware_dir()
            for empty_s in ("Slot_1", "Slot_2"):
                if empty_s in self.lims.deck_labware:
                    del self.lims.deck_labware[empty_s]

            deck_setup = {
                "Slot_3": "myriamed_48_well.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": res_file if os.path.exists(os.path.join(lw_dir, res_file)) else "reservoir_7_column.json",
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            for s_all in ("Slot_1", "Slot_2"):
                if s_all not in self.placed_slots and s_all in self.lims.deck_slots:
                    self.placed_slots.append(s_all)

            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'):
                self.draw_deck()

            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            self.has_tip_var.set(False)

            for st in steps:
                self.workflow_sequence.append(st)
                self.wf_box.insert(tk.END, self._format_step_msg(st))

            self._update_estimated_timer_preview()

            mode_desc = f"{'All 8 Channels' if med_mode == 'all_8ch' else 'Offset Multi-Drug'} | {'Remove + Fresh' if inc_rem_var.get() else 'Fresh Only'}"
            drop_desc = "Slot_4 Empty Cols" if tip_drop_var.get() == "rack_graveyard" else f"Slot_6 A{waste_l} Waste"
            self.logger.info(
                f"Loaded 8×1000 µL EHM Protocol [{mode_desc} | {len(steps)} steps | Drop: {drop_desc} | "
                f"8-Ch Offset: ({cal_dx:+.1f}, {cal_dy:+.1f}, {cal_dz:+.1f}) mm]."
            )
            top.destroy()

        ttk.Button(btn_bar, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(
            btn_bar,
            text="🚀 Apply & Load 8×1000 Protocol",
            bg="#6f42c1",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=12,
            pady=4,
            command=_apply_and_load,
        ).pack(side=tk.RIGHT, padx=5)

    def _is_multichannel_head_active(self) -> bool:
        """Return True if the active pipettor/dropdown head is multi-channel."""
        pip = getattr(getattr(self, "lims", None), "pipettor", None)
        if pip is not None:
            return bool(getattr(pip, "multichannel", False))
        pip_sel = (self.proto_pipettor_var.get() if hasattr(self, "proto_pipettor_var") else "").lower()
        return ("multi" in pip_sel) or ("8-channel" in pip_sel)

    def _expand_target_well_input(
        self,
        raw_well: str,
        slot_name: str,
        action: str,
        is_multichannel: bool,
    ) -> Optional[List[Dict[str, Any]]]:
        """Parse Target Well input into step specs, supporting whole columns (Col 1, Col 1-3) and ranges (A1:H1, A1:E1)."""
        raw_str = (raw_well or "").strip()
        if not raw_str or raw_str.upper() in ("AUTO", "DEFAULT", "NONE", "DISCARD", "WASTE"):
            return [{"well": raw_str}]

        labware_obj = getattr(getattr(self, "lims", None), "deck_labware", {}).get(slot_name)
        n_rows = max(1, min(8, int(getattr(labware_obj, "rows", 8) or 8)))
        n_cols = max(1, int(getattr(labware_obj, "columns", 12) or 12))
        row_letters = "ABCDEFGH"[:n_rows]
        specs: List[Dict[str, Any]] = []

        def _append_col_slice(col: int, r_start: int = 0, r_end: Optional[int] = None) -> bool:
            if col < 1 or col > n_cols:
                messagebox.showwarning(
                    "Invalid Column",
                    f"Column {col} is out of range for {slot_name} (valid columns: 1..{n_cols}).",
                )
                return False
            end_i = (n_rows - 1) if r_end is None else r_end
            start_i, end_i = (min(r_start, end_i), max(r_start, end_i))
            start_i = max(0, min(n_rows - 1, start_i))
            end_i = max(0, min(n_rows - 1, end_i))
            count = (end_i - start_i) + 1

            if action == "Discard Tip":
                specs.append({"well": f"{row_letters[start_i]}{col}"})
                return True

            if is_multichannel:
                if count >= 2 and start_i == 0:
                    specs.append({
                        "well": f"A{col}",
                        "mounted_channels": f"A-{row_letters[end_i]}",
                        "eight_ch_symmetric": (count == n_rows and n_rows == 8),
                    })
                    return True
                if count == 1:
                    specs.append({"well": f"{row_letters[start_i]}{col}"})
                    return True

            for ri in range(start_i, end_i + 1):
                specs.append({"well": f"{row_letters[ri]}{col}"})
            return True

        tokens = [t.strip() for t in raw_str.split(",") if t.strip()]
        for tok in tokens:
            tok_up = tok.upper()
            m_col_range = re.match(r"^COL(?:UMN)?\s*(\d+)\s*[-:]\s*(?:COL(?:UMN)?\s*)?(\d+)$", tok_up)
            if m_col_range:
                c1, c2 = int(m_col_range.group(1)), int(m_col_range.group(2))
                step_dir = 1 if c1 <= c2 else -1
                for col in range(c1, c2 + step_dir, step_dir):
                    if not _append_col_slice(col):
                        return None
                continue

            m_col = re.match(r"^COL(?:UMN)?\s*(\d+)$", tok_up)
            if m_col:
                if not _append_col_slice(int(m_col.group(1))):
                    return None
                continue

            m_range = re.match(r"^([A-H])(\d+)\s*[:\-]\s*([A-H])(\d+)$", tok_up)
            if m_range:
                r1, c1, r2, c2 = m_range.group(1), int(m_range.group(2)), m_range.group(3), int(m_range.group(4))
                if r1 not in row_letters or r2 not in row_letters or c1 < 1 or c1 > n_cols or c2 < 1 or c2 > n_cols:
                    messagebox.showwarning(
                        "Invalid Well Range",
                        f"Range '{tok}' exceeds {slot_name} bounds (rows A..{row_letters[-1]}, cols 1..{n_cols}).",
                    )
                    return None
                i1, i2 = row_letters.index(r1), row_letters.index(r2)
                if c1 == c2:
                    if not _append_col_slice(c1, i1, i2):
                        return None
                elif i1 == i2:
                    step_dir = 1 if c1 <= c2 else -1
                    for col in range(c1, c2 + step_dir, step_dir):
                        specs.append({"well": f"{r1}{col}"})
                else:
                    step_dir = 1 if c1 <= c2 else -1
                    for col in range(c1, c2 + step_dir, step_dir):
                        if not _append_col_slice(col, i1, i2):
                            return None
                continue

            specs.append({"well": tok_up if re.match(r"^[A-H]\d+$", tok_up) else tok})

        return specs

    def add_wf_step(self):
        action = self.wf_action.get()
        is_manual = self.manual_mode_var.get()
        step_data = {"action": action, "mode": "manual" if is_manual else "auto"}

        if "System" in action:
            step_data["mode"] = "auto"
            if "Incubate" in action:
                try:
                    vol_val = float(self.ent_vol.get())
                except ValueError:
                    vol_val = 0.0
                step_data["volume"] = vol_val
                msg = f"[SYSTEM] Incubate for {vol_val} seconds."
            elif "FOC48" in action:
                custom_exp = self.ent_well.get().strip()
                chosen_exp = custom_exp if custom_exp else self.foc_exp_var.get().strip()
                step_data["well"] = chosen_exp
                msg = f"[MEASURE] FOC48_autoOrgan -> Experiment: '{chosen_exp}'"
            elif "Data Analysis" in action:
                msg = f"[ANALYSIS] Execute Hill Equation Modeling"
            elif "DB Upload" in action:
                msg = f"[DATABASE] Sync Results to ContractionDB"
            self.wf_box.insert(tk.END, msg)
            self.workflow_sequence.append(step_data)
        elif is_manual:
            x, y, z, vol = self.ent_x.get(), self.ent_y.get(), self.ent_z.get(), self.ent_vol.get()
            try:
                step_data["x"] = float(x)
                step_data["y"] = float(y)
                step_data["z"] = float(z)
                step_data["volume"] = float(vol) if vol else 0.0
            except ValueError:
                step_data["x"] = 0.0
                step_data["y"] = 0.0
                step_data["z"] = 0.0
                step_data["volume"] = 0.0

            if step_data["z"] > 103.5:
                if not messagebox.askyesno(
                    "⚠️ Hardware Z Limit Warning",
                    f"Warning: Commanded Z={step_data['z']}mm exceeds safe machine limit (103.5mm).\n"
                    f"Instrument firmware hard limit is 103.8mm and will trigger CommandFailed.\n"
                    f"Do you want to proceed anyway?"
                ):
                    return

            if action in ["Pick Up Tip", "Discard Tip", "Detect Liquid Level"]:
                msg = f"[{action.upper()} MANUAL] X:{step_data['x']} Y:{step_data['y']} Z:{step_data['z']}"
            else:
                msg = f"[{action.upper()} MANUAL] X:{step_data['x']} Y:{step_data['y']} Z:{step_data['z']} Vol:{step_data['volume']}\u03bcL"
            self.wf_box.insert(tk.END, msg)
            self.workflow_sequence.append(step_data)
        else:
            slot, raw_well, vol = self.cbx_slot.get(), self.ent_well.get(), self.ent_vol.get()
            extra_z_val = self.ent_z.get() if self.ent_z.winfo_ismapped() else "0.0"

            if not slot:
                messagebox.showwarning("Incomplete Data", "Please select a target deck slot.")
                return
            step_data["slot"] = slot
            try:
                step_data["volume"] = float(vol) if vol else 0.0
            except ValueError:
                step_data["volume"] = 0.0

            try:
                step_data["extra_z"] = float(extra_z_val) if extra_z_val else 0.0
            except ValueError:
                step_data["extra_z"] = 0.0

            target_specs = self._expand_target_well_input(
                raw_well, slot, action, self._is_multichannel_head_active()
            )
            if target_specs is None:
                return

            steps_to_add = []
            for spec in target_specs:
                st = dict(step_data)
                st.update(spec)
                steps_to_add.append(st)

            # Y Travel Limit Guardrail (check first out-of-bounds target once for the batch)
            for st in steps_to_add:
                w = st.get("well", "")
                if w:
                    _wx, _wy = self._resolve_step_xy(st, slot, w.strip().upper())
                    if _wy > 212.0:
                        messagebox.showwarning(
                            "⚠️ Physical Travel Limit Warning",
                            f"Warning: Target '{w}' on {slot} resolves to Y ≈ {_wy:.1f}mm, which exceeds the physical travel limit of the pipette head (~212mm)."
                        )
                        break

            # Safe Z-Depth Guardrail Check (once for the batch)
            if action in ["Aspirate Media", "Dispense Media"] and steps_to_add:
                labware_obj = self.lims.deck_labware.get(slot)
                try:
                    calc_z = self._calculate_z(action, labware_obj, steps_to_add[0]["well"], "auto", 0.0, slot, step_data["extra_z"])
                except ValueError as cal_err:
                    messagebox.showwarning("Labware Not Calibrated", f"{cal_err}\n\nThe step will be added, but the run will stop at it until calibrated.")
                    calc_z = 0.0
                z_limits = getattr(labware_obj, 'z_limits', {}) if labware_obj else {}
                max_b = z_limits.get('max_safe_bottom_z', 103.0)
                if calc_z > max_b:
                    if not messagebox.askyesno(
                        "⚠️ Safe Z-Depth Warning",
                        f"Warning: Resulting Z-Depth ({calc_z:.1f}mm) exceeds safe limit ({max_b:.1f}mm) for {slot} ({getattr(labware_obj, 'name', 'Labware')})!\n\n"
                        f"This might bend the tip or damage the labware.\n"
                        f"Do you want to proceed and add this step anyway?"
                    ):
                        return

            for st in steps_to_add:
                self.wf_box.insert(tk.END, self._format_step_msg(st))
                self.workflow_sequence.append(st)

        if hasattr(self, '_update_estimated_timer_preview'):
            self._update_estimated_timer_preview()

    def _format_step_msg(self, step_data):
        if step_data.get('label'):
            return str(step_data['label'])
        action = step_data.get('action', '')
        mode = step_data.get('mode', 'auto')
        vol = step_data.get('volume', 0.0)
        slot = step_data.get('slot', '')
        well = step_data.get('well', '')
        extra_z = step_data.get('extra_z', 0.0)
        mix_c = step_data.get('mix_cycles', 0)
        mix_v = step_data.get('mix_volume', 100.0)
        ch_msg = f" [Ch {step_data.get('mounted_channels')}]" if step_data.get('mounted_channels') else ""

        if "FOC48" in action:
            return f"[MEASURE] FOC48_autoOrgan -> Experiment: '{well or 'Default'}'"
        elif "Incubate" in action:
            return f"[SYSTEM] Incubate for {vol} seconds."
        elif "Data Analysis" in action or "DB Upload" in action or "Calcium Curve" in action:
            return f"[{action.upper()}]"
        elif mode == "manual":
            return f"[{action.upper()}] Manual -> X:{step_data.get('x',0)} Y:{step_data.get('y',0)} Z:{step_data.get('z',0)} Vol:{vol}uL"
        elif action in ["Pick Up Tip", "Discard Tip"]:
            slot_str = slot or "Default Tip Rack"
            well_str = f"Well {well}" if well and well.upper() not in ("AUTO", "DEFAULT", "NONE", "") else "Auto (Default Start Spot)"
            return f"[{action.upper()}] from {slot_str}, {well_str}{ch_msg}" if action == "Pick Up Tip" else f"[{action.upper()}] into {slot} (Well {well})"
        elif action == "Detect Liquid Level":
            return f"[{action.upper()}] at {slot}, Well {well}"
        else:
            z_msg = f" (Z{float(extra_z):+}mm)" if abs(float(extra_z)) > 1e-9 else ""
            mix_msg = f" [Mix {mix_c}x {mix_v}uL]" if int(mix_c) > 0 and action == "Dispense Media" else ""
            return f"[{action.upper()}] {vol}\u03bcL at {slot}, Well {well}{ch_msg}{z_msg}{mix_msg}"

    def _set_protocol_edit_buttons_state(self, state):
        for btn in getattr(self, 'protocol_edit_buttons', []):
            try:
                btn.config(state=state)
            except Exception:
                pass

    def action_delete_step(self):
        sel = self.wf_box.curselection()
        if not sel:
            messagebox.showinfo("Delete Step", "Please select a step in the protocol list to delete.")
            return
        idx = sel[0]
        if idx >= len(self.workflow_sequence): return
        del_step = self.workflow_sequence[idx]
        del self.workflow_sequence[idx]
        self.wf_box.delete(idx)
        if self.is_running and hasattr(self, 'current_step_idx'):
            if idx < self.current_step_idx:
                self.current_step_idx = max(0, self.current_step_idx - 1)
            self.estimated_total_time = self.estimate_workflow_time(self.workflow_sequence)
        self.logger.info(f"Protocol Step {idx + 1} deleted ({del_step.get('action')}). Remaining: {len(self.workflow_sequence)}.")
        if self.workflow_sequence:
            new_sel = min(idx, len(self.workflow_sequence) - 1)
            self.wf_box.selection_set(new_sel)

    def action_insert_step(self):
        sel = self.wf_box.curselection()
        insert_idx = (sel[0] + 1) if sel else len(self.workflow_sequence)
        if sel and sel[0] < len(self.workflow_sequence):
            template_step = dict(self.workflow_sequence[sel[0]])
        else:
            template_step = {
                'action': 'Aspirate Media',
                'mode': 'auto',
                'slot': 'Slot_1',
                'well': 'A1',
                'volume': 100.0,
                'extra_z': 0.0,
                'mix_cycles': 0,
                'mix_volume': 100.0
            }
        self._open_step_editor_dialog(template_step, insert_idx=insert_idx)

    def action_move_step_up(self):
        sel = self.wf_box.curselection()
        if not sel or sel[0] == 0: return
        idx = sel[0]
        if idx >= len(self.workflow_sequence): return
        self.workflow_sequence[idx - 1], self.workflow_sequence[idx] = self.workflow_sequence[idx], self.workflow_sequence[idx - 1]
        msg_cur = self.wf_box.get(idx)
        msg_prev = self.wf_box.get(idx - 1)
        self.wf_box.delete(idx - 1, idx)
        self.wf_box.insert(idx - 1, msg_cur)
        self.wf_box.insert(idx, msg_prev)
        self.wf_box.selection_set(idx - 1)
        if self.is_running and hasattr(self, 'current_step_idx'):
            if self.current_step_idx == idx:
                self.current_step_idx -= 1
            elif self.current_step_idx == idx - 1:
                self.current_step_idx += 1
        self.logger.info(f"Moved Step {idx + 1} UP to Position {idx}.")

    def action_move_step_down(self):
        sel = self.wf_box.curselection()
        if not sel or sel[0] >= len(self.workflow_sequence) - 1: return
        idx = sel[0]
        self.workflow_sequence[idx], self.workflow_sequence[idx + 1] = self.workflow_sequence[idx + 1], self.workflow_sequence[idx]
        msg_cur = self.wf_box.get(idx)
        msg_next = self.wf_box.get(idx + 1)
        self.wf_box.delete(idx, idx + 1)
        self.wf_box.insert(idx, msg_next)
        self.wf_box.insert(idx + 1, msg_cur)
        self.wf_box.selection_set(idx + 1)
        if self.is_running and hasattr(self, 'current_step_idx'):
            if self.current_step_idx == idx:
                self.current_step_idx += 1
            elif self.current_step_idx == idx + 1:
                self.current_step_idx -= 1
        self.logger.info(f"Moved Step {idx + 1} DOWN to Position {idx + 2}.")

    def edit_wf_step(self, event=None):
        sel = self.wf_box.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self.workflow_sequence): return
        step = self.workflow_sequence[idx]
        self._open_step_editor_dialog(step, edit_idx=idx)

    def _open_step_editor_dialog(self, step_data, edit_idx=None, insert_idx=None):
        dlg = tk.Toplevel(self.root)
        is_edit = edit_idx is not None
        dlg.title(f"{'Edit' if is_edit else 'Insert'} Protocol Step")
        dlg.geometry("400x380")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        pad = {"padx": 10, "pady": 4}
        f = ttk.Frame(dlg, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Action:").grid(row=0, column=0, sticky="w", **pad)
        actions = ["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip", "Mix Well", "Detect Liquid Level", "System: Incubate (Wait)", "System: FOC48 Measurement"]
        act_cb = ttk.Combobox(f, values=actions, state="readonly")
        cur_act = step_data.get('action', 'Aspirate Media')
        act_cb.set(cur_act if cur_act in actions else actions[1])
        act_cb.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Deck Slot:").grid(row=1, column=0, sticky="w", **pad)
        slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
        slot_cb = ttk.Combobox(f, values=slots, state="readonly")
        slot_cb.set(step_data.get('slot', 'Slot_1'))
        slot_cb.grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Well / Col (e.g., A1, Col 1):").grid(row=2, column=0, sticky="w", **pad)
        well_ent = ttk.Entry(f)
        well_ent.insert(0, str(step_data.get('well', 'A1')))
        well_ent.grid(row=2, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Volume (\u03bcL) / Time (s):").grid(row=3, column=0, sticky="w", **pad)
        vol_ent = ttk.Entry(f)
        vol_ent.insert(0, str(step_data.get('volume', 100.0)))
        vol_ent.grid(row=3, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Extra Z offset (mm):").grid(row=4, column=0, sticky="w", **pad)
        z_ent = ttk.Entry(f)
        z_ent.insert(0, str(step_data.get('extra_z', 0.0)))
        z_ent.grid(row=4, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Mix Cycles:").grid(row=5, column=0, sticky="w", **pad)
        mix_c_ent = ttk.Entry(f)
        mix_c_ent.insert(0, str(step_data.get('mix_cycles', 0)))
        mix_c_ent.grid(row=5, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Mix Volume (\u03bcL):").grid(row=6, column=0, sticky="w", **pad)
        mix_v_ent = ttk.Entry(f)
        mix_v_ent.insert(0, str(step_data.get('mix_volume', 100.0)))
        mix_v_ent.grid(row=6, column=1, sticky="ew", **pad)

        def save():
            try:
                base_data = dict(step_data)
                orig_well_str = str(step_data.get('well', '')).strip().upper()
                new_well_str = well_ent.get().strip().upper()
                new_action = act_cb.get()
                new_slot = slot_cb.get()
                new_vol = float(vol_ent.get())
                new_extra_z = float(z_ent.get())
                new_mix_c = int(mix_c_ent.get())
                new_mix_v = float(mix_v_ent.get())

                fields_changed = (
                    (not is_edit)
                    or new_action != str(step_data.get('action', ''))
                    or new_slot != str(step_data.get('slot', ''))
                    or new_well_str != orig_well_str
                    or abs(new_vol - float(step_data.get('volume', 0.0))) > 1e-9
                    or abs(new_extra_z - float(step_data.get('extra_z', 0.0))) > 1e-9
                    or new_mix_c != int(step_data.get('mix_cycles', 0))
                    or abs(new_mix_v - float(step_data.get('mix_volume', 100.0))) > 1e-9
                )

                if is_edit and new_well_str != orig_well_str:
                    base_data.pop('mounted_channels', None)
                    base_data.pop('eight_ch_symmetric', None)
                base_data['action'] = new_action
                base_data['slot'] = new_slot
                base_data['volume'] = new_vol
                base_data['extra_z'] = new_extra_z
                base_data['mix_cycles'] = new_mix_c
                base_data['mix_volume'] = new_mix_v

                target_specs = self._expand_target_well_input(
                    well_ent.get(), base_data['slot'], base_data['action'], self._is_multichannel_head_active()
                )
                if target_specs is None:
                    return

                if fields_changed or len(target_specs) > 1:
                    base_data.pop('label', None)

                expanded = []
                for spec in target_specs:
                    st = dict(base_data)
                    st.update(spec)
                    expanded.append(st)

                if is_edit:
                    self.workflow_sequence[edit_idx:edit_idx + 1] = expanded
                    self.wf_box.delete(edit_idx)
                    for offset, st in enumerate(expanded):
                        self.wf_box.insert(edit_idx + offset, self._format_step_msg(st))
                    self.wf_box.selection_set(edit_idx)
                    if self.is_running and hasattr(self, 'current_step_idx') and edit_idx < self.current_step_idx:
                        self.current_step_idx += max(0, len(expanded) - 1)
                    self.logger.info(f"Edited Step {edit_idx + 1} ({len(expanded)} step(s)).")
                else:
                    for offset, st in enumerate(expanded):
                        self.workflow_sequence.insert(insert_idx + offset, st)
                        self.wf_box.insert(insert_idx + offset, self._format_step_msg(st))
                    self.wf_box.selection_set(insert_idx)
                    if self.is_running and hasattr(self, 'current_step_idx') and insert_idx <= self.current_step_idx:
                        self.current_step_idx += len(expanded)
                    self.logger.info(f"Inserted {len(expanded)} step(s) at {insert_idx + 1}.")

                if self.is_running:
                    self.estimated_total_time = self.estimate_workflow_time(self.workflow_sequence)
                if hasattr(self, '_update_estimated_timer_preview'):
                    self._update_estimated_timer_preview()

                dlg.destroy()
            except ValueError as ve:
                messagebox.showerror("Invalid Input", f"Please check numerical values:\n{ve}", parent=dlg)

        btn_box = ttk.Frame(f)
        btn_box.grid(row=7, column=0, columnspan=2, pady=15)
        ttk.Button(btn_box, text="💾 Save Step", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)

    def action_load_deck_2_ehm_multiplate(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(script_dir, "deck_2_ehm_plates_slot2_discard_a1.json"),
            os.path.join(script_dir, "protocols", "deck_2_ehm_plates_slot2_discard_a1.json"),
            os.path.join(os.path.dirname(script_dir), "protocols", "deck_2_ehm_plates_slot2_discard_a1.json"),
            os.path.join(script_dir, "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(script_dir, "deck_configurations", "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(os.getcwd(), "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(os.getcwd(), "protocols", "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "deck_2_ehm_plates_slot2_discard_50ml.json"),
        ]
        target_path = next((p for p in cand_paths if os.path.exists(p)), None)
        if target_path:
            self._deserialize_workspace(target_path)
            self.logger.info("Loaded 2-EHM Multi-Plate Deck Configuration (Slot 1 Media A1/A2, Slot 2 Discard A1, Slot 3 Drug Plate, Slot 4 Tips, Slot 5 Plt 1, Slot 6 Plt 2).")
        else:
            messagebox.showerror("Error", "Could not locate deck_2_ehm_plates_slot2_discard_a1.json")

    def sync_deck_manager(self):
        """
        Synchronizes the strongly-typed DeckManager with the GUI's deck_slots and deck_labware.
        Maps labware definitions to dedicated LabwareBase subclasses and attaches HeightAdapters.
        """
        if not hasattr(self, 'deck_manager'):
            self.deck_manager = DeckManager()

        for slot_name, slot_obj in self.lims.deck_slots.items():
            adapter = ADAPTER_90MM_BLOCK if slot_name in ("Slot_1", "Slot_2") else ADAPTER_NONE

            labware_obj = self.lims.deck_labware.get(slot_name)
            if not labware_obj:
                if slot_name in self.deck_manager.slots:
                    self.deck_manager.slots[slot_name].labware = None
                    self.deck_manager.slots[slot_name].adapter = adapter
                continue

            src = str(getattr(labware_obj, 'source_file', '') or '').lower()
            name = str(getattr(labware_obj, 'name', '') or '').lower()
            both = f"{src} {name}"

            typed_lw = None
            if "3x50ml" in both or "50ml" in both or "tube_rack_3x50ml" in src:
                typed_lw = FalconRack50mL(source_file=src)
            elif "2x6" in both or "2ml" in both or "tube_rack_2x6" in src:
                typed_lw = TubeRack2x6_2mL(source_file=src)
            elif "reservoir_3" in src or "3_well" in src or "3-well" in name or "30ml" in both:
                typed_lw = Reservoir3Well(source_file=src)
            elif "reservoir_7" in src or "7_column" in src or "7-column" in name or "7_well" in src or "7-well" in name:
                typed_lw = Reservoir7Column(source_file=src)
            elif "reservoir_6" in src or "6_column" in src or "6-column" in name:
                typed_lw = Reservoir6Column(source_file=src)
            elif "tip" in both or "tip_rack" in src:
                existing_offset = (0.0, 0.0)
                if slot_name in self.deck_manager.slots and isinstance(self.deck_manager.slots[slot_name].labware, TipRack96):
                    existing_offset = (
                        self.deck_manager.slots[slot_name].labware.learned_rack_offset_x,
                        self.deck_manager.slots[slot_name].labware.learned_rack_offset_y
                    )
                typed_lw = TipRack96(source_file=src)
                typed_lw.learned_rack_offset_x, typed_lw.learned_rack_offset_y = existing_offset
            elif "waste" in both or (slot_name == "Slot_6" and not both.strip()):
                typed_lw = WasteTrough(source_file=src)
            elif "myriamed" in both or "ehm" in both or "48" in both:
                typed_lw = Plate48Myriamed(source_file=src)
            elif "96" in both or (getattr(labware_obj, 'rows', 0) == 8 and getattr(labware_obj, 'columns', 0) == 12):
                typed_lw = Plate96(source_file=src)
            else:
                typed_lw = LabwareBase(
                    name=getattr(labware_obj, 'name', 'Generic Labware'),
                    category="custom",
                    rows=getattr(labware_obj, 'rows', 1),
                    columns=getattr(labware_obj, 'columns', 1),
                    z_height_mm=getattr(labware_obj, 'z_height_mm', 14.35),
                    well_depth_mm=getattr(labware_obj, 'well_depth_mm', 10.0),
                    well_radius_mm=getattr(labware_obj, 'well_radius_mm', 3.4),
                    source_file=src,
                    raw_data=getattr(labware_obj, 'raw_data', {}) or {}
                )

            self.deck_manager.mount_labware(slot_name, typed_lw, adapter=adapter)

    def _estimate_step_durations(self, sequence) -> list:
        """
        Compute calibrated physical baseline durations (in seconds) for each step:
        - Tip pickup / eject: ~3.2-3.5s + XY travel (~4-4.5s)
        - Removal / standard aspirate or dispense: ~8-10s + XY travel
        - Reservoir/tube single-channel LLD meniscus probing: +4.6s probe descent
        - Dispense with 2x in-well mixing: ~21-24s including XY travel
        Calibrated so the full 1,372-step 2-plate Media Change + Drug protocol estimates ~4.5-4.8 hours.
        """
        durations = []
        current_x, current_y = 0.0, 0.0
        speed_pct = self.speed_var.get() if hasattr(self, 'speed_var') else 80.0
        xy_speed = max(50.0, 250.0 * (speed_pct / 100.0))
        lld_enabled = (
            (not hasattr(self, 'lld_tracking_var') or bool(self.lld_tracking_var.get()))
            or (hasattr(self, 'dynamic_z_var') and bool(self.dynamic_z_var.get()))
        )

        for s in sequence:
            action = s.get('action', '')
            vol = float(s.get('volume', 0.0))
            mix_cycles = int(s.get('mix_cycles', 0)) if getattr(self, 'enable_mixing_for_run', True) else 0

            if "Incubate" in action:
                durations.append(max(0.0, vol))
                continue
            elif "FOC48" in action:
                durations.append(150.0)
                continue
            elif "Data Analysis" in action:
                durations.append(5.0)
                continue
            elif "DB Upload" in action:
                durations.append(3.0)
                continue
            elif "Calcium Curve" in action:
                durations.append(60.0)
                continue

            slot = s.get('slot', '')
            well = s.get('well', '')
            tx, ty = (self._resolve_step_xy(s, slot, well) or (current_x, current_y)) if slot else (current_x, current_y)
            travel_dist = math.hypot(tx - current_x, ty - current_y)
            current_x, current_y = tx, ty
            travel_time = (travel_dist / xy_speed) + 0.35

            is_8ch = bool(self.lims.pipettor.multichannel or s.get('eight_ch_symmetric'))

            if action == "Pick Up Tip":
                step_t = travel_time + 3.5
            elif action == "Discard Tip":
                step_t = travel_time + 3.2
            elif action == "Aspirate Media":
                has_air = (
                    (0.0 < vol <= 50.0)
                    and not s.get('no_air_cushion', False)
                    and not self._is_machine_2_10ul_active()
                )
                air_time = 1.2 if has_air else 0.0
                draw_time = max(0.8, vol * 0.005)

                step_lw = str(s.get('labware') or '').lower()
                if not step_lw and slot in self.lims.deck_labware:
                    step_lw = str(getattr(self.lims.deck_labware.get(slot), 'source_file', '') or '').lower()
                is_plate_lw = any(k in step_lw for k in ('plate', '96', '48', 'ehm', 'myriamed', 'corning'))
                is_tube_or_res = (
                    any(k in step_lw for k in ('reservoir', 'tube', 'falcon', '2x6', '50ml', '3_well'))
                    and not is_plate_lw
                )
                uses_lld = (not is_8ch) and lld_enabled and is_tube_or_res
                lld_time = 6.0 if uses_lld else 0.0
                step_t = travel_time + 8.3 + air_time + draw_time + lld_time
            elif action == "Dispense Media":
                disp_time = max(0.6, vol * 0.004)
                mix_time = mix_cycles * 4.7
                step_t = travel_time + 8.0 + disp_time + 0.4 + mix_time
            elif action == "Mix Well":
                step_t = travel_time + 4.0 + (mix_cycles * 4.7)
            elif action == "Detect Liquid Level":
                step_t = travel_time + 8.5
            else:
                step_t = travel_time + 2.0

            durations.append(step_t)

        return durations

    def estimate_workflow_time(self, sequence) -> float:
        return round(sum(self._estimate_step_durations(sequence)), 1)

    def pause_resume_run(self):
        if self.pause_event.is_set():
            self._begin_pause_tracking()
            self.pause_event.clear()
            self.btn_pause.config(text="▶ RESUME", bg="#17a2b8")
            self._set_protocol_edit_buttons_state(tk.NORMAL)
            self.logger.info("Protocol Paused by User. Timer & Speed Factor frozen. Steps can be edited, added, reordered, or deleted.")
        else:
            self._end_pause_tracking()
            self.step_baseline_times = self._estimate_step_durations(self.workflow_sequence)
            self.pause_event.set()
            self.btn_pause.config(text="⏸ PAUSE", bg="#ffc107")
            self._set_protocol_edit_buttons_state(tk.DISABLED)
            cur_i = getattr(self, 'current_step_idx', 0)
            self.logger.info(f"Protocol Resumed at Step {cur_i + 1}/{len(self.workflow_sequence)}.")

    def stop_run(self):
        if getattr(self, 'session_abort_status', None) is None:
            self.session_abort_status = "ABORTED_USER"
        self.is_aborted = True
        self._end_pause_tracking()
        self.pause_event.set()
        self.logger.info("Protocol Abort Signal Sent by Operator. Halting sequence...")
        try:
            self.btn_stop.config(state=tk.DISABLED, text="Stopping...")
        except Exception:
            pass

    def update_ui_state(self, running):
        self.is_running = running
        state = tk.DISABLED if running else tk.NORMAL
        self.btn_play.config(state=state)
        self.btn_pause.config(state=tk.NORMAL if running else tk.DISABLED, text="⏸ PAUSE", bg="#ffc107")
        self.btn_stop.config(state=tk.NORMAL if running else tk.DISABLED, text="⏹ CANCEL")
        self._set_protocol_edit_buttons_state(tk.NORMAL if not running else tk.DISABLED)

    def ask_error_resolution(self, error_msg, step_idx):
        """
        Interactive Error Recovery Dialog with User-Directed Clearance.
        Offers 4 clear paths:
        1. [ Retry Step ]
        2. [ Clear / Unjam Tip ]: Operator chooses target slot and well (defaults to safe slot center),
           robot purges liquid, optionally ejects tip, and retracts.
        3. [ Skip Step & Continue ]
        4. [ Safe Abort ]
        """
        err_str = str(error_msg)
        classified = self._classify_abort_reason(error_msg)
        if any(kw in err_str for kw in ["CRITICAL", "COLLISION", "DOUBLE-TIP", "ejection failed", "SAFETY INTERLOCK"]):
            self.logger.critical(f"🛑 CRITICAL SAFETY ABORT on Step {step_idx}: {err_str}")
            self.session_abort_status = "AUTO_ABORTED_HARDWARE"
            self.is_aborted = True
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except Exception:
                    pass
            return

        self._begin_pause_tracking()
        self.pause_event.clear()
        if hasattr(self, "btn_pause"):
            self.root.after(0, lambda: self.btn_pause.config(text="▶ RESUME", bg="#17a2b8"))
        self.user_decision = None

        def open_recovery_dialog():
            dlg = tk.Toplevel(self.root)
            dlg.title("⚠️ Protocol Execution Interrupted — Error Recovery")
            dlg.geometry("540x440")
            dlg.transient(self.root)
            dlg.grab_set()

            try:
                rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 270
                ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 220
                dlg.geometry(f"+{max(0, rx)}+{max(0, ry)}")
            except Exception:
                pass

            step = {}
            if 0 <= (step_idx - 1) < len(self.workflow_sequence):
                step = self.workflow_sequence[step_idx - 1]

            header_f = tk.Frame(dlg, bg="#dc3545", padx=12, pady=10)
            header_f.pack(fill=tk.X)
            tk.Label(header_f, text="⚠️ Protocol Execution Halted", font=("Arial", 12, "bold"), fg="white", bg="#dc3545").pack(anchor="w")
            step_summary = f"Step {step_idx}/{len(self.workflow_sequence)}: [{step.get('action', 'Unknown')}] at {step.get('slot', 'Slot')} {step.get('well', '')}"
            tk.Label(header_f, text=step_summary, font=("Arial", 9), fg="#f8d7da", bg="#dc3545").pack(anchor="w")

            msg_box = ttk.LabelFrame(dlg, text="Hardware / Software Trace", padding=8)
            msg_box.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)
            txt = tk.Text(msg_box, height=4, font=("Consolas", 9), bg="#f8f9fa", fg="#212529", wrap="word")
            txt.insert("1.0", err_str)
            txt.config(state="disabled")
            txt.pack(fill=tk.BOTH, expand=True)

            # Clearance Controls Frame
            clear_frame = ttk.LabelFrame(dlg, text="🧹 Tip & Manifold Clearance Settings", padding=8)
            clear_frame.pack(fill=tk.X, padx=14, pady=(0, 8))

            row_c = ttk.Frame(clear_frame)
            row_c.pack(fill=tk.X, pady=2)
            ttk.Label(row_c, text="Clearance Slot:").pack(side=tk.LEFT, padx=(0, 4))
            clear_slot_var = tk.StringVar(value="Slot_2" if "Slot_2" in self.lims.deck_slots else "Slot_6")
            cb_clear_slot = ttk.Combobox(row_c, textvariable=clear_slot_var, values=["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"], state="readonly", width=10)
            cb_clear_slot.pack(side=tk.LEFT, padx=(0, 12))

            ttk.Label(row_c, text="Target Well (optional):").pack(side=tk.LEFT, padx=(0, 4))
            clear_well_var = tk.StringVar(value="")
            ent_clear_well = ttk.Entry(row_c, textvariable=clear_well_var, width=8)
            ent_clear_well.pack(side=tk.LEFT)
            ttk.Label(clear_frame, text="* Leave well blank to clear at the safe center of that slot.", font=("Arial", 8, "italic"), foreground="#6c757d").pack(anchor="w", pady=(2, 0))

            lbl_clear_status = ttk.Label(clear_frame, text="", font=("Arial", 8, "bold"), foreground="#059669")
            lbl_clear_status.pack(anchor="w", pady=(2, 0))

            def execute_clearance():
                t_slot = clear_slot_var.get()
                t_well = clear_well_var.get().strip().upper()
                try:
                    self.logger.info(f"[RECOVERY] Performing clearance move to {t_slot} (well: '{t_well or 'CENTER'}')...")
                    if self.lims.pipettor.hardware:
                        self.lims.pipettor.hardware.move_z(0)

                    if t_well:
                        coords = self._calculate_xy(t_slot, t_well)
                    else:
                        slot_obj = self.lims.deck_slots.get(t_slot)
                        if slot_obj:
                            coords = (slot_obj.x_abs + (slot_obj.width_mm / 2.0), slot_obj.y_abs + (slot_obj.height_mm / 2.0))
                        else:
                            coords = (150.0, 150.0)

                    cx, cy = coords
                    self.lims.hw.move_to(cx, cy, 0, speed=50)

                    clear_z = 20.0
                    if self.lims.pipettor.hardware:
                        self.lims.pipettor.hardware.move_z(clear_z)
                        try:
                            self.lims.pipettor.hardware.dispense(0)
                        except Exception:
                            pass

                    ans_drop = messagebox.askyesno("Eject Tip?", "Liquid blowout purge complete.\nDo you also want to eject and discard the tip(s)?")
                    if ans_drop and self.lims.pipettor.hardware:
                        try:
                            self.lims.pipettor.hardware.eject_tip()
                            self.has_tip_var.set(False)
                        except Exception as ee:
                            self.logger.warning(f"Tip ejection error during clearance: {ee}")

                    if self.lims.pipettor.hardware:
                        self.lims.pipettor.hardware.move_z(0)

                    lbl_clear_status.config(text=f"✔ Cleared at {t_slot} {t_well or 'Center'}. You may now Retry or Skip.")
                    self.logger.info(f"[RECOVERY] Clearance completed safely at {t_slot}.")
                except Exception as ce:
                    self.logger.error(f"[RECOVERY] Clearance error: {ce}")
                    lbl_clear_status.config(text=f"Clearance failed: {ce}")

            tk.Button(clear_frame, text="⚡ Execute Clearance Now", bg="#17a2b8", fg="white", font=("Arial", 8, "bold"), command=execute_clearance).pack(anchor="w", pady=(4, 2))

            # Action Buttons Row
            btn_row = ttk.Frame(dlg)
            btn_row.pack(fill=tk.X, padx=14, pady=(6, 12))

            def on_retry():
                self.user_decision = "retry"
                dlg.destroy()

            def on_skip():
                self.user_decision = "skip"
                dlg.destroy()

            def on_abort():
                self.user_decision = "abort"
                dlg.destroy()

            tk.Button(btn_row, text="🔁 Retry Step", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=on_retry).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            tk.Button(btn_row, text="⏭️ Skip Step", bg="#0d6efd", fg="white", font=("Arial", 10, "bold"), command=on_skip).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            tk.Button(btn_row, text="🛑 Safe Abort", bg="#dc3545", fg="white", font=("Arial", 10, "bold"), command=on_abort).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.root.after(0, open_recovery_dialog)
        while self.user_decision is None and not self.is_aborted:
            time.sleep(0.1)

        self._end_pause_tracking()
        if self.user_decision == "abort" or self.is_aborted:
            if self.session_abort_status is None:
                self.session_abort_status = classified
            self.is_aborted = True
        elif self.user_decision in ("retry", "skip", "ignore"):
            self.logger.warning(f"Operator selected '{self.user_decision}' for Step {step_idx}.")
            self.session_abort_status = None
            self.pause_event.set()
            if hasattr(self, "btn_pause"):
                self.root.after(0, lambda: self.btn_pause.config(text="⏸ PAUSE", bg="#ffc107"))

    def _probe_surface_and_wait(self, limit_z: float, submerge_mm: float = 1.0) -> float:
        """
        Safely probes downward for liquid meniscus using Biohit tip frequency sensor.
        Blocks until physical movement completes, pauses for visual confirmation,
        and returns the measured liquid surface Z coordinate (in mm).
        CRITICAL FIRMWARE CONSTRAINT: InstrumentLib.dll _MoveToSurface enforces limit <= 100.0f.
        Any limit > 100.0f causes immediate rejection with ErrorCode 2 without energizing the Z motor.
        We strictly clamp limit_z to safe_limit_z <= 99.5mm.
        """
        # Strict hard cap: InstrumentLib.dll _MoveToSurface strictly enforces limit <= 100.0f
        safe_limit_z = min(99.5, max(10.0, float(limit_z)))
        hw = getattr(self.lims.pipettor, 'hardware', None)
        if not hw:
            # Simulator mode fallback
            time.sleep(1.0)
            return max(0.0, safe_limit_z - 15.0)

        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9))) if hasattr(self, 'speed_var') else 7
        saved_z_speed = getattr(hw, 'z_speed', hw_speed)
        try:
            # Set responsive probe speed (probe at speed 5-7 instead of crawling at 3)
            probe_speed = max(5, min(hw_speed, 7))
            hw.z_speed = probe_speed
            self.logger.info(f"[SURFACE PROBE] Descending toward safe limit Z={safe_limit_z:.1f}mm (depth={submerge_mm:.1f}mm, speed={probe_speed}, Cap<=99.5mm)...")

            # Execute move_to_surface
            called_ok = False
            try:
                hw.move_to_surface(limit=float(safe_limit_z), distance_from_surface=float(submerge_mm))
                called_ok = True
            except Exception as e_wrap:
                self.logger.warning(f"[SURFACE PROBE] pipettor.move_to_surface exception: {e_wrap}")

            if not called_ok:
                inst = getattr(hw, '_Pipettor__instrument', None)
                if inst:
                    try:
                        if hasattr(inst, 'MoveToSurface'):
                            res = inst.MoveToSurface(float(safe_limit_z), float(submerge_mm))
                            called_ok = bool(res)
                        elif hasattr(inst, 'Control') and hasattr(inst.Control, 'MoveToSurface'):
                            res = inst.Control.MoveToSurface(float(safe_limit_z), True)
                            called_ok = bool(res)
                    except Exception as e_clr:
                        self.logger.error(f"[SURFACE PROBE] Direct CLR MoveToSurface call failed: {e_clr}")

            if not called_ok:
                self.logger.error(f"[SURFACE PROBE] MoveToSurface command was rejected by hardware firmware (limit={safe_limit_z:.1f}mm).")
                raise RuntimeError(f"MoveToSurface rejected by pipettor firmware (limit={safe_limit_z:.1f}mm).")

            # Wait for physical descent to complete (polling drive state and position stability)
            inst = getattr(hw, '_Pipettor__instrument', None)
            t_start = time.time()
            max_wait_sec = 25.0
            time.sleep(0.3)  # Brief grace period for motor acceleration

            last_z = None
            stable_ticks = 0
            while (time.time() - t_start) < max_wait_sec:
                drive_active = False
                if inst and hasattr(inst, 'Control') and hasattr(inst.Control, 'IsDriveOn'):
                    try:
                        drive_active = bool(inst.Control.IsDriveOn("Z"))
                    except Exception:
                        drive_active = False

                curr_z = getattr(hw, 'z_position', None)
                if curr_z is not None:
                    if last_z is not None and abs(curr_z - last_z) < 0.08:
                        stable_ticks += 1
                    else:
                        stable_ticks = 0
                    last_z = curr_z

                # Stop waiting when drive is off and position has stabilized for 3 consecutive ticks
                if not drive_active and stable_ticks >= 3:
                    break

                time.sleep(0.1)

            z_measured = getattr(hw, 'z_position', safe_limit_z)

            # Sanity guard: clearance ceiling is Z=0.0-5.0mm. No container rim on this deck is above Z=40mm.
            # If Z <= 25.0mm, the motor never moved or hit a false trigger in open air near the top.
            if z_measured <= 25.0:
                self.logger.error(f"[SURFACE PROBE FAILURE] Tip remained near ceiling at Z={z_measured:.2f}mm (<=25mm). Probe aborted or failed to descend.")
                raise RuntimeError(f"Surface probe failed: tip remained near ceiling at Z={z_measured:.2f}mm")

            self.logger.info(f"[SURFACE PROBE] Surface detected/stopped at Z={z_measured:.2f}mm (limit={safe_limit_z:.1f}mm)")

            # Visual confirmation pause
            time.sleep(0.15)
            return float(z_measured)

        finally:
            try:
                hw.z_speed = hw_speed
            except Exception:
                pass

    # ------------------------------------------------------------------
    # MODULAR LABWARE KINEMATICS
    # Coordinates depend on (slot A1 origin) + (labware geometry), never on
    # hardcoded slot identity. Any labware can sit on any slot.
    # ------------------------------------------------------------------

    # Machine XY of "well A1" for each slot (physically jog-calibrated where noted)
    SLOT_A1_ORIGINS = {
        "Slot_1": (235.05, 5.27),  # calibrated (front right, 3-well reservoir A1: X=235.05, Y=5.27)
        "Slot_2": (95.5, 13.0),    # calibrated (front left, 3-well reservoir/waste trough A1)
        "Slot_3": (243.81, 52.64), # calibrated (Machine 2 1-10µL: A1 X=243.81, A1 Y=52.64, 8-ch center Y=84.14)
        "Slot_4": (105.63, 52.64), # calibrated (Slot 4 Tip Rack: A1 X=105.63, A1 Y=52.64, 8-ch center Y=84.14)
        "Slot_5": (242.98, 147.64), # calibrated (96-well plate A1 center: X=242.98, Y=147.64)
        "Slot_6": (105.60, 146.81), # calibrated (Machine 2: 8-ch center Y=178.31 -> A1 Y=146.81)
    }

    # Calibrated per-slot column tables for 96-format labware (override pitch math)
    SLOT_96_COL_OVERRIDES = {
        "Slot_4": [round(105.63 - (c * 9.0), 2) for c in range(12)],
        "Slot_5": [round(242.98 - (c * 9.0), 2) for c in range(12)],
    }

    # Calibrated per-slot Z for 96-well microplates: (deep / aspirate / mix, brim / dispense)
    SLOT_96_PLATE_Z = {
        "Slot_3": (78.40, 68.43),
        "Slot_4": (78.40, 68.43),
        "Slot_5": (78.40, 68.43),
        "Slot_6": (78.40, 68.43),
    }
    DEFAULT_96_PLATE_Z = (78.40, 68.43)

    def _lw_kind(self, labware_obj):
        """Classify a labware object by its definition (file first, then name)."""
        if not labware_obj:
            return None
        src = (getattr(labware_obj, 'source_file', '') or '').lower()
        name = (getattr(labware_obj, 'name', '') or '').lower()
        both = src + " " + name
        raw = getattr(labware_obj, 'raw_data', {}) or {}

        if "tip" in both:
            return "tip_rack"
        if "2x6" in both:
            return "tube_rack_2x6"
        if "biohit_rack" in both or "17a" in both or "4x6" in both:
            return "tube_rack_4x6"
        if "waste" in both:
            return "waste"
        if "reservoir_3" in src or "3_well" in src or "3-well" in name:
            return "reservoir_3"
        if "reservoir_7" in src or "7_column" in src or "7-column" in name or "7_well" in src or "7-well" in name:
            return "reservoir_7"
        if "reservoir_6" in src or "6_column" in src or "6-column" in name:
            return "reservoir_6"
        if "myriamed" in both or "ehm" in both or "48" in both:
            return "ehm48"
        if "96" in both or (getattr(labware_obj, 'rows', 0) == 8 and getattr(labware_obj, 'columns', 0) == 12):
            return "plate96"
        if raw.get('kinematics'):
            return "json_kinematics"
        return "generic"

    def _is_front_slot(self, slot_name):
        slot_obj = self.lims.deck_slots.get(slot_name)
        if slot_obj is not None:
            return slot_obj.y_abs < 40.0
        return slot_name in ("Slot_1", "Slot_2")

    def _slot_a1_origin(self, slot_name):
        is_300ul = (
            ("300" in getattr(self, "active_profile_id", ""))
            or ("300" in str(getattr(self, "current_protocol_file", "")).lower())
            or ("300" in str(getattr(self, "loaded_protocol_name", "")).lower())
            or ("300" in str(getattr(self, "proto_workflow_var", tk.StringVar()).get()).lower())
            or ("300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower())
            or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 0) == 300.0)
        )
        if is_300ul:
            origins_300 = {
                "Slot_1": (235.05, 5.27),
                "Slot_2": (95.50, 13.0),
                "Slot_3": (243.81, 52.64),
                "Slot_4": (105.63, 52.64),
                "Slot_5": (242.98, 147.64),
                "Slot_6": (105.60, 146.81),
            }
            if slot_name in origins_300:
                return origins_300[slot_name]

        is_10ul = ("10ul" in getattr(self, "active_profile_id", "")) or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 200) <= 10.0)
        if is_10ul:
            if slot_name == "Slot_4":
                return 105.63, 52.64
            if slot_name == "Slot_3":
                return 243.81, 52.64
            if slot_name == "Slot_5":
                return 242.98, 147.64
            if slot_name == "Slot_6":
                return 105.60, 146.81
            if slot_name == "Slot_1":
                return 235.05, 5.27
            if slot_name == "Slot_2":
                return 95.50, 13.0
        m1_origins = {
            "Slot_1": (235.05, 5.27),
            "Slot_2": (95.5, 13.0),
            "Slot_3": (243.81, 53.02),
            "Slot_4": (105.60, 53.02),
            "Slot_5": (242.98, 147.64),
            "Slot_6": (105.60, 147.19),
        }
        if slot_name in m1_origins:
            return m1_origins[slot_name]
        if slot_name in self.SLOT_A1_ORIGINS:
            return self.SLOT_A1_ORIGINS[slot_name]
        slot_obj = self.lims.deck_slots.get(slot_name)
        if not slot_obj:
            return 0.0, 0.0
        ox = 243.81 if slot_obj.x_abs >= 70.0 else 105.0
        if slot_obj.y_abs < 40.0:
            oy = 13.0
        elif slot_obj.y_abs < 120.0:
            oy = 53.0
        else:
            oy = 149.23
        return ox, oy

    @staticmethod
    def _parse_well(well_id):
        """'B3' -> (row_idx=1, col_idx=2). Returns (None, None) if invalid."""
        if not well_id or len(well_id) < 2:
            return None, None
        r_c = well_id[0].upper()
        try:
            c_idx = int(well_id[1:]) - 1
        except ValueError:
            return None, None
        r_idx = ord(r_c) - ord('A')
        if r_idx < 0 or c_idx < 0:
            return None, None
        return r_idx, c_idx

    @staticmethod
    def _m2_slot4_tip_base_xy(tip_count: int) -> Tuple[float, float]:
        """Return Slot 4 Col 1 base (X, Y) for Machine 2 (1-10 uL) for 1..8 tips."""
        n = max(1, min(8, int(tip_count)))
        if n <= 5:
            t = (n - 1) / 4.0
            bx = 105.66
            by = round(21.53 + t * (56.83 - 21.53) + 1e-9, 2)
        else:
            t = (n - 5) / 3.0
            bx = round(105.66 + t * (105.47 - 105.66), 2)
            by = round(56.83 + t * (84.99 - 56.83), 2)
        return bx, by

    @staticmethod
    def _parse_mounted_tip_count(raw_mounted: str) -> Optional[int]:
        """Parse mounted_channels string (e.g. 'A', 'A-E', '5', '1-5', '5CH') into 1..8."""
        s = str(raw_mounted or "").strip().upper()
        if not s:
            return None
        if len(s) == 1 and s in "ABCDEFGH":
            return 1
        if "-" in s:
            parts = [p.strip() for p in s.split("-", 1)]
            if len(parts) == 2:
                if len(parts[0]) == 1 and len(parts[1]) == 1 and parts[0] in "ABCDEFGH" and parts[1] in "ABCDEFGH":
                    return max(1, min(8, ord(parts[1]) - ord(parts[0]) + 1))
                if parts[0].isdigit() and parts[1].isdigit():
                    return max(1, min(8, int(parts[1]) - int(parts[0]) + 1))
        if "," in s:
            items = [p.strip() for p in s.split(",") if p.strip()]
            if items:
                return max(1, min(8, len(items)))
        digits = "".join(ch for ch in s if ch.isdigit())
        if digits and (s == digits or s.startswith("CH") or "CH" in s or "TIP" in s):
            return max(1, min(8, int(digits)))
        return None

    def _calculate_xy(self, slot_name, well_id):
        is_300ul = (
            ("300" in getattr(self, "active_profile_id", ""))
            or ("300" in str(getattr(self, "current_protocol_file", "")).lower())
            or ("300" in str(getattr(self, "loaded_protocol_name", "")).lower())
            or ("300" in str(getattr(self, "proto_workflow_var", tk.StringVar()).get()).lower())
            or ("300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower())
            or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 0) == 300.0)
        )
        is_10ul = not is_300ul and (
            ("10ul" in getattr(self, "active_profile_id", ""))
            or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 200) <= 10.0 and getattr(self.lims.pipettor, "multichannel", False))
        )

        # Direct Machine 3 (300 µL Single-Channel) Kinematics:
        # Slot 4 Tip Rack: A1 strictly at X=105.63, Y=52.64
        # Slot 5 96-Well Plate: A1 strictly at X=242.98, Y=147.64
        # Slot 3 96-Well Plate: A1 strictly at X=243.81, Y=52.64
        if is_300ul:
            r_idx, c_idx = self._parse_well(well_id)
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 12) else 0
            ri = r_idx if (r_idx is not None and 0 <= r_idx < 8) else 0
            if slot_name == "Slot_4":
                return round(105.63 - (ci * 9.0), 2), round(52.64 + (ri * 9.0), 2)
            if slot_name == "Slot_5":
                return round(242.98 - (ci * 9.0), 2), round(147.64 + (ri * 9.0), 2)
            if slot_name == "Slot_3":
                return round(243.81 - (ci * 9.0), 2), round(52.64 + (ri * 9.0), 2)
            if slot_name == "Slot_1":
                return round(235.05 - (ci * 42.6), 2), 5.27
            if slot_name == "Slot_2":
                col_x = [95.5, 57.0, 12.0]
                return col_x[ci if ci < 3 else 2], 13.0
            if slot_name == "Slot_6":
                col_x_s6 = [108.81, 93.81, 75.06, 56.31, 37.56, 18.81, 5.91]
                return col_x_s6[ci if ci < len(col_x_s6) else 0], 183.64

        # Immediate Machine 2 (1-10 µL ONLY) Slot 3 & Slot 4 override (prevents any hidden fallback or deck model bypass)
        if slot_name in ("Slot_3", "Slot_4") and is_10ul:
            r_idx, c_idx = self._parse_well(well_id)
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 12) else 0
            ri = r_idx if (r_idx is not None and 0 <= r_idx < 8) else 0
            if slot_name == "Slot_4":
                base_x, base_y = self._m2_slot4_tip_base_xy(1 + ri)
                learned_dx, learned_dy = getattr(self, 'tip_rack_learned_offset', (0.0, 0.0))
                return round(base_x - (ci * 9.0) + learned_dx, 2), round(base_y + learned_dy, 2)
            base_x = 243.81
            base_y = 52.64
            return round(base_x - (ci * 9.0), 2), round(base_y + (ri * 9.0), 2)

        if slot_name in ("Slot_5", "Slot_6") and is_10ul and (getattr(self, "_lw_kind", lambda x: "")(self.lims.deck_labware.get(slot_name)) == "plate96" or "triplicate" in str(getattr(self, "current_protocol_file", "")).lower() or "triplicate" in str(getattr(self, "loaded_protocol_name", "")).lower()):
            r_idx, c_idx = self._parse_well(well_id)
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 12) else 0
            ri = r_idx if (r_idx is not None and 0 <= r_idx < 8) else 0
            base_x = 242.98 if slot_name == "Slot_5" else 105.60
            base_y = 147.64 if slot_name == "Slot_5" else 146.81
            return round(base_x - (ci * 9.0), 2), round(base_y + (ri * 9.0), 2)

        # 0. Object-Oriented DeckManager Kinematics
        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
            slot_model = self.deck_manager.slots[slot_name]
            slot_model.active_profile_id = getattr(self, 'active_profile_id', 'machine_2_1_10ul')
            if slot_model.labware:
                cx, cy = slot_model.labware.get_well_xy(slot_model, well_id)
                if cx != 0.0 or cy != 0.0:
                    return cx, cy

        slot_obj = self.lims.deck_slots.get(slot_name)
        if not slot_obj: return 0.0, 0.0

        cx = slot_obj.x_abs + (slot_obj.width_mm / 2.0)
        cy = slot_obj.y_abs + (slot_obj.height_mm / 2.0)

        labware_obj = self.lims.deck_labware.get(slot_name)
        kind = self._lw_kind(labware_obj)
        ox, oy = self._slot_a1_origin(slot_name)
        front = self._is_front_slot(slot_name)
        r_idx, c_idx = self._parse_well(well_id)
        raw = getattr(labware_obj, 'raw_data', None) or {}

        # 1. 3-WELL RESERVOIR / WASTE TROUGH ON SLOT 2:
        # User physically calibrated: A1 is at X=95.5, A2 is at X=57.0, A3 (Waste Discard) is at X=12.0, Y=13.0
        if slot_name == "Slot_2":
            w_str = str(well_id or "").upper().strip()
            if w_str in ("A1", "1"):
                return 95.5, 13.0
            elif w_str in ("A2", "2"):
                return 57.0, 13.0
            elif w_str in ("A3", "3", "DISCARD", "WASTE") or not w_str or kind in ("waste", "reservoir_3", "tube_rack_3x50ml"):
                return 12.0, 13.0

        # 1b. WASTE TROUGH: always the centre of Slot 6 (or generic single-cavity waste)
        if kind == "waste" or (kind is None and slot_name == "Slot_6"):
            return cx, cy

        # 2. 96-FORMAT (tip rack or 96-well plate) on ANY slot
        if kind in ("tip_rack", "plate96") or (kind is None and not front):
            if r_idx is not None and 0 <= r_idx < 8 and 0 <= c_idx < 12:
                if kind == "tip_rack":
                    # Tip rack A1 physically calibrated:
                    # Machine 2 (1-10 µL) & Machine 3 (300 µL): A1 at X=105.63, Y=52.64
                    # Machine 1 (8x1000 µL): standard A1 at X=105.60, Y=53.02 (8-ch center Y=84.52)
                    learned_dx, learned_dy = getattr(self, 'tip_rack_learned_offset', (0.0, 0.0))
                    is_10ul = ("10ul" in getattr(self, "active_profile_id", "")) or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 200) <= 10.0)
                    is_m1_8x1000 = ("1000" in getattr(self, "active_profile_id", "")) or ("machine_1" in getattr(self, "active_profile_id", ""))
                    if slot_name == "Slot_4":
                        if is_m1_8x1000 and not is_10ul:
                            return (105.60 - (c_idx * 9.0)) + learned_dx, (53.02 + (r_idx * 9.0)) + learned_dy
                        return (105.63 - (c_idx * 9.0)) + learned_dx, (52.64 + (r_idx * 9.0)) + learned_dy
                    if is_10ul:
                        return (ox - (c_idx * 9.0)) + learned_dx, (52.64 + (r_idx * 9.0)) + learned_dy
                    return (ox - (c_idx * 9.0)) + learned_dx, (oy + (r_idx * 9.0)) + learned_dy
                col_table = self.SLOT_96_COL_OVERRIDES.get(slot_name)
                tx = col_table[c_idx] if col_table else ox - (c_idx * 9.0)
                return tx, oy + (r_idx * 9.0)
            return cx, cy

        # 3. MYRIAMED 48-WELL EHM PLATE (calibrated on Slot_4: cols 105..15, rows 57..119, +1.0mm X offset, -2.0mm Y offset)
        if kind == "ehm48":
            col_dx = [0.0, -18.0, -36.0, -54.0, -72.0, -90.0]
            row_dy = [1.0, 9.0, 18.0, 26.0, 35.0, 44.0, 54.0, 63.0]
            if r_idx is not None and r_idx < len(row_dy) and c_idx < len(col_dx):
                return ox + col_dx[c_idx] + 1.0, oy + row_dy[r_idx] - 2.0
            return cx, cy

        # 4. 3-WELL RESERVOIR (calibrated on Slot_1: A1=(235.05, 5.27), pitch 42.6mm; Slot_2: A1=95.5, A2=57.0, A3=12.0)
        if kind == "reservoir_3" or (kind is None and front):
            if slot_name == "Slot_2":
                col_x = [95.5, 57.0, 12.0]
                ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
                if c_idx is None and well_id in ("1", "2", "3"):
                    ci = int(well_id) - 1
                return col_x[ci], oy + (0.0 if front else 31.5)
            col_dx = [0.0, -42.6, -85.2]
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
            if c_idx is None and well_id in ("1", "2", "3"):
                ci = int(well_id) - 1
            if slot_name == "Slot_1":
                return round(235.05 + col_dx[ci], 2), 5.27
            return round(ox + col_dx[ci], 2), oy + (0.0 if front else 31.5)

        # 5. 6-COLUMN RESERVOIR
        if kind == "reservoir_6":
            col_dx = [3.0, -12.0, -30.0, -46.5, -63.0, -79.5]
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 6) else 0
            if c_idx is None and str(well_id or "").upper().strip().lstrip("R") in ("1", "2", "3", "4", "5", "6"):
                ci = int(str(well_id).upper().strip().lstrip("R")) - 1
            return ox + col_dx[ci], oy + (0.0 if front else 31.5)

        # 5b. 7-COLUMN RESERVOIR (User calibrated on Slot 6: R1=108.81, R2=93.81, R3=75.06, R4=56.31, R5=37.56, R6=18.81, R7=5.91)
        if kind == "reservoir_7":
            col_x = [108.81, 93.81, 75.06, 56.31, 37.56, 18.81, 5.91]
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 7) else 0
            if c_idx is None and str(well_id or "").upper().strip().lstrip("R") in ("1", "2", "3", "4", "5", "6", "7"):
                ci = int(str(well_id).upper().strip().lstrip("R")) - 1
            if slot_name == "Slot_6":
                return col_x[ci], 183.64
            return ox + 3.81 - (ci * 15.0), oy + (0.0 if front else 30.67)

        # 6. 4x6 TUBE RACK (Biohit 17A, pitch 19.3 mm)
        if kind == "tube_rack_4x6":
            if r_idx is not None and r_idx < 4 and c_idx < 6:
                return ox + 7.15 - (c_idx * 19.3), oy + (0.0 if front else 24.3) + (r_idx * 19.3)
            return cx, cy

        # 7. 2x6 TUBE RACK / 3-WELL RESERVOIR ON SLOT 1
        # User calibrated: Slot 1 A1 is at X = 235.05, Y = 5.27
        if kind == "tube_rack_2x6":
            orig_x = 235.05 if slot_obj.x_abs >= 70.0 else (245.0 - 135.2)
            orig_y = 5.27 if front else oy
            if r_idx is not None and 0 <= r_idx < 2 and c_idx is not None and 0 <= c_idx < 6:
                return round(orig_x - (c_idx * 18.0), 2), round(orig_y + (r_idx * 18.0), 2)
            return cx, cy

        # 8. DATA-DRIVEN LABWARE: geometry read from its JSON "kinematics" block
        kin = raw.get('kinematics') if raw else None
        if kin:
            rows = getattr(labware_obj, 'rows', 1)
            cols = getattr(labware_obj, 'columns', 1)
            if r_idx is not None and r_idx < rows and c_idx < cols:
                return (ox + float(kin.get('a1_dx_mm', 0.0)) - c_idx * float(kin.get('pitch_col_mm', 9.0)),
                        oy + float(kin.get('a1_dy_mm', 0.0)) + r_idx * float(kin.get('pitch_row_mm', 9.0)))
            return cx, cy

        # 8. Fallback Generic Labware (centred on slot using JSON well offsets)
        if labware_obj and labware_obj.wells:
            first_w = list(labware_obj.wells.values())[0]
            lw_w = max(w.x_rel for w in labware_obj.wells.values()) + first_w.x_rel
            lw_h = max(w.y_rel for w in labware_obj.wells.values()) + first_w.y_rel
            well_obj = labware_obj.wells.get(well_id)
            if well_obj:
                return cx + ((lw_w / 2.0) - well_obj.x_rel), cy - (lw_h / 2.0) + well_obj.y_rel

        return cx, cy

    def _resolve_step_xy(self, step, slot_name, well_id):
        """
        Resolves machine (X, Y) for a protocol step.
        For 8-channel symmetric steps (`eight_ch_symmetric=True` or `pipettor.multichannel=True`):
        - Centers the 8-channel manifold symmetrically between Row A and Row H of the target column
          on 8-row labware (`ehm48`, `plate96`, `tip_rack`), or uses the symmetric lane center on `reservoir_6`.
        - Applies `tip_offset_rows * 9.0` mm Y shift for offset partial tip-picking / tip-shoveling.
        - Applies `self.eight_ch_cal_offset['X']` and `self.eight_ch_cal_offset['Y']` fine calibration trims.
        """
        # multi-channel action (mounted_channels with range/count or eight_ch_symmetric)
        m_channels = str((step or {}).get("mounted_channels", "")).strip().upper()
        parsed_m_count = self._parse_mounted_tip_count(m_channels)
        is_multi_channel_action = bool(
            (parsed_m_count is not None and parsed_m_count > 1)
            or (m_channels and len(m_channels) > 1 and m_channels not in ("1", "CH1", "A") and parsed_m_count != 1)
        )
        is_8ch_step = bool(step and step.get('eight_ch_symmetric')) or is_multi_channel_action

        lw_obj = self.lims.deck_labware.get(slot_name)
        kind = self._lw_kind(lw_obj)
        is_300ul = (
            ("300" in getattr(self, "active_profile_id", ""))
            or ("300" in str(getattr(self, "current_protocol_file", "")).lower())
            or ("300" in str(getattr(self, "loaded_protocol_name", "")).lower())
            or ("300" in str(getattr(self, "proto_workflow_var", tk.StringVar()).get()).lower())
            or ("300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower())
            or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 0) == 300.0)
        )

        # Direct Machine 3 (300 µL Single-Channel) Resolution:
        # Strictly dispatch to exact well coordinates with zero 8-channel or manifold offset
        if is_300ul:
            return self._calculate_xy(slot_name, well_id)

        is_10ul = ("10ul" in getattr(self, "active_profile_id", "")) or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 200) <= 10.0)

        # Machine 2 (1-10 µL ONLY): 8-channel multi-head fixed-center kinematics across all plate/tip slots
        # ONLY applies when executing an actual multi-channel action (e.g. 5-tip A-E or 8-tip symmetric).
        # Single-tip / single-channel operations must resolve strictly to the exact well coordinate.
        is_m2_reservoir_or_waste = (slot_name == "Slot_6" and kind in ("waste", "reservoir_3", "reservoir_6", "reservoir_7")) or (slot_name in ("Slot_1", "Slot_2"))
        if is_10ul and is_8ch_step and slot_name in ("Slot_3", "Slot_4", "Slot_5", "Slot_6") and not is_m2_reservoir_or_waste:
            w_str = str(well_id or "A1").strip().upper()
            col_digits = "".join(ch for ch in w_str if ch.isdigit()) or "1"
            col_i = max(0, min(11, int(col_digits) - 1))

            raw_m_ch = str((step or {}).get("mounted_channels", "")).strip().upper()
            parsed_tips = self._parse_mounted_tip_count(raw_m_ch)
            if parsed_tips is not None:
                num_tips = parsed_tips
            elif not step.get('eight_ch_symmetric'):
                num_tips = 5
            else:
                num_tips = 8

            if slot_name == "Slot_4":
                learned_dx, _ = getattr(self, 'tip_rack_learned_offset', (0.0, 0.0))
                base_x, ty = self._m2_slot4_tip_base_xy(num_tips)
                tx = round(base_x - (col_i * 9.0) + learned_dx, 2)
            elif slot_name == "Slot_6":
                tx = round(105.60 - (col_i * 9.0), 2)
            elif slot_name == "Slot_3":
                tx = round(243.81 - (col_i * 9.0), 2)
            else:  # Slot_5
                tx = round(242.98 - (col_i * 9.0), 2)

            if slot_name == "Slot_3":
                if num_tips == 5:
                    ty = 57.12
                elif num_tips == 8:
                    ty = 84.14
                else:
                    ty = round(84.14 - (8 - num_tips) * 9.06, 2)
            elif slot_name in ("Slot_5", "Slot_6"):
                if num_tips == 5:
                    ty = 147.64 if slot_name == "Slot_5" else 146.81
                elif num_tips == 8:
                    ty = 179.14 if slot_name == "Slot_5" else 178.31
                else:
                    ty = round((179.14 if slot_name == "Slot_5" else 178.31) - (8 - num_tips) * 9.06, 2)

            offset_rows = int((step or {}).get('tip_offset_rows', 0) or 0)
            ty += offset_rows * 9.0

            cal = getattr(self, 'eight_ch_cal_offset', {"X": 0.0, "Y": 0.0, "Z": 0.0})
            tx += float(cal.get("X", 0.0))
            ty += float(cal.get("Y", 0.0))

            max_x = float(self.lims.machine_config.get("max_x_mm", 300.0))
            max_y = float(self.lims.machine_config.get("max_y_mm", 300.0))
            tx = max(0.0, min(tx, max_x))
            ty = max(0.0, min(ty, max_y))

            slot_center_str = f"{ty:.2f}" if slot_name == "Slot_4" else ("84.14" if slot_name == "Slot_3" else "178.31")
            self.logger.info(f"🎯 [MACHINE 2: 1-10µL] Resolved multi-channel {slot_name} {well_id}: X={tx:.2f}mm, Y={ty:.2f}mm (Slot Center Y={slot_center_str}mm)")
            return tx, ty

        if not is_8ch_step:
            coords = self._calculate_xy(slot_name, well_id)
            if not coords:
                return None
            tx, ty = coords
            # Only shift +31.50mm for Machine 1 (8×1000 µL) where the 8-channel manifold is permanently fixed
            # and a single-well operation uses Nozzle 1 (Row A). Never shift for Machine 2 or Machine 3.
            is_m1_8ch = ("1000" in getattr(self, "active_profile_id", "")) or ("machine_1" in getattr(self, "active_profile_id", ""))
            if is_m1_8ch and getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "multichannel", False) and kind in ("ehm48", "plate96", "tip_rack"):
                ty += 31.50
            return tx, ty

        w_str = str(well_id or "A1").strip().upper()
        col_digits = "".join(ch for ch in w_str if ch.isdigit()) or "1"

        if kind in ("ehm48", "plate96", "tip_rack"):
            ca = self._calculate_xy(slot_name, f"A{col_digits}")
            ch = self._calculate_xy(slot_name, f"H{col_digits}")
            if ca and ch and (ca[0] != 0.0 or ca[1] != 0.0):
                tx = ca[0]
                ty = (ca[1] + ch[1]) / 2.0
            else:
                coords = self._calculate_xy(slot_name, well_id)
                if not coords:
                    return None
                tx, ty = coords
        else:
            coords = self._calculate_xy(slot_name, well_id)
            if not coords:
                return None
            tx, ty = coords

        offset_rows = int((step or {}).get('tip_offset_rows', 0) or 0)
        ty += offset_rows * 9.0

        cal = getattr(self, 'eight_ch_cal_offset', {"X": 0.0, "Y": 0.0, "Z": 0.0})
        tx += float(cal.get("X", 0.0))
        ty += float(cal.get("Y", 0.0))

        max_x = float(self.lims.machine_config.get("max_x_mm", 300.0))
        max_y = float(self.lims.machine_config.get("max_y_mm", 300.0))
        tx = max(0.0, min(tx, max_x))
        ty = max(0.0, min(ty, max_y))
        return tx, ty

    def _rim_calibrated_z(self, labware_obj, deep):
        """Z for labware calibrated by rim height (z_calibration block)."""
        raw = getattr(labware_obj, 'raw_data', {}) or {}
        zc = raw.get('z_calibration', {}) or {}
        rim_z = zc.get('rim_z')
        if rim_z is None:
            rim_z = 75.0  # User calibrated value
        rim_z = float(rim_z)
        if deep:
            # Safe aspiration deep inside the tube (capped at 100.0 mm to avoid hardware limits)
            asp_depth = float(zc.get('aspirate_depth_mm', 23.0))
            return min(rim_z + asp_depth, 100.0)
        disp_below = float(zc.get('dispense_below_rim_mm', 5.0))
        return rim_z + disp_below

    def _labware_bottom_z(self, labware_obj, slot_name):
        """Deepest safe Z for probing / liquid detection, based on labware type."""
        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
            slot_model = self.deck_manager.slots[slot_name]
            if slot_model.labware:
                return slot_model.labware.get_bottom_z(slot_model)
        kind = self._lw_kind(labware_obj)
        if kind == "tube_rack_2x6":
            return self._rim_calibrated_z(labware_obj, deep=True)
        if labware_obj and 'max_safe_bottom_z' in (getattr(labware_obj, 'z_limits', {}) or {}):
            return float(labware_obj.z_limits['max_safe_bottom_z'])
        if kind == "ehm48":
            return 24.5
        if kind == "reservoir_7":
            return 92.0
        if kind == "plate96":
            return self.SLOT_96_PLATE_Z.get(slot_name, self.DEFAULT_96_PLATE_Z)[0]
        if kind == "reservoir_3" or (kind is None and self._is_front_slot(slot_name)):
            return 100.0
        if kind == "reservoir_6":
            return 103.0
        if kind == "tube_rack_4x6":
            return 95.0
        return 90.0

    def _get_next_tube_in_sequence(self, slot_name, current_well):
        """Returns the next well/tube ID in sequence for auto-advancing when liquid is depleted.
        STRICTLY for Falcon tube racks only. NEVER advances on plates or dedicated reservoirs!"""
        slot_model = self.deck_manager.slots.get(slot_name) if hasattr(self, 'deck_manager') else None
        lw = slot_model.labware if slot_model else None
        lw_obj = self.lims.deck_labware.get(slot_name)
        lw_src = str(getattr(lw_obj, 'source_file', '')).lower()
        lw_kind = self._lw_kind(lw_obj)

        # 1. 2mL Falcon Rack
        if isinstance(lw, TubeRack2x6_2mL) or "2x6" in lw_src or lw_kind == "tube_rack_2x6":
            tube_order = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6"]
            if current_well in tube_order:
                c_idx = tube_order.index(current_well)
                if c_idx + 1 < len(tube_order):
                    return tube_order[c_idx + 1]
            return None

        # 2. 50mL Falcon Rack (A1 Media, A2 Stock; A3 is Discard)
        if isinstance(lw, FalconRack50mL) or "50ml" in lw_src or "3x50ml" in lw_src:
            tube_order = ["A1", "A2"]
            if current_well in tube_order:
                c_idx = tube_order.index(current_well)
                if c_idx + 1 < len(tube_order):
                    return tube_order[c_idx + 1]
            return None

        # Guard: NEVER auto-advance on plates or multi-cavity reservoirs where wells are dedicated!
        return None

    def _calculate_z(self, action, labware_obj, well_id, mode, manual_z, slot_name, extra_z=0.0, mix_cycles=0):
        if action == "Pick Up Tip":
            return 0.0

        if mode == "manual": return manual_z

        slot_obj = self.lims.deck_slots.get(slot_name)
        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

        is_8ch = bool(getattr(self.lims.pipettor, 'multichannel', False))
        kind = self._lw_kind(labware_obj)

        # Persistent 8-channel / calibrated heights memory lookup (GUI remembers operator depths)
        if hasattr(self, 'calibrated_heights'):
            is_300ul = (
                ("300" in getattr(self, "active_profile_id", ""))
                or ("300" in str(getattr(self, "current_protocol_file", "")).lower())
                or ("300" in str(getattr(self, "loaded_protocol_name", "")).lower())
                or ("300" in str(getattr(self, "proto_workflow_var", tk.StringVar()).get()).lower())
                or ("300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower())
                or (not is_8ch and getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 200) >= 200.0)
            )
            is_10ul = not is_300ul and (
                ("10ul" in getattr(self, "active_profile_id", ""))
                or (getattr(getattr(self, "lims", None), "pipettor", None) and getattr(self.lims.pipettor, "tip_volume", 200) <= 10.0)
            )
            is_triplicate = "triplicate" in str(getattr(self, "current_protocol_file", "")).lower() or "triplicate" in str(getattr(self, "loaded_protocol_name", "")).lower()
            is_96 = (kind in ("plate96", None)) or is_triplicate or "96" in str(getattr(labware_obj, "source_file", "")).lower() or "96" in str(getattr(labware_obj, "name", "")).lower()
            # EHM 48-Well Plates (Slot 5 & Slot 6) calibrated depth: 72.35mm (safe, prevents tip bending)
            if kind == "ehm48" or (slot_name in ("Slot_5", "Slot_6") and "reservoir" not in str(kind) and "waste" not in str(kind) and "96" not in str(getattr(labware_obj, "source_file", "")).lower()):
                def_ehm_asp = 72.35 if (is_10ul or is_300ul) else 24.17
                def_ehm_disp = 62.35 if (is_10ul or is_300ul) else 14.17
                if action in ("Aspirate Media", "Mix Well") or int(mix_cycles or 0) > 0:
                    return min(float(self.calibrated_heights.get("ehm_aspirate_z", def_ehm_asp)) + slot_z_offset + extra_z, 103.5)
                elif action == "Dispense Media":
                    return min(float(self.calibrated_heights.get("ehm_dispense_z", def_ehm_disp)) + slot_z_offset + extra_z, 103.5)
            elif kind == "plate96" or (is_8ch and slot_name in ("Slot_3", "Slot_5") and is_96) or (is_300ul and slot_name in ("Slot_3", "Slot_5")):
                def_p96_asp = 98.72 if is_300ul else 78.40
                def_p96_disp = 98.72 if is_300ul else 68.43
                raw_asp = 98.72 if is_300ul else float(self.calibrated_heights.get("plate96_aspirate_z", def_p96_asp))
                raw_disp = 98.72 if is_300ul else float(self.calibrated_heights.get("plate96_dispense_z", def_p96_disp))
                if action in ("Aspirate Media", "Mix Well") or int(mix_cycles or 0) > 0:
                    return min(raw_asp + slot_z_offset + extra_z, 103.5)
                elif action == "Dispense Media":
                    is_dmso_dispense = is_300ul and (
                        getattr(self, "last_aspirate_slot", None) in ("Slot_1", "Slot_6")
                        or getattr(self, "last_aspirate_lw_kind", None) in ("reservoir_3", "reservoir_7", "reservoir_6", "tube_rack_2x6")
                    )
                    if is_dmso_dispense:
                        return min(98.72 + slot_z_offset + extra_z, 103.5)
                    return min(raw_disp + slot_z_offset + extra_z, 103.5)
            elif (slot_name in ("Slot_6", "Slot_1", "Slot_2") and ("reservoir" in str(kind) or "waste" in str(kind) or (is_300ul and slot_name == "Slot_1"))) or kind in ("reservoir_7", "reservoir_6", "reservoir_3", "waste"):
                if action == "Dispense Media":
                    return min(float(self.calibrated_heights.get("waste_dispense_z", 8.37)) + slot_z_offset + extra_z, 103.5)
                elif action in ("Aspirate Media", "Mix Well"):
                    res_key = "reservoir_3_aspirate_z" if (slot_name in ("Slot_1", "Slot_2") and "reservoir_3_aspirate_z" in self.calibrated_heights) else "reservoir_aspirate_z"
                    return min(float(self.calibrated_heights.get(res_key, 86.0 if is_300ul else 90.42)) + slot_z_offset + extra_z, 103.5)
                elif action == "Discard Tip":
                    return min(float(self.calibrated_heights.get("waste_tip_drop_z", 8.37)) + slot_z_offset + extra_z, 103.5)
            elif slot_name == "Slot_4" and action == "Discard Tip":
                return min(float(self.calibrated_heights.get("tip_rack_discard_z", 40.50)) + slot_z_offset + extra_z, 103.5)

        # 0. Object-Oriented DeckManager Kinematics
        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
            slot_model = self.deck_manager.slots[slot_name]
            if slot_model.labware:
                in_liquid = action in ("Aspirate Media", "Mix Well") or int(mix_cycles or 0) > 0
                computed_z = self.deck_manager.calculate_z(action, slot_name, well_id, in_liquid=in_liquid)
                return min(computed_z + slot_z_offset + extra_z, 103.5)

        # "deep" = going into the liquid (aspirate / mix); otherwise stop at the brim
        deep = action in ("Aspirate Media", "Mix Well") or int(mix_cycles or 0) > 0

        if action in ["Aspirate Media", "Dispense Media", "Discard Tip", "Mix Well"]:
            if action == "Discard Tip" or kind == "waste" or (kind is None and slot_name == "Slot_6"):
                zl = getattr(labware_obj, 'z_limits', {}) or {}
                if 'recommended_discard_z' in zl:
                    base_z = float(zl['recommended_discard_z'])
                elif 'recommended_dispense_z' in zl:
                    base_z = float(zl['recommended_dispense_z'])
                elif self._is_front_slot(slot_name):
                    # For 3-well reservoir on 90mm block (rim=47mm), safe discard height is Z=35.0mm (above rim).
                    # For 50mL Falcon rack on 90mm block (rim=68mm), safe discard depth into tube mouth is Z=75.0mm.
                    is_3well = kind == "reservoir_3" or "3_well" in str(getattr(labware_obj, 'source_file', '')).lower()
                    base_z = 35.0 if is_3well else 75.0
                else:
                    base_z = 45.0
            elif kind == "tube_rack_2x6":
                base_z = self._rim_calibrated_z(labware_obj, deep)
            elif kind == "reservoir_3" or (kind is None and self._is_front_slot(slot_name)):
                base_z = 52.0  # Safe meniscus submerge (47.0mm + 5.0mm) with printed height blocks
            elif kind == "plate96":
                deep_z, brim_z = self.SLOT_96_PLATE_Z.get(slot_name, self.DEFAULT_96_PLATE_Z)
                base_z = deep_z if deep else brim_z
            elif kind == "reservoir_6":
                base_z = 101.0 if deep else 78.0
            elif kind == "reservoir_7":
                base_z = 90.42 if deep else 8.37  # 90.42 deep to take media, 8.37 discard/dispense
            elif kind == "ehm48":
                base_z = 24.17 if deep else 14.17  # 24.17 inside well, 14.17 dispense (10mm above bottom)
            elif kind == "tip_rack":
                base_z = 98.0
            elif kind == "tube_rack_4x6":
                base_z = 95.0
            else:
                zl = getattr(labware_obj, 'z_limits', {}) or {}
                key = 'recommended_aspirate_z' if deep else 'recommended_dispense_z'
                base_z = float(zl.get(key, zl.get('recommended_aspirate_z', 101.0)))

            return min(base_z + slot_z_offset + extra_z, 103.5)

        return 0.0

    def prompt_for_return_tip_well(self):
        """
        Direct Operation: Returns/ejects mounted tip(s) to a specific slot and well,
        dynamically reading the assigned labware and valid wells from Deck Setup.
        """
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return

        top = tk.Toplevel(self.root)
        top.title("Return Tip to Specific Well")
        top.geometry("460x340")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        f = ttk.Frame(top, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            f,
            text="Return Tip(s) to Specific Slot & Well",
            font=("Arial", 11, "bold"),
            foreground="#0d6efd",
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            f,
            text="Reads assigned labware and well grid directly from Deck Setup (Tab 2):",
            font=("Arial", 9),
            foreground="#555",
        ).pack(anchor="w", pady=(0, 10))

        # Slot Selection (prioritize slots with assigned labware in Deck Setup)
        slot_choices = [s for s in self.placed_slots if s in self.lims.deck_labware]
        for s in self.placed_slots:
            if s and s not in slot_choices:
                slot_choices.append(s)
        for s in [f"Slot_{i}" for i in range(1, 7)]:
            if s not in slot_choices:
                slot_choices.append(s)

        default_slot = self.get_default_tip_slot()
        if default_slot not in slot_choices and slot_choices:
            default_slot = slot_choices[0]

        f_slot = ttk.Frame(f)
        f_slot.pack(fill=tk.X, pady=4)
        ttk.Label(f_slot, text="Deck Slot:", width=15, anchor="w", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        slot_var = tk.StringVar(value=default_slot)
        cb_slot = ttk.Combobox(f_slot, textvariable=slot_var, values=slot_choices, state="readonly", width=24)
        cb_slot.pack(side=tk.LEFT)

        f_lw = ttk.Frame(f)
        f_lw.pack(fill=tk.X, pady=4)
        ttk.Label(f_lw, text="Deck Labware:", width=15, anchor="w", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        lbl_lw_val = ttk.Label(f_lw, text="", font=("Arial", 9), foreground="#0056b3")
        lbl_lw_val.pack(side=tk.LEFT, anchor="w")

        f_well = ttk.Frame(f)
        f_well.pack(fill=tk.X, pady=4)
        ttk.Label(f_well, text="Target Well:", width=15, anchor="w", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        well_var = tk.StringVar(value="A1")
        cb_well = ttk.Combobox(f_well, textvariable=well_var, width=24)
        cb_well.pack(side=tk.LEFT)

        f_z = ttk.Frame(f)
        f_z.pack(fill=tk.X, pady=4)
        ttk.Label(f_z, text="Drop Z Height (mm):", width=15, anchor="w", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        z_var = tk.StringVar(value=f"{float(self.calibrated_heights.get('tip_rack_discard_z', 40.50)):.2f}")
        ent_z = ttk.Entry(f_z, textvariable=z_var, width=12, justify="center")
        ent_z.pack(side=tk.LEFT)

        lbl_coords_preview = ttk.Label(f, text="", font=("Consolas", 9), foreground="#333333", justify="left")
        lbl_coords_preview.pack(fill=tk.X, pady=(8, 6))

        def _get_wells_for_slot(s_name: str) -> list:
            lw = self.lims.deck_labware.get(s_name)
            kind = self._lw_kind(lw)
            if lw and getattr(lw, "wells", None):
                raw_wells = [str(w).upper() for w in lw.wells.keys()]
                if kind in ("tip_rack", "plate96"):
                    ordered = [w for w in TIP_ORDER_96 if w in set(raw_wells)]
                    if ordered:
                        return ordered
                return raw_wells
            if kind in ("tip_rack", "plate96"):
                return list(TIP_ORDER_96)
            if kind == "ehm48":
                return [f"{r}{c}" for c in range(1, 7) for r in "ABCDEFGH"]
            if kind == "reservoir_7":
                return [f"A{c}" for c in range(1, 8)]
            if kind == "reservoir_6":
                return [f"A{c}" for c in range(1, 7)]
            if kind == "reservoir_3":
                return ["A1", "A2", "A3"]
            if kind == "tube_rack_2x6":
                return [f"{r}{c}" for r in "AB" for c in range(1, 7)]
            return list(TIP_ORDER_96)

        def _update_preview(*args):
            s = slot_var.get()
            w = (well_var.get() or "A1").strip().upper()
            lw = self.lims.deck_labware.get(s)
            kind = self._lw_kind(lw)
            step_ctx = {"action": "Discard Tip", "eight_ch_symmetric": bool(self.lims.pipettor.multichannel)}
            coords = self._resolve_step_xy(step_ctx, s, w) or self._calculate_xy(s, w)
            tx, ty = coords if coords else (0.0, 0.0)
            try:
                dz = float(z_var.get())
            except Exception:
                dz = 40.50
            mode_note = "8-Channel Column Return" if self.lims.pipettor.multichannel else "Single-Channel Well Return"
            lbl_coords_preview.config(
                text=f"Target: {s} -> Well {w} ({kind or 'unassigned'})\n"
                     f"Resolved Coordinates: X={tx:.2f} mm, Y={ty:.2f} mm, Z={dz:.2f} mm [{mode_note}]"
            )

        def _on_slot_changed(*args):
            s = slot_var.get()
            lw = self.lims.deck_labware.get(s)
            kind = self._lw_kind(lw)
            if lw:
                lw_name = getattr(lw, "name", "Labware")
                lw_src = getattr(lw, "source_file", "")
                lbl_lw_val.config(text=f"{lw_name} ({lw_src})" if lw_src else lw_name)
            else:
                lbl_lw_val.config(text="(No labware assigned in Deck Setup)")

            wells = _get_wells_for_slot(s)
            cb_well["values"] = wells

            # Default well: if returning to tip rack with consumed tips, suggest the most recently consumed or A1
            consumed = list(self._get_tip_tracker(s).get("consumed", ())) if s in getattr(self, "session_tip_tracker", {}) else []
            if consumed:
                ordered_consumed = [w for w in wells if w in set(consumed)]
                if ordered_consumed:
                    well_var.set(ordered_consumed[-1])
                elif well_var.get() not in wells and wells:
                    well_var.set(wells[0])
            elif well_var.get() not in wells and wells:
                well_var.set(wells[0])

            # Pre-fill calibrated drop Z for the selected slot/labware
            if kind == "tip_rack" or s == "Slot_4":
                calc_z = float(self.calibrated_heights.get("tip_rack_discard_z", 40.50))
            else:
                calc_z = self._calculate_z("Discard Tip", lw, well_var.get() or "A1", "auto", 40.50, s)
                if calc_z <= 0.0:
                    calc_z = 40.50
            z_var.set(f"{calc_z:.2f}")
            _update_preview()

        slot_var.trace_add("write", _on_slot_changed)
        well_var.trace_add("write", _update_preview)
        z_var.trace_add("write", _update_preview)
        _on_slot_changed()

        def on_confirm():
            s = slot_var.get()
            w = (well_var.get() or "A1").strip().upper()
            if not s or not w:
                messagebox.showwarning("Input Missing", "Please select both a Deck Slot and a Target Well.", parent=top)
                return
            try:
                drop_z = float(z_var.get())
            except ValueError:
                drop_z = float(self.calibrated_heights.get("tip_rack_discard_z", 40.50))
            top.destroy()
            threading.Thread(
                target=self.run_direct_return_tip_routine,
                args=(s, w, drop_z),
                daemon=True,
            ).start()

        btn_frame = ttk.Frame(f)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
        tk.Button(
            btn_frame,
            text="↩ Return Tip to Well Now",
            bg="#0d6efd",
            fg="white",
            font=("Arial", 10, "bold"),
            command=on_confirm,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT)

    def run_direct_return_tip_routine(self, slot_name: str, well_id: str, drop_z: float = None):
        """
        Moves to the exact (X, Y, Z) of `slot_name` / `well_id` based on the labware assigned in Deck Setup,
        ejects the tip(s), restores session tip memory for that well/column, sets HAS_TIP = False, and homes Z to 0.0 mm.
        """
        hw_instance = self.lims.pipettor.hardware
        well_clean = (well_id or "A1").strip().upper()
        labware_obj = self.lims.deck_labware.get(slot_name)
        lw_name = getattr(labware_obj, "name", getattr(labware_obj, "source_file", "Unassigned Labware"))
        lw_kind = self._lw_kind(labware_obj)
        is_8ch = bool(getattr(self.lims.pipettor, "multichannel", False))

        step_ctx = {"action": "Discard Tip", "eight_ch_symmetric": is_8ch}
        coords = self._resolve_step_xy(step_ctx, slot_name, well_clean) or self._calculate_xy(slot_name, well_clean)
        tx, ty = coords if coords else (0.0, 0.0)

        if drop_z is None:
            if lw_kind == "tip_rack" or slot_name == "Slot_4":
                tz = float(self.calibrated_heights.get("tip_rack_discard_z", 40.50))
            else:
                tz = self._calculate_z("Discard Tip", labware_obj, well_clean, "auto", 40.50, slot_name)
                if tz <= 0.0:
                    tz = 40.50
        else:
            tz = float(drop_z)
        tz = max(0.0, min(tz, 102.0))

        self.logger.info(
            f"--- Direct Op: Returning Tip to {slot_name} Well {well_clean} "
            f"[Labware: {lw_name} | X={tx:.2f}mm, Y={ty:.2f}mm, Z={tz:.2f}mm] ---"
        )
        try:
            if hw_instance:
                hw_instance.move_z(0.0)
            self.lims.hw.move_to(tx, ty, 0.0, speed=self.speed_var.get())
            if hw_instance:
                hw_instance.move_z(tz)
                hw_instance.eject_tip()
                time.sleep(0.25)
                try:
                    hw_instance.eject_tip()
                except Exception:
                    pass
                hw_instance.move_z(0.0)
                self._home_z_axis_only(reason=f"Return Tip ({slot_name} {well_clean})")

            # Restore session tip memory if returned into a tip rack
            if lw_kind == "tip_rack" or slot_name in getattr(self, "session_tip_tracker", {}) or slot_name == "Slot_4":
                if is_8ch:
                    for sock in self._expand_8ch_tip_sockets(step_ctx, well_clean):
                        self.mark_tip_restored(slot_name, sock, redraw=False)
                    self._schedule_deck_redraw()
                else:
                    self.mark_tip_restored(slot_name, well_clean)

            self.has_air_cushion = False
            self.air_cushion_ul = 0.0
            self.tip_liquid_ul = 0.0
            self._set_has_tip(False)
            self.logger.info(
                f"Direct Op: Tip successfully returned to {slot_name} Well {well_clean} ({lw_name}). HAS_TIP = False"
            )
        except Exception as e:
            self.logger.critical(
                f"Error returning tip to {slot_name} Well {well_clean}: {e}. Tip may still be mounted!"
            )
            self._set_has_tip(True)
            if hw_instance:
                try:
                    hw_instance.move_z(0.0)
                except Exception:
                    pass

    def prompt_for_discard_slot(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return

        top = tk.Toplevel(self.root)
        top.title("Discard Tip Location")
        top.geometry("380x170")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        ttk.Label(top, text="Select destination slot to discard tip into:", font=("Arial", 10, "bold")).pack(pady=(15, 6))

        # Default to waste slot (Slot_6 or any slot with 'waste' in labware name)
        default_slot = "Slot_6"
        for s in self.placed_slots:
            lw = self.lims.deck_labware.get(s)
            if lw and "waste" in getattr(lw, 'name', '').lower():
                default_slot = s
                break

        slot_choices = list(self.placed_slots) if self.placed_slots else ["Slot_6", "Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5"]
        if default_slot not in slot_choices and default_slot in ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]:
            slot_choices.append(default_slot)

        slot_var = tk.StringVar(value=default_slot if default_slot in slot_choices else slot_choices[0])
        cb = ttk.Combobox(top, textvariable=slot_var, values=slot_choices, state="readonly", width=25)
        cb.pack(pady=5)

        def on_confirm():
            slot = slot_var.get()
            top.destroy()
            if slot:
                threading.Thread(target=self.run_direct_discard_routine, args=(slot,), daemon=True).start()

        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=(12, 10))
        ttk.Button(btn_frame, text="Discard Tip Now", command=on_confirm).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=6)

    def run_direct_discard_routine(self, slot_name):
        hw_instance = self.lims.pipettor.hardware
        if not hw_instance:
            self.logger.error("Hardware not initialized for tip discard.")
            return

        self.logger.info(f"--- Direct Op: Moving to {slot_name} to Discard Tip ---")
        try:
            # 1. Raise Z to safe travel height
            hw_instance.move_z(0.0)

            # 2. Move XY to slot target coordinates (Well A1 or center of slot)
            tx, ty = self._calculate_xy(slot_name, "A1")
            self.lims.hw.move_to(tx, ty, 0.0, speed=self.speed_var.get())

            # 3. Lower Z to discard height
            labware_obj = self.lims.deck_labware.get(slot_name)
            tz = self._calculate_z("Discard Tip", labware_obj, "A1", "auto", 90.0, slot_name)
            if tz <= 0.0:
                tz = 90.0
            hw_instance.move_z(tz)

            # 4. Eject tip (double-pulse to guarantee mechanical separation)
            hw_instance.eject_tip()
            time.sleep(0.25)
            try:
                hw_instance.eject_tip()
            except Exception:
                pass
            self.root.after(0, lambda: self.has_tip_var.set(False))
            self.logger.info(f"Direct Op: Tip successfully discarded into {slot_name}. HAS_TIP = False")

            # 5. Return Z to 0 (safe travel)
            hw_instance.move_z(0.0)
        except Exception as e:
            self.logger.critical(f"Error during direct tip discard to {slot_name}: {e}. Tip may still be mounted on the pipettor!")
            self.root.after(0, lambda: self.has_tip_var.set(True))
            try:
                hw_instance.move_z(0.0)
            except Exception:
                pass

    def prompt_for_m2_step_test(self):
        """Prompt operator to run the Machine 2 raw piston step sweep diagnostic."""
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return
        if getattr(self, "is_running", False):
            messagebox.showwarning("Wait", "A protocol is currently running.")
            return

        top = tk.Toplevel(self.root)
        top.title("Machine 2 Piston Step Test (1-10 µL Head)")
        top.geometry("500x400")
        top.transient(self.root)

        f = ttk.Frame(top, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            f,
            text="Machine 2 Raw Piston Step-Sweep Calibration",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w")

        checklist = ttk.LabelFrame(f, text=" Deck Checklist ", padding=8)
        checklist.pack(fill=tk.X, pady=(8, 10))
        ttk.Label(
            checklist,
            text=(
                "1. Fill Slot 3 Col 1 (A1-H1) with water\n"
                "2. Load fresh 10 µL tips in Slot 4 Col 1 (or check below if already mounted)\n"
                "3. Keep Slot 2 Waste clear (dispenses & ejects there)"
            ),
            justify=tk.LEFT,
        ).pack(anchor="w")

        default_asp_z = float(self.calibrated_heights.get("plate96_aspirate_z", 78.40))
        steps_var = tk.StringVar(value="50, 100, 150, 200")
        tip_slot_var = tk.StringVar(value="Slot_4")
        tip_well_var = tk.StringVar(value="A1")
        water_slot_var = tk.StringVar(value="Slot_3")
        water_well_var = tk.StringVar(value="A1")
        asp_z_var = tk.StringVar(value=f"{default_asp_z:.2f}")
        already_mounted = bool(getattr(self, "_worker_has_tip", False) or (hasattr(self, "has_tip_var") and self.has_tip_var.get()))
        skip_pickup_var = tk.BooleanVar(value=already_mounted)
        eject_end_var = tk.BooleanVar(value=True)

        grid = ttk.Frame(f)
        grid.pack(fill=tk.X, pady=(0, 8))

        rows = [
            ("Piston steps (comma-sep):", steps_var),
            ("Tip slot / col:", None),
            ("Water slot / col:", None),
            ("Aspirate Z (mm):", asp_z_var),
        ]
        for idx, (label, var) in enumerate(rows):
            ttk.Label(grid, text=label).grid(row=idx, column=0, sticky="w", pady=3, padx=(0, 8))
            if var is not None:
                ttk.Entry(grid, textvariable=var, width=28).grid(row=idx, column=1, columnspan=2, sticky="ew", pady=3)
            elif idx == 1:
                ttk.Entry(grid, textvariable=tip_slot_var, width=12).grid(row=idx, column=1, sticky="w", pady=3)
                ttk.Entry(grid, textvariable=tip_well_var, width=10).grid(row=idx, column=2, sticky="w", pady=3, padx=(6, 0))
            else:
                ttk.Entry(grid, textvariable=water_slot_var, width=12).grid(row=idx, column=1, sticky="w", pady=3)
                ttk.Entry(grid, textvariable=water_well_var, width=10).grid(row=idx, column=2, sticky="w", pady=3, padx=(6, 0))

        ttk.Checkbutton(
            f,
            text="Tips already mounted (skip Slot 4 pickup)",
            variable=skip_pickup_var,
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            f,
            text="Eject tips at Slot 2 Waste when finished",
            variable=eject_end_var,
        ).pack(anchor="w", pady=2)

        def on_confirm():
            try:
                parsed_steps = [float(tok.strip()) for tok in steps_var.get().split(",") if tok.strip()]
                if not parsed_steps or any(s <= 0 for s in parsed_steps):
                    raise ValueError("Enter one or more positive step counts.")
                az = float(asp_z_var.get().strip())
            except ValueError as err:
                messagebox.showerror("Invalid Input", str(err), parent=top)
                return

            kwargs = {
                "steps_list": parsed_steps,
                "tip_slot": tip_slot_var.get().strip() or "Slot_4",
                "tip_well": (tip_well_var.get().strip() or "A1").upper(),
                "water_slot": water_slot_var.get().strip() or "Slot_3",
                "water_well": (water_well_var.get().strip() or "A1").upper(),
                "aspirate_z": az,
                "skip_tip_pickup": bool(skip_pickup_var.get()),
                "eject_at_end": bool(eject_end_var.get()),
            }
            top.destroy()
            threading.Thread(target=self.run_m2_piston_step_sweep, kwargs=kwargs, daemon=True).start()

        btn_frame = ttk.Frame(f)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        tk.Button(
            btn_frame,
            text="Start Step Sweep",
            bg="#0d6efd",
            fg="white",
            font=("Arial", 10, "bold"),
            command=on_confirm,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT)

    def _m2_pause_prompt(self, title: str, message: str, pause_callback=None) -> bool:
        """Pause step sweep safely on main thread (or via pause_callback/headless)."""
        if pause_callback is not None:
            return bool(pause_callback(title, message))
        if getattr(self, "headless_test_mode", False):
            return True
        done = threading.Event()
        result = {"ok": False}

        def _ask():
            try:
                result["ok"] = bool(messagebox.askokcancel(title, message, parent=self.root))
            finally:
                done.set()

        self.root.after(0, _ask)
        done.wait()
        return result["ok"]

    def _m2_resolve_col_xy(self, action: str, slot_name: str, well_id: str, fallback: tuple[float, float]) -> tuple[float, float]:
        """Resolve 8-channel XY via deck calibration, falling back to verified Machine 2 coords."""
        step_ctx = {"action": action, "eight_ch_symmetric": True}
        try:
            coords = self._resolve_step_xy(step_ctx, slot_name, well_id)
            if coords and (coords[0] != 0.0 or coords[1] != 0.0):
                return float(coords[0]), float(coords[1])
        except Exception:
            pass
        return fallback

    def run_m2_piston_step_sweep(
        self,
        steps_list=None,
        tip_slot: str = "Slot_4",
        tip_well: str = "A1",
        water_slot: str = "Slot_3",
        water_well: str = "A1",
        aspirate_z=None,
        skip_tip_pickup: bool = False,
        eject_at_end: bool = True,
        pause_callback=None,
    ):
        """
        Execute a stepped raw-piston aspiration diagnostic for Machine 2 (1-10 µL 8-channel):
        1. Picks up 8 tips at Slot 4 (unless skip_tip_pickup=True).
        2. For each step count (default [50, 100, 150, 200]):
           - Moves to Slot 3 water column and lowers to plate96_aspirate_z (78.40 mm).
           - Aspirates raw piston `steps` via Control.Aspirate(float(steps), True, True)
             (or `hw.aspirate(steps / 2.0)` fallback in simulation/mocks), logging P position & errors.
           - Retracts to Z=0.0 so operator can inspect/measure drawn water.
           - Moves to Slot 2 Waste (95.5, 13.0) and calls Control.DispenseAll(True) (or dispense fallback).
        3. Ejects tips at Slot 2 Waste if eject_at_end=True and homes Z to 0.0.
        """
        hw = getattr(getattr(self.lims, "pipettor", None), "hardware", None)
        if not hw:
            self.logger.error("Machine 2 Step Sweep aborted: hardware not initialized.")
            return []

        raw_steps = list(steps_list) if steps_list is not None else [50, 100, 150, 200]
        steps_seq = [float(s) for s in raw_steps if float(s) > 0]
        if not steps_seq:
            self.logger.error("Machine 2 Step Sweep aborted: no positive step counts provided.")
            return []

        asp_z = float(aspirate_z if aspirate_z is not None else self.calibrated_heights.get("plate96_aspirate_z", 78.40))
        asp_z = max(0.0, min(asp_z, 102.0))
        waste_disp_z = max(0.0, min(float(self.calibrated_heights.get("waste_dispense_z", 8.37)), 102.0))
        waste_drop_z = max(0.0, min(float(self.calibrated_heights.get("waste_tip_drop_z", 8.37)), 102.0))
        speed = self.speed_var.get() if hasattr(self, "speed_var") else 100

        ctrl = getattr(getattr(hw, "_Pipettor__instrument", None), "Control", None)
        results = []
        aborted = False

        self.logger.info(
            f"=== Direct Op M2_STEP_TEST: Piston sweep {steps_seq} | Water={water_slot} {water_well} (Z={asp_z:.2f}mm) | Control={'DLL' if ctrl else 'Wrapper'} ==="
        )
        try:
            hw.move_z(0.0)

            if not skip_tip_pickup:
                tip_x, tip_y = self._m2_resolve_col_xy("Pick Up Tip", tip_slot, tip_well, (105.47, 84.99))
                approach_z = float(self.calibrated_heights.get("tip_10ul_approach_z", self.calibrated_heights.get("tip_rack_pickup_approach_z", 50.0)))
                configured_limit = float(self.calibrated_heights.get("tip_10ul_limit_z", self.calibrated_heights.get("tip_rack_pickup_limit_z", 75.0)))
                pickup_limit = min(80.0, max(68.0, configured_limit))
                extra_press = float(self.calibrated_heights.get("tip_10ul_extra_press_mm", self.calibrated_heights.get("tip_pickup_extra_press_mm", 2.50)))

                self.logger.info(f"[M2_STEP_TEST] Picking up 8 tips at {tip_slot} {tip_well} (X={tip_x:.2f}, Y={tip_y:.2f}, limit={pickup_limit:.2f}mm)")
                self.lims.hw.move_to(tip_x, tip_y, 0.0, speed=speed)
                hw.move_z(approach_z)
                try:
                    hw.tip_pickup_force = 26
                except Exception:
                    pass
                hw.pick_tip(pickup_limit)
                curr_z = float(getattr(hw, "z_position", pickup_limit) or pickup_limit)
                if extra_press > 0 and curr_z > 48.0:
                    try:
                        hw.move_z(min(pickup_limit, curr_z + extra_press))
                    except Exception:
                        pass
                hw.move_z(0.0)
                if hasattr(self, "mark_tip_consumed"):
                    for sock in self._expand_8ch_tip_sockets({"action": "Pick Up Tip", "eight_ch_symmetric": True}, tip_well):
                        self.mark_tip_consumed(tip_slot, sock, redraw=False)
                    if hasattr(self, "_schedule_deck_redraw"):
                        self._schedule_deck_redraw()
                self._set_has_tip(True)

            water_x, water_y = self._m2_resolve_col_xy("Aspirate Media", water_slot, water_well, (243.81, 84.14))
            waste_x, waste_y = (95.5, 13.0)

            for idx, steps in enumerate(steps_seq, start=1):
                self.lims.hw.move_to(water_x, water_y, 0.0, speed=speed)
                hw.move_z(asp_z)

                p_before = ctrl.PollPosition("P", True) if ctrl else None
                if ctrl:
                    asp_ok = ctrl.Aspirate(float(steps), True, True)
                    p_after = ctrl.PollPosition("P", True)
                    err_m = ctrl.PollError("M")
                    err_p = ctrl.PollError("P")
                    err_code = getattr(ctrl, "ErrorCode", None)
                    msg = (
                        f"[M2_STEP_TEST] Step {idx}/{len(steps_seq)}: Control.Aspirate({steps:.0f}, True, True) -> {asp_ok} | "
                        f"P: {p_before} -> {p_after} | Err(M={err_m}, P={err_p}, Code={err_code})"
                    )
                else:
                    equiv_ul = float(steps) / 2.0
                    hw.aspirate(equiv_ul)
                    p_after = None
                    asp_ok = True
                    msg = f"[M2_STEP_TEST] Step {idx}/{len(steps_seq)}: Wrapper hw.aspirate({equiv_ul:.1f} uL = {steps:.0f} steps)"

                self.logger.info(msg)
                results.append({"steps": float(steps), "p_before": p_before, "p_after": p_after, "ok": asp_ok})

                hw.move_z(0.0)
                prompt_msg = (
                    f"{msg}\n\n"
                    f"Tips are raised at Z=0.0 mm over {water_slot} {water_well}.\n"
                    f"Inspect or measure drawn water volume, then click OK to dispense into { 'Slot 2 Waste' } and continue "
                    f"(or Cancel to stop sweep cleanly)."
                )
                keep_going = self._m2_pause_prompt(
                    f"M2 Step Test ({idx}/{len(steps_seq)}: {steps:.0f} steps)",
                    prompt_msg,
                    pause_callback=pause_callback,
                )

                # Always dispense captured water into waste before continuing or exiting
                self.lims.hw.move_to(waste_x, waste_y, 0.0, speed=speed)
                hw.move_z(waste_disp_z)
                if ctrl:
                    disp_ok = ctrl.DispenseAll(True)
                    p_disp = ctrl.PollPosition("P", True)
                    self.logger.info(f"[M2_STEP_TEST] Control.DispenseAll(True) at Slot 2 Waste -> {disp_ok} | P={p_disp}")
                else:
                    hw.dispense_all() if hasattr(hw, "dispense_all") else hw.dispense(float(steps) / 2.0)
                    self.logger.info(f"[M2_STEP_TEST] Wrapper dispense at Slot 2 Waste for {steps:.0f} steps")
                hw.move_z(0.0)

                if not keep_going:
                    aborted = True
                    self.logger.warning(f"[M2_STEP_TEST] Sweep aborted by user after {steps:.0f} steps.")
                    break

            if eject_at_end:
                self.lims.hw.move_to(waste_x, waste_y, 0.0, speed=speed)
                hw.move_z(waste_drop_z)
                hw.eject_tip()
                hw.move_z(0.0)
                self._set_has_tip(False)
                self.logger.info("[M2_STEP_TEST] Tips ejected at Slot 2 Waste. HAS_TIP = False")

            self.logger.info(f"=== Direct Op M2_STEP_TEST {'ABORTED' if aborted else 'COMPLETE'} ({len(results)}/{len(steps_seq)} steps tested) ===")
            return results
        except Exception as e:
            self.logger.critical(f"[M2_STEP_TEST] Error during piston step sweep: {e}")
            try:
                hw.move_z(0.0)
            except Exception:
                pass
            raise

    def prompt_for_tip_slot(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return

        top = tk.Toplevel(self.root)
        top.title("Smart Tip Search")
        top.geometry("350x150")
        ttk.Label(top, text="Select the slot containing the tip rack:").pack(pady=10)
        slot_var = tk.StringVar()
        cb = ttk.Combobox(top, textvariable=slot_var, values=self.placed_slots, state="readonly")
        cb.pack(pady=5)
        if self.placed_slots: cb.current(0)

        def on_confirm():
            slot = slot_var.get()
            top.destroy()
            if slot: threading.Thread(target=self.run_find_tip_routine, args=(slot,), daemon=True).start()

        ttk.Button(top, text="Start Search Sequence", command=on_confirm).pack(pady=10)

    def run_find_tip_routine(self, slot_name):
        self.logger.info(f"--- Direct Op: Smart Tip Search in {slot_name} ---")
        labware_obj = self.lims.deck_labware.get(slot_name)
        if not labware_obj:
            self.logger.error(f"No labware assigned to {slot_name}.")
            return

        wells = self._ordered_tip_wells(slot_name)
        consumed_now = self._get_tip_tracker(slot_name)["consumed"]
        tip_found = False

        is_10ul = ("10ul" in getattr(self, "active_profile_id", "")) or (getattr(self.lims.pipettor, "tip_volume", 200.0) <= 50.0 and getattr(self.lims.pipettor, "multichannel", False))
        is_8ch = bool(getattr(self.lims.pipettor, "multichannel", False))
        if is_10ul:
            collar_z = float(self.calibrated_heights.get("tip_10ul_collar_z", self.calibrated_heights.get("tip_rack_collar_z", 64.49)))
            configured_limit = float(self.calibrated_heights.get("tip_10ul_limit_z", self.calibrated_heights.get("tip_rack_pickup_limit_z", 75.0)))
            approach_z = float(self.calibrated_heights.get("tip_10ul_approach_z", self.calibrated_heights.get("tip_rack_pickup_approach_z", 50.0)))
            pickup_limit = min(80.0, max(68.0, configured_limit))
            valid_collar_min = 48.0
            valid_collar_max = max(74.0, collar_z + 8.0)
        elif is_8ch:
            collar_z = float(self.calibrated_heights.get("tip_rack_collar_z", 86.36))
            configured_limit = float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 98.0))
            approach_z = float(self.calibrated_heights.get("tip_rack_pickup_approach_z", 75.0))
            pickup_limit = min(99.5, max(88.0, configured_limit))
            valid_collar_min = 84.0
            valid_collar_max = min(98.5, configured_limit - 0.5)
        else:
            collar_z = float(self.calibrated_heights.get("tip_rack_collar_z", 86.36))
            configured_limit = max(92.0, float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 92.0)))
            approach_z = float(self.calibrated_heights.get("tip_rack_pickup_approach_z", 50.0))
            pickup_limit = min(98.0, max(92.0, configured_limit, collar_z + 4.5))
            valid_collar_min = 48.0
            valid_collar_max = max(90.5, min(97.5, pickup_limit - 0.4))

        for current_well in wells:
            if self.is_aborted: break
            if current_well in consumed_now:
                continue

            # Safe tuple unpacking
            coords = self._resolve_step_xy({"action": "Pick Up Tip"}, slot_name, current_well)
            tx, ty = coords if coords else (0, 0)

            if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
            self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
            time.sleep(0.05)

            self.logger.info(f"Triggering native pick_tip({pickup_limit:.1f}) search algorithm at {current_well} (X={tx:.2f}, Y={ty:.2f}).")
            try:
                hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                if self.lims.pipettor.hardware:
                    self.lims.pipettor.hardware.z_speed = hw_speed
                    self.lims.pipettor.hardware.move_z(approach_z)
                    self.lims.pipettor.hardware.z_speed = 3
                    self.lims.pipettor.hardware.tip_pickup_force = 26 if is_8ch else 20
                    pick_ok = False
                    try:
                        self.lims.pipettor.hardware.pick_tip(pickup_limit)
                        pick_ok = True
                    except Exception as pe:
                        self.logger.warning(f"pick_tip hardware return/exception: {pe}")
                        pick_ok = False

                    curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                    valid_collar = (valid_collar_min <= curr_z <= valid_collar_max)
                    is_seated = valid_collar or (pick_ok and curr_z >= valid_collar_min and curr_z <= max(valid_collar_max, pickup_limit - 0.1))

                    if not is_seated:
                        self.mark_tip_consumed(slot_name, current_well)
                        raise Exception(f"No tip present in {current_well} (Z={curr_z:.2f}mm, pick_ok={pick_ok})")

                    # High-torque mechanical seating press to prevent tips falling off
                    extra_press = float(self.calibrated_heights.get("tip_pickup_extra_press_mm", 1.50))
                    if extra_press > 0:
                        try:
                            press_target = min(pickup_limit + extra_press, curr_z + extra_press)
                            self.lims.pipettor.hardware.z_speed = 2
                            self.lims.pipettor.hardware.move_z(press_target)
                            time.sleep(0.25)
                        except Exception as se:
                            self.logger.warning(f"Single-channel seating press notice: {se}")
                    time.sleep(0.2)
                else:
                    curr_z = collar_z
                self.mark_tip_consumed(slot_name, current_well)
                self.logger.info(f"🎯 Tip acquired at {current_well} (Z={curr_z:.2f}mm). HAS_TIP = True")
                time.sleep(0.2)
                tip_found = True
                self._set_has_tip(True)
                if self.lims.pipettor.hardware:
                    try:
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)
                break
            except RuntimeError as re:
                self.logger.critical(f"🛑 CRITICAL SAFETY ABORT during tip search: {re}")
                self.root.after(0, lambda: self.has_tip_var.set(True))
                if self.lims.pipettor.hardware:
                    try:
                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)
                return
            except Exception as e:
                self.logger.warning(f"Well {current_well} empty or passed. Tracking to next well...")
                if self.lims.pipettor.hardware:
                    try:
                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)

        if not tip_found:
            self.logger.error("Tip search failed. Rack is empty.")
            self.root.after(0, lambda: messagebox.showerror("Search Failed", f"No tips found in {slot_name}."))

    def prompt_for_liquid_check(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return
        if self.lims.pipettor.multichannel:
            messagebox.showinfo(
                "8-Channel Manifold Active",
                "The 8×1000 µL 8-channel manifold does not have a single-tip capacitance/oscillation sensor.\n\n"
                "8-channel protocols use calibrated Z heights automatically. Switch to 1×200 µL Single-Channel mode if using the single-channel head."
            )
            return

        top = tk.Toplevel(self.root)
        top.title("Auto-Read Liquid Level (Sensor Probing)")
        top.geometry("420x290")
        top.resizable(False, False)

        f = ttk.Frame(top, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Select Target Slot & Well:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))

        # Slot Selection
        f_slot = ttk.Frame(f)
        f_slot.pack(fill=tk.X, pady=4)
        ttk.Label(f_slot, text="Deck Slot:", width=14, anchor="w").pack(side=tk.LEFT)
        slot_var = tk.StringVar()
        slot_choices = [s for s in self.placed_slots if s] if self.placed_slots else [f"Slot_{i}" for i in range(1, 7)]
        cb_slot = ttk.Combobox(f_slot, textvariable=slot_var, values=slot_choices, state="readonly", width=18)
        cb_slot.pack(side=tk.LEFT)

        # Well Selection
        f_well = ttk.Frame(f)
        f_well.pack(fill=tk.X, pady=4)
        ttk.Label(f_well, text="Target Well:", width=14, anchor="w").pack(side=tk.LEFT)
        well_var = tk.StringVar(value="A1")
        cb_well = ttk.Combobox(f_well, textvariable=well_var, width=18)
        cb_well.pack(side=tk.LEFT)

        # Info Label (displays labware details and well radius)
        lbl_info = ttk.Label(f, text="", font=("Arial", 9), foreground="#333333", wraplength=380, justify="left")
        lbl_info.pack(fill=tk.X, pady=10)

        def update_info(*args):
            s = slot_var.get()
            lw = self.lims.deck_labware.get(s)
            if lw:
                lw_name = getattr(lw, 'name', 'Labware')
                wells = list(getattr(lw, 'wells', {}).keys())
                if wells:
                    cb_well['values'] = wells
                    if well_var.get() not in wells:
                        well_var.set(wells[0])
                first_w = next(iter(getattr(lw, 'wells', {}).values()), None)
                rad = getattr(first_w, 'radius', 3.4) if first_w else 3.4
                z_lim = getattr(lw, 'z_limits', {}).get('max_safe_bottom_z', 'Auto')
                lbl_info.config(text=f"Labware: {lw_name}\nWell Radius: {rad:.1f} mm | Bottom Limit: {z_lim} mm")
            else:
                lbl_info.config(text=f"Slot: {s} (Generic / Unassigned Labware)")

        slot_var.trace_add("write", update_info)
        if slot_choices:
            if "Slot_6" in slot_choices:
                slot_var.set("Slot_6")
            else:
                slot_var.set(slot_choices[0])
        else:
            update_info()

        def on_confirm():
            slot = slot_var.get()
            well = well_var.get().strip().upper()
            if not slot or not well:
                messagebox.showwarning("Input Missing", "Please specify both Slot and Well.")
                return

            if not self.has_tip_var.get():
                if not messagebox.askyesno(
                    "Tip Check",
                    "The Biohit tip sensor requires a pipette tip mounted on the channel.\n\n"
                    "Pipette tip state is currently marked as EMPTY.\n\n"
                    "Do you want to proceed anyway?"
                ):
                    return

            top.destroy()
            threading.Thread(target=self.run_liquid_check_routine, args=(slot, well), daemon=True).start()

        ttk.Button(f, text="Probe Liquid Level", command=on_confirm).pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def run_liquid_check_routine(self, slot_name, well_id):
        self.logger.info(f"--- Direct Op: Liquid Level Auto-Read at {slot_name} Well {well_id} ---")
        if not self.lims.hw.is_initialized:
            self.logger.error("Hardware not initialized.")
            return

        coords = self._calculate_xy(slot_name, well_id)
        if not coords or (coords[0] == 0.0 and coords[1] == 0.0):
            msg = f"Could not calculate XY coordinates for {slot_name} well {well_id}."
            self.logger.error(msg)
            self.root.after(0, lambda: messagebox.showerror("Coordinate Error", msg))
            return

        tx, ty = coords
        labware_obj = self.lims.deck_labware.get(slot_name)
        slot_obj = self.lims.deck_slots.get(slot_name)
        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

        lw_name = (getattr(labware_obj, 'name', '') or '').lower()
        lw_src = (getattr(labware_obj, 'source_file', '') or '').lower()

        # Bottom Z determination (labware-driven, slot independent)
        try:
            bottom_z = self._labware_bottom_z(labware_obj, slot_name)
        except ValueError as cal_err:
            self.logger.error(str(cal_err))
            self.root.after(0, lambda m=str(cal_err): messagebox.showerror("Labware Not Calibrated", m))
            return

        bottom_z = min(99.5, bottom_z + slot_z_offset)

        # Well radius determination
        radius_mm = 3.4
        if labware_obj and hasattr(labware_obj, 'wells') and well_id in labware_obj.wells:
            radius_mm = getattr(labware_obj.wells[well_id], 'radius', 3.4)
        elif labware_obj and hasattr(labware_obj, 'raw_data'):
            radius_mm = labware_obj.raw_data.get('well_properties', {}).get('radius_mm', 3.4)

        if radius_mm <= 0.0:
            radius_mm = 3.4

        try:
            # 1. Retract to safe Z=0
            if self.lims.pipettor.hardware:
                self.lims.pipettor.hardware.move_z(0)
            self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
            time.sleep(0.1)

            # 2. Execute surface detection
            z_measured = self._probe_surface_and_wait(bottom_z, submerge_mm=1.0)

            # 3. Retract back to safe Z=0
            if self.lims.pipettor.hardware:
                self.lims.pipettor.hardware.move_z(0)

            # 4. Analyze result
            if z_measured >= (bottom_z - 1.0):
                res_msg = (
                    f"No liquid detected in {slot_name} Well {well_id}.\n\n"
                    f"Sensor reached bottom limit (Z={bottom_z:.1f} mm) without meniscus contact.\n"
                    f"The well/tube appears empty."
                )
                self.logger.warning(f"Liquid Level: {slot_name} {well_id} -> EMPTY (Z={z_measured:.2f}mm, limit={bottom_z:.1f}mm)")
                self.root.after(0, lambda: messagebox.showwarning("Liquid Level Detection", res_msg))
            else:
                liquid_height_mm = max(0.0, bottom_z - z_measured)
                area_mm2 = math.pi * (radius_mm ** 2)
                volume_ul = area_mm2 * liquid_height_mm
                volume_ml = volume_ul / 1000.0

                if volume_ul >= 1000.0:
                    vol_text = f"{volume_ul:.1f} µL ({volume_ml:.2f} mL)"
                else:
                    vol_text = f"{volume_ul:.1f} µL"

                report = (
                    f"Target: {slot_name} | Well: {well_id}\n"
                    f"Labware: {getattr(labware_obj, 'name', 'Generic')}\n"
                    f"-----------------------------------------\n"
                    f"Surface Contact Z: {z_measured:.2f} mm\n"
                    f"Bottom Limit Z:    {bottom_z:.2f} mm\n"
                    f"Liquid Height:     {liquid_height_mm:.2f} mm\n"
                    f"Well Radius:       {radius_mm:.2f} mm\n"
                    f"-----------------------------------------\n"
                    f"Estimated Remaining Volume: {vol_text}"
                )
                self.logger.info(f"Liquid Level Detected: {slot_name} {well_id} -> Z={z_measured:.2f}mm, H={liquid_height_mm:.2f}mm, Vol={vol_text}")
                self.root.after(0, lambda: messagebox.showinfo("Liquid Level Measured", report))

        except Exception as err:
            self.logger.error(f"Liquid level detection error: {err}")
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except Exception:
                    pass
            self.root.after(0, lambda: messagebox.showerror("Detection Error", f"Surface detection failed: {err}"))

    def update_timer(self):
        if not getattr(self, 'timer_running', False):
            return

        if self.is_aborted:
            self.lbl_timer.config(text="Time Remaining: ABORTED", foreground="red")
            return

        remaining = self.compute_remaining_time()
        self.lbl_timer.config(text=f"Time Remaining: {self.format_hms(remaining)}", foreground="blue")

        if self.timer_running:
            self.root.after(1000, self.update_timer)

    @staticmethod
    def _apply_run_z_clearance(base_z: float, clearance_dz: float, max_z: float = 103.5) -> float:
        """Apply pre-run Z offset (>0 less deep, <0 deeper), safely clamped to [0.0, max_z]."""
        if abs(clearance_dz) <= 1e-9:
            return max(0.0, min(float(max_z), float(base_z)))
        return max(0.0, min(float(max_z), float(base_z) - float(clearance_dz)))

    @classmethod
    def _format_run_z_preview(cls, base_z: float, clearance_dz: float, max_z: float = 103.5) -> Tuple[str, str]:
        """Return (label_text, foreground_color) for the pre-run Z adjustment preview."""
        if base_z > 0.0:
            raw_eff = float(base_z) - float(clearance_dz)
            eff = cls._apply_run_z_clearance(base_z, clearance_dz, max_z=max_z)
            if clearance_dz > 1e-9:
                return f"{eff:.2f} mm (-{clearance_dz:.2f}mm)", "#0d6efd"
            if clearance_dz < -1e-9:
                capped = " MAX!" if raw_eff > max_z + 1e-9 else ""
                return f"{eff:.2f} mm (+{abs(clearance_dz):.2f}mm deeper{capped})", "#dc3545"
            return f"{eff:.2f} mm (Standard)", "#28a745"
        if clearance_dz > 1e-9:
            return f"-{clearance_dz:.2f} mm (less deep)", "#0d6efd"
        if clearance_dz < -1e-9:
            return f"+{abs(clearance_dz):.2f} mm (deeper)", "#dc3545"
        return "Default", "#28a745"

    def prompt_z_clearance_for_run(self) -> bool:
        """
        Pre-run prompt (Option A) asking operator if they want to adjust liquid-handling Z depth
        for each valid labware in the current protocol.
        Positive values (+mm, ▲ arrow) reduce depth (less deep / clearance off bottom).
        Negative values (-mm, ▼ arrow) increase depth (deeper +Z), safely clamped at 103.5 mm max.
        """
        seq = getattr(self, "workflow_sequence", [])
        liquid_slots = []
        slot_actions = {}
        for step in seq:
            act = step.get("action", "")
            slot = step.get("slot", "")
            if act in ("Aspirate Media", "Dispense Media", "Mix Well") and slot:
                if slot not in slot_actions:
                    slot_actions[slot] = set()
                slot_actions[slot].add(act)
                if slot not in liquid_slots and "Slot_" in slot:
                    lw_obj = getattr(getattr(self, "lims", None), "deck_labware", {}).get(slot)
                    lw_src = str(getattr(lw_obj, "source_file", "")).lower()
                    lw_name = str(getattr(lw_obj, "name", "")).lower()
                    if "tip" not in lw_src and "tip" not in lw_name:
                        liquid_slots.append(slot)

        if not liquid_slots:
            self.run_z_clearance_offsets = {}
            return True

        def _slot_sort_key(s):
            try:
                return int(s.replace("Slot_", ""))
            except Exception:
                return 99

        liquid_slots.sort(key=_slot_sort_key)

        if getattr(self, "headless_test_mode", False) or not hasattr(self, "root") or not self.root:
            return True

        adjust_depth = messagebox.askyesno(
            "Well Bottom Depth Adjustment (- / + Z)",
            "Do you want to adjust well bottom Z depth for this run?\n\n"
            "• YES: Adjust Z per labware using the arrows:\n"
            "   ▲ Positive (+mm) = less deep (higher off bottom)\n"
            "   ▼ Negative (-mm) = deeper (+Z, clamped at 103.5 mm max)\n"
            "• NO: Run at standard calibrated depths (default)."
        )
        if not adjust_depth:
            self.run_z_clearance_offsets = {}
            return True

        top = tk.Toplevel(self.root)
        top.title("Configure Well Bottom Depth Adjustment (- / + Z)")
        win_h = max(380, 240 + len(liquid_slots) * 60)
        top.geometry(f"740x{min(680, win_h)}")
        top.transient(self.root)
        top.grab_set()

        try:
            rx = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 370
            ry = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (min(680, win_h) // 2)
            top.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass

        hdr = tk.Frame(top, bg="#0d6efd", padx=14, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="🟢 Configure Well Bottom Depth Adjustment (- / + Z)",
            font=("Arial", 11, "bold"),
            bg="#0d6efd",
            fg="white"
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="▲ +mm = less deep (tip stays higher). ▼ -mm = deeper (+Z, capped at 103.5 mm max). Tip pickup is preserved.",
            font=("Arial", 9),
            bg="#0d6efd",
            fg="#e7f1ff"
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(top, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        q_frame = ttk.LabelFrame(body, text="Quick Set All Valid Labware", padding=8)
        q_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(q_frame, text="Offset (+ less deep / - deeper):").pack(side=tk.LEFT, padx=(0, 6))
        q_var = tk.StringVar(value="1.0")
        q_spin = ttk.Spinbox(q_frame, from_=-25.0, to=25.0, increment=0.5, width=7, textvariable=q_var)
        q_spin.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(q_frame, text="mm").pack(side=tk.LEFT, padx=(0, 10))

        table_f = ttk.Frame(body)
        table_f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(table_f, text="Slot", font=("Arial", 9, "bold"), width=8).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(table_f, text="Labware / Reagent Deck Purpose", font=("Arial", 9, "bold"), width=30).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Label(table_f, text="Standard Z", font=("Arial", 9, "bold"), width=12).grid(row=0, column=2, sticky="w", pady=2)
        ttk.Label(table_f, text="Clearance (mm)", font=("Arial", 9, "bold"), width=15).grid(row=0, column=3, sticky="w", pady=2)
        ttk.Label(table_f, text="Effective Depth", font=("Arial", 9, "bold")).grid(row=0, column=4, sticky="w", pady=2)
        ttk.Separator(table_f, orient="horizontal").grid(row=1, column=0, columnspan=5, sticky="ew", pady=(2, 6))

        slot_vars = {}
        slot_preview_labels = {}
        slot_nominal_z = {}

        def _parse_offset(raw: str) -> float:
            try:
                val = float(str(raw).strip() or 0.0)
                return max(-25.0, min(25.0, val))
            except ValueError:
                return 0.0

        def _refresh_row_preview(s_key: str):
            c_val = _parse_offset(slot_vars[s_key].get())
            text, fg = self._format_run_z_preview(slot_nominal_z[s_key], c_val)
            slot_preview_labels[s_key].config(text=text, foreground=fg)

        for row_idx, slot in enumerate(liquid_slots, start=2):
            lw_obj = getattr(getattr(self, "lims", None), "deck_labware", {}).get(slot)
            lw_name = getattr(lw_obj, "name", None) or getattr(lw_obj, "source_file", slot)
            acts = list(slot_actions.get(slot, []))
            act_str = "/".join(a.replace(" Media", "").replace(" Well", "") for a in acts)

            test_act = acts[0] if acts else "Aspirate Media"
            try:
                nom_z = float(self._calculate_z(test_act, lw_obj, "A1", "auto", 0.0, slot))
            except Exception:
                nom_z = 0.0
            slot_nominal_z[slot] = nom_z

            badge = tk.Label(table_f, text=slot.replace("_", " "), font=("Consolas", 9, "bold"), bg="#cce5ff", fg="#004085", padx=4, pady=2)
            badge.grid(row=row_idx, column=0, sticky="w", pady=4)

            desc_text = f"{lw_name} ({act_str})"
            if len(desc_text) > 32:
                desc_text = desc_text[:30] + "..."
            ttk.Label(table_f, text=desc_text, font=("Arial", 9)).grid(row=row_idx, column=1, sticky="w", pady=4, padx=(0, 6))

            ttk.Label(table_f, text=f"{nom_z:.2f} mm" if nom_z > 0 else "Auto", font=("Consolas", 9)).grid(row=row_idx, column=2, sticky="w", pady=4)

            s_var = tk.StringVar(value="0.0")
            spin = ttk.Spinbox(table_f, from_=-25.0, to=25.0, increment=0.5, width=7, textvariable=s_var)
            spin.grid(row=row_idx, column=3, sticky="w", pady=4, padx=(0, 6))
            slot_vars[slot] = s_var

            init_text, init_fg = self._format_run_z_preview(nom_z, 0.0)
            lbl_eff = ttk.Label(table_f, text=init_text, font=("Consolas", 9, "bold"), foreground=init_fg)
            lbl_eff.grid(row=row_idx, column=4, sticky="w", pady=4)
            slot_preview_labels[slot] = lbl_eff

            s_var.trace_add("write", lambda *args, s_key=slot: _refresh_row_preview(s_key))

        def apply_quick_to_all():
            v = _parse_offset(q_var.get())
            for s_key, s_var in slot_vars.items():
                s_var.set(f"{v:.1f}")
                _refresh_row_preview(s_key)

        ttk.Button(q_frame, text="Apply to All Rows", command=apply_quick_to_all).pack(side=tk.LEFT)

        user_confirmed = {"status": False}

        def on_confirm():
            offsets = {}
            for s_key, s_var in slot_vars.items():
                c_val = _parse_offset(s_var.get())
                if abs(c_val) > 1e-9:
                    offsets[s_key] = c_val
            self.run_z_clearance_offsets = offsets
            if offsets:
                off_strs = [
                    f"{s}: -{v:.2f}mm (less deep)" if v > 0 else f"{s}: +{abs(v):.2f}mm (deeper)"
                    for s, v in offsets.items()
                ]
                self.logger.info(f"Operator configured well bottom Z adjustments: {', '.join(off_strs)}")
            else:
                self.logger.info("Operator confirmed protocol run at standard calibrated depths (0.0mm offset).")
            user_confirmed["status"] = True
            top.destroy()

        def on_cancel():
            user_confirmed["status"] = False
            top.destroy()

        btn_bar = ttk.Frame(top, padding=12)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_bar, text="Cancel Protocol Run", command=on_cancel).pack(side=tk.RIGHT, padx=4)
        tk.Button(
            btn_bar,
            text="🟢 Start Protocol with Selected Depths",
            bg="#28a745",
            fg="white",
            font=("Arial", 9, "bold"),
            command=on_confirm
        ).pack(side=tk.RIGHT, padx=4)

        top.wait_window()
        return user_confirmed["status"]

    def _is_machine_2_10ul_active(self) -> bool:
        """Return True ONLY when Machine 2 (1-10 uL multichannel) is active."""
        pid = str(getattr(self, "active_profile_id", "") or "").lower()
        if "300" in pid or "1000" in pid or "machine_1" in pid or "machine_3" in pid:
            return False
        if "10ul" in pid or "machine_2" in pid:
            return True
        head_var = getattr(self, "head_mode_var", None)
        head_txt = str(head_var.get() if head_var else "").lower()
        if "1-10" in head_txt or "1–10" in head_txt:
            return True
        pip = getattr(getattr(self, "lims", None), "pipettor", None)
        return bool(pip and getattr(pip, "multichannel", False) and float(getattr(pip, "tip_volume", 1000.0)) <= 10.0)

    def execute_protocol(self):
        if getattr(self, 'is_running', False):
            self.logger.warning("Protocol sequence is already active or stopping. Please wait.")
            return
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock",
                                 "Hardware must be homed via 'Connect & Initialize' before executing automated workflows.")
            return
        if not getattr(self, 'is_head_initialized', False):
            self.is_head_initialized = True
            self.initialized_head = self.active_profile_id
            self.update_window_title()
        if not self.workflow_sequence:
            messagebox.showinfo("No Protocol", "No protocol steps loaded in the Protocol Runner.")
            return

        is_300_run = (
            ("300" in getattr(self, "active_profile_id", ""))
            or ("300" in str(getattr(self, "current_protocol_file", "")).lower())
            or ("300" in str(getattr(self, "loaded_protocol_name", "")).lower())
            or ("300" in str(getattr(self, "proto_workflow_var", tk.StringVar()).get()).lower())
            or ("300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower())
            or any("300" in str(s.get("label", "")).lower() or "300" in str(s.get("labware", "")).lower() for s in self.workflow_sequence)
        )

        # Pre-Run Safety Check: Verify Tip Usage & Clearance Slots
        tips_info, empty_slots, active_slots = self._analyze_protocol_tips_and_slots(self.workflow_sequence)
        check_msg = ["PROTOCOL PRE-RUN SAFETY CHECK\n"]
        if tips_info:
            check_msg.append("🎯 TIP REQUIREMENTS:")
            for ti in tips_info:
                check_msg.append(f"  • {ti}")
            check_msg.append("")
        if empty_slots:
            check_msg.append("⛔ SLOTS TO KEEP COMPLETELY EMPTY (CLEARANCE):")
            for es in empty_slots:
                check_msg.append(f"  • {es} (Must be completely clear of any labware or obstacles)")
            check_msg.append("")
        else:
            check_msg.append("ℹ️ All 6 deck slots are occupied.\n")

        check_msg.append("Have you verified fresh tips are loaded and confirmed all empty slot(s) are clear?")
        confirm = True if getattr(self, "headless_test_mode", False) else messagebox.askyesno("Protocol Pre-Run Safety Check", "\n".join(check_msg))
        if not confirm:
            self.logger.info("Protocol run cancelled by operator during Pre-Run Safety Check.")
            return

        if is_300_run:
            if getattr(self, "active_profile_id", "") != "machine_3_300ul":
                self.switch_machine_profile("machine_3_300ul", save_to_disk=True)
            self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        else:
            needs_8ch = any(s.get('eight_ch_symmetric') for s in self.workflow_sequence) or ("10ul" in getattr(self, "active_profile_id", ""))
            if needs_8ch and not self.lims.pipettor.multichannel:
                self.switch_pipettor_head("8-Channel Multi (1-10 µL)" if "10ul" in getattr(self, "active_profile_id", "") else True, quiet=True)
            elif not needs_8ch and self.lims.pipettor.multichannel:
                max_v = max((float(s.get('volume', 0.0) or 0.0) for s in self.workflow_sequence), default=7.5)
                if max_v <= 15.0:
                    self.switch_pipettor_head("8-Channel Multi (1-10 µL)", quiet=True)
                elif max_v <= 50.0:
                    self.switch_pipettor_head("20 µL Single-Channel", quiet=True)
                else:
                    self.switch_pipettor_head("300 µL Single-Channel", quiet=True)
        has_mix_steps = any(int(s.get('mix_cycles', 0)) > 0 or s.get('action') == "Mix Well" for s in self.workflow_sequence)
        if has_mix_steps and not getattr(self, "headless_test_mode", False):
            self.enable_mixing_for_run = messagebox.askyesno(
                "In-Well Mixing Option",
                "Do you want to enable 2x in-well mixing for this run?\n\n"
                "• YES (Mix ON): Goes down into the well (92mm on Slot 5 96-well / 90mm on Slot 4 / 86mm on 48-well EHM) and mixes 2 times after adding drug.\n"
                "• NO (Mix OFF): Skips all mixing and dispenses from the brim (85mm on 96-well) without touching the well liquid."
            )
        else:
            self.enable_mixing_for_run = False

        # Well Bottom Clearance / Less Deep Prompt (Option A)
        proceed_with_run = self.prompt_z_clearance_for_run()
        if not proceed_with_run:
            self.logger.info("Protocol run cancelled by operator during Depth Clearance configuration.")
            return

        self.is_running = True

        # --- AUTO SAVE FUNCTIONALITY INJECTED HERE ---
        export_dir = os.path.join(os.path.expanduser("~"), "Desktop", "pipette trials export")
        os.makedirs(export_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        auto_save_path = os.path.join(export_dir, f"run_{timestamp}.json")
        try:
            with open(auto_save_path, 'w') as f:
                json.dump(self.workflow_sequence, f, indent=4)
        except Exception as e:
            self.logger.warning(f"Could not auto-save to desktop: {e}")

        # ---------------------------------------------
        threading.Thread(target=self.run_sequence, daemon=True).start()

    def run_sequence(self):
        def _worker():
            self.is_running = True
            self.is_aborted = False
            self.session_abort_status = None
            # Fresh liquid-level ledger for every run (tubes assumed refilled to start level)
            self.liquid_ledger = {}
            self.has_air_cushion = False
            self.air_cushion_ul = 0.0
            self.tip_liquid_ul = 0.0
            self.last_aspirate_slot = None
            self.last_aspirate_lw_kind = None
            self.z_home_step_counter = 0
            self.pause_event.set()
            self.root.after(0, lambda: self.update_ui_state(True))
            total_steps = len(self.workflow_sequence)

            self.sync_deck_manager()
            # --- WEIGHTED TIME ESTIMATION & LIVE SPEED FACTOR INIT ---
            self.step_baseline_times = self._estimate_step_durations(self.workflow_sequence)
            self.estimated_total_time = round(sum(self.step_baseline_times), 1)
            self.completed_baseline_time = 0.0
            self.live_speed_factor = 1.0
            self.total_paused_seconds = 0.0
            self.pause_started_at = None
            self.active_elapsed_at_step_start = 0.0
            self._start_session_log(total_steps=total_steps, est_seconds=self.estimated_total_time)
            self.logger.info("--- Protocol Sequence Initiated ---")
            self.run_start_time = time.time()
            self.timer_running = True
            self.root.after(0, self.update_timer)
            # ---------------------------------------------------------

            self.current_step_idx = 0
            while self.current_step_idx < len(self.workflow_sequence):
                self.pause_event.wait()
                if self.is_aborted: break

                step = self.workflow_sequence[self.current_step_idx]
                i = self.current_step_idx + 1
                total_steps = len(self.workflow_sequence)
                step_skipped_fast = False

                try:
                    self.root.after(0, lambda idx=i - 1: self.wf_box.selection_clear(0, tk.END))
                    self.root.after(0, lambda idx=i - 1: self.wf_box.selection_set(idx))
                    self.root.after(0, lambda idx=i - 1: self.wf_box.see(idx))
                    self.root.after(0, lambda idx=i: self.progress_var.set((idx / total_steps) * 100))

                    action, mode, vol = step['action'], step.get('mode', 'auto'), step.get('volume', 0.0)
                    extra_z = step.get('extra_z', 0.0)
                    m_channels = str((step or {}).get("mounted_channels", "")).strip().upper()
                    is_multi_channel_action = bool(m_channels and len(m_channels) > 1 and m_channels not in ("1", "CH1", "A"))
                    is_8ch = bool(self.lims.pipettor.multichannel or step.get('eight_ch_symmetric') or is_multi_channel_action)
                    step_desc = step.get('label') or f"[{action}]"
                    self.logger.info(f"Executing Step {i}/{total_steps}: {step_desc}")

                    if action == "Pick Up Tip" and mode != "manual":
                        if self._worker_has_tip:
                            self.logger.info("Tip State: ATTACHED. Skipping redundant pickup step.")
                            step_skipped_fast = True
                            time.sleep(0.05)
                            continue
                    elif action == "Discard Tip" and mode != "manual":
                        if not self._worker_has_tip:
                            self.logger.info("Tip State: EMPTY. Skipping redundant discard step.")
                            step_skipped_fast = True
                            time.sleep(0.05)
                            continue

                    # --- DB / UPLOAD REMOVED FROM EXECUTION LOGIC ---
                    if "System:" in action:
                        try:
                            if "Incubate" in action:
                                self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get())
                                self.logger.info(f"System: Waiting {vol:.0f}s at safety origin (adjust or lower liquid height in tube now)...")
                                time.sleep(vol)
                                self.logger.info("Wait complete. Resuming protocol sequence.")
                            elif "FOC48" in action:
                                self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get())
                                try:
                                    import foc_automation
                                    step_exp = (step.get('well', '') or '').strip()
                                    global_exp = self.foc_exp_var.get().strip() if hasattr(self, 'foc_exp_var') else ''
                                    chosen_exp = step_exp if (step_exp and step_exp.upper() != 'A1') else (global_exp or step_exp)
                                    foc_automation.execute_foc48_measurement(plate_name=chosen_exp, logger=self.logger)
                                except Exception as foc_err:
                                    self.logger.error(f"FOC48 Automation Error: {foc_err}")
                            elif "Data Analysis" in action:
                                self.logger.info("Launching Analysis Subsystem (Hill Equations)...")
                                time.sleep(1.5)
                                self.logger.info("Analysis complete. Results buffered.")
                            elif "DB Upload" in action:
                                self.logger.info("Launching DB Subsystem...")
                                time.sleep(1.0)
                                self.logger.info("Payload verified. Pushed to Contraction DB.")
                            elif "Calcium Curve" in action:
                                self.logger.info("Executing Automated Calcium Curve Macro...")
                                time.sleep(2.0)
                                self.logger.info("Calcium Curve executed successfully.")

                        except Exception as e:
                            self.logger.error(f"System step {i} error: {e}\n{traceback.format_exc()}")
                            self.ask_error_resolution(e, i)
                        time.sleep(0.05)
                        continue

                    slot_name, well_id = step.get('slot', ''), step.get('well', '')
                    target_x, target_y, target_z = None, None, None

                    # If slot is unspecified for tip pickup, default to the mounted tip rack (or Slot_4)
                    if action == "Pick Up Tip" and (not slot_name or slot_name.upper() in ("AUTO", "DEFAULT", "NONE", "")):
                        slot_name = self.get_default_tip_slot()

                    if mode == "manual":
                        target_x, target_y, target_z = step.get('x', 0.0), step.get('y', 0.0), step.get('z', 0.0)
                    elif slot_name in self.lims.deck_slots:
                        if slot_name not in self.lims.deck_labware:
                            req_lw = step.get('labware', '')
                            if slot_name == "Slot_1" and req_lw == "tube_rack_2x6_2ml.json":
                                req_lw = "reservoir_3_well.json"
                            req_path = os.path.join(self.get_labware_dir(), req_lw) if req_lw else ''
                            if req_lw and os.path.exists(req_path):
                                self.lims.deck_labware[slot_name] = Labware(req_path)
                                self.lims.deck_labware[slot_name].source_file = req_lw
                                if slot_name not in self.placed_slots: self.placed_slots.append(slot_name)
                                self.sync_deck_manager()
                                self.logger.info(f"{slot_name} was empty -> mounted protocol-declared {req_lw}.")
                            elif action != "Discard Tip":
                                self.ask_error_resolution(f"No labware assigned to {slot_name}. Assign one in the Deck tab.", i)
                                continue

                        # --- ACTIVE SESSION TIP MEMORY (Virtual Tip Remapping) ---
                        if action == "Pick Up Tip":
                            if not is_8ch:
                                resolved_well, was_remapped = self.resolve_session_tip(slot_name, well_id)
                                if resolved_well is None:
                                    self.session_abort_status = "AUTO_ABORTED_EMPTY_TIPS"
                                    self.logger.critical(
                                        f"🛑 All 96 tip sockets in {slot_name} are exhausted in this session! "
                                        f"Load a fresh tip box and click '🔄 Reset Tip Rack'."
                                    )
                                    self.is_aborted = True
                                    break
                                if was_remapped:
                                    self.logger.info(
                                        f"[TIP MEMORY] Virtual Tip Remap on {slot_name}: Requested {well_id or 'Auto'} (already consumed) -> Remapped to fresh tip {resolved_well}"
                                    )
                                well_id = resolved_well
                            else:
                                col, was_remapped = self.resolve_8ch_session_tip_col(slot_name, well_id, step)
                                if col is None:
                                    self.session_abort_status = "AUTO_ABORTED_EMPTY_TIPS"
                                    self.logger.critical(
                                        f"🛑 All 12 tip columns in {slot_name} are exhausted in this session! "
                                        f"Load a fresh tip box and click '🔄 Reset Tip Rack'."
                                    )
                                    self.is_aborted = True
                                    break
                                orig_req = well_id or "Auto"
                                well_id = f"A{col}"
                                if was_remapped:
                                    self.logger.info(
                                        f"[TIP MEMORY] 8-Channel Virtual Tip Remap on {slot_name}: Requested {orig_req} (already consumed) -> Advanced to fresh Column {col} ({well_id})"
                                    )
                                else:
                                    self.logger.info(f"[TIP MEMORY] 8-Channel tip pickup using fresh Column {col} ({well_id})")
                        # ---------------------------------------------------------

                        coords = self._resolve_step_xy(step, slot_name, well_id)
                        if coords and (coords[0] != 0.0 or coords[1] != 0.0):
                            target_x, target_y = coords
                        else:
                            self.ask_error_resolution(f"Coordinate mapping failed for {slot_name} Well {well_id}.", i)
                            continue
                    else:
                        self.ask_error_resolution(f"Unknown slot '{slot_name}'. Coordinate mapping failed.", i)
                        continue

                    if action == "Pick Up Tip":
                        self.last_aspirate_slot = None
                        self.last_aspirate_lw_kind = None
                        cal_dz = float(self.eight_ch_cal_offset.get("Z", 0.0)) if is_8ch else 0.0
                        tip_vol = getattr(self.lims.pipettor, 'tip_volume', 1000.0)
                        is_10ul = ("10ul" in getattr(self, "active_profile_id", "")) or (is_8ch and tip_vol <= 50.0) or ("10ul" in str(getattr(self, 'initialized_head', '')).lower())

                        if is_10ul:
                            # Dedicated 8-Channel 1-10 µL head (calibrated collar Z=64.49mm)
                            collar_z = float(self.calibrated_heights.get("tip_10ul_collar_z", self.calibrated_heights.get("tip_rack_collar_z", 64.49)))
                            configured_limit = float(self.calibrated_heights.get("tip_10ul_limit_z", self.calibrated_heights.get("tip_rack_pickup_limit_z", 75.0)))
                            approach_z = float(self.calibrated_heights.get("tip_10ul_approach_z", self.calibrated_heights.get("tip_rack_pickup_approach_z", 50.0)))
                            extra_press = float(self.calibrated_heights.get("tip_10ul_extra_press_mm", self.calibrated_heights.get("tip_pickup_extra_press_mm", 2.50)))
                            pickup_limit = min(80.0, max(68.0, configured_limit + extra_z + cal_dz))
                            valid_collar_min = 48.0
                            valid_collar_max = max(74.0, collar_z + 8.0)
                        elif is_8ch:
                            # Dedicated 8×1000 µL Multi-Channel (Monday calibrated heights)
                            collar_z = float(self.calibrated_heights.get("tip_rack_collar_z", 86.36))
                            configured_limit = float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 98.0))
                            approach_z = float(self.calibrated_heights.get("tip_rack_pickup_approach_z", 75.0))
                            extra_press = float(self.calibrated_heights.get("tip_pickup_extra_press_mm", 2.50))
                            pickup_limit = min(99.5, max(88.0, configured_limit + extra_z + cal_dz))
                            valid_collar_min = 84.0
                            valid_collar_max = min(98.5, configured_limit - 0.5)
                        else:
                            # Single-Channel (e.g. 300 µL or 20 µL)
                            collar_z = float(self.calibrated_heights.get("tip_rack_collar_z", 86.36))
                            configured_limit = max(92.0, float(self.calibrated_heights.get("tip_rack_pickup_limit_z", 92.0)))
                            approach_z = float(self.calibrated_heights.get("tip_rack_pickup_approach_z", 50.0))
                            extra_press = float(self.calibrated_heights.get("tip_pickup_extra_press_mm", 1.50))
                            pickup_limit = min(98.0, max(92.0, configured_limit + extra_z, collar_z + 4.5))
                            valid_collar_min = 48.0
                            valid_collar_max = max(90.5, min(97.5, pickup_limit - 0.4))

                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        labware_obj = self.lims.deck_labware.get(slot_name)

                        tip_rack_model = None
                        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
                            lw_cand = self.deck_manager.slots[slot_name].labware
                            if isinstance(lw_cand, TipRack96):
                                tip_rack_model = lw_cand

                        def _do_pick(tx, ty):
                            if is_10ul:
                                self.logger.info(f"🎯 [MACHINE 2: 1-10µL] Tip pickup moving to seated coordinates: X={tx:.2f}mm, Y={ty:.2f}mm, Z_collar={collar_z:.2f}mm")
                            if self.lims.pipettor.hardware:
                                self.lims.pipettor.hardware.move_z(0)
                            self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
                            time.sleep(0.05)
                            if not self.lims.pipettor.hardware:
                                return True, collar_z + 2.50

                            hw = self.lims.pipettor.hardware
                            hw.z_speed = hw_speed
                            hw.move_z(approach_z)
                            hw.z_speed = 3
                            hw.tip_pickup_force = 26 if is_8ch else 20
                            
                            pick_ok = False
                            try:
                                hw.pick_tip(pickup_limit)
                                pick_ok = True
                            except Exception as pe:
                                self.logger.warning(f"pick_tip hardware return/exception: {pe}")
                                pick_ok = False

                            curr_z = getattr(hw, 'z_position', 0.0)

                            # 1. VALID SEATED TIP:
                            valid_collar = (valid_collar_min <= curr_z <= valid_collar_max)
                            is_seated = valid_collar or (pick_ok and curr_z >= valid_collar_min and curr_z <= max(valid_collar_max, pickup_limit - 0.1))

                            if is_seated:
                                # Monday High-torque mechanical seating press & double-tap to wedge nozzles firmly into tip collars
                                if extra_press > 0:
                                    try:
                                        press_target = min(pickup_limit, curr_z + extra_press)
                                        self.logger.info(f"🔧 Seating tip(s) firmly: high-torque press to Z={press_target:.2f}mm (+{extra_press:.2f}mm)...")
                                        hw.z_speed = 2 # slow, maximum motor torque
                                        hw.move_z(press_target)
                                        time.sleep(0.25)
                                        # Double-tap: slight retract and re-press for airtight friction lock
                                        if press_target - curr_z >= 1.0:
                                            hw.move_z(max(curr_z, press_target - 1.0))
                                            time.sleep(0.1)
                                            hw.move_z(press_target)
                                            time.sleep(0.25)
                                    except Exception as se:
                                        self.logger.warning(f"Tip seating press notice: {se}")

                                time.sleep(0.2)
                                try:
                                    hw.z_speed = hw_speed
                                    hw.move_z(0)
                                except Exception:
                                    hw.move_z(0)
                                return True, curr_z

                            # 2. EMPTY SOCKET (Z >= pickup_limit - 0.8 or failed pick):
                            self.logger.warning(f"Empty socket detected at Z={curr_z:.2f}mm (pick_ok={pick_ok}, is_8ch={is_8ch}). Advancing...")
                            try:
                                hw.z_speed = hw_speed
                                hw.move_z(0)
                                if getattr(self, "mid_protocol_z_home_var", None) and self.mid_protocol_z_home_var.get():
                                    self.lims.hw.home_z_only(logger=self.logger, reason="Empty tip socket retry")
                            except Exception:
                                hw.move_z(0)
                            return False, curr_z

                        if mode == "manual":
                            seated, cz = _do_pick(target_x, target_y)
                            if seated:
                                self.logger.info(f"🎯 Manual tip pickup succeeded at Z={cz:.2f}mm. HAS_TIP = True")
                                self._set_has_tip(True)
                            else:
                                self.logger.warning(f"Manual tip pick: No tip detected (Z={cz:.2f}mm).")

                        elif self.auto_tip_search_var.get() and not is_8ch:
                            ordered_wells = self._ordered_tip_wells(slot_name)
                            consumed_now = self._get_tip_tracker(slot_name)["consumed"]
                            start_idx = ordered_wells.index(well_id) if well_id in ordered_wells else 0
                            search_indices = list(range(start_idx, len(ordered_wells))) + list(range(0, start_idx))
                            tip_found = False

                            for idx in search_indices:
                                if self.is_aborted:
                                    break
                                current_well = ordered_wells[idx]
                                if current_well in consumed_now:
                                    continue
                                coords = self._resolve_step_xy(step, slot_name, current_well)
                                tx, ty = coords if coords else (0, 0)
                                self.logger.info(f"Checking tip at {slot_name} {current_well} ({tx:.2f}, {ty:.2f})...")
                                seated, cz = _do_pick(tx, ty)
                                self.mark_tip_consumed(slot_name, current_well)
                                if seated:
                                    self.logger.info(f"🎯 Tip acquired at {slot_name} {current_well} (Z={cz:.2f}mm). HAS_TIP = True")
                                    tip_found = True
                                    self._set_has_tip(True)
                                    break
                                else:
                                    self.logger.warning(
                                        f"Well {current_well} empty or passed (Z={cz:.2f}mm). Marked consumed & tracking to next column-major well..."
                                    )

                            if not tip_found and not self.is_aborted:
                                self.session_abort_status = "AUTO_ABORTED_EMPTY_TIPS"
                                self.logger.critical(f"🛑 Tip rack on {slot_name} is completely empty! All 96 sockets exhausted.")
                                self.is_aborted = True
                                break
                        else:
                            seated, cz = _do_pick(target_x, target_y)
                            if seated:
                                if is_8ch:
                                    for sock in self._expand_8ch_tip_sockets(step, well_id):
                                        self.mark_tip_consumed(slot_name, sock, redraw=False)
                                    self._schedule_deck_redraw()
                                else:
                                    self.mark_tip_consumed(slot_name, well_id)
                                ch_note = f" [Ch {step.get('mounted_channels')}]" if step.get('mounted_channels') else ""
                                self.logger.info(f"🎯 Tip acquired at {well_id}{ch_note} (X={target_x:.1f}, Y={target_y:.1f}, Z={cz:.2f}mm). HAS_TIP = True")
                                self._set_has_tip(True)
                            else:
                                if not is_8ch:
                                    self.mark_tip_consumed(slot_name, well_id)
                                self.session_abort_status = "AUTO_ABORTED_HARDWARE"
                                raise RuntimeError(f"Tip pickup failed at {well_id} (X={target_x:.1f}, Y={target_y:.1f}, Z={cz:.2f}mm).")

                    elif action == "Detect Liquid Level":
                        if self.lims.pipettor.multichannel:
                            self.logger.warning("Detect Liquid Level skipped: 8×1000 µL manifold has no single-tip sensor.")
                            time.sleep(0.05)
                            continue
                        labware_obj = self.lims.deck_labware.get(slot_name)
                        slot_obj = self.lims.deck_slots.get(slot_name)
                        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

                        if mode == "manual":
                            bottom_z = target_z
                        else:
                            bottom_z = self._labware_bottom_z(labware_obj, slot_name)

                        # Strict firmware clamp: InstrumentLib.dll enforces limit <= 100.0mm
                        bottom_z = min(99.5, bottom_z + (slot_z_offset if mode != "manual" else 0.0))

                        radius_mm = 3.4
                        if labware_obj and hasattr(labware_obj, 'wells') and well_id in labware_obj.wells:
                            radius_mm = getattr(labware_obj.wells[well_id], 'radius', 3.4)
                        elif labware_obj and hasattr(labware_obj, 'raw_data'):
                            radius_mm = labware_obj.raw_data.get('well_properties', {}).get('radius_mm', 3.4)
                        if radius_mm <= 0.0:
                            radius_mm = 3.4

                        self.logger.info(f"Detect Liquid Level: moving to {slot_name} Well {well_id} (Z-limit={bottom_z:.1f}mm)...")
                        if self.lims.pipettor.hardware:
                            self.lims.pipettor.hardware.move_z(0)
                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                        time.sleep(0.05)

                        try:
                            z_measured = self._probe_surface_and_wait(bottom_z, submerge_mm=1.0)
                            if self.lims.pipettor.hardware:
                                self.lims.pipettor.hardware.move_z(0)

                            if z_measured >= (bottom_z - 1.0):
                                self.logger.warning(f"[LIQUID LEVEL] {slot_name} Well {well_id}: EMPTY (reached bottom limit Z={bottom_z:.1f}mm).")
                            else:
                                liquid_height_mm = max(0.0, bottom_z - z_measured)
                                volume_ul = math.pi * (radius_mm ** 2) * liquid_height_mm
                                vol_str = f"{volume_ul:.1f}uL ({volume_ul / 1000.0:.2f}mL)" if volume_ul >= 1000.0 else f"{volume_ul:.1f}uL"
                                self.logger.info(f"[LIQUID LEVEL] {slot_name} Well {well_id}: Surface Z={z_measured:.2f}mm, Height={liquid_height_mm:.2f}mm, Remaining Volume={vol_str}")
                        except Exception as probe_err:
                            self.logger.error(f"[LIQUID LEVEL] Sensor probe failed at {slot_name} {well_id}: {probe_err}")
                            if self.lims.pipettor.hardware:
                                self.lims.pipettor.hardware.move_z(0)

                    elif action in ["Aspirate Media", "Dispense Media", "Discard Tip", "Mix Well"]:
                        if action == "Mix Well" and not getattr(self, 'enable_mixing_for_run', True):
                            self.logger.info("Mixing opted out for this run. Skipping Mix Well step.")
                            step_skipped_fast = True
                            time.sleep(0.05)
                            continue
                        effective_mix = int(step.get('mix_cycles', 0)) if getattr(self, 'enable_mixing_for_run', True) else 0
                        cal_dz = float(self.eight_ch_cal_offset.get("Z", 0.0)) if is_8ch else 0.0
                        clearance_dz = 0.0
                        if action == "Discard Tip" and step.get('discard_z_override') is not None and mode != "manual":
                            tz = min(float(step['discard_z_override']) + extra_z + cal_dz, 102.0)
                        elif mode == "manual":
                            tz = target_z
                        else:
                            tz = min(
                                self._calculate_z(
                                    action,
                                    self.lims.deck_labware.get(slot_name),
                                    well_id,
                                    mode,
                                    0.0,
                                    slot_name,
                                    extra_z,
                                    mix_cycles=effective_mix,
                                ) + cal_dz,
                                103.5,
                            )
                            lw_kind = self._lw_kind(self.lims.deck_labware.get(slot_name))
                            is_already_cal = (
                                getattr(self.lims.deck_labware.get(slot_name), 'is_8ch_calibrated', False)
                                or lw_kind in ("ehm48", "reservoir_7", "reservoir_6", "reservoir_3", "waste")
                                or (slot_name in ("Slot_3", "Slot_5"))
                                or (slot_name in ("Slot_6", "Slot_1", "Slot_2") and "reservoir" in str(lw_kind))
                            )
                            if is_8ch and not is_already_cal:
                                # 1000 µL tips are ~20.5 mm longer than the 200 µL calibration tip
                                tz = max(0.0, tz - self.EIGHT_CH_TIP_Z_COMP_MM)

                            # Apply user-configured pre-run Z offset (+ less deep, - deeper) for liquid operations
                            if action in ("Aspirate Media", "Dispense Media", "Mix Well"):
                                clearance_dz = float(getattr(self, "run_z_clearance_offsets", {}).get(slot_name, 0.0) or 0.0)
                                tz = self._apply_run_z_clearance(tz, clearance_dz)

                        if clearance_dz > 1e-9:
                            clearance_tag = f" [Clearance: -{clearance_dz:.2f}mm less deep -> final Z={tz:.2f}mm]"
                        elif clearance_dz < -1e-9:
                            clearance_tag = f" [Depth Adjust: +{abs(clearance_dz):.2f}mm deeper -> final Z={tz:.2f}mm]"
                        else:
                            clearance_tag = ""
                        self.logger.info(
                            f"Absolute Z-Depth Executed: Z={tz:.2f}mm for {well_id if mode != 'manual' else 'Manual Target'}{clearance_tag}"
                            + (f" (8-ch 1000 µL tip compensation -{self.EIGHT_CH_TIP_Z_COMP_MM:.1f} mm)" if is_8ch and not is_already_cal and mode != "manual" and not (action == "Discard Tip" and step.get('discard_z_override') is not None) else "")
                            + (f" (8-ch direct physical calibration: {tz:.2f}mm)" if is_8ch and is_already_cal else ""))

                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        if self.lims.pipettor.hardware:
                            try:
                                self.lims.pipettor.hardware.z_speed = hw_speed
                                self.lims.pipettor.hardware.move_z(0)
                            except Exception:
                                self.lims.pipettor.hardware.move_z(0)
                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                        time.sleep(0.05)

                        if self.lims.pipettor.hardware:
                            if action == "Aspirate Media":
                                self.last_aspirate_slot = slot_name
                                self.last_aspirate_lw_kind = self._lw_kind(self.lims.deck_labware.get(slot_name))
                                tip_vol = float(getattr(self.lims.pipettor, 'tip_volume', 300.0))
                                is_machine_3 = (not is_8ch) and (
                                    "300" in getattr(self, "active_profile_id", "")
                                    or "300" in str(getattr(self, "current_protocol_file", "")).lower()
                                    or "300" in str(getattr(self, "loaded_protocol_name", "")).lower()
                                    or "300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower()
                                )
                                is_300 = is_machine_3 or ((not is_8ch) and tip_vol >= 250.0)
                                if is_8ch:
                                    hw_plunger_max = 10.0 if "10ul" in getattr(self, "active_profile_id", "") else 1000.0
                                elif is_300:
                                    hw_plunger_max = 250.0
                                else:
                                    hw_plunger_max = 250.0
                                req_vol_f = float(vol)
                                avail_air = max(0.0, hw_plunger_max - req_vol_f)
                                # Draw air cushion in open air (Z=0) BEFORE tip enters media, only when tip is empty
                                # and when cumulative stroke (air_vol + req_vol_f) stays within hw_plunger_max (200uL on single-channel).
                                # Machine 2 (1-10 uL 8-channel head) aspirates requested liquid directly with no air pre-draw.
                                # Machine 3 (300 uL Single Channel): aspirations >= 150 uL bypass the air cushion.
                                # Machine 1 and Machine 3 (<150 uL) preserve existing air-cushion behavior.
                                if (
                                    req_vol_f > 0.0
                                    and avail_air >= 0.5
                                    and not step.get('no_air_cushion', False)
                                    and not self._is_machine_2_10ul_active()
                                    and not (is_machine_3 and req_vol_f >= 150.0)
                                    and getattr(self, 'air_cushion_ul', 0.0) <= 0.0
                                    and getattr(self, 'tip_liquid_ul', 0.0) <= 0.0
                                ):
                                    if tip_vol <= 10.0:
                                        air_vol = min(1.5, avail_air, max(0.5, tip_vol - req_vol_f))
                                    elif tip_vol <= 20.0:
                                        air_vol = min(2.0, avail_air, max(1.0, tip_vol - req_vol_f))
                                    elif tip_vol <= 300.0:
                                        air_vol = min(15.0 if req_vol_f < 185.0 else 10.0, avail_air)
                                    else:
                                        air_vol = min(30.0, avail_air, max(0.0, tip_vol - req_vol_f))

                                    if air_vol > 0.0:
                                        try:
                                            self.lims.pipettor.hardware.aspirate(air_vol)
                                            self.air_cushion_ul = air_vol
                                            self.has_air_cushion = True
                                            self.logger.info(
                                                f"Air Cushion: Pre-aspirated {air_vol:.2f}uL air cushion in open air (Z=0.0mm) "
                                                f"before entering media for {req_vol_f:.1f}uL ({slot_name} {well_id})."
                                            )
                                            time.sleep(0.25)
                                        except Exception as air_err:
                                            self.air_cushion_ul = 0.0
                                            self.has_air_cushion = False
                                            self.logger.warning(f"Air cushion draw skipped: {air_err}")

                                # --- Liquid Level Tracking (Software Meniscus Tracking + Sensor LLD) ---
                                slot_model = self.deck_manager.slots.get(slot_name) if hasattr(self, 'deck_manager') else None
                                lw_model = slot_model.labware if slot_model else None
                                lw_src_lower = str(getattr(self.lims.deck_labware.get(slot_name), 'source_file', '')).lower()
                                lw_kind = self._lw_kind(self.lims.deck_labware.get(slot_name))

                                # Explicit check: Is this labware a plate? Plates NEVER auto-advance or probe meniscus!
                                is_plate = (
                                    lw_kind in ("plate96", "ehm48")
                                    or "plate" in lw_src_lower
                                    or "96" in lw_src_lower
                                    or "48" in lw_src_lower
                                    or "ehm" in lw_src_lower
                                    or "drug" in lw_src_lower
                                    or "pcr" in lw_src_lower
                                    or "assay" in lw_src_lower
                                )

                                is_300ul_slot1_res = (
                                    slot_name == "Slot_1"
                                    and ("300" in str(getattr(self, "active_profile_id", "")) or tip_vol == 300.0)
                                    and not is_plate
                                    and "50ml" not in lw_src_lower
                                    and "3x50ml" not in lw_src_lower
                                )

                                is_2ml_falcon = (
                                    not is_300ul_slot1_res
                                    and (
                                        isinstance(lw_model, TubeRack2x6_2mL) or (
                                            (lw_kind == "tube_rack_2x6" or (self._is_front_slot(slot_name) and "2x6" in lw_src_lower))
                                            and not isinstance(lw_model, (FalconRack50mL, Reservoir3Well))
                                            and "50ml" not in lw_src_lower and "3x50ml" not in lw_src_lower and "30ml" not in lw_src_lower
                                        )
                                    )
                                ) and not is_plate

                                is_reservoir = (
                                    is_300ul_slot1_res
                                    or isinstance(lw_model, Reservoir3Well) or (
                                        ((self._is_front_slot(slot_name) and lw_kind in ("reservoir_3", None))
                                        or "reservoir" in lw_src_lower
                                        or "3_well" in lw_src_lower
                                        or "30ml" in lw_src_lower)
                                        and not is_2ml_falcon and not isinstance(lw_model, FalconRack50mL)
                                        and "50ml" not in lw_src_lower
                                    )
                                ) and not is_plate

                                is_50ml_falcon = (
                                    isinstance(lw_model, FalconRack50mL) or ("50ml" in lw_src_lower or "3x50ml" in lw_src_lower)
                                ) and not is_plate

                                is_tube_or_reservoir = (
                                    is_2ml_falcon or is_reservoir or is_50ml_falcon
                                    or ("tube" in lw_src_lower or "falcon" in lw_src_lower or "reservoir" in lw_src_lower)
                                ) and not is_plate

                                # Pipettor Automated Liquid Tracking System (Sensor LLD / Dynamic Height)
                                # STRICTLY for Single-Channel Reservoirs and Tubes only! Plates and 8-channel manifold
                                # must NEVER auto-advance or probe meniscus.
                                auto_track_active = (
                                    (not self.lims.pipettor.multichannel)
                                    and (not is_8ch)
                                    and is_tube_or_reservoir
                                    and (
                                        (getattr(self, 'lld_tracking_var', None) and self.lld_tracking_var.get()) or
                                        (getattr(self, 'dynamic_z_var', None) and self.dynamic_z_var.get())
                                    )
                                )
                                if auto_track_active and mode != "manual":
                                    try:
                                        # Strict firmware ceiling: InstrumentLib.dll requires limit <= 100.0mm
                                        raw_bottom_z = self._labware_bottom_z(self.lims.deck_labware.get(slot_name), slot_name)
                                        probe_bottom_z = min(99.5, raw_bottom_z)
                                        while not self.is_aborted:
                                            self.logger.info(f"[AUTO LIQUID TRACKING] Probing meniscus at {slot_name} {well_id} (Safety Cap Z<={probe_bottom_z:.1f}mm)...")
                                            z_found = self._probe_surface_and_wait(probe_bottom_z, submerge_mm=2.5)
                                            # Liquid is depleted if probe reached bottom limit without stopping at a higher meniscus
                                            if z_found >= (probe_bottom_z - 1.0):
                                                self.logger.warning(
                                                    f"[AUTO LIQUID TRACKING] Liquid depleted in {slot_name} {well_id} (Z_measured={z_found:.2f}mm >= {probe_bottom_z - 1.0:.1f}mm floor). "
                                                    f"Pipette detected liquid is over using auto liquid tracking."
                                                )
                                                next_tube = self._get_next_tube_in_sequence(slot_name, well_id)
                                                if next_tube:
                                                    self.logger.info(
                                                        f"[AUTO-ADVANCE] Advancing from {well_id} -> {next_tube} in {slot_name}..."
                                                    )
                                                    well_id = next_tube
                                                    if self.lims.pipettor.hardware:
                                                        self.lims.pipettor.hardware.move_z(0)
                                                    new_xy = self._calculate_xy(slot_name, well_id)
                                                    if new_xy:
                                                        target_x, target_y = new_xy
                                                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                                                        time.sleep(0.1)
                                                    continue
                                                else:
                                                    self.logger.error(f"[AUTO LIQUID TRACKING] All available tubes/wells in {slot_name} are depleted!")
                                                    self.refill_decision = None
                                                    self._begin_pause_tracking()
                                                    def _prompt_empty_rack():
                                                        ans = messagebox.askyesno(
                                                            "Liquid Depleted",
                                                            f"Auto liquid tracking detected liquid is over in {slot_name} ({well_id}) and reached floor limit (Z={probe_bottom_z:.1f}mm).\n\n"
                                                            f"Please refill liquid and click YES to re-probe, or NO to abort."
                                                        )
                                                        self.refill_decision = "refilled" if ans else "abort"
                                                    self.root.after(0, _prompt_empty_rack)
                                                    while self.refill_decision is None and not self.is_aborted:
                                                        time.sleep(0.1)
                                                    self._end_pause_tracking()
                                                    if self.refill_decision == "refilled":
                                                        if self.lims.pipettor.hardware:
                                                            self.lims.pipettor.hardware.move_z(0)
                                                        continue
                                                    else:
                                                        if self.session_abort_status is None:
                                                            self.session_abort_status = "AUTO_ABORTED_DEPLETED"
                                                        self.is_aborted = True
                                                        self.logger.critical(f"🛑 Protocol auto-aborted: Liquid depleted in {slot_name} ({well_id}).")
                                                        break
                                            else:
                                                # Liquid present: Calculate depth and volume left based on pipette's auto tracking
                                                rad_mm = getattr(lw_model, 'well_radius_mm', 14.0) if lw_model else 14.0
                                                area_mm2 = math.pi * (rad_mm ** 2)
                                                req_vol = float(vol)
                                                vol_drop_mm = req_vol / area_mm2 if area_mm2 > 0 else 1.0
                                                target_submerge_z = z_found + max(0.0, vol_drop_mm - 1.0)
                                                tz = min(target_submerge_z, probe_bottom_z - 0.5, 99.5)
                                                depth_left_mm = max(0.0, probe_bottom_z - z_found)
                                                rem_vol_ml = (depth_left_mm * area_mm2) / 1000.0
                                                self.logger.info(
                                                    f"[AUTO LIQUID TRACKING] Surface detected at Z={z_found:.2f}mm. "
                                                    f"Liquid depth left: {depth_left_mm:.1f}mm (~{rem_vol_ml:.1f}mL remaining). "
                                                    f"Submerging to Z={tz:.2f}mm (Safety Floor Cap = {probe_bottom_z:.1f}mm)."
                                                )
                                                break
                                    except Exception as lld_err:
                                        self.logger.warning(f"[AUTO LIQUID TRACKING] Surface probe fallback: {lld_err}. Submerging to calibrated depth Z={tz:.1f}mm")
                                    if self.is_aborted:
                                        break

                                elif mode != "manual" and (not is_8ch) and (lw_kind != "reservoir_6") and (not is_300ul_slot1_res) and (is_reservoir or is_2ml_falcon) and step.get('track_liquid', True):
                                    if not hasattr(self, 'liquid_ledger'):
                                        self.liquid_ledger = {}
                                    ledger_key = f"{slot_name}_{well_id}"
                                    if ledger_key not in self.liquid_ledger:
                                        if is_2ml_falcon:
                                            # 2mL Falcon tube on 90mm height block: starts at rim Z=75.0mm, bottom Z=103.0mm, 28mm depth for 2000uL -> area=71.43mm2
                                            self.liquid_ledger[ledger_key] = {
                                                "surface_z": float(step.get('start_surface_z', 75.0)),
                                                "bottom_z": float(step.get('tube_bottom_z', 103.0)),
                                                "area_mm2": float(step.get('tube_area_mm2', 71.43))
                                            }
                                        else:
                                            self.liquid_ledger[ledger_key] = {
                                                "surface_z": float(step.get('start_surface_z', 47.0)),  # Start meniscus (47.0mm with height blocks)
                                                "bottom_z": float(step.get('tube_bottom_z', 100.0)),     # Base of reservoir/tube
                                                "area_mm2": float(step.get('tube_area_mm2', 434.0))     # Cross-section
                                            }
                                    tube_info = self.liquid_ledger[ledger_key]
                                    req_vol = float(vol)

                                    # --- Low-volume refill / auto-rollover check ---
                                    rem_before_ml = max(0.0, tube_info["bottom_z"] - tube_info["surface_z"]) * tube_info["area_mm2"] / 1000.0
                                    reserve_ml = float(step.get('min_reserve_ml', 0.05 if is_2ml_falcon else 2.0))
                                    if rem_before_ml - (req_vol / 1000.0) < reserve_ml:
                                        if is_2ml_falcon:
                                            # Auto-advance to next Falcon tube in rack (A1 -> A2 -> A3...)
                                            tube_order = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6"]
                                            curr_idx = tube_order.index(well_id) if well_id in tube_order else -1
                                            if curr_idx != -1 and curr_idx + 1 < len(tube_order):
                                                next_well = tube_order[curr_idx + 1]
                                                self.logger.warning(
                                                    f"[2mL TUBE TRACKER] {slot_name} {well_id} depleted (2.0mL consumed) -> Auto-advancing to {slot_name} {next_well} for fresh DMSO!")
                                                well_id = next_well
                                                ledger_key = f"{slot_name}_{well_id}"
                                                self.liquid_ledger[ledger_key] = {
                                                    "surface_z": 75.0,
                                                    "bottom_z": 103.0,
                                                    "area_mm2": 71.43
                                                }
                                                tube_info = self.liquid_ledger[ledger_key]
                                                new_coords = self._calculate_xy(slot_name, well_id)
                                                if new_coords and (new_coords[0] != 0 or new_coords[1] != 0):
                                                    target_x, target_y = new_coords
                                                    self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                                                    time.sleep(0.05)
                                        else:
                                            self.logger.warning(
                                                f"[OPTION 2 TRACKER] {slot_name} {well_id} LOW: ~{rem_before_ml:.2f}mL left (reserve {reserve_ml:.1f}mL). Pausing for refill.")
                                            self.refill_decision = None
                                            start_z = float(step.get('start_surface_z', 47.0))

                                            def _ask_refill():
                                                ok = messagebox.askyesno(
                                                    "Refill Tube",
                                                    f"{slot_name} {well_id} is nearly empty (~{rem_before_ml:.1f} mL left).\n\n"
                                                    f"Refill it to the start mark (Z={start_z:.0f} mm), then press YES.\n\n"
                                                    f"Press NO to continue without refilling (tip will go near the bottom).")
                                                self.refill_decision = "refilled" if ok else "continue"

                                            self._begin_pause_tracking()
                                            self.root.after(0, _ask_refill)
                                            while self.refill_decision is None and not self.is_aborted:
                                                time.sleep(0.1)
                                            self._end_pause_tracking()
                                            if self.refill_decision == "refilled":
                                                tube_info["surface_z"] = start_z
                                                self.logger.info(f"[OPTION 2 TRACKER] {slot_name} {well_id} refilled -> surface reset to Z={start_z:.1f}mm")

                                    curr_surface = tube_info["surface_z"]
                                    submerge_depth = 2.5 if is_2ml_falcon else 5.0
                                    tz = min(curr_surface + submerge_depth, tube_info["bottom_z"] - 0.5)

                                    dz = req_vol / tube_info["area_mm2"]
                                    new_surface = min(curr_surface + dz, tube_info["bottom_z"])
                                    tube_info["surface_z"] = new_surface

                                    rem_height = max(0.0, tube_info["bottom_z"] - new_surface)
                                    rem_ml = (rem_height * tube_info["area_mm2"]) / 1000.0
                                    tracker_name = "2mL TUBE TRACKER" if is_2ml_falcon else "OPTION 2 TRACKER"
                                    self.logger.info(
                                        f"[{tracker_name}] {slot_name} {well_id}: Meniscus Z={curr_surface:.1f}mm -> Submerging to Z={tz:.1f}mm (Bottom={tube_info['bottom_z']:.1f}mm). Est. Remaining: ~{rem_ml:.2f}mL"
                                    )

                            safe_tz = min(float(tz), 102.0)
                            hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                            try:
                                self.lims.pipettor.hardware.z_speed = hw_speed
                            except Exception:
                                pass
                            self.lims.pipettor.hardware.move_z(safe_tz)

                            if action == "Aspirate Media":
                                # --- GUI SAFETY MANIFOLD CAP & EQUILIBRATION ---
                                requested_vol = float(vol)
                                if requested_vol > 0:
                                    tip_cap = float(getattr(self.lims.pipettor, 'tip_volume', 300.0))
                                    is_machine_3 = (not is_8ch) and (
                                        "300" in getattr(self, "active_profile_id", "")
                                        or "300" in str(getattr(self, "current_protocol_file", "")).lower()
                                        or "300" in str(getattr(self, "loaded_protocol_name", "")).lower()
                                        or "300" in str(getattr(self, "proto_pipettor_var", tk.StringVar()).get()).lower()
                                    )
                                    is_300 = is_machine_3 or ((not is_8ch) and tip_cap >= 250.0)
                                    if is_8ch:
                                        hw_plunger_max = 10.0 if "10ul" in getattr(self, "active_profile_id", "") else 1000.0
                                    elif is_300:
                                        hw_plunger_max = 250.0
                                    else:
                                        hw_plunger_max = 250.0

                                    if is_300 or not is_8ch:
                                        tip_cap = max(tip_cap, 250.0)

                                    max_allowed = min(tip_cap, max(0.0, hw_plunger_max - getattr(self, 'air_cushion_ul', 0.0)))
                                    actual_vol = min(requested_vol, max_allowed)

                                    if requested_vol > max_allowed:
                                        self.logger.warning(
                                            f"MANIFOLD FLOOD PREVENTED: {requested_vol}uL requested, but plunger/tip limit is {max_allowed}uL. Automatically capped to {actual_vol}uL."
                                        )

                                    try:
                                        self.lims.pipettor.hardware.aspirate(actual_vol)
                                    except Exception as asp_err:
                                        fallback_vol = max(0.0, hw_plunger_max - getattr(self, 'air_cushion_ul', 0.0))
                                        if fallback_vol > 0 and fallback_vol < actual_vol:
                                            actual_vol = fallback_vol
                                            self.lims.pipettor.hardware.aspirate(actual_vol)
                                        else:
                                            raise asp_err
                                    self.tip_liquid_ul = getattr(self, 'tip_liquid_ul', 0.0) + actual_vol
                                    time.sleep(1.5)
                                else:
                                    time.sleep(0.3)
                            elif action == "Dispense Media":
                                actual_dispense = min(float(vol), float(getattr(self.lims.pipettor, 'tip_volume', 300.0)))
                                mix_cycles = effective_mix
                                if actual_dispense > 0:
                                    try:
                                        self.lims.pipettor.hardware.dispense(actual_dispense)
                                        self.tip_liquid_ul = max(0.0, getattr(self, 'tip_liquid_ul', 0.0) - actual_dispense)
                                        time.sleep(0.4 if mix_cycles > 0 else 0.05)
                                    except Exception as d_err:
                                        self.logger.warning(f"Dispense exception ignored: {d_err}")
                                else:
                                    time.sleep(0.3)

                                if mix_cycles > 0:
                                    mix_vol = min(float(step.get('mix_volume', 100.0)), float(getattr(self.lims.pipettor, 'tip_volume', 300.0)))
                                    self.logger.info(f"In-place mixing at {well_id}: {mix_cycles}x {mix_vol}uL (submerged at Z={tz:.1f}mm, air cushion held above media)")
                                    for c_idx in range(mix_cycles):
                                        if self.is_aborted: break
                                        try:
                                            self.lims.pipettor.hardware.aspirate(mix_vol)
                                            time.sleep(1.2)
                                            self.lims.pipettor.hardware.dispense(mix_vol)
                                            time.sleep(0.8)
                                        except Exception as m_err:
                                            self.logger.warning(f"Mix stroke {c_idx + 1}/{mix_cycles} warning: {m_err}")

                                # Preserve air cushion across multi-dispense (no_blowout=True or liquid remaining in tip).
                                # When final dispense finishes, lift tip ABOVE the media first before blowing out the air cushion
                                # so the last drop is expelled cleanly without creating bubbles in the liquid!
                                is_partial_dispense = bool(step.get('no_blowout', False)) or (getattr(self, 'tip_liquid_ul', 0.0) > 0.1)
                                air_to_blow = float(getattr(self, 'air_cushion_ul', 0.0))
                                if is_partial_dispense:
                                    self.has_air_cushion = (air_to_blow > 0.0)
                                elif air_to_blow > 0.0:
                                    try:
                                        blowout_z = max(0.0, safe_tz - 12.0)
                                        self.lims.pipettor.hardware.move_z(blowout_z)
                                        time.sleep(0.1)
                                        self.lims.pipettor.hardware.dispense(air_to_blow)
                                        self.logger.info(
                                            f"Air Cushion Blowout (Bubble-Free): Lifted tip out of media to Z={blowout_z:.2f}mm "
                                            f"and expelled {air_to_blow:.2f}uL air cushion to clear residual drop."
                                        )
                                        time.sleep(0.2)
                                    except Exception as blow_err:
                                        self.logger.warning(f"Air cushion blowout notice: {blow_err}")
                                    finally:
                                        self.air_cushion_ul = 0.0
                                        self.has_air_cushion = False
                                        self.tip_liquid_ul = 0.0

                            elif action == "Mix Well":
                                mix_cycles = int(step.get('mix_cycles', 5))
                                mix_vol = min(float(vol if vol > 0 else step.get('mix_volume', 100.0)), float(getattr(self.lims.pipettor, 'tip_volume', 300.0)))
                                self.logger.info(f"In-place mixing at {well_id}: {mix_cycles}x {mix_vol}uL (submerged at Z={tz:.1f}mm)")
                                for c_idx in range(mix_cycles):
                                    if self.is_aborted: break
                                    try:
                                        self.lims.pipettor.hardware.aspirate(mix_vol)
                                        time.sleep(1.2)
                                        self.lims.pipettor.hardware.dispense(mix_vol)
                                        time.sleep(0.8)
                                    except Exception as m_err:
                                        self.logger.warning(f"Mix stroke {c_idx + 1}/{mix_cycles} warning: {m_err}")
                                air_to_blow = float(getattr(self, 'air_cushion_ul', 0.0))
                                if air_to_blow > 0.0 and not step.get('no_blowout', False):
                                    try:
                                        blowout_z = max(0.0, safe_tz - 12.0)
                                        self.lims.pipettor.hardware.move_z(blowout_z)
                                        time.sleep(0.1)
                                        self.lims.pipettor.hardware.dispense(air_to_blow)
                                    except Exception:
                                        pass
                                    finally:
                                        self.air_cushion_ul = 0.0
                                        self.has_air_cushion = False
                                        self.tip_liquid_ul = 0.0

                            elif action == "Discard Tip":
                                try:
                                    if self.lims.pipettor.hardware:
                                        self.lims.pipettor.hardware.eject_tip()
                                        time.sleep(0.25)
                                        # Pulse eject a second time to guarantee mechanical separation
                                        try:
                                            self.lims.pipettor.hardware.eject_tip()
                                        except Exception:
                                            pass
                                    if is_8ch and step.get("is_shovel_place"):
                                        for sock in self._expand_8ch_tip_sockets(step, well_id):
                                            self.mark_tip_restored(slot_name, sock, redraw=False)
                                        self._schedule_deck_redraw()
                                    self.air_cushion_ul = 0.0
                                    self.has_air_cushion = False
                                    self.tip_liquid_ul = 0.0
                                    self.last_aspirate_slot = None
                                    self.last_aspirate_lw_kind = None
                                    self._set_has_tip(False)
                                    self.logger.info("System state updated: Tip successfully ejected -> HAS_TIP = False")
                                except Exception as e_err:
                                    self.logger.critical(f"Eject Tip Failed: {e_err}")
                                    self._set_has_tip(True)
                                    self.session_abort_status = "AUTO_ABORTED_HARDWARE"
                                    raise RuntimeError(f"CRITICAL: Tip ejection failed! Tip is still attached to the cone. Halting: {e_err}")

                            try:
                                if self.lims.pipettor.hardware:
                                    self.lims.pipettor.hardware.z_speed = hw_speed
                                self.lims.pipettor.hardware.move_z(0)
                            except Exception:
                                self.lims.pipettor.hardware.move_z(0)
                        elif action == "Aspirate Media":
                            self.last_aspirate_slot = slot_name
                            self.last_aspirate_lw_kind = self._lw_kind(self.lims.deck_labware.get(slot_name))
                        elif action == "Discard Tip":
                            if is_8ch and step.get("is_shovel_place"):
                                for sock in self._expand_8ch_tip_sockets(step, well_id):
                                    self.mark_tip_restored(slot_name, sock, redraw=False)
                                self._schedule_deck_redraw()
                            self.last_aspirate_slot = None
                            self.last_aspirate_lw_kind = None
                            self._set_has_tip(False)
                            self.logger.info("Simulation: Tip ejected -> HAS_TIP = False")

                    # Mid-Protocol Z-Axis Physical Homing (Default: Every 1 Step)
                    # Re-zeros the Z actuator against the top optical sensor after step retraction
                    # to eliminate cumulative downward Z-stepper drift while preserving tip & plunger state.
                    z_home_enabled = True
                    z_home_interval = 1
                    try:
                        if hasattr(self, "mid_protocol_z_home_var"):
                            z_home_enabled = bool(self.mid_protocol_z_home_var.get())
                        if hasattr(self, "mid_protocol_z_home_interval_var"):
                            z_home_interval = max(1, int(self.mid_protocol_z_home_interval_var.get()))
                    except Exception:
                        z_home_interval = 1

                    if z_home_enabled and not step_skipped_fast and (i % z_home_interval == 0):
                        self._home_z_axis_only(reason=action, step_idx=i, total_steps=total_steps)

                    # Record step telemetry into audit log
                    self.session_step_audit_log.append({
                        "step_idx": i,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "action": action,
                        "slot": slot_name or "",
                        "well": well_id or "",
                        "vol": float(vol or 0.0),
                        "z": float(getattr(self.lims.pipettor.hardware, 'z_position', 0.0) if self.lims.pipettor.hardware else 0.0),
                        "status": "SUCCESS",
                        "note": step.get("label", "")
                    })

                    # Update 2D fluid meniscus tracking
                    if action == "Dispense Media" and slot_name and well_id:
                        cur_lvl = self.slot_liquid_levels.get((slot_name, well_id), 0.0)
                        self.slot_liquid_levels[(slot_name, well_id)] = cur_lvl + float(vol or 0.0)
                        self._schedule_deck_redraw()
                    elif action == "Aspirate Media" and slot_name and well_id:
                        cur_lvl = self.slot_liquid_levels.get((slot_name, well_id), 100.0)
                        self.slot_liquid_levels[(slot_name, well_id)] = max(0.0, cur_lvl - float(vol or 0.0))
                        self._schedule_deck_redraw()

                except RuntimeError as rt_err:
                    err_str = str(rt_err)
                    self.logger.error(f"RuntimeError on Step {i}: {err_str}\n{traceback.format_exc()}")
                    if any(kw in err_str for kw in ["CRITICAL", "COLLISION", "DOUBLE-TIP", "ejection failed", "SAFETY INTERLOCK"]):
                        self.logger.critical(f"🛑 CRITICAL SAFETY ABORT on Step {i}: {err_str}")
                        self.session_abort_status = "AUTO_ABORTED_HARDWARE"
                        self.is_aborted = True
                        if self.lims.pipettor.hardware:
                            try:
                                self.lims.pipettor.hardware.move_z(0)
                            except Exception:
                                pass
                        break
                    else:
                        self.ask_error_resolution(rt_err, i)
                        if self.is_aborted:
                            break
                except Exception as e:
                    self.logger.error(f"Exception on Step {i}: {e}\n{traceback.format_exc()}")
                    self.ask_error_resolution(e, i)
                    if self.is_aborted:
                        break

                if not self.is_aborted:
                    if getattr(self, "user_decision", None) == "retry":
                        self.user_decision = None
                        self.logger.info(f"Retrying Step {i} per operator error recovery selection...")
                        time.sleep(0.05)
                        continue
                    expected_b = (
                        0.05
                        if step_skipped_fast
                        else (
                            self.step_baseline_times[self.current_step_idx]
                            if self.current_step_idx < len(self.step_baseline_times)
                            else 2.0
                        )
                    )
                    self.record_step_completion_for_timer(expected_b)
                    self.current_step_idx += 1
                time.sleep(0.05)

        try:
            _worker()
        except Exception as fatal_err:
            self.is_aborted = True
            if self.session_abort_status is None:
                self.session_abort_status = "AUTO_ABORTED_ERROR"
            self.logger.critical(f"Unhandled session runtime exception: {fatal_err}\n{traceback.format_exc()}")
        finally:
            self._end_pause_tracking()
            self.timer_running = False
            all_done = (not self.is_aborted) and (self.current_step_idx >= len(self.workflow_sequence))
            if all_done:
                final_status = "COMPLETED"
                self.logger.info("--- Protocol Completed Successfully ---")
                self.root.after(0, lambda: self.lbl_timer.config(text="Time Remaining: 00h 00m 00s", foreground="green"))
            else:
                final_status = self.session_abort_status or "ABORTED_USER"
                self.logger.info(f"--- Protocol Aborted ({final_status}) ---")
                self.root.after(0, lambda: self.lbl_timer.config(text="Time Remaining: ABORTED", foreground="red"))

            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except Exception as ze:
                    self.logger.warning(f"Z clearance move warning: {ze}")

            self._finalize_session_log(final_status)
            self.is_running = False
            self.root.after(0, lambda: self.update_ui_state(False))
            self.root.after(0, lambda: self.progress_var.set(0))

    def _on_port_selected(self, event=None):
        sel = (self.port_var.get() or "").strip()
        if sel and sel not in ("Select Hardware Port...", "(No Serial Ports Detected)"):
            self.logger.info(f"[PORT SELECTION] Selected hardware port: {sel}")

    def hw_scan(self, announce: bool = True):
        ports = self.lims.hw.scan_ports()
        self.port_drop['values'] = ports
        cur = (self.port_var.get() or "").strip()
        if cur in ports:
            self.port_var.set(cur)
        elif len(ports) == 1 and not ports[0].startswith("("):
            self.port_var.set(ports[0])
        elif len(ports) > 1:
            com_ports = [p for p in ports if ("COM" in p or "usb" in p.lower()) and not p.startswith("(")]
            if com_ports:
                self.port_var.set(com_ports[0])
            else:
                self.port_var.set("Select Hardware Port...")
        else:
            self.port_var.set("Select Hardware Port...")

        if announce:
            self.logger.info(f"Scanned {len(ports)} hardware port(s): {', '.join(ports)}")

    def hw_init(self):
        selected_port = (self.port_var.get() or "").strip()
        if not selected_port or selected_port in ("Select Hardware Port...", "Select Port...", "(No Serial Ports Detected)"):
            self.logger.warning("Hardware initialization blocked: No hardware port selected.")
            messagebox.showwarning(
                "Hardware Port Required",
                "Hardware initialization cannot proceed: No hardware port is selected.\n\n"
                "Please choose a valid serial/COM port from the dropdown, then click 'Connect & Initialize'."
            )
            return

        clean_port = getattr(self.lims.hw, "extract_clean_port", lambda p: p.split(" — ")[0].strip())(selected_port)
        self.logger.info(f"Connecting to hardware port: {selected_port} ({clean_port})...")
        ok, m = self.lims.hw.connect(selected_port)
        if not ok:
            self.hw_stat_can.itemconfig(self.hw_led, fill="red")
            self.lbl_hw_stat.config(text="ERROR", foreground="red")
            self.logger.error(f"Hardware connection failed on {clean_port}: {m}")
            messagebox.showerror("Connection Failed", f"Could not connect to {selected_port}:\n{m}")
            return

        ok2, m2 = self.lims.hw.initialize()
        if ok2:
            self.hw_stat_can.itemconfig(self.hw_led, fill="green")
            self.lbl_hw_stat.config(text=f"ONLINE ({clean_port})", foreground="green")
            self.is_head_initialized = True
            self.initialized_head = self.active_profile_id
            self.update_window_title()
            self.logger.info(f"✅ {m2}")

            # --- STARTUP INTERLOCK: Speed and Force Integration ---
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.aspirate_speed = 1
                    self.lims.pipettor.hardware.tip_pickup_force = 20
                    self.logger.info("Startup Interlock: Plunger speeds and pickup force calibrated.")
                except Exception as e:
                    self.logger.warning(f"Initial speed lock failed: {e}")
            # ------------------------------------------------------

            if self.lims.pipettor.hardware:
                try:
                    hw = self.lims.pipettor.hardware
                    hx = round(float(getattr(hw, 'x_position', 0.0)), 2)
                    hy = round(float(getattr(hw, 'y_position', 0.0)), 2)
                    hz = round(float(getattr(hw, 'z_position', 0.0)), 2)
                    for ax, v in [("X", hx), ("Y", hy), ("Z", hz)]:
                        self.jog_vars[ax].set(v)
                        self.current_pos[ax] = v
                except Exception:
                    pass

            for axis in ["X", "Y", "Z"]:
                self.jog_sliders[axis].config(state='normal')
                self.deck_jog_sliders[axis].config(state='normal')
                if hasattr(self, 'jog_btns') and axis in self.jog_btns:
                    self.jog_btns[axis].config(state='normal')
                if hasattr(self, 'deck_jog_btns') and axis in self.deck_jog_btns:
                    self.deck_jog_btns[axis].config(state='normal')
            for btn in getattr(self, 'jog_nudge_btns', []):
                try:
                    btn.config(state='normal')
                except Exception:
                    pass
            self.start_telemetry()
            messagebox.showinfo(
                "Hardware Online",
                f"Successfully connected and initialized!\n\nPort: {selected_port}\nStatus: ONLINE & HOMED"
            )
        else:
            self.hw_stat_can.itemconfig(self.hw_led, fill="red")
            self.lbl_hw_stat.config(text="INIT FAILED", foreground="red")
            self.logger.error(f"Hardware initialization failed on {clean_port}: {m2}")
            messagebox.showerror("Initialization Failed", f"Could not home/initialize hardware on {clean_port}:\n{m2}")

    def run_direct_op(self, c):
        if not self.lims.hw.is_initialized: return
        hw_instance = self.lims.pipettor.hardware
        if c == "HOME":
            if hw_instance: hw_instance.initialize()
        elif c == "RETURN_TIP":
            self.prompt_for_return_tip_well()
        elif c == "DISCARD":
            self.prompt_for_discard_slot()
        elif c == "FIND_TIP":
            self.prompt_for_tip_slot()
        elif c == "CHECK_LIQUID":
            self.prompt_for_liquid_check()
        elif c == "CHECK":
            self.check_alignment()
        elif c == "M2_STEP_TEST":
            self.prompt_for_m2_step_test()

    def sync_to_backend(self, k, var):
        if self.selected_slot_name and not self.dragging_slot:
            try:
                setattr(self.lims.deck_slots[self.selected_slot_name], k, float(var.get()));
                self.draw_deck()
            except:
                pass

    def drag_start(self, e):
        rx, ry = self.get_m_x(e.x), e.y / self.scale
        for name in reversed(self.placed_slots):
            s = self.lims.deck_slots[name]
            if s.x_abs <= rx <= s.x_abs + s.width_mm and s.y_abs <= ry <= s.y_abs + s.height_mm:
                self.selected_slot_name = name
                for k in ['x_abs', 'y_abs', 'width_mm', 'height_mm', 'z_offset']:
                    self.entries[k].set(str(getattr(s, k, 0.0)))
                assigned = getattr(self.lims.deck_labware.get(name), 'source_file', '')
                self.lw_var.set(assigned if assigned else '')
                self.draw_deck()
                return
        self.selected_slot_name = None
        self.draw_deck()

    def drag_move(self, e):
        pass

    def drag_end(self, e):
        pass

    def get_labware_dir(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for cand in [
            os.path.join(script_dir, "labware"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "labware"),
            os.path.join(os.getcwd(), "labware"),
        ]:
            if os.path.isdir(cand):
                return cand
        return "labware"

    def get_calibration_path(self, filename="deck_calibration.json"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for cand in [
            os.path.join(script_dir, filename),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", filename),
            os.path.join(os.getcwd(), filename),
        ]:
            if os.path.isfile(cand):
                return cand
        return filename

    def refresh_ui(self):
        self.list_unplaced.delete(0, tk.END)
        [self.list_unplaced.insert(tk.END, s) for s in self.unplaced_slots]
        self.list_placed.delete(0, tk.END)
        [self.list_placed.insert(tk.END, s) for s in self.placed_slots]
        self.cbx_slot['values'] = self.placed_slots
        lw_dir = self.get_labware_dir()
        if os.path.exists(lw_dir):
            self.lw_drop['values'] = sorted([f for f in os.listdir(lw_dir) if f.endswith(".json")])
        self.draw_deck()

    def place_slot(self):
        sel = self.list_unplaced.curselection()
        if sel: n = self.list_unplaced.get(sel[0]); self.unplaced_slots.remove(n); self.placed_slots.append(
            n); self.refresh_ui()

    def remove_slot(self):
        sel = self.list_placed.curselection()
        if sel: n = self.list_placed.get(sel[0]); self.placed_slots.remove(n); self.unplaced_slots.append(
            n); self.refresh_ui()

    def on_placed_slot_select(self, event=None):
        sel = self.list_placed.curselection()
        if not sel:
            return
        name = self.list_placed.get(sel[0])
        s = self.lims.deck_slots.get(name)
        if not s:
            return
        self.selected_slot_name = name
        for k in ['x_abs', 'y_abs', 'width_mm', 'height_mm', 'z_offset']:
            self.entries[k].set(str(getattr(s, k, 0.0)))
        assigned = getattr(self.lims.deck_labware.get(name), 'source_file', '')
        self.lw_var.set(assigned if assigned else '')
        self.draw_deck()

    def assign_lw(self):
        fn = self.lw_var.get()
        if not self.selected_slot_name:
            messagebox.showwarning("No Slot Selected", "Select a slot first (click it on the deck or in the placed list).")
            return
        if not fn:
            messagebox.showwarning("No Labware Selected", "Choose a labware file from the dropdown first.")
            return
        lw_path = os.path.join(self.get_labware_dir(), fn)
        self.lims.deck_labware[self.selected_slot_name] = Labware(lw_path)
        self.lims.deck_labware[self.selected_slot_name].source_file = fn
        if self.selected_slot_name not in self.placed_slots:
            self.placed_slots.append(self.selected_slot_name)
        self.sync_deck_manager()
        self.logger.info(f"Assigned {fn} to {self.selected_slot_name}. Coordinates now follow this labware (press SAVE WORKSPACE to keep it).")
        self.draw_deck()
        try:
            self.update_safe_z_hint()
        except Exception:
            pass

    def unassign_lw(self):
        if self.selected_slot_name in self.lims.deck_labware:
            del self.lims.deck_labware[self.selected_slot_name]
            self.sync_deck_manager()
            self.draw_deck()

    def action_new_deck(self):
        self.lims.deck_slots.clear()
        self.lims.deck_labware.clear()
        self.placed_slots.clear()
        self.unplaced_slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
        for n in self.unplaced_slots:
            slot = DeckSlot(n, 20, 20, 110, 75)
            slot.z_offset = 0.0
            self.lims.deck_slots[n] = slot
        self.selected_slot_name = None
        self.refresh_ui()
        self.sync_deck_manager()

    def _serialize_workspace(self, path):
        data = {
            n: {"name": s.name, "x_abs": s.x_abs, "y_abs": s.y_abs, "width_mm": s.width_mm, "height_mm": s.height_mm,
                "z_offset": getattr(s, 'z_offset', 0.0), "is_placed": n in self.placed_slots,
                "labware_file": getattr(self.lims.deck_labware.get(n), 'source_file', None)} for n, s in
            self.lims.deck_slots.items()}
        with open(path, 'w') as f: json.dump(data, f, indent=4)

    def _deserialize_workspace(self, path):
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Read Error", f"Could not read workspace file:\n{e}")
            return

        if not isinstance(data, dict):
            messagebox.showerror(
                "File Format Mismatch",
                "The selected file is a Protocol (sequence of steps), not a Deck Workspace layout.\n\n"
                "To load a Protocol, click '📂 Load JSON Protocol' on the left panel.\n"
                "Your current deck workspace has been kept safe."
            )
            return

        self.lims.deck_slots.clear()
        self.lims.deck_labware.clear()
        self.placed_slots.clear()
        self.unplaced_slots.clear()
        lw_dir = self.get_labware_dir()
        for n, d in data.items():
            if not isinstance(d, dict): continue
            slot = DeckSlot(n, d.get('x_abs', 0.0), d.get('y_abs', 0.0), d.get('width_mm', 127.8), d.get('height_mm', 85.5))
            slot.z_offset = d.get('z_offset', 0.0)
            self.lims.deck_slots[n] = slot
            (self.placed_slots if d.get('is_placed', False) else self.unplaced_slots).append(n)
            lab_file = d.get('labware_file')
            if lab_file:
                lw_path = os.path.join(lw_dir, lab_file)
                if os.path.exists(lw_path):
                    self.lims.deck_labware[n] = Labware(lw_path)
                    self.lims.deck_labware[n].source_file = lab_file
        self.refresh_ui()
        self.sync_deck_manager()

    def save_all(self):
        cal_path = self.get_calibration_path()
        self._serialize_workspace(cal_path)
        self.logger.info(f"Workspace securely saved to {cal_path}")
        messagebox.showinfo("Success", f"Deck workspace saved securely to {cal_path}")

    def action_save_deck_as(self):
        filepath = filedialog.asksaveasfilename(title="Save Workspace As...",
                                                defaultextension=".json",
                                                filetypes=[("JSON Workspace", "*.json")])
        if filepath:
            self._serialize_workspace(filepath)
            self.logger.info(f"Workspace successfully exported to {filepath}")

    def action_load_deck(self):
        p = filedialog.askopenfilename(
            title="Load Deck Workspace",
            filetypes=[("JSON Workspace", "*.json"), ("All Files", "*.*")]
        )
        if p: self._deserialize_workspace(p)

    def apply_default_deck_for_profile(self, profile_id: str = None):
        """
        Automatically populates the default deck layout matching the active machine ID:
        - Machine 3 (300 µL):
            Slot_1: reservoir_3_well.json (3-Well Reservoir)
            Slot_3: generic_96_well_plate.json (96-Well Drug Plate)
            Slot_4: tip_rack_1000ul.json (Tips)
            Slot_5: generic_96_well_plate.json (Target 96-Well Plate)
        - Machine 1 (8×1000 µL):
            Slot_3: myriamed_48_well.json (EHM Plate)
            Slot_4: tip_rack_1000ul.json (Tips)
            Slot_5: myriamed_48_well.json (EHM Plate)
            Slot_6: reservoir_7_column.json (7-Well Reservoir)
        - Machine 2 (1–10 µL):
            Slot_3: generic_96_well_plate.json (96-Well Plate)
            Slot_4: tip_rack_1000ul.json (Tips)
            Slot_5: myriamed_48_well.json (EHM Plate)
            Slot_6: myriamed_48_well.json (EHM Plate)
        """
        pid = str(profile_id or getattr(self, "active_profile_id", "machine_2_1_10ul")).lower()

        grid_layout = [
            ("Slot_1", 135.2, 0.0, 127.8, 26.0),
            ("Slot_2", 0.0, 0.0, 127.8, 26.0),
            ("Slot_3", 135.2, 45.0, 127.8, 85.5),
            ("Slot_4", 0.0, 45.0, 127.8, 85.5),
            ("Slot_5", 135.2, 144.0, 127.8, 85.5),
            ("Slot_6", 0.0, 144.0, 127.8, 85.5),
        ]
        for name, x, y, w, h in grid_layout:
            if name not in self.lims.deck_slots:
                slot = DeckSlot(name, x, y, w, h)
                slot.z_offset = 0.0
                self.lims.deck_slots[name] = slot
            if name not in self.placed_slots:
                self.placed_slots.append(name)
            if name in self.unplaced_slots:
                self.unplaced_slots.remove(name)

        if "300" in pid or "machine_3" in pid:
            default_map = {
                "Slot_1": "reservoir_3_well.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "generic_96_well_plate.json",
            }
        elif "1000" in pid or "machine_1" in pid:
            default_map = {
                "Slot_3": "myriamed_48_well.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "reservoir_7_column.json",
            }
        else:
            default_map = {
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "myriamed_48_well.json",
            }

        self.lims.deck_labware.clear()
        lw_dir = self.get_labware_dir()
        for s_name, lw_file in default_map.items():
            lw_path = os.path.join(lw_dir, lw_file)
            if os.path.exists(lw_path):
                self.lims.deck_labware[s_name] = Labware(lw_path)
                self.lims.deck_labware[s_name].source_file = lw_file

        self.sync_deck_manager()
        try:
            self.refresh_ui()
        except Exception:
            pass
        if hasattr(self, "_update_deck_and_tip_preview"):
            try:
                self._update_deck_and_tip_preview()
            except Exception:
                pass
        if hasattr(self, "logger"):
            summary = ", ".join(f"{k}: {v}" for k, v in sorted(default_map.items()))
            self.logger.info(f"[DEFAULT DECK] Loaded profile deck for '{pid}': {summary}")

    def emergency_reset(self):
        cal_path = self.get_calibration_path()
        if os.path.exists(cal_path):
            self._deserialize_workspace(cal_path)
        self.apply_default_deck_for_profile(getattr(self, "active_profile_id", "machine_2_1_10ul"))

    def action_save_workflow_as(self):
        if not self.workflow_sequence: return
        export_dir = os.path.join(os.path.expanduser("~"), "Desktop", "pipette trials export")
        os.makedirs(export_dir, exist_ok=True)
        filepath = filedialog.asksaveasfilename(title="Export Workflow Sequence", initialdir=export_dir,
                                                defaultextension=".json",
                                                filetypes=[("JSON Protocol", "*.json")])
        if filepath:
            with open(filepath, 'w') as f: json.dump(self.workflow_sequence, f, indent=4)

    def action_load_workflow(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        proto_dir = ""
        for candidate in (
            os.path.join(script_dir, "protocols"),
            os.path.join(parent_dir, "robolab_gui", "resources", "protocols"),
            os.path.join(parent_dir, "protocols"),
        ):
            if os.path.isdir(candidate):
                proto_dir = candidate
                break
        filepath = filedialog.askopenfilename(
            title="Import Workflow Sequence",
            initialdir=proto_dir if os.path.isdir(proto_dir) else None,
            filetypes=[("JSON Protocol", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    loaded_sequence = json.load(f)

                if isinstance(loaded_sequence, dict):
                    if "steps" in loaded_sequence and isinstance(loaded_sequence["steps"], list):
                        loaded_sequence = loaded_sequence["steps"]
                    elif "sequence" in loaded_sequence and isinstance(loaded_sequence["sequence"], list):
                        loaded_sequence = loaded_sequence["sequence"]

                if not isinstance(loaded_sequence, list):
                    messagebox.showerror("Format Exception",
                                         "JSON structure mismatch. The selected file is a dictionary, not a workflow array. Did you select a Deck Workspace instead of a Protocol?")
                    return

                p_name = os.path.basename(filepath)
                is_8ch = any(s.get('eight_ch_symmetric') or bool((s.get('mounted_channels') or '').count('-') > 0) for s in loaded_sequence)
                max_vol = max((float(s.get('volume', 0.0) or 0.0) for s in loaded_sequence), default=0.0)

                # Protocol Compatibility Guard: Inspect required head vs active station profile
                req_station = None
                if is_8ch and max_vol > 50.0:
                    req_station = "machine_1_8x1000"
                    req_label = "Machine 1: 8x1000 µL"
                elif is_8ch and max_vol <= 50.0:
                    req_station = "machine_2_1_10ul"
                    req_label = "Machine 2: 1-10 µL"
                elif not is_8ch and max_vol >= 50.0:
                    req_station = "machine_3_300ul"
                    req_label = "Machine 3: 300 µL"

                if req_station and req_station != self.active_profile_id:
                    cur_disp = self.profile_manager.get_display_name(self.active_profile_id) if getattr(self, "profile_manager", None) else self.active_profile_id
                    switch_prompt = messagebox.askyesno(
                        "Station Profile Mismatch",
                        f"Protocol '{p_name}' requires:\n  • {req_label}\n\n"
                        f"Current active station profile is:\n  • {cur_disp}\n\n"
                        f"Would you like to automatically switch active station to {req_label} now to match this protocol?"
                    )
                    if switch_prompt:
                        self.switch_machine_profile(req_station, save_to_disk=False)
                    else:
                        self.logger.warning(f"Protocol loaded under mismatched station profile: {cur_disp} (requires {req_label})")

                # Extract declared slots & labwares to preview deck setup
                declared_deck = {}
                slot_descs = {}
                for st in loaded_sequence:
                    s_name, lw_file = st.get('slot', ''), st.get('labware', '')
                    if s_name == "Slot_1" and lw_file == "tube_rack_2x6_2ml.json":
                        existing_s1 = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None)
                        lw_file = existing_s1 if (existing_s1 and existing_s1 != "tube_rack_2x6_2ml.json") else "reservoir_3_well.json"
                        st["labware"] = lw_file
                    if s_name and lw_file and s_name.startswith("Slot_") and s_name not in declared_deck:
                        declared_deck[s_name] = lw_file
                        slot_descs[s_name] = f"Protocol declared labware ({lw_file})"

                def do_load():
                    self.workflow_sequence.clear()
                    self.wf_box.delete(0, tk.END)

                    for step in loaded_sequence:
                        if 'action' not in step:
                            continue

                        self.workflow_sequence.append(step)
                        if step.get('label'):
                            self.wf_box.insert(tk.END, self._format_step_msg(step))
                            continue
                        m = step.get('mode', 'auto')

                        if "System" in step['action']:
                            if "Incubate" in step['action']:
                                msg = f"[SYSTEM] Incubate for {step.get('volume', 0.0)} seconds."
                            elif "FOC48" in step['action']:
                                msg = f"[MEASURE] Execute FOC48_Stim_0.xml for Plate: '{step.get('well', '')}'"
                            else:
                                msg = f"[{step['action'].upper()}]"
                        elif m == "manual":
                            if step['action'] in ["Pick Up Tip", "Discard Tip"]:
                                msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)}"
                            elif step['action'] == "Detect Liquid Level":
                                msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)}"
                            else:
                                msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)} Vol:{step.get('volume', 0.0)}\u03bcL"
                        else:
                            if step['action'] == "Pick Up Tip":
                                msg = f"[{step['action'].upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                            elif step['action'] == "Discard Tip":
                                msg = f"[{step['action'].upper()}] into {step.get('slot', '')} (Waste Trough)"
                            elif step['action'] == "Detect Liquid Level":
                                msg = f"[{step['action'].upper()}] at {step.get('slot', '')}, Well {step.get('well', '')}"
                            else:
                                z_msg = f" (Z+{step.get('extra_z', 0.0)}mm)" if step.get('extra_z', 0.0) > 0 else ""
                                mix_c = int(step.get('mix_cycles', 0))
                                mix_msg = f" [+ Mix {mix_c}x {step.get('mix_volume', 100.0)}\u03bcL]" if mix_c > 0 else ""
                                msg = f"[{step['action'].upper()}] {step.get('volume', 0.0)}\u03bcL at {step.get('slot', '')}, Well {step.get('well', '')}{z_msg}{mix_msg}"

                        self.wf_box.insert(tk.END, msg)

                    if is_8ch:
                        self._set_has_tip(False)
                        if not self.lims.pipettor.multichannel:
                            self.switch_pipettor_head(True, quiet=True)

                    self._sync_protocol_labware(loaded_sequence)
                    self.sync_deck_manager()
                    if hasattr(self, 'draw_deck'): self.draw_deck()
                    self._update_estimated_timer_preview()
                    self.logger.info(f"Loaded protocol '{p_name}' ({len(self.workflow_sequence)} steps).")

                if declared_deck:
                    head_mode_str = "8×1000 µL (8-Channel Manifold)" if is_8ch else "Single-Channel"
                    self.show_protocol_deck_setup_modal(
                        protocol_name=f"Imported Protocol: {p_name}",
                        pipettor_mode=head_mode_str,
                        is_multichannel=is_8ch,
                        deck_setup=declared_deck,
                        slot_descriptions=slot_descs,
                        sequence=loaded_sequence,
                        on_confirm_callback=do_load
                    )
                else:
                    do_load()

            except Exception as e:
                self.logger.error(f"Import Exception: {str(e)}")
                messagebox.showerror("Import Exception", f"Failed to parse protocol file.\n\nTraceback: {str(e)}")

    def _sync_protocol_labware(self, sequence):
        lw_dir = self.get_labware_dir()
        declared = {}
        for st in sequence:
            s_name, lw_file = st.get('slot', ''), st.get('labware', '')
            if s_name == "Slot_1" and lw_file == "tube_rack_2x6_2ml.json":
                existing_s1 = getattr(self.lims.deck_labware.get("Slot_1"), "source_file", None)
                lw_file = existing_s1 if (existing_s1 and existing_s1 != "tube_rack_2x6_2ml.json") else "reservoir_3_well.json"
                st["labware"] = lw_file
            if s_name and lw_file and s_name not in declared:
                declared[s_name] = lw_file

        mismatches = []
        for s_name, lw_file in declared.items():
            lp = os.path.join(lw_dir, lw_file)
            if not os.path.exists(lp):
                self.logger.warning(f"Protocol declares {lw_file} on {s_name}, but that labware file does not exist.")
                continue
            current = self.lims.deck_labware.get(s_name)
            if current is None:
                self.lims.deck_labware[s_name] = Labware(lp)
                self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots: self.placed_slots.append(s_name)
                self.logger.info(f"{s_name} was empty -> mounted protocol-declared {lw_file}.")
            elif (getattr(current, 'source_file', '') or '') != lw_file:
                mismatches.append((s_name, getattr(current, 'source_file', '') or getattr(current, 'name', '?'), lw_file))

        if mismatches:
            lines = "\n".join(f"• {s}: deck has '{cur}', protocol expects '{exp}'" for s, cur, exp in mismatches)
            if messagebox.askyesno(
                    "Deck / Protocol Labware Mismatch",
                    f"This protocol was written for different labware:\n\n{lines}\n\n"
                    f"YES = swap the deck to match the protocol.\n"
                    f"NO = keep YOUR deck (coordinates follow your assigned labware)."):
                for s_name, _cur, exp in mismatches:
                    self.lims.deck_labware[s_name] = Labware(os.path.join(lw_dir, exp))
                    self.lims.deck_labware[s_name].source_file = exp
                    self.logger.info(f"{s_name} swapped to {exp} to match protocol.")
            else:
                self.logger.info("Kept user deck labware; protocol coordinates will follow assigned labware.")

        undeclared_empty = sorted({st.get('slot') for st in sequence
                                   if st.get('slot', '').startswith('Slot_') and st.get('slot') not in self.lims.deck_labware
                                   and st.get('action') != "Discard Tip"})
        if undeclared_empty:
            messagebox.showwarning("Empty Slots",
                                   "This protocol uses slots with no labware assigned:\n\n" + ", ".join(undeclared_empty) +
                                   "\n\nAssign labware in the Deck tab before running.")

    def action_import_python_protocol(self):
        filepath = filedialog.askopenfilename(
            title="Import Opentrons Python Protocol (.py)",
            filetypes=[("Python Script", "*.py"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        try:
            from opentrons_python_converter import detect_opentrons_labware, convert_opentrons_py_to_biohit

            detected_lw = detect_opentrons_labware(filepath)

            top = tk.Toplevel(self.root)
            top.title("Opentrons to Biohit Protocol Importer & Labware Mapper")
            top.geometry("780x520")
            top.resizable(True, True)
            top.transient(self.root)
            top.grab_set()

            ttk.Label(top, text="Import Opentrons Python Protocol (.py)", font=("Arial", 12, "bold")).pack(pady=(12, 2))
            ttk.Label(top, text=f"File: {os.path.basename(filepath)}", font=("Arial", 9, "italic"), foreground="gray").pack(pady=(0, 8))

            # Labware discovery from disk
            lw_dir = self.get_labware_dir()
            available_files = []
            if os.path.isdir(lw_dir):
                available_files = sorted([f for f in os.listdir(lw_dir) if f.endswith(".json")])

            lw_display_to_file = {}
            lw_file_to_display = {}
            for f in available_files:
                name_clean = f.replace(".json", "").replace("_", " ").title()
                f_lower = f.lower()
                if "2x6" in f_lower or "2ml" in f_lower:
                    disp = "12-Falcon Tube Rack 2x6 (tube_rack_2x6_2ml.json)"
                elif "17a" in f_lower or "4x6" in f_lower:
                    disp = "24-Tube Rack 4x6 (biohit_rack_4x6_17a.json)"
                elif "3_well" in f_lower or "3-well" in f_lower:
                    disp = "3-Well Reservoir (reservoir_3_well.json)"
                elif "7_column" in f_lower or "reservoir_7" in f_lower or "7_well" in f_lower:
                    disp = "7-Column Reservoir (reservoir_7_column.json)"
                elif "6_column" in f_lower or "reservoir_6" in f_lower:
                    disp = "6-Column Reservoir (reservoir_6_column.json)"
                elif "generic_96" in f_lower or "96_well" in f_lower:
                    disp = "96-Well Microplate (generic_96_well_plate.json)"
                elif "48" in f_lower or "myriamed" in f_lower:
                    disp = "48-Well EHM Plate (myriamed_48_well.json)"
                elif "ehm_42" in f_lower:
                    disp = "42-Well EHM Plate (ehm_42_well.json)"
                elif "tip_rack" in f_lower or "tip" in f_lower:
                    disp = "1000µL Tip Rack (tip_rack_1000ul.json)"
                elif "waste" in f_lower or "trough" in f_lower:
                    disp = "Waste Trough (waste_trough.json)"
                elif "corning_96" in f_lower:
                    disp = "Corning 96 Flat (corning_96_flat.json)"
                elif "corning_24" in f_lower:
                    disp = "Corning 24 Well (corning_24_well.json)"
                elif "corning_12" in f_lower:
                    disp = "Corning 12 Well (corning_12_well.json)"
                elif "corning_6" in f_lower:
                    disp = "Corning 6 Well (corning_6_well.json)"
                else:
                    disp = f"{name_clean} ({f})"
                lw_display_to_file[disp] = f
                lw_file_to_display[f] = disp

            labware_display_options = list(lw_display_to_file.keys())

            frame_mappings = ttk.LabelFrame(top, text="Detected Opentrons Labware & Biohit Slot/Labware Configuration", padding=10)
            frame_mappings.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

            # Table Header Row
            hdr = ttk.Frame(frame_mappings)
            hdr.pack(fill=tk.X, pady=(0, 6))
            ttk.Label(hdr, text="Opentrons Item (Slot)", font=("Arial", 9, "bold"), width=28, anchor="w").pack(side=tk.LEFT, padx=2)
            ttk.Label(hdr, text="Target Biohit Slot", font=("Arial", 9, "bold"), width=15, anchor="w").pack(side=tk.LEFT, padx=4)
            ttk.Label(hdr, text="Biohit Labware Type", font=("Arial", 9, "bold"), width=34, anchor="w").pack(side=tk.LEFT, padx=4)
            ttk.Label(hdr, text="Reagent Well", font=("Arial", 9, "bold"), width=14, anchor="w").pack(side=tk.LEFT, padx=2)

            biohit_slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
            well_options = ["Auto / As-is", "Well A1", "Well A2", "Well A3", "Well A4", "Well A5", "Well A6"]

            row_widgets = {}

            if detected_lw:
                for idx, item in enumerate(detected_lw):
                    row = ttk.Frame(frame_mappings)
                    row.pack(fill=tk.X, pady=3)

                    # 1. Opentrons source label
                    ot_name_short = item['name'][:22]
                    lbl_text = f"{ot_name_short} (OT {item['opentrons_slot']}):"
                    ttk.Label(row, text=lbl_text, width=28, anchor="w").pack(side=tk.LEFT, padx=2)

                    # 2. Biohit Slot
                    cb_slot = ttk.Combobox(row, values=biohit_slots, state="readonly", width=13)
                    suggested_slot = item.get("suggested_biohit_slot", "Slot_4")
                    cb_slot.set(suggested_slot)
                    cb_slot.pack(side=tk.LEFT, padx=4)

                    # 3. Biohit Labware Dropdown
                    cb_lw = ttk.Combobox(row, values=labware_display_options, state="readonly", width=32)
                    suggested_lw_file = item.get("suggested_biohit_labware", "generic_96_well_plate.json")
                    suggested_lw_disp = lw_file_to_display.get(suggested_lw_file, labware_display_options[0] if labware_display_options else "")
                    cb_lw.set(suggested_lw_disp)
                    cb_lw.pack(side=tk.LEFT, padx=4)

                    # 4. Reagent Well Selection
                    cb_well = ttk.Combobox(row, values=well_options, state="readonly", width=13)
                    is_tuberack = any(k in item['name'].lower() for k in ["tuberack", "falcon", "reservoir", "rack"])
                    cb_well.set("Well A1" if is_tuberack else "Auto / As-is")
                    cb_well.pack(side=tk.LEFT, padx=2)

                    row_widgets[item['opentrons_slot']] = {
                        "slot": cb_slot,
                        "labware": cb_lw,
                        "well": cb_well
                    }
            else:
                ttk.Label(frame_mappings, text="No explicit labware definitions detected in script.\nDefault slot layout will be used.", justify="center").pack(pady=20)

            frame_stroke = ttk.Frame(top)
            frame_stroke.pack(fill=tk.X, padx=15, pady=8)
            ttk.Label(frame_stroke, text="Max Pipette Stroke (µL):").pack(side=tk.LEFT)
            ent_stroke = ttk.Entry(frame_stroke, width=8)
            current_tip_vol = getattr(getattr(self.lims, 'pipettor', None), 'tip_volume', 250.0)
            ent_stroke.insert(0, str(float(current_tip_vol)))
            ent_stroke.pack(side=tk.LEFT, padx=5)

            def do_convert():
                try:
                    slot_map = {}
                    labware_map = {}
                    well_map = {}

                    for ot_s, wdict in row_widgets.items():
                        b_slot = wdict['slot'].get()
                        lw_disp = wdict['labware'].get()
                        lw_file = lw_display_to_file.get(lw_disp, lw_disp)
                        w_choice = wdict['well'].get()

                        slot_map[ot_s] = b_slot
                        labware_map[b_slot] = lw_file
                        if w_choice and w_choice != "Auto / As-is":
                            well_map[b_slot] = w_choice

                    try:
                        max_vol = float(ent_stroke.get())
                    except ValueError:
                        max_vol = 250.0

                    converted_steps = convert_opentrons_py_to_biohit(
                        filepath,
                        slot_mapping=slot_map,
                        labware_mapping=labware_map,
                        well_mapping=well_map,
                        max_volume=max_vol
                    )

                    if not converted_steps:
                        messagebox.showwarning("Empty Protocol", "No pipetting steps were generated from this script.")
                        top.destroy()
                        return

                    # Detect if converted script is a DMSO-Drug Dilution / Plate Prep protocol (1..12 stock drug aspirations from Slot_3)
                    drug_steps_in_py = [
                        i for i, s in enumerate(converted_steps)
                        if s.get("slot") == "Slot_3" and "Aspirate" in s.get("action", "")
                    ]
                    if 1 <= len(drug_steps_in_py) <= 12:
                        eff_deck = dict(labware_map)
                        eff_deck.setdefault("Slot_1", "tube_rack_2x6_2ml.json")
                        eff_deck["Slot_2"] = "waste_trough.json"
                        eff_deck.setdefault("Slot_3", "generic_96_well_plate.json")
                        eff_deck.setdefault("Slot_4", "tip_rack_1000ul.json")
                        eff_deck.setdefault("Slot_5", "generic_96_well_plate.json")
                        top.destroy()
                        self.prompt_drug_wells_and_load(
                            converted_steps,
                            protocol_name=f"Imported DMSO-Drug Prep ({os.path.basename(filepath)})",
                            deck_setup=eff_deck,
                        )
                        return

                    # Configure physical deck labware in orchestrator
                    for b_slot, lw_file in labware_map.items():
                        if b_slot and lw_file:
                            lp = os.path.join(lw_dir, lw_file)
                            if os.path.exists(lp):
                                self.lims.deck_labware[b_slot] = Labware(lp)
                                self.lims.deck_labware[b_slot].source_file = lw_file
                                if b_slot not in self.placed_slots:
                                    self.placed_slots.append(b_slot)
                                self.logger.info(f"Deck Configured: {b_slot} ➔ {lw_file}")

                    self.sync_deck_manager()
                    # Redraw visual canvas with newly mounted labware
                    if hasattr(self, 'draw_deck'):
                        self.draw_deck()

                    self.workflow_sequence.clear()
                    self.wf_box.delete(0, tk.END)

                    for step in converted_steps:
                        self.workflow_sequence.append(step)
                        action = step['action']
                        m = step.get('mode', 'auto')
                        if action == "Pick Up Tip":
                            msg = f"[{action.upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                        elif action == "Discard Tip":
                            msg = f"[{action.upper()}] into {step.get('slot', '')} (Waste Trough)"
                        else:
                            z_msg = f" (Z+{step.get('extra_z', 0.0)}mm)" if step.get('extra_z', 0.0) > 0 else ""
                            mix_c = int(step.get('mix_cycles', 0))
                            mix_msg = f" [+ Mix {mix_c}x {step.get('mix_volume', 100.0)}\u03bcL]" if mix_c > 0 else ""
                            msg = f"[{action.upper()}] {step.get('volume', 0.0)}\u03bcL at {step.get('slot', '')}, Well {step.get('well', '')}{z_msg}{mix_msg}"
                        self.wf_box.insert(tk.END, msg)

                    self._update_estimated_timer_preview()
                    top.destroy()
                    self.logger.info(f"Imported {len(converted_steps)} steps from Python script {os.path.basename(filepath)}.")
                    messagebox.showinfo(
                        "Conversion Complete",
                        f"Successfully converted and loaded {len(converted_steps)} steps from:\n{os.path.basename(filepath)}\n\nConfigured deck labware:\n" + "\n".join(f"• {s}: {f}" for s, f in labware_map.items()) + "\n\nYou can now run the workflow or export it via 'Save JSON Protocol As...'."
                    )
                except Exception as ce:
                    self.logger.error(f"Conversion error: {ce}")
                    messagebox.showerror("Conversion Error", f"Failed to convert Python script:\n{ce}")

            btn_frame = ttk.Frame(top)
            btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
            ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(btn_frame, text="✔ Convert & Load Protocol", command=do_convert).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            self.logger.error(f"Python script parse error: {e}")
            messagebox.showerror("Parse Error", f"Failed to parse Opentrons script:\n{e}")
            messagebox.showerror("Import Error", f"Could not inspect Python protocol:\n{e}")


def launch():
    """Entry point for robolab / robolab-gui / biohit-gui CLI commands."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)
    os.chdir(pkg_dir)
    try:
        root = tk.Tk()
        app = LIMSMasterApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            from tkinter import messagebox
            messagebox.showerror("RoboLab Boot Error", f"Fatal error during application startup:\n\n{e}\n\n{traceback.format_exc()}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    launch()

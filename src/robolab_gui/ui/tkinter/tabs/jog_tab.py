"""Manual Jog and Calibration tab."""

import tkinter as tk
from tkinter import ttk
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.configuration.calibration_service import CalibrationService
from robolab_gui.ui.tkinter.dialogs.z_verification_dialog import ZVerificationDialog
from robolab_gui.ui.tkinter.themes import GUITheme


class JogCalibrationTab(ttk.Frame):
    """Manual axis jogging and calibration tools."""

    def __init__(self, parent, session: HardwareSession, cal_service: CalibrationService, theme: GUITheme):
        super().__init__(parent)
        self.session = session
        self.cal_service = cal_service
        self.theme = theme

        self._build_ui()

    def _build_ui(self):
        jog_frame = ttk.LabelFrame(self, text="Manual Motor Jogging (XYZ)")
        jog_frame.pack(fill="x", padx=15, pady=10)

        ttk.Button(jog_frame, text="Home All (0,0,0)", command=self._home).pack(side="left", padx=10, pady=10)
        ttk.Button(jog_frame, text="Safe Traverse (Z=0)", command=self._safe_z).pack(side="left", padx=10, pady=10)

        # Tim's Z-check tool launcher button
        tim_frame = ttk.LabelFrame(self, text="Assisted Calibration Tools")
        tim_frame.pack(fill="x", padx=15, pady=10)

        ttk.Button(tim_frame, text="🔍 Tim's Slot-by-Slot Tip Z-Verification Tool...", command=self._open_z_check).pack(padx=15, pady=15, anchor="w")

    def _home(self):
        if self.session.is_connected():
            self.session.hardware.home()

    def _safe_z(self):
        if self.session.is_connected():
            self.session.hardware.move_abs(z=0.0)

    def _open_z_check(self):
        dlg = ZVerificationDialog(self, self.cal_service, self.session)

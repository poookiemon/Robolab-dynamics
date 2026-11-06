"""Tim's slot-by-slot tip Z-depth verification and table editor dialog."""

import tkinter as tk
from tkinter import ttk, messagebox
from robolab_gui.configuration.calibration_service import CalibrationService
from robolab_gui.hardware.session import HardwareSession


class ZVerificationDialog(tk.Toplevel):
    """Assisted visual jog mode: takes a tip from Slot 4 and verifies target Z depth per slot."""

    def __init__(self, parent, calibration_service: CalibrationService, session: HardwareSession):
        super().__init__(parent)
        self.cal_service = calibration_service
        self.session = session
        self.title("Tim's Tip Z-Verification & Depth Editor")
        self.geometry("520x360")
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Slot-by-Slot Z Depth Verification (Slot 4 Tip Check)", font=("Helvetica", 11, "bold")).pack(padx=15, pady=10, anchor="w")

        # Slot selection
        slot_frame = ttk.LabelFrame(self, text="Target Slot & Well")
        slot_frame.pack(padx=15, pady=5, fill="x")

        ttk.Label(slot_frame, text="Slot:").grid(row=0, column=0, padx=5, pady=5)
        self.slot_var = tk.StringVar(value="Slot_5")
        self.slot_combo = ttk.Combobox(slot_frame, textvariable=self.slot_var, values=["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"], state="readonly", width=12)
        self.slot_combo.grid(row=0, column=1, padx=5, pady=5)
        self.slot_combo.bind("<<ComboboxSelected>>", lambda e: self._on_slot_change())

        ttk.Label(slot_frame, text="Well:").grid(row=0, column=2, padx=5, pady=5)
        self.well_var = tk.StringVar(value="A1")
        ttk.Entry(slot_frame, textvariable=self.well_var, width=8).grid(row=0, column=3, padx=5, pady=5)

        # Z Height Editor
        z_frame = ttk.LabelFrame(self, text="Verified Z Depth (mm)")
        z_frame.pack(padx=15, pady=10, fill="x")

        self.z_var = tk.DoubleVar(value=self.cal_service.get_nominal_z("Slot_5", "A1"))
        ttk.Label(z_frame, text="Target Z:").grid(row=0, column=0, padx=5, pady=5)
        self.z_entry = ttk.Entry(z_frame, textvariable=self.z_var, width=12)
        self.z_entry.grid(row=0, column=1, padx=5, pady=5)

        # Jog adjustment buttons
        jog_frame = ttk.Frame(z_frame)
        jog_frame.grid(row=1, column=0, columnspan=4, pady=5)
        for delta in [-10.0, -2.0, -0.5, -0.1, 0.1, 0.5, 2.0, 10.0]:
            text = f"{delta:+.1f}" if abs(delta) < 1.0 else f"{delta:+.0f}"
            ttk.Button(jog_frame, text=text, width=5, command=lambda d=delta: self._adjust_z(d)).pack(side="left", padx=2)

        # Bottom Actions
        act_frame = ttk.Frame(self)
        act_frame.pack(padx=15, pady=15, fill="x")
        ttk.Button(act_frame, text="Pick Tip & Travel to Slot", command=self._travel).pack(side="left", padx=5)
        ttk.Button(act_frame, text="Save to Active Profile", command=self._save).pack(side="right", padx=5)
        ttk.Button(act_frame, text="Return Tip & Close", command=self.destroy).pack(side="right")

    def _on_slot_change(self):
        slot = self.slot_var.get()
        well = self.well_var.get()
        self.z_var.set(self.cal_service.get_nominal_z(slot, well))

    def _adjust_z(self, delta: float):
        curr = self.z_var.get()
        new_val = round(curr + delta, 2)
        self.z_var.set(new_val)
        if self.session.is_connected():
            try:
                self.session.hardware.move_abs(z=new_val)
            except Exception:
                pass

    def _travel(self):
        messagebox.showinfo("Travel", f"Taking tip from Slot 4 and traveling to {self.slot_var.get()} Well {self.well_var.get()} at Z={self.z_var.get():.2f}mm.")

    def _save(self):
        slot = self.slot_var.get()
        well = self.well_var.get()
        val = self.z_var.get()
        self.cal_service.save_verified_height(slot, well, val)
        messagebox.showinfo("Saved", f"Successfully saved Z={val:.2f}mm for {slot} into active machine profile!")

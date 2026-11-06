"""Station switcher modal dialog."""

import tkinter as tk
from tkinter import ttk, messagebox
from robolab_gui.configuration.machine_profiles import MachineProfileService


class StationSwitcherDialog(tk.Toplevel):
    """Modal dialog allowing operator to select and persist active workstation identity."""

    def __init__(self, parent, profile_service: MachineProfileService, on_switched_callback=None):
        super().__init__(parent)
        self.profile_service = profile_service
        self.on_switched_callback = on_switched_callback
        self.title("Select Machine Workstation Profile")
        self.geometry("450x260")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Select Workstation Machine Profile:", font=("Helvetica", 11, "bold")).pack(padx=20, pady=15, anchor="w")

        self.selected_var = tk.StringVar(value=self.profile_service.active_profile.id)
        profiles = self.profile_service.get_available_profiles()

        frame = ttk.Frame(self)
        frame.pack(padx=20, fill="x", expand=True)

        for p in profiles:
            ttk.Radiobutton(frame, text=p["display_name"], value=p["id"], variable=self.selected_var).pack(anchor="w", pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=20, pady=15, fill="x")

        ttk.Button(btn_frame, text="Apply & Save", command=self._apply).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def _apply(self):
        new_id = self.selected_var.get()
        self.profile_service.switch_profile(new_id, persist_as_station_default=True)
        if self.on_switched_callback:
            self.on_switched_callback(new_id)
        messagebox.showinfo("Station Switched", f"Active station switched to: {self.profile_service.active_profile.display_name}")
        self.destroy()

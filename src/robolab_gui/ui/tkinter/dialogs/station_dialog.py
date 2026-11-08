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
        self.geometry("480x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        try:
            self.lift()
            self.attributes("-topmost", True)
            self.after_idle(lambda: self.attributes("-topmost", False))
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="🏢 Select Workstation Machine Profile:", font=("Helvetica", 11, "bold")).pack(padx=20, pady=(15, 5), anchor="w")
        ttk.Label(
            self,
            text="Choose which physical robot this computer is running.",
            font=("Helvetica", 9),
            foreground="#555",
        ).pack(padx=20, pady=(0, 10), anchor="w")

        self.selected_var = tk.StringVar(value=self.profile_service.active_profile.id)
        profiles = self.profile_service.get_available_profiles()

        frame = ttk.Frame(self)
        frame.pack(padx=20, fill="x", expand=True)

        for p in profiles:
            ttk.Radiobutton(frame, text=p["display_name"], value=p["id"], variable=self.selected_var).pack(anchor="w", pady=4)

        self.persist_var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(self, text="📌 Remember this machine on this computer (.machine_id)", variable=self.persist_var)
        chk.pack(padx=20, pady=(8, 2), anchor="w")

        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=20, pady=12, fill="x")

        ttk.Button(btn_frame, text="✔ Activate & Remember", command=self._apply).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def _apply(self):
        new_id = self.selected_var.get()
        persist = self.persist_var.get()
        self.profile_service.switch_profile(new_id, persist_as_station_default=persist)
        if self.on_switched_callback:
            self.on_switched_callback(new_id)
        msg = "Saved to local .machine_id on this computer." if persist else "Active for this session only."
        messagebox.showinfo("Station Switched", f"Active station switched to:\n{self.profile_service.active_profile.display_name}\n\n{msg}")
        self.destroy()

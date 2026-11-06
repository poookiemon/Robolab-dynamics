"""Interactive error recovery dialog with user-directed clearance targeting."""

import tkinter as tk
from tkinter import ttk
from robolab_gui.execution.recovery import RecoveryAction, RecoveryDecision


class ErrorRecoveryDialog(tk.Toplevel):
    """Modal dialog prompting operator when a step encounters an error."""

    def __init__(self, parent, error: Exception, step_index: int):
        super().__init__(parent)
        self.error = error
        self.step_index = step_index
        self.result: RecoveryAction = RecoveryAction(decision=RecoveryDecision.SAFE_ABORT)

        self.title("RoboLab - Step Execution Exception")
        self.geometry("500x320")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text=f"⚠️ Exception at Step {self.step_index + 1}", font=("Helvetica", 12, "bold"), foreground="#dc3545").pack(padx=20, pady=10, anchor="w")
        ttk.Label(self, text=str(self.error), wraplength=460).pack(padx=20, pady=5, anchor="w")

        # Destination frame for Clear / Unjam
        dest_frame = ttk.LabelFrame(self, text="Target Destination for Tip Clearance / Unjam")
        dest_frame.pack(padx=20, pady=10, fill="x")

        ttk.Label(dest_frame, text="Slot:").grid(row=0, column=0, padx=5, pady=5)
        self.slot_var = tk.StringVar(value="Slot_2")
        ttk.Combobox(dest_frame, textvariable=self.slot_var, values=["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"], width=10, state="readonly").grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dest_frame, text="Well:").grid(row=0, column=2, padx=5, pady=5)
        self.well_var = tk.StringVar(value="A1")
        ttk.Entry(dest_frame, textvariable=self.well_var, width=8).grid(row=0, column=3, padx=5, pady=5)

        # 4 Decision Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=20, pady=15, fill="x")

        ttk.Button(btn_frame, text="🔄 Retry Step", command=self._on_retry).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🧹 Clear / Unjam", command=self._on_clear).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="⏩ Skip Step", command=self._on_skip).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🛑 Safe Abort", command=self._on_abort).pack(side="right", padx=5)

    def _on_retry(self):
        self.result = RecoveryAction(decision=RecoveryDecision.RETRY)
        self.destroy()

    def _on_clear(self):
        self.result = RecoveryAction(
            decision=RecoveryDecision.CLEAR_UNJAM,
            clear_slot=self.slot_var.get(),
            clear_well=self.well_var.get(),
        )
        self.destroy()

    def _on_skip(self):
        self.result = RecoveryAction(decision=RecoveryDecision.SKIP)
        self.destroy()

    def _on_abort(self):
        self.result = RecoveryAction(decision=RecoveryDecision.SAFE_ABORT)
        self.destroy()

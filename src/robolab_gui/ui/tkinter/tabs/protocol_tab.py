"""Protocol Runner tab implementation."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from robolab_gui.execution.engine import ExecutionEngine
from robolab_gui.protocols.catalog import ProtocolCatalog
from robolab_gui.protocols.importers.json_importer import JSONProtocolImporter
from robolab_gui.protocols.planning import ProtocolPlanner
from robolab_gui.ui.tkinter.themes import GUITheme


class ProtocolRunnerTab(ttk.Frame):
    """Protocol runner tab with dynamic machine dropdown, live timer, and run controls."""

    def __init__(self, parent, engine: ExecutionEngine, catalog: ProtocolCatalog, theme: GUITheme):
        super().__init__(parent)
        self.engine = engine
        self.catalog = catalog
        self.theme = theme

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.LabelFrame(self, text="Protocol Selection")
        top_frame.pack(fill="x", padx=15, pady=10)

        self.protocol_var = tk.StringVar()
        protocols = list(self.catalog.get_all_protocols().keys())
        self.combo = ttk.Combobox(top_frame, textvariable=self.protocol_var, values=protocols, state="readonly", width=45)
        if protocols:
            self.combo.current(0)
        self.combo.pack(side="left", padx=10, pady=10)

        ttk.Button(top_frame, text="Load Protocol", command=self._load).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Reset Tip Rack", command=self._reset_tips).pack(side="left", padx=5)

        # Timer & Status
        stat_frame = ttk.LabelFrame(self, text="Execution Status & Dynamic Timer")
        stat_frame.pack(fill="x", padx=15, pady=10)

        self.timer_label = ttk.Label(stat_frame, text="Est. Remaining: --h --m --s", font=(self.theme.font_family, self.theme.font_size_large, "bold"))
        self.timer_label.pack(side="left", padx=15, pady=15)

        self.speed_label = ttk.Label(stat_frame, text="Speed Factor: 1.00x", font=(self.theme.font_family, self.theme.font_size_normal))
        self.speed_label.pack(side="right", padx=15, pady=15)

        # Controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill="x", padx=15, pady=15)

        self.btn_run = ttk.Button(ctrl_frame, text="▶ START RUN", command=self._start_run)
        self.btn_run.pack(side="left", padx=5)

        self.btn_pause = ttk.Button(ctrl_frame, text="⏸ PAUSE", command=self._pause_run)
        self.btn_pause.pack(side="left", padx=5)

        self.btn_abort = ttk.Button(ctrl_frame, text="⏹ ABORT", command=self._abort_run)
        self.btn_abort.pack(side="left", padx=5)

    def _load(self):
        p_name = self.protocol_var.get()
        p_path = self.catalog.resolve_protocol_path(p_name)
        if p_path:
            self.active_protocol = JSONProtocolImporter.load(p_path)
            est = ProtocolPlanner.estimate_total_duration(self.active_protocol)
            self.timer_label.config(text=f"Est. Duration: {ProtocolPlanner.format_duration(est)}")

    def _reset_tips(self):
        self.engine.tip_tracker.reset_slot("Slot_4")
        messagebox.showinfo("Tip Rack Reset", "Slot 4 Tip Rack reset to A1 (0/96 used).")

    def _start_run(self):
        if not hasattr(self, "active_protocol"):
            self._load()
        if hasattr(self, "active_protocol"):
            import threading
            threading.Thread(target=self.engine.execute_protocol, args=(self.active_protocol,), daemon=True).start()

    def _pause_run(self):
        self.engine.pause()

    def _abort_run(self):
        self.engine.abort()

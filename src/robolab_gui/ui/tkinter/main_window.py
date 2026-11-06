"""Modular Tkinter Main Window assembling tabs, menus, and cleanroom themes."""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

from robolab_gui.domain.deck import DeckManager
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.configuration.machine_profiles import MachineProfileService
from robolab_gui.configuration.calibration_service import CalibrationService
from robolab_gui.protocols.catalog import ProtocolCatalog
from robolab_gui.execution.engine import ExecutionEngine
from robolab_gui.ui.tkinter.themes import THEME_STANDARD, THEME_CLEANROOM, GUITheme
from robolab_gui.ui.tkinter.tabs.deck_tab import DeckSetupTab
from robolab_gui.ui.tkinter.tabs.protocol_tab import ProtocolRunnerTab
from robolab_gui.ui.tkinter.tabs.jog_tab import JogCalibrationTab
from robolab_gui.ui.tkinter.tabs.analysis_tab import AnalysisQCTab
from robolab_gui.ui.tkinter.dialogs.station_dialog import StationSwitcherDialog

logger = logging.getLogger("RoboLab.MainWindow")


class MainWindow(tk.Tk):
    """Main application window for RoboLab GUI."""

    def __init__(
        self,
        deck_manager: DeckManager,
        session: HardwareSession,
        profile_service: MachineProfileService,
        catalog: ProtocolCatalog,
        engine: ExecutionEngine,
    ):
        super().__init__()
        self.deck_manager = deck_manager
        self.session = session
        self.profile_service = profile_service
        self.cal_service = CalibrationService(profile_service)
        self.catalog = catalog
        self.engine = engine
        self.current_theme: GUITheme = THEME_STANDARD

        self._update_title()
        self.geometry("1100x720")
        self.minsize(900, 600)

        self._build_menu()
        self._build_tabs()
        self._build_status_bar()

    def _update_title(self):
        prof = self.profile_service.active_profile
        self.title(f"RoboLab GUI v3.0 — [Station: {prof.display_name}]")

    def _build_menu(self):
        menubar = tk.Menu(self)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Change Machine Station Profile...", command=self._open_station_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Toggle Cleanroom Touch Theme", command=self._toggle_theme)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self.config(menu=menubar)

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.tab_deck = DeckSetupTab(self.notebook, self.deck_manager, self.current_theme)
        self.tab_proto = ProtocolRunnerTab(self.notebook, self.engine, self.catalog, self.current_theme)
        self.tab_jog = JogCalibrationTab(self.notebook, self.session, self.cal_service, self.current_theme)
        self.tab_analysis = AnalysisQCTab(self.notebook, self.current_theme)

        self.notebook.add(self.tab_proto, text="📋 Protocol Runner")
        self.notebook.add(self.tab_deck, text="🎛 Deck Setup")
        self.notebook.add(self.tab_jog, text="🕹 Jog & Calibration")
        self.notebook.add(self.tab_analysis, text="📊 Analysis & QC")

    def _build_status_bar(self):
        self.status_bar = ttk.Label(self, text="Ready", relief="sunken", anchor="w", padding=4)
        self.status_bar.pack(side="bottom", fill="x")

    def _open_station_dialog(self):
        StationSwitcherDialog(self, self.profile_service, on_switched_callback=lambda pid: self._update_title())

    def _toggle_theme(self):
        if self.current_theme.name == THEME_STANDARD.name:
            self.current_theme = THEME_CLEANROOM
        else:
            self.current_theme = THEME_STANDARD
        self.tab_deck.canvas.set_theme(self.current_theme)
        messagebox.showinfo("Theme Toggled", f"Switched theme to: {self.current_theme.name}")

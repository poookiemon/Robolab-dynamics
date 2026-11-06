"""Assay Analysis & Quality Control tab."""

import tkinter as tk
from tkinter import ttk
from robolab_gui.ui.tkinter.themes import GUITheme


class AnalysisQCTab(ttk.Frame):
    """Assay analysis, dose response fitting, and QC dashboard tab."""

    def __init__(self, parent, theme: GUITheme):
        super().__init__(parent)
        self.theme = theme

        ttk.Label(self, text="Assay Analysis & QC Dashboard", font=(theme.font_family, theme.font_size_large, "bold")).pack(padx=20, pady=20, anchor="w")

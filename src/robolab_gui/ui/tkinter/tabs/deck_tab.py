"""Deck Setup tab implementation."""

import tkinter as tk
from tkinter import ttk
from robolab_gui.domain.deck import DeckManager
from robolab_gui.ui.tkinter.widgets.deck_canvas import DeckCanvasWidget
from robolab_gui.ui.tkinter.themes import GUITheme


class DeckSetupTab(ttk.Frame):
    """Deck setup and visual configuration tab."""

    def __init__(self, parent, deck_manager: DeckManager, theme: GUITheme):
        super().__init__(parent)
        self.deck_manager = deck_manager
        self.theme = theme

        self.canvas = DeckCanvasWidget(self, deck_manager, theme)
        self.canvas.pack(fill="both", expand=True, padx=15, pady=15)

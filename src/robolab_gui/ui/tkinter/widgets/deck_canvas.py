"""2D deck canvas visualizer widget with animated pipettor head and fluid meniscus."""

import tkinter as tk
from typing import Optional, Dict, Tuple
from robolab_gui.domain.deck import DeckManager
from robolab_gui.ui.tkinter.themes import GUITheme, THEME_STANDARD


class DeckCanvasWidget(tk.Canvas):
    """Canvas widget that renders the 6 deck slots, mounted labware, and live carriage crosshairs."""

    def __init__(self, parent, deck_manager: DeckManager, theme: GUITheme = THEME_STANDARD, **kwargs):
        super().__init__(parent, bg=theme.bg_card, highlightthickness=1, highlightbackground=theme.border, **kwargs)
        self.deck_manager = deck_manager
        self.theme = theme
        self.head_pos: Tuple[float, float] = (0.0, 0.0)
        self.bind("<Configure>", lambda e: self.redraw())

    def update_head_position(self, x: float, y: float):
        self.head_pos = (x, y)
        self.redraw()

    def set_theme(self, theme: GUITheme):
        self.theme = theme
        self.configure(bg=theme.bg_card, highlightbackground=theme.border)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or h < 50:
            return

        # 6-Slot Grid layout (3 cols, 2 rows)
        slots = [
            ("Slot 2", 20, 20, 100, 60),
            ("Slot 4", 20, 95, 100, 80),
            ("Slot 6", 20, 190, 100, 80),
            ("Slot 1", 135, 20, 100, 60),
            ("Slot 3", 135, 95, 100, 80),
            ("Slot 5", 135, 190, 100, 80),
        ]

        for name, sx, sy, sw, sh in slots:
            slot_obj = self.deck_manager.get_slot(name)
            lw_name = slot_obj.labware.name if (slot_obj and slot_obj.labware) else "Empty"
            self.create_rectangle(sx, sy, sx + sw, sy + sh, fill="#f8f9fa" if self.theme.bg_main != "#121212" else "#2c2c2c", outline=self.theme.border, width=2)
            self.create_text(sx + sw / 2, sy + 15, text=name, font=(self.theme.font_family, self.theme.font_size_normal, "bold"), fill=self.theme.fg_text)
            self.create_text(sx + sw / 2, sy + sh / 2 + 5, text=lw_name, font=(self.theme.font_family, self.theme.font_size_normal - 2), fill=self.theme.fg_muted)

        # Pipettor Head Indicator
        hx = 20 + (self.head_pos[0] / 300.0) * 215
        hy = 20 + (self.head_pos[1] / 300.0) * 250
        self.create_oval(hx - 5, hy - 5, hx + 5, hy + 5, fill=self.theme.accent, outline="white", width=2)

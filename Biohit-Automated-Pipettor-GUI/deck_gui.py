import tkinter as tk
from tkinter import ttk, messagebox
from working import LIMSOrchestrator, Pipettor

class DeckManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LIMS Deck Configuration Manager")
        self.root.geometry("600x400")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.lims = LIMSOrchestrator(hardware=Pipettor(tip_volume=200, multichannel=True))
        self.current_profile = "deck_calibration.json"

        try:
            self.lims.load_deck_profile(self.current_profile)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find {self.current_profile}. Please ensure it is in the same directory.")
            self.on_closing()
            return

        self.setup_ui()
        self.load_slot_data()

    def on_closing(self):
        if hasattr(self, 'lims') and hasattr(self.lims.pipettor, 'close'):
            self.lims.pipettor.close()
        self.root.destroy()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        profile_lbl = ttk.Label(main_frame, text=f"Active Profile: {self.current_profile}", font=("Arial", 12, "bold"))
        profile_lbl.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        ttk.Label(main_frame, text="Select Deck Slot:").grid(row=1, column=0, sticky="w", pady=5)
        self.slot_var = tk.StringVar()
        self.slot_dropdown = ttk.Combobox(main_frame, textvariable=self.slot_var, state="readonly")
        self.slot_dropdown['values'] = list(self.lims.deck_slots.keys())
        self.slot_dropdown.grid(row=1, column=1, sticky="ew", pady=5)
        self.slot_dropdown.bind("<<ComboboxSelected>>", self.on_slot_select)

        self.entries = {}
        fields = [("X Coordinate (mm)", "x_abs"), ("Y Coordinate (mm)", "y_abs"),
                  ("Width (mm)", "width"), ("Height (mm)", "height")]

        row_idx = 2
        for label_text, key in fields:
            ttk.Label(main_frame, text=label_text).grid(row=row_idx, column=0, sticky="w", pady=5)
            entry_var = tk.StringVar()
            entry = ttk.Entry(main_frame, textvariable=entry_var)
            entry.grid(row=row_idx, column=1, sticky="ew", pady=5)

            entry_var.trace_add("write", lambda *args, k=key, v=entry_var: self.on_value_change(k, v))
            self.entries[key] = entry_var
            row_idx += 1

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=20)

        save_btn = ttk.Button(btn_frame, text="Save to Profile", command=self.save_profile)
        save_btn.pack(side=tk.LEFT, padx=5)

    def load_slot_data(self):
        if self.lims.deck_slots:
            first_slot = list(self.lims.deck_slots.keys())[0]
            self.slot_dropdown.set(first_slot)
            self.on_slot_select()

    def on_slot_select(self, event=None):
        slot_name = self.slot_var.get()
        if not slot_name: return

        slot_obj = self.lims.deck_slots[slot_name]
        self.entries["x_abs"].set(str(slot_obj.x_abs))
        self.entries["y_abs"].set(str(slot_obj.y_abs))
        self.entries["width"].set(str(slot_obj.width))
        self.entries["height"].set(str(slot_obj.height))

    def on_value_change(self, key, string_var):
        slot_name = self.slot_var.get()
        if not slot_name: return

        try:
            new_value = float(string_var.get())
            kwargs = {key: new_value}
            self.lims.update_slot_dimensions_from_ui(slot_name, **kwargs)
        except ValueError:
            pass

    def save_profile(self):
        try:
            self.lims.save_deck_profile()
            messagebox.showinfo("Success", f"Deck dimensions saved securely to {self.current_profile}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = DeckManagerGUI(root)
    root.mainloop()
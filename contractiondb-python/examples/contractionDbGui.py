import tkinter as tk
from tkinter import ttk
import json

class DBStudio:
    def __init__(self, parent_frame=None, config_path=None):
        if parent_frame:
            self.window = parent_frame
        else:
            self.window = tk.Tk()
            self.window.geometry('600x400')
            self.window.title('contractionDb')
            
        lbl = ttk.Label(self.window, text="Contraction DB Interface")
        lbl.pack(pady=10)
        
        self.table = ttk.Treeview(self.window)
        self.table.pack(expand=True, fill="both")
        
        if config_path:
            try:
                with open(config_path) as f:
                    data = json.load(f)
                    self.table.insert("", "end", text=f"Config loaded: {data.get('user', 'unknown')}")
            except Exception as e:
                self.table.insert("", "end", text=f"Error loading config: {e}")

if __name__ == "__main__":
    app = DBStudio()
    app.window.mainloop()

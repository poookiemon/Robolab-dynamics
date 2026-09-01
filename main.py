import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import threading
import os

from auto_runner import AutoRunner

class RobolabDashboard(ttk.Window):
    def __init__(self):
        # We use a beautiful modern flat theme
        super().__init__(themename="cosmo")
        self.title("Robolab Dynamics - Mission Control")
        self.geometry("700x750")
        
        self.protocol_path = tk.StringVar()
        self.data_path = tk.StringVar()
        self.db_config_path = tk.StringVar()
        
        self.build_ui()

    def build_ui(self):
        # Header Area
        header_frame = ttk.Frame(self, padding=20)
        header_frame.pack(fill=X)
        
        header = ttk.Label(header_frame, text="Robolab Dynamics Pipeline", font=("Helvetica", 24, "bold"), bootstyle="primary")
        header.pack(pady=(10, 5))
        
        subtitle = ttk.Label(header_frame, text="Hands-Free Orchestrator Dashboard", font=("Helvetica", 14), bootstyle="secondary")
        subtitle.pack()
        
        # Main Cards Area
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Step 1 Card
        card1 = ttk.Labelframe(main_frame, text=" Step 1: Pipettor Protocol JSON ", padding=15, bootstyle="info")
        card1.pack(fill=X, pady=10)
        
        row1 = ttk.Frame(card1)
        row1.pack(fill=X)
        ttk.Entry(row1, textvariable=self.protocol_path, state="readonly", font=("Helvetica", 10)).pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Button(row1, text="Browse File", command=self.browse_protocol, bootstyle="info-outline").pack(side=RIGHT)
        
        # Step 2 Card
        card2 = ttk.Labelframe(main_frame, text=" Step 2: FOC Data Target ", padding=15, bootstyle="success")
        card2.pack(fill=X, pady=10)
        
        row2 = ttk.Frame(card2)
        row2.pack(fill=X)
        ttk.Entry(row2, textvariable=self.data_path, state="readonly", font=("Helvetica", 10)).pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Button(row2, text="Browse Folder", command=self.browse_data, bootstyle="success-outline").pack(side=RIGHT)
        
        # Step 3 Card
        card3 = ttk.Labelframe(main_frame, text=" Step 3: Database Config JSON ", padding=15, bootstyle="warning")
        card3.pack(fill=X, pady=10)
        
        row3 = ttk.Frame(card3)
        row3.pack(fill=X)
        ttk.Entry(row3, textvariable=self.db_config_path, state="readonly", font=("Helvetica", 10)).pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Button(row3, text="Browse File", command=self.browse_config, bootstyle="warning-outline").pack(side=RIGHT)
        
        # Status Log Area
        status_frame = ttk.Labelframe(main_frame, text=" Live Execution Log ", padding=10, bootstyle="secondary")
        status_frame.pack(fill=BOTH, expand=YES, pady=15)
        
        self.log_text = tk.Text(status_frame, height=8, font=("Consolas", 11), state=DISABLED, bg="#f8f9fa", wrap=WORD)
        self.log_text.pack(fill=BOTH, expand=YES)
        
        # Action Area
        action_frame = ttk.Frame(self, padding=20)
        action_frame.pack(fill=X, side=BOTTOM)
        
        self.start_btn = ttk.Button(action_frame, text="🚀 START AUTOMATED RUN", style="success.TButton", padding=15, command=self.start_run)
        self.start_btn.pack(fill=X)
        
    def log(self, message):
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
        
    def browse_protocol(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if filepath:
            self.protocol_path.set(filepath)
            
    def browse_data(self):
        filepath = filedialog.askdirectory()
        if filepath:
            self.data_path.set(filepath)
            
    def browse_config(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if filepath:
            self.db_config_path.set(filepath)
            
    def start_run(self):
        if not self.protocol_path.get() or not self.data_path.get() or not self.db_config_path.get():
            messagebox.showwarning("Missing Inputs", "Please select all three required paths before starting the run.")
            return
            
        self.start_btn.config(state=DISABLED, text="⚙️ PIPELINE RUNNING...")
        self.log_text.config(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.config(state=DISABLED)
        
        self.log("--- Initializing Hands-Free Orchestrator ---")
        
        runner = AutoRunner(
            self.protocol_path.get(), 
            self.data_path.get(), 
            self.db_config_path.get(), 
            self.log
        )
        
        # We run the heavy automation script in a separate background thread 
        # so the GUI does not freeze and the log window updates beautifully in real-time.
        threading.Thread(target=self.run_thread, args=(runner,), daemon=True).start()
        
    def run_thread(self, runner):
        runner.run_pipeline()
        # Once complete, safely restore the button
        self.after(0, lambda: self.start_btn.config(state=NORMAL, text="🚀 START AUTOMATED RUN"))

if __name__ == "__main__":
    app = RobolabDashboard()
    app.mainloop()

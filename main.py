import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess

from auto_runner import AutoRunner

class RobolabDashboard(ttk.Window):
    def __init__(self):
        # We use a beautiful modern flat theme. "flatly" or "cosmo" or "yeti" are great.
        super().__init__(themename="flatly")
        self.title("Robolab Dynamics - Mission Control")
        self.geometry("750x850")
        
        self.protocol_path = tk.StringVar()
        self.data_path = tk.StringVar()
        self.db_config_path = tk.StringVar()
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.biohit_dir = os.path.join(self.base_dir, "Biohit-Automated-Pipettor-GUI")
        self.analyze_dir = os.path.join(self.base_dir, "analyze-measurement-py")
        self.contraction_dir = os.path.join(self.base_dir, "contractiondb-python")

        self.build_ui()

    def launch_app(self, app_path, cwd):
        target_file = os.path.join(cwd, app_path)
        if not os.path.exists(target_file):
            messagebox.showerror("Error", f"Could not find {app_path} in {cwd}")
            return
        try:
            cmd = [sys.executable, app_path]
            env = os.environ.copy()
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = f"{cwd}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env["PYTHONPATH"] = cwd
            subprocess.Popen(cmd, cwd=cwd, env=env)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {app_path}:\n{str(e)}")

    def build_ui(self):
        # Header Area
        header_frame = ttk.Frame(self, padding=(20, 25, 20, 10))
        header_frame.pack(fill=X)
        
        header = ttk.Label(header_frame, text="Robolab Dynamics", font=("Helvetica", 28, "bold"), bootstyle="primary")
        header.pack()
        
        subtitle = ttk.Label(header_frame, text="Unified Orchestration & Setup Studio", font=("Helvetica", 14), bootstyle="secondary")
        subtitle.pack(pady=(5, 0))
        
        # Main Cards Area
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # --- Step 1 Card ---
        card1 = ttk.Labelframe(main_frame, text=" Step 1: Liquid Handling (Biohit) ", padding=15, bootstyle="info")
        card1.pack(fill=X, pady=8)
        
        # Studio Button
        ttk.Button(card1, text="🛠️ Open Biohit Studio (Setup Labware & Protocols)", bootstyle="info",
                   command=lambda: self.launch_app("lims_master_gui.py", self.biohit_dir)).pack(fill=X, pady=(0, 10))
        
        # File Picker
        row1 = ttk.Frame(card1)
        row1.pack(fill=X)
        ttk.Label(row1, text="Protocol JSON:").pack(side=LEFT, padx=(0, 10))
        ttk.Entry(row1, textvariable=self.protocol_path, state="readonly", font=("Helvetica", 10)).pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Button(row1, text="Browse", command=self.browse_protocol, bootstyle="info-outline").pack(side=RIGHT)
        
        
        # --- Step 2 Card ---
        card2 = ttk.Labelframe(main_frame, text=" Step 2: Data Analysis & CA Curves ", padding=15, bootstyle="success")
        card2.pack(fill=X, pady=8)
        
        # Studio Button
        ttk.Button(card2, text="🛠️ Open Analysis Studio (Test Math & View Graphs)", bootstyle="success",
                   command=lambda: self.launch_app("run_gui.py", self.analyze_dir)).pack(fill=X, pady=(0, 10))
        
        # File Picker
        row2 = ttk.Frame(card2)
        row2.pack(fill=X)
        ttk.Label(row2, text="FOC Data Folder:").pack(side=LEFT, padx=(0, 10))
        ttk.Entry(row2, textvariable=self.data_path, state="readonly", font=("Helvetica", 10)).pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Button(row2, text="Browse", command=self.browse_data, bootstyle="success-outline").pack(side=RIGHT)
        
        
        # --- Step 3 Card ---
        card3 = ttk.Labelframe(main_frame, text=" Step 3: Database Archiving ", padding=15, bootstyle="warning")
        card3.pack(fill=X, pady=8)
        
        # Studio Button
        ttk.Button(card3, text="🛠️ Open DB Studio (Manage Credentials & View DB)", bootstyle="warning",
                   command=lambda: self.launch_app("examples/contractionDbGui.py", self.contraction_dir)).pack(fill=X, pady=(0, 10))
        
        # File Picker
        row3 = ttk.Frame(card3)
        row3.pack(fill=X)
        ttk.Label(row3, text="DB Config JSON:").pack(side=LEFT, padx=(0, 10))
        ttk.Entry(row3, textvariable=self.db_config_path, state="readonly", font=("Helvetica", 10)).pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Button(row3, text="Browse", command=self.browse_config, bootstyle="warning-outline").pack(side=RIGHT)
        
        
        # --- Status Log Area ---
        status_frame = ttk.Labelframe(main_frame, text=" Live Orchestrator Log ", padding=10, bootstyle="secondary")
        status_frame.pack(fill=BOTH, expand=YES, pady=15)
        
        self.log_text = tk.Text(status_frame, height=6, font=("Consolas", 11), state=DISABLED, bg="#f8f9fa", wrap=WORD)
        self.log_text.pack(fill=BOTH, expand=YES)
        
        # --- Action Area ---
        action_frame = ttk.Frame(self, padding=20)
        action_frame.pack(fill=X, side=BOTTOM)
        
        self.start_btn = ttk.Button(action_frame, text="🚀 START HANDS-FREE RUN", style="success.TButton", padding=15, command=self.start_run)
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
            messagebox.showwarning("Missing Inputs", "Please browse and select all three targets before starting the automated run.")
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
        
        # Run in background thread
        threading.Thread(target=self.run_thread, args=(runner,), daemon=True).start()
        
    def run_thread(self, runner):
        runner.run_pipeline()
        self.after(0, lambda: self.start_btn.config(state=NORMAL, text="🚀 START HANDS-FREE RUN"))

if __name__ == "__main__":
    app = RobolabDashboard()
    app.mainloop()

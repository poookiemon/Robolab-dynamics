import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess

from auto_runner import AutoRunner

# Configure modern aesthetic
ctk.set_appearance_mode("Dark")  # Sleek dark mode
ctk.set_default_color_theme("blue")  # Professional blue accents

class RobolabDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Robolab Dynamics - Mission Control")
        self.geometry("900x850")
        
        self.protocol_path = ctk.StringVar()
        self.data_path = ctk.StringVar()
        self.db_config_path = ctk.StringVar()
        
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
            
        self.log(f"--- Launching Studio: {os.path.basename(app_path)} ---")
        try:
            cmd = [sys.executable, app_path]
            env = os.environ.copy()
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = f"{cwd}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env["PYTHONPATH"] = cwd
                
            p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            def read_output():
                for line in iter(p.stdout.readline, ''):
                    if line:
                        # Schedule UI update
                        self.after(0, lambda l=line: self.log("STUDIO: " + l.strip()))
                p.stdout.close()
                self.after(0, lambda: self.log(f"--- Studio Closed ({os.path.basename(app_path)}) ---"))
                
            threading.Thread(target=read_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {app_path}:\n{str(e)}")

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header Area ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        
        header_title = ctk.CTkLabel(header_frame, text="Robolab Dynamics", font=ctk.CTkFont(family="Helvetica", size=32, weight="bold"))
        header_title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(header_frame, text="Unified Orchestration & Setup Studio", font=ctk.CTkFont(family="Helvetica", size=16), text_color="gray")
        subtitle.pack(anchor="w")

        # --- Main Cards Area ---
        main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_scroll.grid(row=1, column=0, sticky="nsew", padx=20)
        main_scroll.grid_columnconfigure(0, weight=1)

        # Function to create a beautifully styled step card
        def create_step_card(parent, step_num, title, button_text, button_cmd, entry_var, browse_cmd, color):
            card = ctk.CTkFrame(parent, corner_radius=15)
            card.grid(sticky="ew", pady=10, padx=10)
            card.grid_columnconfigure(1, weight=1)
            
            # Title
            title_lbl = ctk.CTkLabel(card, text=f"Step {step_num}: {title}", font=ctk.CTkFont(size=18, weight="bold"))
            title_lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))
            
            # Studio Button
            btn_studio = ctk.CTkButton(card, text=button_text, command=button_cmd, fg_color=color, hover_color=color, height=40, font=ctk.CTkFont(weight="bold"))
            btn_studio.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 20))
            
            # File Picker
            lbl_file = ctk.CTkLabel(card, text="Target File/Folder:", font=ctk.CTkFont(size=14))
            lbl_file.grid(row=2, column=0, sticky="w", padx=(20, 10), pady=(0, 20))
            
            entry_file = ctk.CTkEntry(card, textvariable=entry_var, state="readonly", height=35)
            entry_file.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 20))
            
            btn_browse = ctk.CTkButton(card, text="Browse", command=browse_cmd, width=100, height=35, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
            btn_browse.grid(row=2, column=2, sticky="e", padx=(0, 20), pady=(0, 20))
            
            return card

        # Step 1
        create_step_card(main_scroll, "1", "Liquid Handling (Biohit)", "🛠️ Open Biohit Studio", 
                         lambda: self.launch_app("lims_master_gui.py", self.biohit_dir),
                         self.protocol_path, self.browse_protocol, "#2A729E")
        
        # Step 2
        create_step_card(main_scroll, "2", "Data Analysis & CA Curves", "🛠️ Open Analysis Studio", 
                         lambda: self.launch_app("run_gui.py", self.analyze_dir),
                         self.data_path, self.browse_data, "#2B8C67")
        
        # Step 3
        create_step_card(main_scroll, "3", "Database Archiving", "🛠️ Open DB Studio", 
                         lambda: self.launch_app("examples/contractionDbGui.py", self.contraction_dir),
                         self.db_config_path, self.browse_config, "#9C6E26")

        # --- Status Log Area ---
        log_frame = ctk.CTkFrame(main_scroll, corner_radius=15)
        log_frame.grid(sticky="ew", pady=10, padx=10)
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_lbl = ctk.CTkLabel(log_frame, text="Live Orchestrator Log", font=ctk.CTkFont(size=16, weight="bold"))
        log_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        self.log_text = ctk.CTkTextbox(log_frame, height=150, font=ctk.CTkFont(family="Consolas", size=12), state="disabled", fg_color="#1E1E1E")
        self.log_text.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        # --- Action Area ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=20)
        action_frame.grid_columnconfigure(0, weight=1)
        
        self.start_btn = ctk.CTkButton(action_frame, text="🚀 START HANDS-FREE RUN", height=60, 
                                       font=ctk.CTkFont(size=18, weight="bold"), fg_color="#2B8C67", hover_color="#20684C",
                                       command=self.start_run)
        self.start_btn.grid(row=0, column=0, sticky="ew")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

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
            messagebox.showwarning("Missing Inputs", "Please browse and select all three targets before starting.")
            return
            
        self.start_btn.configure(state="disabled", text="⚙️ PIPELINE RUNNING...")
        self.log_text.configure(state="normal")
        self.log_text.delete("0.0", "end")
        self.log_text.configure(state="disabled")
        
        self.log("--- Initializing Hands-Free Orchestrator ---")
        
        runner = AutoRunner(
            self.protocol_path.get(), 
            self.data_path.get(), 
            self.db_config_path.get(), 
            self.log
        )
        
        threading.Thread(target=self.run_thread, args=(runner,), daemon=True).start()
        
    def run_thread(self, runner):
        runner.run_pipeline()
        self.after(0, lambda: self.start_btn.configure(state="normal", text="🚀 START HANDS-FREE RUN"))

if __name__ == "__main__":
    app = RobolabDashboard()
    app.mainloop()

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess

from auto_runner import AutoRunner

# Force the bright, light "ReportGen" aesthetic
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue") 

# Autumn Palette
BG_COLOR = "#FFF8F0"        # Warm cream background
CARD_COLOR = "#FFFFFF"      # Crisp white cards
TEXT_COLOR = "#432818"      # Deep espresso brown for text
ACCENT_PINK = "#D95D39"     # Burnt Orange / Rustic Red
ACCENT_PURPLE = "#E07A5F"   # Terracotta
ACCENT_BLUE = "#D4A373"     # Warm Sand / Golden Yellow
START_BTN_COLOR = "#9E2A2B" # Deep Autumn Red
START_BTN_HOVER = "#540B0E" # Darker Crimson

class RobolabDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Robolab Dynamics - Mission Control")
        self.geometry("900x850")
        self.configure(fg_color=BG_COLOR)
        
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
                    if line: self.after(0, lambda l=line: self.log("STUDIO: " + l.strip()))
                p.stdout.close()
                self.after(0, lambda: self.log(f"--- Studio Closed ({os.path.basename(app_path)}) ---"))
                
            threading.Thread(target=read_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {app_path}:\n{str(e)}")

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # The tabs get the expanding space
        self.grid_rowconfigure(2, weight=0) # Log stays fixed size
        self.grid_rowconfigure(3, weight=0) # Button stays fixed size

        # --- Header Area ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        
        header_title = ctk.CTkLabel(header_frame, text="Robolab Dynamics", text_color=START_BTN_COLOR, font=ctk.CTkFont(family="Helvetica", size=36, weight="bold"))
        header_title.pack()

        # --- Tabs Area ---
        tabview = ctk.CTkTabview(self, fg_color=CARD_COLOR, segmented_button_fg_color="#F1F5F9", segmented_button_selected_color=START_BTN_COLOR, segmented_button_selected_hover_color=START_BTN_HOVER, corner_radius=15)
        tabview.grid(row=1, column=0, sticky="nsew", padx=40, pady=10)
        
        tab_1 = tabview.add("1. Liquid Handling")
        tab_2 = tabview.add("2. Data Analysis")
        tab_3 = tabview.add("3. Database")

        # Function to build content inside a tab
        def build_tab(parent_tab, title, button_text, button_cmd, entry_var, browse_cmd, color):
            parent_tab.grid_columnconfigure(1, weight=1)
            
            title_lbl = ctk.CTkLabel(parent_tab, text=title, text_color=color, font=ctk.CTkFont(size=24, weight="bold"))
            title_lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(30, 20))
            
            # Studio Button
            btn_studio = ctk.CTkButton(parent_tab, text=button_text, command=button_cmd, fg_color=color, hover_color=color, text_color="white", corner_radius=12, height=55, font=ctk.CTkFont(size=16, weight="bold"))
            btn_studio.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 40))
            
            # File Picker
            lbl_file = ctk.CTkLabel(parent_tab, text="Target file or folder:", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR)
            lbl_file.grid(row=2, column=0, sticky="w", padx=(20, 10), pady=(0, 20))
            
            entry_file = ctk.CTkEntry(parent_tab, textvariable=entry_var, state="readonly", height=45, fg_color="#F8FAFC", text_color="#334155", border_color="#E2E8F0", corner_radius=12)
            entry_file.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 20))
            
            btn_browse = ctk.CTkButton(parent_tab, text="Browse", command=browse_cmd, width=120, height=45, fg_color="transparent", border_width=2, border_color=color, text_color=color, corner_radius=12, font=ctk.CTkFont(weight="bold"))
            btn_browse.grid(row=2, column=2, sticky="e", padx=(0, 20), pady=(0, 20))

        # Populate Tabs
        build_tab(tab_1, "Liquid handling setup", "Open Biohit studio", 
                  lambda: self.launch_app("lims_master_gui.py", self.biohit_dir),
                  self.protocol_path, self.browse_protocol, ACCENT_PINK)
                  
        build_tab(tab_2, "Data analysis setup", "Open analysis studio", 
                  lambda: self.launch_app("run_gui.py", self.analyze_dir),
                  self.data_path, self.browse_data, ACCENT_PURPLE)
                  
        build_tab(tab_3, "Database archiving setup", "Open DB studio", 
                  lambda: self.launch_app("examples/contractionDbGui.py", self.contraction_dir),
                  self.db_config_path, self.browse_config, ACCENT_BLUE)

        # --- Status Log Area ---
        log_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=15, border_width=2, border_color="#F1F5F9")
        log_frame.grid(row=2, column=0, sticky="ew", padx=40, pady=10)
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_lbl = ctk.CTkLabel(log_frame, text="Live orchestrator log", text_color="#475569", font=ctk.CTkFont(size=16, weight="bold"))
        log_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        self.log_text = ctk.CTkTextbox(log_frame, height=120, font=ctk.CTkFont(family="Consolas", size=13), state="disabled", fg_color="#F8FAFC", text_color="#10B981", corner_radius=12, border_width=1, border_color="#E2E8F0")
        self.log_text.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        # --- Action Area ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", padx=40, pady=(10, 30))
        action_frame.grid_columnconfigure(0, weight=1)
        
        self.start_btn = ctk.CTkButton(action_frame, text="Start automated run", height=65, 
                                       font=ctk.CTkFont(size=20, weight="bold"), fg_color=START_BTN_COLOR, hover_color=START_BTN_HOVER, corner_radius=20,
                                       command=self.start_run)
        self.start_btn.grid(row=0, column=0, sticky="ew")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def browse_protocol(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if filepath: self.protocol_path.set(filepath)
            
    def browse_data(self):
        filepath = filedialog.askdirectory()
        if filepath: self.data_path.set(filepath)
            
    def browse_config(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if filepath: self.db_config_path.set(filepath)
            
    def start_run(self):
        if not self.protocol_path.get() or not self.data_path.get() or not self.db_config_path.get():
            messagebox.showwarning("Missing inputs", "Please browse and select all three targets before starting.")
            return
            
        self.start_btn.configure(state="disabled", text="Pipeline running...")
        self.log_text.configure(state="normal")
        self.log_text.delete("0.0", "end")
        self.log_text.configure(state="disabled")
        
        self.log("--- Initializing hands-free orchestrator ---")
        
        runner = AutoRunner(
            self.protocol_path.get(), 
            self.data_path.get(), 
            self.db_config_path.get(), 
            self.log
        )
        
        threading.Thread(target=self.run_thread, args=(runner,), daemon=True).start()
        
    def run_thread(self, runner):
        runner.run_pipeline()
        self.after(0, lambda: self.start_btn.configure(state="normal", text="Start automated run"))

if __name__ == "__main__":
    app = RobolabDashboard()
    app.mainloop()

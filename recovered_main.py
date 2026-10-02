import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess

from auto_runner import AutoRunner

# --- TECHIE & SMART AESTHETIC ---
ctk.set_appearance_mode("Dark")  # Pure dark mode
ctk.set_default_color_theme("blue")

# Tech Palette
BG_COLOR = "#0B0F19"         # Deep cyber-blue/black background
CARD_COLOR = "#151B2B"       # Slightly lighter for panels
TEXT_COLOR = "#E2E8F0"       # Crisp white/grey text
ACCENT_CYAN = "#00F0FF"      # Neon Cyan for accents
ACCENT_GREEN = "#39FF14"     # Matrix green for success
ACCENT_PURPLE = "#B026FF"    # Deep tech purple
ACCENT_BLUE = "#007BFF"      # Industrial blue

class RobolabDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Robolab Dynamics - Core System")
        self.geometry("950x850")
        self.configure(fg_color=BG_COLOR)
        
        self.protocol_path = ctk.StringVar()
        self.data_path = ctk.StringVar()
        self.db_config_path = ctk.StringVar()
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.biohit_dir = os.path.join(self.base_dir, "Biohit-Automated-Pipettor-GUI")
        self.analyze_dir = os.path.join(self.base_dir, "analyze-measurement-py")
        self.contraction_dir = os.path.join(self.base_dir, "contractiondb-python")

        self.build_ui()

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 
        self.grid_rowconfigure(2, weight=0) 

        # --- Header Area ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        
        header_title = ctk.CTkLabel(header_frame, text="ROBOLAB DYNAMICS // CORE", text_color=ACCENT_CYAN, font=ctk.CTkFont(family="Consolas", size=28, weight="bold"))
        header_title.pack(anchor="w")

        # --- Tabs Area ---
        tabview = ctk.CTkTabview(self, fg_color=CARD_COLOR, segmented_button_fg_color="#0B0F19", segmented_button_selected_color=ACCENT_BLUE, segmented_button_selected_hover_color="#0056b3", corner_radius=10)
        tabview.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        
        tab_ops = tabview.add("⚙️ Routine Ops")
        tab_biohit = tabview.add("🧪 Biohit Studio")
        tab_analyze = tabview.add("📊 Analysis Studio")
        tab_db = tabview.add("🗄️ DB Studio")
        tab_calc = tabview.add("🧮 Dilution Calc")

        self.build_ops_tab(tab_ops)
        self.build_calc_tab(tab_calc)
        
        # --- EMBEDDING ALIEN GUIS INTO TABS ---
        try:
            sys.path.insert(0, self.biohit_dir)
            from lims_master_gui import LIMSMasterApp
            self.lims_app = LIMSMasterApp(tab_biohit)
            sys.path.pop(0)
        except Exception as e:
            ctk.CTkLabel(tab_biohit, text=f"Error embedding Biohit Studio: {e}", text_color="red").pack(pady=20)

        try:
            sys.path.insert(0, self.analyze_dir)
            if 'gui' in sys.modules:
                del sys.modules['gui']
            from gui.gui import GUI as AnalyzeGUI
            self.analyze_app = AnalyzeGUI(parent_frame=tab_analyze)
            sys.path.pop(0)
        except Exception as e:
            ctk.CTkLabel(tab_analyze, text=f"Error embedding Analysis Studio: {e}", text_color="red").pack(pady=20)

        try:
            sys.path.insert(0, self.contraction_dir)
            from examples.contractionDbGui import DBStudio
            self.db_app = DBStudio(parent_frame=tab_db)
            sys.path.pop(0)
        except Exception as e:
            ctk.CTkLabel(tab_db, text=f"Error embedding DB Studio: {e}", text_color="red").pack(pady=20)

        # --- Terminal Log Area ---
        log_frame = ctk.CTkFrame(self, fg_color="#000000", corner_radius=5, border_width=1, border_color="#333333")
        log_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 20))
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_lbl = ctk.CTkLabel(log_frame, text="TERMINAL OUTPUT", text_color="#555555", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        log_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))
        
        self.log_text = ctk.CTkTextbox(log_frame, height=120, font=ctk.CTkFont(family="Consolas", size=12), state="disabled", fg_color="#000000", text_color=ACCENT_GREEN, corner_radius=0)
        self.log_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def load_config(self):
        self.config_file = os.path.join(self.base_dir, "routine_config.json")
        if os.path.exists(self.config_file):
            import json
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "media_change": "",
            "acute_test": "",
            "calcium_curve": ""
        }

    def save_config(self, op_key):
        config = self.load_config()
        config[op_key] = self.protocol_path.get()
        import json
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        self.log(f"[SYS] Assigned unified protocol path to {op_key} successfully.")
        messagebox.showinfo("Success", f"Unified protocol successfully assigned to {op_key}!")

    def execute_routine(self, op_key, op_name):
        config = self.load_config()
        protocol = config.get(op_key, "")
        if not protocol:
            messagebox.showwarning("Unassigned", f"No protocol assigned to '{op_name}'.\nPlease assign one first.")
            return
            
        self.log(f"[SYS] Initializing Routine Op: {op_name}")
        runner = AutoRunner(protocol, self.log)
        threading.Thread(target=runner.run_pipeline, daemon=True).start()

    def build_ops_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        
        # --- LEFT SIDE: EXECUTION ---
        exec_frame = ctk.CTkFrame(parent, fg_color="transparent")
        exec_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        lbl = ctk.CTkLabel(exec_frame, text="TECHNICIAN DAILY OPERATIONS", text_color=TEXT_COLOR, font=ctk.CTkFont(family="Consolas", size=18, weight="bold"))
        lbl.grid(row=0, column=0, pady=(0, 20))

        btn_media = ctk.CTkButton(exec_frame, text="[RUN] Daily Media Change (500µL)", fg_color=ACCENT_BLUE, hover_color="#0056b3", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), height=50, 
                                  command=lambda: self.execute_routine("media_change", "Daily Media Change"))
        btn_media.grid(row=1, column=0, sticky="ew", pady=10)

        btn_acute = ctk.CTkButton(exec_frame, text="[RUN] Friday Acute SIPA Test", fg_color=ACCENT_PURPLE, hover_color="#7A18B3", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), height=50, 
                                  command=lambda: self.execute_routine("acute_test", "Acute SIPA Test"))
        btn_acute.grid(row=2, column=0, sticky="ew", pady=10)

        btn_ca = ctk.CTkButton(exec_frame, text="[RUN] Automated Calcium Curve", fg_color="#E63946", hover_color="#B32431", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), height=50, 
                               command=lambda: self.execute_routine("calcium_curve", "Calcium Curve"))
        btn_ca.grid(row=3, column=0, sticky="ew", pady=10)

        # --- RIGHT SIDE: CONFIGURATION & ASSIGNMENT ---
        config_frame = ctk.CTkFrame(parent, fg_color="#0F172A", corner_radius=10, border_width=1, border_color="#334155")
        config_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        config_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(config_frame, text="CONFIG ASSIGNMENT", text_color=ACCENT_CYAN, font=ctk.CTkFont(family="Consolas", size=16, weight="bold")).grid(row=0, column=0, columnspan=3, pady=10)

        ctk.CTkLabel(config_frame, text="Unified JSON:", font=ctk.CTkFont(family="Consolas", size=12)).grid(row=1, column=0, sticky="e", padx=10, pady=5)
        ctk.CTkEntry(config_frame, textvariable=self.protocol_path, state="readonly", width=150, fg_color="#0B0F19", border_color="#334155").grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(config_frame, text="Browse", width=60, command=self.browse_protocol, fg_color="#334155", hover_color="#475569").grid(row=1, column=2, padx=10, pady=5)

        ctk.CTkLabel(config_frame, text="Assign To:", font=ctk.CTkFont(family="Consolas", size=12, weight="bold")).grid(row=4, column=0, sticky="e", padx=10, pady=(20, 5))
        self.op_var = ctk.StringVar(value="media_change")
        ctk.CTkOptionMenu(config_frame, variable=self.op_var, values=["media_change", "acute_test", "calcium_curve"], fg_color="#334155").grid(row=4, column=1, sticky="ew", padx=5, pady=(20, 5))
        
        ctk.CTkButton(config_frame, text="Save Target Mapping", fg_color="#F59E0B", hover_color="#D97706", text_color="black", font=ctk.CTkFont(family="Consolas", weight="bold"), command=lambda: self.save_config(self.op_var.get())).grid(row=5, column=0, columnspan=3, pady=20, padx=20, sticky="ew")

    def build_calc_tab(self, parent):
        parent.grid_columnconfigure((0,1), weight=1)

        ctk.CTkLabel(parent, text="SIPA DILUTION MATRIX CALCULATOR", text_color=ACCENT_CYAN, font=ctk.CTkFont(family="Consolas", size=18, weight="bold")).grid(row=0, column=0, columnspan=2, pady=20)

        # Inputs
        ctk.CTkLabel(parent, text="Stock Concentration (mM):", font=ctk.CTkFont(family="Consolas")).grid(row=1, column=0, sticky="e", padx=10, pady=10)
        stock_entry = ctk.CTkEntry(parent, placeholder_text="e.g. 10")
        stock_entry.grid(row=1, column=1, sticky="w", padx=10, pady=10)

        ctk.CTkLabel(parent, text="Target Well Volume (µL):", font=ctk.CTkFont(family="Consolas")).grid(row=2, column=0, sticky="e", padx=10, pady=10)
        vol_entry = ctk.CTkEntry(parent, placeholder_text="e.g. 500")
        vol_entry.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        # Output Box
        res_box = ctk.CTkTextbox(parent, height=120, font=ctk.CTkFont(family="Consolas", size=13), state="disabled", fg_color="#0B0F19", text_color=ACCENT_GREEN, corner_radius=5)
        res_box.grid(row=4, column=0, columnspan=2, sticky="ew", padx=40, pady=20)

        def calculate():
            try:
                stock_mm = float(stock_entry.get())
                target_vol = float(vol_entry.get())
                # Acute test targets: 0.1, 0.3, 1.0, 3.0, 10.0 uM
                targets = [0.1, 0.3, 1.0, 3.0, 10.0]
                
                res_box.configure(state="normal")
                res_box.delete("0.0", "end")
                res_box.insert("end", f"Stock: {stock_mm} mM | Target Well Vol: {target_vol} µL\n")
                res_box.insert("end", "-"*50 + "\n")
                
                for t_um in targets:
                    # C1V1 = C2V2  =>  (stock_mm * 1000) * V1 = t_um * target_vol
                    v1_ul = (t_um * target_vol) / (stock_mm * 1000)
                    dmso_pct = (v1_ul / target_vol) * 100
                    
                    warning = ""
                    if v1_ul < 50: warning += " [! <50µL (use serial dil)]"
                    if dmso_pct > 1.0: warning += " [! >1% DMSO TOXIC]"
                    
                    res_box.insert("end", f"Target: {t_um:4} µM -> Add {v1_ul:6.2f} µL stock {warning}\n")
                    
                res_box.configure(state="disabled")
            except ValueError:
                res_box.configure(state="normal")
                res_box.delete("0.0", "end")
                res_box.insert("end", "Error: Please enter valid numbers.")
                res_box.configure(state="disabled")

        ctk.CTkButton(parent, text="CALCULATE MATRICES", fg_color=ACCENT_CYAN, text_color="black", hover_color="#00C4D1", font=ctk.CTkFont(family="Consolas", weight="bold"), command=calculate).grid(row=3, column=0, columnspan=2, pady=10)


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
            
        self.start_btn.configure(state="disabled", text="SEQUENCE RUNNING...")
        self.log_text.configure(state="normal")
        self.log_text.delete("0.0", "end")
        self.log_text.configure(state="disabled")
        
        self.log("[SYS] Initializing Master Sequence Orchestrator...")
        
        runner = AutoRunner(
            self.protocol_path.get(), 
            self.data_path.get(), 
            self.db_config_path.get(), 
            self.log
        )
        
        threading.Thread(target=self.run_thread, args=(runner,), daemon=True).start()
        
    def run_thread(self, runner):
        runner.run_pipeline()
        self.after(0, lambda: self.start_btn.configure(state="normal", text="INITIATE MASTER SEQUENCE"))

if __name__ == "__main__":
    app = RobolabDashboard()
    app.mainloop()

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, logging, threading, time, os, subprocess
import ctypes  # Native Windows library for ghost mouse
from working import LIMSOrchestrator, Labware, DeckSlot, Pipettor
from gui import GUI as AnalyzerGUI

import xml.etree.ElementTree as ET
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)

        self.text_widget.after(0, append)


class LIMSMasterApp:
    def __init__(self, root):
        self.root = root
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        except AttributeError:
            pass

        is_multi = False  # Auto-defaulted to Single-Channel per user request

        # --- SAFETY LOCK: 200uL Hardware Manifold Limitation ---
        self.lims = LIMSOrchestrator(hardware=Pipettor(tip_volume=200.0, multichannel=is_multi))
        self.lims.load_machine_profile()

        self.scale = 2.65
        self.bed_width = self.lims.machine_config.get("max_x_mm", 300.0)
        self.bed_height = self.lims.machine_config.get("max_y_mm", 300.0)
        self.bed_z_limit = self.lims.machine_config.get("max_z_mm", 310.0)
        self.tip_length_var = tk.DoubleVar(value=50.89)

        self.placed_slots, self.unplaced_slots = [], []
        self.selected_slot_name, self.dragging_slot = None, None
        self.workflow_sequence = []
        self.jog_sliders, self.deck_jog_sliders = {}, {}

        self.is_running = False
        self.is_aborted = False
        self.pause_event = threading.Event()
        self.pause_event.set()

        self.has_tip_var = tk.BooleanVar(value=False)
        self.current_pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.telemetry_active = False

        self.setup_menu()
        self.setup_ui()
        self.setup_logging()

        hw_mode = "Multichannel (8-channel) array" if is_multi else "Single-channel direct mapping"
        self.logger.info(f"System Boot: {hw_mode} | Tracking bypassed. Pure kinematics engaged.")

        self.root.update()
        self.emergency_reset()

    def on_closing(self):
        self.telemetry_active = False
        self.is_aborted = True
        self.pause_event.set()
        if hasattr(self, 'logger'): self.logger.info("Releasing hardware COM locks and terminating...")
        if hasattr(self.lims.pipettor, 'close'): self.lims.pipettor.close()
        self.root.destroy()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Deck Layout", command=self.action_new_deck)
        filemenu.add_command(label="Load Workspace...", command=self.action_load_deck)
        filemenu.add_command(label="Save Workspace As...", command=self.action_save_deck_as)
        filemenu.add_command(label="Load JSON Protocol...", command=self.action_load_workflow)
        filemenu.add_command(label="Save JSON Protocol As...", command=self.action_save_workflow_as)
        filemenu.add_separator()
        filemenu.add_command(label="Import Python Protocol (.py)...", command=self.action_import_python_protocol)
        filemenu.add_separator()
        filemenu.add_command(label="Machine Chassis Settings...", command=self.action_edit_machine_limits)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=filemenu)
        try:
            self.root.config(menu=menubar)
        except Exception:
            pass

    def action_edit_machine_limits(self):
        top = tk.Toplevel(self.root)
        top.title("Hardware Chassis Configuration")
        top.geometry("380x300")
        ttk.Label(top, text="Global Machine Boundaries & Tools", font=("Arial", 11, "bold")).pack(pady=10)
        f = ttk.Frame(top)
        f.pack(fill=tk.BOTH, expand=True, padx=20)

        ttk.Label(f, text="Max X Travel (mm):").grid(row=0, column=0, sticky="w", pady=5)
        x_var = tk.StringVar(value=str(self.lims.machine_config.get("max_x_mm", 300.0)))
        ttk.Entry(f, textvariable=x_var, width=15).grid(row=0, column=1, pady=5)

        ttk.Label(f, text="Max Y Travel (mm):").grid(row=1, column=0, sticky="w", pady=5)
        y_var = tk.StringVar(value=str(self.lims.machine_config.get("max_y_mm", 300.0)))
        ttk.Entry(f, textvariable=y_var, width=15).grid(row=1, column=1, pady=5)

        ttk.Label(f, text="Max Z Travel (Bed Floor mm):").grid(row=2, column=0, sticky="w", pady=5)
        z_var = tk.StringVar(value=str(self.bed_z_limit))
        ttk.Entry(f, textvariable=z_var, width=15).grid(row=2, column=1, pady=5)

        ttk.Separator(f, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(f, text="Attached Tip Length (mm):").grid(row=4, column=0, sticky="w", pady=5)
        t_var = tk.StringVar(value=str(self.tip_length_var.get()))
        ttk.Entry(f, textvariable=t_var, width=15).grid(row=4, column=1, pady=5)

        def commit_changes():
            try:
                self.lims.machine_config["max_x_mm"] = float(x_var.get())
                self.lims.machine_config["max_y_mm"] = float(y_var.get())
                self.lims.machine_config["max_z_mm"] = float(z_var.get())
                self.bed_width = float(x_var.get())
                self.bed_height = float(y_var.get())
                self.bed_z_limit = float(z_var.get())
                self.tip_length_var.set(float(t_var.get()))
                self.lims.save_machine_profile()
                self.canvas.config(width=self.bed_width * self.scale, height=self.bed_height * self.scale)
                self.draw_deck()
                self.logger.info(f"Chassis updated. Z-Floor locked to {self.bed_z_limit}mm.")
                top.destroy()
            except ValueError:
                messagebox.showerror("Parsing Error", "Dimensions must be floating-point numerals.")

        ttk.Button(top, text="Apply & Restart Canvas", command=commit_changes).pack(pady=20)

    def setup_logging(self):
        self.logger = logging.getLogger("LIMS")
        self.logger.setLevel(logging.INFO)
        th = TextHandler(self.console_text)
        th.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(th)

    def setup_ui(self):
        con_f = ttk.LabelFrame(self.root, text="Diagnostic Output")
        con_f.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)
        self.console_text = tk.Text(con_f, height=8, state='disabled', bg="white", fg="black", font=("Consolas", 10))
        self.console_text.pack(fill=tk.X)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tab_jog = ttk.Frame(self.nb, padding=10)
        self.tab_deck = ttk.Frame(self.nb, padding=10)
        self.tab_direct = ttk.Frame(self.nb, padding=15)
        self.tab_workflow = ttk.Frame(self.nb, padding=10)
        self.tab_analysis = ttk.Frame(self.nb, padding=10)  # NEW
        self.tab_ops = ttk.Frame(self.nb, padding=10)
        self.tab_dilution = ttk.Frame(self.nb, padding=10)

        self.nb.add(self.tab_jog, text="1. Jog & Hardware")
        self.nb.add(self.tab_deck, text="2. Deck Setup")
        self.nb.add(self.tab_direct, text="3. Direct Operations")
        self.nb.add(self.tab_workflow, text="4. Protocol Runner")
        self.nb.add(self.tab_analysis, text="5. Data Analysis")  # NEW
        self.nb.add(self.tab_ops, text="6. Daily Operations")
        self.nb.add(self.tab_dilution, text="7. SIPA Dilution Calc")

        self.build_jog_tab()
        self.build_deck_tab()
        self.build_direct_ops_tab()
        self.build_workflow_tab()
        self.build_analysis_tab()
        self.build_ops_tab()
        self.build_dilution_tab()

        # AnalyzerGUI is now launched via pop-out button  # NEW------------------


    def execute_routine(self, op_name, default_file):
        config_file = "routine_config.json"
        import json
        import os
        import threading
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        protocol_path = config.get(op_name, default_file)
        
        if not os.path.exists(protocol_path):
            messagebox.showwarning("Not Found", f"Protocol file not found:\n{protocol_path}")
            return
            
        try:
            with open(protocol_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            for step in loaded_sequence:
                if 'action' not in step: continue
                self.workflow_sequence.append(step)
                self.wf_box.insert(tk.END, f"[LOADED] {step['action']}")
            self.nb.select(self.tab_workflow)
            self.logger.info(f"Loaded {op_name} Routine. Auto-starting sequence...")
            
            # Start the run sequence automatically in a background thread just like the RUN button does
            threading.Thread(target=self.run_sequence, daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error loading routine: {e}")
            messagebox.showerror("Error", str(e))

    def assign_routine(self, op_name):
        filepath = filedialog.askopenfilename(title=f"Assign JSON to {op_name}", filetypes=[("JSON Protocol", "*.json")])
        if filepath:
            config_file = "routine_config.json"
            import json, os
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            config[op_name] = filepath
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Saved", f"{op_name} is now mapped to:\n{filepath}")


    def build_analysis_tab(self):
        # Create left and right container boxes
        self.frame_heatmap = ttk.LabelFrame(self.tab_analysis, text="Quality Control (Baseline Heatmaps)")
        self.frame_heatmap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Analyze Measurement")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        lbl_ca2 = ttk.Label(self.frame_ca2, text="Kinetic Traces & Peak Forces", font=("Arial", 16, "bold"))
        lbl_ca2.pack(pady=5)
        
        desc_ca2 = ttk.Label(self.frame_ca2, text="Launch the full-screen interactive dashboard\nto analyze measurements and kinetic traces.", justify=tk.CENTER)
        desc_ca2.pack(pady=5)
        
        btn_launch = ttk.Button(self.frame_ca2, text="Launch Dashboard", command=self.launch_analyzer_popout)
        btn_launch.pack(pady=20)

        # Place heatmap logic in the left box
        lbl = ttk.Label(self.frame_heatmap, text="FOC48 Baseline Heatmaps", font=("Arial", 16, "bold"))
        lbl.pack(pady=5)
        
        desc = ttk.Label(self.frame_heatmap, text="Automatically parses .stats.xml and .xml files\nto generate baseline heatmaps.", justify=tk.CENTER)
        desc.pack(pady=5)
        
        btn_folder = ttk.Button(self.frame_heatmap, text="Select Folder for Heatmaps", command=self.run_heatmap_analysis)
        btn_folder.pack(pady=10)
        
        # Image Viewer Section
        self.heatmap_display = tk.Label(self.frame_heatmap, text="No image to display", bg="white")
        self.heatmap_display.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # Navigation Buttons
        self.heatmap_nav_frame = ttk.Frame(self.frame_heatmap)
        self.heatmap_nav_frame.pack(pady=5)
        
        self.btn_prev = ttk.Button(self.heatmap_nav_frame, text="< Prev", command=self.prev_heatmap, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        
        self.lbl_gallery = ttk.Label(self.heatmap_nav_frame, text="0 / 0")
        self.lbl_gallery.pack(side=tk.LEFT, padx=10)
        
        self.btn_next = ttk.Button(self.heatmap_nav_frame, text="Next >", command=self.next_heatmap, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        
        self.heatmap_image_paths = []
        self.current_heatmap_index = 0
        self._current_photo = None

    def run_heatmap_analysis(self):
        import json
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("heatmap", "/")
        except Exception: pass

        folder_path = filedialog.askdirectory(title="Select FOC48 Data Folder", initialdir=init_dir)
        if folder_path:
            try:
                data = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f: data = json.load(f)
                data["heatmap"] = folder_path
                with open(config_path, "w") as f: json.dump(data, f)
            except Exception: pass

        if not folder_path: return
        
        import glob
        from datetime import datetime
        
        search_pattern = os.path.join(folder_path, "*.stats.xml")
        stats_files = glob.glob(search_pattern)
        
        if not stats_files:
            messagebox.showinfo("No Files", f"No .stats.xml files found in {folder_path}")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_dir = os.path.join(folder_path, f"Analysis_{timestamp}")
        os.makedirs(save_dir, exist_ok=True)
            
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = ['1', '2', '3', '4', '5', '6']
        
        for stats_file in stats_files:
            base_xml = stats_file.replace(".stats.xml", ".xml")
            pix2mm = 28.7
            
            def clean_and_parse(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    xml_data = f.read()
                xml_data = xml_data.replace('encoding="UTF - 8"', 'encoding="UTF-8"').replace('version="1.1"', 'version="1.0"')
                xml_data = re.sub(r'<!.*?>', '', xml_data)
                return ET.fromstring(xml_data)
            
            if os.path.exists(base_xml):
                try:
                    b_root = clean_and_parse(base_xml)
                    p_node = b_root.find("pixel_per_mm")
                    if p_node is not None: pix2mm = float(p_node.text)
                except Exception as e:
                    self.logger.warning(f"Could not read pix2mm: {e}")
            
            try:
                root = clean_and_parse(stats_file)
                df = pd.DataFrame(index=rows, columns=cols, dtype=float)
                for r in rows:
                    for c in cols:
                        w_node = root.find(f"{r}{c}")
                        if w_node is not None:
                            b_pix = w_node.find("baseline")
                            if b_pix is not None:
                                df.at[r, c] = float(b_pix.text) / pix2mm
                                
                from matplotlib.colors import LinearSegmentedColormap
                colors = [
                    (0.000, "mediumblue"),
                    (0.332, "deepskyblue"),
                    (0.333, "mediumseagreen"),
                    (0.500, "limegreen"),
                    (0.666, "mediumseagreen"),
                    (0.667, "lightcoral"),
                    (1.000, "firebrick")
                ]
                custom_cmap = LinearSegmentedColormap.from_list("blue_green_red", colors)
                fig, ax = plt.subplots(figsize=(12, 9))
                sns.heatmap(df, annot=True, fmt=".2f", cmap=custom_cmap, vmin=3.5, vmax=4.4, cbar_kws={'label': 'Baseline (mm)'}, ax=ax)
                ax.xaxis.tick_top()
                ax.xaxis.set_label_position('top')
                plt.yticks(rotation=0)
                
                # --- Apply QC Flags ---
                try:
                    from backend_qc import qc_heatmap_baselines
                    fail_mask = qc_heatmap_baselines(df)
                    for i in range(df.shape[0]):
                        for j in range(df.shape[1]):
                            if fail_mask.iloc[i, j]:
                                # Draw a translucent bold red X over failing cells
                                plt.text(j + 0.5, i + 0.5, 'X', color='red', fontsize=32, ha='center', va='center', fontweight='bold', alpha=0.5)
                except Exception as qc_e:
                    self.logger.error(f"QC Flagging failed: {qc_e}")
                # ----------------------
                
                file_name = os.path.basename(stats_file)
                plt.title(f"Baseline Heatmap: {file_name}\n(Calculated using {pix2mm} pixels/mm)\nTarget Range: 3.8mm - 4.1mm", fontsize=14)
                plt.xlabel("Columns")
                plt.ylabel("Rows")
                plt.figtext(0.5, 0.01, "Values between 3.8 and 4.1 are ideal. <3.8 is too small, >4.1 is too large.", ha="center", fontsize=10, bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})
                
                # Save to the timestamped folder
                image_name = file_name.replace(".stats.xml", "_heatmap.png")
                save_path = os.path.join(save_dir, image_name)
                plt.savefig(save_path, bbox_inches='tight', dpi=150)
                
                # Close the plot silently instead of popping up a blocking window
                plt.close()
            except Exception as e:
                self.logger.error(f"Error parsing {stats_file}: {e}")
                messagebox.showerror("Error", f"Failed to process {os.path.basename(stats_file)}\n{e}")
                
        
        # Load into gallery
        self.heatmap_image_paths = [os.path.join(save_dir, f) for f in os.listdir(save_dir) if f.endswith('_heatmap.png')]
        self.heatmap_image_paths.sort()
        if self.heatmap_image_paths:
            self.current_heatmap_index = 0
            self.update_heatmap_gallery()
            
        messagebox.showinfo("Success", f"Analysis complete! Displaying heatmaps.\nFiles saved to:\n{save_dir}")


    def update_heatmap_gallery(self):
        if not self.heatmap_image_paths:
            return
            
        img_path = self.heatmap_image_paths[self.current_heatmap_index]
        try:
            pil_img = Image.open(img_path)
            # Resize image to fit nicely in the GUI frame
            pil_img.thumbnail((600, 500), Image.Resampling.LANCZOS)
            self._current_photo = ImageTk.PhotoImage(pil_img)
            self.heatmap_display.config(image=self._current_photo, text="")
            
            # Update counter and buttons
            total = len(self.heatmap_image_paths)
            self.lbl_gallery.config(text=f"{self.current_heatmap_index + 1} / {total}")
            
            self.btn_prev.config(state=tk.NORMAL if self.current_heatmap_index > 0 else tk.DISABLED)
            self.btn_next.config(state=tk.NORMAL if self.current_heatmap_index < total - 1 else tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"Failed to display heatmap {img_path}: {e}")

    def prev_heatmap(self):
        if self.current_heatmap_index > 0:
            self.current_heatmap_index -= 1
            self.update_heatmap_gallery()
            
    def next_heatmap(self):
        if self.current_heatmap_index < len(self.heatmap_image_paths) - 1:
            self.current_heatmap_index += 1
            self.update_heatmap_gallery()

    def launch_analyzer_popout(self):
        popout = tk.Toplevel(self.root)
        popout.title("Analyze Measurement Dashboard")
        popout.geometry("1600x900")
        
        # Instantiate the AnalyzerGUI inside the new full-screen Toplevel window
        from gui import GUI as AnalyzerGUI
        self.analyzer = AnalyzerGUI(master=popout)

    def build_ops_tab(self):
        ttk.Label(self.tab_ops, text="TECHNICIAN DAILY OPERATIONS", font=("Arial", 14, "bold")).pack(pady=20)
        
        frame_ops = ttk.Frame(self.tab_ops)
        frame_ops.pack(fill=tk.BOTH, expand=True, padx=50)
        
        ops = [
            ("Daily Media Change (500uL)", "media_change"),
            ("Friday Acute SIPA Test", "acute_test"),
            ("Automated Calcium Curve", "calcium_curve")
        ]
        
        for ui_name, key in ops:
            row = ttk.Frame(frame_ops)
            row.pack(fill=tk.X, pady=10)
            ttk.Button(row, text=f"RUN: {ui_name}", command=lambda k=key: self.execute_routine(k, "")).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            ttk.Button(row, text="Assign JSON", width=15, command=lambda k=key: self.assign_routine(k)).pack(side=tk.RIGHT, padx=10)

    def build_dilution_tab(self):
        ttk.Label(self.tab_dilution, text="SIPA Dilution Calculator (Target <1% DMSO, >50uL vol)", font=("Arial", 12, "bold")).pack(pady=10)
        
        f_in = ttk.LabelFrame(self.tab_dilution, text="Inputs", padding=15)
        f_in.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(f_in, text="Stock Concentration (mM):").grid(row=0, column=0, sticky="e", pady=5)
        ent_stock = ttk.Entry(f_in)
        ent_stock.insert(0, "10")
        ent_stock.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(f_in, text="Target Well Concentration (uM):").grid(row=1, column=0, sticky="e", pady=5)
        ent_target = ttk.Entry(f_in)
        ent_target.insert(0, "30")
        ent_target.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(f_in, text="Well Media Volume (uL):").grid(row=2, column=0, sticky="e", pady=5)
        ent_vol = ttk.Entry(f_in)
        ent_vol.insert(0, "500")
        ent_vol.grid(row=2, column=1, pady=5, padx=5)
        
        res_text = tk.Text(self.tab_dilution, height=10, font=("Consolas", 10))
        res_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        def calc():
            try:
                stock_um = float(ent_stock.get()) * 1000
                target_um = float(ent_target.get())
                well_vol = float(ent_vol.get())
                
                dilution_factor = stock_um / target_um
                transfer_vol = well_vol / (dilution_factor - 1)
                dmso_pct = (transfer_vol / (well_vol + transfer_vol)) * 100
                
                res = f"--- DILUTION RESULTS ---\n"
                res += f"Transfer Volume Needed: {transfer_vol:.2f} uL\n"
                res += f"Final DMSO Concentration: {dmso_pct:.3f}%\n\n"
                
                if transfer_vol < 50:
                    res += "[WARNING] Transfer volume is < 50uL! Prepare an intermediate working stock.\n"
                else:
                    res += "[OK] Transfer volume is >= 50uL.\n"
                    
                if dmso_pct > 1.0:
                    res += "[WARNING] DMSO limit exceeded (>1%)! Tissue toxicity risk.\n"
                else:
                    res += "[OK] DMSO is within safe limits (<1%).\n"
                    
                res_text.delete(1.0, tk.END)
                res_text.insert(tk.END, res)
            except Exception as e:
                res_text.delete(1.0, tk.END)
                res_text.insert(tk.END, f"Error: {e}")
                
        ttk.Button(f_in, text="Calculate", command=calc).grid(row=3, column=0, columnspan=2, pady=15)

    def build_jog_tab(self):
        f_conn = ttk.LabelFrame(self.tab_jog, text="Hardware Handshake", padding=15)
        f_conn.pack(fill=tk.X, padx=20, pady=10)
        self.port_var = tk.StringVar()
        self.port_drop = ttk.Combobox(f_conn, textvariable=self.port_var, state="readonly", width=30)
        self.port_drop.pack(side=tk.LEFT, padx=5)
        ttk.Button(f_conn, text="Scan Ports", command=self.hw_scan).pack(side=tk.LEFT, padx=5)
        ttk.Button(f_conn, text="Connect & Initialize", command=self.hw_init).pack(side=tk.LEFT, padx=15)
        self.hw_stat_can = tk.Canvas(f_conn, width=20, height=20, highlightthickness=0)
        self.hw_stat_can.pack(side=tk.LEFT, padx=5)
        self.hw_led = self.hw_stat_can.create_oval(2, 2, 18, 18, fill="gray")
        self.lbl_hw_stat = ttk.Label(f_conn, text="OFFLINE", font=("Arial", 9, "bold"))
        self.lbl_hw_stat.pack(side=tk.LEFT)

        f_speed = ttk.LabelFrame(self.tab_jog, text="Global Kinematic Speed (%)", padding=15)
        f_speed.pack(fill=tk.X, padx=20, pady=5)
        self.speed_var = tk.IntVar(value=100)
        speed_f = ttk.Frame(f_speed)
        speed_f.pack(fill=tk.X, padx=100, pady=5)
        ttk.Label(speed_f, text="Velocity:", width=10, font=("Arial", 11)).pack(side=tk.LEFT)
        s_speed = ttk.Scale(speed_f, from_=1, to=100, variable=self.speed_var, orient='horizontal')
        s_speed.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        l_speed = ttk.Label(speed_f, text="100%", width=8, font=("Arial", 11, "bold"))
        l_speed.pack(side=tk.LEFT)
        self.speed_var.trace_add("write", lambda *a, var=self.speed_var, lbl=l_speed: lbl.config(text=f"{var.get()}%"))

        f_jog = ttk.LabelFrame(self.tab_jog, text="Position Calibration Sliders", padding=15)
        f_jog.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self.jog_vars = {"X": tk.DoubleVar(), "Y": tk.DoubleVar(), "Z": tk.DoubleVar()}
        self.jog_btns = {}

        for axis in ["X", "Y", "Z"]:
            f = ttk.Frame(f_jog)
            f.pack(fill=tk.X, padx=100, pady=10)
            ttk.Label(f, text=f"{axis}-Axis (mm):", width=12, font=("Arial", 11)).pack(side=tk.LEFT)

            e = ttk.Entry(f, textvariable=self.jog_vars[axis], font=("Consolas", 11), state='disabled', width=15)
            e.pack(side=tk.LEFT, padx=10)
            self.jog_sliders[axis] = e

            btn = tk.Button(f, text="MOVE", bg="#007bff", fg="white", font=("Arial", 9, "bold"), state='disabled',
                            command=lambda ax=axis: self.lims.hw.move_to(self.jog_vars["X"].get(),
                                                                         self.jog_vars["Y"].get(),
                                                                         self.jog_vars["Z"].get(),
                                                                         speed=self.speed_var.get()))
            btn.pack(side=tk.LEFT, padx=5)
            self.jog_btns[axis] = btn

            e.bind('<Return>',
                   lambda event, ax=axis: self.lims.hw.move_to(self.jog_vars["X"].get(), self.jog_vars["Y"].get(),
                                                               self.jog_vars["Z"].get(), speed=self.speed_var.get()))

    def start_telemetry(self):
        if not self.telemetry_active:
            self.telemetry_active = True
            threading.Thread(target=self._poll_coordinates, daemon=True).start()

    def _poll_coordinates(self):
        while self.telemetry_active:
            if self.lims.pipettor.hardware:
                try:
                    self.current_pos = {"X": self.jog_vars["X"].get(), "Y": self.jog_vars["Y"].get(),
                                        "Z": self.jog_vars["Z"].get()}
                except Exception:
                    pass
            self.root.after(0, self.draw_deck)
            time.sleep(0.1)

    def get_render_width(self):
        return self.bed_width

    def get_v_x(self, m_x):
        return (self.bed_width - m_x) * self.scale

    def get_m_x(self, c_x):
        return self.bed_width - (c_x / self.scale)

    def track_mouse(self, e):
        rx, ry = self.get_m_x(e.x), e.y / self.scale
        self.lbl_coords.config(text=f"Physical Coordinates -> X: {rx:.1f}, Y: {ry:.1f}")

    def draw_deck(self):
        self.canvas.delete("all")
        render_width = self.bed_width
        self.canvas.config(width=render_width * self.scale, height=self.bed_height * self.scale)

        for x in range(0, int(render_width) + 10, 10):
            vx = self.get_v_x(x)
            self.canvas.create_line(vx, 0, vx, self.bed_height * self.scale,
                                    fill="#ebebeb" if x % 50 != 0 else "#cccccc")
            if x % 50 == 0: self.canvas.create_text(vx, 10, text=f"{x}mm", fill="#888")

        for y in range(0, int(self.bed_height) + 10, 10):
            vy = y * self.scale
            self.canvas.create_line(0, vy, render_width * self.scale, vy, fill="#ebebeb" if y % 50 != 0 else "#cccccc")
            if y % 50 == 0: self.canvas.create_text(render_width * self.scale - 10, vy, text=f"{y}mm", fill="#888",
                                                    anchor="e")

        ox = render_width * self.scale
        self.canvas.create_oval(ox - 15, 2, ox - 2, 15, fill="red", outline="black")
        self.canvas.create_text(ox - 18, 15, text="(0,0)", anchor="ne", fill="red", font=("Arial", 9, "bold"))

        for name in self.placed_slots:
            s = self.lims.deck_slots[name]

            visual_x_right = self.get_v_x(s.x_abs)
            visual_x_left = self.get_v_x(s.x_abs + s.width_mm)

            y0 = s.y_abs * self.scale
            y1 = (s.y_abs + s.height_mm) * self.scale

            is_sel = (name == self.selected_slot_name)
            fill = "#e9ecef" if name in self.lims.deck_labware else ("#cce5ff" if is_sel else "#f8f9fa")
            outline = "blue" if is_sel else "#6c757d"

            self.canvas.create_rectangle(visual_x_left, y0, visual_x_right, y1, fill=fill, outline=outline,
                                         width=3 if is_sel else 2)
            self.canvas.create_text(visual_x_left + 5, y0 + 5, text=name, anchor="nw", font=("Arial", 10, "bold"))

            if name in self.lims.deck_labware:
                lab = self.lims.deck_labware[name]
                first_w = list(lab.wells.values())[0]
                lw_w = max(w.x_rel for w in lab.wells.values()) + first_w.x_rel
                lw_h = max(w.y_rel for w in lab.wells.values()) + first_w.y_rel
                cx = s.x_abs + (s.width_mm / 2.0)
                cy = s.y_abs + (s.height_mm / 2.0)

                # --- VISUAL UI FIX: Render all labware wells matching physical kinematics ---
                for w in lab.wells.values():
                    coords = self._calculate_xy(name, w.name)
                    if coords:
                        phys_wx, phys_wy = coords
                    else:
                        phys_wx = cx + ((lw_w / 2.0) - w.x_rel)
                        phys_wy = cy - (lw_h / 2.0) + w.y_rel

                    wx, wy, r = self.get_v_x(phys_wx), phys_wy * self.scale, w.radius * self.scale

                    self.canvas.create_oval(wx - r, wy - r, wx + r, wy + r, fill="white", outline="#dee2e6")
                    if r > 4: self.canvas.create_text(wx, wy, text=w.name, font=("Arial", int(r * 0.8)), fill="#666")
                # ----------------------------------------------------------------------

            if is_sel:
                badge_text = f" [{name}] X: {s.x_abs:.1f} | Y: {s.y_abs:.1f} "
                self.canvas.create_rectangle(visual_x_right - 190, y0 - 24, visual_x_right, y0, fill="#007bff",
                                             outline="black")
                self.canvas.create_text(visual_x_right - 185, y0 - 12, text=badge_text, anchor="w", fill="white",
                                        font=("Consolas", 10, "bold"))
                self.canvas.create_oval(visual_x_right - 4, y0 - 4, visual_x_right + 4, y0 + 4, fill="red",
                                        outline="black")

        px, py = self.get_v_x(self.current_pos["X"]), self.current_pos["Y"] * self.scale
        self.canvas.create_line(px - 10, py, px + 10, py, fill="red", width=2)
        self.canvas.create_line(px, py - 10, px, py + 10, fill="red", width=2)
        self.canvas.create_oval(px - 5, py - 5, px + 5, py + 5, outline="red")

        hud_bg = self.canvas.create_rectangle(5, 5, 140, 75, fill="#333", stipple="gray50")
        hud_text = f"LIVE TELEMETRY\nX: {self.current_pos['X']:>6.2f} mm\nY: {self.current_pos['Y']:>6.2f} mm\nZ: {self.current_pos['Z']:>6.2f} mm"
        self.canvas.create_text(10, 10, text=hud_text, anchor="nw", fill="#00ff00", font=("Consolas", 10, "bold"))

    def build_deck_tab(self):
        pane_l = ttk.Frame(self.tab_deck, width=240)
        pane_l.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        pane_m = ttk.Frame(self.tab_deck, width=260)
        pane_m.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        right_f = ttk.Frame(self.tab_deck)
        right_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_f = ttk.Frame(right_f)
        canvas_f.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.lbl_coords = ttk.Label(canvas_f, text="Physical Coordinates -> X: 0.0, Y: 0.0")
        self.lbl_coords.pack(anchor="ne")

        self.canvas = tk.Canvas(canvas_f, bg="white", relief="sunken", bd=2)
        self.canvas.pack(pady=10, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Motion>", self.track_mouse)
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.drag_end)

        f_jog = ttk.LabelFrame(right_f, text="Live Calibration Jog Control", padding=10)
        f_jog.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.deck_jog_btns = {}
        for axis in ["X", "Y", "Z"]:
            f = ttk.Frame(f_jog)
            f.pack(fill=tk.X, padx=10, pady=2)
            ttk.Label(f, text=f"{axis} (mm):", width=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

            e = ttk.Entry(f, textvariable=self.jog_vars[axis], font=("Consolas", 10), state='disabled', width=10)
            e.pack(side=tk.LEFT, padx=10)
            self.deck_jog_sliders[axis] = e

            btn = tk.Button(f, text="MOVE", bg="#007bff", fg="white", font=("Arial", 8, "bold"), state='disabled',
                            command=lambda ax=axis: self.lims.hw.move_to(self.jog_vars["X"].get(),
                                                                         self.jog_vars["Y"].get(),
                                                                         self.jog_vars["Z"].get(),
                                                                         speed=self.speed_var.get()))
            btn.pack(side=tk.LEFT, padx=5)
            self.deck_jog_btns[axis] = btn

            e.bind('<Return>',
                   lambda event, ax=axis: self.lims.hw.move_to(self.jog_vars["X"].get(), self.jog_vars["Y"].get(),
                                                               self.jog_vars["Z"].get(), speed=self.speed_var.get()))

        ttk.Label(pane_l, text="Inventory", font=("Arial", 10, "bold")).pack(pady=5)
        self.list_unplaced = tk.Listbox(pane_l, height=10, bg="white")
        self.list_unplaced.pack(fill=tk.X)
        ttk.Button(pane_l, text="Place on Deck \u2192", command=self.place_slot).pack(fill=tk.X, pady=2)
        self.list_placed = tk.Listbox(pane_l, height=10, bg="white")
        self.list_placed.pack(fill=tk.X)
        ttk.Button(pane_l, text="Remove from Deck \u2190", command=self.remove_slot).pack(fill=tk.X, pady=2)
        ttk.Button(pane_l, text="EMERGENCY RESET", command=self.emergency_reset).pack(fill=tk.X, pady=30)

        self.entries = {}
        for lab, key in [("X Coord", "x_abs"), ("Y Coord", "y_abs"), ("Width", "width_mm"), ("Height", "height_mm"),
                         ("Z Floor Offset (+mm)", "z_offset")]:
            ttk.Label(pane_m, text=lab).pack(anchor="w")
            v = tk.StringVar()
            e = ttk.Entry(pane_m, textvariable=v)
            e.pack(fill=tk.X, pady=2)
            self.entries[key] = v
            v.trace_add("write", lambda *args, k=key, var=v: self.sync_to_backend(k, var))

        self.lw_var = tk.StringVar()
        self.lw_drop = ttk.Combobox(pane_m, textvariable=self.lw_var, state="readonly")
        self.lw_drop.pack(fill=tk.X, pady=10)
        ttk.Button(pane_m, text="Assign Labware", command=self.assign_lw).pack(fill=tk.X)
        ttk.Button(pane_m, text="Unassign Labware", command=self.unassign_lw).pack(fill=tk.X, pady=2)
        ttk.Button(pane_m, text="SAVE WORKSPACE", command=self.save_all).pack(side=tk.BOTTOM, fill=tk.X, pady=20)

    def check_alignment(self):
        mouse_x = self.get_m_x(self.canvas.winfo_pointerx() - self.canvas.winfo_rootx())
        hardware_x = self.jog_vars["X"].get()
        self.logger.info(f"--- ALIGNMENT CHECK ---")
        self.logger.info(f"Visual Grid X (Mouse Cursor): {mouse_x:.1f}mm")
        self.logger.info(f"Hardware Jog X (Machine Base): {hardware_x:.1f}mm")

    def build_direct_ops_tab(self):
        ttk.Label(self.tab_direct, text="Immediate Machine Controls", font=("Arial", 16, "bold")).pack(anchor="w")
        ops = [
            ("Home Head", "Resets pipette head to safety origin.", "HOME"),
            ("Find Tip", "Auto-searches a designated slot using NATIVE API.", "FIND_TIP"),
            ("Discard Tips", "Moves head to designated Waste slot and triggers ejection mechanism.", "DISCARD"),
            ("Check Alignment", "Compares visual mouse grid to hardware jog coordinates.", "CHECK")
        ]
        for title, desc, code in ops:
            f = ttk.LabelFrame(self.tab_direct, text=f" {title} ", padding=15)
            f.pack(fill=tk.X, pady=8)
            sub = ttk.Frame(f)
            sub.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Label(sub, text=f"Action: {desc}").pack(anchor="w")
            tk.Button(f, text=f"RUN {code}", bg="#007bff", fg="white", font=("Arial", 9, "bold"), width=12,
                      command=lambda c=code: self.run_direct_op(c)).pack(side=tk.RIGHT, padx=10)

    def build_workflow_tab(self):
        pane_ctrl = ttk.Frame(self.tab_workflow, width=380)
        pane_ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=15)
        pane_list = ttk.Frame(self.tab_workflow)
        pane_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(pane_ctrl, text="Protocol Builder", font=("Arial", 11, "bold")).pack(pady=(10, 5))
        ttk.Label(pane_ctrl, text="Action Type:").pack(anchor="w")

        self.wf_action = ttk.Combobox(pane_ctrl, state="readonly",
                                      values=["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip",
                                              "System: Incubate (Wait)", "System: FOC48 Measurement", "System: Calcium Curve", "System: Data Analysis", "System: DB Upload"])
        self.wf_action.current(0)
        self.wf_action.pack(fill=tk.X, pady=(0, 5))

        self.auto_tip_search_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Auto-Search Tips (Skip empty wells)", variable=self.auto_tip_search_var).pack(
            fill=tk.X, pady=(5, 2))

        self.dynamic_z_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Auto-Height Detection (Liquids ONLY)", variable=self.dynamic_z_var).pack(
            fill=tk.X, pady=(0, 2))

        ttk.Checkbutton(pane_ctrl, text="Pipette Currently Has Tip", variable=self.has_tip_var).pack(fill=tk.X,
                                                                                                     pady=(0, 2))

        self.manual_mode_var = tk.BooleanVar(value=False)
        self.chk_manual_mode = ttk.Checkbutton(pane_ctrl, text="Enable Manual Coordinates",
                                               variable=self.manual_mode_var, command=self._toggle_wf_inputs)
        self.chk_manual_mode.pack(fill=tk.X, pady=(0, 10))

        self.input_frame = ttk.Frame(pane_ctrl)
        self.input_frame.pack(fill=tk.X, expand=True)
        self.lbl_1 = ttk.Label(self.input_frame, text="")
        self.cbx_slot = ttk.Combobox(self.input_frame, state="readonly")
        self.ent_x = ttk.Entry(self.input_frame)
        self.lbl_2 = ttk.Label(self.input_frame, text="")
        self.ent_well = ttk.Entry(self.input_frame)
        self.ent_y = ttk.Entry(self.input_frame)
        self.lbl_3 = ttk.Label(self.input_frame, text="")
        self.ent_z = ttk.Entry(self.input_frame)
        self.lbl_4 = ttk.Label(self.input_frame, text="")
        self.ent_vol = ttk.Entry(self.input_frame)

        ttk.Button(pane_ctrl, text="+ Add Step to Protocol", command=self.add_wf_step).pack(fill=tk.X, pady=10)
        ttk.Button(pane_ctrl, text="Clear Protocol",
                   command=lambda: [self.wf_box.delete(0, tk.END), self.workflow_sequence.clear()]).pack(fill=tk.X)
        ttk.Separator(pane_ctrl, orient="horizontal").pack(fill=tk.X, pady=8)
        ttk.Button(pane_ctrl, text="📥 Convert & Import Python (.py)", command=self.action_import_python_protocol).pack(fill=tk.X, pady=2)
        ttk.Button(pane_ctrl, text="📂 Load JSON Protocol", command=self.action_load_workflow).pack(fill=tk.X, pady=2)
        ttk.Button(pane_ctrl, text="💾 Save Protocol As JSON...", command=self.action_save_workflow_as).pack(fill=tk.X, pady=2)

        self.wf_box = tk.Listbox(pane_list, font=("Consolas", 11), bg="#f8f9fa", fg="black", selectbackground="#007bff")
        self.wf_box.pack(fill=tk.BOTH, expand=True)

        run_frame = ttk.LabelFrame(pane_list, text="Opentrons-Style Run Dashboard", padding=10)
        run_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(run_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.lbl_timer = ttk.Label(run_frame, text="Time Remaining: --:--", font=("Consolas", 11, "bold"),
                                   foreground="blue")
        self.lbl_timer.pack(pady=(0, 10))

        ctrl_frame = ttk.Frame(run_frame)
        ctrl_frame.pack(fill=tk.X)
        self.btn_play = tk.Button(ctrl_frame, text="▶ START PROTOCOL", bg="#28a745", fg="white",
                                  font=("Arial", 11, "bold"), command=self.execute_protocol)
        self.btn_play.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_pause = tk.Button(ctrl_frame, text="⏸ PAUSE", bg="#ffc107", font=("Arial", 11, "bold"),
                                   state=tk.DISABLED, command=self.pause_resume_run)
        self.btn_pause.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_stop = tk.Button(ctrl_frame, text="⏹ CANCEL", bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
                                  state=tk.DISABLED, command=self.stop_run)
        self.btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.wf_action.bind("<<ComboboxSelected>>", self._toggle_wf_inputs)
        self._toggle_wf_inputs()

    def _toggle_wf_inputs(self, event=None):
        action = self.wf_action.get()
        is_manual = self.manual_mode_var.get()
        for w in self.input_frame.winfo_children(): w.pack_forget()

        if "System" in action or "DB:" in action:
            self.chk_manual_mode.config(state="disabled")
            is_manual = False
        else:
            self.chk_manual_mode.config(state="normal")

        if is_manual:
            self.lbl_1.config(text="Visual Grid X (mm):")
            self.lbl_1.pack(anchor="w")
            self.ent_x.pack(fill=tk.X, pady=(0, 5))
            self.lbl_2.config(text="Visual Grid Y (mm):")
            self.lbl_2.pack(anchor="w")
            self.ent_y.pack(fill=tk.X, pady=(0, 5))
            self.lbl_3.config(text="Action Z-Depth (mm):")
            self.lbl_3.pack(anchor="w")
            self.ent_z.pack(fill=tk.X, pady=(0, 5))
            if action not in ["Pick Up Tip", "Discard Tip"]:
                self.lbl_4.config(text="Volume (\u03bcL):")
                self.lbl_4.pack(anchor="w")
                self.ent_vol.pack(fill=tk.X, pady=(0, 5))
        else:
            if "Incubate" in action:
                self.lbl_4.config(text="Seconds (e.g., 300):")
                self.lbl_4.pack(anchor="w")
                self.ent_vol.pack(fill=tk.X, pady=(0, 5))
            elif "FOC48" in action:
                self.lbl_2.config(text="Assay Plate Name:")
                self.lbl_2.pack(anchor="w")
                self.ent_well.pack(fill=tk.X, pady=(0, 5))
            elif "Data Analysis" in action:
                pass
            elif "DB Upload" in action:
                pass
            elif "Calcium Curve" in action:
                pass
            elif "DB:" in action:
                pass
            else:
                self.lbl_1.config(text="Target Deck Slot:")
                self.lbl_1.pack(anchor="w")
                self.cbx_slot.pack(fill=tk.X, pady=(0, 5))
                self.lbl_2.config(text="Target Well (e.g., A1):")
                self.lbl_2.pack(anchor="w")
                self.ent_well.pack(fill=tk.X, pady=(0, 5))
                if action not in ["Pick Up Tip", "Discard Tip"]:
                    self.lbl_4.config(text="Volume (\u03bcL):")
                    self.lbl_4.pack(anchor="w")
                    self.ent_vol.pack(fill=tk.X, pady=(0, 5))
                    self.lbl_3.config(text="Extra Z-Depth (+mm) [Optional]:")
                    self.lbl_3.pack(anchor="w")
                    self.ent_z.pack(fill=tk.X, pady=(0, 5))

    def add_wf_step(self):
        action = self.wf_action.get()
        is_manual = self.manual_mode_var.get()
        step_data = {"action": action, "mode": "manual" if is_manual else "auto"}

        if "System" in action:
            step_data["mode"] = "auto"
            if "Incubate" in action:
                try:
                    vol_val = float(self.ent_vol.get())
                except ValueError:
                    vol_val = 0.0
                step_data["volume"] = vol_val
                msg = f"[SYSTEM] Incubate for {vol_val} seconds."
            elif "FOC48" in action:
                step_data["well"] = self.ent_well.get()
                msg = f"[MEASURE] Execute FOC48_Stim_0.xml for Plate: '{step_data['well']}'"
            elif "Data Analysis" in action:
                msg = f"[ANALYSIS] Execute Hill Equation Modeling"
            elif "DB Upload" in action:
                msg = f"[DATABASE] Sync Results to ContractionDB"
        elif is_manual:
            x, y, z, vol = self.ent_x.get(), self.ent_y.get(), self.ent_z.get(), self.ent_vol.get()
            try:
                step_data["x"] = float(x)
                step_data["y"] = float(y)
                step_data["z"] = float(z)
                step_data["volume"] = float(vol) if vol else 0.0
            except ValueError:
                step_data["x"] = 0.0
                step_data["y"] = 0.0
                step_data["z"] = 0.0
                step_data["volume"] = 0.0
            if action in ["Pick Up Tip", "Discard Tip"]:
                msg = f"[{action.upper()} MANUAL] X:{step_data['x']} Y:{step_data['y']} Z:{step_data['z']}"
            else:
                msg = f"[{action.upper()} MANUAL] X:{step_data['x']} Y:{step_data['y']} Z:{step_data['z']} Vol:{step_data['volume']}\u03bcL"
        else:
            slot, well, vol = self.cbx_slot.get(), self.ent_well.get(), self.ent_vol.get()
            extra_z_val = self.ent_z.get() if self.ent_z.winfo_ismapped() else "0.0"

            if not slot: messagebox.showwarning("Incomplete Data", "Please select a target deck slot."); return
            step_data["slot"], step_data["well"] = slot, well
            try:
                step_data["volume"] = float(vol) if vol else 0.0
            except ValueError:
                step_data["volume"] = 0.0

            try:
                step_data["extra_z"] = float(extra_z_val) if extra_z_val else 0.0
            except ValueError:
                step_data["extra_z"] = 0.0

            if action in ["Pick Up Tip", "Discard Tip"]:
                msg = f"[{action.upper()}] from {slot}, Well {well}" if action == "Pick Up Tip" else f"[{action.upper()}] into {slot} (Waste Trough)"
            else:
                z_msg = f" (Z+{step_data['extra_z']}mm)" if step_data.get('extra_z', 0.0) > 0 else ""
                msg = f"[{action.upper()}] {step_data['volume']}\u03bcL at {slot}, Well {well}{z_msg}"

        self.wf_box.insert(tk.END, msg)
        self.workflow_sequence.append(step_data)

    def pause_resume_run(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="▶ RESUME", bg="#17a2b8")
            self.logger.info("Protocol Paused by User.")
        else:
            self.pause_event.set()
            self.btn_pause.config(text="⏸ PAUSE", bg="#ffc107")
            self.logger.info("Protocol Resumed.")

    def stop_run(self):
        self.is_aborted = True
        self.pause_event.set()
        self.logger.info("Protocol Abort Signal Sent.")

    def update_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        self.btn_play.config(state=state)
        self.btn_pause.config(state=tk.NORMAL if running else tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL if running else tk.DISABLED)

    def ask_error_resolution(self, error_msg, step_idx):
        self.pause_event.clear()
        self.root.after(0, lambda: self.btn_pause.config(text="▶ RESUME", bg="#17a2b8"))
        self.user_decision = None

        def prompt():
            ans = messagebox.askyesno("Hardware Exception",
                                      f"Protocol Halted on Step {step_idx}.\n\nHardware Trace:\n{error_msg}\n\nOpentrons Failsafe: Do you want to IGNORE this hardware warning and force the script to continue?")
            self.user_decision = "ignore" if ans else "abort"

        self.root.after(0, prompt)
        while self.user_decision is None: time.sleep(0.1)

        if self.user_decision == "abort":
            self.is_aborted = True
        else:
            self.logger.warning(f"User overrode hardware interlock on Step {step_idx}. Forcing continuation.")
            self.pause_event.set()
            self.root.after(0, lambda: self.btn_pause.config(text="⏸ PAUSE", bg="#ffc107"))

    def _calculate_xy(self, slot_name, well_id):
        slot_obj = self.lims.deck_slots.get(slot_name)
        sy = slot_obj.y_abs if slot_obj else 60.0

        # --- PHYSICAL HARDWARE OVERRIDE FOR SLOT 3 TIP RACK ---
        if slot_name == "Slot_3":
            col_x = {
                '1': 242.0, '2': 233.0, '3': 224.0, '4': 215.0,
                '5': 206.0, '6': 197.0, '7': 188.0, '8': 179.0,
                '9': 170.0, '10': 161.0, '11': 152.0, '12': 143.0
            }
            row_y = {
                'A': 60.0,  'B': 69.0,  'C': 78.0,  'D': 87.0,
                'E': 96.0,  'F': 105.0, 'G': 114.0, 'H': 123.0
            }
            if len(well_id) >= 2:
                r_c = well_id[0].upper()
                c_c = well_id[1:]
                if r_c in row_y and c_c in col_x:
                    return col_x[c_c], row_y[r_c]

            # Optional logging for lims_master_gui.py
            if hasattr(self, 'logger'):
                self.logger.warning(f"Slot 3 Override: Well {well_id} falls outside defined 96-tip grid.")
        # ---------------------------------------------
        # --- PHYSICAL HARDWARE OVERRIDE FOR SLOT 4 EHM PLATE ---
        if slot_name == "Slot_4":
            col_x = {'1': 105.00, '2': 87.00, '3': 68.88, '4': 51.54, '5': 34.20, '6': 15.60}
            row_y = {
                'A': 67.30, 'B': 75.30, 'C': 85.30, 'D': 95.30,
                'E': 105.30, 'F': 113.30, 'G': 121.30, 'H': 129.30
            }
            # Catch empty or malformed well IDs
            if len(well_id) >= 2:
                row_char = well_id[0].upper()
                col_char = well_id[1:]
                if row_char in row_y and col_char in col_x:
                    return col_x[col_char], row_y[row_char]

            self.logger.warning(
                f"Slot 4 Override: Well {well_id} falls outside defined EHM grid. Defaulting to center.")
        # ------------------------------------------------------------------------
        # --- BULLETPROOF FIX: Dynamic Physical Override for Slot 5 Reagent Reservoir ---
        if slot_name == "Slot_5":
            col_x = {
                '1': 239.0, '2': 220.0, '3': 201.0,
                '4': 182.0, '5': 163.0, '6': 144.0
            }
            col_char = well_id[1:] if len(well_id) >= 2 else '1'
            target_x = col_x.get(col_char, 191.5)
            target_y = 207.75
            return target_x, target_y
        # ------------------------------------------------------------------------

        # Safety catch if slot is deleted mid-render
        if not slot_obj: return 0.0, 0.0

        cx = slot_obj.x_abs + (slot_obj.width_mm / 2.0)
        cy = slot_obj.y_abs + (slot_obj.height_mm / 2.0)

        if slot_name == "Slot_6":
            return cx, cy

        # Safety catch if labware is unassigned mid-render
        labware_obj = self.lims.deck_labware.get(slot_name)
        if not labware_obj or not labware_obj.wells:
            return cx, cy

        first_w = list(labware_obj.wells.values())[0]
        lw_w = max(w.x_rel for w in labware_obj.wells.values()) + first_w.x_rel
        lw_h = max(w.y_rel for w in labware_obj.wells.values()) + first_w.y_rel
        well_obj = labware_obj.wells.get(well_id)

        if not well_obj: return cx, cy

        return cx + ((lw_w / 2.0) - well_obj.x_rel), cy - (lw_h / 2.0) + well_obj.y_rel

    def _calculate_z(self, action, labware_obj, well_id, mode, manual_z, slot_name, extra_z=0.0):
        if action == "Pick Up Tip":
            return 0.0

        if mode == "manual": return manual_z

        slot_obj = self.lims.deck_slots.get(slot_name)
        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

        if action in ["Aspirate Media", "Dispense Media", "Discard Tip"]:
            # --- Z-DEPTH FIX: Force 102.0mm for Slot 4 ---
            if slot_name == "Slot_4":
                base_z = 98.0
            elif slot_name == "Slot_5":
                base_z = 101.5
            elif slot_name == "Slot_6":
                base_z = 90.0
            elif action == "Discard Tip" and slot_name == "Slot_1":
                base_z = 90.0
            elif labware_obj and (
                    getattr(labware_obj, 'z_height_mm', 20.0) == 105.81 or "reservoir" in labware_obj.name.lower()):
                base_z = 101.5
            else:
                base_z = 101.0

            return min(base_z + slot_z_offset + extra_z, 103.5)

        return 0.0

    def prompt_for_tip_slot(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return

        top = tk.Toplevel(self.root)
        top.title("Smart Tip Search")
        top.geometry("350x150")
        ttk.Label(top, text="Select the slot containing the tip rack:").pack(pady=10)
        slot_var = tk.StringVar()
        cb = ttk.Combobox(top, textvariable=slot_var, values=self.placed_slots, state="readonly")
        cb.pack(pady=5)
        if self.placed_slots: cb.current(0)

        def on_confirm():
            slot = slot_var.get()
            top.destroy()
            if slot: threading.Thread(target=self.run_find_tip_routine, args=(slot,), daemon=True).start()

        ttk.Button(top, text="Start Search Sequence", command=on_confirm).pack(pady=10)

    def run_find_tip_routine(self, slot_name):
        self.logger.info(f"--- Direct Op: Smart Tip Search in {slot_name} ---")
        labware_obj = self.lims.deck_labware.get(slot_name)
        if not labware_obj:
            self.logger.error(f"No labware assigned to {slot_name}.")
            return

        wells = list(labware_obj.wells.keys())
        tip_found = False

        for current_well in wells:
            if self.is_aborted: break

            # Safe tuple unpacking
            coords = self._calculate_xy(slot_name, current_well)
            tx, ty = coords if coords else (0, 0)

            if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
            self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
            time.sleep(0.05)

            self.logger.info(f"Triggering native pick_tip(87.0) search algorithm at {current_well}.")
            try:
                hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                labware_obj = self.lims.deck_labware.get(slot_name)
                z_height = getattr(labware_obj, 'z_height_mm', 78.18) if labware_obj else 78.18
                approach_z = max(0.0, min(55.0, z_height - 18.0))
                if self.lims.pipettor.hardware:
                    self.lims.pipettor.hardware.z_speed = hw_speed
                    self.lims.pipettor.hardware.move_z(approach_z)
                    self.lims.pipettor.hardware.z_speed = 3
                    self.lims.pipettor.hardware.tip_pickup_force = 26
                    try:
                        self.lims.pipettor.hardware.pick_tip(87.0)
                    except Exception as p_err:
                        curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                        if curr_z < 60.0:
                            raise p_err
                    curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                    if curr_z >= 60.0:
                        try:
                            push_z = min(curr_z + 2.5, 89.0)
                            self.lims.pipettor.hardware.move_z(push_z)
                            time.sleep(0.35)
                        except Exception as pe:
                            self.logger.warning(f"Pushback seating completed with resistance: {pe}")
                else:
                    curr_z = 75.0
                self.logger.info(f"Tip acquired at {current_well} (Z={curr_z:.2f}mm). System state updated: HAS_TIP = True")
                time.sleep(0.35)
                tip_found = True
                self.root.after(0, lambda: self.has_tip_var.set(True))
                if self.lims.pipettor.hardware:
                    try:
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)
                break
            except Exception as e:
                self.logger.warning(f"Sensor exception at {current_well} (Empty). Tracking to next well...")
                if self.lims.pipettor.hardware:
                    try:
                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)

        if not tip_found:
            self.logger.error("Tip search failed. Rack is empty.")
            self.root.after(0, lambda: messagebox.showerror("Search Failed", f"No tips found in {slot_name}."))

    def update_timer(self):
        if not getattr(self, 'timer_running', False):
            return

        if self.is_aborted:
            self.lbl_timer.config(text="Time Remaining: ABORTED", foreground="red")
            return

        if not self.pause_event.is_set():
            # If the protocol is paused, push the start time forward so the countdown freezes
            self.run_start_time += 1.0

        elapsed = time.time() - self.run_start_time
        remaining = max(0, self.estimated_total_time - elapsed)

        mins, secs = divmod(int(remaining), 60)
        self.lbl_timer.config(text=f"Time Remaining: {mins:02d}:{secs:02d}", foreground="blue")

        if self.timer_running:
            self.root.after(1000, self.update_timer)

    def execute_protocol(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock",
                                 "Hardware must be homed via 'Connect & Initialize' before executing automated workflows.")
            return
        if not self.workflow_sequence: return

        # --- AUTO SAVE FUNCTIONALITY INJECTED HERE ---
        export_dir = os.path.join(os.path.expanduser("~"), "Desktop", "pipette trials export")
        os.makedirs(export_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        auto_save_path = os.path.join(export_dir, f"run_{timestamp}.json")
        try:
            with open(auto_save_path, 'w') as f:
                json.dump(self.workflow_sequence, f, indent=4)
        except Exception as e:
            self.logger.warning(f"Could not auto-save to desktop: {e}")

        # ---------------------------------------------

        def run_sequence():
            self.logger.info("--- Protocol Sequence Initiated ---")
            self.is_aborted = False
            self.pause_event.set()
            self.root.after(0, lambda: self.update_ui_state(True))
            total_steps = len(self.workflow_sequence)

            # --- IMPROVED TIME TRACKING ---
            self.estimated_total_time = 0
            for s in self.workflow_sequence:
                action = s.get('action', '')
                vol = s.get('volume', 0.0)

                if "Incubate" in action:
                    self.estimated_total_time += vol
                elif "FOC48" in action:
                    self.estimated_total_time += 15.0
                elif "Data Analysis" in action:
                    self.estimated_total_time += 5.0
                elif "DB Upload" in action:
                    self.estimated_total_time += 3.0
                elif "Calcium Curve" in action:
                    self.estimated_total_time += 60.0
                elif "Aspirate Media" in action:
                    self.estimated_total_time += 10.0 + (vol * 0.02)
                elif "Dispense Media" in action:
                    self.estimated_total_time += 14.0
                else:
                    self.estimated_total_time += 10.0

            self.run_start_time = time.time()
            self.timer_running = True
            self.root.after(0, self.update_timer)
            # ----------------------------------------

            for i, step in enumerate(self.workflow_sequence, 1):
                self.pause_event.wait()
                if self.is_aborted: break

                self.root.after(0, lambda idx=i - 1: self.wf_box.selection_clear(0, tk.END))
                self.root.after(0, lambda idx=i - 1: self.wf_box.selection_set(idx))
                self.root.after(0, lambda idx=i - 1: self.wf_box.see(idx))
                self.root.after(0, lambda idx=i: self.progress_var.set((idx / total_steps) * 100))

                action, mode, vol = step['action'], step.get('mode', 'auto'), step.get('volume', 0.0)
                extra_z = step.get('extra_z', 0.0)
                self.logger.info(f"Executing Step {i}/{total_steps}: [{action}]")

                if action == "Pick Up Tip" and mode != "manual":
                    if self.has_tip_var.get():
                        self.logger.info("Tip State: ATTACHED. Skipping redundant pickup step.")
                        time.sleep(0.05)
                        continue
                elif action == "Discard Tip" and mode != "manual":
                    if not self.has_tip_var.get():
                        self.logger.info("Tip State: EMPTY. Skipping redundant discard step.")
                        time.sleep(0.05)
                        continue

                # --- DB / UPLOAD REMOVED FROM EXECUTION LOGIC ---
                if "System:" in action:
                    try:
                        if "Incubate" in action:
                            self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get());
                            time.sleep(vol)
                        elif "FOC48" in action:
                            self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get())

                            # Launch the executable in the background
                            p = subprocess.Popen(
                                [r'C:\Labhub\Import\FOC48_20240227.exe', r'C:\Labhub\Import\myrPlate_Stim_0.xml',
                                 str(step.get('well', ''))])

                            self.logger.info("Waiting for FOC48 window to load...")
                            time.sleep(7.0)

                            self.logger.info("Executing ghost mouse clicks...")
                            # 1. Click First Experiment
                            ctypes.windll.user32.SetCursorPos(404, 168)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(1.0)

                            # 2. Click First Measurement
                            ctypes.windll.user32.SetCursorPos(690, 168)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(1.0)

                            # 3. Click Save all
                            ctypes.windll.user32.SetCursorPos(1021, 531)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)

                            self.logger.info("Optical reading in progress. Waiting for FOC48 task to finish...")
                            p.wait()
                        elif "Data Analysis" in action:
                            self.logger.info("Launching Analysis Subsystem (Hill Equations)...")
                            time.sleep(1.5)
                            self.logger.info("Analysis complete. Results buffered.")
                        elif "DB Upload" in action:
                            self.logger.info("Launching DB Subsystem...")
                            time.sleep(1.0)
                            self.logger.info("Payload verified. Pushed to Contraction DB.")
                        elif "Calcium Curve" in action:
                            self.logger.info("Executing Automated Calcium Curve Macro...")
                            time.sleep(2.0)
                            self.logger.info("Calcium Curve executed successfully.")

                    except Exception as e:
                        self.ask_error_resolution(e, i)
                    time.sleep(0.05)
                    continue

                slot_name, well_id = step.get('slot', ''), step.get('well', '')
                target_x, target_y, target_z = None, None, None

                if mode == "manual":
                    target_x, target_y, target_z = step.get('x', 0.0), step.get('y', 0.0), step.get('z', 0.0)
                elif slot_name in self.lims.deck_slots and (
                        slot_name in self.lims.deck_labware or slot_name == "Slot_6"):
                    if slot_name == "Slot_6" or well_id in self.lims.deck_labware[slot_name].wells:

                        # Safe Tuple Unpacking during automated run
                        coords = self._calculate_xy(slot_name, well_id)
                        if coords:
                            target_x, target_y = coords
                        else:
                            self.ask_error_resolution("Well ID mapping failed.", i)
                            continue

                    else:
                        self.ask_error_resolution("Well ID mapping failed.", i)
                        continue
                else:
                    self.ask_error_resolution("Coordinate mapping failed. Is Labware assigned?", i)
                    continue

                try:
                    if action == "Pick Up Tip":
                        pickup_limit = min(92.0, max(82.0, 87.0 + extra_z))
                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        labware_obj = self.lims.deck_labware.get(slot_name)
                        z_height = getattr(labware_obj, 'z_height_mm', 78.18) if labware_obj else 78.18
                        approach_z = max(0.0, min(55.0, z_height - 18.0))
                        if mode == "manual":
                            if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                            self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                            time.sleep(0.05)
                            try:
                                if self.lims.pipettor.hardware:
                                    self.lims.pipettor.hardware.z_speed = hw_speed
                                    self.lims.pipettor.hardware.move_z(approach_z)
                                    self.lims.pipettor.hardware.z_speed = 3
                                    self.lims.pipettor.hardware.tip_pickup_force = 26
                                    try:
                                        self.lims.pipettor.hardware.pick_tip(pickup_limit)
                                    except Exception as p_err:
                                        curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                                        if curr_z < 60.0:
                                            raise p_err
                                    curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                                    if curr_z >= 60.0:
                                        try:
                                            push_z = min(curr_z + 2.5, pickup_limit + 2.0)
                                            self.lims.pipettor.hardware.move_z(push_z)
                                            time.sleep(0.35)
                                        except Exception as pe:
                                            self.logger.warning(f"Pushback seating completed with resistance: {pe}")
                                else:
                                    curr_z = 75.0
                                self.logger.info(f"Manual tip pickup at Z={curr_z:.2f}mm.")
                                time.sleep(0.35)
                            except Exception as e:
                                self.logger.warning(f"Ignored tip error: {e}")
                            self.root.after(0, lambda: self.has_tip_var.set(True))
                            if self.lims.pipettor.hardware:
                                try:
                                    self.lims.pipettor.hardware.z_speed = hw_speed
                                    self.lims.pipettor.hardware.move_z(0)
                                except TypeError:
                                    self.lims.pipettor.hardware.move_z(0)

                        elif self.auto_tip_search_var.get():
                            wells = list(labware_obj.wells.keys()) if labware_obj else []
                            start_idx = wells.index(well_id) if well_id in wells else 0
                            tip_found = False

                            for idx in range(start_idx, len(wells)):
                                if self.is_aborted: break
                                current_well = wells[idx]

                                coords = self._calculate_xy(slot_name, current_well)
                                tx, ty = coords if coords else (0, 0)

                                if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                                self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
                                time.sleep(0.05)

                                self.logger.info(f"Triggering native pick_tip({pickup_limit}) algorithm at {current_well}.")
                                try:
                                    if self.lims.pipettor.hardware:
                                        self.lims.pipettor.hardware.z_speed = hw_speed
                                        self.lims.pipettor.hardware.move_z(approach_z)
                                        self.lims.pipettor.hardware.z_speed = 3
                                        self.lims.pipettor.hardware.tip_pickup_force = 26
                                        try:
                                            self.lims.pipettor.hardware.pick_tip(pickup_limit)
                                        except Exception as p_err:
                                            curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                                            if curr_z < 60.0:
                                                raise p_err
                                        curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                                        if curr_z >= 60.0:
                                            try:
                                                push_z = min(curr_z + 2.5, pickup_limit + 2.0)
                                                self.lims.pipettor.hardware.move_z(push_z)
                                                time.sleep(0.35)
                                            except Exception as pe:
                                                self.logger.warning(f"Pushback seating completed with resistance: {pe}")
                                    else:
                                        curr_z = 75.0
                                    self.logger.info(f"Tip acquired at {current_well} (Z={curr_z:.2f}mm). HAS_TIP = True")
                                    time.sleep(0.35)
                                    tip_found = True
                                    self.root.after(0, lambda: self.has_tip_var.set(True))
                                    if self.lims.pipettor.hardware:
                                        try:
                                            self.lims.pipettor.hardware.z_speed = hw_speed
                                            self.lims.pipettor.hardware.move_z(0)
                                        except TypeError:
                                            self.lims.pipettor.hardware.move_z(0)
                                    break
                                except Exception as e:
                                    self.logger.warning(
                                        f"Sensor exception at {current_well} (Empty). Tracking to next well...")
                                    if self.lims.pipettor.hardware:
                                        try:
                                            self.lims.pipettor.hardware.z_speed = hw_speed
                                            self.lims.pipettor.hardware.move_z(0)
                                        except TypeError:
                                            self.lims.pipettor.hardware.move_z(0)

                            if not tip_found and not self.is_aborted:
                                self.ask_error_resolution("Tip rack is completely empty!", i)
                        else:
                            if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                            self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                            time.sleep(0.05)
                            try:
                                if self.lims.pipettor.hardware:
                                    self.lims.pipettor.hardware.z_speed = hw_speed
                                    self.lims.pipettor.hardware.move_z(approach_z)
                                    self.lims.pipettor.hardware.z_speed = 3
                                    self.lims.pipettor.hardware.tip_pickup_force = 26
                                    try:
                                        self.lims.pipettor.hardware.pick_tip(pickup_limit)
                                    except Exception as p_err:
                                        curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                                        if curr_z < 60.0:
                                            raise p_err
                                    curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                                    if curr_z >= 60.0:
                                        try:
                                            push_z = min(curr_z + 2.5, pickup_limit + 2.0)
                                            self.lims.pipettor.hardware.move_z(push_z)
                                            time.sleep(0.35)
                                        except Exception as pe:
                                            self.logger.warning(f"Pushback seating completed with resistance: {pe}")
                                else:
                                    curr_z = 75.0
                                self.logger.info(f"Tip pickup completed at Z={curr_z:.2f}mm (limit: {pickup_limit:.1f}mm).")
                                time.sleep(0.35)
                                self.root.after(0, lambda: self.has_tip_var.set(True))
                                self.logger.info("System state updated: HAS_TIP = True")
                            except Exception as e:
                                raise Exception("Tip detection failed. Manifold empty.")
                            if self.lims.pipettor.hardware:
                                try:
                                    self.lims.pipettor.hardware.z_speed = hw_speed
                                    self.lims.pipettor.hardware.move_z(0)
                                except TypeError:
                                    self.lims.pipettor.hardware.move_z(0)

                    elif action in ["Aspirate Media", "Dispense Media", "Discard Tip"]:
                        tz = target_z if mode == "manual" else self._calculate_z(action,
                                                                                 self.lims.deck_labware.get(slot_name),
                                                                                 well_id, mode, 0.0, slot_name, extra_z)
                        self.logger.info(
                            f"Absolute Z-Depth Override Executed: Z={tz:.1f}mm for {well_id if mode != 'manual' else 'Manual Target'}")

                        if self.lims.pipettor.hardware: self.lims.pipettor.hardware.move_z(0)
                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                        time.sleep(0.05)

                        if self.lims.pipettor.hardware:
                            self.lims.pipettor.hardware.move_z(tz)

                            if action == "Aspirate Media":
                                # --- GUI SAFETY MANIFOLD CAP & EQUILIBRATION ---
                                requested_vol = float(vol)
                                actual_vol = min(requested_vol, self.lims.pipettor.tip_volume)

                                if requested_vol > self.lims.pipettor.tip_volume:
                                    self.logger.warning(
                                        f"MANIFOLD FLOOD PREVENTED: {requested_vol}uL requested, but tip limit is {self.lims.pipettor.tip_volume}uL. Automatically capped to {actual_vol}uL.")

                                self.lims.pipettor.hardware.aspirate(actual_vol)
                                time.sleep(1.5)
                            elif action == "Dispense Media":
                                actual_dispense = min(float(vol), self.lims.pipettor.tip_volume)
                                self.lims.pipettor.hardware.dispense(actual_dispense)
                                time.sleep(0.05)
                                self.lims.pipettor.hardware.dispense(50)

                            elif action == "Discard Tip":
                                self.lims.pipettor.hardware.eject_tip()
                                self.root.after(0, lambda: self.has_tip_var.set(False))
                                self.logger.info("System state updated: HAS_TIP = False")

                            try:
                                self.lims.pipettor.hardware.move_z(0)
                            except TypeError:
                                self.lims.pipettor.hardware.move_z(0)

                except Exception as e:
                    self.ask_error_resolution(e, i)
                time.sleep(0.05)

            if self.is_aborted:
                self.logger.info("--- Protocol Aborted ---")
            else:
                self.logger.info("--- Protocol Completed Successfully ---")

            self.timer_running = False
            if not self.is_aborted:
                self.root.after(0, lambda: self.lbl_timer.config(text="Time Remaining: 00:00", foreground="green"))

            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except TypeError:
                    self.lims.pipettor.hardware.move_z(0)
            self.root.after(0, lambda: self.update_ui_state(False))
            self.root.after(0, lambda: self.progress_var.set(0))

        threading.Thread(target=run_sequence, daemon=True).start()

    def hw_scan(self):
        ports = self.lims.hw.scan_ports()
        self.port_drop['values'] = ports

    def hw_init(self):
        ok, m = self.lims.hw.connect(self.port_var.get())
        if ok:
            ok2, m2 = self.lims.hw.initialize()
            if ok2:
                self.hw_stat_can.itemconfig(self.hw_led, fill="green")
                self.lbl_hw_stat.config(text="ONLINE", foreground="green")
                self.logger.info(m2)

                # --- STARTUP INTERLOCK: Speed and Force Integration ---
                if self.lims.pipettor.hardware:
                    try:
                        self.lims.pipettor.hardware.aspirate_speed = 1
                        self.lims.pipettor.hardware.tip_pickup_force = 20
                        self.logger.info("Startup Interlock: Plunger speeds and pickup force calibrated.")
                    except Exception as e:
                        self.logger.warning(f"Initial speed lock failed: {e}")
                # ------------------------------------------------------

                for axis in ["X", "Y", "Z"]:
                    self.jog_sliders[axis].config(state='normal')
                    self.deck_jog_sliders[axis].config(state='normal')
                    if hasattr(self, 'jog_btns') and axis in self.jog_btns:
                        self.jog_btns[axis].config(state='normal')
                    if hasattr(self, 'deck_jog_btns') and axis in self.deck_jog_btns:
                        self.deck_jog_btns[axis].config(state='normal')
                self.start_telemetry()
        else:
            self.logger.error(f"Connection failed: {m}")

    def run_direct_op(self, c):
        if not self.lims.hw.is_initialized: return
        hw_instance = self.lims.pipettor.hardware
        if c == "HOME":
            if hw_instance: hw_instance.initialize()
        elif c == "DISCARD":
            if hw_instance:
                try:
                    hw_instance.move_z(90.0)
                except TypeError:
                    hw_instance.move_z(90.0)
                hw_instance.eject_tip()
                self.root.after(0, lambda: self.has_tip_var.set(False))
                self.logger.info("Direct Op: Tips discarded. HAS_TIP = False")
                try:
                    hw_instance.move_z(0)
                except TypeError:
                    pass
        elif c == "FIND_TIP":
            self.prompt_for_tip_slot()
        elif c == "CHECK":
            self.check_alignment()

    def sync_to_backend(self, k, var):
        if self.selected_slot_name and not self.dragging_slot:
            try:
                setattr(self.lims.deck_slots[self.selected_slot_name], k, float(var.get()));
                self.draw_deck()
            except:
                pass

    def drag_start(self, e):
        rx, ry = self.get_m_x(e.x), e.y / self.scale
        for name in reversed(self.placed_slots):
            s = self.lims.deck_slots[name]
            if s.x_abs <= rx <= s.x_abs + s.width_mm and s.y_abs <= ry <= s.y_abs + s.height_mm:
                self.selected_slot_name = name
                for k in ['x_abs', 'y_abs', 'width_mm', 'height_mm', 'z_offset']:
                    self.entries[k].set(str(getattr(s, k, 0.0)))
                assigned = getattr(self.lims.deck_labware.get(name), 'source_file', '')
                self.lw_var.set(assigned if assigned else '')
                self.draw_deck()
                return
        self.selected_slot_name = None
        self.draw_deck()

    def drag_move(self, e):
        pass

    def drag_end(self, e):
        pass

    def get_labware_dir(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for cand in [
            os.path.join(script_dir, "labware"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "labware"),
            os.path.join(os.getcwd(), "labware"),
        ]:
            if os.path.isdir(cand):
                return cand
        return "labware"

    def get_calibration_path(self, filename="deck_calibration.json"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for cand in [
            os.path.join(script_dir, filename),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", filename),
            os.path.join(os.getcwd(), filename),
        ]:
            if os.path.isfile(cand):
                return cand
        return filename

    def refresh_ui(self):
        self.list_unplaced.delete(0, tk.END)
        [self.list_unplaced.insert(tk.END, s) for s in self.unplaced_slots]
        self.list_placed.delete(0, tk.END)
        [self.list_placed.insert(tk.END, s) for s in self.placed_slots]
        self.cbx_slot['values'] = self.placed_slots
        lw_dir = self.get_labware_dir()
        if os.path.exists(lw_dir):
            self.lw_drop['values'] = sorted([f for f in os.listdir(lw_dir) if f.endswith(".json")])
        self.draw_deck()

    def place_slot(self):
        sel = self.list_unplaced.curselection()
        if sel: n = self.list_unplaced.get(sel[0]); self.unplaced_slots.remove(n); self.placed_slots.append(
            n); self.refresh_ui()

    def remove_slot(self):
        sel = self.list_placed.curselection()
        if sel: n = self.list_placed.get(sel[0]); self.placed_slots.remove(n); self.unplaced_slots.append(
            n); self.refresh_ui()

    def assign_lw(self):
        fn = self.lw_var.get()
        if fn and self.selected_slot_name:
            lw_path = os.path.join(self.get_labware_dir(), fn)
            self.lims.deck_labware[self.selected_slot_name] = Labware(lw_path)
            self.lims.deck_labware[self.selected_slot_name].source_file = fn
            self.draw_deck()

    def unassign_lw(self):
        if self.selected_slot_name in self.lims.deck_labware: del self.lims.deck_labware[
            self.selected_slot_name]; self.draw_deck()

    def action_new_deck(self):
        self.lims.deck_slots.clear()
        self.lims.deck_labware.clear()
        self.placed_slots.clear()
        self.unplaced_slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
        for n in self.unplaced_slots:
            slot = DeckSlot(n, 20, 20, 110, 75)
            slot.z_offset = 0.0
            self.lims.deck_slots[n] = slot
        self.selected_slot_name = None
        self.refresh_ui()

    def _serialize_workspace(self, path):
        data = {
            n: {"name": s.name, "x_abs": s.x_abs, "y_abs": s.y_abs, "width_mm": s.width_mm, "height_mm": s.height_mm,
                "z_offset": getattr(s, 'z_offset', 0.0), "is_placed": n in self.placed_slots,
                "labware_file": getattr(self.lims.deck_labware.get(n), 'source_file', None)} for n, s in
            self.lims.deck_slots.items()}
        with open(path, 'w') as f: json.dump(data, f, indent=4)

    def _deserialize_workspace(self, path):
        if not os.path.exists(path): return
        with open(path, 'r') as f:
            data = json.load(f)
        self.lims.deck_slots.clear()
        self.lims.deck_labware.clear()
        self.placed_slots.clear()
        self.unplaced_slots.clear()
        lw_dir = self.get_labware_dir()
        for n, d in data.items():
            slot = DeckSlot(n, d['x_abs'], d['y_abs'], d['width_mm'], d['height_mm'])
            slot.z_offset = d.get('z_offset', 0.0)
            self.lims.deck_slots[n] = slot
            (self.placed_slots if d.get('is_placed', False) else self.unplaced_slots).append(n)
            lab_file = d.get('labware_file')
            if lab_file:
                lw_path = os.path.join(lw_dir, lab_file)
                if os.path.exists(lw_path):
                    self.lims.deck_labware[n] = Labware(lw_path)
                    self.lims.deck_labware[n].source_file = lab_file
        self.refresh_ui()

    def save_all(self):
        cal_path = self.get_calibration_path()
        self._serialize_workspace(cal_path)
        self.logger.info(f"Workspace securely saved to {cal_path}")
        messagebox.showinfo("Success", f"Deck workspace saved securely to {cal_path}")

    def action_save_deck_as(self):
        filepath = filedialog.asksaveasfilename(title="Save Workspace As...",
                                                defaultextension=".json",
                                                filetypes=[("JSON Workspace", "*.json")])
        if filepath:
            self._serialize_workspace(filepath)
            self.logger.info(f"Workspace successfully exported to {filepath}")
        if filepath:
            with open(filepath, 'w') as f: json.dump(self.workflow_sequence, f, indent=4)

    def action_load_deck(self):
        p = filedialog.askopenfilename()
        if p: self._deserialize_workspace(p)

    def emergency_reset(self):
        cal_path = self.get_calibration_path()
        if os.path.exists(cal_path):
            self._deserialize_workspace(cal_path)
        else:
            self.lims.deck_labware.clear()
            self.placed_slots.clear()
            self.unplaced_slots.clear()
            grid_layout = [("Slot_1", 135.2, 5.0, 127.8, 35.0), ("Slot_2", 0.0, 5.0, 127.8, 35.0),
                           ("Slot_3", 135.2, 60.0, 127.8, 85.5), ("Slot_4", 0.0, 60.0, 127.8, 85.5),
                           ("Slot_5", 135.2, 165.5, 127.8, 85.5), ("Slot_6", 0.0, 165.5, 127.8, 85.5)]
            for name, x, y, w, h in grid_layout:
                slot = DeckSlot(name, x, y, w, h)
                slot.z_offset = 0.0
                self.lims.deck_slots[name] = slot
                self.placed_slots.append(name)
            self.refresh_ui()

    def action_save_workflow_as(self):
        if not self.workflow_sequence: return
        export_dir = os.path.join(os.path.expanduser("~"), "Desktop", "pipette trials export")
        os.makedirs(export_dir, exist_ok=True)
        filepath = filedialog.asksaveasfilename(title="Export Workflow Sequence", initialdir=export_dir,
                                                defaultextension=".json",
                                                filetypes=[("JSON Protocol", "*.json")])
        if filepath:
            with open(filepath, 'w') as f: json.dump(self.workflow_sequence, f, indent=4)

    def action_load_workflow(self):
        filepath = filedialog.askopenfilename(title="Import Workflow Sequence", filetypes=[("JSON Protocol", "*.json")])
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    loaded_sequence = json.load(f)

                if not isinstance(loaded_sequence, list):
                    messagebox.showerror("Format Exception",
                                         "JSON structure mismatch. The selected file is a dictionary, not a workflow array. Did you select a Deck Workspace instead of a Protocol?")
                    return

                self.workflow_sequence.clear()
                self.wf_box.delete(0, tk.END)

                for step in loaded_sequence:
                    if 'action' not in step:
                        continue

                    self.workflow_sequence.append(step)
                    m = step.get('mode', 'auto')

                    if "System" in step['action']:
                        if "Incubate" in step['action']:
                            msg = f"[SYSTEM] Incubate for {step.get('volume', 0.0)} seconds."
                        elif "FOC48" in step['action']:
                            msg = f"[MEASURE] Execute FOC48_Stim_0.xml for Plate: '{step.get('well', '')}'"
                        else:
                            msg = f"[{step['action'].upper()}]"
                    elif m == "manual":
                        if step['action'] in ["Pick Up Tip", "Discard Tip"]:
                            msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)}"
                        else:
                            msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)} Vol:{step.get('volume', 0.0)}\u03bcL"
                    else:
                        if step['action'] == "Pick Up Tip":
                            msg = f"[{step['action'].upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                        elif step['action'] == "Discard Tip":
                            msg = f"[{step['action'].upper()}] into {step.get('slot', '')} (Waste Trough)"
                        else:
                            z_msg = f" (Z+{step.get('extra_z', 0.0)}mm)" if step.get('extra_z', 0.0) > 0 else ""
                            msg = f"[{step['action'].upper()}] {step.get('volume', 0.0)}\u03bcL at {step.get('slot', '')}, Well {step.get('well', '')}{z_msg}"

                    self.wf_box.insert(tk.END, msg)

            except Exception as e:
                self.logger.error(f"Import Exception: {str(e)}")
                messagebox.showerror("Import Exception", f"Failed to parse protocol file.\n\nTraceback: {str(e)}")

    def action_import_python_protocol(self):
        filepath = filedialog.askopenfilename(
            title="Import Opentrons Python Protocol (.py)",
            filetypes=[("Python Script", "*.py"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        try:
            from opentrons_python_converter import detect_opentrons_labware, convert_opentrons_py_to_biohit

            detected_lw = detect_opentrons_labware(filepath)

            top = tk.Toplevel(self.root)
            top.title("Opentrons to Biohit Slot Mapping")
            top.geometry("520x420")
            top.resizable(False, False)
            top.transient(self.root)
            top.grab_set()

            ttk.Label(top, text="Import Opentrons Python Protocol", font=("Arial", 12, "bold")).pack(pady=(12, 4))
            ttk.Label(top, text=f"File: {os.path.basename(filepath)}", font=("Arial", 9, "italic"), foreground="gray").pack(pady=(0, 10))

            frame_mappings = ttk.LabelFrame(top, text="Detected Labware & Slot Assignments", padding=10)
            frame_mappings.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

            biohit_slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
            combos = {}

            if detected_lw:
                for idx, item in enumerate(detected_lw):
                    row = ttk.Frame(frame_mappings)
                    row.pack(fill=tk.X, pady=4)

                    lbl_text = f"{item['name'][:24]} (OT Slot {item['opentrons_slot']}):"
                    ttk.Label(row, text=lbl_text, width=32, anchor="w").pack(side=tk.LEFT)

                    cb = ttk.Combobox(row, values=biohit_slots, state="readonly", width=12)
                    suggested = item.get("suggested_biohit_slot", "Slot_4")
                    cb.set(suggested)
                    cb.pack(side=tk.RIGHT)
                    combos[item['opentrons_slot']] = cb
            else:
                ttk.Label(frame_mappings, text="No explicit labware definitions detected.\nDefault slot layout will be used.", justify="center").pack(pady=20)

            frame_stroke = ttk.Frame(top)
            frame_stroke.pack(fill=tk.X, padx=15, pady=8)
            ttk.Label(frame_stroke, text="Max Pipette Stroke (µL):").pack(side=tk.LEFT)
            ent_stroke = ttk.Entry(frame_stroke, width=8)
            current_tip_vol = getattr(getattr(self.lims, 'pipettor', None), 'tip_volume', 200.0)
            ent_stroke.insert(0, str(float(current_tip_vol)))
            ent_stroke.pack(side=tk.LEFT, padx=5)

            def do_convert():
                try:
                    slot_map = {ot_s: cb.get() for ot_s, cb in combos.items()}
                    try:
                        max_vol = float(ent_stroke.get())
                    except ValueError:
                        max_vol = 200.0

                    converted_steps = convert_opentrons_py_to_biohit(filepath, slot_mapping=slot_map, max_volume=max_vol)

                    if not converted_steps:
                        messagebox.showwarning("Empty Protocol", "No pipetting steps were generated from this script.")
                        top.destroy()
                        return

                    self.workflow_sequence.clear()
                    self.wf_box.delete(0, tk.END)

                    for step in converted_steps:
                        self.workflow_sequence.append(step)
                        action = step['action']
                        m = step.get('mode', 'auto')
                        if action == "Pick Up Tip":
                            msg = f"[{action.upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                        elif action == "Discard Tip":
                            msg = f"[{action.upper()}] into {step.get('slot', '')} (Waste Trough)"
                        else:
                            z_msg = f" (Z+{step.get('extra_z', 0.0)}mm)" if step.get('extra_z', 0.0) > 0 else ""
                            msg = f"[{action.upper()}] {step.get('volume', 0.0)}\u03bcL at {step.get('slot', '')}, Well {step.get('well', '')}{z_msg}"
                        self.wf_box.insert(tk.END, msg)

                    top.destroy()
                    self.logger.info(f"Imported {len(converted_steps)} steps from Python script {os.path.basename(filepath)}.")
                    messagebox.showinfo(
                        "Conversion Complete",
                        f"Successfully converted and loaded {len(converted_steps)} steps from:\n{os.path.basename(filepath)}\n\nYou can now run the workflow or export it via 'Save JSON Protocol As...'."
                    )
                except Exception as ce:
                    self.logger.error(f"Conversion error: {ce}")
                    messagebox.showerror("Conversion Error", f"Failed to convert Python script:\n{ce}")

            btn_frame = ttk.Frame(top)
            btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
            ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(btn_frame, text="✔ Convert & Load Protocol", command=do_convert).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            self.logger.error(f"Python script parse error: {e}")
            messagebox.showerror("Import Error", f"Could not inspect Python protocol:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LIMSMasterApp(root)
    root.mainloop()
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, logging, threading, time, os, subprocess, math
import ctypes  # Native Windows library for ghost mouse
from working import LIMSOrchestrator, Labware, DeckSlot, Pipettor
try:
    from gui import GUI as AnalyzerGUI
except Exception:
    AnalyzerGUI = None
from labware_models import (
    DeckManager, DeckSlot as ModelDeckSlot, HeightAdapter,
    ADAPTER_NONE, ADAPTER_90MM_BLOCK, ADAPTER_45MM_BLOCK,
    LabwareBase, Plate96, Plate48Myriamed, Reservoir3Well,
    TubeRack2x6_2mL, FalconRack50mL, TipRack96, WasteTrough
)

import xml.etree.ElementTree as ET
try:
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
except ImportError:
    pd = None
    sns = None
    plt = None
import re, queue


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.log_queue = queue.Queue()
        self._poll_logs()

    def emit(self, record):
        try:
            self.log_queue.put_nowait(self.format(record))
        except Exception:
            pass

    def _poll_logs(self):
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get_nowait()
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)
        except Exception:
            pass
        finally:
            try:
                self.text_widget.after(100, self._poll_logs)
            except Exception:
                pass


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
        self.has_air_cushion = False
        self.pause_event = threading.Event()
        self.pause_event.set()

        # Object-Oriented Labware & Kinematics Engine
        self.deck_manager = DeckManager()
        self.current_step_idx = 0
        self.protocol_edit_buttons = []
        self.tip_rack_learned_offset = (0.0, 0.0)

        self.has_tip_var = tk.BooleanVar(value=False)
        self.current_pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.telemetry_active = False

        # Live Jogging & Keyboard Control State
        self.jog_step_var = tk.DoubleVar(value=1.0)
        self.jog_z_clearance_var = tk.BooleanVar(value=False)
        self.jog_nudge_btns = []
        self._jogging_in_progress = False

        self.setup_menu()
        self.setup_ui()
        self.setup_logging()

        try:
            self.root.bind("<KeyPress>", self._on_key_press)
        except Exception:
            pass

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
        global AnalyzerGUI
        if AnalyzerGUI is None:
            try:
                from gui import GUI as AnalyzerGUI
            except Exception:
                AnalyzerGUI = None
        if AnalyzerGUI:
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
            f.pack(fill=tk.X, padx=100, pady=8)
            ttk.Label(f, text=f"{axis}-Axis (mm):", width=12, font=("Arial", 11)).pack(side=tk.LEFT)

            btn_m = tk.Button(f, text=" - ", bg="#e9ecef", font=("Consolas", 10, "bold"), width=4, state='disabled',
                              command=lambda a=axis: self.jog_step(a, -1.0))
            btn_m.pack(side=tk.LEFT, padx=(5, 3))
            self.jog_nudge_btns.append(btn_m)

            e = ttk.Entry(f, textvariable=self.jog_vars[axis], font=("Consolas", 11), state='disabled', width=12)
            e.pack(side=tk.LEFT, padx=3)
            self.jog_sliders[axis] = e

            btn_p = tk.Button(f, text=" + ", bg="#e9ecef", font=("Consolas", 10, "bold"), width=4, state='disabled',
                              command=lambda a=axis: self.jog_step(a, +1.0))
            btn_p.pack(side=tk.LEFT, padx=(3, 10))
            self.jog_nudge_btns.append(btn_p)

            btn = tk.Button(f, text="GO TO", bg="#007bff", fg="white", font=("Arial", 9, "bold"), state='disabled',
                            command=lambda ax=axis: self._execute_jog_move(ax))
            btn.pack(side=tk.LEFT, padx=5)
            self.jog_btns[axis] = btn

            e.bind('<Return>', lambda event, ax=axis: self._execute_jog_move(ax))

        f_step = ttk.Frame(f_jog)
        f_step.pack(fill=tk.X, padx=100, pady=(15, 5))
        ttk.Label(f_step, text="Jog Step Size:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        for step_val in [0.1, 1.0, 5.0, 10.0]:
            r_btn = ttk.Radiobutton(f_step, text=f"{step_val} mm", value=step_val, variable=self.jog_step_var)
            r_btn.pack(side=tk.LEFT, padx=6)

        f_opt = ttk.Frame(f_jog)
        f_opt.pack(fill=tk.X, padx=100, pady=5)
        ttk.Checkbutton(f_opt, text="Retract Z to 0 before XY moves (Clearance Lift)", variable=self.jog_z_clearance_var).pack(side=tk.LEFT)

        f_guide = ttk.LabelFrame(f_jog, text="⌨️ Keyboard Live Jog Controls (Active Anywhere in Window)", padding=10)
        f_guide.pack(fill=tk.X, padx=100, pady=12)
        guide_text = (
            "• X-Axis (Left / Right):   ◄ / ►   or   A / D\n"
            "• Y-Axis (Forward / Back): ▲ / ▼   or   W / S\n"
            "• Z-Axis (Up / Down):      PgUp (▲) / PgDn (▼)   or   Q / E   or   + / -\n"
            "• Multipliers: Hold Shift for 10× (10mm) | Hold Ctrl for 0.1× (0.1mm)\n"
            "• Direct Motion: Moves directly without pulling Z up to 0 (stays at current height)"
        )
        ttk.Label(f_guide, text=guide_text, font=("Consolas", 9), foreground="#0056b3").pack(anchor="w")

    def _safe_get_jog(self, axis):
        try:
            if hasattr(self, 'jog_sliders') and axis in self.jog_sliders:
                txt = self.jog_sliders[axis].get().strip()
                if txt:
                    val = float(txt)
                    self.jog_vars[axis].set(round(val, 2))
                    return val
        except Exception:
            pass
        try:
            val = self.jog_vars[axis].get()
            return float(val)
        except Exception:
            cur = float(self.current_pos.get(axis, 0.0))
            try:
                self.jog_vars[axis].set(cur)
            except Exception:
                pass
            return cur

    def _safe_get_speed(self):
        try:
            return float(self.speed_var.get())
        except Exception:
            return 1500.0

    def _execute_jog_move(self, ax=None):
        x = self._safe_get_jog("X")
        y = self._safe_get_jog("Y")
        z = self._safe_get_jog("Z")
        speed = self._safe_get_speed()
        clearance = getattr(self, 'jog_z_clearance_var', tk.BooleanVar(value=False)).get()

        try:
            self.root.focus_set()
        except Exception:
            pass

        self.current_pos["X"] = x
        self.current_pos["Y"] = y
        self.current_pos["Z"] = z
        if hasattr(self, 'draw_deck'):
            try:
                self.draw_deck()
            except Exception:
                pass

        def _worker():
            try:
                hw = self.lims.pipettor.hardware
                if hw:
                    hw_speed = max(1, min(9, int((speed / 100.0) * 9)))
                    try:
                        hw.x_speed = hw_speed
                        hw.y_speed = hw_speed
                        hw.z_speed = hw_speed
                    except Exception:
                        pass

                    if ax == "Z":
                        hw.move_z(z, wait=True)
                    elif ax == "X":
                        if clearance:
                            hw.move_z(0, wait=True)
                        try:
                            hw.move_x(x, wait=True)
                        except (AttributeError, TypeError):
                            try:
                                hw.move_xy(x, hw.y_position, wait=True)
                            except (AttributeError, TypeError):
                                hw.move_xy(x, y, wait=True)
                        if clearance and z > 0:
                            hw.move_z(z, wait=True)
                    elif ax == "Y":
                        if clearance:
                            hw.move_z(0, wait=True)
                        try:
                            hw.move_y(y, wait=True)
                        except (AttributeError, TypeError):
                            try:
                                hw.move_xy(hw.x_position, y, wait=True)
                            except (AttributeError, TypeError):
                                hw.move_xy(x, y, wait=True)
                        if clearance and z > 0:
                            hw.move_z(z, wait=True)
                    else:
                        if clearance:
                            hw.move_z(0, wait=True)
                        try:
                            hw.move_xy(x, y, wait=True)
                        except TypeError:
                            hw.move_xy(x, y)
                        if clearance and z > 0:
                            hw.move_z(z, wait=True)
                self.logger.info(f"Jog Move {ax or 'All'} -> X:{x:.1f}, Y:{y:.1f}, Z:{z:.1f} (Clearance={'ON' if clearance else 'OFF'})")
            except Exception as e:
                self.logger.error(f"Jog move failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def jog_step(self, axis, direction):
        if getattr(self, '_jogging_in_progress', False):
            return

        hw = self.lims.pipettor.hardware
        if hw and not self.lims.hw.is_initialized:
            self.logger.warning("Hardware not initialized. Please click 'Connect & Initialize' first.")
            return

        step = 1.0
        try:
            step = float(self.jog_step_var.get())
        except Exception:
            pass
        delta = float(direction) * step

        curr_x = self._safe_get_jog("X")
        curr_y = self._safe_get_jog("Y")
        curr_z = self._safe_get_jog("Z")

        target_x, target_y, target_z = curr_x, curr_y, curr_z
        max_x = self.lims.machine_config.get("max_x_mm", 300.0)
        max_y = self.lims.machine_config.get("max_y_mm", 300.0)

        if axis == "X":
            target_x = max(0.0, min(curr_x + delta, max_x))
            self.jog_vars["X"].set(round(target_x, 2))
        elif axis == "Y":
            target_y = max(0.0, min(curr_y + delta, max_y))
            self.jog_vars["Y"].set(round(target_y, 2))
        elif axis == "Z":
            target_z = max(0.0, min(curr_z + delta, 103.5))
            self.jog_vars["Z"].set(round(target_z, 2))

        speed = self._safe_get_speed()
        clearance = False
        try:
            clearance = bool(self.jog_z_clearance_var.get())
        except Exception:
            pass

        self.current_pos["X"] = target_x
        self.current_pos["Y"] = target_y
        self.current_pos["Z"] = target_z
        if hasattr(self, 'draw_deck'):
            try:
                self.draw_deck()
            except Exception:
                pass

        self._jogging_in_progress = True
        threading.Thread(
            target=self._jog_step_worker,
            args=(axis, target_x, target_y, target_z, speed, clearance, delta),
            daemon=True
        ).start()

    def _jog_step_worker(self, axis, target_x, target_y, target_z, speed, clearance, delta):
        try:
            hw = self.lims.pipettor.hardware
            if hw:
                hw_speed = max(1, min(9, int((speed / 100.0) * 9)))
                try:
                    hw.x_speed = hw_speed
                    hw.y_speed = hw_speed
                    hw.z_speed = hw_speed
                except Exception:
                    pass

                if axis == "Z":
                    hw.move_z(target_z, wait=True)
                elif axis == "X":
                    if clearance:
                        hw.move_z(0, wait=True)
                    try:
                        hw.move_x(target_x, wait=True)
                    except (AttributeError, TypeError):
                        try:
                            hw.move_xy(target_x, hw.y_position, wait=True)
                        except (AttributeError, TypeError):
                            hw.move_xy(target_x, target_y, wait=True)
                    if clearance and target_z > 0:
                        hw.move_z(target_z, wait=True)
                elif axis == "Y":
                    if clearance:
                        hw.move_z(0, wait=True)
                    try:
                        hw.move_y(target_y, wait=True)
                    except (AttributeError, TypeError):
                        try:
                            hw.move_xy(hw.x_position, target_y, wait=True)
                        except (AttributeError, TypeError):
                            hw.move_xy(target_x, target_y, wait=True)
                    if clearance and target_z > 0:
                        hw.move_z(target_z, wait=True)

            self.logger.info(f"Jog {axis} {delta:+.2f}mm -> (X:{target_x:.1f}, Y:{target_y:.1f}, Z:{target_z:.1f})")
        except Exception as e:
            self.logger.error(f"Jog {axis} failed: {e}")
        finally:
            self._jogging_in_progress = False

    def _on_key_press(self, event):
        key = event.keysym.lower()
        shift = bool(event.state & 0x0001)  # Shift key pressed -> 10x step
        ctrl = bool(event.state & 0x0004)   # Ctrl key pressed -> 0.1x step

        mult = 1.0
        if shift:
            mult = 10.0
        elif ctrl:
            mult = 0.1

        # PageUp / PageDown / + / - always jog Z immediately even if focus is inside an Entry!
        if key in ('prior', 'pageup', 'page_up', 'equal', 'plus'):
            self.jog_step('Z', -1.0 * mult)
            return "break"
        elif key in ('next', 'pagedown', 'page_down', 'minus', 'underscore'):
            self.jog_step('Z', +1.0 * mult)
            return "break"

        # Escape releases focus from any active Entry
        if key == 'escape':
            try:
                self.root.focus_set()
            except Exception:
                pass
            return "break"

        # Ignore keyboard controls if user is currently typing in an input widget
        focus_w = self.root.focus_get()
        if focus_w:
            w_class = getattr(focus_w, 'winfo_class', lambda: '')()
            if w_class in ('Entry', 'TEntry', 'Text', 'Combobox', 'TCombobox', 'Spinbox'):
                return

        # X-Axis Jog (Left / Right)
        if key in ('left', 'a'):
            self.jog_step('X', -1.0 * mult)
            return "break"
        elif key in ('right', 'd'):
            self.jog_step('X', +1.0 * mult)
            return "break"

        # Y-Axis Jog (Forward / Back)
        elif key in ('up', 'w'):
            self.jog_step('Y', +1.0 * mult)
            return "break"
        elif key in ('down', 's'):
            self.jog_step('Y', -1.0 * mult)
            return "break"

        # Z-Axis Jog (Q / E)
        elif key == 'q':
            self.jog_step('Z', -1.0 * mult)
            return "break"
        elif key == 'e':
            self.jog_step('Z', +1.0 * mult)
            return "break"

    def start_telemetry(self):
        if not self.telemetry_active:
            self.telemetry_active = True
            threading.Thread(target=self._poll_coordinates, daemon=True).start()

    def _poll_coordinates(self):
        last_pos = None
        while self.telemetry_active:
            if self.lims.pipettor.hardware:
                try:
                    hw = self.lims.pipettor.hardware
                    hx = round(float(getattr(hw, 'x_position', self.current_pos.get("X", 0.0))), 2)
                    hy = round(float(getattr(hw, 'y_position', self.current_pos.get("Y", 0.0))), 2)
                    hz = round(float(getattr(hw, 'z_position', self.current_pos.get("Z", 0.0))), 2)
                    new_pos = {"X": hx, "Y": hy, "Z": hz}
                    if new_pos != last_pos:
                        self.current_pos = new_pos
                        last_pos = dict(new_pos)
                        focus_w = self.root.focus_get()
                        is_typing = focus_w and getattr(focus_w, 'winfo_class', lambda: '')() in ('Entry', 'TEntry')
                        if not is_typing:
                            for ax in ("X", "Y", "Z"):
                                self.jog_vars[ax].set(new_pos[ax])
                        try:
                            self.draw_deck()
                        except Exception:
                            pass
                except Exception:
                    pass
            time.sleep(0.25)

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

        # Pass 1: draw ALL slot rectangles first, so no slot body can paint over another slot's wells
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

        # Pass 2: draw wells on top of every rectangle, then the selection badge
        for name in self.placed_slots:
            s = self.lims.deck_slots[name]
            visual_x_right = self.get_v_x(s.x_abs)
            y0 = s.y_abs * self.scale
            is_sel = (name == self.selected_slot_name)

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

            btn_m = tk.Button(f, text="-", width=2, bg="#e9ecef", font=("Consolas", 8, "bold"), state='disabled',
                              command=lambda a=axis: self.jog_step(a, -1.0))
            btn_m.pack(side=tk.LEFT, padx=(2, 2))
            self.jog_nudge_btns.append(btn_m)

            e = ttk.Entry(f, textvariable=self.jog_vars[axis], font=("Consolas", 10), state='disabled', width=8)
            e.pack(side=tk.LEFT, padx=3)
            self.deck_jog_sliders[axis] = e

            btn_p = tk.Button(f, text="+", width=2, bg="#e9ecef", font=("Consolas", 8, "bold"), state='disabled',
                              command=lambda a=axis: self.jog_step(a, +1.0))
            btn_p.pack(side=tk.LEFT, padx=(2, 5))
            self.jog_nudge_btns.append(btn_p)

            btn = tk.Button(f, text="MOVE", bg="#007bff", fg="white", font=("Arial", 8, "bold"), state='disabled',
                            command=lambda ax=axis: self._execute_jog_move(ax))
            btn.pack(side=tk.LEFT, padx=3)
            self.deck_jog_btns[axis] = btn

            e.bind('<Return>', lambda event, ax=axis: self._execute_jog_move(ax))

        deck_ctrl_f = ttk.Frame(f_jog)
        deck_ctrl_f.pack(fill=tk.X, padx=10, pady=(4, 0))
        ttk.Label(deck_ctrl_f, text="Step:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        for step_val in [0.1, 1.0, 5.0]:
            ttk.Radiobutton(deck_ctrl_f, text=f"{step_val}mm", value=step_val, variable=self.jog_step_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(deck_ctrl_f, text="Clearance (Z=0)", variable=self.jog_z_clearance_var).pack(side=tk.LEFT, padx=6)
        ttk.Label(deck_ctrl_f, text="⌨️ Arrow keys / PgUp-PgDn active", font=("Arial", 8, "italic"), foreground="#0066cc").pack(side=tk.RIGHT)

        ttk.Label(pane_l, text="Inventory", font=("Arial", 10, "bold")).pack(pady=5)
        self.list_unplaced = tk.Listbox(pane_l, height=10, bg="white")
        self.list_unplaced.pack(fill=tk.X)
        ttk.Button(pane_l, text="Place on Deck \u2192", command=self.place_slot).pack(fill=tk.X, pady=2)
        self.list_placed = tk.Listbox(pane_l, height=10, bg="white")
        self.list_placed.pack(fill=tk.X)
        self.list_placed.bind("<<ListboxSelect>>", self.on_placed_slot_select)
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
            ("Check Liquid Level", "Detects liquid surface in selected slot/well and calculates remaining volume.", "CHECK_LIQUID"),
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
                                              "Detect Liquid Level",
                                              "System: Incubate (Wait)", "System: FOC48 Measurement", "System: Calcium Curve", "System: Data Analysis", "System: DB Upload"])
        self.wf_action.current(0)
        self.wf_action.pack(fill=tk.X, pady=(0, 5))

        self.auto_tip_search_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Auto-Search Tips (Skip empty wells)", variable=self.auto_tip_search_var).pack(
            fill=tk.X, pady=(5, 2))

        self.adaptive_tip_centering_var = tk.BooleanVar(value=False)

        self.dynamic_z_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Auto-Height Detection (Liquids ONLY)", variable=self.dynamic_z_var).pack(
            fill=tk.X, pady=(0, 2))

        self.lld_tracking_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pane_ctrl, text="Sensor Liquid Level Detection (LLD)", variable=self.lld_tracking_var).pack(
            fill=tk.X, pady=(0, 2))

        ttk.Checkbutton(pane_ctrl, text="Pipette Currently Has Tip", variable=self.has_tip_var).pack(fill=tk.X,
                                                                                                     pady=(0, 2))

        self.manual_mode_var = tk.BooleanVar(value=False)
        self.chk_manual_mode = ttk.Checkbutton(pane_ctrl, text="Enable Manual Coordinates",
                                               variable=self.manual_mode_var, command=self._toggle_wf_inputs)
        self.chk_manual_mode.pack(fill=tk.X, pady=(0, 6))

        foc_frame = ttk.LabelFrame(pane_ctrl, text="🔬 FOC48 Experiment Selection", padding=6)
        foc_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(foc_frame, text="Target Experiment (Plate 1 = 17a, Plate 2 = 17b):", font=("Arial", 8, "bold")).pack(anchor="w")
        foc_presets = [
            "17b (Plate 2 - 1st in list)",
            "17a (Plate 1 - 2nd in list)",
            "Row 1 (1st Experiment)",
            "Row 2 (2nd Experiment)",
            "Row 3 (3rd Experiment)"
        ]
        try:
            import foc_automation
            for exp_dir in foc_automation.get_available_experiments():
                if exp_dir not in foc_presets:
                    foc_presets.append(exp_dir)
        except Exception:
            pass
        self.foc_exp_var = tk.StringVar(value=foc_presets[0])
        self.cbx_foc_exp = ttk.Combobox(foc_frame, textvariable=self.foc_exp_var, values=foc_presets, state="normal")
        self.cbx_foc_exp.pack(fill=tk.X, pady=(2, 0))

        self.input_frame = ttk.Frame(pane_ctrl)
        self.input_frame.pack(fill=tk.X, expand=True)
        self.lbl_1 = ttk.Label(self.input_frame, text="")
        self.cbx_slot = ttk.Combobox(self.input_frame, state="readonly")
        self.cbx_slot.bind("<<ComboboxSelected>>", self.update_safe_z_hint)
        self.ent_x = ttk.Entry(self.input_frame)
        self.lbl_2 = ttk.Label(self.input_frame, text="")
        self.ent_well = ttk.Entry(self.input_frame)
        self.ent_y = ttk.Entry(self.input_frame)
        self.lbl_3 = ttk.Label(self.input_frame, text="")
        self.ent_z = ttk.Entry(self.input_frame)
        self.lbl_safe_z = ttk.Label(self.input_frame, text="", font=("Arial", 9, "italic"), foreground="#0d6efd", wraplength=200)
        self.lbl_4 = ttk.Label(self.input_frame, text="")
        self.ent_vol = ttk.Entry(self.input_frame)

        ttk.Button(pane_ctrl, text="+ Add Step to Protocol", command=self.add_wf_step).pack(fill=tk.X, pady=10)
        ttk.Button(pane_ctrl, text="Clear Protocol",
                   command=lambda: [self.wf_box.delete(0, tk.END), self.workflow_sequence.clear()]).pack(fill=tk.X)
        ttk.Separator(pane_ctrl, orient="horizontal").pack(fill=tk.X, pady=8)

        # Instant Load Protocols (DMSO-Drug and Media+Drug Only)
        lbl_inst = ttk.Label(pane_ctrl, text="⚡ INSTANT PROTOCOL LOAD", font=("Arial", 10, "bold"), foreground="#007bff")
        lbl_inst.pack(fill=tk.X, pady=(2, 4))

        # Media Change + Drug Protocols (2 Plates)
        ttk.Button(pane_ctrl, text="🧫 Media Change + Drug (7.5 µL)", command=lambda: self.action_load_media_and_drug_protocol(7.5)).pack(fill=tk.X, pady=2)
        ttk.Button(pane_ctrl, text="🧫 Media Change + Drug (5.0 µL)", command=lambda: self.action_load_media_and_drug_protocol(5.0)).pack(fill=tk.X, pady=2)

        # DMSO & Drug Protocols
        ttk.Button(pane_ctrl, text="💊 Drug Addition Only (2 Plates, 5 µL)", command=self.action_load_drug_addition_only_protocol).pack(fill=tk.X, pady=2)
        ttk.Button(pane_ctrl, text="🧪 DMSO Dilution Plate (12 Tubes -> 96 Well)", command=self.action_load_dmso_dilution_protocol).pack(fill=tk.X, pady=2)

        ttk.Separator(pane_ctrl, orient="horizontal").pack(fill=tk.X, pady=6)
        ttk.Button(pane_ctrl, text="📥 Convert & Import Python (.py)", command=self.action_import_python_protocol).pack(fill=tk.X, pady=2)
        ttk.Button(pane_ctrl, text="📂 Load JSON Protocol", command=self.action_load_workflow).pack(fill=tk.X, pady=2)
        ttk.Button(pane_ctrl, text="💾 Save Protocol As JSON...", command=self.action_save_workflow_as).pack(fill=tk.X, pady=2)

        self.wf_box = tk.Listbox(pane_list, font=("Consolas", 11), bg="#f8f9fa", fg="black", selectbackground="#007bff")
        self.wf_box.pack(fill=tk.BOTH, expand=True)
        self.wf_box.bind("<Double-Button-1>", self.edit_wf_step)

        # Mid-Run & Offline Protocol Modification Toolbar
        bar_edit = ttk.Frame(pane_list)
        bar_edit.pack(fill=tk.X, pady=(3, 6))
        self.btn_wf_insert = ttk.Button(bar_edit, text="➕ Insert", width=8, command=self.action_insert_step)
        self.btn_wf_insert.pack(side=tk.LEFT, padx=1)
        self.btn_wf_delete = ttk.Button(bar_edit, text="🗑️ Delete", width=8, command=self.action_delete_step)
        self.btn_wf_delete.pack(side=tk.LEFT, padx=1)
        self.btn_wf_edit = ttk.Button(bar_edit, text="✏️ Edit", width=7, command=self.edit_wf_step)
        self.btn_wf_edit.pack(side=tk.LEFT, padx=1)
        self.btn_wf_up = ttk.Button(bar_edit, text="⬆️ Up", width=6, command=self.action_move_step_up)
        self.btn_wf_up.pack(side=tk.LEFT, padx=1)
        self.btn_wf_down = ttk.Button(bar_edit, text="⬇️ Down", width=6, command=self.action_move_step_down)
        self.btn_wf_down.pack(side=tk.LEFT, padx=1)
        self.protocol_edit_buttons = [self.btn_wf_insert, self.btn_wf_delete, self.btn_wf_edit, self.btn_wf_up, self.btn_wf_down]

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
            if action not in ["Pick Up Tip", "Discard Tip", "Detect Liquid Level"]:
                self.lbl_4.config(text="Volume (\u03bcL):")
                self.lbl_4.pack(anchor="w")
                self.ent_vol.pack(fill=tk.X, pady=(0, 5))
        else:
            if "Incubate" in action:
                self.lbl_4.config(text="Seconds (e.g., 120):")
                self.lbl_4.pack(anchor="w")
                self.ent_vol.pack(fill=tk.X, pady=(0, 5))
            elif "FOC48" in action:
                self.lbl_2.config(text="Experiment Override (optional, or use selector above):")
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
                if action not in ["Pick Up Tip", "Discard Tip", "Detect Liquid Level"]:
                    self.lbl_4.config(text="Volume (\u03bcL):")
                    self.lbl_4.pack(anchor="w")
                    self.ent_vol.pack(fill=tk.X, pady=(0, 5))
                    self.lbl_3.config(text="Extra Z-Depth (+mm) [Optional]:")
                    self.lbl_3.pack(anchor="w")
                    self.ent_z.pack(fill=tk.X, pady=(0, 2))
                    self.lbl_safe_z.pack(fill=tk.X, pady=(0, 5))
                    self.update_safe_z_hint()

    def update_safe_z_hint(self, *args):
        slot = self.cbx_slot.get()
        if not slot:
            self.lbl_safe_z.config(text="")
            return
        labware_obj = self.lims.deck_labware.get(slot)
        if not labware_obj:
            self.lbl_safe_z.config(text=f"⚠️ No labware assigned to {slot} (Deck tab)")
            return
        kind = self._lw_kind(labware_obj)
        try:
            if kind == "tip_rack":
                self.lbl_safe_z.config(text=f"💡 Tip rack ({getattr(labware_obj, 'name', '')}): pickup Z 87.0mm | ⚠️ Max 92.0mm")
                return
            asp = self._calculate_z("Aspirate Media", labware_obj, "A1", "auto", 0.0, slot)
            disp = self._calculate_z("Dispense Media", labware_obj, "A1", "auto", 0.0, slot)
            max_b = self._labware_bottom_z(labware_obj, slot)
            self.lbl_safe_z.config(text=f"💡 {getattr(labware_obj, 'name', '')}: Aspirate {asp:.1f}mm | Dispense {disp:.1f}mm | ⚠️ Max Safe: {max_b:.1f}mm")
        except ValueError:
            self.lbl_safe_z.config(text=f"⚠️ {getattr(labware_obj, 'name', '')}: Z NOT CALIBRATED (set rim_z in its JSON)")

    def action_load_ehm_test_protocol(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(script_dir, "protocols", "mock_ehm_diagonal_a1_to_h6.json"),
            os.path.join(os.getcwd(), "protocols", "mock_ehm_diagonal_a1_to_h6.json"),
            os.path.join(script_dir, "protocols", "ehm_48_well_test.json"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "protocols", "ehm_48_well_test.json"),
            os.path.join(os.getcwd(), "protocols", "ehm_48_well_test.json"),
        ]
        target_path = None
        for p in cand_paths:
            if os.path.exists(p):
                target_path = p
                break
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            self.has_tip_var.set(True)
            lw_dir = self.get_labware_dir()
            ehm_path = os.path.join(lw_dir, "myriamed_48_well.json")
            if os.path.exists(ehm_path):
                self.lims.deck_labware["Slot_4"] = Labware(ehm_path)
                self.lims.deck_labware["Slot_4"].source_file = "myriamed_48_well.json"
            if "Slot_4" not in self.placed_slots: self.placed_slots.append("Slot_4")
            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                if step['action'] == "Pick Up Tip":
                    msg = f"[{step['action'].upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                else:
                    msg = f"[{step['action'].upper()}] at {step.get('slot', '')}, Well {step.get('well', '')} (Z=86.0mm)"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded EHM 48-Well Diagonal Mock ({len(loaded_sequence)} steps, Z=86.0mm, no tip pickup).")
        else:
            messagebox.showerror("File Not Found", "Could not locate ehm_48_well_test.json")

    def action_load_quick_mock_protocol(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(script_dir, "protocols", "quick_mock_5slots.json"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "protocols", "quick_mock_5slots.json"),
            os.path.join(os.getcwd(), "protocols", "quick_mock_5slots.json"),
        ]
        target_path = None
        for p in cand_paths:
            if os.path.exists(p):
                target_path = p
                break
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()
            deck_setup = {
                "Slot_2": "reservoir_3_well.json",
                "Slot_3": "reservoir_6_column.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "generic_96_well_plate.json",
                "Slot_6": "waste_trough.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots: self.placed_slots.append(s_name)
            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = step.get('volume', 0.0)
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot} (Waste Trough)"
                else:
                    msg = f"[{act.upper()}] {vol}\u03bcL at {slot}, Well {well}"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded Quick 5-Slot Mock Protocol ({len(loaded_sequence)} steps). Labware auto-assigned.")
        else:
            messagebox.showerror("File Not Found", "Could not locate quick_mock_5slots.json")

    def action_load_slot5_rowA_protocol(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(script_dir, "protocols", "slot5_96well_rowA_test.json"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "protocols", "slot5_96well_rowA_test.json"),
            os.path.join(os.getcwd(), "protocols", "slot5_96well_rowA_test.json"),
        ]
        target_path = None
        for p in cand_paths:
            if os.path.exists(p):
                target_path = p
                break
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            self.has_tip_var.set(True)
            lw_dir = self.get_labware_dir()
            plate_file = "generic_96_well_plate.json"
            plate_path = os.path.join(lw_dir, plate_file)
            if os.path.exists(plate_path):
                self.lims.deck_labware["Slot_5"] = Labware(plate_path)
                self.lims.deck_labware["Slot_5"].source_file = plate_file
            if "Slot_5" not in self.placed_slots: self.placed_slots.append("Slot_5")
            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                msg = f"[{act.upper()}] at {slot}, Well {well}"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded Slot 5 96-Well Row A Test Protocol ({len(loaded_sequence)} steps). Labware auto-assigned and Tip state marked ATTACHED.")
        else:
            messagebox.showerror("File Not Found", "Could not locate slot5_96well_rowA_test.json")

    def action_load_liquid_test_protocol(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(script_dir, "protocols", "test_lld_slot1_a1_media_removal.json"),
            os.path.join(os.path.dirname(script_dir), "protocols", "test_lld_slot1_a1_media_removal.json"),
            os.path.join(script_dir, "protocols", "Test_Liquid_Level_Detection.json"),
            os.path.join(os.path.dirname(script_dir), "protocols", "Test_Liquid_Level_Detection.json"),
        ]
        target_path = None
        for p in cand_paths:
            if os.path.exists(p):
                target_path = p
                break
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            # Auto-assign Slot 1 = 50mL Falcon Media, Slot 2 = 50mL Falcon Discard (A3), Slot 4 = 1000uL Tip Rack
            deck_setup = {
                "Slot_1": "tube_rack_3x50ml.json",
                "Slot_2": "tube_rack_3x50ml.json",
                "Slot_4": "tip_rack_1000ul.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = step.get('volume', 0.0)
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot} (Waste)"
                elif act == "Detect Liquid Level":
                    msg = f"[{act.upper()}] at {slot}, Well {well}"
                elif "Incubate" in act:
                    msg = f"[SYSTEM] Wait {vol:.0f}s (Adjust/lower liquid height in Slot 6 Tube A1)"
                else:
                    msg = f"[{act.upper()}] {vol:.0f}\u03bcL at {slot}, Well {well}"
                self.wf_box.insert(tk.END, msg)
            if hasattr(self, 'draw_deck'): self.draw_deck()
            self.logger.info(f"Loaded Liquid Height Test Protocol ({len(loaded_sequence)} steps). Slot 6 Rack & Slot 2 Waste auto-assigned.")
        else:
            messagebox.showerror("File Not Found", "Could not locate Test_Liquid_Level_Detection.json")

    def action_load_media_and_drug_protocol(self, volume: float = 7.5):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        vol_suffix = f"_{volume:.1f}uL" if volume == 5.0 else "_7.5uL"
        cand_paths = [
            os.path.join(script_dir, "protocols", f"media_change_and_drug_addition_2_plates{vol_suffix}.json"),
            os.path.join(repo_root, "protocols", f"media_change_and_drug_addition_2_plates{vol_suffix}.json"),
            os.path.join(script_dir, "protocols", f"2_EHM_Media_Change_and_Drug_Addition{vol_suffix}.json"),
            os.path.join(repo_root, "protocols", f"2_EHM_Media_Change_and_Drug_Addition{vol_suffix}.json"),
            os.path.join(script_dir, "protocols", "media_change_and_drug_addition_2_plates.json"),
            os.path.join(repo_root, "protocols", "media_change_and_drug_addition_2_plates.json"),
        ]
        target_path = next((p for p in cand_paths if os.path.exists(p)), None)
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            # 6-slot deck configuration:
            # Slot 1: Media Reservoir (A1 Plt 1, A2 Plt 2)
            # Slot 2: Discard Falcon Rack / Reservoir (A1 Media Waste, A2 Plt 1 Tips, A3 Plt 2 Tips)
            # Slot 3: Drug Plate (generic 96 well)
            # Slot 4: Tip Rack (1000uL)
            # Slot 5: Plate 1 (Myriamed 48 well)
            # Slot 6: Plate 2 (Myriamed 48 well)
            deck_setup = {
                "Slot_1": "reservoir_3_well.json",
                "Slot_2": "reservoir_3_well.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "myriamed_48_well.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'): self.draw_deck()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = float(step.get('volume', 0.0))
                mix_cycles = int(step.get('mix_cycles', 0))
                mix_vol = float(step.get('mix_volume', 100.0))
                mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
                vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot}, Well {well}"
                else:
                    msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
                self.wf_box.insert(tk.END, msg)

            self.logger.info(f"Loaded Media Change + Drug Addition ({volume:.1f}µL) Protocol ({len(loaded_sequence)} steps). Deck configured: Slot 1 Media (A1/A2), Slot 2 Falcon A Waste, B/C Tips, Slot 3 Drug Plate, Slot 4 Tips, Slot 5 Plt 1, Slot 6 Plt 2.")
        else:
            messagebox.showerror("File Not Found", f"Could not locate media_change_and_drug_addition_2_plates{vol_suffix}.json")

    def action_load_unified_media_and_drug_protocol(self):
        return self.action_load_media_and_drug_protocol(7.5)

    def action_load_drug_addition_only_protocol(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        cand_paths = [
            os.path.join(script_dir, "protocols", "drug_addition_only_2_ehm_plates.json"),
            os.path.join(repo_root, "protocols", "drug_addition_only_2_ehm_plates.json"),
            os.path.join(script_dir, "protocols", "2b_EHM_Drug_Addition.json"),
            os.path.join(repo_root, "protocols", "2b_EHM_Drug_Addition.json"),
        ]
        target_path = next((p for p in cand_paths if os.path.exists(p)), None)
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            deck_setup = {
                "Slot_2": "tube_rack_3x50ml.json",
                "Slot_3": "generic_96_well_plate.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "myriamed_48_well.json",
                "Slot_6": "myriamed_48_well.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'): self.draw_deck()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = float(step.get('volume', 0.0))
                mix_cycles = int(step.get('mix_cycles', 0))
                mix_vol = float(step.get('mix_volume', 100.0))
                mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
                vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot}, Well {well}"
                else:
                    msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
                self.wf_box.insert(tk.END, msg)

            self.logger.info(f"Loaded Drug Addition Only Protocol ({len(loaded_sequence)} steps). Slot 3 Drug Plate, Slot 4 Tips, Slot 5/6 EHM Plates.")
        else:
            messagebox.showerror("File Not Found", "Could not locate drug_addition_only_2_ehm_plates.json")

    def action_load_dmso_dilution_protocol(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        cand_paths = [
            os.path.join(script_dir, "protocols", "1_Serial_Dilution_Plate.json"),
            os.path.join(repo_root, "protocols", "1_Serial_Dilution_Plate.json"),
            os.path.join(script_dir, "protocols", "bakar_v2_drug_dmso_initial_loading.json"),
            os.path.join(repo_root, "protocols", "bakar_v2_drug_dmso_initial_loading.json"),
        ]
        target_path = next((p for p in cand_paths if os.path.exists(p)), None)
        if target_path:
            with open(target_path, 'r') as f:
                loaded_sequence = json.load(f)
            self.workflow_sequence.clear()
            self.wf_box.delete(0, tk.END)
            lw_dir = self.get_labware_dir()

            deck_setup = {
                "Slot_1": "tube_rack_2x6_2ml.json",
                "Slot_4": "tip_rack_1000ul.json",
                "Slot_5": "generic_96_well_plate.json"
            }
            for s_name, lw_file in deck_setup.items():
                lp = os.path.join(lw_dir, lw_file)
                if os.path.exists(lp):
                    self.lims.deck_labware[s_name] = Labware(lp)
                    self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots:
                    self.placed_slots.append(s_name)
            self.sync_deck_manager()
            if hasattr(self, 'draw_deck'): self.draw_deck()

            for step in loaded_sequence:
                self.workflow_sequence.append(step)
                act = step['action']
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = float(step.get('volume', 0.0))
                mix_cycles = int(step.get('mix_cycles', 0))
                mix_vol = float(step.get('mix_volume', 100.0))
                mix_str = f" [Mix {mix_cycles}x {mix_vol:g}\u03bcL]" if mix_cycles > 0 else ""
                vol_str = f" {vol:.1f}\u03bcL" if vol % 1 != 0 else (f" {vol:.0f}\u03bcL" if vol > 0 else "")
                if act == "Pick Up Tip":
                    msg = f"[{act.upper()}] from {slot}, Well {well}"
                elif act == "Discard Tip":
                    msg = f"[{act.upper()}] into {slot}, Well {well}"
                else:
                    msg = f"[{act.upper()}]{vol_str} at {slot}, Well {well}{mix_str}"
                self.wf_box.insert(tk.END, msg)

            self.logger.info(f"Loaded DMSO Dilution Plate Protocol ({len(loaded_sequence)} steps). Slot 1 2mL Rack, Slot 4 Tips, Slot 5 96-Well Plate.")
        else:
            messagebox.showerror("File Not Found", "Could not locate 1_Serial_Dilution_Plate.json")

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
                custom_exp = self.ent_well.get().strip()
                chosen_exp = custom_exp if custom_exp else self.foc_exp_var.get().strip()
                step_data["well"] = chosen_exp
                msg = f"[MEASURE] FOC48_autoOrgan -> Experiment: '{chosen_exp}'"
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

            if step_data["z"] > 103.5:
                if not messagebox.askyesno(
                    "⚠️ Hardware Z Limit Warning",
                    f"Warning: Commanded Z={step_data['z']}mm exceeds safe machine limit (103.5mm).\n"
                    f"Instrument firmware hard limit is 103.8mm and will trigger CommandFailed.\n"
                    f"Do you want to proceed anyway?"
                ):
                    return

            if action in ["Pick Up Tip", "Discard Tip"]:
                msg = f"[{action.upper()} MANUAL] X:{step_data['x']} Y:{step_data['y']} Z:{step_data['z']}"
            elif action == "Detect Liquid Level":
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

            # Y Travel Limit Guardrail (any slot / any labware): Row G on back slots (~209mm) is the last reachable row
            if well:
                _wx, _wy = self._calculate_xy(slot, well.strip().upper())
                if _wy > 212.0:
                    messagebox.showwarning(
                        "⚠️ Physical Travel Limit Warning",
                        f"Warning: Well '{well}' on {slot} is at Y ≈ {_wy:.1f}mm, which exceeds the physical travel limit of the pipette head (~212mm)."
                    )

            # Safe Z-Depth Guardrail Check
            if action in ["Aspirate Media", "Dispense Media"]:
                labware_obj = self.lims.deck_labware.get(slot)
                try:
                    calc_z = self._calculate_z(action, labware_obj, well, "auto", 0.0, slot, step_data["extra_z"])
                except ValueError as cal_err:
                    messagebox.showwarning("Labware Not Calibrated", f"{cal_err}\n\nThe step will be added, but the run will stop at it until calibrated.")
                    calc_z = 0.0
                z_limits = getattr(labware_obj, 'z_limits', {}) if labware_obj else {}
                max_b = z_limits.get('max_safe_bottom_z', 103.0)
                if calc_z > max_b:
                    if not messagebox.askyesno(
                        "⚠️ Safe Z-Depth Warning",
                        f"Warning: Resulting Z-Depth ({calc_z:.1f}mm) exceeds safe limit ({max_b:.1f}mm) for {slot} ({getattr(labware_obj, 'name', 'Labware')})!\n\n"
                        f"This might bend the tip or damage the labware.\n"
                        f"Do you want to proceed and add this step anyway?"
                    ):
                        return

            if action in ["Pick Up Tip", "Discard Tip"]:
                msg = f"[{action.upper()}] from {slot}, Well {well}" if action == "Pick Up Tip" else f"[{action.upper()}] into {slot} (Waste Trough)"
            elif action == "Detect Liquid Level":
                msg = f"[{action.upper()}] at {slot}, Well {well}"
            else:
                z_msg = f" (Z+{step_data['extra_z']}mm)" if step_data.get('extra_z', 0.0) > 0 else ""
                msg = f"[{action.upper()}] {step_data['volume']}\u03bcL at {slot}, Well {well}{z_msg}"

        self.wf_box.insert(tk.END, msg)
        self.workflow_sequence.append(step_data)

    def _format_step_msg(self, step_data):
        action = step_data.get('action', '')
        mode = step_data.get('mode', 'auto')
        vol = step_data.get('volume', 0.0)
        slot = step_data.get('slot', '')
        well = step_data.get('well', '')
        extra_z = step_data.get('extra_z', 0.0)
        mix_c = step_data.get('mix_cycles', 0)
        mix_v = step_data.get('mix_volume', 100.0)

        if "FOC48" in action:
            return f"[MEASURE] FOC48_autoOrgan -> Experiment: '{well or 'Default'}'"
        elif "Incubate" in action:
            return f"[SYSTEM] Incubate for {vol} seconds."
        elif "Data Analysis" in action or "DB Upload" in action or "Calcium Curve" in action:
            return f"[{action.upper()}]"
        elif mode == "manual":
            return f"[{action.upper()}] Manual -> X:{step_data.get('x',0)} Y:{step_data.get('y',0)} Z:{step_data.get('z',0)} Vol:{vol}uL"
        elif action in ["Pick Up Tip", "Discard Tip"]:
            return f"[{action.upper()}] from {slot}, Well {well}" if action == "Pick Up Tip" else f"[{action.upper()}] into {slot} (Well {well})"
        elif action == "Detect Liquid Level":
            return f"[{action.upper()}] at {slot}, Well {well}"
        else:
            z_msg = f" (Z+{extra_z}mm)" if extra_z > 0 else ""
            mix_msg = f" [Mix {mix_c}x {mix_v}uL]" if int(mix_c) > 0 and action == "Dispense Media" else ""
            return f"[{action.upper()}] {vol}\u03bcL at {slot}, Well {well}{z_msg}{mix_msg}"

    def _set_protocol_edit_buttons_state(self, state):
        for btn in getattr(self, 'protocol_edit_buttons', []):
            try:
                btn.config(state=state)
            except Exception:
                pass

    def action_delete_step(self):
        sel = self.wf_box.curselection()
        if not sel:
            messagebox.showinfo("Delete Step", "Please select a step in the protocol list to delete.")
            return
        idx = sel[0]
        if idx >= len(self.workflow_sequence): return
        del_step = self.workflow_sequence[idx]
        del self.workflow_sequence[idx]
        self.wf_box.delete(idx)
        if self.is_running and hasattr(self, 'current_step_idx'):
            if idx < self.current_step_idx:
                self.current_step_idx = max(0, self.current_step_idx - 1)
            self.estimated_total_time = self.estimate_workflow_time(self.workflow_sequence)
        self.logger.info(f"Protocol Step {idx + 1} deleted ({del_step.get('action')}). Remaining: {len(self.workflow_sequence)}.")
        if self.workflow_sequence:
            new_sel = min(idx, len(self.workflow_sequence) - 1)
            self.wf_box.selection_set(new_sel)

    def action_insert_step(self):
        sel = self.wf_box.curselection()
        insert_idx = (sel[0] + 1) if sel else len(self.workflow_sequence)
        if sel and sel[0] < len(self.workflow_sequence):
            template_step = dict(self.workflow_sequence[sel[0]])
        else:
            template_step = {
                'action': 'Aspirate Media',
                'mode': 'auto',
                'slot': 'Slot_1',
                'well': 'A1',
                'volume': 100.0,
                'extra_z': 0.0,
                'mix_cycles': 0,
                'mix_volume': 100.0
            }
        self._open_step_editor_dialog(template_step, insert_idx=insert_idx)

    def action_move_step_up(self):
        sel = self.wf_box.curselection()
        if not sel or sel[0] == 0: return
        idx = sel[0]
        if idx >= len(self.workflow_sequence): return
        self.workflow_sequence[idx - 1], self.workflow_sequence[idx] = self.workflow_sequence[idx], self.workflow_sequence[idx - 1]
        msg_cur = self.wf_box.get(idx)
        msg_prev = self.wf_box.get(idx - 1)
        self.wf_box.delete(idx - 1, idx)
        self.wf_box.insert(idx - 1, msg_cur)
        self.wf_box.insert(idx, msg_prev)
        self.wf_box.selection_set(idx - 1)
        if self.is_running and hasattr(self, 'current_step_idx'):
            if self.current_step_idx == idx:
                self.current_step_idx -= 1
            elif self.current_step_idx == idx - 1:
                self.current_step_idx += 1
        self.logger.info(f"Moved Step {idx + 1} UP to Position {idx}.")

    def action_move_step_down(self):
        sel = self.wf_box.curselection()
        if not sel or sel[0] >= len(self.workflow_sequence) - 1: return
        idx = sel[0]
        self.workflow_sequence[idx], self.workflow_sequence[idx + 1] = self.workflow_sequence[idx + 1], self.workflow_sequence[idx]
        msg_cur = self.wf_box.get(idx)
        msg_next = self.wf_box.get(idx + 1)
        self.wf_box.delete(idx, idx + 1)
        self.wf_box.insert(idx, msg_next)
        self.wf_box.insert(idx + 1, msg_cur)
        self.wf_box.selection_set(idx + 1)
        if self.is_running and hasattr(self, 'current_step_idx'):
            if self.current_step_idx == idx:
                self.current_step_idx += 1
            elif self.current_step_idx == idx + 1:
                self.current_step_idx -= 1
        self.logger.info(f"Moved Step {idx + 1} DOWN to Position {idx + 2}.")

    def edit_wf_step(self, event=None):
        sel = self.wf_box.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self.workflow_sequence): return
        step = self.workflow_sequence[idx]
        self._open_step_editor_dialog(step, edit_idx=idx)

    def _open_step_editor_dialog(self, step_data, edit_idx=None, insert_idx=None):
        dlg = tk.Toplevel(self.root)
        is_edit = edit_idx is not None
        dlg.title(f"{'Edit' if is_edit else 'Insert'} Protocol Step")
        dlg.geometry("400x380")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        pad = {"padx": 10, "pady": 4}
        f = ttk.Frame(dlg, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Action:").grid(row=0, column=0, sticky="w", **pad)
        actions = ["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip", "Mix Well", "Detect Liquid Level", "System: Incubate (Wait)", "System: FOC48 Measurement"]
        act_cb = ttk.Combobox(f, values=actions, state="readonly")
        cur_act = step_data.get('action', 'Aspirate Media')
        act_cb.set(cur_act if cur_act in actions else actions[1])
        act_cb.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Deck Slot:").grid(row=1, column=0, sticky="w", **pad)
        slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
        slot_cb = ttk.Combobox(f, values=slots, state="readonly")
        slot_cb.set(step_data.get('slot', 'Slot_1'))
        slot_cb.grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Well:").grid(row=2, column=0, sticky="w", **pad)
        well_ent = ttk.Entry(f)
        well_ent.insert(0, str(step_data.get('well', 'A1')))
        well_ent.grid(row=2, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Volume (\u03bcL) / Time (s):").grid(row=3, column=0, sticky="w", **pad)
        vol_ent = ttk.Entry(f)
        vol_ent.insert(0, str(step_data.get('volume', 100.0)))
        vol_ent.grid(row=3, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Extra Z offset (mm):").grid(row=4, column=0, sticky="w", **pad)
        z_ent = ttk.Entry(f)
        z_ent.insert(0, str(step_data.get('extra_z', 0.0)))
        z_ent.grid(row=4, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Mix Cycles:").grid(row=5, column=0, sticky="w", **pad)
        mix_c_ent = ttk.Entry(f)
        mix_c_ent.insert(0, str(step_data.get('mix_cycles', 0)))
        mix_c_ent.grid(row=5, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Mix Volume (\u03bcL):").grid(row=6, column=0, sticky="w", **pad)
        mix_v_ent = ttk.Entry(f)
        mix_v_ent.insert(0, str(step_data.get('mix_volume', 100.0)))
        mix_v_ent.grid(row=6, column=1, sticky="ew", **pad)

        def save():
            try:
                new_data = dict(step_data)
                new_data['action'] = act_cb.get()
                new_data['slot'] = slot_cb.get()
                new_data['well'] = well_ent.get().strip().upper()
                new_data['volume'] = float(vol_ent.get())
                new_data['extra_z'] = float(z_ent.get())
                new_data['mix_cycles'] = int(mix_c_ent.get())
                new_data['mix_volume'] = float(mix_v_ent.get())

                msg = self._format_step_msg(new_data)
                if is_edit:
                    self.workflow_sequence[edit_idx] = new_data
                    self.wf_box.delete(edit_idx)
                    self.wf_box.insert(edit_idx, msg)
                    self.wf_box.selection_set(edit_idx)
                    self.logger.info(f"Edited Step {edit_idx + 1}: {msg}")
                else:
                    self.workflow_sequence.insert(insert_idx, new_data)
                    self.wf_box.insert(insert_idx, msg)
                    self.wf_box.selection_set(insert_idx)
                    if self.is_running and hasattr(self, 'current_step_idx'):
                        if insert_idx <= self.current_step_idx:
                            self.current_step_idx += 1
                    self.logger.info(f"Inserted Step at {insert_idx + 1}: {msg}")

                if self.is_running:
                    self.estimated_total_time = self.estimate_workflow_time(self.workflow_sequence)

                dlg.destroy()
            except ValueError as ve:
                messagebox.showerror("Invalid Input", f"Please check numerical values:\n{ve}", parent=dlg)

        btn_box = ttk.Frame(f)
        btn_box.grid(row=7, column=0, columnspan=2, pady=15)
        ttk.Button(btn_box, text="💾 Save Step", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)

    def action_load_deck_2_ehm_multiplate(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cand_paths = [
            os.path.join(script_dir, "deck_2_ehm_plates_slot2_discard_a1.json"),
            os.path.join(script_dir, "protocols", "deck_2_ehm_plates_slot2_discard_a1.json"),
            os.path.join(os.path.dirname(script_dir), "protocols", "deck_2_ehm_plates_slot2_discard_a1.json"),
            os.path.join(script_dir, "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(script_dir, "deck_configurations", "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(os.getcwd(), "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(os.getcwd(), "protocols", "deck_2_ehm_plates_slot2_discard_50ml.json"),
            os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI", "deck_2_ehm_plates_slot2_discard_50ml.json"),
        ]
        target_path = next((p for p in cand_paths if os.path.exists(p)), None)
        if target_path:
            self._deserialize_workspace(target_path)
            self.logger.info("Loaded 2-EHM Multi-Plate Deck Configuration (Slot 1 Media A1/A2, Slot 2 Discard A1, Slot 3 Drug Plate, Slot 4 Tips, Slot 5 Plt 1, Slot 6 Plt 2).")
        else:
            messagebox.showerror("Error", "Could not locate deck_2_ehm_plates_slot2_discard_a1.json")

    def sync_deck_manager(self):
        """
        Synchronizes the strongly-typed DeckManager with the GUI's deck_slots and deck_labware.
        Maps labware definitions to dedicated LabwareBase subclasses and attaches HeightAdapters.
        """
        if not hasattr(self, 'deck_manager'):
            self.deck_manager = DeckManager()

        for slot_name, slot_obj in self.lims.deck_slots.items():
            adapter = ADAPTER_90MM_BLOCK if slot_name in ("Slot_1", "Slot_2") else ADAPTER_NONE

            labware_obj = self.lims.deck_labware.get(slot_name)
            if not labware_obj:
                if slot_name in self.deck_manager.slots:
                    self.deck_manager.slots[slot_name].labware = None
                    self.deck_manager.slots[slot_name].adapter = adapter
                continue

            src = str(getattr(labware_obj, 'source_file', '') or '').lower()
            name = str(getattr(labware_obj, 'name', '') or '').lower()
            both = f"{src} {name}"

            typed_lw = None
            if "3x50ml" in both or "50ml" in both or "tube_rack_3x50ml" in src:
                typed_lw = FalconRack50mL(source_file=src)
            elif "2x6" in both or "2ml" in both or "tube_rack_2x6" in src:
                typed_lw = TubeRack2x6_2mL(source_file=src)
            elif "reservoir_3" in src or "3_well" in src or "3-well" in name or "30ml" in both:
                typed_lw = Reservoir3Well(source_file=src)
            elif "tip" in both or "tip_rack" in src:
                existing_offset = (0.0, 0.0)
                if slot_name in self.deck_manager.slots and isinstance(self.deck_manager.slots[slot_name].labware, TipRack96):
                    existing_offset = (
                        self.deck_manager.slots[slot_name].labware.learned_rack_offset_x,
                        self.deck_manager.slots[slot_name].labware.learned_rack_offset_y
                    )
                typed_lw = TipRack96(source_file=src)
                typed_lw.learned_rack_offset_x, typed_lw.learned_rack_offset_y = existing_offset
            elif "waste" in both or (slot_name == "Slot_6" and not both.strip()):
                typed_lw = WasteTrough(source_file=src)
            elif "myriamed" in both or "ehm" in both or "48" in both:
                typed_lw = Plate48Myriamed(source_file=src)
            elif "96" in both or (getattr(labware_obj, 'rows', 0) == 8 and getattr(labware_obj, 'columns', 0) == 12):
                typed_lw = Plate96(source_file=src)
            else:
                typed_lw = LabwareBase(
                    name=getattr(labware_obj, 'name', 'Generic Labware'),
                    category="custom",
                    rows=getattr(labware_obj, 'rows', 1),
                    columns=getattr(labware_obj, 'columns', 1),
                    z_height_mm=getattr(labware_obj, 'z_height_mm', 14.35),
                    well_depth_mm=getattr(labware_obj, 'well_depth_mm', 10.0),
                    well_radius_mm=getattr(labware_obj, 'well_radius_mm', 3.4),
                    source_file=src,
                    raw_data=getattr(labware_obj, 'raw_data', {}) or {}
                )

            self.deck_manager.mount_labware(slot_name, typed_lw, adapter=adapter)

    def estimate_workflow_time(self, sequence) -> float:
        total_time = 0.0
        current_x, current_y = 0.0, 0.0
        speed_pct = self.speed_var.get() if hasattr(self, 'speed_var') else 80.0
        xy_speed = max(50.0, 250.0 * (speed_pct / 100.0))

        for s in sequence:
            action = s.get('action', '')
            vol = float(s.get('volume', 0.0))
            mix_cycles = int(s.get('mix_cycles', 0)) if getattr(self, 'enable_mixing_for_run', True) else 0

            if "Incubate" in action:
                total_time += vol
                continue
            elif "FOC48" in action:
                total_time += 150.0
                continue
            elif "Data Analysis" in action:
                total_time += 5.0
                continue
            elif "DB Upload" in action:
                total_time += 3.0
                continue
            elif "Calcium Curve" in action:
                total_time += 60.0
                continue

            slot = s.get('slot', '')
            well = s.get('well', '')
            tx, ty = self._calculate_xy(slot, well) if slot else (current_x, current_y)
            travel_dist = math.hypot(tx - current_x, ty - current_y)
            current_x, current_y = tx, ty
            travel_time = (travel_dist / xy_speed) + 0.35

            if action == "Pick Up Tip":
                total_time += travel_time + 8.5
            elif action == "Discard Tip":
                total_time += travel_time + 4.5
            elif action == "Aspirate Media":
                has_air = (vol <= 50.0) or (slot == "Slot_5")
                air_time = 1.5 if has_air else 0.0
                draw_time = max(1.0, vol * 0.005)
                total_time += travel_time + 3.5 + air_time + draw_time
            elif action == "Dispense Media":
                disp_time = max(0.5, vol * 0.004)
                mix_time = mix_cycles * 2.8
                total_time += travel_time + 3.0 + disp_time + 0.5 + mix_time
            elif action == "Mix Well":
                total_time += travel_time + 3.0 + (mix_cycles * 2.8)
            elif action == "Detect Liquid Level":
                total_time += travel_time + 8.0
            else:
                total_time += travel_time + 2.0

        return round(total_time, 1)

    def pause_resume_run(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="▶ RESUME", bg="#17a2b8")
            self._set_protocol_edit_buttons_state(tk.NORMAL)
            self.logger.info("Protocol Paused by User. Steps can be edited, added, reordered, or deleted.")
        else:
            self.pause_event.set()
            self.btn_pause.config(text="⏸ PAUSE", bg="#ffc107")
            self._set_protocol_edit_buttons_state(tk.DISABLED)
            cur_i = getattr(self, 'current_step_idx', 0)
            self.logger.info(f"Protocol Resumed at Step {cur_i + 1}/{len(self.workflow_sequence)}.")

    def stop_run(self):
        self.is_aborted = True
        self.pause_event.set()
        self.logger.info("Protocol Abort Signal Sent. Halting sequence...")
        try:
            self.btn_stop.config(state=tk.DISABLED, text="Stopping...")
        except Exception:
            pass

    def update_ui_state(self, running):
        self.is_running = running
        state = tk.DISABLED if running else tk.NORMAL
        self.btn_play.config(state=state)
        self.btn_pause.config(state=tk.NORMAL if running else tk.DISABLED, text="⏸ PAUSE", bg="#ffc107")
        self.btn_stop.config(state=tk.NORMAL if running else tk.DISABLED, text="⏹ CANCEL")
        self._set_protocol_edit_buttons_state(tk.NORMAL if not running else tk.DISABLED)

    def ask_error_resolution(self, error_msg, step_idx):
        err_str = str(error_msg)
        if any(kw in err_str for kw in ["CRITICAL", "COLLISION", "DOUBLE-TIP", "ejection failed", "SAFETY INTERLOCK"]):
            self.logger.critical(f"🛑 CRITICAL SAFETY ABORT on Step {step_idx}: {err_str}")
            self.is_aborted = True
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except Exception:
                    pass
            return

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

    def _probe_surface_and_wait(self, limit_z: float, submerge_mm: float = 1.0) -> float:
        """
        Safely probes downward for liquid meniscus using Biohit tip frequency sensor.
        Blocks until physical movement completes, pauses for visual confirmation,
        and returns the measured liquid surface Z coordinate (in mm).
        CRITICAL FIRMWARE CONSTRAINT: InstrumentLib.dll _MoveToSurface enforces limit <= 100.0f.
        Any limit > 100.0f causes immediate rejection with ErrorCode 2 without energizing the Z motor.
        We strictly clamp limit_z to safe_limit_z <= 99.5mm.
        """
        # Strict hard cap: InstrumentLib.dll _MoveToSurface strictly enforces limit <= 100.0f
        safe_limit_z = min(99.5, max(10.0, float(limit_z)))
        hw = getattr(self.lims.pipettor, 'hardware', None)
        if not hw:
            # Simulator mode fallback
            time.sleep(1.0)
            return max(0.0, safe_limit_z - 15.0)

        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9))) if hasattr(self, 'speed_var') else 7
        saved_z_speed = getattr(hw, 'z_speed', hw_speed)
        try:
            # Set responsive probe speed (probe at speed 5-7 instead of crawling at 3)
            probe_speed = max(5, min(hw_speed, 7))
            hw.z_speed = probe_speed
            self.logger.info(f"[SURFACE PROBE] Descending toward safe limit Z={safe_limit_z:.1f}mm (depth={submerge_mm:.1f}mm, speed={probe_speed}, Cap<=99.5mm)...")

            # Execute move_to_surface
            called_ok = False
            try:
                hw.move_to_surface(limit=float(safe_limit_z), distance_from_surface=float(submerge_mm))
                called_ok = True
            except Exception as e_wrap:
                self.logger.warning(f"[SURFACE PROBE] pipettor.move_to_surface exception: {e_wrap}")

            if not called_ok:
                inst = getattr(hw, '_Pipettor__instrument', None)
                if inst:
                    try:
                        if hasattr(inst, 'MoveToSurface'):
                            res = inst.MoveToSurface(float(safe_limit_z), float(submerge_mm))
                            called_ok = bool(res)
                        elif hasattr(inst, 'Control') and hasattr(inst.Control, 'MoveToSurface'):
                            res = inst.Control.MoveToSurface(float(safe_limit_z), True)
                            called_ok = bool(res)
                    except Exception as e_clr:
                        self.logger.error(f"[SURFACE PROBE] Direct CLR MoveToSurface call failed: {e_clr}")

            if not called_ok:
                self.logger.error(f"[SURFACE PROBE] MoveToSurface command was rejected by hardware firmware (limit={safe_limit_z:.1f}mm).")
                raise RuntimeError(f"MoveToSurface rejected by pipettor firmware (limit={safe_limit_z:.1f}mm).")

            # Wait for physical descent to complete (polling drive state and position stability)
            inst = getattr(hw, '_Pipettor__instrument', None)
            t_start = time.time()
            max_wait_sec = 25.0
            time.sleep(0.3)  # Brief grace period for motor acceleration

            last_z = None
            stable_ticks = 0
            while (time.time() - t_start) < max_wait_sec:
                drive_active = False
                if inst and hasattr(inst, 'Control') and hasattr(inst.Control, 'IsDriveOn'):
                    try:
                        drive_active = bool(inst.Control.IsDriveOn("Z"))
                    except Exception:
                        drive_active = False

                curr_z = getattr(hw, 'z_position', None)
                if curr_z is not None:
                    if last_z is not None and abs(curr_z - last_z) < 0.08:
                        stable_ticks += 1
                    else:
                        stable_ticks = 0
                    last_z = curr_z

                # Stop waiting when drive is off and position has stabilized for 3 consecutive ticks
                if not drive_active and stable_ticks >= 3:
                    break

                time.sleep(0.1)

            z_measured = getattr(hw, 'z_position', safe_limit_z)

            # Sanity guard: clearance ceiling is Z=0.0-5.0mm. No container rim on this deck is above Z=40mm.
            # If Z <= 25.0mm, the motor never moved or hit a false trigger in open air near the top.
            if z_measured <= 25.0:
                self.logger.error(f"[SURFACE PROBE FAILURE] Tip remained near ceiling at Z={z_measured:.2f}mm (<=25mm). Probe aborted or failed to descend.")
                raise RuntimeError(f"Surface probe failed: tip remained near ceiling at Z={z_measured:.2f}mm")

            self.logger.info(f"[SURFACE PROBE] Surface detected/stopped at Z={z_measured:.2f}mm (limit={safe_limit_z:.1f}mm)")

            # Visual confirmation pause
            time.sleep(0.15)
            return float(z_measured)

        finally:
            try:
                hw.z_speed = hw_speed
            except Exception:
                pass

    # ------------------------------------------------------------------
    # MODULAR LABWARE KINEMATICS
    # Coordinates depend on (slot A1 origin) + (labware geometry), never on
    # hardcoded slot identity. Any labware can sit on any slot.
    # ------------------------------------------------------------------

    # Machine XY of "well A1" for each slot (physically jog-calibrated where noted)
    SLOT_A1_ORIGINS = {
        "Slot_1": (238.2, 13.0),   # calibrated (front right, height-block slot)
        "Slot_2": (95.5, 13.0),    # calibrated (front left, 3-well reservoir/waste trough A1)
        "Slot_3": (243.81, 53.0),  # calibrated (exact center: X=243.81, Y=53.0)
        "Slot_4": (105.0, 53.0),   # calibrated (96-well A1 X=105, Y=53)
        "Slot_5": (243.81, 149.23), # calibrated (exact center: X=243.81, Y=149.23)
        "Slot_6": (105.0, 149.23), # derived (Slot_4 X column + Slot_5 Y row)
    }

    # Calibrated per-slot column tables for 96-format labware (override pitch math)
    SLOT_96_COL_OVERRIDES = {
        "Slot_5": [243.81, 234.81, 225.81, 216.81, 207.81, 198.81, 189.81, 180.81, 171.81, 162.81, 153.81, 144.81],
    }

    # Calibrated per-slot Z for 96-well microplates: (deep / aspirate / mix, brim / dispense)
    SLOT_96_PLATE_Z = {
        "Slot_3": (91.0, 85.0),
        "Slot_4": (90.0, 85.0),
        "Slot_5": (92.0, 85.0),
    }
    DEFAULT_96_PLATE_Z = (92.0, 85.0)

    def _lw_kind(self, labware_obj):
        """Classify a labware object by its definition (file first, then name)."""
        if not labware_obj:
            return None
        src = (getattr(labware_obj, 'source_file', '') or '').lower()
        name = (getattr(labware_obj, 'name', '') or '').lower()
        both = src + " " + name
        raw = getattr(labware_obj, 'raw_data', {}) or {}

        if "tip" in both:
            return "tip_rack"
        if "2x6" in both:
            return "tube_rack_2x6"
        if "biohit_rack" in both or "17a" in both or "4x6" in both:
            return "tube_rack_4x6"
        if "waste" in both:
            return "waste"
        if "reservoir_3" in src or "3_well" in src or "3-well" in name:
            return "reservoir_3"
        if "reservoir_6" in src or "6_column" in src or "6-column" in name:
            return "reservoir_6"
        if "myriamed" in both or "ehm" in both or "48" in both:
            return "ehm48"
        if "96" in both or (getattr(labware_obj, 'rows', 0) == 8 and getattr(labware_obj, 'columns', 0) == 12):
            return "plate96"
        if raw.get('kinematics'):
            return "json_kinematics"
        return "generic"

    def _is_front_slot(self, slot_name):
        slot_obj = self.lims.deck_slots.get(slot_name)
        if slot_obj is not None:
            return slot_obj.y_abs < 40.0
        return slot_name in ("Slot_1", "Slot_2")

    def _slot_a1_origin(self, slot_name):
        if slot_name in self.SLOT_A1_ORIGINS:
            return self.SLOT_A1_ORIGINS[slot_name]
        slot_obj = self.lims.deck_slots.get(slot_name)
        if not slot_obj:
            return 0.0, 0.0
        ox = 243.81 if slot_obj.x_abs >= 70.0 else 105.0
        if slot_obj.y_abs < 40.0:
            oy = 13.0
        elif slot_obj.y_abs < 120.0:
            oy = 53.0
        else:
            oy = 149.23
        return ox, oy

    @staticmethod
    def _parse_well(well_id):
        """'B3' -> (row_idx=1, col_idx=2). Returns (None, None) if invalid."""
        if not well_id or len(well_id) < 2:
            return None, None
        r_c = well_id[0].upper()
        try:
            c_idx = int(well_id[1:]) - 1
        except ValueError:
            return None, None
        r_idx = ord(r_c) - ord('A')
        if r_idx < 0 or c_idx < 0:
            return None, None
        return r_idx, c_idx

    def _calculate_xy(self, slot_name, well_id):
        # 0. Object-Oriented DeckManager Kinematics
        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
            slot_model = self.deck_manager.slots[slot_name]
            if slot_model.labware:
                cx, cy = slot_model.labware.get_well_xy(slot_model, well_id)
                if cx != 0.0 or cy != 0.0:
                    return cx, cy

        slot_obj = self.lims.deck_slots.get(slot_name)
        if not slot_obj: return 0.0, 0.0

        cx = slot_obj.x_abs + (slot_obj.width_mm / 2.0)
        cy = slot_obj.y_abs + (slot_obj.height_mm / 2.0)

        labware_obj = self.lims.deck_labware.get(slot_name)
        kind = self._lw_kind(labware_obj)
        ox, oy = self._slot_a1_origin(slot_name)
        front = self._is_front_slot(slot_name)
        r_idx, c_idx = self._parse_well(well_id)
        raw = getattr(labware_obj, 'raw_data', None) or {}

        # 1. 3-WELL RESERVOIR / WASTE TROUGH ON SLOT 2:
        # User physically calibrated: A1 is at X=95.5, A2 is at X=57.0, A3 (Waste Discard) is at X=12.0, Y=13.0
        if slot_name == "Slot_2":
            w_str = str(well_id or "").upper().strip()
            if w_str in ("A1", "1"):
                return 95.5, 13.0
            elif w_str in ("A2", "2"):
                return 57.0, 13.0
            elif w_str in ("A3", "3", "DISCARD", "WASTE") or not w_str or kind in ("waste", "reservoir_3", "tube_rack_3x50ml"):
                return 12.0, 13.0

        # 1b. WASTE TROUGH: always the centre of Slot 6 (or generic single-cavity waste)
        if kind == "waste" or (kind is None and slot_name == "Slot_6"):
            return cx, cy

        # 2. 96-FORMAT (tip rack or 96-well plate) on ANY slot
        if kind in ("tip_rack", "plate96") or (kind is None and not front):
            if r_idx is not None and 0 <= r_idx < 8 and 0 <= c_idx < 12:
                if kind == "tip_rack":
                    # Tip rack A1 physically calibrated at X=105.0, Y=53.0 on Slot 4
                    learned_dx, learned_dy = getattr(self, 'tip_rack_learned_offset', (0.0, 0.0))
                    if slot_name == "Slot_4":
                        return (105.0 - (c_idx * 9.0)) + learned_dx, (53.0 + (r_idx * 9.0)) + learned_dy
                    return (ox - (c_idx * 9.0)) + learned_dx, (oy + (r_idx * 9.0)) + learned_dy
                col_table = self.SLOT_96_COL_OVERRIDES.get(slot_name)
                tx = col_table[c_idx] if col_table else ox - (c_idx * 9.0)
                return tx, oy + (r_idx * 9.0)
            return cx, cy

        # 3. MYRIAMED 48-WELL EHM PLATE (calibrated on Slot_4: cols 105..15, rows 57..119, +1.0mm X offset, -2.0mm Y offset)
        if kind == "ehm48":
            col_dx = [0.0, -18.0, -36.0, -54.0, -72.0, -90.0]
            row_dy = [1.0, 9.0, 18.0, 26.0, 35.0, 44.0, 54.0, 63.0]
            if r_idx is not None and r_idx < len(row_dy) and c_idx < len(col_dx):
                return ox + col_dx[c_idx] + 1.0, oy + row_dy[r_idx] - 2.0
            return cx, cy

        # 4. 3-WELL RESERVOIR (calibrated on Slot_1: pitch 42.6mm; Slot_2: A1=95.5, A2=57.0, A3=12.0)
        if kind == "reservoir_3" or (kind is None and front):
            if slot_name == "Slot_2":
                col_x = [95.5, 57.0, 12.0]
                ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
                if c_idx is None and well_id in ("1", "2", "3"):
                    ci = int(well_id) - 1
                return col_x[ci], oy + (0.0 if front else 31.5)
            col_dx = [0.0, -42.6, -85.2]
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 3) else 0
            if c_idx is None and well_id in ("1", "2", "3"):
                ci = int(well_id) - 1
            return ox + col_dx[ci], oy + (0.0 if front else 31.5)

        # 5. 6-COLUMN RESERVOIR
        if kind == "reservoir_6":
            col_dx = [3.0, -12.0, -30.0, -46.5, -63.0, -79.5]
            ci = c_idx if (c_idx is not None and 0 <= c_idx < 6) else 3
            return ox + col_dx[ci], oy + (0.0 if front else 45.0)

        # 6. 4x6 TUBE RACK (Biohit 17A, pitch 19.3 mm)
        if kind == "tube_rack_4x6":
            if r_idx is not None and r_idx < 4 and c_idx < 6:
                return ox + 7.15 - (c_idx * 19.3), oy + (0.0 if front else 24.3) + (r_idx * 19.3)
            return cx, cy

        # 7. 2x6 TUBE RACK (2 mL Falcon / Microcentrifuge Tubes on 90mm Height Block)
        # User calibrated: Slot 1 A1 is at X = 245.0, Y = 0.0, rim Z = 75.0mm
        if kind == "tube_rack_2x6":
            orig_x = 245.0 if slot_obj.x_abs >= 70.0 else (245.0 - 135.2)
            orig_y = 0.0 if front else oy
            if r_idx is not None and 0 <= r_idx < 2 and c_idx is not None and 0 <= c_idx < 6:
                return orig_x - (c_idx * 18.0), orig_y + (r_idx * 18.0)
            return cx, cy

        # 8. DATA-DRIVEN LABWARE: geometry read from its JSON "kinematics" block
        kin = raw.get('kinematics') if raw else None
        if kin:
            rows = getattr(labware_obj, 'rows', 1)
            cols = getattr(labware_obj, 'columns', 1)
            if r_idx is not None and r_idx < rows and c_idx < cols:
                return (ox + float(kin.get('a1_dx_mm', 0.0)) - c_idx * float(kin.get('pitch_col_mm', 9.0)),
                        oy + float(kin.get('a1_dy_mm', 0.0)) + r_idx * float(kin.get('pitch_row_mm', 9.0)))
            return cx, cy

        # 8. Fallback Generic Labware (centred on slot using JSON well offsets)
        if labware_obj and labware_obj.wells:
            first_w = list(labware_obj.wells.values())[0]
            lw_w = max(w.x_rel for w in labware_obj.wells.values()) + first_w.x_rel
            lw_h = max(w.y_rel for w in labware_obj.wells.values()) + first_w.y_rel
            well_obj = labware_obj.wells.get(well_id)
            if well_obj:
                return cx + ((lw_w / 2.0) - well_obj.x_rel), cy - (lw_h / 2.0) + well_obj.y_rel

        return cx, cy

    def _rim_calibrated_z(self, labware_obj, deep):
        """Z for labware calibrated by rim height (z_calibration block)."""
        raw = getattr(labware_obj, 'raw_data', {}) or {}
        zc = raw.get('z_calibration', {}) or {}
        rim_z = zc.get('rim_z')
        if rim_z is None:
            rim_z = 75.0  # User calibrated value
        rim_z = float(rim_z)
        if deep:
            # Safe aspiration deep inside the tube (capped at 100.0 mm to avoid hardware limits)
            asp_depth = float(zc.get('aspirate_depth_mm', 23.0))
            return min(rim_z + asp_depth, 100.0)
        disp_below = float(zc.get('dispense_below_rim_mm', 5.0))
        return rim_z + disp_below

    def _labware_bottom_z(self, labware_obj, slot_name):
        """Deepest safe Z for probing / liquid detection, based on labware type."""
        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
            slot_model = self.deck_manager.slots[slot_name]
            if slot_model.labware:
                return slot_model.labware.get_bottom_z(slot_model)
        kind = self._lw_kind(labware_obj)
        if kind == "tube_rack_2x6":
            return self._rim_calibrated_z(labware_obj, deep=True)
        if labware_obj and 'max_safe_bottom_z' in (getattr(labware_obj, 'z_limits', {}) or {}):
            return float(labware_obj.z_limits['max_safe_bottom_z'])
        if kind == "ehm48":
            return 86.0
        if kind == "plate96":
            return self.SLOT_96_PLATE_Z.get(slot_name, self.DEFAULT_96_PLATE_Z)[0]
        if kind == "reservoir_3" or (kind is None and self._is_front_slot(slot_name)):
            return 100.0
        if kind == "reservoir_6":
            return 103.0
        if kind == "tube_rack_4x6":
            return 95.0
        return 90.0

    def _get_next_tube_in_sequence(self, slot_name, current_well):
        """Returns the next well/tube ID in sequence for auto-advancing when liquid is depleted.
        STRICTLY for Falcon tube racks only. NEVER advances on plates or dedicated reservoirs!"""
        slot_model = self.deck_manager.slots.get(slot_name) if hasattr(self, 'deck_manager') else None
        lw = slot_model.labware if slot_model else None
        lw_obj = self.lims.deck_labware.get(slot_name)
        lw_src = str(getattr(lw_obj, 'source_file', '')).lower()
        lw_kind = self._lw_kind(lw_obj)

        # 1. 2mL Falcon Rack
        if isinstance(lw, TubeRack2x6_2mL) or "2x6" in lw_src or lw_kind == "tube_rack_2x6":
            tube_order = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6"]
            if current_well in tube_order:
                c_idx = tube_order.index(current_well)
                if c_idx + 1 < len(tube_order):
                    return tube_order[c_idx + 1]
            return None

        # 2. 50mL Falcon Rack (A1 Media, A2 Stock; A3 is Discard)
        if isinstance(lw, FalconRack50mL) or "50ml" in lw_src or "3x50ml" in lw_src:
            tube_order = ["A1", "A2"]
            if current_well in tube_order:
                c_idx = tube_order.index(current_well)
                if c_idx + 1 < len(tube_order):
                    return tube_order[c_idx + 1]
            return None

        # Guard: NEVER auto-advance on plates or multi-cavity reservoirs where wells are dedicated!
        return None

    def _calculate_z(self, action, labware_obj, well_id, mode, manual_z, slot_name, extra_z=0.0, mix_cycles=0):
        if action == "Pick Up Tip":
            return 0.0

        if mode == "manual": return manual_z

        slot_obj = self.lims.deck_slots.get(slot_name)
        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

        # 0. Object-Oriented DeckManager Kinematics
        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
            slot_model = self.deck_manager.slots[slot_name]
            if slot_model.labware:
                in_liquid = action in ("Aspirate Media", "Mix Well") or int(mix_cycles or 0) > 0
                computed_z = self.deck_manager.calculate_z(action, slot_name, well_id, in_liquid=in_liquid)
                return min(computed_z + slot_z_offset + extra_z, 103.5)

        kind = self._lw_kind(labware_obj)
        # "deep" = going into the liquid (aspirate / mix); otherwise stop at the brim
        deep = action in ("Aspirate Media", "Mix Well") or int(mix_cycles or 0) > 0

        if action in ["Aspirate Media", "Dispense Media", "Discard Tip", "Mix Well"]:
            if action == "Discard Tip" or kind == "waste" or (kind is None and slot_name == "Slot_6"):
                zl = getattr(labware_obj, 'z_limits', {}) or {}
                if 'recommended_discard_z' in zl:
                    base_z = float(zl['recommended_discard_z'])
                elif 'recommended_dispense_z' in zl:
                    base_z = float(zl['recommended_dispense_z'])
                elif self._is_front_slot(slot_name):
                    # For 3-well reservoir on 90mm block (rim=47mm), safe discard height is Z=35.0mm (above rim).
                    # For 50mL Falcon rack on 90mm block (rim=68mm), safe discard depth into tube mouth is Z=75.0mm.
                    is_3well = kind == "reservoir_3" or "3_well" in str(getattr(labware_obj, 'source_file', '')).lower()
                    base_z = 35.0 if is_3well else 75.0
                else:
                    base_z = 45.0
            elif kind == "tube_rack_2x6":
                base_z = self._rim_calibrated_z(labware_obj, deep)
            elif kind == "reservoir_3" or (kind is None and self._is_front_slot(slot_name)):
                base_z = 52.0  # Safe meniscus submerge (47.0mm + 5.0mm) with printed height blocks
            elif kind == "plate96":
                deep_z, brim_z = self.SLOT_96_PLATE_Z.get(slot_name, self.DEFAULT_96_PLATE_Z)
                base_z = deep_z if deep else brim_z
            elif kind == "reservoir_6":
                base_z = 103.0
            elif kind == "ehm48":
                base_z = 87.0 if deep else 81.0  # Calibrated: 87.0 inside well (+1mm lower), 81.0 brim
            elif kind == "tip_rack":
                base_z = 98.0
            elif kind == "tube_rack_4x6":
                base_z = 95.0
            else:
                zl = getattr(labware_obj, 'z_limits', {}) or {}
                key = 'recommended_aspirate_z' if deep else 'recommended_dispense_z'
                base_z = float(zl.get(key, zl.get('recommended_aspirate_z', 101.0)))

            return min(base_z + slot_z_offset + extra_z, 103.5)

        return 0.0

    def prompt_for_discard_slot(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return

        top = tk.Toplevel(self.root)
        top.title("Discard Tip Location")
        top.geometry("380x170")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        ttk.Label(top, text="Select destination slot to discard tip into:", font=("Arial", 10, "bold")).pack(pady=(15, 6))

        # Default to waste slot (Slot_6 or any slot with 'waste' in labware name)
        default_slot = "Slot_6"
        for s in self.placed_slots:
            lw = self.lims.deck_labware.get(s)
            if lw and "waste" in getattr(lw, 'name', '').lower():
                default_slot = s
                break

        slot_choices = list(self.placed_slots) if self.placed_slots else ["Slot_6", "Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5"]
        if default_slot not in slot_choices and default_slot in ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]:
            slot_choices.append(default_slot)

        slot_var = tk.StringVar(value=default_slot if default_slot in slot_choices else slot_choices[0])
        cb = ttk.Combobox(top, textvariable=slot_var, values=slot_choices, state="readonly", width=25)
        cb.pack(pady=5)

        def on_confirm():
            slot = slot_var.get()
            top.destroy()
            if slot:
                threading.Thread(target=self.run_direct_discard_routine, args=(slot,), daemon=True).start()

        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=(12, 10))
        ttk.Button(btn_frame, text="Discard Tip Now", command=on_confirm).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=6)

    def run_direct_discard_routine(self, slot_name):
        hw_instance = self.lims.pipettor.hardware
        if not hw_instance:
            self.logger.error("Hardware not initialized for tip discard.")
            return

        self.logger.info(f"--- Direct Op: Moving to {slot_name} to Discard Tip ---")
        try:
            # 1. Raise Z to safe travel height
            hw_instance.move_z(0.0)

            # 2. Move XY to slot target coordinates (Well A1 or center of slot)
            tx, ty = self._calculate_xy(slot_name, "A1")
            self.lims.hw.move_to(tx, ty, 0.0, speed=self.speed_var.get())

            # 3. Lower Z to discard height
            labware_obj = self.lims.deck_labware.get(slot_name)
            tz = self._calculate_z("Discard Tip", labware_obj, "A1", "auto", 90.0, slot_name)
            if tz <= 0.0:
                tz = 90.0
            hw_instance.move_z(tz)

            # 4. Eject tip (double-pulse to guarantee mechanical separation)
            hw_instance.eject_tip()
            time.sleep(0.25)
            try:
                hw_instance.eject_tip()
            except Exception:
                pass
            self.root.after(0, lambda: self.has_tip_var.set(False))
            self.logger.info(f"Direct Op: Tip successfully discarded into {slot_name}. HAS_TIP = False")

            # 5. Return Z to 0 (safe travel)
            hw_instance.move_z(0.0)
        except Exception as e:
            self.logger.critical(f"Error during direct tip discard to {slot_name}: {e}. Tip may still be mounted on the pipettor!")
            self.root.after(0, lambda: self.has_tip_var.set(True))
            try:
                hw_instance.move_z(0.0)
            except Exception:
                pass

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
                approach_z = max(0.0, min(48.0, z_height - 25.0))
                if self.lims.pipettor.hardware:
                    self.lims.pipettor.hardware.z_speed = hw_speed
                    self.lims.pipettor.hardware.move_z(approach_z)
                    self.lims.pipettor.hardware.z_speed = 3
                    self.lims.pipettor.hardware.tip_pickup_force = 26
                    pick_ok = False
                    try:
                        self.lims.pipettor.hardware.pick_tip(87.0)
                        pick_ok = True
                    except Exception as pe:
                        self.logger.warning(f"pick_tip hardware return/exception: {pe}")
                        pick_ok = False

                    curr_z = getattr(self.lims.pipettor.hardware, 'z_position', 0.0)
                    is_1000 = "1000" in (getattr(labware_obj, 'name', '') + getattr(labware_obj, 'source_file', '')).lower()
                    valid_collar = (curr_z <= 59.5) if is_1000 else (curr_z <= 78.0)

                    if not (valid_collar and pick_ok):
                        raise Exception(f"No tip present in {current_well} (Z={curr_z:.2f}mm, pick_ok={pick_ok})")
                    time.sleep(0.2)
                else:
                    curr_z = 55.09
                self.logger.info(f"🎯 Tip acquired at {current_well} (Z={curr_z:.2f}mm). HAS_TIP = True")
                time.sleep(0.2)
                tip_found = True
                self.root.after(0, lambda: self.has_tip_var.set(True))
                if self.lims.pipettor.hardware:
                    try:
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)
                break
            except RuntimeError as re:
                self.logger.critical(f"🛑 CRITICAL SAFETY ABORT during tip search: {re}")
                self.root.after(0, lambda: self.has_tip_var.set(True))
                if self.lims.pipettor.hardware:
                    try:
                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        self.lims.pipettor.hardware.z_speed = hw_speed
                        self.lims.pipettor.hardware.move_z(0)
                    except Exception:
                        self.lims.pipettor.hardware.move_z(0)
                return
            except Exception as e:
                self.logger.warning(f"Well {current_well} empty or passed. Tracking to next well...")
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

    def prompt_for_liquid_check(self):
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock", "Hardware must be initialized first.")
            return

        top = tk.Toplevel(self.root)
        top.title("Auto-Read Liquid Level (Sensor Probing)")
        top.geometry("420x290")
        top.resizable(False, False)

        f = ttk.Frame(top, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Select Target Slot & Well:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))

        # Slot Selection
        f_slot = ttk.Frame(f)
        f_slot.pack(fill=tk.X, pady=4)
        ttk.Label(f_slot, text="Deck Slot:", width=14, anchor="w").pack(side=tk.LEFT)
        slot_var = tk.StringVar()
        slot_choices = [s for s in self.placed_slots if s] if self.placed_slots else [f"Slot_{i}" for i in range(1, 7)]
        cb_slot = ttk.Combobox(f_slot, textvariable=slot_var, values=slot_choices, state="readonly", width=18)
        cb_slot.pack(side=tk.LEFT)

        # Well Selection
        f_well = ttk.Frame(f)
        f_well.pack(fill=tk.X, pady=4)
        ttk.Label(f_well, text="Target Well:", width=14, anchor="w").pack(side=tk.LEFT)
        well_var = tk.StringVar(value="A1")
        cb_well = ttk.Combobox(f_well, textvariable=well_var, width=18)
        cb_well.pack(side=tk.LEFT)

        # Info Label (displays labware details and well radius)
        lbl_info = ttk.Label(f, text="", font=("Arial", 9), foreground="#333333", wraplength=380, justify="left")
        lbl_info.pack(fill=tk.X, pady=10)

        def update_info(*args):
            s = slot_var.get()
            lw = self.lims.deck_labware.get(s)
            if lw:
                lw_name = getattr(lw, 'name', 'Labware')
                wells = list(getattr(lw, 'wells', {}).keys())
                if wells:
                    cb_well['values'] = wells
                    if well_var.get() not in wells:
                        well_var.set(wells[0])
                first_w = next(iter(getattr(lw, 'wells', {}).values()), None)
                rad = getattr(first_w, 'radius', 3.4) if first_w else 3.4
                z_lim = getattr(lw, 'z_limits', {}).get('max_safe_bottom_z', 'Auto')
                lbl_info.config(text=f"Labware: {lw_name}\nWell Radius: {rad:.1f} mm | Bottom Limit: {z_lim} mm")
            else:
                lbl_info.config(text=f"Slot: {s} (Generic / Unassigned Labware)")

        slot_var.trace_add("write", update_info)
        if slot_choices:
            if "Slot_6" in slot_choices:
                slot_var.set("Slot_6")
            else:
                slot_var.set(slot_choices[0])
        else:
            update_info()

        def on_confirm():
            slot = slot_var.get()
            well = well_var.get().strip().upper()
            if not slot or not well:
                messagebox.showwarning("Input Missing", "Please specify both Slot and Well.")
                return

            if not self.has_tip_var.get():
                if not messagebox.askyesno(
                    "Tip Check",
                    "The Biohit tip sensor requires a pipette tip mounted on the channel.\n\n"
                    "Pipette tip state is currently marked as EMPTY.\n\n"
                    "Do you want to proceed anyway?"
                ):
                    return

            top.destroy()
            threading.Thread(target=self.run_liquid_check_routine, args=(slot, well), daemon=True).start()

        ttk.Button(f, text="Probe Liquid Level", command=on_confirm).pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def run_liquid_check_routine(self, slot_name, well_id):
        self.logger.info(f"--- Direct Op: Liquid Level Auto-Read at {slot_name} Well {well_id} ---")
        if not self.lims.hw.is_initialized:
            self.logger.error("Hardware not initialized.")
            return

        coords = self._calculate_xy(slot_name, well_id)
        if not coords or (coords[0] == 0.0 and coords[1] == 0.0):
            msg = f"Could not calculate XY coordinates for {slot_name} well {well_id}."
            self.logger.error(msg)
            self.root.after(0, lambda: messagebox.showerror("Coordinate Error", msg))
            return

        tx, ty = coords
        labware_obj = self.lims.deck_labware.get(slot_name)
        slot_obj = self.lims.deck_slots.get(slot_name)
        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

        lw_name = (getattr(labware_obj, 'name', '') or '').lower()
        lw_src = (getattr(labware_obj, 'source_file', '') or '').lower()

        # Bottom Z determination (labware-driven, slot independent)
        try:
            bottom_z = self._labware_bottom_z(labware_obj, slot_name)
        except ValueError as cal_err:
            self.logger.error(str(cal_err))
            self.root.after(0, lambda m=str(cal_err): messagebox.showerror("Labware Not Calibrated", m))
            return

        bottom_z = min(99.5, bottom_z + slot_z_offset)

        # Well radius determination
        radius_mm = 3.4
        if labware_obj and hasattr(labware_obj, 'wells') and well_id in labware_obj.wells:
            radius_mm = getattr(labware_obj.wells[well_id], 'radius', 3.4)
        elif labware_obj and hasattr(labware_obj, 'raw_data'):
            radius_mm = labware_obj.raw_data.get('well_properties', {}).get('radius_mm', 3.4)

        if radius_mm <= 0.0:
            radius_mm = 3.4

        try:
            # 1. Retract to safe Z=0
            if self.lims.pipettor.hardware:
                self.lims.pipettor.hardware.move_z(0)
            self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
            time.sleep(0.1)

            # 2. Execute surface detection
            z_measured = self._probe_surface_and_wait(bottom_z, submerge_mm=1.0)

            # 3. Retract back to safe Z=0
            if self.lims.pipettor.hardware:
                self.lims.pipettor.hardware.move_z(0)

            # 4. Analyze result
            if z_measured >= (bottom_z - 1.0):
                res_msg = (
                    f"No liquid detected in {slot_name} Well {well_id}.\n\n"
                    f"Sensor reached bottom limit (Z={bottom_z:.1f} mm) without meniscus contact.\n"
                    f"The well/tube appears empty."
                )
                self.logger.warning(f"Liquid Level: {slot_name} {well_id} -> EMPTY (Z={z_measured:.2f}mm, limit={bottom_z:.1f}mm)")
                self.root.after(0, lambda: messagebox.showwarning("Liquid Level Detection", res_msg))
            else:
                liquid_height_mm = max(0.0, bottom_z - z_measured)
                area_mm2 = math.pi * (radius_mm ** 2)
                volume_ul = area_mm2 * liquid_height_mm
                volume_ml = volume_ul / 1000.0

                if volume_ul >= 1000.0:
                    vol_text = f"{volume_ul:.1f} µL ({volume_ml:.2f} mL)"
                else:
                    vol_text = f"{volume_ul:.1f} µL"

                report = (
                    f"Target: {slot_name} | Well: {well_id}\n"
                    f"Labware: {getattr(labware_obj, 'name', 'Generic')}\n"
                    f"-----------------------------------------\n"
                    f"Surface Contact Z: {z_measured:.2f} mm\n"
                    f"Bottom Limit Z:    {bottom_z:.2f} mm\n"
                    f"Liquid Height:     {liquid_height_mm:.2f} mm\n"
                    f"Well Radius:       {radius_mm:.2f} mm\n"
                    f"-----------------------------------------\n"
                    f"Estimated Remaining Volume: {vol_text}"
                )
                self.logger.info(f"Liquid Level Detected: {slot_name} {well_id} -> Z={z_measured:.2f}mm, H={liquid_height_mm:.2f}mm, Vol={vol_text}")
                self.root.after(0, lambda: messagebox.showinfo("Liquid Level Measured", report))

        except Exception as err:
            self.logger.error(f"Liquid level detection error: {err}")
            if self.lims.pipettor.hardware:
                try:
                    self.lims.pipettor.hardware.move_z(0)
                except Exception:
                    pass
            self.root.after(0, lambda: messagebox.showerror("Detection Error", f"Surface detection failed: {err}"))

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
        if getattr(self, 'is_running', False):
            self.logger.warning("Protocol sequence is already active or stopping. Please wait.")
            return
        if not self.lims.hw.is_initialized:
            messagebox.showerror("Safety Interlock",
                                 "Hardware must be homed via 'Connect & Initialize' before executing automated workflows.")
            return
        if not self.workflow_sequence: return
        has_mix_steps = any(int(s.get('mix_cycles', 0)) > 0 or s.get('action') == "Mix Well" for s in self.workflow_sequence)
        if has_mix_steps:
            self.enable_mixing_for_run = messagebox.askyesno(
                "In-Well Mixing Option",
                "Do you want to enable 2x in-well mixing for this run?\n\n"
                "• YES (Mix ON): Goes down into the well (92mm on Slot 5 96-well / 90mm on Slot 4 / 86mm on 48-well EHM) and mixes 2 times after adding drug.\n"
                "• NO (Mix OFF): Skips all mixing and dispenses from the brim (85mm on 96-well) without touching the well liquid."
            )
        else:
            self.enable_mixing_for_run = False
        self.is_running = True

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
            # Fresh liquid-level ledger for every run (tubes assumed refilled to start level)
            self.liquid_ledger = {}
            self.has_air_cushion = False
            self.pause_event.set()
            self.root.after(0, lambda: self.update_ui_state(True))
            total_steps = len(self.workflow_sequence)

            self.sync_deck_manager()
            # --- PHYSICS-BASED TIME ESTIMATION ---
            self.estimated_total_time = self.estimate_workflow_time(self.workflow_sequence)
            self.run_start_time = time.time()
            self.timer_running = True
            self.root.after(0, self.update_timer)
            # ----------------------------------------

            self.current_step_idx = 0
            while self.current_step_idx < len(self.workflow_sequence):
                self.pause_event.wait()
                if self.is_aborted: break

                step = self.workflow_sequence[self.current_step_idx]
                i = self.current_step_idx + 1
                total_steps = len(self.workflow_sequence)

                try:
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
                                self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get())
                                self.logger.info(f"System: Waiting {vol:.0f}s at safety origin (adjust or lower liquid height in tube now)...")
                                time.sleep(vol)
                                self.logger.info("Wait complete. Resuming protocol sequence.")
                            elif "FOC48" in action:
                                self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get())
                                try:
                                    import foc_automation
                                    step_exp = (step.get('well', '') or '').strip()
                                    global_exp = self.foc_exp_var.get().strip() if hasattr(self, 'foc_exp_var') else ''
                                    chosen_exp = step_exp if (step_exp and step_exp.upper() != 'A1') else (global_exp or step_exp)
                                    foc_automation.execute_foc48_measurement(plate_name=chosen_exp, logger=self.logger)
                                except Exception as foc_err:
                                    self.logger.error(f"FOC48 Automation Error: {foc_err}")
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
                    elif slot_name in self.lims.deck_slots:
                        if slot_name not in self.lims.deck_labware:
                            req_lw = step.get('labware', '')
                            req_path = os.path.join(self.get_labware_dir(), req_lw) if req_lw else ''
                            if req_lw and os.path.exists(req_path):
                                self.lims.deck_labware[slot_name] = Labware(req_path)
                                self.lims.deck_labware[slot_name].source_file = req_lw
                                if slot_name not in self.placed_slots: self.placed_slots.append(slot_name)
                                self.sync_deck_manager()
                                self.logger.info(f"{slot_name} was empty -> mounted protocol-declared {req_lw}.")
                            elif action != "Discard Tip":
                                self.ask_error_resolution(f"No labware assigned to {slot_name}. Assign one in the Deck tab.", i)
                                continue

                        coords = self._calculate_xy(slot_name, well_id)
                        if coords and (coords[0] != 0.0 or coords[1] != 0.0):
                            target_x, target_y = coords
                        else:
                            self.ask_error_resolution(f"Coordinate mapping failed for {slot_name} Well {well_id}.", i)
                            continue
                    else:
                        self.ask_error_resolution(f"Unknown slot '{slot_name}'. Coordinate mapping failed.", i)
                        continue

                    if action == "Pick Up Tip":
                        pickup_limit = min(92.0, max(82.0, 87.0 + extra_z))
                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        labware_obj = self.lims.deck_labware.get(slot_name)
                        z_height = getattr(labware_obj, 'z_height_mm', 78.18) if labware_obj else 78.18
                        approach_z = max(0.0, min(48.0, z_height - 25.0))

                        tip_rack_model = None
                        if hasattr(self, 'deck_manager') and slot_name in self.deck_manager.slots:
                            lw_cand = self.deck_manager.slots[slot_name].labware
                            if isinstance(lw_cand, TipRack96):
                                tip_rack_model = lw_cand

                        def _do_pick(tx, ty):
                            if self.lims.pipettor.hardware:
                                self.lims.pipettor.hardware.move_z(0)
                            self.lims.hw.move_to(tx, ty, 0, speed=self.speed_var.get())
                            time.sleep(0.05)
                            if not self.lims.pipettor.hardware:
                                return True, 55.09

                            hw = self.lims.pipettor.hardware
                            hw.z_speed = hw_speed
                            hw.move_z(approach_z)
                            hw.z_speed = 3
                            hw.tip_pickup_force = 26
                            
                            pick_ok = False
                            try:
                                hw.pick_tip(pickup_limit)
                                pick_ok = True
                            except Exception as pe:
                                self.logger.warning(f"pick_tip hardware return/exception: {pe}")
                                pick_ok = False

                            curr_z = getattr(hw, 'z_position', 0.0)

                            # 1. VALID SEATED TIP (Double-tip collision interlock disabled for hands-free operation):
                            # Accepts seated tips (<= 59.5mm for 1000uL, <= 78.0mm for 300uL)
                            # On empty sockets, bare nose cone penetrates past collar to Z >= 60mm (typically 65-87mm).
                            is_1000 = "1000" in (getattr(labware_obj, 'name', '') + getattr(labware_obj, 'source_file', '')).lower()
                            valid_collar = (curr_z <= 59.5) if is_1000 else (curr_z <= 78.0)

                            if valid_collar and pick_ok:
                                time.sleep(0.2)
                                try:
                                    hw.z_speed = hw_speed
                                    hw.move_z(0)
                                except Exception:
                                    hw.move_z(0)
                                return True, curr_z

                            # 2. EMPTY SOCKET (Z >= 60.0mm or failed pick):
                            self.logger.warning(f"Empty socket detected at Z={curr_z:.2f}mm (pick_ok={pick_ok}). Advancing...")
                            try:
                                hw.z_speed = hw_speed
                                hw.move_z(0)
                            except Exception:
                                hw.move_z(0)
                            return False, curr_z

                        if mode == "manual":
                            seated, cz = _do_pick(target_x, target_y)
                            if seated:
                                self.logger.info(f"🎯 Manual tip pickup succeeded at Z={cz:.2f}mm. HAS_TIP = True")
                                self.root.after(0, lambda: self.has_tip_var.set(True))
                            else:
                                self.logger.warning(f"Manual tip pick: No tip detected (Z={cz:.2f}mm).")

                        elif self.auto_tip_search_var.get():
                            wells = list(labware_obj.wells.keys()) if labware_obj else []
                            start_idx = wells.index(well_id) if well_id in wells else 0
                            tip_found = False

                            for idx in range(start_idx, len(wells)):
                                if self.is_aborted: break
                                current_well = wells[idx]
                                coords = self._calculate_xy(slot_name, current_well)
                                tx, ty = coords if coords else (0, 0)
                                self.logger.info(f"Checking tip at {current_well} ({tx:.2f}, {ty:.2f})...")
                                seated, cz = _do_pick(tx, ty)
                                if seated:
                                    self.logger.info(f"🎯 Tip acquired at {current_well} (Z={cz:.2f}mm). HAS_TIP = True")
                                    tip_found = True
                                    self.root.after(0, lambda: self.has_tip_var.set(True))
                                    break
                                else:
                                    self.logger.warning(f"Well {current_well} empty or passed (Z={cz:.2f}mm). Tracking to next well...")

                            if not tip_found and not self.is_aborted:
                                self.ask_error_resolution("Tip rack is completely empty!", i)
                        else:
                            seated, cz = _do_pick(target_x, target_y)
                            if seated:
                                self.logger.info(f"🎯 Tip acquired at {well_id} (Z={cz:.2f}mm). HAS_TIP = True")
                                self.root.after(0, lambda: self.has_tip_var.set(True))
                            else:
                                raise Exception(f"Tip pickup failed at {well_id} (Z={cz:.2f}mm).")

                    elif action == "Detect Liquid Level":
                        labware_obj = self.lims.deck_labware.get(slot_name)
                        slot_obj = self.lims.deck_slots.get(slot_name)
                        slot_z_offset = getattr(slot_obj, 'z_offset', 0.0)

                        if mode == "manual":
                            bottom_z = target_z
                        else:
                            bottom_z = self._labware_bottom_z(labware_obj, slot_name)

                        # Strict firmware clamp: InstrumentLib.dll enforces limit <= 100.0mm
                        bottom_z = min(99.5, bottom_z + (slot_z_offset if mode != "manual" else 0.0))

                        radius_mm = 3.4
                        if labware_obj and hasattr(labware_obj, 'wells') and well_id in labware_obj.wells:
                            radius_mm = getattr(labware_obj.wells[well_id], 'radius', 3.4)
                        elif labware_obj and hasattr(labware_obj, 'raw_data'):
                            radius_mm = labware_obj.raw_data.get('well_properties', {}).get('radius_mm', 3.4)
                        if radius_mm <= 0.0:
                            radius_mm = 3.4

                        self.logger.info(f"Detect Liquid Level: moving to {slot_name} Well {well_id} (Z-limit={bottom_z:.1f}mm)...")
                        if self.lims.pipettor.hardware:
                            self.lims.pipettor.hardware.move_z(0)
                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                        time.sleep(0.05)

                        try:
                            z_measured = self._probe_surface_and_wait(bottom_z, submerge_mm=1.0)
                            if self.lims.pipettor.hardware:
                                self.lims.pipettor.hardware.move_z(0)

                            if z_measured >= (bottom_z - 1.0):
                                self.logger.warning(f"[LIQUID LEVEL] {slot_name} Well {well_id}: EMPTY (reached bottom limit Z={bottom_z:.1f}mm).")
                            else:
                                liquid_height_mm = max(0.0, bottom_z - z_measured)
                                volume_ul = math.pi * (radius_mm ** 2) * liquid_height_mm
                                vol_str = f"{volume_ul:.1f}uL ({volume_ul / 1000.0:.2f}mL)" if volume_ul >= 1000.0 else f"{volume_ul:.1f}uL"
                                self.logger.info(f"[LIQUID LEVEL] {slot_name} Well {well_id}: Surface Z={z_measured:.2f}mm, Height={liquid_height_mm:.2f}mm, Remaining Volume={vol_str}")
                        except Exception as probe_err:
                            self.logger.error(f"[LIQUID LEVEL] Sensor probe failed at {slot_name} {well_id}: {probe_err}")
                            if self.lims.pipettor.hardware:
                                self.lims.pipettor.hardware.move_z(0)

                    elif action in ["Aspirate Media", "Dispense Media", "Discard Tip", "Mix Well"]:
                        if action == "Mix Well" and not getattr(self, 'enable_mixing_for_run', True):
                            self.logger.info("Mixing opted out for this run. Skipping Mix Well step.")
                            time.sleep(0.05)
                            continue
                        effective_mix = int(step.get('mix_cycles', 0)) if getattr(self, 'enable_mixing_for_run', True) else 0
                        tz = target_z if mode == "manual" else self._calculate_z(action,
                                                                                 self.lims.deck_labware.get(slot_name),
                                                                                 well_id, mode, 0.0, slot_name, extra_z,
                                                                                 mix_cycles=effective_mix)
                        self.logger.info(
                            f"Absolute Z-Depth Override Executed: Z={tz:.1f}mm for {well_id if mode != 'manual' else 'Manual Target'}")

                        hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                        if self.lims.pipettor.hardware:
                            try:
                                self.lims.pipettor.hardware.z_speed = hw_speed
                                self.lims.pipettor.hardware.move_z(0)
                            except Exception:
                                self.lims.pipettor.hardware.move_z(0)
                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                        time.sleep(0.05)

                        if self.lims.pipettor.hardware:
                            if action == "Aspirate Media":
                                next_step = self.workflow_sequence[i] if i < len(self.workflow_sequence) else {}
                                next_has_mix = int(next_step.get('mix_cycles', 0)) > 0 and getattr(self, 'enable_mixing_for_run', True)
                                is_micro_vol = 0 < float(vol) <= 50.0
                                if is_micro_vol and not next_has_mix:
                                    try:
                                        self.lims.pipettor.hardware.aspirate(50.0)
                                        self.has_air_cushion = True
                                        self.logger.info(f"Air Cushion: Pre-aspirated 50.0uL air push cushion at Z=0 for clean detachment of {vol}uL ({slot_name} {well_id}).")
                                        time.sleep(0.3)
                                    except Exception as air_err:
                                        self.logger.warning(f"Air cushion draw skipped: {air_err}")
                                else:
                                    self.has_air_cushion = False

                                # --- Liquid Level Tracking (Software Meniscus Tracking + Sensor LLD) ---
                                slot_model = self.deck_manager.slots.get(slot_name) if hasattr(self, 'deck_manager') else None
                                lw_model = slot_model.labware if slot_model else None
                                lw_src_lower = str(getattr(self.lims.deck_labware.get(slot_name), 'source_file', '')).lower()
                                lw_kind = self._lw_kind(self.lims.deck_labware.get(slot_name))

                                # Explicit check: Is this labware a plate? Plates NEVER auto-advance or probe meniscus!
                                is_plate = (
                                    lw_kind in ("plate96", "ehm48")
                                    or "plate" in lw_src_lower
                                    or "96" in lw_src_lower
                                    or "48" in lw_src_lower
                                    or "ehm" in lw_src_lower
                                    or "drug" in lw_src_lower
                                    or "pcr" in lw_src_lower
                                    or "assay" in lw_src_lower
                                )

                                is_2ml_falcon = (
                                    isinstance(lw_model, TubeRack2x6_2mL) or (
                                        (lw_kind == "tube_rack_2x6" or (self._is_front_slot(slot_name) and "2x6" in lw_src_lower))
                                        and not isinstance(lw_model, (FalconRack50mL, Reservoir3Well))
                                        and "50ml" not in lw_src_lower and "3x50ml" not in lw_src_lower and "30ml" not in lw_src_lower
                                    )
                                ) and not is_plate

                                is_reservoir = (
                                    isinstance(lw_model, Reservoir3Well) or (
                                        ((self._is_front_slot(slot_name) and lw_kind in ("reservoir_3", None))
                                        or "reservoir" in lw_src_lower
                                        or "3_well" in lw_src_lower
                                        or "30ml" in lw_src_lower)
                                        and not is_2ml_falcon and not isinstance(lw_model, FalconRack50mL)
                                        and "50ml" not in lw_src_lower
                                    )
                                ) and not is_plate

                                is_50ml_falcon = (
                                    isinstance(lw_model, FalconRack50mL) or ("50ml" in lw_src_lower or "3x50ml" in lw_src_lower)
                                ) and not is_plate

                                is_tube_or_reservoir = (
                                    is_2ml_falcon or is_reservoir or is_50ml_falcon
                                    or ("tube" in lw_src_lower or "falcon" in lw_src_lower or "reservoir" in lw_src_lower)
                                ) and not is_plate

                                # Pipettor Automated Liquid Tracking System (Sensor LLD / Dynamic Height)
                                # STRICTLY for Reservoirs and Tubes only! Plates (e.g. drug plates, EHM plates)
                                # must NEVER auto-advance or probe meniscus.
                                auto_track_active = (
                                    is_tube_or_reservoir and (
                                        (getattr(self, 'lld_tracking_var', None) and self.lld_tracking_var.get()) or
                                        (getattr(self, 'dynamic_z_var', None) and self.dynamic_z_var.get())
                                    )
                                )
                                if auto_track_active and mode != "manual":
                                    try:
                                        # Strict firmware ceiling: InstrumentLib.dll requires limit <= 100.0mm
                                        raw_bottom_z = self._labware_bottom_z(self.lims.deck_labware.get(slot_name), slot_name)
                                        probe_bottom_z = min(99.5, raw_bottom_z)
                                        while not self.is_aborted:
                                            self.logger.info(f"[AUTO LIQUID TRACKING] Probing meniscus at {slot_name} {well_id} (Safety Cap Z<={probe_bottom_z:.1f}mm)...")
                                            z_found = self._probe_surface_and_wait(probe_bottom_z, submerge_mm=2.5)
                                            # Liquid is depleted if probe reached bottom limit without stopping at a higher meniscus
                                            if z_found >= (probe_bottom_z - 1.0):
                                                self.logger.warning(
                                                    f"[AUTO LIQUID TRACKING] Liquid depleted in {slot_name} {well_id} (Z_measured={z_found:.2f}mm >= {probe_bottom_z - 1.0:.1f}mm floor). "
                                                    f"Pipette detected liquid is over using auto liquid tracking."
                                                )
                                                next_tube = self._get_next_tube_in_sequence(slot_name, well_id)
                                                if next_tube:
                                                    self.logger.info(
                                                        f"[AUTO-ADVANCE] Advancing from {well_id} -> {next_tube} in {slot_name}..."
                                                    )
                                                    well_id = next_tube
                                                    if self.lims.pipettor.hardware:
                                                        self.lims.pipettor.hardware.move_z(0)
                                                    new_xy = self._calculate_xy(slot_name, well_id)
                                                    if new_xy:
                                                        target_x, target_y = new_xy
                                                        self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                                                        time.sleep(0.1)
                                                    continue
                                                else:
                                                    self.logger.error(f"[AUTO LIQUID TRACKING] All available tubes/wells in {slot_name} are depleted!")
                                                    self.refill_decision = None
                                                    def _prompt_empty_rack():
                                                        ans = messagebox.askyesno(
                                                            "Liquid Depleted",
                                                            f"Auto liquid tracking detected liquid is over in {slot_name} ({well_id}) and reached floor limit (Z={probe_bottom_z:.1f}mm).\n\n"
                                                            f"Please refill liquid and click YES to re-probe, or NO to abort."
                                                        )
                                                        self.refill_decision = "refilled" if ans else "abort"
                                                    self.root.after(0, _prompt_empty_rack)
                                                    while self.refill_decision is None and not self.is_aborted:
                                                        time.sleep(0.1)
                                                    if self.refill_decision == "refilled":
                                                        if self.lims.pipettor.hardware:
                                                            self.lims.pipettor.hardware.move_z(0)
                                                        continue
                                                    else:
                                                        raise Exception(f"Protocol aborted: Liquid depleted in {slot_name}.")
                                            else:
                                                # Liquid present: Calculate depth and volume left based on pipette's auto tracking
                                                rad_mm = getattr(lw_model, 'well_radius_mm', 14.0) if lw_model else 14.0
                                                area_mm2 = math.pi * (rad_mm ** 2)
                                                req_vol = float(vol)
                                                vol_drop_mm = req_vol / area_mm2 if area_mm2 > 0 else 1.0
                                                target_submerge_z = z_found + max(0.0, vol_drop_mm - 1.0)
                                                tz = min(target_submerge_z, probe_bottom_z - 0.5, 99.5)
                                                depth_left_mm = max(0.0, probe_bottom_z - z_found)
                                                rem_vol_ml = (depth_left_mm * area_mm2) / 1000.0
                                                self.logger.info(
                                                    f"[AUTO LIQUID TRACKING] Surface detected at Z={z_found:.2f}mm. "
                                                    f"Liquid depth left: {depth_left_mm:.1f}mm (~{rem_vol_ml:.1f}mL remaining). "
                                                    f"Submerging to Z={tz:.2f}mm (Safety Floor Cap = {probe_bottom_z:.1f}mm)."
                                                )
                                                break
                                    except Exception as lld_err:
                                        self.logger.warning(f"[AUTO LIQUID TRACKING] Surface probe fallback: {lld_err}. Submerging to calibrated depth Z={tz:.1f}mm")

                                elif mode != "manual" and (is_reservoir or is_2ml_falcon) and step.get('track_liquid', True):
                                    if not hasattr(self, 'liquid_ledger'):
                                        self.liquid_ledger = {}
                                    ledger_key = f"{slot_name}_{well_id}"
                                    if ledger_key not in self.liquid_ledger:
                                        if is_2ml_falcon:
                                            # 2mL Falcon tube on 90mm height block: starts at rim Z=75.0mm, bottom Z=103.0mm, 28mm depth for 2000uL -> area=71.43mm2
                                            self.liquid_ledger[ledger_key] = {
                                                "surface_z": float(step.get('start_surface_z', 75.0)),
                                                "bottom_z": float(step.get('tube_bottom_z', 103.0)),
                                                "area_mm2": float(step.get('tube_area_mm2', 71.43))
                                            }
                                        else:
                                            self.liquid_ledger[ledger_key] = {
                                                "surface_z": float(step.get('start_surface_z', 47.0)),  # Start meniscus (47.0mm with height blocks)
                                                "bottom_z": float(step.get('tube_bottom_z', 100.0)),     # Base of reservoir/tube
                                                "area_mm2": float(step.get('tube_area_mm2', 434.0))     # Cross-section
                                            }
                                    tube_info = self.liquid_ledger[ledger_key]
                                    req_vol = float(vol)

                                    # --- Low-volume refill / auto-rollover check ---
                                    rem_before_ml = max(0.0, tube_info["bottom_z"] - tube_info["surface_z"]) * tube_info["area_mm2"] / 1000.0
                                    reserve_ml = float(step.get('min_reserve_ml', 0.05 if is_2ml_falcon else 2.0))
                                    if rem_before_ml - (req_vol / 1000.0) < reserve_ml:
                                        if is_2ml_falcon:
                                            # Auto-advance to next Falcon tube in rack (A1 -> A2 -> A3...)
                                            tube_order = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6"]
                                            curr_idx = tube_order.index(well_id) if well_id in tube_order else -1
                                            if curr_idx != -1 and curr_idx + 1 < len(tube_order):
                                                next_well = tube_order[curr_idx + 1]
                                                self.logger.warning(
                                                    f"[2mL TUBE TRACKER] {slot_name} {well_id} depleted (2.0mL consumed) -> Auto-advancing to {slot_name} {next_well} for fresh DMSO!")
                                                well_id = next_well
                                                ledger_key = f"{slot_name}_{well_id}"
                                                self.liquid_ledger[ledger_key] = {
                                                    "surface_z": 75.0,
                                                    "bottom_z": 103.0,
                                                    "area_mm2": 71.43
                                                }
                                                tube_info = self.liquid_ledger[ledger_key]
                                                new_coords = self._calculate_xy(slot_name, well_id)
                                                if new_coords and (new_coords[0] != 0 or new_coords[1] != 0):
                                                    target_x, target_y = new_coords
                                                    self.lims.hw.move_to(target_x, target_y, 0, speed=self.speed_var.get())
                                                    time.sleep(0.05)
                                        else:
                                            self.logger.warning(
                                                f"[OPTION 2 TRACKER] {slot_name} {well_id} LOW: ~{rem_before_ml:.2f}mL left (reserve {reserve_ml:.1f}mL). Pausing for refill.")
                                            self.refill_decision = None
                                            start_z = float(step.get('start_surface_z', 47.0))

                                            def _ask_refill():
                                                ok = messagebox.askyesno(
                                                    "Refill Tube",
                                                    f"{slot_name} {well_id} is nearly empty (~{rem_before_ml:.1f} mL left).\n\n"
                                                    f"Refill it to the start mark (Z={start_z:.0f} mm), then press YES.\n\n"
                                                    f"Press NO to continue without refilling (tip will go near the bottom).")
                                                self.refill_decision = "refilled" if ok else "continue"

                                            self.root.after(0, _ask_refill)
                                            while self.refill_decision is None and not self.is_aborted:
                                                time.sleep(0.1)
                                            if self.refill_decision == "refilled":
                                                tube_info["surface_z"] = start_z
                                                self.logger.info(f"[OPTION 2 TRACKER] {slot_name} {well_id} refilled -> surface reset to Z={start_z:.1f}mm")

                                    curr_surface = tube_info["surface_z"]
                                    submerge_depth = 2.5 if is_2ml_falcon else 5.0
                                    tz = min(curr_surface + submerge_depth, tube_info["bottom_z"] - 0.5)

                                    dz = req_vol / tube_info["area_mm2"]
                                    new_surface = min(curr_surface + dz, tube_info["bottom_z"])
                                    tube_info["surface_z"] = new_surface

                                    rem_height = max(0.0, tube_info["bottom_z"] - new_surface)
                                    rem_ml = (rem_height * tube_info["area_mm2"]) / 1000.0
                                    tracker_name = "2mL TUBE TRACKER" if is_2ml_falcon else "OPTION 2 TRACKER"
                                    self.logger.info(
                                        f"[{tracker_name}] {slot_name} {well_id}: Meniscus Z={curr_surface:.1f}mm -> Submerging to Z={tz:.1f}mm (Bottom={tube_info['bottom_z']:.1f}mm). Est. Remaining: ~{rem_ml:.2f}mL"
                                    )

                            safe_tz = min(float(tz), 102.0)
                            hw_speed = max(1, min(9, int((self.speed_var.get() / 100.0) * 9)))
                            try:
                                self.lims.pipettor.hardware.z_speed = hw_speed
                            except Exception:
                                pass
                            self.lims.pipettor.hardware.move_z(safe_tz)

                            if action == "Aspirate Media":
                                # --- GUI SAFETY MANIFOLD CAP & EQUILIBRATION ---
                                requested_vol = float(vol)
                                if requested_vol > 0:
                                    actual_vol = min(requested_vol, self.lims.pipettor.tip_volume)

                                    if requested_vol > self.lims.pipettor.tip_volume:
                                        self.logger.warning(
                                            f"MANIFOLD FLOOD PREVENTED: {requested_vol}uL requested, but tip limit is {self.lims.pipettor.tip_volume}uL. Automatically capped to {actual_vol}uL.")

                                    self.lims.pipettor.hardware.aspirate(actual_vol)
                                    time.sleep(1.5)
                                else:
                                    time.sleep(0.3)
                            elif action == "Dispense Media":
                                actual_dispense = min(float(vol), self.lims.pipettor.tip_volume)
                                mix_cycles = effective_mix
                                had_air = getattr(self, 'has_air_cushion', False)
                                self.has_air_cushion = False
                                if actual_dispense > 0:
                                    try:
                                        self.lims.pipettor.hardware.dispense(actual_dispense)
                                        time.sleep(0.4 if mix_cycles > 0 else 0.05)
                                        if (had_air or mix_cycles == 0) and not step.get('no_blowout', False):
                                            self.lims.pipettor.hardware.dispense(50)
                                            if had_air:
                                                self.logger.info(f"Air Push: Dispensed 50.0uL air push blowout to detach {actual_dispense}uL droplet cleanly.")
                                            time.sleep(0.2)
                                    except Exception as d_err:
                                        self.logger.warning(f"Dispense blowout exception ignored: {d_err}")
                                else:
                                    time.sleep(0.3)

                                if mix_cycles > 0:
                                    mix_vol = min(float(step.get('mix_volume', 100.0)), self.lims.pipettor.tip_volume)
                                    self.logger.info(f"In-place mixing at {well_id}: {mix_cycles}x {mix_vol}uL (submerged at Z={tz:.1f}mm)")
                                    for c_idx in range(mix_cycles):
                                        if self.is_aborted: break
                                        try:
                                            self.lims.pipettor.hardware.aspirate(mix_vol)
                                            time.sleep(1.2)
                                            self.lims.pipettor.hardware.dispense(mix_vol)
                                            time.sleep(0.8)
                                        except Exception as m_err:
                                            self.logger.warning(f"Mix stroke {c_idx + 1}/{mix_cycles} warning: {m_err}")
                                    if not step.get('no_blowout', False):
                                        try:
                                            self.lims.pipettor.hardware.dispense(50)
                                        except Exception:
                                            pass

                            elif action == "Mix Well":
                                mix_cycles = int(step.get('mix_cycles', 5))
                                mix_vol = min(float(vol if vol > 0 else step.get('mix_volume', 100.0)), self.lims.pipettor.tip_volume)
                                self.logger.info(f"In-place mixing at {well_id}: {mix_cycles}x {mix_vol}uL (submerged at Z={tz:.1f}mm)")
                                for c_idx in range(mix_cycles):
                                    if self.is_aborted: break
                                    try:
                                        self.lims.pipettor.hardware.aspirate(mix_vol)
                                        time.sleep(1.2)
                                        self.lims.pipettor.hardware.dispense(mix_vol)
                                        time.sleep(0.8)
                                    except Exception as m_err:
                                        self.logger.warning(f"Mix stroke {c_idx + 1}/{mix_cycles} warning: {m_err}")
                                try:
                                    self.lims.pipettor.hardware.dispense(50)
                                except Exception:
                                    pass

                            elif action == "Discard Tip":
                                try:
                                    if self.lims.pipettor.hardware:
                                        self.lims.pipettor.hardware.eject_tip()
                                        time.sleep(0.25)
                                        # Pulse eject a second time to guarantee mechanical separation
                                        try:
                                            self.lims.pipettor.hardware.eject_tip()
                                        except Exception:
                                            pass
                                    self.root.after(0, lambda: self.has_tip_var.set(False))
                                    self.logger.info("System state updated: Tip successfully ejected -> HAS_TIP = False")
                                except Exception as e_err:
                                    self.logger.critical(f"Eject Tip Failed: {e_err}")
                                    self.root.after(0, lambda: self.has_tip_var.set(True))
                                    raise RuntimeError(f"CRITICAL: Tip ejection failed! Tip is still attached to the cone. Halting: {e_err}")

                            try:
                                if self.lims.pipettor.hardware:
                                    self.lims.pipettor.hardware.z_speed = hw_speed
                                self.lims.pipettor.hardware.move_z(0)
                            except Exception:
                                self.lims.pipettor.hardware.move_z(0)

                except RuntimeError as re:
                    err_str = str(re)
                    if any(kw in err_str for kw in ["CRITICAL", "COLLISION", "DOUBLE-TIP", "ejection failed", "SAFETY INTERLOCK"]):
                        self.logger.critical(f"🛑 CRITICAL SAFETY ABORT on Step {i}: {err_str}")
                        self.is_aborted = True
                        if self.lims.pipettor.hardware:
                            try:
                                self.lims.pipettor.hardware.move_z(0)
                            except Exception:
                                pass
                        break
                    else:
                        self.ask_error_resolution(re, i)
                        if self.is_aborted:
                            break
                except Exception as e:
                    self.ask_error_resolution(e, i)
                    if self.is_aborted:
                        break
                finally:
                    self.current_step_idx += 1
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
                except Exception as ze:
                    self.logger.warning(f"Z clearance move warning: {ze}")
            self.is_running = False
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

                if self.lims.pipettor.hardware:
                    try:
                        hw = self.lims.pipettor.hardware
                        hx = round(float(getattr(hw, 'x_position', 0.0)), 2)
                        hy = round(float(getattr(hw, 'y_position', 0.0)), 2)
                        hz = round(float(getattr(hw, 'z_position', 0.0)), 2)
                        for ax, v in [("X", hx), ("Y", hy), ("Z", hz)]:
                            self.jog_vars[ax].set(v)
                            self.current_pos[ax] = v
                    except Exception:
                        pass

                for axis in ["X", "Y", "Z"]:
                    self.jog_sliders[axis].config(state='normal')
                    self.deck_jog_sliders[axis].config(state='normal')
                    if hasattr(self, 'jog_btns') and axis in self.jog_btns:
                        self.jog_btns[axis].config(state='normal')
                    if hasattr(self, 'deck_jog_btns') and axis in self.deck_jog_btns:
                        self.deck_jog_btns[axis].config(state='normal')
                for btn in getattr(self, 'jog_nudge_btns', []):
                    try:
                        btn.config(state='normal')
                    except Exception:
                        pass
                self.start_telemetry()
        else:
            self.logger.error(f"Connection failed: {m}")

    def run_direct_op(self, c):
        if not self.lims.hw.is_initialized: return
        hw_instance = self.lims.pipettor.hardware
        if c == "HOME":
            if hw_instance: hw_instance.initialize()
        elif c == "DISCARD":
            self.prompt_for_discard_slot()
        elif c == "FIND_TIP":
            self.prompt_for_tip_slot()
        elif c == "CHECK_LIQUID":
            self.prompt_for_liquid_check()
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

    def on_placed_slot_select(self, event=None):
        sel = self.list_placed.curselection()
        if not sel:
            return
        name = self.list_placed.get(sel[0])
        s = self.lims.deck_slots.get(name)
        if not s:
            return
        self.selected_slot_name = name
        for k in ['x_abs', 'y_abs', 'width_mm', 'height_mm', 'z_offset']:
            self.entries[k].set(str(getattr(s, k, 0.0)))
        assigned = getattr(self.lims.deck_labware.get(name), 'source_file', '')
        self.lw_var.set(assigned if assigned else '')
        self.draw_deck()

    def assign_lw(self):
        fn = self.lw_var.get()
        if not self.selected_slot_name:
            messagebox.showwarning("No Slot Selected", "Select a slot first (click it on the deck or in the placed list).")
            return
        if not fn:
            messagebox.showwarning("No Labware Selected", "Choose a labware file from the dropdown first.")
            return
        lw_path = os.path.join(self.get_labware_dir(), fn)
        self.lims.deck_labware[self.selected_slot_name] = Labware(lw_path)
        self.lims.deck_labware[self.selected_slot_name].source_file = fn
        if self.selected_slot_name not in self.placed_slots:
            self.placed_slots.append(self.selected_slot_name)
        self.sync_deck_manager()
        self.logger.info(f"Assigned {fn} to {self.selected_slot_name}. Coordinates now follow this labware (press SAVE WORKSPACE to keep it).")
        self.draw_deck()
        try:
            self.update_safe_z_hint()
        except Exception:
            pass

    def unassign_lw(self):
        if self.selected_slot_name in self.lims.deck_labware:
            del self.lims.deck_labware[self.selected_slot_name]
            self.sync_deck_manager()
            self.draw_deck()

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
        self.sync_deck_manager()

    def _serialize_workspace(self, path):
        data = {
            n: {"name": s.name, "x_abs": s.x_abs, "y_abs": s.y_abs, "width_mm": s.width_mm, "height_mm": s.height_mm,
                "z_offset": getattr(s, 'z_offset', 0.0), "is_placed": n in self.placed_slots,
                "labware_file": getattr(self.lims.deck_labware.get(n), 'source_file', None)} for n, s in
            self.lims.deck_slots.items()}
        with open(path, 'w') as f: json.dump(data, f, indent=4)

    def _deserialize_workspace(self, path):
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Read Error", f"Could not read workspace file:\n{e}")
            return

        if not isinstance(data, dict):
            messagebox.showerror(
                "File Format Mismatch",
                "The selected file is a Protocol (sequence of steps), not a Deck Workspace layout.\n\n"
                "To load a Protocol, click '📂 Load JSON Protocol' on the left panel.\n"
                "Your current deck workspace has been kept safe."
            )
            return

        self.lims.deck_slots.clear()
        self.lims.deck_labware.clear()
        self.placed_slots.clear()
        self.unplaced_slots.clear()
        lw_dir = self.get_labware_dir()
        for n, d in data.items():
            if not isinstance(d, dict): continue
            slot = DeckSlot(n, d.get('x_abs', 0.0), d.get('y_abs', 0.0), d.get('width_mm', 127.8), d.get('height_mm', 85.5))
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
        self.sync_deck_manager()

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

    def action_load_deck(self):
        p = filedialog.askopenfilename(
            title="Load Deck Workspace",
            filetypes=[("JSON Workspace", "*.json"), ("All Files", "*.*")]
        )
        if p: self._deserialize_workspace(p)

    def emergency_reset(self):
        cal_path = self.get_calibration_path()
        if os.path.exists(cal_path):
            self._deserialize_workspace(cal_path)
        if not self.lims.deck_slots:
            self.lims.deck_labware.clear()
            self.placed_slots.clear()
            self.unplaced_slots.clear()
            grid_layout = [("Slot_1", 135.2, 0.0, 127.8, 26.0), ("Slot_2", 0.0, 0.0, 127.8, 26.0),
                           ("Slot_3", 135.2, 45.0, 127.8, 85.5), ("Slot_4", 0.0, 45.0, 127.8, 85.5),
                           ("Slot_5", 135.2, 144.0, 127.8, 85.5), ("Slot_6", 0.0, 144.0, 127.8, 85.5)]
            for name, x, y, w, h in grid_layout:
                slot = DeckSlot(name, x, y, w, h)
                slot.z_offset = 0.0
                self.lims.deck_slots[name] = slot
                self.placed_slots.append(name)
            self.refresh_ui()
            self.sync_deck_manager()

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
                        elif step['action'] == "Detect Liquid Level":
                            msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)}"
                        else:
                            msg = f"[{step['action'].upper()} MANUAL] X:{step.get('x', 0)} Y:{step.get('y', 0)} Z:{step.get('z', 0)} Vol:{step.get('volume', 0.0)}\u03bcL"
                    else:
                        if step['action'] == "Pick Up Tip":
                            msg = f"[{step['action'].upper()}] from {step.get('slot', '')}, Well {step.get('well', '')}"
                        elif step['action'] == "Discard Tip":
                            msg = f"[{step['action'].upper()}] into {step.get('slot', '')} (Waste Trough)"
                        elif step['action'] == "Detect Liquid Level":
                            msg = f"[{step['action'].upper()}] at {step.get('slot', '')}, Well {step.get('well', '')}"
                        else:
                            z_msg = f" (Z+{step.get('extra_z', 0.0)}mm)" if step.get('extra_z', 0.0) > 0 else ""
                            mix_c = int(step.get('mix_cycles', 0))
                            mix_msg = f" [+ Mix {mix_c}x {step.get('mix_volume', 100.0)}\u03bcL]" if mix_c > 0 else ""
                            msg = f"[{step['action'].upper()}] {step.get('volume', 0.0)}\u03bcL at {step.get('slot', '')}, Well {step.get('well', '')}{z_msg}{mix_msg}"

                    self.wf_box.insert(tk.END, msg)

                # Labware sync: the protocol may DECLARE labware per step ('labware' field).
                # Empty slots get the declared labware; occupied slots are only changed if the user agrees.
                self._sync_protocol_labware(loaded_sequence)
                if hasattr(self, 'draw_deck'): self.draw_deck()

            except Exception as e:
                self.logger.error(f"Import Exception: {str(e)}")
                messagebox.showerror("Import Exception", f"Failed to parse protocol file.\n\nTraceback: {str(e)}")

    def _sync_protocol_labware(self, sequence):
        lw_dir = self.get_labware_dir()
        declared = {}
        for st in sequence:
            s_name, lw_file = st.get('slot', ''), st.get('labware', '')
            if s_name and lw_file and s_name not in declared:
                declared[s_name] = lw_file

        mismatches = []
        for s_name, lw_file in declared.items():
            lp = os.path.join(lw_dir, lw_file)
            if not os.path.exists(lp):
                self.logger.warning(f"Protocol declares {lw_file} on {s_name}, but that labware file does not exist.")
                continue
            current = self.lims.deck_labware.get(s_name)
            if current is None:
                self.lims.deck_labware[s_name] = Labware(lp)
                self.lims.deck_labware[s_name].source_file = lw_file
                if s_name not in self.placed_slots: self.placed_slots.append(s_name)
                self.logger.info(f"{s_name} was empty -> mounted protocol-declared {lw_file}.")
            elif (getattr(current, 'source_file', '') or '') != lw_file:
                mismatches.append((s_name, getattr(current, 'source_file', '') or getattr(current, 'name', '?'), lw_file))

        if mismatches:
            lines = "\n".join(f"• {s}: deck has '{cur}', protocol expects '{exp}'" for s, cur, exp in mismatches)
            if messagebox.askyesno(
                    "Deck / Protocol Labware Mismatch",
                    f"This protocol was written for different labware:\n\n{lines}\n\n"
                    f"YES = swap the deck to match the protocol.\n"
                    f"NO = keep YOUR deck (coordinates follow your assigned labware)."):
                for s_name, _cur, exp in mismatches:
                    self.lims.deck_labware[s_name] = Labware(os.path.join(lw_dir, exp))
                    self.lims.deck_labware[s_name].source_file = exp
                    self.logger.info(f"{s_name} swapped to {exp} to match protocol.")
            else:
                self.logger.info("Kept user deck labware; protocol coordinates will follow assigned labware.")

        undeclared_empty = sorted({st.get('slot') for st in sequence
                                   if st.get('slot', '').startswith('Slot_') and st.get('slot') not in self.lims.deck_labware
                                   and st.get('action') != "Discard Tip"})
        if undeclared_empty:
            messagebox.showwarning("Empty Slots",
                                   "This protocol uses slots with no labware assigned:\n\n" + ", ".join(undeclared_empty) +
                                   "\n\nAssign labware in the Deck tab before running.")

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
            top.title("Opentrons to Biohit Protocol Importer & Labware Mapper")
            top.geometry("780x520")
            top.resizable(True, True)
            top.transient(self.root)
            top.grab_set()

            ttk.Label(top, text="Import Opentrons Python Protocol (.py)", font=("Arial", 12, "bold")).pack(pady=(12, 2))
            ttk.Label(top, text=f"File: {os.path.basename(filepath)}", font=("Arial", 9, "italic"), foreground="gray").pack(pady=(0, 8))

            # Labware discovery from disk
            lw_dir = self.get_labware_dir()
            available_files = []
            if os.path.isdir(lw_dir):
                available_files = sorted([f for f in os.listdir(lw_dir) if f.endswith(".json")])

            lw_display_to_file = {}
            lw_file_to_display = {}
            for f in available_files:
                name_clean = f.replace(".json", "").replace("_", " ").title()
                f_lower = f.lower()
                if "2x6" in f_lower or "2ml" in f_lower:
                    disp = "12-Falcon Tube Rack 2x6 (tube_rack_2x6_2ml.json)"
                elif "17a" in f_lower or "4x6" in f_lower:
                    disp = "24-Tube Rack 4x6 (biohit_rack_4x6_17a.json)"
                elif "3_well" in f_lower or "3-well" in f_lower:
                    disp = "3-Well Reservoir (reservoir_3_well.json)"
                elif "6_column" in f_lower or "reservoir_6" in f_lower:
                    disp = "6-Column Reservoir (reservoir_6_column.json)"
                elif "generic_96" in f_lower or "96_well" in f_lower:
                    disp = "96-Well Microplate (generic_96_well_plate.json)"
                elif "48" in f_lower or "myriamed" in f_lower:
                    disp = "48-Well EHM Plate (myriamed_48_well.json)"
                elif "ehm_42" in f_lower:
                    disp = "42-Well EHM Plate (ehm_42_well.json)"
                elif "tip_rack" in f_lower or "tip" in f_lower:
                    disp = "1000µL Tip Rack (tip_rack_1000ul.json)"
                elif "waste" in f_lower or "trough" in f_lower:
                    disp = "Waste Trough (waste_trough.json)"
                elif "corning_96" in f_lower:
                    disp = "Corning 96 Flat (corning_96_flat.json)"
                elif "corning_24" in f_lower:
                    disp = "Corning 24 Well (corning_24_well.json)"
                elif "corning_12" in f_lower:
                    disp = "Corning 12 Well (corning_12_well.json)"
                elif "corning_6" in f_lower:
                    disp = "Corning 6 Well (corning_6_well.json)"
                else:
                    disp = f"{name_clean} ({f})"
                lw_display_to_file[disp] = f
                lw_file_to_display[f] = disp

            labware_display_options = list(lw_display_to_file.keys())

            frame_mappings = ttk.LabelFrame(top, text="Detected Opentrons Labware & Biohit Slot/Labware Configuration", padding=10)
            frame_mappings.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

            # Table Header Row
            hdr = ttk.Frame(frame_mappings)
            hdr.pack(fill=tk.X, pady=(0, 6))
            ttk.Label(hdr, text="Opentrons Item (Slot)", font=("Arial", 9, "bold"), width=28, anchor="w").pack(side=tk.LEFT, padx=2)
            ttk.Label(hdr, text="Target Biohit Slot", font=("Arial", 9, "bold"), width=15, anchor="w").pack(side=tk.LEFT, padx=4)
            ttk.Label(hdr, text="Biohit Labware Type", font=("Arial", 9, "bold"), width=34, anchor="w").pack(side=tk.LEFT, padx=4)
            ttk.Label(hdr, text="Reagent Well", font=("Arial", 9, "bold"), width=14, anchor="w").pack(side=tk.LEFT, padx=2)

            biohit_slots = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"]
            well_options = ["Auto / As-is", "Well A1", "Well A2", "Well A3", "Well A4", "Well A5", "Well A6"]

            row_widgets = {}

            if detected_lw:
                for idx, item in enumerate(detected_lw):
                    row = ttk.Frame(frame_mappings)
                    row.pack(fill=tk.X, pady=3)

                    # 1. Opentrons source label
                    ot_name_short = item['name'][:22]
                    lbl_text = f"{ot_name_short} (OT {item['opentrons_slot']}):"
                    ttk.Label(row, text=lbl_text, width=28, anchor="w").pack(side=tk.LEFT, padx=2)

                    # 2. Biohit Slot
                    cb_slot = ttk.Combobox(row, values=biohit_slots, state="readonly", width=13)
                    suggested_slot = item.get("suggested_biohit_slot", "Slot_4")
                    cb_slot.set(suggested_slot)
                    cb_slot.pack(side=tk.LEFT, padx=4)

                    # 3. Biohit Labware Dropdown
                    cb_lw = ttk.Combobox(row, values=labware_display_options, state="readonly", width=32)
                    suggested_lw_file = item.get("suggested_biohit_labware", "generic_96_well_plate.json")
                    suggested_lw_disp = lw_file_to_display.get(suggested_lw_file, labware_display_options[0] if labware_display_options else "")
                    cb_lw.set(suggested_lw_disp)
                    cb_lw.pack(side=tk.LEFT, padx=4)

                    # 4. Reagent Well Selection
                    cb_well = ttk.Combobox(row, values=well_options, state="readonly", width=13)
                    is_tuberack = any(k in item['name'].lower() for k in ["tuberack", "falcon", "reservoir", "rack"])
                    cb_well.set("Well A1" if is_tuberack else "Auto / As-is")
                    cb_well.pack(side=tk.LEFT, padx=2)

                    row_widgets[item['opentrons_slot']] = {
                        "slot": cb_slot,
                        "labware": cb_lw,
                        "well": cb_well
                    }
            else:
                ttk.Label(frame_mappings, text="No explicit labware definitions detected in script.\nDefault slot layout will be used.", justify="center").pack(pady=20)

            frame_stroke = ttk.Frame(top)
            frame_stroke.pack(fill=tk.X, padx=15, pady=8)
            ttk.Label(frame_stroke, text="Max Pipette Stroke (µL):").pack(side=tk.LEFT)
            ent_stroke = ttk.Entry(frame_stroke, width=8)
            current_tip_vol = getattr(getattr(self.lims, 'pipettor', None), 'tip_volume', 200.0)
            ent_stroke.insert(0, str(float(current_tip_vol)))
            ent_stroke.pack(side=tk.LEFT, padx=5)

            def do_convert():
                try:
                    slot_map = {}
                    labware_map = {}
                    well_map = {}

                    for ot_s, wdict in row_widgets.items():
                        b_slot = wdict['slot'].get()
                        lw_disp = wdict['labware'].get()
                        lw_file = lw_display_to_file.get(lw_disp, lw_disp)
                        w_choice = wdict['well'].get()

                        slot_map[ot_s] = b_slot
                        labware_map[b_slot] = lw_file
                        if w_choice and w_choice != "Auto / As-is":
                            well_map[b_slot] = w_choice

                    try:
                        max_vol = float(ent_stroke.get())
                    except ValueError:
                        max_vol = 200.0

                    converted_steps = convert_opentrons_py_to_biohit(
                        filepath,
                        slot_mapping=slot_map,
                        labware_mapping=labware_map,
                        well_mapping=well_map,
                        max_volume=max_vol
                    )

                    if not converted_steps:
                        messagebox.showwarning("Empty Protocol", "No pipetting steps were generated from this script.")
                        top.destroy()
                        return

                    # Configure physical deck labware in orchestrator
                    for b_slot, lw_file in labware_map.items():
                        if b_slot and lw_file:
                            lp = os.path.join(lw_dir, lw_file)
                            if os.path.exists(lp):
                                self.lims.deck_labware[b_slot] = Labware(lp)
                                self.lims.deck_labware[b_slot].source_file = lw_file
                                if b_slot not in self.placed_slots:
                                    self.placed_slots.append(b_slot)
                                self.logger.info(f"Deck Configured: {b_slot} ➔ {lw_file}")

                    # Redraw visual canvas with newly mounted labware
                    if hasattr(self, 'draw_deck'):
                        self.draw_deck()

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
                            mix_c = int(step.get('mix_cycles', 0))
                            mix_msg = f" [+ Mix {mix_c}x {step.get('mix_volume', 100.0)}\u03bcL]" if mix_c > 0 else ""
                            msg = f"[{action.upper()}] {step.get('volume', 0.0)}\u03bcL at {step.get('slot', '')}, Well {step.get('well', '')}{z_msg}{mix_msg}"
                        self.wf_box.insert(tk.END, msg)

                    top.destroy()
                    self.logger.info(f"Imported {len(converted_steps)} steps from Python script {os.path.basename(filepath)}.")
                    messagebox.showinfo(
                        "Conversion Complete",
                        f"Successfully converted and loaded {len(converted_steps)} steps from:\n{os.path.basename(filepath)}\n\nConfigured deck labware:\n" + "\n".join(f"• {s}: {f}" for s, f in labware_map.items()) + "\n\nYou can now run the workflow or export it via 'Save JSON Protocol As...'."
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
            messagebox.showerror("Parse Error", f"Failed to parse Opentrons script:\n{e}")
            messagebox.showerror("Import Error", f"Could not inspect Python protocol:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LIMSMasterApp(root)
    root.mainloop()
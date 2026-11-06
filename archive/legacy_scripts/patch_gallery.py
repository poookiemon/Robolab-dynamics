import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# Add Pillow imports at the top if not present
if "from PIL import Image, ImageTk" not in code:
    code = "from PIL import Image, ImageTk\n" + code

old_build_tab = """    def build_analysis_tab(self):
        # Create left and right container boxes
        self.frame_heatmap = ttk.LabelFrame(self.tab_analysis, text="Quality Control (d0 Baseline Heatmaps)")
        self.frame_heatmap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Kinetic Traces (Ca2+ Curves)")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Place heatmap logic in the left box
        lbl = ttk.Label(self.frame_heatmap, text="FOC48 Baseline Heatmaps", font=("Arial", 16, "bold"))
        lbl.pack(pady=20)
        
        desc = ttk.Label(self.frame_heatmap, text="Automatically parses .stats.xml and .xml files\\nto generate Day 0 baseline heatmaps.", justify=tk.CENTER)
        desc.pack(pady=10)
        
        btn_folder = ttk.Button(self.frame_heatmap, text="Select Folder for Heatmaps", command=self.run_heatmap_analysis)
        btn_folder.pack(pady=20)"""

new_build_tab = """    def build_analysis_tab(self):
        # Create left and right container boxes
        self.frame_heatmap = ttk.LabelFrame(self.tab_analysis, text="Quality Control (Baseline Heatmaps)")
        self.frame_heatmap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_ca2 = ttk.LabelFrame(self.tab_analysis, text="Kinetic Traces (Ca2+ Curves)")
        self.frame_ca2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Place heatmap logic in the left box
        lbl = ttk.Label(self.frame_heatmap, text="FOC48 Baseline Heatmaps", font=("Arial", 16, "bold"))
        lbl.pack(pady=5)
        
        desc = ttk.Label(self.frame_heatmap, text="Automatically parses .stats.xml and .xml files\\nto generate baseline heatmaps.", justify=tk.CENTER)
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
        self._current_photo = None"""


# Update run_heatmap_analysis to remove d0 title, populate self.heatmap_image_paths, and call self.update_heatmap_gallery()
old_run = """                plt.title(f"d0 Measurement: {file_name}\\n(Calculated using {pix2mm} pixels/mm)\\nTarget Range: 3.7mm - 4.2mm", fontsize=14)"""
new_run = """                plt.title(f"Baseline Heatmap: {file_name}\\n(Calculated using {pix2mm} pixels/mm)\\nTarget Range: 3.7mm - 4.2mm", fontsize=14)"""

# Also remove the Mac folder opener
old_opener = """        # Auto-open the folder on Mac (or Windows) so they can use native Image Viewer
        import subprocess, sys
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", save_dir])
            elif sys.platform == "win32":
                os.startfile(save_dir)
        except Exception:
            pass
            
        messagebox.showinfo("Success", f"Analysis complete! Saved all heatmaps to:\\n{save_dir}")"""

new_opener = """        # Load into gallery
        self.heatmap_image_paths = [os.path.join(save_dir, f) for f in os.listdir(save_dir) if f.endswith('_heatmap.png')]
        self.heatmap_image_paths.sort()
        if self.heatmap_image_paths:
            self.current_heatmap_index = 0
            self.update_heatmap_gallery()
            
        messagebox.showinfo("Success", f"Analysis complete! Displaying heatmaps.\\nFiles saved to:\\n{save_dir}")"""


# Inject the 3 new gallery methods right before build_ops_tab
gallery_methods = """
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

    def build_ops_tab"""


if old_build_tab in code:
    code = code.replace(old_build_tab, new_build_tab)
else:
    print("FAILED build tab")

if old_run in code:
    code = code.replace(old_run, new_run)
else:
    print("FAILED run title")
    
if old_opener in code:
    code = code.replace(old_opener, new_opener)
else:
    print("FAILED opener")
    
if "def build_ops_tab" in code:
    code = code.replace("    def build_ops_tab", gallery_methods)
else:
    print("FAILED gallery methods")

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("ALL DONE")

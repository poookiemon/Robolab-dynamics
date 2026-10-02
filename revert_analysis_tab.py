import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# We need to replace build_analysis_tab and its helper functions
start_str = "    def build_analysis_tab(self):"
end_str = "    def build_dilution_tab(self):"

start_idx = code.find(start_str)
end_idx = code.find(end_str)

old_methods = code[start_idx:end_idx]

new_methods = """    def build_analysis_tab(self):
        from PyQt6.QtWidgets import QGroupBox, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap
        import os, json, glob
        import watchdog_pipeline
        
        layout = QHBoxLayout(self.tab_analysis)
        
        # LEFT SIDE: Heatmap Gallery
        left_group = QGroupBox("Quality Control (Baseline Heatmaps)")
        l_layout = QVBoxLayout(left_group)
        
        l_layout.addWidget(QLabel("<b>FOC48 Baseline Heatmaps</b>"))
        desc = QLabel("Automatically parses .stats.xml and .xml files\\nto generate baseline heatmaps.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_layout.addWidget(desc)
        
        btn_folder = QPushButton("Select Folder for Heatmaps")
        btn_folder.clicked.connect(self.run_heatmap_gallery)
        l_layout.addWidget(btn_folder)
        
        self.heatmap_display = QLabel("No image to display")
        self.heatmap_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_display.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        l_layout.addWidget(self.heatmap_display, 1) # expand
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Prev")
        self.btn_prev.setEnabled(False)
        self.btn_prev.clicked.connect(self.prev_heatmap)
        
        self.lbl_gallery = QLabel("0 / 0")
        self.lbl_gallery.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_next = QPushButton("Next >")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self.next_heatmap)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_gallery)
        nav_layout.addWidget(self.btn_next)
        l_layout.addLayout(nav_layout)
        
        # RIGHT SIDE: Launch Dashboard
        right_group = QGroupBox("Analyze Measurement")
        r_layout = QVBoxLayout(right_group)
        
        r_layout.addWidget(QLabel("<b>Kinetic Traces & Peak Forces</b>"))
        r_desc = QLabel("Launch the full-screen interactive dashboard\\nto analyze measurements and kinetic traces.")
        r_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_layout.addWidget(r_desc)
        
        btn_launch = QPushButton("Launch Dashboard")
        btn_launch.clicked.connect(self.launch_analyzer_popout)
        r_layout.addWidget(btn_launch)
        r_layout.addStretch()
        
        layout.addWidget(left_group)
        layout.addWidget(right_group)
        
        self.heatmap_images = []
        self.current_heatmap_idx = 0

    def run_heatmap_gallery(self):
        import json, os, glob
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        import watchdog_pipeline
        
        config_path = "last_dir.json"
        init_dir = "/"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f: init_dir = json.load(f).get("heatmap", "/")
        except Exception: pass
        
        folder_path = QFileDialog.getExistingDirectory(self, "Select FOC48 Data Folder", init_dir)
        if not folder_path: return
        
        try:
            data = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f: data = json.load(f)
            data["heatmap"] = folder_path
            with open(config_path, "w") as f: json.dump(data, f)
        except Exception: pass
        
        stats_files = glob.glob(os.path.join(folder_path, "*.stats.xml"))
        if not stats_files:
            QMessageBox.information(self, "No Files", f"No .stats.xml files found in {folder_path}")
            return
            
        self.log(f"Running QC on {len(stats_files)} files in {folder_path}...")
        
        # We reuse the watchdog pipeline logic to generate the images
        handler = watchdog_pipeline.FOC48Handler()
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_dir = os.path.join(folder_path, f"Analysis_{timestamp}")
        os.makedirs(save_dir, exist_ok=True)
        
        for sf in stats_files:
            handler.generate_heatmap(sf, save_dir)
            
        # Find all generated PNGs
        self.heatmap_images = glob.glob(os.path.join(save_dir, "*_heatmap.png"))
        if self.heatmap_images:
            self.current_heatmap_idx = 0
            self.update_heatmap_gallery()
            self.log(f"Generated {len(self.heatmap_images)} heatmaps successfully.")
        else:
            self.log("Failed to generate heatmap images.")
            
    def update_heatmap_gallery(self):
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        if not self.heatmap_images: return
        
        img_path = self.heatmap_images[self.current_heatmap_idx]
        pixmap = QPixmap(img_path)
        # scale keeping aspect ratio
        scaled_pixmap = pixmap.scaled(self.heatmap_display.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.heatmap_display.setPixmap(scaled_pixmap)
        
        self.lbl_gallery.setText(f"{self.current_heatmap_idx + 1} / {len(self.heatmap_images)}")
        
        self.btn_prev.setEnabled(self.current_heatmap_idx > 0)
        self.btn_next.setEnabled(self.current_heatmap_idx < len(self.heatmap_images) - 1)
        
    def prev_heatmap(self):
        if self.current_heatmap_idx > 0:
            self.current_heatmap_idx -= 1
            self.update_heatmap_gallery()
            
    def next_heatmap(self):
        if self.current_heatmap_idx < len(self.heatmap_images) - 1:
            self.current_heatmap_idx += 1
            self.update_heatmap_gallery()
            
    def launch_analyzer_popout(self):
        import subprocess, sys, os
        gui_path = os.path.join(os.path.dirname(__file__), "gui.py")
        subprocess.Popen([sys.executable, gui_path])
        self.log("Launched external Matplotlib Ca2+ Analyzer.")

"""

if start_idx != -1 and end_idx != -1:
    code = code.replace(old_methods, new_methods)
    with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

old_import_analysis = """    def build_analysis_tab(self):
        from PyQt6.QtWidgets import QGroupBox, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap
        import os, json, glob
        import watchdog_pipeline"""

new_import_analysis = """    def build_analysis_tab(self):
        from PyQt6.QtWidgets import QGroupBox, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap
        import os, sys, json, glob
        
        # Add parent directory to path so we can import watchdog_pipeline which is at the root
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        import watchdog_pipeline"""

if old_import_analysis in code:
    code = code.replace(old_import_analysis, new_import_analysis)
    
old_import_gallery = """    def run_heatmap_gallery(self):
        import json, os, glob
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        import watchdog_pipeline"""

new_import_gallery = """    def run_heatmap_gallery(self):
        import json, os, glob, sys
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        import watchdog_pipeline"""

if old_import_gallery in code:
    code = code.replace(old_import_gallery, new_import_gallery)

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("PATCH SUCCESSFUL")

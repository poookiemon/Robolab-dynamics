import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# 1. Inject imports
import_str = """from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread"""
new_import_str = """from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView"""
if import_str in code:
    code = code.replace(import_str, new_import_str)

# 2. Inject tabs
old_tabs = """        self.tab_dilution = QWidget()
        
        self.tabs.addTab(self.tab_jog, "1. Jog & Hardware")
        self.tabs.addTab(self.tab_deck, "2. 3D Deck Designer")
        self.tabs.addTab(self.tab_workflow, "3. Protocol Runner")
        self.tabs.addTab(self.tab_ops, "4. Daily Operations")
        self.tabs.addTab(self.tab_dilution, "5. SIPA Dilution Calc")
        
        self.build_jog_tab()
        self.build_deck_tab()
        self.build_workflow_tab()
        self.build_ops_tab()
        self.build_dilution_tab()"""

new_tabs = """        self.tab_dilution = QWidget()
        self.tab_analysis = QWidget()
        
        self.tabs.addTab(self.tab_jog, "1. Jog & Hardware")
        self.tabs.addTab(self.tab_deck, "2. 3D Deck Designer")
        self.tabs.addTab(self.tab_workflow, "3. Protocol Runner")
        self.tabs.addTab(self.tab_ops, "4. Daily Operations")
        self.tabs.addTab(self.tab_dilution, "5. SIPA Dilution Calc")
        self.tabs.addTab(self.tab_analysis, "6. Data Analysis & QC")
        
        self.build_jog_tab()
        self.build_deck_tab()
        self.build_workflow_tab()
        self.build_ops_tab()
        self.build_dilution_tab()
        self.build_analysis_tab()"""

if old_tabs in code:
    code = code.replace(old_tabs, new_tabs)

# 3. Inject build_analysis_tab and WatchdogRunner class
methods_str = """    def build_dilution_tab(self):"""

analysis_methods = """
class WatchdogRunner(QThread):
    log_signal = pyqtSignal(str)
    
    def run(self):
        import watchdog_pipeline
        self.log_signal.emit("Starting Watchdog Daemon in background...")
        try:
            watchdog_pipeline.start_watchdog()
        except Exception as e:
            self.log_signal.emit(f"Watchdog Error: {e}")

    def build_analysis_tab(self):
        layout = QVBoxLayout(self.tab_analysis)
        
        # Top Controls
        top_bar = QHBoxLayout()
        btn_watchdog = QPushButton("Start Hands-Free Watchdog")
        btn_watchdog.clicked.connect(self.start_watchdog_thread)
        btn_watchdog.setStyleSheet("background-color: #2b3e50; color: white; font-weight: bold; padding: 10px;")
        
        btn_manual_qc = QPushButton("Manual Heatmap QC")
        btn_manual_qc.clicked.connect(self.run_manual_heatmap_qc)
        
        btn_manual_ca2 = QPushButton("Manual Interactive Plotly")
        btn_manual_ca2.clicked.connect(self.run_manual_ca2_plotly)
        
        top_bar.addWidget(btn_watchdog)
        top_bar.addWidget(btn_manual_qc)
        top_bar.addWidget(btn_manual_ca2)
        top_bar.addStretch()
        
        layout.addLayout(top_bar)
        
        # Web Engine View for embedded HTML
        self.web_view = QWebEngineView()
        html = \"\"\"
        <html><body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #f0f0f0;">
        <h2>Interactive Plotly Engine Ready.<br>Load a Ca2+ CSV or start the Watchdog pipeline.</h2>
        </body></html>
        \"\"\"
        self.web_view.setHtml(html)
        
        layout.addWidget(self.web_view)

    def start_watchdog_thread(self):
        self.log("Initializing FOC48 Background Watchdog...")
        self.watchdog_thread = WatchdogRunner()
        self.watchdog_thread.log_signal.connect(self.log)
        self.watchdog_thread.start()
        
    def run_manual_heatmap_qc(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select FOC48 Data Folder")
        if not folder_path: return
        import watchdog_pipeline
        self.log(f"Running manual QC on {folder_path}...")
        try:
            watchdog_pipeline.FOC48Handler().run_pipeline(folder_path)
            self.log(f"QC Pipeline finished. Heatmaps generated in folder.")
        except Exception as e:
            self.log(f"Error: {e}")
            
    def run_manual_ca2_plotly(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select FOC48 CSV", filter="CSV Files (*.csv)")
        if not file_path: return
        self.log(f"Generating interactive Plotly for {file_path}...")
        try:
            import numpy as np
            import os
            from backend_plotly import generate_interactive_html
            data = np.loadtxt(file_path, delimiter=",")
            time_arr = data[:, 0]
            values_arr = data[:, 1:]
            out_file = os.path.join(os.path.dirname(file_path), "temp_interactive.html")
            generate_interactive_html(time_arr, values_arr, out_file, title=f"Kinetics: {os.path.basename(file_path)}")
            
            # Load into embedded Chromium WebEngine
            self.web_view.setUrl(QUrl.fromLocalFile(out_file))
            self.log("Plotly HTML embedded successfully.")
        except Exception as e:
            self.log(f"Error: {e}")

    def build_dilution_tab(self):"""

if methods_str in code:
    code = code.replace(methods_str, analysis_methods)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)
print("PATCH SUCCESSFUL")


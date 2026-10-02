import time
import os
import glob
import re
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add Biohit folder to path so we can import backend logic
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Biohit-Automated-Pipettor-GUI"))
try:
    from backend_qc import qc_heatmap_baselines
    from backend_plotly import generate_interactive_html
except Exception as e:
    print(f"Warning: could not import backend modules. {e}")

class FOC48Handler(FileSystemEventHandler):
    def __init__(self):
        self.pending_folders = set()
        self.last_modified = {}

    def on_any_event(self, event):
        if not event.is_directory:
            folder = os.path.dirname(event.src_path)
            # Only track top-level folders inside FOC48_Incoming
            if os.path.basename(os.path.dirname(folder)) == "FOC48_Incoming":
                self.pending_folders.add(folder)
                self.last_modified[folder] = time.time()

    def process_pending(self):
        now = time.time()
        for folder in list(self.pending_folders):
            # If no new files/writes in the last 10 seconds, assume machine is done
            if now - self.last_modified.get(folder, now) > 10.0:
                print(f"[Watchdog] Machine finished writing to: {folder}")
                self.pending_folders.remove(folder)
                self.run_pipeline(folder)

    def run_pipeline(self, folder_path):
        print(f"[Watchdog] Starting Pipeline for {folder_path}...")
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_dir = os.path.join(folder_path, f"Automated_Analysis_{timestamp}")
        os.makedirs(save_dir, exist_ok=True)
        
        # 1. Process Heatmaps
        stats_files = glob.glob(os.path.join(folder_path, "*.stats.xml"))
        for stats_file in stats_files:
            self.generate_heatmap(stats_file, save_dir)
            
        # 2. Process CSVs for Plotly HTML
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
        for csv_file in csv_files:
            self.generate_plotly(csv_file, save_dir)
            
        print(f"[Watchdog] Pipeline Complete! Results saved to {save_dir}")

    def generate_heatmap(self, stats_file, save_dir):
        print(f"[Watchdog] Generating Heatmap for {os.path.basename(stats_file)}")
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = ['1', '2', '3', '4', '5', '6']
        pix2mm = 28.7
        
        base_xml = stats_file.replace(".stats.xml", ".xml")
        
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
            except Exception: pass
            
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
            # Custom colormap: blue (<3.8), green (3.8-4.1), red (>4.1)
            colors = [
                (0.000, "mediumblue"),
                (0.332, "deepskyblue"),
                (0.333, "mediumseagreen"),  # 3.8 becomes green
                (0.500, "limegreen"),
                (0.666, "mediumseagreen"),  # 4.1 remains green
                (0.667, "lightcoral"),
                (1.000, "firebrick")
            ]
            custom_cmap = LinearSegmentedColormap.from_list("blue_green_red", colors)
            
            fig, ax = plt.subplots(figsize=(12, 9))  # 4:3 ratio
            sns.heatmap(df, annot=True, fmt=".2f", cmap=custom_cmap, vmin=3.5, vmax=4.4, cbar_kws={'label': 'Baseline (mm)'}, ax=ax)
            
            # Put X-axis labels on top (1-6)
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position('top')
            
            # Ensure Y-axis labels are horizontal and easy to read (A-H)
            plt.yticks(rotation=0)
            
            try:
                fail_mask = qc_heatmap_baselines(df)
                for i in range(df.shape[0]):
                    for j in range(df.shape[1]):
                        if fail_mask.iloc[i, j]:
                            plt.text(j + 0.5, i + 0.5, 'X', color='red', fontsize=32, ha='center', va='center', fontweight='bold', alpha=0.5)
            except Exception: pass
            
            plt.title(f"Automated QC Heatmap: {os.path.basename(stats_file)}", fontsize=14)
            plt.xlabel("Columns")
            plt.ylabel("Rows")
            
            image_name = os.path.basename(stats_file).replace(".stats.xml", "_heatmap.png")
            plt.savefig(os.path.join(save_dir, image_name), bbox_inches='tight', dpi=150)
            plt.close()
        except Exception as e:
            print(f"Error generating heatmap: {e}")

    def generate_plotly(self, csv_file, save_dir):
        print(f"[Watchdog] Generating Plotly HTML for {os.path.basename(csv_file)}")
        try:
            data = np.loadtxt(csv_file, delimiter=",")
            time_arr = data[:, 0]
            values_arr = data[:, 1:]
            html_name = os.path.basename(csv_file).replace(".csv", "_interactive.html")
            generate_interactive_html(time_arr, values_arr, os.path.join(save_dir, html_name), title=f"Automated Kinetics: {os.path.basename(csv_file)}")
        except Exception as e:
            print(f"Error generating Plotly: {e}")


def start_watchdog():
    path = os.path.expanduser("~/Desktop/FOC48_Incoming")
    print(f"Starting FOC48 Watchdog Pipeline on: {path}")
    print("Waiting for new data folders...")
    
    event_handler = FOC48Handler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            event_handler.process_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watchdog()

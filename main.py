import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys

def launch_app(app_path, cwd, extra_args=None):
    target_file = os.path.join(cwd, app_path)
    if not os.path.exists(target_file):
        messagebox.showerror("Error", f"Could not find {app_path} in {cwd}")
        return
    try:
        # Use sys.executable to ensure the same Python environment is used
        cmd = [sys.executable, app_path]
        if extra_args:
            cmd.extend(extra_args)
        subprocess.Popen(cmd, cwd=cwd)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch {app_path}:\n{str(e)}")

def main():
    root = tk.Tk()
    root.title("Robolab Dynamics - Master Hub")
    root.geometry("450x350")
    
    # Optional styling
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    
    label = ttk.Label(root, text="Robolab Dynamics Hub", font=("Helvetica", 18, "bold"))
    label.pack(pady=25)

    subtitle = ttk.Label(root, text="Select an application to launch:", font=("Helvetica", 12))
    subtitle.pack(pady=5)

    # Paths and working directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    biohit_dir = os.path.join(base_dir, "Biohit-Automated-Pipettor-GUI")
    analyze_dir = os.path.join(base_dir, "analyze-measurement-py")
    contraction_dir = os.path.join(base_dir, "contractiondb-python")

    btn_biohit = ttk.Button(
        root, 
        text="🧪 Launch Biohit Automated Pipettor", 
        command=lambda: launch_app("lims_master_gui.py", biohit_dir)
    )
    btn_biohit.pack(pady=10, fill='x', padx=60, ipady=5)

    btn_analyze = ttk.Button(
        root, 
        text="📊 Launch Analyze Measurement", 
        command=lambda: launch_app("run_gui.py", analyze_dir)
    )
    btn_analyze.pack(pady=10, fill='x', padx=60, ipady=5)

    btn_contraction = ttk.Button(
        root, 
        text="🗄️ Launch Contraction DB GUI", 
        command=lambda: launch_app("examples/contractionDbGui.py", contraction_dir)
    )
    btn_contraction.pack(pady=10, fill='x', padx=60, ipady=5)

    btn_exit = ttk.Button(root, text="Exit", command=root.destroy)
    btn_exit.pack(side='bottom', pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()

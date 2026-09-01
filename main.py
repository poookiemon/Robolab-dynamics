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
        cmd = [sys.executable, app_path]
        if extra_args:
            cmd.extend(extra_args)
            
        # Ensure the subprocess can import local modules from its root directory
        env = os.environ.copy()
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{cwd}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = cwd
            
        subprocess.Popen(cmd, cwd=cwd, env=env)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch {app_path}:\n{str(e)}")

def main():
    root = tk.Tk()
    root.title("Robolab Dynamics - Experimental Workflow")
    root.geometry("600x650")
    
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    style.configure("Step.TLabelframe", font=("Helvetica", 12, "bold"))
    style.configure("Step.TLabelframe.Label", font=("Helvetica", 12, "bold"), foreground="#333333")
    
    title_label = ttk.Label(root, text="Robolab Dynamics Pipeline", font=("Helvetica", 18, "bold"))
    title_label.pack(pady=(20, 10))

    subtitle = ttk.Label(root, text="Follow the steps below to complete the experimental workflow:", font=("Helvetica", 11))
    subtitle.pack(pady=(0, 20))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    biohit_dir = os.path.join(base_dir, "Biohit-Automated-Pipettor-GUI")
    analyze_dir = os.path.join(base_dir, "analyze-measurement-py")
    contraction_dir = os.path.join(base_dir, "contractiondb-python")

    # Step 1: Liquid Handling
    frame1 = ttk.LabelFrame(root, text=" Step 1: Liquid Handling & Setup ", style="Step.TLabelframe")
    frame1.pack(fill="x", padx=40, pady=5)
    
    lbl1 = ttk.Label(frame1, text="Prepare and execute the pipetting protocols.")
    lbl1.pack(pady=(10, 5))
    
    btn_biohit = ttk.Button(
        frame1, 
        text="🧪 Launch Biohit Automated Pipettor", 
        command=lambda: launch_app("lims_master_gui.py", biohit_dir)
    )
    btn_biohit.pack(pady=(5, 10), fill='x', padx=60, ipady=5)

    # Down Arrow
    arrow1 = ttk.Label(root, text="⬇", font=("Helvetica", 16))
    arrow1.pack()

    # Step 2: Analysis & Measurements
    frame2 = ttk.LabelFrame(root, text=" Step 2: Analysis & Measurements ", style="Step.TLabelframe")
    frame2.pack(fill="x", padx=40, pady=5)
    
    lbl2 = ttk.Label(frame2, text="Analyze measurements and compute curves.")
    lbl2.pack(pady=(10, 5))

    btn_analyze = ttk.Button(
        frame2, 
        text="📊 Launch Analyze Measurement", 
        command=lambda: launch_app("run_gui.py", analyze_dir)
    )
    btn_analyze.pack(pady=5, fill='x', padx=60, ipady=5)

    btn_ca_curves = ttk.Button(
        frame2, 
        text="📈 Launch CA Curves (Pending Repo Addition)", 
        state=tk.DISABLED
    )
    btn_ca_curves.pack(pady=(5, 10), fill='x', padx=60, ipady=5)

    # Down Arrow
    arrow2 = ttk.Label(root, text="⬇", font=("Helvetica", 16))
    arrow2.pack()

    # Step 3: Database & Archiving
    frame3 = ttk.LabelFrame(root, text=" Step 3: Database & Archiving ", style="Step.TLabelframe")
    frame3.pack(fill="x", padx=40, pady=5)
    
    lbl3 = ttk.Label(frame3, text="Upload and archive results to the database.")
    lbl3.pack(pady=(10, 5))

    btn_contraction = ttk.Button(
        frame3, 
        text="🗄️ Launch Contraction DB GUI", 
        command=lambda: launch_app("examples/contractionDbGui.py", contraction_dir)
    )
    btn_contraction.pack(pady=(5, 10), fill='x', padx=60, ipady=5)

    # Bottom exit button
    btn_exit = ttk.Button(root, text="Exit Pipeline", command=root.destroy)
    btn_exit.pack(pady=(20, 10))

    root.mainloop()

if __name__ == "__main__":
    main()

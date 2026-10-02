import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'r') as f:
    code = f.read()

# Replace the exact 5 logic with dynamic length logic
old_block1 = """        # 1. Target the pre-calculated FOC48 peak files
        file_paths = filedialog.askopenfilenames(
            title="Select exactly 5 '*peak_forces.csv' files",
            filetypes=[("Peak Forces CSV", "*peak_forces.csv"), ("All CSV", "*.csv")]
        )
        if not file_paths or len(file_paths) != 5:
            print("Operation aborted: Exactly 5 files required.")
            return

        file_paths = sorted(file_paths)
        print(f"Ingesting target files: {[os.path.basename(p) for p in file_paths]}")

        # 2. Acquire concentration gradient parameters
        conc_str = simpledialog.askstring(
            "Concentration Gradient",
            "Enter 5 Calcium concentrations (mM) separated by commas:\\n(e.g., 0.2, 0.5, 1.0, 2.0, 4.0)",
            initialvalue="0.2, 0.5, 1.0, 2.0, 4.0"
        )
        if not conc_str: return

        try:
            concentrations = np.array([float(x.strip()) for x in conc_str.split(',')])
            if len(concentrations) != 5: raise ValueError
        except ValueError:
            Messagebox.show_error("Invalid matrix. Require exactly 5 numeric values.", "Parsing Error")
            return"""

new_block1 = """        # 1. Target the pre-calculated FOC48 peak files
        file_paths = filedialog.askopenfilenames(
            title="Select '*peak_forces.csv' or standard '.csv' files",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not file_paths:
            return
            
        num_files = len(file_paths)

        file_paths = sorted(file_paths)
        print(f"Ingesting {num_files} target files: {[os.path.basename(p) for p in file_paths]}")

        # 2. Acquire concentration gradient parameters dynamically
        default_concs = ", ".join([str(0.2 * (i+1)) for i in range(num_files)])
        conc_str = simpledialog.askstring(
            "Concentration Gradient",
            f"You selected {num_files} files.\\nEnter {num_files} Calcium concentrations (mM) separated by commas:\\n(e.g., {default_concs})",
            initialvalue=default_concs
        )
        if not conc_str: return

        try:
            concentrations = np.array([float(x.strip()) for x in conc_str.split(',')])
            if len(concentrations) != num_files: 
                raise ValueError
        except ValueError:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Parsing Error", f"Invalid input. You must enter exactly {num_files} numeric values separated by commas.")
            return"""

if old_block1 in code:
    code = code.replace(old_block1, new_block1)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

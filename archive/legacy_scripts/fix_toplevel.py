with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# Replace ttk.Toplevel with tk.Toplevel
bad_code = "        popout = ttk.Toplevel(self.root)"
good_code = "        popout = tk.Toplevel(self.root)"

if bad_code in code:
    code = code.replace(bad_code, good_code)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

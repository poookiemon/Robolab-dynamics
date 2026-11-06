with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

old_block = """        is_multi = messagebox.askyesno("Pipette Configuration", "Are you using a Multichannel Pipette for this routine?")
        self.logger.info(f"System Boot: {'Multichannel' if is_multi else 'Single-channel'} direct mapping | Tracking bypassed. Pure kinematics engaged.")"""

new_block = """        # Multichannel prompt disabled per user request - defaulting to Single-channel
        is_multi = False
        self.logger.info(f"System Boot: {'Multichannel' if is_multi else 'Single-channel'} direct mapping | Tracking bypassed. Pure kinematics engaged.")"""

if old_block in code:
    code = code.replace(old_block, new_block)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO FIND OLD BLOCK")


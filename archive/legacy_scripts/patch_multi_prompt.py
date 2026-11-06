with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

import re

# We will regex out the askyesno call and replace it with is_multi = False
old_pattern = r'is_multi\s*=\s*messagebox\.askyesno\([\s\S]*?Single-Channel"\s*\)'

new_code = re.sub(old_pattern, 'is_multi = False  # Auto-defaulted to Single-Channel per user request', code)

if new_code != code:
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(new_code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")

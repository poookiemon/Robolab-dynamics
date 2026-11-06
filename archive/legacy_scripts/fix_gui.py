with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

bad_line = "file_name = os.path.basename(stats_file_path=stats_file)"
good_line = "file_name = os.path.basename(stats_file)"

if bad_line in code:
    code = code.replace(bad_line, good_line)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(code)
    print("FIXED")
else:
    print("NOT FOUND")
